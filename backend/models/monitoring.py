import enum
from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import mapped_column, relationship
from .base import Base, UUIDMixin, TimestampMixin


class TaskStatus(str, enum.Enum):
    DUE = "DUE"
    OVERDUE = "OVERDUE"
    DONE = "DONE"
    WAIVED = "WAIVED"
    ONGOING = "ONGOING"


class AbnormalFlag(str, enum.Enum):
    NORMAL = "NORMAL"
    OUTSIDE_WARNING = "OUTSIDE_WARNING"
    OUTSIDE_CRITICAL = "OUTSIDE_CRITICAL"
    UNKNOWN = "UNKNOWN"


class ReviewStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    REVIEWED = "REVIEWED"


class MonitoringEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "monitoring_events"

    patient_id = mapped_column(ForeignKey("patients.id"), nullable=False)
    medication_order_id = mapped_column(ForeignKey("medication_orders.id"), nullable=True)
    test_type = mapped_column(String(64), nullable=False)
    performed_date = mapped_column(Date, nullable=False)
    value = mapped_column(String(128), nullable=True)
    unit = mapped_column(String(32), nullable=True)
    interpretation = mapped_column(String(32), nullable=True)
    attachment_url = mapped_column(String(512), nullable=True)
    source_system = mapped_column(String(64), nullable=False)
    source_id = mapped_column(String(64), nullable=True)
    recorded_by = mapped_column(String(64), nullable=True)
    abnormal_flag = mapped_column(
        Enum(AbnormalFlag, name="abnormalflag"),
        default=AbnormalFlag.UNKNOWN,
        nullable=False,
    )
    abnormal_reason_code = mapped_column(String(64), nullable=True)
    reviewed_status = mapped_column(Enum(ReviewStatus, name="reviewstatus"), nullable=True)
    reviewed_by = mapped_column(String(64), nullable=True)
    reviewed_at = mapped_column(DateTime(timezone=True), nullable=True)

    patient = relationship("Patient")
    medication = relationship("MedicationOrder")


class MonitoringTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "monitoring_tasks"

    patient_id = mapped_column(ForeignKey("patients.id"), nullable=False)
    medication_order_id = mapped_column(ForeignKey("medication_orders.id"), nullable=False)
    test_type = mapped_column(String(64), nullable=False)
    due_date = mapped_column(Date, nullable=False)
    status = mapped_column(Enum(TaskStatus), default=TaskStatus.DUE, nullable=False)
    assigned_to = mapped_column(String(64), nullable=True)
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)
    waived_reason = mapped_column(Text, nullable=True)
    waived_until = mapped_column(Date, nullable=True)

    patient = relationship("Patient")
    medication = relationship("MedicationOrder", back_populates="tasks")


class PatientRiskFlags(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "patient_risk_flags"

    patient_id = mapped_column(ForeignKey("patients.id"), nullable=False, unique=True)
    ecg_indicated = mapped_column(Boolean, default=False, nullable=False)
    cv_risk_present = mapped_column(Boolean, default=False, nullable=False)
    inpatient_admission = mapped_column(Boolean, default=False, nullable=False)
    family_history_cvd = mapped_column(Boolean, default=False, nullable=False)
    attested_by = mapped_column(String(64), nullable=True)
    attested_at = mapped_column(DateTime(timezone=True), nullable=True)

    patient = relationship("Patient", back_populates="risk_flags")
