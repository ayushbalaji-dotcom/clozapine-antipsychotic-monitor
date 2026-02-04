import enum
from sqlalchemy import Date, String, Enum, JSON, ForeignKey
from sqlalchemy.orm import mapped_column, relationship
from .base import Base, UUIDMixin, TimestampMixin


class DrugCategory(str, enum.Enum):
    STANDARD = "STANDARD"
    SPECIAL_GROUP = "SPECIAL_GROUP"
    HDAT = "HDAT"


class MedicationOrder(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "medication_orders"

    patient_id = mapped_column(ForeignKey("patients.id"), nullable=False)
    drug_name = mapped_column(String(128), nullable=False)
    drug_category = mapped_column(Enum(DrugCategory), nullable=False)
    start_date = mapped_column(Date, nullable=False)
    stop_date = mapped_column(Date, nullable=True)
    dose = mapped_column(String(64), nullable=True)
    route = mapped_column(String(32), nullable=True)
    frequency = mapped_column(String(64), nullable=True)
    flags = mapped_column(JSON, nullable=False, default=dict)
    source_system = mapped_column(String(64), nullable=True)
    source_id = mapped_column(String(64), nullable=True)

    patient = relationship("Patient", back_populates="medications")
    tasks = relationship("MonitoringTask", back_populates="medication")
