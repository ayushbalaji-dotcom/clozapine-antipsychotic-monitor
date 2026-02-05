from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..models.medication import MedicationOrder
from ..models.monitoring import MonitoringTask, MonitoringEvent
from ..models.patient import Patient
from ..services.scheduling import SchedulingEngine
from ..services.task_generator import TaskGenerator
from ..services.audit_logger import create_audit_event
from ..models.audit import AuditAction

router = APIRouter(tags=["scheduling"])


@router.post("/medications/{med_id}/calculate-schedule")
def recalculate_schedule(
    med_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("clinician")),
):
    med = db.query(MedicationOrder).filter_by(id=med_id).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
    patient = db.query(Patient).filter_by(id=med.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    engine = SchedulingEngine()
    tasks = engine.calculate_schedule(med, patient)

    generator = TaskGenerator(db)
    saved = generator.create_or_update_tasks(tasks, actor=getattr(current_user, "username", "SYSTEM"))

    create_audit_event(
        db,
        actor=getattr(current_user, "username", "SYSTEM"),
        action=AuditAction.UPDATE,
        entity_type="MedicationOrder",
        entity_id=str(med_id),
        details={"recalculated": True},
        request=request,
        commit=False,
    )
    db.commit()

    return {
        "medication_id": str(med_id),
        "tasks_created_or_updated": len(saved),
    }


@router.get("/patients/{patient_id}/monitoring-timeline")
def patient_monitoring_timeline(
    patient_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("clinician")),
):
    patient = db.query(Patient).filter_by(id=patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    meds = db.query(MedicationOrder).filter_by(patient_id=patient_id).all()
    tasks = db.query(MonitoringTask).filter_by(patient_id=patient_id).all()
    events = db.query(MonitoringEvent).filter_by(patient_id=patient_id).all()

    create_audit_event(
        db,
        actor=getattr(current_user, "username", "SYSTEM"),
        action=AuditAction.VIEW,
        entity_type="Patient",
        entity_id=str(patient_id),
        details={"pseudonym": patient.pseudonym},
        request=request,
        commit=False,
    )
    db.commit()

    return {
        "patient": {"id": str(patient.id), "pseudonym": patient.pseudonym},
        "medications": [
            {
                "id": str(med.id),
                "drug_name": med.drug_name,
                "drug_category": med.drug_category.value,
                "start_date": med.start_date.isoformat(),
                "stop_date": med.stop_date.isoformat() if med.stop_date else None,
            }
            for med in meds
        ],
        "tasks": [
            {
                "id": str(task.id),
                "test_type": task.test_type,
                "due_date": task.due_date.isoformat(),
                "status": task.status.value,
            }
            for task in tasks
        ],
        "events": [
            {
                "id": str(event.id),
                "test_type": event.test_type,
                "performed_date": event.performed_date.isoformat(),
                "value": event.value,
                "unit": event.unit,
                "abnormal_flag": event.abnormal_flag.value if event.abnormal_flag else None,
                "reviewed_status": event.reviewed_status.value if event.reviewed_status else None,
                "source_system": event.source_system,
            }
            for event in events
        ],
    }
