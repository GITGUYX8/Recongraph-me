from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from contextvars import ContextVar
from pathlib import Path
import os
import io
import uuid
import csv
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from recongraph.engine import ReconGraphEngine
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
from .database import AsyncSessionLocal, engine
from . import repository
from . import models  # noqa: F401  (registers models on Base.metadata)
from .processing import run_engine

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


# Persistence: single SQLAlchemy/async store (see models.py, repository.py).
UPLOAD_ROOT = Path(os.getenv("RECONGRAPH_UPLOAD_DIR", "./data/uploads"))
_gst_portal = StubGSTPortalClient()
_nic = StubNicClient()


@app.on_event("startup")
async def _startup_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


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


async def _persist_upload(
    session, run_id: str, tenant_id: str, kind: str, upload: UploadFile, content: bytes
) -> str:
    relative = str(Path(tenant_id) / run_id / f"{kind}{Path(upload.filename).suffix}")
    abs_path = UPLOAD_ROOT / relative
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(content)
    await repository.create_upload(
        session, run_id, tenant_id, kind, upload.filename, len(content), relative
    )
    return relative


@app.post("/reconcile", response_model=RunResponse)
async def reconcile(
    purchases: UploadFile = File(...),
    gsts: UploadFile = File(...),
    current_user: dict = Depends(require_auditor),
):
    MAX_CSV_SIZE = 10 * 1024 * 1024
    tenant_id = current_user.get("tenant_id", "tenant-001")

    p_content_bytes = await purchases.read()
    if len(p_content_bytes) > MAX_CSV_SIZE:
        raise HTTPException(status_code=413, detail="Purchases CSV exceeds 10MB limit.")
    g_content_bytes = await gsts.read()
    if len(g_content_bytes) > MAX_CSV_SIZE:
        raise HTTPException(status_code=413, detail="GSTs CSV exceeds 10MB limit.")

    run_id = str(uuid.uuid4())
    try:
        async with AsyncSessionLocal() as session:
            await repository.create_run(
                session, run_id, tenant_id, current_user.get("username", "unknown")
            )
            await _persist_upload(session, run_id, tenant_id, "purchases", purchases, p_content_bytes)
            await _persist_upload(session, run_id, tenant_id, "gsts", gsts, g_content_bytes)
            await repository.create_job(session, run_id, tenant_id)
    except Exception as e:
        logger.exception("Failed to enqueue reconciliation run %s", run_id)
        raise HTTPException(status_code=500, detail=str(e))

    return RunResponse(run_id=run_id, status="queued", message="Job dispatched successfully")


@app.get("/runs/{run_id}")
async def get_run(run_id: str, current_user: dict = Depends(require_auditor)):
    tenant_id = current_user.get("tenant_id", "tenant-001")
    async with AsyncSessionLocal() as session:
        run = await repository.get_run_for_tenant(session, run_id, tenant_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        run["actions"] = await repository.get_run_actions(session, run_id)
        job = await repository.get_job_for_run(session, run_id)
    if job:
        run["job"] = job
    return run


@app.get("/runs")
async def list_runs(current_user: dict = Depends(require_auditor)):
    tenant_id = current_user.get("tenant_id", "tenant-001")
    async with AsyncSessionLocal() as session:
        return await repository.list_runs(session, tenant_id)


@app.post("/runs/{run_id}/actions")
async def apply_actions(run_id: str, request: ActionBatchRequest, current_user: dict = Depends(require_auditor)):
    tenant_id = current_user.get("tenant_id", "tenant-001")
    async with AsyncSessionLocal() as session:
        run = await repository.get_run_for_tenant(session, run_id, tenant_id)
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
            await repository.apply_packet_action(session, run_id, tenant_id, item.packet_id, {
                "action": decision.action.value,
                "status": decision.status,
                "itc_availability": itc.availability.value,
                "itc_claim_period": itc.claim_period,
                "reason_itc_unavailability": itc.reason_unavailable,
                "reviewer_id": decision.reviewer_id,
                "comments": decision.comments,
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
    tenant_id = current_user.get("tenant_id", "tenant-001")
    async with AsyncSessionLocal() as session:
        run = await repository.get_run_for_tenant(session, run_id, tenant_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        packet = next(
            (p for p in (run["result"] or {}).get("review_packets", []) if p.get("packet_id") == packet_id),
            None,
        )
        if not packet:
            raise HTTPException(status_code=404, detail="Packet not found")
        packet["ims"] = await repository.get_packet_action(session, run_id, packet_id)
    return packet


@app.get("/runs/{run_id}/export")
async def export_run(run_id: str, report: str = "match_summary", format: str = "csv", current_user: dict = Depends(require_auditor)):
    tenant_id = current_user.get("tenant_id", "tenant-001")
    async with AsyncSessionLocal() as session:
        run = await repository.get_run_for_tenant(session, run_id, tenant_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        result = run.get("result")

    try:
        payload = compliance_reports.export_report(result, report, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))

    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if format == "xlsx" else "text/csv"
    return Response(content=payload, media_type=media_type)


@app.get("/export/{run_id}")
async def export_run_csv(run_id: str, current_user: dict = Depends(require_auditor)):
    tenant_id = current_user.get("tenant_id", "tenant-001")
    async with AsyncSessionLocal() as session:
        run = await repository.get_run_for_tenant(session, run_id, tenant_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.get("status") != "success":
            raise HTTPException(status_code=400, detail="Run not completed yet")
        result = run.get("result") or {}
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
    tenant_id = current_user.get("tenant_id", "tenant-001")
    try:
        async with AsyncSessionLocal() as session:
            await repository.save_feedback(session, {
                "tenant_id": tenant_id,
                "packet_id": feedback.packet_id,
                "purchase_record_id": feedback.purchase_record_id,
                "gst_record_id": feedback.gst_record_id,
                "deterministic_decision": feedback.deterministic_decision,
                "deterministic_score": feedback.deterministic_score,
                "deterministic_coverage": feedback.deterministic_coverage,
                "ml_score": feedback.ml_score,
                "calibrated_ml_probability": feedback.calibrated_ml_probability,
                "graph_features": json.dumps(feedback.graph_features),
                "evidence_features": json.dumps(feedback.evidence_features),
                "final_human_decision": feedback.action,
                "reviewer_action": feedback.action,
                "engine_version": feedback.engine_version,
                "model_version": feedback.model_version,
                "config_hash": feedback.config_hash,
                "explanation_version": feedback.explanation_version,
                "rag_context_identifiers": json.dumps(feedback.rag_context_identifiers),
                "legacy_payload": json.dumps(feedback.payload),
            })
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

        result = run_engine(P, G).to_dict()

    run_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        await repository.create_run(session, run_id, "tenant-001", "demo", status="success")
        await repository.save_run_result(
            session,
            run_id,
            result_json=json.dumps(result),
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
