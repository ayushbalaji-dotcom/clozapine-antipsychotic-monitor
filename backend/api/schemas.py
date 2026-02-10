from pydantic import BaseModel, ConfigDict, model_validator
from datetime import date, datetime
from typing import Optional
from ..config import get_settings
from ..services.identifier_detection import scan_payload_for_identifiers


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _reject_identifiers(self):
        settings = get_settings()
        if settings.ALLOW_IDENTIFIERS:
            return self
        risks = scan_payload_for_identifiers(self.model_dump())
        if risks:
            raise ValueError("Identifier-like values detected in payload")
        return self


class PatientIdentifier(StrictModel):
    patient_id: Optional[str] = None
    nhs_number: Optional[str] = None
    mrn: Optional[str] = None
    pseudonym: Optional[str] = None

    @model_validator(mode="after")
    def _reject_identifier_fields(self):
        settings = get_settings()
        if settings.ALLOW_IDENTIFIERS:
            return self
        if self.nhs_number or self.mrn:
            raise ValueError("Identifiers are not allowed in anonymised mode")
        return self


class MedicationPayload(StrictModel):
    drug_name: str
    start_date: date
    stop_date: Optional[date] = None
    dose: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None


class MonitoringEventPayload(StrictModel):
    test_type: str
    performed_date: date
    value: Optional[str] = None
    unit: Optional[str] = None
    interpretation: Optional[str] = None
    attachment_url: Optional[str] = None


class WebhookMedicationRequest(StrictModel):
    patient: PatientIdentifier
    medication: MedicationPayload
    source_system: str
    timestamp: datetime
    source_id: Optional[str] = None


class WebhookMonitoringEventRequest(StrictModel):
    patient: PatientIdentifier
    event: MonitoringEventPayload
    source_system: str
    timestamp: datetime
    source_id: Optional[str] = None


class WaiveTaskRequest(StrictModel):
    reason: str
    waived_until: Optional[date] = None


class AcknowledgeTaskRequest(StrictModel):
    assigned_to: Optional[str] = None


class CompleteTaskRequest(StrictModel):
    monitoring_event_id: str


class ConfigUpdateRequest(StrictModel):
    values: dict


class RuleSetUploadRequest(StrictModel):
    version: str
    effective_from: date
    rules_json: dict


class ThresholdPayload(StrictModel):
    monitoring_type: str
    unit: str
    comparator_type: str  # numeric | coded
    sex: Optional[str] = None
    age_band: Optional[str] = None
    source_system_scope: Optional[str] = None
    low_critical: Optional[float] = None
    low_warning: Optional[float] = None
    high_warning: Optional[float] = None
    high_critical: Optional[float] = None
    coded_abnormal_values: Optional[list[str]] = None
    enabled: Optional[bool] = True
    version: Optional[str] = None


class IntegrationFetchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # NHS number is accepted only for user-initiated EPR fetch and never stored.
    nhs_number: str
    requested_by: Optional[str] = None
    source_system: Optional[str] = None
