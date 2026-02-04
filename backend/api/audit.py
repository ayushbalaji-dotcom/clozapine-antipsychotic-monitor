from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..models.audit import AuditEvent

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def get_audit(
    patient_id: UUID | None = None,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("audit_viewer")),
):
    query = db.query(AuditEvent)
    if patient_id:
        query = query.filter(AuditEvent.entity_id == str(patient_id))
    if from_ts:
        query = query.filter(AuditEvent.timestamp >= from_ts)
    if to_ts:
        query = query.filter(AuditEvent.timestamp <= to_ts)

    events = query.order_by(AuditEvent.timestamp.desc()).limit(1000).all()

    return {
        "count": len(events),
        "events": [
            {
                "actor": e.actor,
                "action": e.action.value,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "request_id": e.request_id,
                "ip_address": e.ip_address,
                "details": e.details,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ],
    }
