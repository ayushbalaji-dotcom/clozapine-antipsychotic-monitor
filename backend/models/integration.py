from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import mapped_column
from .base import Base, UUIDMixin


class TrackedPatient(Base, UUIDMixin):
    __tablename__ = "tracked_patients"

    patient_id = mapped_column(ForeignKey("patients.id"), nullable=False, unique=True)
    patient_hash = mapped_column(String(128), nullable=True)
    source_system = mapped_column(String(64), nullable=True)
    requested_by = mapped_column(String(64), nullable=True)
    request_count = mapped_column(Integer, nullable=False, default=1)
    first_requested_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_requested_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
