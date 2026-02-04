from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from ..config import get_settings
from ..models.medication import DrugCategory, MedicationOrder
from ..models.monitoring import MonitoringEvent, MonitoringTask, TaskStatus
from ..models.patient import Patient
from ..rules.rule_loader import load_ruleset
from ..database import get_sessionmaker
from .rule_evaluator import RuleEvaluator


@dataclass
class Milestone:
    name: str
    due_date: date
    tests: list[str]


def add_months(start: date, months: int) -> date:
    """Add months to a date while preserving month-end behavior."""
    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    day = min(start.day, _days_in_month(year, month))
    return date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - timedelta(days=1)).day


def _normalize_test_type(test_type: str) -> str:
    return test_type.strip().lower()


def _matches_test_type(task_type: str, event_type: str) -> bool:
    task_norm = _normalize_test_type(task_type)
    event_norm = _normalize_test_type(event_type)
    if task_norm == event_norm:
        return True
    if "glucose" in task_norm or "hba1c" in task_norm:
        if "glucose" in event_norm or "hba1c" in event_norm:
            return True
    return False


class SchedulingEngine:
    def __init__(self, ruleset_path: str | None = None):
        self.ruleset = load_ruleset(ruleset_path)
        settings = get_settings()
        self.window_days = settings.TASK_WINDOW_DAYS
        self.horizon_years = settings.SCHEDULING_HORIZON_YEARS
        self.evaluator = RuleEvaluator()

    def calculate_schedule(
        self,
        medication: MedicationOrder,
        patient: Patient,
        existing_events: list[MonitoringEvent] | None = None,
    ) -> list[MonitoringTask]:
        category = self._determine_category(medication)
        category_rules = self.ruleset["categories"].get(category)
        if not category_rules:
            raise ValueError(f"No rules defined for category: {category}")

        ecg_required = self.evaluator.should_require_ecg(medication, patient)

        milestones = self._build_milestones(medication, category_rules)

        events = self._load_events(patient.id) if existing_events is None else list(existing_events)

        tasks: list[MonitoringTask] = []
        for milestone in milestones:
            tasks.extend(
                self._generate_milestone_tasks(
                    medication=medication,
                    patient=patient,
                    milestone=milestone,
                    existing_events=events,
                    ecg_required=ecg_required,
                )
            )

        tasks = self.evaluator.apply_clozapine_fbc_schedule(tasks, medication, self.horizon_years)
        tasks = self.evaluator.apply_hdat_extra_rules(tasks, medication)

        tasks = self._dedupe(tasks)

        if medication.stop_date:
            tasks = [task for task in tasks if task.due_date <= medication.stop_date]

        tasks.sort(key=lambda t: (t.due_date, t.test_type))
        return tasks

    def _determine_category(self, medication: MedicationOrder) -> str:
        flags = medication.flags or {}
        drug_category = medication.drug_category
        if isinstance(drug_category, str):
            if drug_category.upper() == DrugCategory.HDAT.value:
                drug_category = DrugCategory.HDAT
            elif drug_category.upper() == DrugCategory.SPECIAL_GROUP.value:
                drug_category = DrugCategory.SPECIAL_GROUP
            else:
                drug_category = DrugCategory.STANDARD

        if flags.get("is_hdat") or drug_category == DrugCategory.HDAT:
            return DrugCategory.HDAT.value
        drug_lower = (medication.drug_name or "").lower()
        if drug_lower in ["chlorpromazine", "clozapine", "olanzapine"]:
            return DrugCategory.SPECIAL_GROUP.value
        if drug_category == DrugCategory.SPECIAL_GROUP:
            return DrugCategory.SPECIAL_GROUP.value
        return DrugCategory.STANDARD.value

    def _build_milestones(self, medication: MedicationOrder, category_rules: dict) -> list[Milestone]:
        start = medication.start_date
        drug_lower = (medication.drug_name or "").lower()
        milestones: list[Milestone] = []

        baseline_tests = list(category_rules.get("baseline", []))
        if baseline_tests:
            milestones.append(Milestone(name="baseline", due_date=start, tests=baseline_tests))

        weekly = category_rules.get("weekly")
        if weekly:
            count = weekly.get("count", 0)
            interval_weeks = weekly.get("interval_weeks", 1)
            tests = weekly.get("tests", [])
            for i in range(count):
                due_date = start + timedelta(weeks=(i + 1) * interval_weeks)
                milestones.append(
                    Milestone(name=f"week-{i + 1}", due_date=due_date, tests=list(tests))
                )

        for milestone in category_rules.get("milestones", []):
            months = milestone.get("months")
            tests = list(milestone.get("tests", []))
            exceptions = milestone.get("exceptions", {})
            if drug_lower in exceptions:
                for remove_test in exceptions[drug_lower].get("remove_tests", []):
                    tests = [t for t in tests if t != remove_test]
            due_date = add_months(start, months)
            milestones.append(
                Milestone(name=f"month-{months}", due_date=due_date, tests=tests)
            )

        annual = category_rules.get("annual")
        if annual:
            for year in range(2, self.horizon_years + 1):
                due_date = add_months(start, 12 * year)
                milestones.append(
                    Milestone(name=f"annual-year-{year}", due_date=due_date, tests=list(annual["tests"]))
                )

        if category_rules.get("every_4_6_months"):
            interval_months = 5
            start_months = 16
            current = start_months
            while current <= self.horizon_years * 12:
                due_date = add_months(start, current)
                milestones.append(
                    Milestone(
                        name=f"glucose-{current}mo",
                        due_date=due_date,
                        tests=list(category_rules["every_4_6_months"]["tests"]),
                    )
                )
                current += interval_months

        if category_rules.get("every_3_months"):
            current = 15
            while current <= self.horizon_years * 12:
                due_date = add_months(start, current)
                milestones.append(
                    Milestone(
                        name=f"quarter-{current}mo",
                        due_date=due_date,
                        tests=list(category_rules["every_3_months"]["tests"]),
                    )
                )
                current += 3

        if category_rules.get("every_6_months"):
            current = 18
            while current <= self.horizon_years * 12:
                due_date = add_months(start, current)
                milestones.append(
                    Milestone(
                        name=f"semiannual-{current}mo",
                        due_date=due_date,
                        tests=list(category_rules["every_6_months"]["tests"]),
                    )
                )
                current += 6

        return milestones

    def _generate_milestone_tasks(
        self,
        medication: MedicationOrder,
        patient: Patient,
        milestone: Milestone,
        existing_events: Iterable[MonitoringEvent],
        ecg_required: bool,
    ) -> list[MonitoringTask]:
        tasks: list[MonitoringTask] = []
        for test_type in milestone.tests:
            if test_type == "ECG_if_indicated":
                if not ecg_required:
                    continue
                test_type = "ECG"

            event = self._check_event_exists(
                patient_id=patient.id,
                test_type=test_type,
                due_date=milestone.due_date,
                window_days=self.window_days,
                existing_events=existing_events,
            )

            if event:
                status = TaskStatus.DONE
                completed_at = datetime.combine(
                    event.performed_date, datetime.min.time(), tzinfo=timezone.utc
                )
            else:
                status = TaskStatus.OVERDUE if milestone.due_date < date.today() else TaskStatus.DUE
                completed_at = None

            task = MonitoringTask(
                patient_id=patient.id,
                medication_order_id=medication.id,
                test_type=test_type,
                due_date=milestone.due_date,
                status=status,
                completed_at=completed_at,
            )
            tasks.append(task)
        return tasks

    def _check_event_exists(
        self,
        patient_id,
        test_type: str,
        due_date: date,
        window_days: int,
        existing_events: Iterable[MonitoringEvent],
    ) -> MonitoringEvent | None:
        window_start = due_date - timedelta(days=window_days)
        window_end = due_date + timedelta(days=window_days)

        for event in existing_events:
            if event.patient_id != patient_id:
                continue
            if not _matches_test_type(test_type, event.test_type):
                continue
            if window_start <= event.performed_date <= window_end:
                return event
        return None

    def _load_events(self, patient_id) -> list[MonitoringEvent]:
        SessionLocal = get_sessionmaker()
        db = SessionLocal()
        try:
            return list(db.query(MonitoringEvent).filter(MonitoringEvent.patient_id == patient_id).all())
        finally:
            db.close()

    def _dedupe(self, tasks: list[MonitoringTask]) -> list[MonitoringTask]:
        seen: set[tuple[str, date, str]] = set()
        deduped: list[MonitoringTask] = []
        for task in tasks:
            key = (task.test_type, task.due_date, str(task.medication_order_id))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(task)
        return deduped


def calculate_monitoring_schedule(
    medication: MedicationOrder,
    patient: Patient | None = None,
    existing_events: list[MonitoringEvent] | None = None,
) -> list[MonitoringTask]:
    if patient is None:
        raise ValueError("patient is required")
    engine = SchedulingEngine()
    return engine.calculate_schedule(medication, patient, existing_events=existing_events)
