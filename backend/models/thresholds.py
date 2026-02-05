import enum
from sqlalchemy import Boolean, Enum, Float, JSON, String
from sqlalchemy.orm import mapped_column
from .base import Base, UUIDMixin, TimestampMixin


class ComparatorType(str, enum.Enum):
    NUMERIC = "numeric"
    CODED = "coded"


class ReferenceThreshold(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reference_thresholds"

    monitoring_type = mapped_column(String(64), nullable=False)
    unit = mapped_column(String(32), nullable=False)
    comparator_type = mapped_column(Enum(ComparatorType, name="comparatortype"), nullable=False)

    sex = mapped_column(String(8), nullable=True)
    age_band = mapped_column(String(16), nullable=True)
    source_system_scope = mapped_column(String(64), nullable=True)

    low_critical = mapped_column(Float, nullable=True)
    low_warning = mapped_column(Float, nullable=True)
    high_warning = mapped_column(Float, nullable=True)
    high_critical = mapped_column(Float, nullable=True)

    coded_abnormal_values = mapped_column(JSON, nullable=True)

    enabled = mapped_column(Boolean, default=True, nullable=False)
    version = mapped_column(String(32), nullable=True)
    updated_by = mapped_column(String(64), nullable=True)
