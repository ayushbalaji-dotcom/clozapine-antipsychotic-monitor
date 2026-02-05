from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session
import pandas as pd
import io

from ..auth import require_role
from ..database import get_db
from ..models.ruleset import RuleSetVersion
from ..models.config import SystemConfig
from ..models.thresholds import ReferenceThreshold, ComparatorType
from ..services.audit_logger import create_audit_event
from ..models.audit import AuditAction
from .schemas import RuleSetUploadRequest, ConfigUpdateRequest, ThresholdPayload
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


@router.get("/thresholds")
def list_thresholds(db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    rows = db.query(ReferenceThreshold).order_by(ReferenceThreshold.monitoring_type.asc()).all()
    return [
        {
            "id": str(row.id),
            "monitoring_type": row.monitoring_type,
            "unit": row.unit,
            "comparator_type": row.comparator_type.value,
            "sex": row.sex,
            "age_band": row.age_band,
            "source_system_scope": row.source_system_scope,
            "low_critical": row.low_critical,
            "low_warning": row.low_warning,
            "high_warning": row.high_warning,
            "high_critical": row.high_critical,
            "coded_abnormal_values": row.coded_abnormal_values,
            "enabled": row.enabled,
            "version": row.version,
            "updated_by": row.updated_by,
            "updated_at": row.updated_at.isoformat(),
        }
        for row in rows
    ]


@router.post("/thresholds")
def create_threshold(
    payload: ThresholdPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    try:
        comparator = ComparatorType(payload.comparator_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid comparator_type")
    threshold = ReferenceThreshold(
        monitoring_type=payload.monitoring_type,
        unit=payload.unit,
        comparator_type=comparator,
        sex=payload.sex,
        age_band=payload.age_band,
        source_system_scope=payload.source_system_scope,
        low_critical=payload.low_critical,
        low_warning=payload.low_warning,
        high_warning=payload.high_warning,
        high_critical=payload.high_critical,
        coded_abnormal_values=payload.coded_abnormal_values,
        enabled=payload.enabled if payload.enabled is not None else True,
        version=payload.version,
        updated_by=getattr(current_user, "username", "SYSTEM"),
    )
    db.add(threshold)
    db.commit()

    create_audit_event(
        db,
        actor=getattr(current_user, "username", "SYSTEM"),
        action=AuditAction.UPDATE,
        entity_type="ReferenceThreshold",
        entity_id=str(threshold.id),
        details={"monitoring_type": threshold.monitoring_type},
        request=request,
    )
    return {"status": "ok", "id": str(threshold.id)}


@router.put("/thresholds/{threshold_id}")
def update_threshold(
    threshold_id: str,
    payload: ThresholdPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    threshold = db.query(ReferenceThreshold).filter_by(id=threshold_id).first()
    if not threshold:
        raise HTTPException(status_code=404, detail="Threshold not found")
    try:
        comparator = ComparatorType(payload.comparator_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid comparator_type")

    threshold.monitoring_type = payload.monitoring_type
    threshold.unit = payload.unit
    threshold.comparator_type = comparator
    threshold.sex = payload.sex
    threshold.age_band = payload.age_band
    threshold.source_system_scope = payload.source_system_scope
    threshold.low_critical = payload.low_critical
    threshold.low_warning = payload.low_warning
    threshold.high_warning = payload.high_warning
    threshold.high_critical = payload.high_critical
    threshold.coded_abnormal_values = payload.coded_abnormal_values
    threshold.enabled = payload.enabled if payload.enabled is not None else True
    threshold.version = payload.version
    threshold.updated_by = getattr(current_user, "username", "SYSTEM")

    db.add(threshold)
    db.commit()

    create_audit_event(
        db,
        actor=getattr(current_user, "username", "SYSTEM"),
        action=AuditAction.UPDATE,
        entity_type="ReferenceThreshold",
        entity_id=str(threshold.id),
        details={"monitoring_type": threshold.monitoring_type},
        request=request,
    )
    return {"status": "ok"}


@router.delete("/thresholds/{threshold_id}")
def delete_threshold(
    threshold_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    threshold = db.query(ReferenceThreshold).filter_by(id=threshold_id).first()
    if not threshold:
        raise HTTPException(status_code=404, detail="Threshold not found")
    db.delete(threshold)
    db.commit()

    create_audit_event(
        db,
        actor=getattr(current_user, "username", "SYSTEM"),
        action=AuditAction.UPDATE,
        entity_type="ReferenceThreshold",
        entity_id=str(threshold_id),
        details={"deleted": True},
        request=request,
    )
    return {"status": "ok"}


@router.get("/thresholds/template")
def thresholds_template(db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    template = """monitoring_type,unit,comparator_type,sex,age_band,source_system_scope,low_critical,low_warning,high_warning,high_critical,coded_abnormal_values,enabled,version
HbA1c,%,numeric,,,,5.0,5.7,6.5,7.5,,true,v1
ECG,ms,coded,,,,"",,,,"CRITICAL;ABNORMAL",true,v1
"""
    return {"template_csv": template}


@router.get("/thresholds/export")
def export_thresholds(
    format: str = "csv",
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    rows = db.query(ReferenceThreshold).order_by(ReferenceThreshold.monitoring_type.asc()).all()
    payload = [
        {
            "monitoring_type": row.monitoring_type,
            "unit": row.unit,
            "comparator_type": row.comparator_type.value,
            "sex": row.sex,
            "age_band": row.age_band,
            "source_system_scope": row.source_system_scope,
            "low_critical": row.low_critical,
            "low_warning": row.low_warning,
            "high_warning": row.high_warning,
            "high_critical": row.high_critical,
            "coded_abnormal_values": ";".join(row.coded_abnormal_values or []),
            "enabled": row.enabled,
            "version": row.version,
        }
        for row in rows
    ]
    if format.lower() == "json":
        return payload

    df = pd.DataFrame(payload)
    return {"csv": df.to_csv(index=False)}


@router.post("/thresholds/import")
def import_thresholds(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    content = file.file.read()
    df = pd.read_csv(io.BytesIO(content))

    inserted = 0
    updated = 0
    errors: list[str] = []

    for idx, row in df.iterrows():
        try:
            monitoring_type = str(row.get("monitoring_type", "")).strip()
            unit = str(row.get("unit", "")).strip()
            comparator_type = str(row.get("comparator_type", "")).strip()
            if not monitoring_type or not unit or not comparator_type:
                raise ValueError("monitoring_type, unit and comparator_type are required")

            lookup = (
                db.query(ReferenceThreshold)
                .filter(
                    ReferenceThreshold.monitoring_type == monitoring_type,
                    ReferenceThreshold.unit == unit,
                    ReferenceThreshold.comparator_type == ComparatorType(comparator_type),
                    ReferenceThreshold.sex == _null_if_nan(row.get("sex")),
                    ReferenceThreshold.age_band == _null_if_nan(row.get("age_band")),
                    ReferenceThreshold.source_system_scope == _null_if_nan(row.get("source_system_scope")),
                )
                .first()
            )

            coded_values = _parse_list(row.get("coded_abnormal_values"))
            if lookup:
                lookup.low_critical = _parse_float(row.get("low_critical"))
                lookup.low_warning = _parse_float(row.get("low_warning"))
                lookup.high_warning = _parse_float(row.get("high_warning"))
                lookup.high_critical = _parse_float(row.get("high_critical"))
                lookup.coded_abnormal_values = coded_values
                lookup.enabled = _parse_bool(row.get("enabled", True))
                lookup.version = _null_if_nan(row.get("version"))
                lookup.updated_by = getattr(current_user, "username", "SYSTEM")
                updated += 1
            else:
                entry = ReferenceThreshold(
                    monitoring_type=monitoring_type,
                    unit=unit,
                    comparator_type=ComparatorType(comparator_type),
                    sex=_null_if_nan(row.get("sex")),
                    age_band=_null_if_nan(row.get("age_band")),
                    source_system_scope=_null_if_nan(row.get("source_system_scope")),
                    low_critical=_parse_float(row.get("low_critical")),
                    low_warning=_parse_float(row.get("low_warning")),
                    high_warning=_parse_float(row.get("high_warning")),
                    high_critical=_parse_float(row.get("high_critical")),
                    coded_abnormal_values=coded_values,
                    enabled=_parse_bool(row.get("enabled", True)),
                    version=_null_if_nan(row.get("version")),
                    updated_by=getattr(current_user, "username", "SYSTEM"),
                )
                db.add(entry)
                inserted += 1
        except Exception as exc:
            errors.append(f"Row {idx}: {exc}")

    db.commit()

    create_audit_event(
        db,
        actor=getattr(current_user, "username", "SYSTEM"),
        action=AuditAction.UPDATE,
        entity_type="ReferenceThreshold",
        entity_id="import",
        details={"inserted": inserted, "updated": updated, "errors": len(errors)},
        request=request,
    )

    return {"inserted": inserted, "updated": updated, "errors": errors[:10]}


def _null_if_nan(value):
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def _parse_float(value):
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _parse_bool(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def _parse_list(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            import json

            data = json.loads(text)
            if isinstance(data, list):
                return data
        except Exception:
            return [text]
    return [item.strip() for item in text.split(";") if item.strip()]
