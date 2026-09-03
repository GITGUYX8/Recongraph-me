"""Durable job-model tests for the reconciliation pipeline.

These exercise the repository and worker directly against an isolated SQLite
database (see conftest.py) so they run without a database server or a live
worker process.
"""

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "recongraph-api"))

from app.database import AsyncSessionLocal
from app import models, repository
from app import worker as worker_module

import app.main as main_app


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch):
    monkeypatch.setenv("RECONGRAPH_AUTH_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("RECONGRAPH_DEMO_ADMIN_USERNAME", "demo-admin")
    monkeypatch.setenv("RECONGRAPH_DEMO_ADMIN_PASSWORD", "correct-password")
    monkeypatch.setenv("RECONGRAPH_DEMO_AUDITOR_USERNAME", "demo-auditor")
    monkeypatch.setenv("RECONGRAPH_DEMO_AUDITOR_PASSWORD", "auditor-password")
    from app import auth as auth_mod
    auth_mod.clear_auth_config_cache()
    yield
    auth_mod.clear_auth_config_cache()


@pytest.fixture(scope="module")
def app_client():
    with TestClient(main_app.app) as c:
        yield c


async def _create_ready_run(run_id: str, tenant: str = "tenant-001", user: str = "tester") -> int:
    async with AsyncSessionLocal() as session:
        await repository.create_run(session, run_id, tenant, user)
        for kind in ("purchases", "gsts"):
            relative = f"{tenant}/{run_id}/{kind}.csv"
            path = Path(main_app.UPLOAD_ROOT) / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("a,b\n1,2\n")
            await repository.create_upload(session, run_id, tenant, kind, f"{kind}.csv", 8, relative)
        await repository.create_job(session, run_id, tenant)
        job = await repository.get_job_for_run(session, run_id)
        return job["id"]


async def test_claim_next_job_is_atomic():
    run_id = "run-claim-1"
    job_id = await _create_ready_run(run_id)
    async with AsyncSessionLocal() as session:
        claimed = await repository.claim_next_job(session, "worker-a", lease_seconds=30)
    assert claimed is not None
    assert claimed["run_id"] == run_id

    # A second worker must not claim the same job.
    async with AsyncSessionLocal() as session:
        again = await repository.claim_next_job(session, "worker-b", lease_seconds=30)
    assert again is None
    async with AsyncSessionLocal() as session:
        await repository.delete_run(session, run_id)


async def test_complete_job_marks_success():
    run_id = "run-complete-1"
    job_id = await _create_ready_run(run_id)
    async with AsyncSessionLocal() as session:
        await repository.claim_next_job(session, "worker-a", lease_seconds=30)
        await repository.complete_job(session, job_id)
    async with AsyncSessionLocal() as session:
        job = await repository.get_job_for_run(session, run_id)
    assert job["status"] == "success"
    async with AsyncSessionLocal() as session:
        await repository.delete_run(session, run_id)


async def test_fail_job_retries_then_terminal():
    run_id = "run-fail-1"
    job_id = await _create_ready_run(run_id)
    async with AsyncSessionLocal() as session:
        await repository.claim_next_job(session, "worker-a", lease_seconds=30)
        await repository.fail_job(session, job_id, "boom", retry_delay_seconds=0, max_attempts=3)
    async with AsyncSessionLocal() as session:
        job = await repository.get_job_for_run(session, run_id)
        assert job["status"] == "queued"
        assert job["attempt_count"] == 1

    async with AsyncSessionLocal() as session:
        await repository.claim_next_job(session, "worker-a", lease_seconds=30)
        await repository.fail_job(session, job_id, "boom", retry_delay_seconds=0, max_attempts=3)
    async with AsyncSessionLocal() as session:
        job = await repository.get_job_for_run(session, run_id)
        assert job["status"] == "queued"

    async with AsyncSessionLocal() as session:
        await repository.claim_next_job(session, "worker-a", lease_seconds=30)
        await repository.fail_job(session, job_id, "boom", retry_delay_seconds=0, max_attempts=3)
    async with AsyncSessionLocal() as session:
        job = await repository.get_job_for_run(session, run_id)
        assert job["status"] == "failed"
    async with AsyncSessionLocal() as session:
        await repository.delete_run(session, run_id)


async def test_requeue_expired_lease_recovers_stuck_job():
    run_id = "run-stuck-1"
    job_id = await _create_ready_run(run_id)
    async with AsyncSessionLocal() as session:
        await repository.claim_next_job(session, "worker-dead", lease_seconds=0)  # lease already expired
    async with AsyncSessionLocal() as session:
        recovered = await repository.requeue_expired_leases(session)
        assert recovered >= 1
        job = await repository.get_job_for_run(session, run_id)
        assert job["status"] == "queued"
    async with AsyncSessionLocal() as session:
        await repository.delete_run(session, run_id)


async def test_tenant_isolation_for_run_access():
    async with AsyncSessionLocal() as session:
        await repository.create_run(session, "run-tenant-a", "tenant-a", "a")
    async with AsyncSessionLocal() as session:
        assert await repository.get_run_for_tenant(session, "run-tenant-a", "tenant-a") is not None
        assert await repository.get_run_for_tenant(session, "run-tenant-a", "tenant-b") is None
    async with AsyncSessionLocal() as session:
        await repository.delete_run(session, "run-tenant-a")


def test_reconcile_enqueues_durable_job_and_worker_completes_it(app_client, monkeypatch):
    token_res = app_client.post(
        "/token", data={"username": "demo-auditor", "password": "auditor-password"}
    )
    assert token_res.status_code == 200
    token = token_res.json()["access_token"]

    res = app_client.post(
        "/reconcile",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "purchases": ("p.csv", b"a,b\n1,2\n", "text/csv"),
            "gsts": ("g.csv", b"a,b\n1,2\n", "text/csv"),
        },
    )
    assert res.status_code == 200
    run_id = res.json()["run_id"]

    # Run is queued, not yet processed.
    status_res = app_client.get(f"/runs/{run_id}", headers={"Authorization": f"Bearer {token}"})
    assert status_res.status_code == 200
    assert status_res.json()["status"] in ("queued", "processing")
    assert "job" in status_res.json()

    # Keep this test focused on queue/persistence behavior, independent of
    # engine regressions covered by the reconciliation test suite.
    class FakeResult:
        engine_version = "test-engine"

        def to_dict(self):
            return {"engine_version": self.engine_version, "review_packets": []}

    monkeypatch.setattr("app.processing.run_engine", lambda purchases, gsts: FakeResult())

    # Worker processes it and persists durable success.
    asyncio.run(worker_module.process_one())

    final_res = app_client.get(f"/runs/{run_id}", headers={"Authorization": f"Bearer {token}"})
    assert final_res.status_code == 200
    assert final_res.json()["status"] == "success"


def test_worker_processes_job_created_by_another_session():
    # Verify process_one() claims a job created by another session.
    import uuid

    run_id = f"run-cross-{uuid.uuid4().hex[:8]}"
    asyncio.run(_create_ready_run(run_id))
    asyncio.run(worker_module.process_one())

    async def _check():
        async with AsyncSessionLocal() as session:
            return await repository.get_run(session, run_id)

    run = asyncio.run(_check())
    assert run["status"] == "success"
