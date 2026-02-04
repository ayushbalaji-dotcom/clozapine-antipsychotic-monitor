"""Add patient demographic fields.

Revision ID: 20260204_add_patient_demo
Revises: None
Create Date: 2026-02-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql


revision = "20260204_add_patient_demo"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "patients" not in tables:
        if bind.dialect.name == "postgresql":
            id_type = postgresql.UUID(as_uuid=True)
        else:
            id_type = sa.String(36)

        op.create_table(
            "patients",
            sa.Column("nhs_number", sa.String(length=512), nullable=True),
            sa.Column("mrn", sa.String(length=512), nullable=True),
            sa.Column("pseudonym", sa.String(length=32), nullable=False),
            sa.Column("age_band", sa.String(length=16), nullable=True),
            sa.Column("sex", sa.String(length=8), nullable=True),
            sa.Column("ethnicity", sa.String(length=64), nullable=True),
            sa.Column("service", sa.String(length=64), nullable=True),
            sa.Column("id", id_type, primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
            sa.UniqueConstraint("pseudonym", name="uq_patients_pseudonym"),
        )
        return

    # Table exists: add missing columns if needed
    cols = {col["name"] for col in inspector.get_columns("patients")}
    if "age_band" not in cols:
        op.add_column("patients", sa.Column("age_band", sa.String(length=16), nullable=True))
    if "sex" not in cols:
        op.add_column("patients", sa.Column("sex", sa.String(length=8), nullable=True))
    if "ethnicity" not in cols:
        op.add_column("patients", sa.Column("ethnicity", sa.String(length=64), nullable=True))
    if "service" not in cols:
        op.add_column("patients", sa.Column("service", sa.String(length=64), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "patients" not in inspector.get_table_names():
        return
    cols = {col["name"] for col in inspector.get_columns("patients")}
    if "service" in cols:
        op.drop_column("patients", "service")
    if "ethnicity" in cols:
        op.drop_column("patients", "ethnicity")
    if "sex" in cols:
        op.drop_column("patients", "sex")
    if "age_band" in cols:
        op.drop_column("patients", "age_band")
