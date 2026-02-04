from __future__ import annotations

from datetime import date, timedelta

from ..models.medication import MedicationOrder, DrugCategory
from ..models.monitoring import MonitoringTask, TaskStatus
from ..models.patient import Patient


class RuleEvaluator:
    SPC_ECG_REQUIRED = {"haloperidol", "pimozide", "sertindole"}

    def should_require_ecg(self, medication: MedicationOrder, patient: Patient) -> bool:
        drug_lower = (medication.drug_name or "").lower()
        if drug_lower in self.SPC_ECG_REQUIRED:
            return True

        flags = patient.risk_flags
        if not flags:
            return False

        if flags.ecg_indicated:
            return True
        if flags.cv_risk_present:
            return True
        if flags.family_history_cvd:
            return True
        if flags.inpatient_admission:
            return True

        return False

    def apply_clozapine_fbc_schedule(
        self,
        tasks: list[MonitoringTask],
        medication: MedicationOrder,
        horizon_years: int,
    ) -> list[MonitoringTask]:
        flags = medication.flags or {}
        drug_lower = (medication.drug_name or "").lower()
        if not flags.get("is_clozapine") and drug_lower != "clozapine":
            return tasks

        non_fbc_tasks = [task for task in tasks if task.test_type != "FBC"]

        start = medication.start_date
        fbc_tasks: list[MonitoringTask] = []

        # Weekly x 18 weeks (weeks 1-18)
        for week in range(1, 19):
            due_date = start + timedelta(weeks=week)
            fbc_tasks.append(
                MonitoringTask(
                    patient_id=medication.patient_id,
                    medication_order_id=medication.id,
                    test_type="FBC",
                    due_date=due_date,
                    status=TaskStatus.OVERDUE if due_date < date.today() else TaskStatus.DUE,
                )
            )

        # 2-weekly x 34 weeks (17 tasks), starting after week 18
        for i in range(17):
            due_date = start + timedelta(weeks=20) + timedelta(weeks=2 * i)
            fbc_tasks.append(
                MonitoringTask(
                    patient_id=medication.patient_id,
                    medication_order_id=medication.id,
                    test_type="FBC",
                    due_date=due_date,
                    status=TaskStatus.OVERDUE if due_date < date.today() else TaskStatus.DUE,
                )
            )

        # 4-weekly thereafter until horizon
        start_after_weeks = 52
        end_weeks = horizon_years * 52
        current = start_after_weeks
        while current <= end_weeks:
            due_date = start + timedelta(weeks=current)
            fbc_tasks.append(
                MonitoringTask(
                    patient_id=medication.patient_id,
                    medication_order_id=medication.id,
                    test_type="FBC",
                    due_date=due_date,
                    status=TaskStatus.OVERDUE if due_date < date.today() else TaskStatus.DUE,
                )
            )
            current += 4

        return non_fbc_tasks + fbc_tasks

    def apply_hdat_extra_rules(
        self, tasks: list[MonitoringTask], medication: MedicationOrder
    ) -> list[MonitoringTask]:
        flags = medication.flags or {}
        drug_category = medication.drug_category
        if isinstance(drug_category, str):
            drug_category = drug_category.upper()
        if not flags.get("is_hdat") and drug_category != DrugCategory.HDAT and drug_category != "HDAT":
            return tasks

        hydration_task = MonitoringTask(
            patient_id=medication.patient_id,
            medication_order_id=medication.id,
            test_type="Hydration vigilance",
            due_date=medication.start_date,
            status=TaskStatus.ONGOING,
        )
        return tasks + [hydration_task]
