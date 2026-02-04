from datetime import date, timedelta
import os
import random
from faker import Faker
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import SessionLocal, init_db
from backend.models.patient import Patient
from backend.models.medication import MedicationOrder, DrugCategory
from backend.models.monitoring import MonitoringEvent

fake = Faker("en_GB")

DRUG_NAMES = {
    DrugCategory.STANDARD: ["haloperidol", "risperidone", "quetiapine", "aripiprazole"],
    DrugCategory.SPECIAL_GROUP: ["chlorpromazine", "clozapine", "olanzapine"],
}

TEST_TYPES = [
    "Weight/BMI",
    "HbA1c",
    "Fasting glucose",
    "Prolactin",
    "Lipids",
    "BP",
    "Pulse",
    "ECG",
    "FBC",
    "U&Es",
    "LFTs",
    "Waist circumference",
]


def generate_synthetic_patients(db: Session, count: int = 100) -> None:
    for _ in range(count):
        patient = Patient(
            nhs_number=fake.bothify(text="##########"),
            mrn=fake.bothify(text="MRN######"),
            pseudonym=f"PT-{fake.bothify(text='???###')}",
        )
        db.add(patient)
        db.flush()

        for _ in range(random.randint(1, 3)):
            drug_category = random.choice(list(DRUG_NAMES.keys()))
            drug_name = random.choice(DRUG_NAMES[drug_category])
            start_date = fake.date_between(start_date="-2y", end_date="today")
            stop_date = None
            if random.random() < 0.3:
                stop_date = fake.date_between(start_date=start_date, end_date="today")

            med = MedicationOrder(
                patient_id=patient.id,
                drug_name=drug_name,
                drug_category=drug_category,
                start_date=start_date,
                stop_date=stop_date,
                dose=f"{random.randint(1, 20)}mg",
                route="PO",
                frequency="OD",
                flags={
                    "is_clozapine": drug_name == "clozapine",
                    "is_olanzapine": drug_name == "olanzapine",
                    "is_chlorpromazine": drug_name == "chlorpromazine",
                    "is_hdat": random.random() < 0.1,
                },
            )
            db.add(med)
            db.flush()

            # Create synthetic monitoring events (50-80% compliance)
            compliance_rate = random.uniform(0.5, 0.8)
            for test_type in random.sample(TEST_TYPES, k=random.randint(4, 8)):
                if random.random() < compliance_rate:
                    performed = fake.date_between(start_date=start_date, end_date="today")
                    event = MonitoringEvent(
                        patient_id=patient.id,
                        medication_order_id=med.id,
                        test_type=test_type,
                        performed_date=performed,
                        source_system="SYNTHETIC_EPR",
                    )
                    db.add(event)

    db.commit()


if __name__ == "__main__":
    settings = get_settings()
    if settings.ENVIRONMENT != "dev" or not settings.SYNTHETIC_DATA_MODE:
        raise SystemExit("Synthetic data generation is only permitted in dev with SYNTHETIC_DATA_MODE=true")

    init_db()
    db = SessionLocal()
    try:
        generate_synthetic_patients(db, count=100)
    finally:
        db.close()

    print("Synthetic data generation complete")
