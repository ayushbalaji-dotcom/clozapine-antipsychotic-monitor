from datetime import date
from uuid import uuid4

from backend.models.medication import MedicationOrder, DrugCategory
from backend.models.patient import Patient
from backend.services.scheduling import SchedulingEngine, add_months


def test_no_tasks_after_stop_date():
    engine = SchedulingEngine()
    patient = Patient(id=uuid4(), pseudonym="PT-STOP-1")
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="risperidone",
        drug_category=DrugCategory.STANDARD,
        start_date=date(2025, 1, 1),
        stop_date=date(2025, 4, 1),
        flags={},
    )

    tasks = engine.calculate_schedule(med, patient, existing_events=[])

    assert any(t.due_date == med.start_date for t in tasks)
    three_month = add_months(med.start_date, 3)
    assert any(t.due_date == three_month for t in tasks)

    six_month = add_months(med.start_date, 6)
    assert not any(t.due_date >= six_month for t in tasks)


def test_null_stop_date_generates_future():
    engine = SchedulingEngine()
    patient = Patient(id=uuid4(), pseudonym="PT-STOP-2")
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="aripiprazole",
        drug_category=DrugCategory.STANDARD,
        start_date=date(2025, 1, 1),
        stop_date=None,
        flags={},
    )

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    assert any(t.due_date > date(2026, 1, 1) for t in tasks)
