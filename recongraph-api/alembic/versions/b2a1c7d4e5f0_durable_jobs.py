"""Durable jobs and canonical run/action/upload tables

Revision ID: b2a1c7d4e5f0
Revises: 004a2ed8d59f
Create Date: 2026-09-03

Adds the canonical persistence tables backing the durable reconciliation
pipeline: runs, jobs, packet_actions, and uploads.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2a1c7d4e5f0'
down_revision: Union[str, Sequence[str], None] = '004a2ed8d59f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'runs',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('created_by', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('engine_version', sa.String(length=64), nullable=True),
        sa.Column('config_hash', sa.String(length=64), nullable=True),
        sa.Column('result_json', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_runs_tenant_id'), 'runs', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_runs_status'), 'runs', ['status'], unique=False)

    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=64), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('job_type', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('attempt_count', sa.Integer(), nullable=False),
        sa.Column('available_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('claimed_by', sa.String(length=128), nullable=True),
        sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', name='uq_jobs_run_id'),
    )
    op.create_index(op.f('ix_jobs_tenant_id'), 'jobs', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_jobs_status'), 'jobs', ['status'], unique=False)

    op.create_table(
        'packet_actions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=64), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('packet_id', sa.String(length=128), nullable=False),
        sa.Column('ims_action', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('itc_availability', sa.String(length=32), nullable=True),
        sa.Column('itc_claim_period', sa.String(length=64), nullable=True),
        sa.Column('reason_itc_unavailability', sa.Text(), nullable=True),
        sa.Column('reviewer_id', sa.String(length=128), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'packet_id', name='uq_packet_actions_run_packet'),
    )
    op.create_index(op.f('ix_packet_actions_run_id'), 'packet_actions', ['run_id'], unique=False)
    op.create_index(op.f('ix_packet_actions_tenant_id'), 'packet_actions', ['tenant_id'], unique=False)

    op.create_table(
        'uploads',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=64), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('storage_path', sa.String(length=512), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_uploads_run_id'), 'uploads', ['run_id'], unique=False)
    op.create_index(op.f('ix_uploads_tenant_id'), 'uploads', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_uploads_tenant_id'), table_name='uploads')
    op.drop_index(op.f('ix_uploads_run_id'), table_name='uploads')
    op.drop_table('uploads')
    op.drop_index(op.f('ix_packet_actions_tenant_id'), table_name='packet_actions')
    op.drop_index(op.f('ix_packet_actions_run_id'), table_name='packet_actions')
    op.drop_table('packet_actions')
    op.drop_index(op.f('ix_jobs_status'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_tenant_id'), table_name='jobs')
    op.drop_table('jobs')
    op.drop_index(op.f('ix_runs_status'), table_name='runs')
    op.drop_index(op.f('ix_runs_tenant_id'), table_name='runs')
    op.drop_table('runs')