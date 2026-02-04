"""Add patient demographic fields.

Revision ID: 20260204_add_patient_demographics
Revises: None
Create Date: 2026-02-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260204_add_patient_demographics"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("age_band", sa.String(length=16), nullable=True))
    op.add_column("patients", sa.Column("sex", sa.String(length=8), nullable=True))
    op.add_column("patients", sa.Column("ethnicity", sa.String(length=64), nullable=True))
    op.add_column("patients", sa.Column("service", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("patients", "service")
    op.drop_column("patients", "ethnicity")
    op.drop_column("patients", "sex")
    op.drop_column("patients", "age_band")
