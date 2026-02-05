"""Add notifications and abnormal monitoring fields.

Revision ID: 20260205_add_alerts
Revises: 20260204_add_patient_demo
Create Date: 2026-02-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql


revision = "20260205_add_alerts"
down_revision = "20260204_add_patient_demo"
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

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'NOTIFICATION_CREATED'")
        op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'NOTIFICATION_VIEWED'")
        op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'NOTIFICATION_ACKED'")

    if "monitoring_events" in tables:
        cols = {col["name"] for col in inspector.get_columns("monitoring_events")}
        if "unit" not in cols:
            op.add_column("monitoring_events", sa.Column("unit", sa.String(length=32), nullable=True))
        if "interpretation" not in cols:
            op.add_column(
                "monitoring_events", sa.Column("interpretation", sa.String(length=32), nullable=True)
            )
        if "abnormal_flag" not in cols:
            op.add_column(
                "monitoring_events",
                sa.Column(
                    "abnormal_flag",
                    sa.Enum(
                        "NORMAL",
                        "OUTSIDE_WARNING",
                        "OUTSIDE_CRITICAL",
                        "UNKNOWN",
                        name="abnormalflag",
                    ),
                    nullable=False,
                    server_default="UNKNOWN",
                ),
            )
        if "abnormal_reason_code" not in cols:
            op.add_column(
                "monitoring_events",
                sa.Column("abnormal_reason_code", sa.String(length=64), nullable=True),
            )
        if "reviewed_status" not in cols:
            op.add_column(
                "monitoring_events",
                sa.Column(
                    "reviewed_status",
                    sa.Enum("PENDING_REVIEW", "REVIEWED", name="reviewstatus"),
                    nullable=True,
                ),
            )
        if "reviewed_by" not in cols:
            op.add_column(
                "monitoring_events", sa.Column("reviewed_by", sa.String(length=64), nullable=True)
            )
        if "reviewed_at" not in cols:
            op.add_column(
                "monitoring_events",
                sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            )

    if "reference_thresholds" not in tables:
        op.create_table(
            "reference_thresholds",
            sa.Column("monitoring_type", sa.String(length=64), nullable=False),
            sa.Column("unit", sa.String(length=32), nullable=False),
            sa.Column(
                "comparator_type",
                sa.Enum("numeric", "coded", name="comparatortype"),
                nullable=False,
            ),
            sa.Column("sex", sa.String(length=8), nullable=True),
            sa.Column("age_band", sa.String(length=16), nullable=True),
            sa.Column("source_system_scope", sa.String(length=64), nullable=True),
            sa.Column("low_critical", sa.Float(), nullable=True),
            sa.Column("low_warning", sa.Float(), nullable=True),
            sa.Column("high_warning", sa.Float(), nullable=True),
            sa.Column("high_critical", sa.Float(), nullable=True),
            sa.Column("coded_abnormal_values", sa.JSON(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("version", sa.String(length=32), nullable=True),
            sa.Column("updated_by", sa.String(length=64), nullable=True),
            sa.Column("id", _uuid_type(bind), primary_key=True),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=func.now(), nullable=False
            ),
            sa.Column(
                "updated_at", sa.DateTime(timezone=True), server_default=func.now(), nullable=False
            ),
        )

    if (
        "in_app_notifications" not in tables
        and "monitoring_tasks" in tables
        and "monitoring_events" in tables
        and "patients" in tables
    ):
        op.create_table(
            "in_app_notifications",
            sa.Column(
                "recipient_type",
                sa.Enum("USER", "TEAM", name="recipienttype"),
                nullable=False,
            ),
            sa.Column("recipient_id", sa.String(length=64), nullable=False),
            sa.Column(
                "notification_type",
                sa.Enum(
                    "TASK_OVERDUE",
                    "TASK_ESCALATED",
                    "EVENT_WARNING",
                    "EVENT_CRITICAL",
                    name="notificationtype",
                ),
                nullable=False,
            ),
            sa.Column(
                "priority",
                sa.Enum("INFO", "WARNING", "CRITICAL", name="notificationpriority"),
                nullable=False,
            ),
            sa.Column(
                "status",
                sa.Enum("UNREAD", "READ", "ACKED", name="inappnotificationstatus"),
                nullable=False,
                server_default="UNREAD",
            ),
            sa.Column("title", sa.String(length=128), nullable=False),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("patient_id", _uuid_type(bind), nullable=True),
            sa.Column("task_id", _uuid_type(bind), nullable=True),
            sa.Column("event_id", _uuid_type(bind), nullable=True),
            sa.Column("dedupe_key", sa.String(length=128), nullable=False),
            sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("acked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("id", _uuid_type(bind), primary_key=True),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=func.now(), nullable=False
            ),
            sa.Column(
                "updated_at", sa.DateTime(timezone=True), server_default=func.now(), nullable=False
            ),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
            sa.ForeignKeyConstraint(["task_id"], ["monitoring_tasks.id"]),
            sa.ForeignKeyConstraint(["event_id"], ["monitoring_events.id"]),
            sa.UniqueConstraint("dedupe_key", name="uq_in_app_notifications_dedupe_key"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "in_app_notifications" in tables:
        op.drop_table("in_app_notifications")

    if "reference_thresholds" in tables:
        op.drop_table("reference_thresholds")

    if "monitoring_events" in tables:
        cols = {col["name"] for col in inspector.get_columns("monitoring_events")}
        if "reviewed_at" in cols:
            op.drop_column("monitoring_events", "reviewed_at")
        if "reviewed_by" in cols:
            op.drop_column("monitoring_events", "reviewed_by")
        if "reviewed_status" in cols:
            op.drop_column("monitoring_events", "reviewed_status")
        if "abnormal_reason_code" in cols:
            op.drop_column("monitoring_events", "abnormal_reason_code")
        if "abnormal_flag" in cols:
            op.drop_column("monitoring_events", "abnormal_flag")
        if "interpretation" in cols:
            op.drop_column("monitoring_events", "interpretation")
        if "unit" in cols:
            op.drop_column("monitoring_events", "unit")
