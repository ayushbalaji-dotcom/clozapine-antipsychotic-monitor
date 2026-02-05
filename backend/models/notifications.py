import enum
from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import mapped_column
from .base import Base, UUIDMixin, TimestampMixin


class RecipientType(str, enum.Enum):
    USER = "USER"
    TEAM = "TEAM"


class NotificationType(str, enum.Enum):
    TASK_OVERDUE = "TASK_OVERDUE"
    TASK_ESCALATED = "TASK_ESCALATED"
    EVENT_WARNING = "EVENT_WARNING"
    EVENT_CRITICAL = "EVENT_CRITICAL"


class NotificationPriority(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class InAppNotificationStatus(str, enum.Enum):
    UNREAD = "UNREAD"
    READ = "READ"
    ACKED = "ACKED"


class InAppNotification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "in_app_notifications"

    recipient_type = mapped_column(Enum(RecipientType, name="recipienttype"), nullable=False)
    recipient_id = mapped_column(String(64), nullable=False)
    notification_type = mapped_column(Enum(NotificationType, name="notificationtype"), nullable=False)
    priority = mapped_column(Enum(NotificationPriority, name="notificationpriority"), nullable=False)
    status = mapped_column(
        Enum(InAppNotificationStatus, name="inappnotificationstatus"),
        default=InAppNotificationStatus.UNREAD,
        nullable=False,
    )

    title = mapped_column(String(128), nullable=False)
    message = mapped_column(Text, nullable=True)
    payload = mapped_column(JSON, nullable=True)

    patient_id = mapped_column(ForeignKey("patients.id"), nullable=True)
    task_id = mapped_column(ForeignKey("monitoring_tasks.id"), nullable=True)
    event_id = mapped_column(ForeignKey("monitoring_events.id"), nullable=True)

    dedupe_key = mapped_column(String(128), nullable=False, unique=True)
    viewed_at = mapped_column(DateTime(timezone=True), nullable=True)
    acked_at = mapped_column(DateTime(timezone=True), nullable=True)
