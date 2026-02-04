from datetime import date, timedelta
from uuid import uuid4

from backend.models.medication import MedicationOrder, DrugCategory
from backend.models.patient import Patient
from backend.services.scheduling import SchedulingEngine, add_months


def build_patient():
    return Patient(id=uuid4(), pseudonym="PT-STD-1")


def build_med(start_date: date):
    return MedicationOrder(
        id=uuid4(),
        patient_id=uuid4(),
        drug_name="risperidone",
        drug_category=DrugCategory.STANDARD,
        start_date=start_date,
        flags={},
    )


def test_standard_pretreatment_baseline():
    engine = SchedulingEngine()
    patient = build_patient()
    med = build_med(date(2025, 1, 1))
    med.patient_id = patient.id

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    baseline = [t for t in tasks if t.due_date == med.start_date]

    required = {"Weight/BMI", "Prolactin", "Lipids", "BP", "Pulse", "U&Es", "FBC"}
    baseline_tests = {t.test_type for t in baseline}
    assert required.issubset(baseline_tests)


def test_standard_weekly_weight_six_weeks():
    engine = SchedulingEngine()
    patient = build_patient()
    med = build_med(date(2025, 1, 1))
    med.patient_id = patient.id

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    weekly_weights = [
        t for t in tasks if t.test_type == "Weight/BMI" and t.due_date > med.start_date
    ]

    # weekly x6 should include 6 tasks within first 6 weeks
    first_six_weeks = [t for t in weekly_weights if t.due_date <= med.start_date + timedelta(weeks=6)]
    assert len(first_six_weeks) == 6


def test_standard_three_month_milestone():
    engine = SchedulingEngine()
    patient = build_patient()
    med = build_med(date(2025, 1, 1))
    med.patient_id = patient.id

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    due_date = add_months(med.start_date, 3)
    three_month = [t for t in tasks if t.due_date == due_date]

    tests = {t.test_type for t in three_month}
    assert "Prolactin" in tests
    assert "Weight/BMI" in tests


def test_standard_six_month_glucose():
    engine = SchedulingEngine()
    patient = build_patient()
    med = build_med(date(2025, 1, 1))
    med.patient_id = patient.id

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    due_date = add_months(med.start_date, 6)
    six_month = [t for t in tasks if t.due_date == due_date]

    assert any("glucose" in t.test_type.lower() or "hba1c" in t.test_type.lower() for t in six_month)


def test_standard_annual_and_recurring():
    engine = SchedulingEngine()
    patient = build_patient()
    med = build_med(date(2025, 1, 1))
    med.patient_id = patient.id

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    year1 = add_months(med.start_date, 12)
    year2 = add_months(med.start_date, 24)

    assert any(t.due_date == year1 and t.test_type == "Lipids" for t in tasks)
    assert any(t.due_date == year2 and t.test_type == "Weight/BMI" for t in tasks)
