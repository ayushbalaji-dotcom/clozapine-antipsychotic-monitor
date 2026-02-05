from datetime import date
from uuid import uuid4

from backend.models.patient import Patient
from backend.models.monitoring import MonitoringEvent, AbnormalFlag
from backend.models.thresholds import ReferenceThreshold, ComparatorType
from backend.services.abnormality import ThresholdEvaluator


def _seed_patient(db):
    patient = Patient(id=uuid4(), pseudonym="PT-ABN-1", sex="F", age_band="35-44")
    db.add(patient)
    db.commit()
    return patient


def test_numeric_threshold_evaluation(db_session):
    patient = _seed_patient(db_session)
    threshold = ReferenceThreshold(
        monitoring_type="HbA1c",
        unit="%",
        comparator_type=ComparatorType.NUMERIC,
        low_warning=4.0,
        high_warning=6.0,
        high_critical=7.0,
    )
    db_session.add(threshold)
    db_session.commit()

    event = MonitoringEvent(
        id=uuid4(),
        patient_id=patient.id,
        test_type="HbA1c",
        performed_date=date.today(),
        value="7.5",
        unit="%",
        source_system="CSV_UPLOAD",
    )
    db_session.add(event)
    db_session.commit()

    evaluator = ThresholdEvaluator(db_session)
    evaluation = evaluator.evaluate_event(event, patient)
    assert evaluation.flag == AbnormalFlag.OUTSIDE_CRITICAL


def test_unit_mismatch_unknown(db_session):
    patient = _seed_patient(db_session)
    threshold = ReferenceThreshold(
        monitoring_type="Creatinine",
        unit="mmol/L",
        comparator_type=ComparatorType.NUMERIC,
        high_warning=120.0,
    )
    db_session.add(threshold)
    db_session.commit()

    event = MonitoringEvent(
        id=uuid4(),
        patient_id=patient.id,
        test_type="Creatinine",
        performed_date=date.today(),
        value="110",
        unit="mg/dL",
        source_system="CSV_UPLOAD",
    )
    db_session.add(event)
    db_session.commit()

    evaluator = ThresholdEvaluator(db_session)
    evaluation = evaluator.evaluate_event(event, patient)
    assert evaluation.flag == AbnormalFlag.UNKNOWN
    assert evaluation.reason == "UNIT_MISMATCH"


def test_coded_abnormal_critical(db_session):
    patient = _seed_patient(db_session)
    threshold = ReferenceThreshold(
        monitoring_type="ECG",
        unit="ms",
        comparator_type=ComparatorType.CODED,
        coded_abnormal_values=["ABNORMAL", "CRITICAL"],
    )
    db_session.add(threshold)
    db_session.commit()

    event = MonitoringEvent(
        id=uuid4(),
        patient_id=patient.id,
        test_type="ECG",
        performed_date=date.today(),
        value="",
        interpretation="ABNORMAL",
        source_system="CSV_UPLOAD",
    )
    db_session.add(event)
    db_session.commit()

    evaluator = ThresholdEvaluator(db_session)
    evaluation = evaluator.evaluate_event(event, patient)
    assert evaluation.flag == AbnormalFlag.OUTSIDE_CRITICAL
