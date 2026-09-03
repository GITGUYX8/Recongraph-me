"""Canonical ORM models for ReconGraph.

These are the single source of truth for persistence. Runs, jobs, packet
actions, feedback, and uploads all live in one database (PostgreSQL in
production, SQLite locally/tests). Schema changes are managed with Alembic.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    engine_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    config_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("run_id", name="uq_jobs_run_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("runs.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False, default="reconcile")
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class PacketAction(Base):
    __tablename__ = "packet_actions"
    __table_args__ = (UniqueConstraint("run_id", "packet_id", name="uq_packet_actions_run_packet"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("runs.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    packet_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ims_action: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    itc_availability: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    itc_claim_period: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reason_itc_unavailability: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Feedback(Base):
    __tablename__ = "feedback_v2"

    review_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    packet_id: Mapped[str] = mapped_column(String(128), index=True, nullable=True)
    purchase_record_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gst_record_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    deterministic_decision: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    deterministic_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    deterministic_coverage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ml_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    calibrated_ml_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    graph_features: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_features: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_human_decision: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    reviewer_action: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    engine_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    config_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    explanation_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    rag_context_identifiers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    legacy_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("runs.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # purchases | gsts
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)