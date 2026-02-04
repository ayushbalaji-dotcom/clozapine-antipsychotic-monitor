from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..models.monitoring import MonitoringTask, TaskStatus
from ..models.medication import MedicationOrder
from ..models.patient import Patient

router = APIRouter(tags=["worklist"])


@router.get("/worklist")
def get_worklist(
    status: TaskStatus | None = None,
    drug_category: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("clinician")),
):
    query = (
        db.query(MonitoringTask, MedicationOrder, Patient)
        .join(MedicationOrder, MonitoringTask.medication_order_id == MedicationOrder.id)
        .join(Patient, MonitoringTask.patient_id == Patient.id)
    )

    if status:
        query = query.filter(MonitoringTask.status == status)
    if drug_category:
        query = query.filter(MedicationOrder.drug_category == drug_category)

    tasks = query.order_by(MonitoringTask.due_date.asc()).all()

    results = []
    for task, med, patient in tasks:
        results.append(
            {
                "task_id": str(task.id),
                "patient_id": str(patient.id),
                "patient": patient.pseudonym,
                "drug_name": med.drug_name,
                "start_date": med.start_date.isoformat(),
                "hdat": bool(med.flags.get("is_hdat")),
                "test_type": task.test_type,
                "due_date": task.due_date.isoformat(),
                "assigned_to": task.assigned_to,
                "status": task.status.value,
            }
        )

    return {"count": len(results), "items": results}
