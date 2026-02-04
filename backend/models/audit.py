import enum
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, JSON
from sqlalchemy.orm import mapped_column
from .base import Base, UUIDMixin


class AuditAction(str, enum.Enum):
    VIEW = "VIEW"
    UPDATE = "UPDATE"
    ACKNOWLEDGE = "ACKNOWLEDGE"
    WAIVE = "WAIVE"


class AuditEvent(Base, UUIDMixin):
    __tablename__ = "audit_events"

    actor = mapped_column(String(64), nullable=False)
    action = mapped_column(Enum(AuditAction), nullable=False)
    entity_type = mapped_column(String(64), nullable=False)
    entity_id = mapped_column(String(64), nullable=False)
    request_id = mapped_column(String(64), nullable=False)
    ip_address = mapped_column(String(64), nullable=False)
    details = mapped_column(JSON, nullable=True)
    timestamp = mapped_column(DateTime(timezone=True), nullable=False)


class NotificationChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    TEAMS = "TEAMS"


class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class NotificationLog(Base, UUIDMixin):
    __tablename__ = "notification_logs"

    task_id = mapped_column(ForeignKey("monitoring_tasks.id"), nullable=False)
    channel = mapped_column(Enum(NotificationChannel), nullable=False)
    recipient = mapped_column(String(128), nullable=False)
    sent_at = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_status = mapped_column(Enum(NotificationStatus), nullable=False)
    error_message = mapped_column(Text, nullable=True)
