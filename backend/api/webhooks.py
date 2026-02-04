from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.medication import MedicationOrder, DrugCategory
from ..models.monitoring import MonitoringEvent
from ..models.patient import Patient
from ..services.webhook_security import WebhookSecurity
from ..services.scheduling import SchedulingEngine
from ..services.task_generator import TaskGenerator
from ..services.audit_logger import create_audit_event
from ..config import get_settings
from ..models.audit import AuditAction
from .schemas import WebhookMedicationRequest, WebhookMonitoringEventRequest

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
security = WebhookSecurity()


def _get_or_create_patient(db: Session, payload) -> Patient:
    settings = get_settings()
    if payload.patient_id:
        patient = db.query(Patient).filter_by(id=payload.patient_id).first()
        if patient:
            return patient
    if payload.pseudonym:
        patient = db.query(Patient).filter_by(pseudonym=payload.pseudonym).first()
        if patient:
            return patient

    patient = Patient(
        id=uuid4(),
        pseudonym=payload.pseudonym or f"PT-{uuid4().hex[:6].upper()}",
        nhs_number=payload.nhs_number if settings.ALLOW_IDENTIFIERS else None,
        mrn=payload.mrn if settings.ALLOW_IDENTIFIERS else None,
    )
    db.add(patient)
    db.commit()
    return patient


def _infer_flags(drug_name: str) -> dict:
    drug_lower = drug_name.lower()
    return {
        "is_clozapine": drug_lower == "clozapine",
        "is_olanzapine": drug_lower == "olanzapine",
        "is_chlorpromazine": drug_lower == "chlorpromazine",
        "is_hdat": False,
    }


@router.post("/medication")
async def ingest_medication(request: Request, db: Session = Depends(get_db)):
    body = await security.validate_request(request)
    payload = WebhookMedicationRequest.model_validate_json(body)

    patient = _get_or_create_patient(db, payload.patient)

    if payload.source_id:
        existing = (
            db.query(MedicationOrder)
            .filter_by(source_system=payload.source_system, source_id=payload.source_id)
            .first()
        )
        if existing:
            return {"status": "duplicate", "medication_id": str(existing.id)}

    category = DrugCategory.STANDARD
    drug_lower = payload.medication.drug_name.lower()
    if drug_lower in {"chlorpromazine", "clozapine", "olanzapine"}:
        category = DrugCategory.SPECIAL_GROUP

    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name=payload.medication.drug_name,
        drug_category=category,
        start_date=payload.medication.start_date,
        stop_date=payload.medication.stop_date,
        dose=payload.medication.dose,
        route=payload.medication.route,
        frequency=payload.medication.frequency,
        flags=_infer_flags(payload.medication.drug_name),
        source_system=payload.source_system,
        source_id=payload.source_id,
    )
    db.add(med)
    db.commit()

    engine = SchedulingEngine()
    tasks = engine.calculate_schedule(med, patient)
    TaskGenerator(db).create_or_update_tasks(tasks, actor="SYSTEM")

    create_audit_event(
        db,
        actor="SYSTEM",
        action=AuditAction.UPDATE,
        entity_type="MedicationOrder",
        entity_id=str(med.id),
        details={"source_system": payload.source_system},
        request=request,
    )

    return {"status": "accepted", "medication_id": str(med.id)}


@router.post("/monitoring-event")
async def ingest_monitoring_event(request: Request, db: Session = Depends(get_db)):
    body = await security.validate_request(request)
    payload = WebhookMonitoringEventRequest.model_validate_json(body)

    patient = _get_or_create_patient(db, payload.patient)

    if payload.source_id:
        existing = (
            db.query(MonitoringEvent)
            .filter_by(source_system=payload.source_system, source_id=payload.source_id)
            .first()
        )
        if existing:
            return {"status": "duplicate", "event_id": str(existing.id)}

    event = MonitoringEvent(
        id=uuid4(),
        patient_id=patient.id,
        medication_order_id=None,
        test_type=payload.event.test_type,
        performed_date=payload.event.performed_date,
        value=payload.event.value,
        source_system=payload.source_system,
        source_id=payload.source_id,
    )
    db.add(event)
    db.commit()

    create_audit_event(
        db,
        actor="SYSTEM",
        action=AuditAction.UPDATE,
        entity_type="MonitoringEvent",
        entity_id=str(event.id),
        details={"source_system": payload.source_system},
        request=request,
    )

    return {"status": "accepted", "event_id": str(event.id)}
