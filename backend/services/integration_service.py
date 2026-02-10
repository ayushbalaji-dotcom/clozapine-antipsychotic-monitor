from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.integration import TrackedPatient
from ..models.medication import DrugCategory, MedicationOrder
from ..models.monitoring import AbnormalFlag, MonitoringEvent
from ..models.notifications import NotificationPriority
from ..models.patient import Patient
from ..services.abnormality import ThresholdEvaluator
from ..services.epr_client import EPRClient, get_field, parse_date
from ..services.notification_engine import NotificationEngine
from ..services.scheduling import SchedulingEngine
from ..services.task_generator import TaskGenerator


class IntegrationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.epr_client = EPRClient()
        self.scheduler = SchedulingEngine()
        self.task_gen = TaskGenerator(db)
        self.evaluator = ThresholdEvaluator(db)
        self.notifier = NotificationEngine(db)

    def fetch_and_import(
        self,
        nhs_number: str,
        requested_by: str | None = None,
        source_system: str | None = None,
    ) -> dict[str, Any]:
        patient_payload = self.epr_client.fetch_patient(nhs_number)
        if not patient_payload:
            raise ValueError("Patient not found in EPR")

        pseudonym = get_field(patient_payload, "pseudonym", "pseudonymous_number")
        if not pseudonym:
            raise ValueError("EPR patient missing pseudonym")

        patient = self._upsert_patient(patient_payload, pseudonym)
        patient_hash = self._hash_patient(nhs_number)
        self._track_patient(patient, patient_hash, requested_by, source_system or "EPR")

        patient_ref = get_field(patient_payload, "id", "patient_id") or pseudonym
        meds_payload = self.epr_client.fetch_medications(patient_ref)
        med_summary = self._import_medications(patient, meds_payload)

        obs_payload = self.epr_client.fetch_observations(patient_ref)
        event_summary = self._import_events(patient, obs_payload)

        self.db.commit()
        return {
            "patient_id": str(patient.id),
            "pseudonym": patient.pseudonym,
            "medications": med_summary,
            "events": event_summary,
        }

    def _upsert_patient(self, payload: dict[str, Any], pseudonym: str) -> Patient:
        patient = self.db.query(Patient).filter_by(pseudonym=pseudonym).first()
        age_band = get_field(payload, "age_band", "ageBand")
        sex = get_field(payload, "sex", "gender")
        if patient:
            patient.age_band = age_band
            patient.sex = sex
            return patient
        patient = Patient(
            pseudonym=pseudonym,
            age_band=age_band,
            sex=sex,
        )
        self.db.add(patient)
        self.db.flush()
        return patient

    def _track_patient(
        self,
        patient: Patient,
        patient_hash: str,
        requested_by: str | None,
        source_system: str,
    ) -> None:
        tracked = self.db.query(TrackedPatient).filter_by(patient_id=patient.id).first()
        now = datetime.now(timezone.utc)
        if tracked:
            tracked.last_requested_at = now
            tracked.request_count += 1
            tracked.requested_by = requested_by or tracked.requested_by
            tracked.source_system = source_system
            return
        tracked = TrackedPatient(
            patient_id=patient.id,
            patient_hash=patient_hash,
            source_system=source_system,
            requested_by=requested_by,
            first_requested_at=now,
            last_requested_at=now,
            request_count=1,
        )
        self.db.add(tracked)

    def _import_medications(self, patient: Patient, meds_payload: list[dict[str, Any]]) -> dict[str, Any]:
        inserted = 0
        updated = 0
        skipped = 0
        errors: list[str] = []

        for idx, payload in enumerate(meds_payload):
            try:
                drug_name = get_field(payload, "drug_name", "medication", "medicationText", "name")
                if drug_name is None and isinstance(payload, dict):
                    med_codeable = payload.get("medicationCodeableConcept")
                    if isinstance(med_codeable, dict):
                        drug_name = med_codeable.get("text")
                drug_name = str(drug_name or "").strip()
                if not drug_name:
                    raise ValueError("Missing drug_name")
                start_date = parse_date(get_field(payload, "start_date", "authoredOn", "start"))
                if not start_date:
                    raise ValueError("Missing start_date")
                stop_date = parse_date(get_field(payload, "stop_date", "end"))
                dose = get_field(payload, "dose", "dosage")
                route = get_field(payload, "route")
                frequency = get_field(payload, "frequency")
                is_hdat = bool(get_field(payload, "is_hdat", "is_hdat"))

                drug_lower = drug_name.lower()
                if is_hdat:
                    category = DrugCategory.HDAT
                elif drug_lower in {"chlorpromazine", "clozapine", "olanzapine"}:
                    category = DrugCategory.SPECIAL_GROUP
                else:
                    category = DrugCategory.STANDARD

                med = (
                    self.db.query(MedicationOrder)
                    .filter_by(
                        patient_id=patient.id,
                        drug_name=drug_name,
                        start_date=start_date,
                    )
                    .first()
                )

                if med:
                    med.stop_date = stop_date
                    med.dose = dose
                    med.route = route
                    med.frequency = frequency
                    med.flags = {**(med.flags or {}), "is_hdat": is_hdat}
                    med.drug_category = category
                    updated += 1
                else:
                    med = MedicationOrder(
                        patient_id=patient.id,
                        drug_name=drug_name,
                        drug_category=category,
                        start_date=start_date,
                        stop_date=stop_date,
                        dose=dose,
                        route=route,
                        frequency=frequency,
                        flags={"is_hdat": is_hdat},
                        source_system="EPR_FETCH",
                    )
                    self.db.add(med)
                    self.db.flush()
                    inserted += 1

                tasks = self.scheduler.calculate_schedule(med, patient)
                self.task_gen.create_or_update_tasks(tasks, actor="SYSTEM")
            except Exception as exc:
                errors.append(f"Medication row {idx}: {exc}")
                skipped += 1

        return {"inserted": inserted, "updated": updated, "skipped": skipped, "errors": errors[:10]}

    def _import_events(self, patient: Patient, obs_payload: list[dict[str, Any]]) -> dict[str, Any]:
        inserted = 0
        updated = 0
        skipped = 0
        errors: list[str] = []
        abnormal_summary = {
            AbnormalFlag.NORMAL.value: 0,
            AbnormalFlag.OUTSIDE_WARNING.value: 0,
            AbnormalFlag.OUTSIDE_CRITICAL.value: 0,
            AbnormalFlag.UNKNOWN.value: 0,
        }

        for idx, payload in enumerate(obs_payload):
            try:
                test_type = str(get_field(payload, "test_type", "type", "code")).strip()
                performed_date = parse_date(
                    get_field(payload, "performed_date", "effectiveDateTime", "date")
                )
                if not test_type or not performed_date:
                    raise ValueError("Missing test_type or performed_date")

                value = get_field(payload, "value", "valueString", "valueText")
                unit = get_field(payload, "unit", "unitText")
                interpretation = get_field(payload, "interpretation")
                attachment_url = get_field(payload, "attachment_url", "image_url", "document_url")

                value_quantity = payload.get("valueQuantity") if isinstance(payload, dict) else None
                if isinstance(value_quantity, dict):
                    if value is None:
                        value = value_quantity.get("value")
                    if unit is None:
                        unit = value_quantity.get("unit")

                existing = (
                    self.db.query(MonitoringEvent)
                    .filter_by(
                        patient_id=patient.id,
                        test_type=test_type,
                        performed_date=performed_date,
                    )
                    .first()
                )
                if existing:
                    if value is not None:
                        existing.value = value
                    if unit is not None:
                        existing.unit = unit
                    if interpretation is not None:
                        existing.interpretation = interpretation
                    if attachment_url is not None:
                        existing.attachment_url = attachment_url
                    updated += 1
                    event = existing
                else:
                    event = MonitoringEvent(
                        patient_id=patient.id,
                        test_type=test_type,
                        performed_date=performed_date,
                        value=value,
                        unit=unit,
                        interpretation=interpretation,
                        attachment_url=attachment_url,
                        source_system="EPR_FETCH",
                    )
                    self.db.add(event)
                    self.db.flush()
                    inserted += 1

                evaluation = self.evaluator.evaluate_event(event, patient)
                self.evaluator.apply_evaluation(event, evaluation)
                abnormal_summary[evaluation.flag.value] += 1

                if evaluation.flag == AbnormalFlag.OUTSIDE_CRITICAL:
                    self.notifier.notify_abnormal_event(
                        event,
                        patient,
                        priority=NotificationPriority.CRITICAL,
                        reason=evaluation.reason,
                    )
                elif evaluation.flag == AbnormalFlag.OUTSIDE_WARNING:
                    self.notifier.notify_abnormal_event(
                        event,
                        patient,
                        priority=NotificationPriority.WARNING,
                        reason=evaluation.reason,
                    )

                self.task_gen.auto_complete_tasks_for_event(event, actor="SYSTEM")
            except Exception as exc:
                errors.append(f"Observation row {idx}: {exc}")
                skipped += 1

        return {
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "errors": errors[:10],
            "abnormal_summary": abnormal_summary,
        }

    def _hash_patient(self, nhs_number: str) -> str:
        salt = self.settings.EPR_HASH_SALT or self.settings.SECRET_KEY or ""
        payload = f"{nhs_number}{salt}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
