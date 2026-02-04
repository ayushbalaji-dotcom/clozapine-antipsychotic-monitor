from datetime import date
from uuid import uuid4

from backend.models.medication import MedicationOrder, DrugCategory
from backend.models.patient import Patient
from backend.services.scheduling import SchedulingEngine, add_months


def build_patient():
    return Patient(id=uuid4(), pseudonym="PT-SP-1")


def test_special_group_one_month_glucose():
    engine = SchedulingEngine()
    patient = build_patient()
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="olanzapine",
        drug_category=DrugCategory.SPECIAL_GROUP,
        start_date=date(2025, 1, 1),
        flags={"is_olanzapine": True},
    )

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    due_date = add_months(med.start_date, 1)
    one_month = [t for t in tasks if t.due_date == due_date]

    assert any("glucose" in t.test_type.lower() or "hba1c" in t.test_type.lower() for t in one_month)


def test_special_group_nine_month():
    engine = SchedulingEngine()
    patient = build_patient()
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="clozapine",
        drug_category=DrugCategory.SPECIAL_GROUP,
        start_date=date(2025, 1, 1),
        flags={"is_clozapine": True},
    )

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    due_date = add_months(med.start_date, 9)
    nine_month = [t for t in tasks if t.due_date == due_date]

    tests = {t.test_type for t in nine_month}
    assert "Weight/BMI" in tests
    assert "Prolactin" in tests


def test_special_group_glucose_recurring_after_year1():
    engine = SchedulingEngine()
    patient = build_patient()
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="olanzapine",
        drug_category=DrugCategory.SPECIAL_GROUP,
        start_date=date(2025, 1, 1),
        flags={"is_olanzapine": True},
    )

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    recurring = [
        t
        for t in tasks
        if t.due_date > add_months(med.start_date, 12)
        and ("glucose" in t.test_type.lower() or "hba1c" in t.test_type.lower())
    ]

    assert len(recurring) >= 3


def test_chlorpromazine_no_lipids_at_6_months():
    engine = SchedulingEngine()
    patient = build_patient()
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="chlorpromazine",
        drug_category=DrugCategory.SPECIAL_GROUP,
        start_date=date(2025, 1, 1),
        flags={"is_chlorpromazine": True},
    )

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    due_date = add_months(med.start_date, 6)
    six_month = [t for t in tasks if t.due_date == due_date]

    assert not any(t.test_type == "Lipids" for t in six_month)
