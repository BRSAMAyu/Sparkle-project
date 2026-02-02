"""
PlanProgressService - Plan health evaluation and progress diagnostics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.models.task import Task
from app.models.task_feedback import TaskFeedback, TaskFeedbackCategory
from app.services.plan_state_service import PlanStateService


@dataclass
class PlanHealthReport:
    plan_id: UUID
    user_id: UUID
    status: str
    severity: str
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    requires_adjustment: bool = False
    recommended_action: str = "none"


class PlanProgressService:
    """
    Evaluate plan health based on execution data and feedback.
    """

    OVERRUN_RATIO_WARN = 1.3
    OVERRUN_RATIO_CRITICAL = 1.6
    OVERRUN_COUNT_WARN = 3
    OVERRUN_COUNT_CRITICAL = 4
    PROGRESS_LAG_WARN = 0.25
    PROGRESS_LAG_CRITICAL = 0.4
    FEEDBACK_COUNT_THRESHOLD = 3

    def __init__(
        self,
        db: AsyncSession,
        redis=None,
        summary_window: int = 10,
        feedback_window: int = 10,
    ) -> None:
        self.db = db
        self.redis = redis
        self.summary_window = summary_window
        self.feedback_window = feedback_window
        self._plan_state_service = PlanStateService(db, redis)

    async def evaluate_progress(self, user_id: UUID, plan_id: UUID) -> PlanHealthReport:
        state = await self._plan_state_service.get_plan_state(user_id, plan_id)
        if not state:
            return PlanHealthReport(
                plan_id=plan_id,
                user_id=user_id,
                status="unknown",
                severity="unknown",
                reasons=["missing_plan_state"],
                metrics={},
                requires_adjustment=False,
                recommended_action="none",
            )

        task_index = state.task_index or {}
        completed = task_index.get("completed", 0)
        total = task_index.get("total", 0)
        completion_rate = task_index.get("avg_completion_rate")
        if completion_rate is None:
            completion_rate = (completed / total) if total else 0.0
        else:
            try:
                completion_rate = float(completion_rate)
            except Exception:
                completion_rate = (completed / total) if total else 0.0

        summaries = (state.task_summaries or [])[: self.summary_window]
        ratio_samples = self._compute_completion_ratios(summaries)
        avg_overrun = (
            round(sum(ratio_samples) / len(ratio_samples), 2) if ratio_samples else None
        )
        overrun_count = sum(1 for ratio in ratio_samples if ratio >= self.OVERRUN_RATIO_WARN)
        severe_overrun_count = sum(
            1 for ratio in ratio_samples if ratio >= self.OVERRUN_RATIO_CRITICAL
        )

        feedback_stats = await self._get_feedback_stats(user_id, plan_id)

        plan = await self._get_plan(user_id, plan_id)
        time_progress = self._compute_time_progress(plan)

        reasons: list[str] = []
        if overrun_count >= self.OVERRUN_COUNT_WARN:
            reasons.append("time_overrun")
        if feedback_stats.get("too_difficult", 0) >= self.FEEDBACK_COUNT_THRESHOLD:
            reasons.append("difficulty_too_hard")
        if feedback_stats.get("too_easy", 0) >= self.FEEDBACK_COUNT_THRESHOLD:
            reasons.append("difficulty_too_easy")
        if time_progress is not None:
            lag = time_progress - completion_rate
            if lag >= self.PROGRESS_LAG_WARN:
                reasons.append("progress_lag")

        severity = "healthy"
        recommended_action = "none"
        if reasons:
            severity = "warning"
            recommended_action = "adjust"

        lag = None
        if time_progress is not None:
            lag = time_progress - completion_rate

        if (
            severe_overrun_count >= self.OVERRUN_COUNT_CRITICAL
            or (lag is not None and lag >= self.PROGRESS_LAG_CRITICAL)
            or feedback_stats.get("too_difficult", 0) >= self.FEEDBACK_COUNT_THRESHOLD + 1
        ):
            severity = "critical"
            recommended_action = "replan"

        metrics = {
            "completion_rate": completion_rate,
            "tasks_completed": completed,
            "tasks_total": total,
            "avg_overrun": avg_overrun,
            "overrun_count": overrun_count,
            "severe_overrun_count": severe_overrun_count,
            "feedback_stats": feedback_stats,
            "time_progress": time_progress,
            "progress_lag": lag,
        }

        if reasons:
            logger.info(
                "Plan health alert: plan_id={}, reasons={}, severity={}",
                plan_id,
                reasons,
                severity,
            )

        return PlanHealthReport(
            plan_id=plan_id,
            user_id=user_id,
            status="active",
            severity=severity,
            reasons=reasons,
            metrics=metrics,
            requires_adjustment=bool(reasons),
            recommended_action=recommended_action,
        )

    def _compute_completion_ratios(self, summaries: list[dict[str, Any]]) -> list[float]:
        ratios = []
        for summary in summaries:
            estimated = summary.get("estimated_minutes")
            actual = summary.get("actual_minutes")
            if estimated and actual:
                try:
                    ratios.append(float(actual) / float(estimated))
                except Exception:
                    continue
        return ratios

    async def _get_feedback_stats(self, user_id: UUID, plan_id: UUID) -> dict[str, int]:
        result = await self.db.execute(
            select(TaskFeedback)
            .join(Task, Task.id == TaskFeedback.task_id)
            .where(
                Task.plan_id == plan_id,
                Task.user_id == user_id,
            )
            .order_by(TaskFeedback.created_at.desc())
            .limit(self.feedback_window)
        )
        feedbacks = list(result.scalars().all())
        stats = {
            "too_difficult": 0,
            "too_easy": 0,
            "too_long": 0,
            "too_short": 0,
        }
        for feedback in feedbacks:
            if feedback.category == TaskFeedbackCategory.TOO_DIFFICULT.value:
                stats["too_difficult"] += 1
            elif feedback.category == TaskFeedbackCategory.TOO_EASY.value:
                stats["too_easy"] += 1
            elif feedback.category == TaskFeedbackCategory.TOO_LONG.value:
                stats["too_long"] += 1
            elif feedback.category == TaskFeedbackCategory.TOO_SHORT.value:
                stats["too_short"] += 1
        return stats

    async def _get_plan(self, user_id: UUID, plan_id: UUID) -> Plan | None:
        result = await self.db.execute(
            select(Plan).where(
                Plan.id == plan_id,
                Plan.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    def _compute_time_progress(self, plan: Plan | None) -> float | None:
        if not plan or not plan.target_date or not plan.created_at:
            return None
        total_days = (plan.target_date - plan.created_at.date()).days
        if total_days <= 0:
            return None
        elapsed_days = (datetime.utcnow().date() - plan.created_at.date()).days
        return min(1.0, max(0.0, elapsed_days / total_days))
