from __future__ import annotations

import csv
import io
import zipfile
from typing import Iterable

from sqlalchemy.orm import Session

from ..models.integration import TrackedPatient
from ..models.medication import MedicationOrder
from ..models.monitoring import MonitoringEvent
from ..models.patient import Patient


class ExportService:
    def __init__(self, db: Session):
        self.db = db

    def build_export_zip(self, tracked_only: bool = True) -> bytes:
        patient_ids = self._tracked_patient_ids() if tracked_only else None

        patients = self._fetch_patients(patient_ids)
        medications = self._fetch_medications(patient_ids)
        events = self._fetch_events(patient_ids)

        patients_csv = _to_csv(
            ["pseudonymous_number", "age_band", "sex", "ethnicity", "service"],
            [
                {
                    "pseudonymous_number": p.pseudonym,
                    "age_band": p.age_band,
                    "sex": p.sex,
                    "ethnicity": p.ethnicity,
                    "service": p.service,
                }
                for p in patients
            ],
        )

        medications_csv = _to_csv(
            [
                "pseudonymous_number",
                "drug_name",
                "start_date",
                "stop_date",
                "dose",
                "route",
                "frequency",
                "is_hdat",
            ],
            [
                {
                    "pseudonymous_number": med.patient.pseudonym,
                    "drug_name": med.drug_name,
                    "start_date": med.start_date.isoformat(),
                    "stop_date": med.stop_date.isoformat() if med.stop_date else "",
                    "dose": med.dose,
                    "route": med.route,
                    "frequency": med.frequency,
                    "is_hdat": bool(med.flags.get("is_hdat")) if med.flags else False,
                }
                for med in medications
            ],
        )

        events_csv = _to_csv(
            [
                "pseudonymous_number",
                "test_type",
                "performed_date",
                "value",
                "unit",
                "interpretation",
                "attachment_url",
                "abnormal_flag",
                "reviewed_status",
                "source_system",
            ],
            [
                {
                    "pseudonymous_number": event.patient.pseudonym,
                    "test_type": event.test_type,
                    "performed_date": event.performed_date.isoformat(),
                    "value": event.value,
                    "unit": event.unit,
                    "interpretation": event.interpretation,
                    "attachment_url": event.attachment_url,
                    "abnormal_flag": event.abnormal_flag.value if event.abnormal_flag else "",
                    "reviewed_status": event.reviewed_status.value if event.reviewed_status else "",
                    "source_system": event.source_system,
                }
                for event in events
            ],
        )

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("patients.csv", patients_csv)
            zf.writestr("medications.csv", medications_csv)
            zf.writestr("events.csv", events_csv)
        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    def _tracked_patient_ids(self) -> list[str]:
        rows = self.db.query(TrackedPatient.patient_id).all()
        return [row[0] for row in rows]

    def _fetch_patients(self, patient_ids: Iterable[str] | None) -> list[Patient]:
        query = self.db.query(Patient)
        if patient_ids is not None:
            patient_ids = list(patient_ids)
            if not patient_ids:
                return []
            query = query.filter(Patient.id.in_(patient_ids))
        return query.order_by(Patient.pseudonym.asc()).all()

    def _fetch_medications(self, patient_ids: Iterable[str] | None) -> list[MedicationOrder]:
        query = self.db.query(MedicationOrder).join(Patient)
        if patient_ids is not None:
            patient_ids = list(patient_ids)
            if not patient_ids:
                return []
            query = query.filter(MedicationOrder.patient_id.in_(patient_ids))
        return query.order_by(MedicationOrder.start_date.asc()).all()

    def _fetch_events(self, patient_ids: Iterable[str] | None) -> list[MonitoringEvent]:
        query = self.db.query(MonitoringEvent).join(Patient)
        if patient_ids is not None:
            patient_ids = list(patient_ids)
            if not patient_ids:
                return []
            query = query.filter(MonitoringEvent.patient_id.in_(patient_ids))
        return query.order_by(MonitoringEvent.performed_date.asc()).all()


def _to_csv(columns: list[str], rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()
