"""Add integration tracking and attachment URLs.

Revision ID: 20260210_add_integration_tracking
Revises: 20260205_add_alerts
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql


revision = "20260210_add_integration_tracking"
down_revision = "20260205_add_alerts"
branch_labels = None
depends_on = None


def _uuid_type(bind):
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.String(36)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "monitoring_events" in tables:
        cols = {col["name"] for col in inspector.get_columns("monitoring_events")}
        if "attachment_url" not in cols:
            op.add_column(
                "monitoring_events", sa.Column("attachment_url", sa.String(length=512), nullable=True)
            )

    if "tracked_patients" not in tables and "patients" in tables:
        op.create_table(
            "tracked_patients",
            sa.Column("patient_id", _uuid_type(bind), nullable=False),
            sa.Column("patient_hash", sa.String(length=128), nullable=True),
            sa.Column("source_system", sa.String(length=64), nullable=True),
            sa.Column("requested_by", sa.String(length=64), nullable=True),
            sa.Column("request_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "first_requested_at",
                sa.DateTime(timezone=True),
                server_default=func.now(),
                nullable=False,
            ),
            sa.Column(
                "last_requested_at",
                sa.DateTime(timezone=True),
                server_default=func.now(),
                nullable=False,
            ),
            sa.Column("id", _uuid_type(bind), primary_key=True),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
            sa.UniqueConstraint("patient_id", name="uq_tracked_patients_patient_id"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "tracked_patients" in tables:
        op.drop_table("tracked_patients")

    if "monitoring_events" in tables:
        cols = {col["name"] for col in inspector.get_columns("monitoring_events")}
        if "attachment_url" in cols:
            op.drop_column("monitoring_events", "attachment_url")
