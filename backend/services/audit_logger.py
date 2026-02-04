import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import Request
from sqlalchemy.orm import Session
from ..config import get_settings
from ..models.audit import AuditEvent, AuditAction
from ..database import get_sessionmaker


def create_audit_event(
    db: Session,
    actor: str,
    action: AuditAction,
    entity_type: str,
    entity_id: str,
    details: dict[str, Any] | None,
    request: Request | None,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    commit: bool = True,
) -> AuditEvent:
    settings = get_settings()
    event = AuditEvent(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        request_id=(
            getattr(request.state, "request_id", "") if request is not None else (request_id or "")
        ),
        ip_address=(
            getattr(request.client, "host", "") if request is not None else (ip_address or "")
        ),
        details=details or {},
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    if commit:
        db.commit()

    if settings.AUDIT_EXPORT_PATH:
        _write_audit_export(settings.AUDIT_EXPORT_PATH, event)

    return event


def _write_audit_export(path: str, event: AuditEvent) -> None:
    export_path = Path(path)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": event.timestamp.isoformat(),
        "actor": event.actor,
        "action": event.action,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "request_id": event.request_id,
        "ip_address": event.ip_address,
        "details": event.details,
    }
    with export_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


class AuditLogger:
    def log_csv_upload(
        self,
        *,
        actor: str,
        file_types: list[str],
        validation_outcome: str,
        validate_only: bool,
        row_counts: dict[str, int],
    ) -> AuditEvent:
        SessionLocal = get_sessionmaker()
        db = SessionLocal()
        try:
            return create_audit_event(
                db,
                actor=actor,
                action=AuditAction.UPDATE,
                entity_type="CSVUpload",
                entity_id="csv_upload",
                details={
                    "file_types": file_types,
                    "validation_outcome": validation_outcome,
                    "validate_only": validate_only,
                    "row_counts": row_counts,
                },
                request=None,
                commit=True,
            )
        finally:
            db.close()
