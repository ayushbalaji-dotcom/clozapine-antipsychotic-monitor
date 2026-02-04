from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..models.monitoring import MonitoringTask, MonitoringEvent
from ..services.task_generator import TaskGenerator
from ..services.audit_logger import create_audit_event
from ..models.audit import AuditAction
from .schemas import AcknowledgeTaskRequest, CompleteTaskRequest, WaiveTaskRequest

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/{task_id}/acknowledge")
def acknowledge_task(
    task_id: UUID,
    payload: AcknowledgeTaskRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("clinician")),
):
    task = db.query(MonitoringTask).filter_by(id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.assigned_to = payload.assigned_to or getattr(current_user, "username", None)
    db.add(task)
    db.commit()

    create_audit_event(
        db,
        actor=getattr(current_user, "username", "SYSTEM"),
        action=AuditAction.ACKNOWLEDGE,
        entity_type="MonitoringTask",
        entity_id=str(task.id),
        details={"assigned_to": task.assigned_to},
        request=request,
    )

    return {"status": "ok", "task_id": str(task.id)}


@router.post("/{task_id}/complete")
def complete_task(
    task_id: UUID,
    payload: CompleteTaskRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("clinician")),
):
    event = db.query(MonitoringEvent).filter_by(id=payload.monitoring_event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Monitoring event not found")

    generator = TaskGenerator(db)
    task = generator.mark_task_done(task_id, getattr(current_user, "username", "SYSTEM"), event)

    create_audit_event(
        db,
        actor=getattr(current_user, "username", "SYSTEM"),
        action=AuditAction.UPDATE,
        entity_type="MonitoringTask",
        entity_id=str(task.id),
        details={"status": "DONE"},
        request=request,
    )

    return {"status": "ok", "task_id": str(task.id)}


@router.post("/{task_id}/waive")
def waive_task(
    task_id: UUID,
    payload: WaiveTaskRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("senior_clinician")),
):
    generator = TaskGenerator(db)
    task = generator.waive_task(
        task_id,
        getattr(current_user, "username", "SYSTEM"),
        payload.reason,
        payload.waived_until,
    )

    create_audit_event(
        db,
        actor=getattr(current_user, "username", "SYSTEM"),
        action=AuditAction.WAIVE,
        entity_type="MonitoringTask",
        entity_id=str(task.id),
        details={"reason": payload.reason},
        request=request,
    )

    return {"status": "ok", "task_id": str(task.id)}
