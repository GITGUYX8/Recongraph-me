"""Durable reconciliation worker.

Polls PostgreSQL (or SQLite in dev) for queued jobs, claims them atomically,
runs the reconciliation engine off the request path, and records durable
status/results. Run as:

    python -m uvicorn ...  (API)
    python -m app.worker    (this process)

Recovery: on startup, abandoned ``processing`` jobs (expired lease) are
requeued before new jobs are claimed.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Uvicorn loads this file for the API via --env-file; the standalone worker
# needs to load the same local configuration itself.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from .database import AsyncSessionLocal, engine
from . import repository

logger = logging.getLogger("recongraph-api.worker")

LEASES_SECONDS = int(os.getenv("RECONGRAPH_JOB_LEASE_SECONDS", "1800"))
MAX_ATTEMPTS = int(os.getenv("RECONGRAPH_JOB_MAX_ATTEMPTS", "3"))
POLL_INTERVAL = float(os.getenv("RECONGRAPH_JOB_POLL_INTERVAL", "2.0"))
RETRY_DELAY_SECONDS = int(os.getenv("RECONGRAPH_JOB_RETRY_DELAY", "60"))
UPLOAD_ROOT = Path(os.getenv("RECONGRAPH_UPLOAD_DIR", "./data/uploads"))

WORKER_ID = os.getenv("RECONGRAPH_WORKER_ID", f"worker-{os.getpid()}")


async def _run_reconciliation(job: dict[str, object]) -> None:
    """Execute one claimed job: read uploads, run engine, persist result."""
    from recongraph.compliance.csv_parsing import parse_purchase_csv, parse_gst_csv

    run_id = job["run_id"]
    tenant_id = job["tenant_id"]

    async with AsyncSessionLocal() as session:
        await repository.update_run_status(session, run_id, "processing")

        p_path = await repository.get_upload(session, run_id, tenant_id, "purchases")
        g_path = await repository.get_upload(session, run_id, tenant_id, "gsts")
        if not p_path or not g_path:
            raise FileNotFoundError("Uploaded purchase/GST files are missing for this run")

        p_bytes = (UPLOAD_ROOT / p_path).read_bytes()
        g_bytes = (UPLOAD_ROOT / g_path).read_bytes()

    p_content = p_bytes.decode("utf-8")
    g_content = g_bytes.decode("utf-8")
    P = parse_purchase_csv(p_content)
    G = parse_gst_csv(g_content)

    if not P or not G:
        raise ValueError("One or both CSV files were empty or unparseable.")

    from .processing import run_engine

    result = await asyncio.to_thread(run_engine, P, G)
    result_dict = result.to_dict()

    async with AsyncSessionLocal() as session:
        await repository.save_run_result(
            session,
            run_id,
            result_json=json.dumps(result_dict),
            engine_version=getattr(result, "engine_version", None),
        )


async def process_one() -> bool:
    async with AsyncSessionLocal() as session:
        job = await repository.claim_next_job(
            session, WORKER_ID, lease_seconds=LEASES_SECONDS, max_attempts=MAX_ATTEMPTS
        )
        if job is None:
            return False
        job_id = job["id"]

    try:
        await _run_reconciliation(job)
        async with AsyncSessionLocal() as session:
            await repository.complete_job(session, job_id)
        logger.info("Job %s (run %s) completed", job_id, job["run_id"])
    except Exception as exc:  # noqa: BLE001 - worker must not crash on job errors
        logger.exception("Job %s (run %s) failed", job_id, job["run_id"])
        async with AsyncSessionLocal() as session:
            await repository.fail_job(
                session,
                job_id,
                str(exc),
                retry_delay_seconds=RETRY_DELAY_SECONDS,
                max_attempts=MAX_ATTEMPTS,
            )
    return True


async def run() -> None:
    logger.info("Worker %s starting", WORKER_ID)
    while True:
        try:
            async with AsyncSessionLocal() as session:
                await repository.requeue_expired_leases(session)
            worked = await process_one()
            if not worked:
                await asyncio.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Worker %s shutting down", WORKER_ID)
            break
        except Exception:  # noqa: BLE001
            logger.exception("Worker loop error")
            await asyncio.sleep(POLL_INTERVAL)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    # Ensure schema exists even if Alembic has not been run (dev convenience).
    asyncio.run(_init_schema())
    asyncio.run(run())


async def _init_schema() -> None:
    from . import models  # noqa: F401  (registers models on Base.metadata)

    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


if __name__ == "__main__":
    sys.exit(main())
