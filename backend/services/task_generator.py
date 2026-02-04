from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_sessionmaker
from ..models.monitoring import MonitoringTask, MonitoringEvent, TaskStatus
from ..services.audit_logger import create_audit_event
from ..models.audit import AuditAction
from ..services.scheduling import _matches_test_type


class TaskGenerator:
    def __init__(self, db: Session | None = None):
        self._external_db = db
        settings = get_settings()
        self.window_days = settings.TASK_WINDOW_DAYS

    def _get_db(self) -> Session:
        if self._external_db is not None:
            return self._external_db
        SessionLocal = get_sessionmaker()
        return SessionLocal()

    def create_or_update_tasks(
        self,
        calculated_tasks: Iterable[MonitoringTask],
        actor: str = "SYSTEM",
    ) -> list[MonitoringTask]:
        db = self._get_db()
        created: list[MonitoringTask] = []
        updated: list[MonitoringTask] = []
        try:
            for calc_task in calculated_tasks:
                if calc_task.status is None:
                    calc_task.status = (
                        TaskStatus.OVERDUE if calc_task.due_date < date.today() else TaskStatus.DUE
                    )
                elif isinstance(calc_task.status, str):
                    calc_task.status = TaskStatus(calc_task.status)
                existing = self._find_existing_task(
                    db,
                    patient_id=calc_task.patient_id,
                    medication_order_id=calc_task.medication_order_id,
                    test_type=calc_task.test_type,
                    due_date=calc_task.due_date,
                )
                if existing:
                    if existing.status in {TaskStatus.DONE, TaskStatus.WAIVED}:
                        continue
                    if existing.due_date != calc_task.due_date or existing.status != calc_task.status:
                        existing.due_date = calc_task.due_date
                        existing.status = calc_task.status
                        updated.append(existing)
                        create_audit_event(
                            db,
                            actor=actor,
                            action=AuditAction.UPDATE,
                            entity_type="MonitoringTask",
                            entity_id=str(existing.id),
                            details={"updated": True},
                            request=None,
                            commit=False,
                        )
                else:
                    db.add(calc_task)
                    db.flush()
                    created.append(calc_task)
                    create_audit_event(
                        db,
                        actor=actor,
                        action=AuditAction.UPDATE,
                        entity_type="MonitoringTask",
                        entity_id=str(calc_task.id),
                        details={"created": True},
                        request=None,
                        commit=False,
                    )

            db.commit()
            return created + updated
        finally:
            if self._external_db is None:
                db.close()

    def update_task_statuses(self) -> int:
        db = self._get_db()
        try:
            updated = (
                db.query(MonitoringTask)
                .filter(
                    MonitoringTask.status == TaskStatus.DUE,
                    MonitoringTask.due_date < date.today(),
                )
                .update({"status": TaskStatus.OVERDUE}, synchronize_session=False)
            )
            db.commit()
            return updated
        finally:
            if self._external_db is None:
                db.close()

    def mark_task_done(
        self,
        task_id: UUID,
        completed_by: str,
        monitoring_event: MonitoringEvent,
    ) -> MonitoringTask:
        db = self._get_db()
        try:
            task = db.query(MonitoringTask).filter_by(id=task_id).first()
            if not task:
                raise ValueError("Task not found")
            if task.status == TaskStatus.DONE:
                return task

            task.status = TaskStatus.DONE
            task.completed_at = datetime.combine(
                monitoring_event.performed_date, datetime.min.time(), tzinfo=timezone.utc
            )

            db.add(task)
            create_audit_event(
                db,
                actor=completed_by,
                action=AuditAction.UPDATE,
                entity_type="MonitoringTask",
                entity_id=str(task.id),
                details={"status": "DONE"},
                request=None,
                commit=False,
            )
            db.commit()
            return task
        finally:
            if self._external_db is None:
                db.close()

    def waive_task(
        self,
        task_id: UUID,
        waived_by: str,
        reason: str,
        waived_until: date | None = None,
    ) -> MonitoringTask:
        db = self._get_db()
        try:
            task = db.query(MonitoringTask).filter_by(id=task_id).first()
            if not task:
                raise ValueError("Task not found")
            task.status = TaskStatus.WAIVED
            task.waived_reason = reason
            task.waived_until = waived_until
            db.add(task)
            create_audit_event(
                db,
                actor=waived_by,
                action=AuditAction.WAIVE,
                entity_type="MonitoringTask",
                entity_id=str(task.id),
                details={"reason": reason},
                request=None,
                commit=False,
            )
            db.commit()
            return task
        finally:
            if self._external_db is None:
                db.close()

    def reactivate_expired_waivers(self) -> int:
        db = self._get_db()
        try:
            today = date.today()
            tasks = (
                db.query(MonitoringTask)
                .filter(
                    MonitoringTask.status == TaskStatus.WAIVED,
                    MonitoringTask.waived_until != None,
                    MonitoringTask.waived_until < today,
                )
                .all()
            )
            for task in tasks:
                task.status = TaskStatus.OVERDUE
                task.waived_reason = None
                task.waived_until = None
            db.commit()
            return len(tasks)
        finally:
            if self._external_db is None:
                db.close()

    def auto_complete_tasks_for_event(
        self,
        event: MonitoringEvent,
        actor: str = "SYSTEM",
    ) -> list[MonitoringTask]:
        db = self._get_db()
        completed: list[MonitoringTask] = []
        try:
            window_start = event.performed_date - timedelta(days=self.window_days)
            window_end = event.performed_date + timedelta(days=self.window_days)
            tasks = (
                db.query(MonitoringTask)
                .filter(
                    MonitoringTask.patient_id == event.patient_id,
                    MonitoringTask.status.in_([TaskStatus.DUE, TaskStatus.OVERDUE]),
                )
                .all()
            )
            for task in tasks:
                if not _matches_test_type(task.test_type, event.test_type):
                    continue
                if not (window_start <= task.due_date <= window_end):
                    continue
                task.status = TaskStatus.DONE
                task.completed_at = datetime.combine(
                    event.performed_date, datetime.min.time(), tzinfo=timezone.utc
                )
                completed.append(task)
                create_audit_event(
                    db,
                    actor=actor,
                    action=AuditAction.UPDATE,
                    entity_type="MonitoringTask",
                    entity_id=str(task.id),
                    details={"status": "DONE", "auto_completed": True},
                    request=None,
                    commit=False,
                )
            if completed:
                db.commit()
            return completed
        finally:
            if self._external_db is None:
                db.close()

    def _find_existing_task(
        self,
        db: Session,
        patient_id,
        medication_order_id,
        test_type: str,
        due_date: date,
    ) -> MonitoringTask | None:
        window_start = due_date - timedelta(days=self.window_days)
        window_end = due_date + timedelta(days=self.window_days)
        return (
            db.query(MonitoringTask)
            .filter(
                MonitoringTask.patient_id == patient_id,
                MonitoringTask.medication_order_id == medication_order_id,
                MonitoringTask.test_type == test_type,
                MonitoringTask.due_date >= window_start,
                MonitoringTask.due_date <= window_end,
            )
            .first()
        )
