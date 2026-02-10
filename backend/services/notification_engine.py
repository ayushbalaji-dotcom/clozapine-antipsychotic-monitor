from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.monitoring import MonitoringTask, MonitoringEvent, TaskStatus
from ..models.notifications import (
    InAppNotification,
    InAppNotificationStatus,
    NotificationPriority,
    NotificationType,
    RecipientType,
)
from ..models.patient import Patient
from ..services.audit_logger import create_audit_event
from ..models.audit import AuditAction
from ..services.notifications import send_notification


class NotificationEngine:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def process_overdue_tasks(self) -> int:
        if not self.settings.IN_APP_NOTIFICATIONS_ENABLED:
            return 0

        today = date.today()
        tasks = (
            self.db.query(MonitoringTask)
            .filter(MonitoringTask.status == TaskStatus.OVERDUE)
            .all()
        )
        created = 0
        for task in tasks:
            patient = self.db.query(Patient).filter_by(id=task.patient_id).first()
            if not patient:
                continue

            overdue_key = f"TASK_OVERDUE:{task.id}"
            if self._create_notification_if_missing(
                dedupe_key=overdue_key,
                recipient=self._recipient_for_task(task),
                notification_type=NotificationType.TASK_OVERDUE,
                priority=NotificationPriority.WARNING,
                title="Monitoring overdue",
                message=f"Task overdue since {task.due_date.isoformat()}",
                patient=patient,
                task=task,
                metadata={
                    "pseudonym": patient.pseudonym,
                    "test_type": task.test_type,
                    "due_date": task.due_date.isoformat(),
                    "status": task.status.value,
                },
            ):
                created += 1

            days_overdue = (today - task.due_date).days
            if days_overdue >= self.settings.ESCALATION_THRESHOLD_DAYS:
                escalation_key = f"TASK_ESCALATED:{task.id}"
                if self._create_notification_if_missing(
                    dedupe_key=escalation_key,
                    recipient=(RecipientType.TEAM, self.settings.TEAM_LEAD_INBOX_ID),
                    notification_type=NotificationType.TASK_ESCALATED,
                    priority=NotificationPriority.CRITICAL,
                    title="Urgent review required",
                    message="Monitoring task overdue beyond escalation threshold.",
                    patient=patient,
                    task=task,
                    metadata={
                        "pseudonym": patient.pseudonym,
                        "test_type": task.test_type,
                        "due_date": task.due_date.isoformat(),
                        "days_overdue": days_overdue,
                        "status": task.status.value,
                    },
                ):
                    created += 1
        self.db.commit()
        return created

    def notify_abnormal_event(
        self,
        event: MonitoringEvent,
        patient: Patient,
        *,
        priority: NotificationPriority,
        reason: str | None = None,
    ) -> InAppNotification | None:
        if not self.settings.IN_APP_NOTIFICATIONS_ENABLED:
            return None

        if priority == NotificationPriority.CRITICAL:
            notification_type = NotificationType.EVENT_CRITICAL
            title = "Urgent review required"
            message = "Monitoring result outside configured critical thresholds."
        else:
            notification_type = NotificationType.EVENT_WARNING
            title = "Review required"
            message = "Monitoring result outside configured warning thresholds."

        dedupe_key = f"{notification_type.value}:{event.id}"
        created = self._create_notification_if_missing(
            dedupe_key=dedupe_key,
            recipient=self._recipient_for_event(patient),
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            patient=patient,
            event=event,
            metadata={
                "pseudonym": patient.pseudonym,
                "test_type": event.test_type,
                "performed_date": event.performed_date.isoformat(),
                "value": event.value,
                "unit": event.unit,
                "attachment_url": event.attachment_url,
                "reason": reason,
            },
        )
        return created

    def mark_notification_read(self, notification: InAppNotification, actor: str) -> None:
        if notification.status == InAppNotificationStatus.UNREAD:
            notification.status = InAppNotificationStatus.READ
            notification.viewed_at = datetime.now(timezone.utc)
            create_audit_event(
                self.db,
                actor=actor,
                action=AuditAction.NOTIFICATION_VIEWED,
                entity_type="InAppNotification",
                entity_id=str(notification.id),
                details={"status": notification.status.value},
                request=None,
                commit=False,
            )

    def mark_notification_acked(self, notification: InAppNotification, actor: str) -> None:
        notification.status = InAppNotificationStatus.ACKED
        notification.acked_at = datetime.now(timezone.utc)
        create_audit_event(
            self.db,
            actor=actor,
            action=AuditAction.NOTIFICATION_ACKED,
            entity_type="InAppNotification",
            entity_id=str(notification.id),
            details={"status": notification.status.value},
            request=None,
            commit=False,
        )

    def _recipient_for_task(self, task: MonitoringTask) -> tuple[RecipientType, str]:
        if task.assigned_to:
            return RecipientType.USER, task.assigned_to
        return RecipientType.TEAM, self.settings.TEAM_INBOX_ID

    def _recipient_for_event(self, patient: Patient) -> tuple[RecipientType, str]:
        task = (
            self.db.query(MonitoringTask)
            .filter(
                MonitoringTask.patient_id == patient.id,
                MonitoringTask.status.in_([TaskStatus.DUE, TaskStatus.OVERDUE]),
                MonitoringTask.assigned_to != None,
            )
            .order_by(MonitoringTask.due_date.asc())
            .first()
        )
        if task and task.assigned_to:
            return RecipientType.USER, task.assigned_to
        return RecipientType.TEAM, self.settings.TEAM_INBOX_ID

    def _create_notification_if_missing(
        self,
        *,
        dedupe_key: str,
        recipient: tuple[RecipientType, str],
        notification_type: NotificationType,
        priority: NotificationPriority,
        title: str,
        message: str,
        patient: Patient | None = None,
        task: MonitoringTask | None = None,
        event: MonitoringEvent | None = None,
        metadata: dict | None = None,
    ) -> InAppNotification | None:
        existing = (
            self.db.query(InAppNotification)
            .filter(InAppNotification.dedupe_key == dedupe_key)
            .first()
        )
        if existing:
            return None

        recipient_type, recipient_id = recipient
        notification = InAppNotification(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            patient_id=getattr(patient, "id", None),
            task_id=getattr(task, "id", None),
            event_id=getattr(event, "id", None),
            payload=metadata or {},
            dedupe_key=dedupe_key,
        )
        self.db.add(notification)
        self.db.flush()

        create_audit_event(
            self.db,
            actor="SYSTEM",
            action=AuditAction.NOTIFICATION_CREATED,
            entity_type="InAppNotification",
            entity_id=str(notification.id),
            details={
                "type": notification_type.value,
                "priority": priority.value,
                "recipient": recipient_id,
            },
            request=None,
            commit=False,
        )

        if self.settings.NOTIFICATIONS_ENABLED:
            send_notification(
                notification_type=notification_type.value,
                recipient=recipient_id,
                title=title,
                message=message,
                metadata=metadata or {},
            )

        return notification
