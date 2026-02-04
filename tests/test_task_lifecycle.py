from datetime import date, timedelta
from uuid import uuid4

from backend.models.patient import Patient
from backend.models.medication import MedicationOrder, DrugCategory
from backend.models.monitoring import MonitoringTask, MonitoringEvent, TaskStatus
from backend.services.task_generator import TaskGenerator


def seed_patient_and_med(db):
    patient = Patient(id=uuid4(), pseudonym="PT-TASK-1")
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="risperidone",
        drug_category=DrugCategory.STANDARD,
        start_date=date(2025, 1, 1),
        flags={},
    )
    db.add(patient)
    db.add(med)
    db.commit()
    return patient, med


def test_task_due_to_overdue(db_session):
    patient, med = seed_patient_and_med(db_session)
    task = MonitoringTask(
        id=uuid4(),
        patient_id=patient.id,
        medication_order_id=med.id,
        test_type="Weight/BMI",
        due_date=date.today() - timedelta(days=1),
        status=TaskStatus.DUE,
    )
    db_session.add(task)
    db_session.commit()

    generator = TaskGenerator(db_session)
    updated = generator.update_task_statuses()
    assert updated == 1

    refreshed = db_session.get(MonitoringTask, task.id)
    assert refreshed.status == TaskStatus.OVERDUE


def test_mark_task_done(db_session):
    patient, med = seed_patient_and_med(db_session)
    task = MonitoringTask(
        id=uuid4(),
        patient_id=patient.id,
        medication_order_id=med.id,
        test_type="HbA1c",
        due_date=date(2025, 4, 1),
        status=TaskStatus.OVERDUE,
    )
    event = MonitoringEvent(
        id=uuid4(),
        patient_id=patient.id,
        medication_order_id=med.id,
        test_type="HbA1c",
        performed_date=date(2025, 4, 5),
        source_system="TEST",
    )
    db_session.add(task)
    db_session.add(event)
    db_session.commit()

    generator = TaskGenerator(db_session)
    completed = generator.mark_task_done(task.id, "clinician-1", event)
    assert completed.status == TaskStatus.DONE


def test_waive_and_reactivate(db_session):
    patient, med = seed_patient_and_med(db_session)
    task = MonitoringTask(
        id=uuid4(),
        patient_id=patient.id,
        medication_order_id=med.id,
        test_type="Prolactin",
        due_date=date(2025, 3, 1),
        status=TaskStatus.OVERDUE,
    )
    db_session.add(task)
    db_session.commit()

    generator = TaskGenerator(db_session)
    waived = generator.waive_task(
        task.id, "senior-1", "Patient declined", date.today() - timedelta(days=1)
    )
    assert waived.status == TaskStatus.WAIVED

    reactivated = generator.reactivate_expired_waivers()
    assert reactivated == 1
    refreshed = db_session.get(MonitoringTask, task.id)
    assert refreshed.status == TaskStatus.OVERDUE


def test_no_duplicate_tasks(db_session):
    patient, med = seed_patient_and_med(db_session)
    generator = TaskGenerator(db_session)

    task = MonitoringTask(
        id=uuid4(),
        patient_id=patient.id,
        medication_order_id=med.id,
        test_type="Weight/BMI",
        due_date=date(2025, 1, 1),
        status=TaskStatus.DUE,
    )
    generator.create_or_update_tasks([task])
    generator.create_or_update_tasks([task])

    count = db_session.query(MonitoringTask).filter_by(medication_order_id=med.id).count()
    assert count == 1
