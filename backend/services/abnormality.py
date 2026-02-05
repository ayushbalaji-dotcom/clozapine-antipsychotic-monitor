from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session

from ..models.monitoring import AbnormalFlag, MonitoringEvent, ReviewStatus
from ..models.patient import Patient
from ..models.thresholds import ComparatorType, ReferenceThreshold


_NUMERIC_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*([a-zA-Z%µ/]+)?")


@dataclass
class AbnormalEvaluation:
    flag: AbnormalFlag
    reason: str | None
    threshold_id: str | None
    numeric_value: float | None
    unit: str | None


def _parse_numeric_value(value: str | None) -> tuple[float | None, str | None]:
    if not value:
        return None, None
    match = _NUMERIC_RE.search(str(value))
    if not match:
        return None, None
    try:
        numeric = float(match.group(1))
    except ValueError:
        return None, None
    unit = match.group(2) or None
    return numeric, unit


def _normalize_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    return unit.strip().replace(" ", "")


class ThresholdEvaluator:
    def __init__(self, db: Session):
        self.db = db

    def evaluate_event(self, event: MonitoringEvent, patient: Patient) -> AbnormalEvaluation:
        thresholds = self._get_thresholds(event)
        if not thresholds:
            return AbnormalEvaluation(
                flag=AbnormalFlag.UNKNOWN,
                reason="NO_THRESHOLDS",
                threshold_id=None,
                numeric_value=None,
                unit=None,
            )

        coded_match = self._evaluate_coded(event, thresholds)
        if coded_match is not None:
            return coded_match

        numeric_value, unit = _parse_numeric_value(event.value)
        unit = event.unit or unit
        if numeric_value is None:
            return AbnormalEvaluation(
                flag=AbnormalFlag.UNKNOWN,
                reason="NON_NUMERIC_VALUE",
                threshold_id=None,
                numeric_value=None,
                unit=unit,
            )

        unit_norm = _normalize_unit(unit)
        threshold = self._select_numeric_threshold(thresholds, patient, event, unit_norm)
        if not threshold:
            return AbnormalEvaluation(
                flag=AbnormalFlag.UNKNOWN,
                reason="UNIT_MISMATCH",
                threshold_id=None,
                numeric_value=numeric_value,
                unit=unit_norm,
            )

        flag, reason = self._compare_numeric(threshold, numeric_value)
        return AbnormalEvaluation(
            flag=flag,
            reason=reason,
            threshold_id=str(threshold.id),
            numeric_value=numeric_value,
            unit=unit_norm,
        )

    def apply_evaluation(self, event: MonitoringEvent, evaluation: AbnormalEvaluation) -> None:
        event.abnormal_flag = evaluation.flag
        event.abnormal_reason_code = evaluation.reason
        if evaluation.unit and not event.unit:
            event.unit = evaluation.unit
        if evaluation.flag in {AbnormalFlag.OUTSIDE_WARNING, AbnormalFlag.OUTSIDE_CRITICAL}:
            event.reviewed_status = ReviewStatus.PENDING_REVIEW
        else:
            event.reviewed_status = None
            event.reviewed_by = None
            event.reviewed_at = None

    def _get_thresholds(self, event: MonitoringEvent) -> list[ReferenceThreshold]:
        return (
            self.db.query(ReferenceThreshold)
            .filter(
                ReferenceThreshold.monitoring_type == event.test_type,
                ReferenceThreshold.enabled.is_(True),
            )
            .all()
        )

    def _evaluate_coded(
        self, event: MonitoringEvent, thresholds: Iterable[ReferenceThreshold]
    ) -> AbnormalEvaluation | None:
        interpretation = (event.interpretation or "").strip()
        if not interpretation:
            return None
        interpretation_upper = interpretation.upper()
        for threshold in thresholds:
            if threshold.comparator_type != ComparatorType.CODED:
                continue
            coded_values = threshold.coded_abnormal_values or []
            coded_values_upper = {str(val).upper() for val in coded_values}
            if interpretation_upper in coded_values_upper:
                return AbnormalEvaluation(
                    flag=AbnormalFlag.OUTSIDE_CRITICAL,
                    reason="CODED_ABNORMAL",
                    threshold_id=str(threshold.id),
                    numeric_value=None,
                    unit=None,
                )
        return None

    def _select_numeric_threshold(
        self,
        thresholds: Iterable[ReferenceThreshold],
        patient: Patient,
        event: MonitoringEvent,
        unit: str | None,
    ) -> ReferenceThreshold | None:
        candidates: list[ReferenceThreshold] = []
        for threshold in thresholds:
            if threshold.comparator_type != ComparatorType.NUMERIC:
                continue
            if _normalize_unit(threshold.unit) != unit:
                continue
            if threshold.sex and threshold.sex != patient.sex:
                continue
            if threshold.age_band and threshold.age_band != patient.age_band:
                continue
            if threshold.source_system_scope and threshold.source_system_scope != event.source_system:
                continue
            candidates.append(threshold)

        if not candidates:
            return None

        def _score(threshold: ReferenceThreshold) -> int:
            score = 0
            if threshold.sex:
                score += 2
            if threshold.age_band:
                score += 1
            if threshold.source_system_scope:
                score += 2
            return score

        candidates.sort(key=_score, reverse=True)
        return candidates[0]

    @staticmethod
    def _compare_numeric(threshold: ReferenceThreshold, value: float) -> tuple[AbnormalFlag, str | None]:
        if (
            threshold.low_critical is None
            and threshold.low_warning is None
            and threshold.high_warning is None
            and threshold.high_critical is None
        ):
            return AbnormalFlag.UNKNOWN, "NO_LIMITS"
        if threshold.low_critical is not None and value < threshold.low_critical:
            return AbnormalFlag.OUTSIDE_CRITICAL, "LOW_CRITICAL"
        if threshold.low_warning is not None and value < threshold.low_warning:
            return AbnormalFlag.OUTSIDE_WARNING, "LOW_WARNING"
        if threshold.high_critical is not None and value > threshold.high_critical:
            return AbnormalFlag.OUTSIDE_CRITICAL, "HIGH_CRITICAL"
        if threshold.high_warning is not None and value > threshold.high_warning:
            return AbnormalFlag.OUTSIDE_WARNING, "HIGH_WARNING"
        return AbnormalFlag.NORMAL, None
