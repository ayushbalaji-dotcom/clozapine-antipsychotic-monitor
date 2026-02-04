from datetime import date
from uuid import uuid4

from backend.models.medication import MedicationOrder, DrugCategory
from backend.models.patient import Patient
from backend.models.monitoring import PatientRiskFlags
from backend.services.scheduling import SchedulingEngine
from backend.services.rule_evaluator import RuleEvaluator


def build_patient():
    return Patient(id=uuid4(), pseudonym="PT-ECG-1")


def test_ecg_not_required_by_default():
    engine = SchedulingEngine()
    patient = build_patient()
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="risperidone",
        drug_category=DrugCategory.STANDARD,
        start_date=date(2025, 1, 1),
        flags={},
    )

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    assert not any(t.test_type == "ECG" for t in tasks)


def test_ecg_required_spc_drug():
    engine = SchedulingEngine()
    evaluator = RuleEvaluator()
    patient = build_patient()
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="haloperidol",
        drug_category=DrugCategory.STANDARD,
        start_date=date(2025, 1, 1),
        flags={},
    )

    assert evaluator.should_require_ecg(med, patient)
    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    assert any(t.test_type == "ECG" for t in tasks)


def test_ecg_required_cv_risk_flag():
    engine = SchedulingEngine()
    patient = build_patient()
    patient.risk_flags = PatientRiskFlags(
        patient_id=patient.id,
        cv_risk_present=True,
        ecg_indicated=True,
    )

    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="quetiapine",
        drug_category=DrugCategory.STANDARD,
        start_date=date(2025, 1, 1),
        flags={},
    )

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    assert any(t.test_type == "ECG" for t in tasks)
