from datetime import date
from uuid import uuid4

from hypothesis import given, strategies as st

from backend.config import get_settings
from backend.models.medication import MedicationOrder, DrugCategory
from backend.models.patient import Patient
from backend.services.scheduling import SchedulingEngine, add_months


@given(
    start_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
    category=st.sampled_from([DrugCategory.STANDARD, DrugCategory.SPECIAL_GROUP, DrugCategory.HDAT]),
)
def test_due_dates_not_before_start(start_date, category):
    engine = SchedulingEngine()
    patient = Patient(id=uuid4(), pseudonym="PT-PROP-1")
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="risperidone",
        drug_category=category,
        start_date=start_date,
        flags={"is_hdat": category == DrugCategory.HDAT},
    )

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    for task in tasks:
        assert task.due_date >= start_date


def test_tasks_within_horizon():
    engine = SchedulingEngine()
    settings = get_settings()
    patient = Patient(id=uuid4(), pseudonym="PT-PROP-2")
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="risperidone",
        drug_category=DrugCategory.STANDARD,
        start_date=date(2025, 1, 1),
        flags={},
    )

    tasks = engine.calculate_schedule(med, patient, existing_events=[])
    horizon_end = add_months(med.start_date, settings.SCHEDULING_HORIZON_YEARS * 12)
    assert all(task.due_date <= horizon_end for task in tasks)
