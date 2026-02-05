from __future__ import annotations

from typing import Dict

import pandas as pd

from ..config import get_settings
from ..database import get_sessionmaker
import logging
from ..models.medication import MedicationOrder, DrugCategory
from ..models.monitoring import MonitoringEvent, AbnormalFlag
from ..models.patient import Patient
from ..models.notifications import NotificationPriority
from ..services.abnormality import ThresholdEvaluator
from ..services.notification_engine import NotificationEngine
from ..services.identifier_detection import (
    IDENTIFIER_PATTERNS,
    banned_columns_found,
    redact_identifiers,
)
from ..services.scheduling import SchedulingEngine
from ..services.task_generator import TaskGenerator


class CSVIngestionService:
    """
    CSV validation and ingestion with strict identifier detection.
    """

    def _resolve_patient_column(self, df: pd.DataFrame) -> str | None:
        if "pseudonymous_number" in df.columns:
            return "pseudonymous_number"
        if "pseudonym" in df.columns:
            return "pseudonym"
        return None

    def _scan_identifier_patterns(self, df: pd.DataFrame) -> list[dict]:
        identifier_risks: list[dict] = []
        sample_df = df.head(100)
        for col in df.columns:
            series = sample_df[col].astype(str)
            for pattern_name, pattern in IDENTIFIER_PATTERNS.items():
                matches = series.str.contains(pattern, regex=True, na=False)
                if matches.any():
                    identifier_risks.append(
                        {
                            "type": "pattern_match",
                            "column": col,
                            "pattern": pattern_name,
                            "match_count": int(matches.sum()),
                            "reason": f"Values match {pattern_name} pattern",
                        }
                    )
        return identifier_risks

    def validate_patients_csv(self, df: pd.DataFrame) -> Dict:
        errors: list[str] = []
        warnings: list[str] = []
        identifier_risks: list[dict] = []

        patient_col = self._resolve_patient_column(df)
        required = [col for col in ["age_band", "sex"] if col not in df.columns]
        if not patient_col:
            required.append("pseudonymous_number")
        if required:
            errors.append(f"Missing required columns: {required}")

        banned_found = banned_columns_found(df.columns)
        if banned_found:
            errors.append(f"FORBIDDEN: Banned columns detected: {banned_found}")
            identifier_risks.append(
                {
                    "type": "banned_column",
                    "columns": banned_found,
                    "reason": "Column names suggest personal identifiers",
                }
            )

        identifier_risks.extend(self._scan_identifier_patterns(df))

        if patient_col:
            invalid_format = ~df[patient_col].astype(str).str.match(
                r"^(PAT-\d{6}|PT-[A-Z0-9]{6})$", na=False
            )
            if invalid_format.any():
                warnings.append(
                    f"{int(invalid_format.sum())} rows have invalid pseudonymous_number format"
                )

            duplicates = df[patient_col].duplicated()
            if duplicates.any():
                errors.append(f"{int(duplicates.sum())} duplicate pseudonymous_numbers found")

        if "age_band" in df.columns:
            valid_bands = ["18-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75+"]
            invalid = ~df["age_band"].isin(valid_bands)
            if invalid.any():
                warnings.append(
                    f"{int(invalid.sum())} rows have invalid age_band (expected: {', '.join(valid_bands)})"
                )

        if "sex" in df.columns:
            valid_sex = ["M", "F", "X", "U"]
            invalid = ~df["sex"].isin(valid_sex)
            if invalid.any():
                warnings.append(
                    f"{int(invalid.sum())} rows have invalid sex (expected: M, F, X, U)"
                )

        settings = get_settings()
        if identifier_risks and not settings.ALLOW_IDENTIFIERS:
            errors.append("Identifier-like values detected")

        is_valid = len(errors) == 0
        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "identifier_risks": identifier_risks,
            "row_count": len(df),
        }

    def validate_medications_csv(self, df: pd.DataFrame) -> Dict:
        errors: list[str] = []
        warnings: list[str] = []
        identifier_risks: list[dict] = []

        patient_col = self._resolve_patient_column(df)
        required = ["drug_name", "start_date"]
        if not patient_col:
            required.append("pseudonymous_number")
        missing = [col for col in required if col not in df.columns]
        if missing:
            errors.append(f"Missing required columns: {missing}")

        banned = banned_columns_found(df.columns)
        if banned:
            errors.append(f"FORBIDDEN: Banned columns: {banned}")
            identifier_risks.append(
                {
                    "type": "banned_column",
                    "columns": banned,
                    "reason": "Column names suggest personal identifiers",
                }
            )

        identifier_risks.extend(self._scan_identifier_patterns(df))

        if "start_date" in df.columns:
            parsed = pd.to_datetime(df["start_date"], errors="coerce")
            invalid = parsed.isna() & df["start_date"].notna()
            if invalid.any():
                errors.append("Invalid start_date format (expected YYYY-MM-DD)")

        if "stop_date" in df.columns:
            parsed = pd.to_datetime(df["stop_date"], errors="coerce")
            invalid = parsed.isna() & df["stop_date"].notna()
            if invalid.any():
                warnings.append("Some stop_date values could not be parsed")

        if "drug_name" in df.columns:
            valid_drugs = [
                "risperidone",
                "quetiapine",
                "aripiprazole",
                "haloperidol",
                "olanzapine",
                "clozapine",
                "chlorpromazine",
                "pimozide",
                "sertindole",
            ]
            invalid = ~df["drug_name"].astype(str).str.lower().isin(valid_drugs)
            if invalid.any():
                warnings.append(
                    f"{int(invalid.sum())} rows have unrecognized drug names"
                )

        settings = get_settings()
        if identifier_risks and not settings.ALLOW_IDENTIFIERS:
            errors.append("Identifier-like values detected")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "identifier_risks": identifier_risks,
            "row_count": len(df),
        }

    def validate_events_csv(self, df: pd.DataFrame) -> Dict:
        errors: list[str] = []
        warnings: list[str] = []
        identifier_risks: list[dict] = []

        patient_col = self._resolve_patient_column(df)
        required = ["test_type", "performed_date"]
        if not patient_col:
            required.append("pseudonymous_number")
        missing = [col for col in required if col not in df.columns]
        if missing:
            errors.append(f"Missing required columns: {missing}")

        banned = banned_columns_found(df.columns)
        if banned:
            errors.append(f"FORBIDDEN: Banned columns: {banned}")
            identifier_risks.append(
                {
                    "type": "banned_column",
                    "columns": banned,
                    "reason": "Column names suggest personal identifiers",
                }
            )

        identifier_risks.extend(self._scan_identifier_patterns(df))

        if "performed_date" in df.columns:
            parsed = pd.to_datetime(df["performed_date"], errors="coerce")
            invalid = parsed.isna() & df["performed_date"].notna()
            if invalid.any():
                errors.append("Invalid performed_date format (expected YYYY-MM-DD)")

        if "test_type" in df.columns:
            valid_tests = [
                "Weight/BMI",
                "HbA1c",
                "Fasting glucose",
                "Prolactin",
                "Lipids",
                "BP",
                "Pulse",
                "FBC",
                "U&Es",
                "LFTs",
                "ECG",
                "Waist circumference",
                "CK",
                "CVD risk assessment",
                "Smoking history",
                "Side effects assessment",
            ]
            invalid = ~df["test_type"].isin(valid_tests)
            if invalid.any():
                warnings.append(f"{int(invalid.sum())} rows have unrecognized test types")

        settings = get_settings()
        if identifier_risks and not settings.ALLOW_IDENTIFIERS:
            errors.append("Identifier-like values detected")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "identifier_risks": identifier_risks,
            "row_count": len(df),
        }

    def import_patients(self, df: pd.DataFrame) -> Dict:
        SessionLocal = get_sessionmaker()
        db = SessionLocal()

        inserted = 0
        updated = 0
        skipped = 0
        errors: list[str] = []

        patient_col = self._resolve_patient_column(df)
        if not patient_col:
            return {
                "inserted": 0,
                "updated": 0,
                "skipped": len(df),
                "errors": ["Missing pseudonymous_number column"],
            }

        try:
            for idx, row in df.iterrows():
                try:
                    pseudonym = str(row[patient_col]).strip()

                    patient = db.query(Patient).filter_by(pseudonym=pseudonym).first()

                    if patient:
                        patient.age_band = _clean_value(row.get("age_band"))
                        patient.sex = _clean_value(row.get("sex"))
                        patient.ethnicity = _clean_value(row.get("ethnicity"))
                        patient.service = _clean_value(row.get("service"))
                        updated += 1
                    else:
                        patient = Patient(
                            pseudonym=pseudonym,
                            age_band=_clean_value(row.get("age_band")),
                            sex=_clean_value(row.get("sex")),
                            ethnicity=_clean_value(row.get("ethnicity")),
                            service=_clean_value(row.get("service")),
                        )
                        db.add(patient)
                        inserted += 1

                except Exception as exc:
                    errors.append(f"Row {idx}: {exc}")
                    skipped += 1

            db.commit()
            logging.getLogger(__name__).info(
                "Patients import: %s inserted, %s updated, %s skipped",
                inserted,
                updated,
                skipped,
            )
        finally:
            db.close()

        return {
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "errors": errors[:10],
        }

    def import_medications(self, df: pd.DataFrame) -> Dict:
        SessionLocal = get_sessionmaker()
        db = SessionLocal()
        engine = SchedulingEngine()
        task_gen = TaskGenerator(db)

        inserted = 0
        updated = 0
        skipped = 0
        errors: list[str] = []

        patient_col = self._resolve_patient_column(df)
        if not patient_col:
            return {
                "inserted": 0,
                "updated": 0,
                "skipped": len(df),
                "errors": ["Missing pseudonymous_number column"],
            }

        try:
            for idx, row in df.iterrows():
                try:
                    patient = (
                        db.query(Patient)
                        .filter_by(pseudonym=str(row[patient_col]).strip())
                        .first()
                    )

                    if not patient:
                        errors.append(f"Row {idx}: Patient not found")
                        skipped += 1
                        continue

                    start_date = pd.to_datetime(row["start_date"]).date()
                    stop_date = (
                        pd.to_datetime(row["stop_date"]).date()
                        if pd.notna(row.get("stop_date"))
                        else None
                    )

                    drug_name = str(row["drug_name"]).strip()
                    is_hdat = _parse_bool(row.get("is_hdat"))
                    drug_lower = drug_name.lower()
                    if is_hdat:
                        category = DrugCategory.HDAT
                    elif drug_lower in {"chlorpromazine", "clozapine", "olanzapine"}:
                        category = DrugCategory.SPECIAL_GROUP
                    else:
                        category = DrugCategory.STANDARD

                    med = (
                        db.query(MedicationOrder)
                        .filter_by(
                            patient_id=patient.id,
                            drug_name=drug_name,
                            start_date=start_date,
                        )
                        .first()
                    )

                    if med:
                        med.stop_date = stop_date
                        med.dose = _clean_value(row.get("dose"))
                        med.route = _clean_value(row.get("route"))
                        med.frequency = _clean_value(row.get("frequency"))
                        med.flags = {**(med.flags or {}), "is_hdat": is_hdat}
                        med.drug_category = category
                        updated += 1
                    else:
                        med = MedicationOrder(
                            patient_id=patient.id,
                            drug_name=drug_name,
                            drug_category=category,
                            start_date=start_date,
                            stop_date=stop_date,
                            dose=_clean_value(row.get("dose")),
                            route=_clean_value(row.get("route")),
                            frequency=_clean_value(row.get("frequency")),
                            flags={"is_hdat": is_hdat},
                            source_system="CSV_UPLOAD",
                        )
                        db.add(med)
                        db.flush()
                        inserted += 1

                    tasks = engine.calculate_schedule(med, patient)
                    task_gen.create_or_update_tasks(tasks, actor="SYSTEM")

                except Exception as exc:
                    errors.append(f"Row {idx}: {exc}")
                    skipped += 1

            db.commit()
            logging.getLogger(__name__).info(
                "Medications import: %s inserted, %s updated, %s skipped",
                inserted,
                updated,
                skipped,
            )
        finally:
            db.close()

        return {
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "errors": errors[:10],
        }

    def import_events(self, df: pd.DataFrame) -> Dict:
        SessionLocal = get_sessionmaker()
        db = SessionLocal()
        task_gen = TaskGenerator(db)
        evaluator = ThresholdEvaluator(db)
        notifier = NotificationEngine(db)

        inserted = 0
        updated = 0
        skipped = 0
        errors: list[str] = []
        abnormal_summary = {
            AbnormalFlag.NORMAL.value: 0,
            AbnormalFlag.OUTSIDE_WARNING.value: 0,
            AbnormalFlag.OUTSIDE_CRITICAL.value: 0,
            AbnormalFlag.UNKNOWN.value: 0,
        }

        patient_col = self._resolve_patient_column(df)
        if not patient_col:
            return {
                "inserted": 0,
                "updated": 0,
                "skipped": len(df),
                "errors": ["Missing pseudonymous_number column"],
            }

        try:
            for idx, row in df.iterrows():
                try:
                    patient = (
                        db.query(Patient)
                        .filter_by(pseudonym=str(row[patient_col]).strip())
                        .first()
                    )
                    if not patient:
                        errors.append(f"Row {idx}: Patient not found")
                        skipped += 1
                        continue

                    performed_date = pd.to_datetime(row["performed_date"]).date()
                    test_type = str(row["test_type"]).strip()

                    existing = (
                        db.query(MonitoringEvent)
                        .filter_by(
                            patient_id=patient.id,
                            test_type=test_type,
                            performed_date=performed_date,
                        )
                        .first()
                    )

                    value = _clean_value(row.get("value"))

                    if existing:
                        if value is not None:
                            existing.value = value
                        unit = _clean_value(row.get("unit"))
                        if unit is not None:
                            existing.unit = unit
                        interpretation = _clean_value(row.get("interpretation"))
                        if interpretation is not None:
                            existing.interpretation = interpretation
                        updated += 1
                        event = existing
                    else:
                        event = MonitoringEvent(
                            patient_id=patient.id,
                            test_type=test_type,
                            performed_date=performed_date,
                            value=value,
                            unit=_clean_value(row.get("unit")),
                            interpretation=_clean_value(row.get("interpretation")),
                            source_system="CSV_UPLOAD",
                        )
                        db.add(event)
                        db.flush()
                        inserted += 1

                        evaluation = evaluator.evaluate_event(event, patient)
                        evaluator.apply_evaluation(event, evaluation)
                        abnormal_summary[evaluation.flag.value] += 1

                        if evaluation.flag == AbnormalFlag.OUTSIDE_CRITICAL:
                            notifier.notify_abnormal_event(
                                event,
                                patient,
                                priority=NotificationPriority.CRITICAL,
                                reason=evaluation.reason,
                            )
                        elif evaluation.flag == AbnormalFlag.OUTSIDE_WARNING:
                            notifier.notify_abnormal_event(
                                event,
                                patient,
                                priority=NotificationPriority.WARNING,
                                reason=evaluation.reason,
                            )

                    task_gen.auto_complete_tasks_for_event(event, actor="SYSTEM")

                except Exception as exc:
                    errors.append(f"Row {idx}: {exc}")
                    skipped += 1

            db.commit()
            logging.getLogger(__name__).info(
                "Events import: %s inserted, %s updated, %s skipped",
                inserted,
                updated,
                skipped,
            )
        finally:
            db.close()

        return {
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "errors": errors[:10],
            "abnormal_summary": abnormal_summary,
        }


def _parse_bool(value) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def _clean_value(value):
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, str):
        settings = get_settings()
        if not settings.ALLOW_IDENTIFIERS:
            redacted, _hits = redact_identifiers(value)
            return redacted
    return value
