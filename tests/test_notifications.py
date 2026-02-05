from datetime import date, timedelta
from uuid import uuid4

from backend.models.medication import MedicationOrder, DrugCategory
from backend.models.monitoring import MonitoringTask, TaskStatus
from backend.models.notifications import InAppNotification
from backend.models.patient import Patient
from backend.services.notification_engine import NotificationEngine


def test_overdue_notification_dedup(db_session):
    patient = Patient(id=uuid4(), pseudonym="PT-NOTIF-1")
    med = MedicationOrder(
        id=uuid4(),
        patient_id=patient.id,
        drug_name="risperidone",
        drug_category=DrugCategory.STANDARD,
        start_date=date(2025, 1, 1),
        flags={},
    )
    task = MonitoringTask(
        id=uuid4(),
        patient_id=patient.id,
        medication_order_id=med.id,
        test_type="Weight/BMI",
        due_date=date.today() - timedelta(days=5),
        status=TaskStatus.OVERDUE,
    )
    db_session.add_all([patient, med, task])
    db_session.commit()

    engine = NotificationEngine(db_session)
    created_first = engine.process_overdue_tasks()
    created_second = engine.process_overdue_tasks()

    count = db_session.query(InAppNotification).count()
    assert created_first >= 1
    assert created_second == 0
    assert count == 1
