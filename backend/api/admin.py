from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..models.ruleset import RuleSetVersion
from ..models.config import SystemConfig
from ..services.audit_logger import create_audit_event
from ..models.audit import AuditAction
from .schemas import RuleSetUploadRequest, ConfigUpdateRequest
from ..rules.rule_loader import load_ruleset

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ruleset")
def get_ruleset(db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    ruleset = db.query(RuleSetVersion).order_by(RuleSetVersion.created_at.desc()).first()
    if ruleset:
        return {
            "version": ruleset.version,
            "effective_from": ruleset.effective_from.isoformat(),
            "rules_json": ruleset.rules_json,
        }
    return load_ruleset()


@router.put("/ruleset")
def put_ruleset(
    payload: RuleSetUploadRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    entry = RuleSetVersion(
        version=payload.version,
        effective_from=payload.effective_from,
        rules_json=payload.rules_json,
    )
    db.add(entry)
    db.commit()

    create_audit_event(
        db,
        actor=getattr(current_user, "username", "SYSTEM"),
        action=AuditAction.UPDATE,
        entity_type="RuleSetVersion",
        entity_id=str(entry.id),
        details={"version": payload.version},
        request=request,
    )

    return {"status": "ok", "version": payload.version}


@router.get("/config")
def get_config(db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    rows = db.query(SystemConfig).all()
    return {row.key: row.value for row in rows}


@router.put("/config")
def put_config(
    payload: ConfigUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    for key, value in payload.values.items():
        row = db.query(SystemConfig).filter_by(key=key).first()
        if row:
            row.value = value
        else:
            row = SystemConfig(key=key, value=value)
            db.add(row)
    db.commit()

    create_audit_event(
        db,
        actor=getattr(current_user, "username", "SYSTEM"),
        action=AuditAction.UPDATE,
        entity_type="SystemConfig",
        entity_id="*",
        details={"keys": list(payload.values.keys())},
        request=request,
    )

    return {"status": "ok"}
