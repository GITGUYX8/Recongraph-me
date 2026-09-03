"""Persistence repository for runs, jobs, packet actions, feedback, and uploads.

Every data access used by the API and worker goes through this layer so tenant
scoping and transactional behavior are centralized. Runs are read/written here
only, replacing the old in-memory ``_runs_store`` and the direct ``sqlite3``
feedback code.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from . import models


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---- runs ------------------------------------------------------------

async def create_run(
    session: AsyncSession,
    run_id: str,
    tenant_id: str,
    created_by: str,
    status: str = "queued",
) -> None:
    session.add(models.Run(id=run_id, tenant_id=tenant_id, created_by=created_by, status=status))
    await session.commit()


async def update_run_status(
    session: AsyncSession,
    run_id: str,
    status: str,
    error_message: Optional[str] = None,
) -> None:
    values: dict[str, Any] = {"status": status}
    if status == "processing" and (await get_run(session, run_id)) is not None:
        values["started_at"] = _utcnow()
    if status in ("success", "failed"):
        values["completed_at"] = _utcnow()
    if error_message is not None:
        values["error_message"] = error_message
    await session.execute(update(models.Run).where(models.Run.id == run_id).values(**values))
    await session.commit()


async def save_run_result(
    session: AsyncSession,
    run_id: str,
    result_json: str,
    engine_version: Optional[str] = None,
    config_hash: Optional[str] = None,
) -> None:
    await session.execute(
        update(models.Run)
        .where(models.Run.id == run_id)
        .values(
            status="success",
            result_json=result_json,
            engine_version=engine_version,
            config_hash=config_hash,
            completed_at=_utcnow(),
            error_message=None,
        )
    )
    await session.commit()


async def get_run(session: AsyncSession, run_id: str) -> Optional[dict[str, Any]]:
    row = await session.get(models.Run, run_id)
    if row is None:
        return None
    return {
        "run_id": row.id,
        "tenant_id": row.tenant_id,
        "created_by": row.created_by,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "engine_version": row.engine_version,
        "config_hash": row.config_hash,
        "result": json.loads(row.result_json) if row.result_json else None,
        "error_message": row.error_message,
    }


async def get_run_for_tenant(session: AsyncSession, run_id: str, tenant_id: str) -> Optional[dict[str, Any]]:
    row = (
        await session.execute(
            select(models.Run).where(models.Run.id == run_id, models.Run.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return await get_run(session, run_id)


async def list_runs(session: AsyncSession, tenant_id: str) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(models.Run)
            .where(models.Run.tenant_id == tenant_id)
            .order_by(models.Run.created_at.desc())
        )
    ).scalars().all()
    return [
        {
            "run_id": r.id,
            "tenant_id": r.tenant_id,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "engine_version": r.engine_version,
            "config_hash": r.config_hash,
        }
        for r in rows
    ]


# ---- jobs -------------------------------------------------------------

async def create_job(
    session: AsyncSession,
    run_id: str,
    tenant_id: str,
    job_type: str = "reconcile",
    available_at: Optional[datetime] = None,
) -> None:
    session.add(
        models.Job(
            run_id=run_id,
            tenant_id=tenant_id,
            job_type=job_type,
            status="queued",
            available_at=available_at or _utcnow(),
        )
    )
    await session.commit()


async def claim_next_job(
    session: AsyncSession,
    worker_id: str,
    lease_seconds: int = 1800,
    max_attempts: int = 3,
) -> Optional[dict[str, Any]]:
    """Atomically claim the oldest queued job.

    Uses an UPDATE ... RETURNING so only one worker can claim a given job even
    without ``FOR UPDATE SKIP LOCKED`` (which SQLite does not support). Jobs past
    ``max_attempts`` are skipped so they surface as terminal failures.
    """
    now = _utcnow()
    subq = (
        select(models.Job.id)
        .where(
            models.Job.status == "queued",
            models.Job.available_at <= now,
            models.Job.attempt_count < max_attempts,
        )
        .order_by(models.Job.created_at.asc())
        .limit(1)
    )
    stmt = (
        update(models.Job)
        .where(models.Job.id.in_(subq))
        .values(
            status="processing",
            claimed_at=now,
            claimed_by=worker_id,
            lease_expires_at=now + timedelta(seconds=lease_seconds),
            attempt_count=models.Job.attempt_count + 1,
            updated_at=now,
        )
        .returning(models.Job.id, models.Job.run_id, models.Job.tenant_id)
    )
    result = await session.execute(stmt)
    await session.commit()
    row = result.first()
    if row is None:
        return None
    return {"id": row[0], "run_id": row[1], "tenant_id": row[2]}


async def complete_job(session: AsyncSession, job_id: int) -> None:
    await session.execute(
        update(models.Job).where(models.Job.id == job_id).values(status="success", updated_at=_utcnow())
    )
    await session.commit()


async def fail_job(
    session: AsyncSession,
    job_id: int,
    error: str,
    retry_delay_seconds: int = 60,
    max_attempts: int = 3,
) -> str:
    job = await session.get(models.Job, job_id)
    if job is None:
        return "missing"
    job.last_error = error
    job.updated_at = _utcnow()
    if job.attempt_count >= max_attempts:
        job.status = "failed"
        await session.execute(
            update(models.Run)
            .where(models.Run.id == job.run_id)
            .values(status="failed", completed_at=_utcnow(), error_message=error)
        )
    else:
        job.status = "queued"
        job.available_at = _utcnow() + timedelta(seconds=retry_delay_seconds)
        job.claimed_by = None
        job.lease_expires_at = None
        await session.execute(
            update(models.Run)
            .where(models.Run.id == job.run_id)
            .values(status="queued", error_message=error)
        )
    await session.commit()
    return job.status


async def requeue_expired_leases(session: AsyncSession) -> int:
    """Recover jobs abandoned by a dead worker (lease expired)."""
    now = _utcnow()
    stmt = (
        update(models.Job)
        .where(
            models.Job.status == "processing",
            models.Job.lease_expires_at.is_not(None),
            models.Job.lease_expires_at < now,
        )
        .values(status="queued", claimed_by=None, lease_expires_at=None, updated_at=now)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0


async def get_job_for_run(session: AsyncSession, run_id: str) -> Optional[dict[str, Any]]:
    row = (
        await session.execute(select(models.Job).where(models.Job.run_id == run_id))
    ).scalar_one_or_none()
    if row is None:
        return None
    return {
        "id": row.id,
        "run_id": row.run_id,
        "status": row.status,
        "attempt_count": row.attempt_count,
        "last_error": row.last_error,
    }


# ---- packet actions ---------------------------------------------------

async def apply_packet_action(
    session: AsyncSession,
    run_id: str,
    tenant_id: str,
    packet_id: str,
    action: dict[str, Any],
) -> None:
    existing = (
        await session.execute(
            select(models.PacketAction).where(
                models.PacketAction.run_id == run_id,
                models.PacketAction.packet_id == packet_id,
            )
        )
    ).scalar_one_or_none()

    fields = {
        "tenant_id": tenant_id,
        "ims_action": action["action"],
        "status": action["status"],
        "itc_availability": action.get("itc_availability"),
        "itc_claim_period": action.get("itc_claim_period"),
        "reason_itc_unavailability": action.get("reason_itc_unavailability"),
        "reviewer_id": action.get("reviewer_id"),
        "comments": action.get("comments"),
        "updated_at": _utcnow(),
    }
    if existing is None:
        session.add(models.PacketAction(run_id=run_id, packet_id=packet_id, **fields))
    else:
        for key, value in fields.items():
            setattr(existing, key, value)
    await session.commit()


async def get_packet_action(
    session: AsyncSession, run_id: str, packet_id: str
) -> Optional[dict[str, Any]]:
    row = (
        await session.execute(
            select(models.PacketAction).where(
                models.PacketAction.run_id == run_id,
                models.PacketAction.packet_id == packet_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


async def get_run_actions(session: AsyncSession, run_id: str) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(models.PacketAction)
            .where(models.PacketAction.run_id == run_id)
            .order_by(models.PacketAction.updated_at.desc())
        )
    ).scalars().all()
    return [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in rows]


# ---- feedback ---------------------------------------------------------

async def save_feedback(session: AsyncSession, feedback: dict[str, Any]) -> None:
    session.add(models.Feedback(**feedback))
    await session.commit()


# ---- uploads ----------------------------------------------------------

async def create_upload(
    session: AsyncSession,
    run_id: str,
    tenant_id: str,
    kind: str,
    filename: str,
    size_bytes: int,
    storage_path: str,
) -> None:
    session.add(
        models.Upload(
            run_id=run_id,
            tenant_id=tenant_id,
            kind=kind,
            filename=filename,
            size_bytes=size_bytes,
            storage_path=storage_path,
        )
    )
    await session.commit()


async def get_upload(session: AsyncSession, run_id: str, tenant_id: str, kind: str) -> Optional[str]:
    row = (
        await session.execute(
            select(models.Upload)
            .where(
                models.Upload.run_id == run_id,
                models.Upload.tenant_id == tenant_id,
                models.Upload.kind == kind,
            )
            .order_by(models.Upload.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return row.storage_path if row else None


async def delete_run(session: AsyncSession, run_id: str) -> None:
    await session.execute(delete(models.Job).where(models.Job.run_id == run_id))
    await session.execute(delete(models.PacketAction).where(models.PacketAction.run_id == run_id))
    await session.execute(delete(models.Upload).where(models.Upload.run_id == run_id))
    run = await session.get(models.Run, run_id)
    if run is not None:
        await session.delete(run)
    await session.commit()
