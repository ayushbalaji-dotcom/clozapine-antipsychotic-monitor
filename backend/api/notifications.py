from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import require_role
from ..config import get_settings
from ..database import get_db
from ..models.monitoring import MonitoringEvent, ReviewStatus
from ..models.notifications import (
    InAppNotification,
    InAppNotificationStatus,
    NotificationPriority,
    NotificationType,
    RecipientType,
)
from ..services.notification_engine import NotificationEngine


router = APIRouter(prefix="/notifications", tags=["notifications"])


def _user_can_access(notification: InAppNotification, username: str, team_ids: set[str]) -> bool:
    if notification.recipient_type == RecipientType.USER:
        return notification.recipient_id == username
    if notification.recipient_type == RecipientType.TEAM:
        return notification.recipient_id in team_ids
    return False


@router.get("")
def list_notifications(
    status: str | None = None,
    priority: str | None = None,
    patient_id: UUID | None = None,
    unread_only: bool = False,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("clinician")),
):
    settings = get_settings()
    team_ids = {settings.TEAM_INBOX_ID, settings.TEAM_LEAD_INBOX_ID}

    query = db.query(InAppNotification).filter(
        or_(
            (InAppNotification.recipient_type == RecipientType.USER)
            & (InAppNotification.recipient_id == current_user.username),
            (InAppNotification.recipient_type == RecipientType.TEAM)
            & (InAppNotification.recipient_id.in_(team_ids)),
        )
    )

    if status:
        try:
            query = query.filter(InAppNotification.status == InAppNotificationStatus(status.upper()))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value")
    if priority:
        try:
            query = query.filter(InAppNotification.priority == NotificationPriority(priority.upper()))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid priority value")
    if patient_id:
        query = query.filter(InAppNotification.patient_id == patient_id)
    if unread_only:
        query = query.filter(InAppNotification.status == InAppNotificationStatus.UNREAD)

    notifications = (
        query.order_by(InAppNotification.created_at.desc())
        .offset(offset)
        .limit(min(limit, 500))
        .all()
    )

    items = []
    for notification in notifications:
        items.append(
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
                "viewed_at": notification.viewed_at.isoformat() if notification.viewed_at else None,
                "acked_at": notification.acked_at.isoformat() if notification.acked_at else None,
            }
        )

    return {"count": len(items), "items": items}


@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("clinician")),
):
    settings = get_settings()
    team_ids = {settings.TEAM_INBOX_ID, settings.TEAM_LEAD_INBOX_ID}

    notification = db.query(InAppNotification).filter_by(id=notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if not _user_can_access(notification, current_user.username, team_ids):
        raise HTTPException(status_code=403, detail="Forbidden")

    engine = NotificationEngine(db)
    engine.mark_notification_read(notification, actor=current_user.username)
    db.commit()

    return {"status": "ok", "notification_id": str(notification.id)}


@router.post("/{notification_id}/ack")
def acknowledge_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("clinician")),
):
    settings = get_settings()
    team_ids = {settings.TEAM_INBOX_ID, settings.TEAM_LEAD_INBOX_ID}

    notification = db.query(InAppNotification).filter_by(id=notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if not _user_can_access(notification, current_user.username, team_ids):
        raise HTTPException(status_code=403, detail="Forbidden")

    engine = NotificationEngine(db)
    engine.mark_notification_acked(notification, actor=current_user.username)

    if notification.event_id:
        event = db.query(MonitoringEvent).filter_by(id=notification.event_id).first()
        if event:
            event.reviewed_status = ReviewStatus.REVIEWED
            event.reviewed_by = current_user.username
            event.reviewed_at = datetime.now(timezone.utc)

    db.commit()

    return {"status": "ok", "notification_id": str(notification.id)}
