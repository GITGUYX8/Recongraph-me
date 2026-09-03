from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from contextvars import ContextVar
import uuid
import io
import csv
import json
import logging
import sqlite3
from decimal import Decimal
from datetime import date, datetime, timezone, timedelta
from typing import Dict, Any, Optional

from recongraph.config import ReconGraphConfig
from recongraph.engine import ReconGraphEngine
from recongraph.plugins.core_providers import (
    FinancialEvidenceProvider, TemporalEvidenceProvider, TaxEvidenceProvider,
    VendorEvidenceProvider, ReferenceEvidenceProvider,
)
from recongraph.domain.vendor.context import VendorIdentityContext
from recongraph.matching.reference_evidence import (
    build_reference_corpus_profile, ReferenceEvidenceContext, ReferenceEvidencePolicy,
)

from recongraph.compliance.csv_parsing import parse_purchase_csv, parse_gst_csv
from recongraph.compliance.ims import ImsAction, apply_action
from recongraph.compliance.itc_claim import set_itc_claim_period_on_match
from recongraph.compliance import reports as compliance_reports
from recongraph.compliance.integrations.gst_portal import (
    StubGSTPortalClient, inward_supply_batch_to_records,
)
from recongraph.compliance.integrations.models import InwardSupplyBatch, InwardSupplyItem
from recongraph.compliance.integrations.nic import StubNicClient

# App components (Phase 8+)
from . import auth
from .auth import authenticate_demo_user, create_access_token, register_temporary_user, require_auditor, require_admin
from .store import Store

logger = logging.getLogger("recongraph-api")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s')

app = FastAPI(title="ReconGraph API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.include_router(auth.router)

request_id_var: ContextVar[str] = ContextVar("request_id", default="unknown")


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()
        return True


logger.addFilter(RequestIdFilter())


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    req_id = str(uuid.uuid4())
    request_id_var.set(req_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


# Persistence: SQLite store (compliance port) + legacy in-memory store (Phase 8).
store = Store()
_runs_store: Dict[str, dict] = {}
_gst_portal = StubGSTPortalClient()
_nic = StubNicClient()


# Setup SQLite for HITL Feedback (Phase 8)
def init_db():
    conn = sqlite3.connect('hitl_feedback.db')
    c = conn.cursor()

    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='feedback_v2'")
    v2_exists = c.fetchone() is not None

    if not v2_exists:
        c.execute('''
            CREATE TABLE feedback_v2
            (review_id INTEGER PRIMARY KEY AUTOINCREMENT,
             packet_id TEXT,
             purchase_record_id TEXT,
             gst_record_id TEXT,
             deterministic_decision TEXT,
             deterministic_score REAL,
             deterministic_coverage REAL,
             ml_score REAL,
             calibrated_ml_probability REAL,
             graph_features TEXT,
             evidence_features TEXT,
             final_human_decision TEXT,
             reviewer_action TEXT,
             timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
             engine_version TEXT,
             model_version TEXT,
             config_hash TEXT,
             explanation_version TEXT,
             rag_context_identifiers TEXT,
             legacy_payload TEXT)
        ''')
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='feedback'")
        v1_exists = c.fetchone() is not None
        if v1_exists:
            c.execute("SELECT packet_id, action, timestamp, payload FROM feedback")
            rows = c.fetchall()
            for row in rows:
                packet_id, action, timestamp, payload = row
                try:
                    payload_dict = json.loads(payload)
                except Exception:
                    payload_dict = {}
                c.execute('''
                    INSERT INTO feedback_v2
                    (packet_id, reviewer_action, timestamp, legacy_payload)
                    VALUES (?, ?, ?, ?)
                ''', (packet_id, action, timestamp, payload))
            c.execute("ALTER TABLE feedback RENAME TO feedback_v1_backup")

    conn.commit()
    conn.close()


init_db()


class FeedbackRequest(BaseModel):
    packet_id: str
    action: str
    purchase_record_id: str = ""
    gst_record_id: str = ""
    deterministic_decision: str = ""
    deterministic_score: float = 0.0
    deterministic_coverage: float = 0.0
    ml_score: float = 0.0
    calibrated_ml_probability: float = 0.0
    graph_features: dict = {}
    evidence_features: dict = {}
    engine_version: str = ""
    model_version: str = ""
    config_hash: str = ""
    explanation_version: str = ""
    rag_context_identifiers: list = []
    payload: dict = {}


class SignupRequest(BaseModel):
    username: str
    password: str


class RunResponse(BaseModel):
    run_id: str
    status: str
    message: str


class ActionRequest(BaseModel):
    packet_id: str
    action: str
    reviewer_id: Optional[str] = "system"
    comments: Optional[str] = ""


class ActionBatchRequest(BaseModel):
    packets: list[ActionRequest]


def _build_providers(purchases, gsts):
    corpus = build_reference_corpus_profile([r.reference for r in purchases + gsts])
    ref_ctx = ReferenceEvidenceContext(corpus, ReferenceEvidencePolicy())
    vendor_ctx = VendorIdentityContext(corpus_profile=None)
    return [
        FinancialEvidenceProvider(),
        TemporalEvidenceProvider(),
        TaxEvidenceProvider(),
        VendorEvidenceProvider(vendor_ctx),
        ReferenceEvidenceProvider(ref_ctx),
    ]


def _run_engine(purchases, gsts):
    providers = _build_providers(purchases, gsts)
    engine = ReconGraphEngine(config=ReconGraphConfig(), providers=providers)
    return engine.reconcile(purchases, gsts)


from fastapi.security import OAuth2PasswordRequestForm


@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        role = authenticate_demo_user(form_data.username, form_data.password)
    except RuntimeError as exc:
        logger.error("Authentication is unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="Authentication is not configured") from exc

    access_token_expires = timedelta(minutes=60 * 24)
    access_token = create_access_token(
        data={"sub": form_data.username, "role": role, "tenant_id": "tenant-001"},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest):
    username = request.username.strip()
    if len(username) < 3 or len(username) > 64:
        raise HTTPException(status_code=400, detail="Username must be between 3 and 64 characters")
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    try:
        register_temporary_user(username, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.error("Signup is unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="Authentication is not configured") from exc
    return {"status": "created", "message": "Account created. You can now sign in."}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/ready")
async def readiness_check():
    return {"status": "ready"}


@app.get("/version")
async def version_check():
    return {"version": ReconGraphEngine.VERSION}


def _run_reconciliation_task(run_id: str, p_content: str, g_content: str):
    try:
        _runs_store[run_id] = {"status": "processing", "message": "Parsing CSV and generating graphs"}
        P = parse_purchase_csv(p_content)
        G = parse_gst_csv(g_content)

        if not P or not G:
            _runs_store[run_id] = {"status": "failed", "message": "One or both CSV files were empty or unparseable."}
            return

        _runs_store[run_id] = {"status": "processing", "message": "Engine running hypothesis search"}
        result = _run_engine(P, G)

        result_dict = result.to_dict()
        _runs_store[run_id] = {"status": "success", "result": result_dict}
        store.save_run(
            run_id=run_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            status="success",
            result=result_dict,
            engine_version=result.engine_version,
        )
    except Exception as e:
        logger.error(f"Reconciliation task {run_id} failed: {e}")
        _runs_store[run_id] = {"status": "failed", "message": str(e)}


@app.post("/reconcile", response_model=RunResponse)
async def reconcile(
    purchases: UploadFile = File(...),
    gsts: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: dict = Depends(require_auditor),
):
    MAX_CSV_SIZE = 10 * 1024 * 1024

    try:
        logger.info(f"Received reconciliation request. Purchases: {purchases.filename}, GSTs: {gsts.filename}")
        p_content_bytes = await purchases.read()
        if len(p_content_bytes) > MAX_CSV_SIZE:
            raise HTTPException(status_code=413, detail="Purchases CSV exceeds 10MB limit.")

        g_content_bytes = await gsts.read()
        if len(g_content_bytes) > MAX_CSV_SIZE:
            raise HTTPException(status_code=413, detail="GSTs CSV exceeds 10MB limit.")

        p_content = p_content_bytes.decode("utf-8")
        g_content = g_content_bytes.decode("utf-8")

        run_id = str(uuid.uuid4())
        _runs_store[run_id] = {"status": "queued", "message": "Job queued for background processing"}

        if background_tasks:
            background_tasks.add_task(_run_reconciliation_task, run_id, p_content, g_content)
        else:
            _run_reconciliation_task(run_id, p_content, g_content)

        return RunResponse(run_id=run_id, status="queued", message="Job dispatched successfully")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    run = store.get_run(run_id)
    if not run:
        if run_id in _runs_store:
            return _runs_store[run_id]
        raise HTTPException(status_code=404, detail="Run not found")
    run["actions"] = store.get_run_actions(run_id)
    return run


@app.get("/runs")
async def list_runs(current_user: dict = Depends(require_auditor)):
    return store.list_runs()


@app.post("/runs/{run_id}/actions")
async def apply_actions(run_id: str, request: ActionBatchRequest, current_user: dict = Depends(require_auditor)):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    results = []
    for item in request.packets:
        try:
            action = ImsAction(item.action)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown action '{item.action}'")

        decision = apply_action(
            packet_id=item.packet_id,
            action=action,
            reviewer_id=item.reviewer_id or "system",
            comments=item.comments or "",
        )
        itc = set_itc_claim_period_on_match(
            match_date=datetime.now(timezone.utc).date(),
            available=action == ImsAction.ACCEPT,
        )
        store.apply_action(run_id, item.packet_id, {
            "action": decision.action.value,
            "status": decision.status,
            "itc_availability": itc.availability.value,
            "itc_claim_period": itc.claim_period,
            "reason_itc_unavailability": itc.reason_unavailable,
            "reviewer_id": decision.reviewer_id,
            "comments": decision.comments,
            "updated_at": decision.updated_at,
        })
        results.append({
            "packet_id": item.packet_id,
            "action": decision.action.value,
            "status": decision.status,
            **itc.to_dict(),
        })

    return {"run_id": run_id, "applied": results}


@app.get("/runs/{run_id}/packets/{packet_id}")
async def get_packet(run_id: str, packet_id: str, current_user: dict = Depends(require_auditor)):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    packet = next(
        (p for p in run["result"].get("review_packets", []) if p.get("packet_id") == packet_id),
        None,
    )
    if not packet:
        raise HTTPException(status_code=404, detail="Packet not found")
    packet["ims"] = store.get_packet_action(run_id, packet_id)
    return packet


@app.get("/runs/{run_id}/export")
async def export_run(run_id: str, report: str = "match_summary", format: str = "csv", current_user: dict = Depends(require_auditor)):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    try:
        payload = compliance_reports.export_report(run["result"], report, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))

    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if format == "xlsx" else "text/csv"
    return Response(content=payload, media_type=media_type)


@app.get("/export/{run_id}")
async def export_run_csv(run_id: str, current_user: dict = Depends(require_auditor)):
    if run_id not in _runs_store:
        raise HTTPException(status_code=404, detail="Run not found")

    run_data = _runs_store[run_id]
    if run_data.get("status") != "success":
        raise HTTPException(status_code=400, detail="Run not completed yet")

    result = run_data.get("result", {})
    packets = result.get("packets", [])

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Packet ID", "Decision", "Polarity", "Missing PR Count", "Missing GST Count",
        "PR Total", "GST Total", "Champion Confidence", "Challenger Confidence",
        "AI Decision", "Reason Codes", "Dataset Version",
    ])

    for p in packets:
        decision = p.get("decision", "UNKNOWN")
        polarity = p.get("polarity", "NONE")
        missing_pr = len(p.get("missing_evidence", {}).get("missing_in_pr", []))
        missing_gst = len(p.get("missing_evidence", {}).get("missing_in_gstr2b", []))

        pr_total = sum(float(r.get("amount", 0)) for r in p.get("purchase_records", []))
        gst_total = sum(float(r.get("amount", 0)) for r in p.get("gst_records", []))

        ai_prov = p.get("ai_provenance", {})
        champ_conf = ai_prov.get("confidence", 0)
        chall_conf = ai_prov.get("challenger_confidence", 0)
        ai_decision = ai_prov.get("decision", "UNKNOWN")

        reason_codes = []
        if champ_conf >= 0.95:
            reason_codes.append("HIGH_CONFIDENCE_MATCH")
        elif champ_conf < 0.70:
            reason_codes.append("LOW_CONFIDENCE_REJECT")
        else:
            reason_codes.append("AMBIGUOUS_SCORE_REVIEW")

        dataset_version = "v1-ai-prod"

        writer.writerow([
            p.get("packet_id"), decision, polarity, missing_pr, missing_gst,
            pr_total, gst_total, champ_conf, chall_conf,
            ai_decision, "|".join(reason_codes), dataset_version,
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=recongraph_audit_{run_id}.csv"},
    )


@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest, current_user: dict = Depends(require_auditor)):
    try:
        conn = sqlite3.connect('hitl_feedback.db')
        c = conn.cursor()
        c.execute(
            """INSERT INTO feedback_v2
               (packet_id, purchase_record_id, gst_record_id, deterministic_decision,
                deterministic_score, deterministic_coverage, ml_score, calibrated_ml_probability,
                graph_features, evidence_features, final_human_decision, reviewer_action,
                engine_version, model_version, config_hash, explanation_version,
                rag_context_identifiers, legacy_payload)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                feedback.packet_id,
                feedback.purchase_record_id,
                feedback.gst_record_id,
                feedback.deterministic_decision,
                feedback.deterministic_score,
                feedback.deterministic_coverage,
                feedback.ml_score,
                feedback.calibrated_ml_probability,
                json.dumps(feedback.graph_features),
                json.dumps(feedback.evidence_features),
                feedback.action,
                feedback.action,
                feedback.engine_version,
                feedback.model_version,
                feedback.config_hash,
                feedback.explanation_version,
                json.dumps(feedback.rag_context_identifiers),
                json.dumps(feedback.payload),
            ),
        )
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/portal/import-2b")
async def import_2b(file: UploadFile = File(...), current_user: dict = Depends(require_auditor)):
    """Scaffold: accept a downloaded GSTR-2B JSON payload and return records."""
    content = (await file.read()).decode("utf-8")
    payload = json.loads(content)
    period = payload.get("data", {}).get("rtnprd") or payload.get("fp") or "unknown"
    gstin = payload.get("gstin", "unknown")
    items = _inward_items_from_payload(payload)
    batch = InwardSupplyBatch(gstin=gstin, return_period=period, return_type="GSTR2B", items=items)
    records = inward_supply_batch_to_records(batch)
    return {
        "return_period": period,
        "gstin": gstin,
        "record_count": len(records),
        "records": [r.__dict__ for r in records],
    }


@app.get("/portal/gstin/{gstin}")
async def verify_gstin(gstin: str, current_user: dict = Depends(require_auditor)):
    status = _gst_portal.verify_gstin(gstin)
    return {"gstin": status.gstin, "valid": status.valid, "status": status.status}


@app.post("/nic/e-invoice")
async def e_invoice(payload: Dict[str, Any], current_user: dict = Depends(require_auditor)):
    return _nic.generate_e_invoice(payload).__dict__


@app.post("/nic/e-waybill")
async def e_waybill(payload: Dict[str, Any], current_user: dict = Depends(require_auditor)):
    return _nic.generate_e_waybill(payload).__dict__


@app.get("/demo")
async def get_demo():
    """Returns the challenge dataset result instantly, persisted as a run."""
    from pathlib import Path

    demo_file = Path("demo_results.json")
    if demo_file.exists():
        with open(demo_file, "r") as f:
            result = json.load(f)
    else:
        challenge_dir = Path("../datasets/challenge")
        p_csv = challenge_dir / "purchase_register_v1.csv"
        g_csv = challenge_dir / "gst_records_v1.csv"

        if not p_csv.exists() or not g_csv.exists():
            raise HTTPException(status_code=404, detail="Demo dataset not found")

        with open(p_csv, "r") as f:
            P = parse_purchase_csv(f.read())
        with open(g_csv, "r") as f:
            G = parse_gst_csv(f.read())

        result = _run_engine(P, G).to_dict()

    run_id = str(uuid.uuid4())
    store.save_run(
        run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        status="success",
        result=result,
        engine_version=result.get("engine_version"),
    )
    return {"run_id": run_id, "status": "success", "result": result}


def _inward_items_from_payload(payload: dict) -> list[InwardSupplyItem]:
    """Best-effort mapping from a GSTR-2B JSON payload to inward supply items."""
    items = []
    data = payload.get("data", payload)
    docs = data.get("docdata") or data.get("b2b") or []
    for doc in docs:
        for inv in doc.get("inv", []):
            items.append(InwardSupplyItem(
                bill_no=inv.get("inum"),
                bill_date=_parse_date(inv.get("idt")),
                supplier_gstin=doc.get("ctin"),
                supplier_name=doc.get("trdnm"),
                taxable_value=_dec(inv.get("val")),
                cgst=_dec(inv.get("camt")),
                sgst=_dec(inv.get("samt")),
                igst=_dec(inv.get("iamt")),
                cess=_dec(inv.get("csamt")),
                place_of_supply=inv.get("pos"),
                is_reverse_charge=(inv.get("rchrg") == "Y"),
                classification="B2B",
                irn_number=inv.get("irn"),
                irn_source=None,
            ))
    return items


def _dec(value) -> Decimal | None:
    try:
        return Decimal(str(value)) if value is not None else None
    except Exception:
        return None


def _parse_date(value) -> Any:
    try:
        return date.fromisoformat(str(value))
    except Exception:
        return None
