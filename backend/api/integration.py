from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import io

from ..auth_integration import require_api_key
from ..database import get_db
from ..services.export_service import ExportService
from ..services.integration_service import IntegrationService
from ..services.notification_engine import NotificationEngine
from ..models.notifications import InAppNotification, InAppNotificationStatus
from ..models.monitoring import MonitoringEvent, ReviewStatus
from ..services.audit_logger import create_audit_event
from ..models.audit import AuditAction
from .schemas import IntegrationFetchRequest


router = APIRouter(prefix="/integration", tags=["integration"])


@router.post("/fetch-monitoring")
def fetch_monitoring(
    payload: IntegrationFetchRequest,
    request: Request,
    db: Session = Depends(get_db),
    _integration=Depends(require_api_key),
):
    try:
        service = IntegrationService(db)
        result = service.fetch_and_import(
            nhs_number=payload.nhs_number,
            requested_by=payload.requested_by,
            source_system=payload.source_system,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    create_audit_event(
        db,
        actor="INTEGRATION_API_KEY",
        action=AuditAction.UPDATE,
        entity_type="EPRFetch",
        entity_id=result.get("patient_id", ""),
        details={"pseudonym": result.get("pseudonym")},
        request=request,
    )

    return result


@router.get("/export/csv")
def export_csv(
    tracked_only: bool = True,
    db: Session = Depends(get_db),
    _integration=Depends(require_api_key),
):
    exporter = ExportService(db)
    data = exporter.build_export_zip(tracked_only=tracked_only)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=monitoring_export.zip"},
    )


@router.get("/notifications")
def list_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    _integration=Depends(require_api_key),
):
    query = db.query(InAppNotification)
    if unread_only:
        query = query.filter(InAppNotification.status == InAppNotificationStatus.UNREAD)

    notifications = query.order_by(InAppNotification.created_at.desc()).limit(500).all()
    return [
        {
            "id": str(notification.id),
            "type": notification.notification_type.value,
            "priority": notification.priority.value,
            "status": notification.status.value,
            "title": notification.title,
            "message": notification.message,
            "patient_id": str(notification.patient_id) if notification.patient_id else None,
            "task_id": str(notification.task_id) if notification.task_id else None,
            "event_id": str(notification.event_id) if notification.event_id else None,
            "metadata": notification.payload or {},
            "created_at": notification.created_at.isoformat(),
        }
        for notification in notifications
    ]


@router.post("/notifications/{notification_id}/ack")
def acknowledge_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    _integration=Depends(require_api_key),
):
    notification = db.query(InAppNotification).filter_by(id=notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    engine = NotificationEngine(db)
    engine.mark_notification_acked(notification, actor="INTEGRATION_API_KEY")

    if notification.event_id:
        event = db.query(MonitoringEvent).filter_by(id=notification.event_id).first()
        if event:
            event.reviewed_status = ReviewStatus.REVIEWED
            event.reviewed_by = "INTEGRATION_API_KEY"
            event.reviewed_at = notification.acked_at

    db.commit()
    return {"status": "ok", "notification_id": str(notification.id)}
