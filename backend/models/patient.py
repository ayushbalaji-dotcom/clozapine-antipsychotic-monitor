from sqlalchemy import String
from sqlalchemy.orm import mapped_column, relationship, validates
from .base import Base, UUIDMixin, TimestampMixin
from .types import EncryptedString
from ..config import get_settings
from ..services.identifier_detection import find_identifier_matches


class Patient(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "patients"

    nhs_number = mapped_column(EncryptedString, nullable=True)
    mrn = mapped_column(EncryptedString, nullable=True)
    pseudonym = mapped_column(String(32), nullable=False, unique=True)
    age_band = mapped_column(String(16), nullable=True)
    sex = mapped_column(String(8), nullable=True)
    ethnicity = mapped_column(String(64), nullable=True)
    service = mapped_column(String(64), nullable=True)

    medications = relationship("MedicationOrder", back_populates="patient")
    risk_flags = relationship("PatientRiskFlags", back_populates="patient", uselist=False)

    @validates("nhs_number", "mrn")
    def _validate_identifiers(self, key, value):
        if value in (None, ""):
            return value
        settings = get_settings()
        if not settings.ALLOW_IDENTIFIERS:
            raise ValueError("Identifiers are disabled in anonymised mode")
        return value

    @validates("pseudonym", "age_band", "sex", "ethnicity", "service")
    def _validate_no_identifier_like(self, key, value):
        if value in (None, ""):
            return value
        settings = get_settings()
        if settings.ALLOW_IDENTIFIERS:
            return value
        matches = find_identifier_matches(str(value))
        if matches:
            raise ValueError(f"{key} contains identifier-like value ({', '.join(matches)})")
        return value
