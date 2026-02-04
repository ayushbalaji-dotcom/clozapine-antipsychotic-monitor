from datetime import date, timedelta
from uuid import uuid4

from backend.models.medication import MedicationOrder, DrugCategory
from backend.models.patient import Patient
from backend.services.scheduling import SchedulingEngine


def build_patient():
    return Patient(id=uuid4(), pseudonym="PT-CLOZ-1")


def test_clozapine_weekly_fbc_18_weeks():
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
    end_week_18 = med.start_date + timedelta(weeks=18)
    weekly = [
        t for t in tasks if t.test_type == "FBC" and t.due_date <= end_week_18
    ]

    assert len(weekly) == 18


def test_clozapine_biweekly_17_tasks():
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
    week_18_end = med.start_date + timedelta(weeks=18)
    week_52_end = med.start_date + timedelta(weeks=52)

    biweekly = [
        t
        for t in tasks
        if t.test_type == "FBC" and week_18_end < t.due_date <= week_52_end
    ]

    assert len(biweekly) == 17


def test_clozapine_monthly_after_year1():
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
    week_52_end = med.start_date + timedelta(weeks=52)

    monthly = [
        t for t in tasks if t.test_type == "FBC" and t.due_date > week_52_end
    ]

    assert len(monthly) >= 12
