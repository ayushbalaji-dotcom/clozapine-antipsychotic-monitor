from datetime import date
from uuid import uuid4

from backend.models.medication import MedicationOrder, DrugCategory
from backend.models.patient import Patient
from backend.services.scheduling import SchedulingEngine, add_months


def build_patient():
    return Patient(id=uuid4(), pseudonym="PT-HDAT-1")


def test_hdat_baseline_includes_ecg():
    engine = SchedulingEngine()
    patient = build_patient()
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="haloperidol",
        drug_category=DrugCategory.HDAT,
        start_date=date(2025, 1, 1),
        flags={"is_hdat": True},
    )

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    baseline = [t for t in tasks if t.due_date == med.start_date]
    tests = {t.test_type for t in baseline}

    assert "ECG" in tests
    assert "Temperature" in tests
    assert "BP (supine + standing)" in tests
    assert "Pulse (supine + standing)" in tests


def test_hdat_3_month_tasks():
    engine = SchedulingEngine()
    patient = build_patient()
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="quetiapine",
        drug_category=DrugCategory.HDAT,
        start_date=date(2025, 1, 1),
        flags={"is_hdat": True},
    )

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    due_date = add_months(med.start_date, 3)
    three_month = [t for t in tasks if t.due_date == due_date]
    tests = {t.test_type for t in three_month}

    assert "Temperature" in tests
    assert "LFTs" in tests


def test_hdat_6_month_includes_ecg():
    engine = SchedulingEngine()
    patient = build_patient()
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="quetiapine",
        drug_category=DrugCategory.HDAT,
        start_date=date(2025, 1, 1),
        flags={"is_hdat": True},
    )

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    due_date = add_months(med.start_date, 6)
    six_month = [t for t in tasks if t.due_date == due_date]
    assert any(t.test_type == "ECG" for t in six_month)


def test_hdat_quarterly_after_year1():
    engine = SchedulingEngine()
    patient = build_patient()
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="olanzapine",
        drug_category=DrugCategory.HDAT,
        start_date=date(2025, 1, 1),
        flags={"is_hdat": True},
    )

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    due_date = add_months(med.start_date, 15)
    quarter = [t for t in tasks if t.due_date == due_date]
    assert any(t.test_type == "Weight/BMI" for t in quarter)


def test_hdat_hydration_vigilance_task():
    engine = SchedulingEngine()
    patient = build_patient()
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="olanzapine",
        drug_category=DrugCategory.HDAT,
        start_date=date(2025, 1, 1),
        flags={"is_hdat": True},
    )

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    hydration = [t for t in tasks if "Hydration" in t.test_type]
    assert hydration
    assert any(t.status.value == "ONGOING" for t in hydration)
