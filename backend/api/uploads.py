from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import StreamingResponse
from typing import Optional
import pandas as pd
import io
import zipfile

from ..auth import require_role
from ..services.csv_ingestion import CSVIngestionService
from ..services.audit_logger import AuditLogger

router = APIRouter(prefix="/uploads", tags=["CSV Uploads"])


@router.post("/csv")
async def upload_csv(
    patients: Optional[UploadFile] = File(None),
    medications: Optional[UploadFile] = File(None),
    events: Optional[UploadFile] = File(None),
    validate_only: bool = Form(False),
    current_user=Depends(require_role("clinician")),
):
    """
    Upload CSV files to populate patients, medications, monitoring events.
    """
    audit = AuditLogger()
    ingestion = CSVIngestionService()

    results = {
        "validation_report": {},
        "import_summary": {},
        "errors": [],
    }

    if patients:
        try:
            content = await patients.read()
            df = pd.read_csv(io.BytesIO(content))

            validation = ingestion.validate_patients_csv(df)
            results["validation_report"]["patients"] = validation

            if not validation["is_valid"]:
                results["errors"].append(f"Patients CSV invalid: {validation['errors']}")
            elif not validate_only:
                summary = ingestion.import_patients(df)
                results["import_summary"]["patients"] = summary
        except Exception as exc:
            results["errors"].append(f"Error processing patients CSV: {exc}")

    if medications:
        try:
            content = await medications.read()
            df = pd.read_csv(io.BytesIO(content))

            validation = ingestion.validate_medications_csv(df)
            results["validation_report"]["medications"] = validation

            if not validation["is_valid"]:
                results["errors"].append(f"Medications CSV invalid: {validation['errors']}")
            elif not validate_only:
                summary = ingestion.import_medications(df)
                results["import_summary"]["medications"] = summary
        except Exception as exc:
            results["errors"].append(f"Error processing medications CSV: {exc}")

    if events:
        try:
            content = await events.read()
            df = pd.read_csv(io.BytesIO(content))

            validation = ingestion.validate_events_csv(df)
            results["validation_report"]["events"] = validation

            if not validation["is_valid"]:
                results["errors"].append(f"Events CSV invalid: {validation['errors']}")
            elif not validate_only:
                summary = ingestion.import_events(df)
                results["import_summary"]["events"] = summary
        except Exception as exc:
            results["errors"].append(f"Error processing events CSV: {exc}")

    audit.log_csv_upload(
        actor=getattr(current_user, "username", "SYSTEM"),
        file_types=[f.filename for f in [patients, medications, events] if f],
        validation_outcome="success" if not results["errors"] else "failed",
        validate_only=validate_only,
        row_counts={
            k: v.get("row_count", 0)
            for k, v in results["validation_report"].items()
        },
    )

    return results


@router.get("/templates")
async def download_templates(
    current_user=Depends(require_role("clinician")),
):
    """
    Download CSV templates as ZIP file.
    """
    patients_csv = """pseudonymous_number,age_band,sex
PAT-000001,45-54,M
PAT-000002,35-44,F
PAT-000003,55-64,M
"""

    medications_csv = """pseudonymous_number,drug_name,start_date,stop_date,dose,route,is_hdat
PAT-000001,risperidone,2025-01-15,,2mg,PO,false
PAT-000002,clozapine,2025-01-10,,100mg,PO,false
PAT-000003,haloperidol,2024-12-01,2025-02-01,5mg,PO,true
"""

    events_csv = """pseudonymous_number,test_type,performed_date,value,unit,interpretation
PAT-000001,Weight/BMI,2025-01-15,75,kg,
PAT-000001,HbA1c,2025-01-20,5.8,%,ABNORMAL
PAT-000002,FBC,2025-01-12,Normal,,
"""

    vocab_md = """# Controlled Vocabulary

## Antipsychotic Drug Names
Standard: risperidone, quetiapine, aripiprazole, haloperidol
Special: chlorpromazine, clozapine, olanzapine
SPC ECG Required: haloperidol, pimozide, sertindole

## Test Types
Weight/BMI, HbA1c, Fasting glucose, Prolactin, Lipids, BP, Pulse,
FBC, U&Es, LFTs, ECG, Waist circumference, CK,
CVD risk assessment, Smoking history, Side effects assessment
"""

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("patients_template.csv", patients_csv)
        zf.writestr("medications_template.csv", medications_csv)
        zf.writestr("events_template.csv", events_csv)
        zf.writestr("controlled_vocabulary.md", vocab_md)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=csv_templates.zip"},
    )


@router.post("/validate")
async def validate_csv_only(
    file: UploadFile = File(...),
    file_type: str = Form("patients"),
    current_user=Depends(require_role("clinician")),
):
    """
    Validate CSV without importing (dry run).
    """
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))

    ingestion = CSVIngestionService()

    if file_type == "patients":
        return ingestion.validate_patients_csv(df)
    if file_type == "medications":
        return ingestion.validate_medications_csv(df)
    if file_type == "events":
        return ingestion.validate_events_csv(df)
    raise HTTPException(400, f"Invalid file_type: {file_type}")
