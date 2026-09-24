"""
PlanProgressService - Plan health evaluation and progress diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.models.task_feedback import TaskFeedback, TaskFeedbackCategory
from app.services.plan_state_service import PlanStateService


@dataclass
class PlanHealthReport:
    plan_id: UUID
    user_id: UUID
    status: str
    severity: str
    health_score: float | None = None
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    requires_adjustment: bool = False
    recommended_action: str = "none"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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
    # WT313 · comeback「离开」维度：与 mobile plan_staleness.dart 的
    # kPlanComebackStaleDays = 3 同口径（一个周末+周一 ≈ 离开数日）。
    # 字段先落地作为服务端真源可选依据，mobile 消费后续卡接。
    INACTIVITY_STALE_DAYS = 3

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
                health_score=None,
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
        avg_overrun = round(sum(ratio_samples) / len(ratio_samples), 2) if ratio_samples else None
        overrun_count = sum(1 for ratio in ratio_samples if ratio >= self.OVERRUN_RATIO_WARN)
        severe_overrun_count = sum(1 for ratio in ratio_samples if ratio >= self.OVERRUN_RATIO_CRITICAL)

        feedback_stats = await self._get_feedback_stats(user_id, plan_id)

        plan = await self._get_plan(user_id, plan_id)
        time_progress = self._compute_time_progress(plan)
        days_since_last_activity = await self._compute_days_since_last_activity(plan)

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
        # WT313 · comeback「离开」维度：仍有未完成任务的活跃计划停摆超阈值
        # → 显式 reason（全完成计划走完成流，不判离开）。
        if (
            days_since_last_activity is not None
            and days_since_last_activity >= self.INACTIVITY_STALE_DAYS
            and completion_rate < 1.0
        ):
            reasons.append("days_since_last_activity")

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
            "days_since_last_activity": days_since_last_activity,
        }
        health_score = self._compute_health_score(
            severity=severity,
            lag=lag,
            avg_overrun=avg_overrun,
            overrun_count=overrun_count,
            severe_overrun_count=severe_overrun_count,
            feedback_stats=feedback_stats,
        )
        metrics["health_score"] = health_score

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
            health_score=health_score,
            reasons=reasons,
            metrics=metrics,
            requires_adjustment=bool(reasons),
            recommended_action=recommended_action,
        )

    def _compute_health_score(
        self,
        *,
        severity: str,
        lag: float | None,
        avg_overrun: float | None,
        overrun_count: int,
        severe_overrun_count: int,
        feedback_stats: dict[str, int],
    ) -> float:
        score = 1.0
        if lag is not None and lag > 0:
            score -= min(0.45, (lag / self.PROGRESS_LAG_CRITICAL) * 0.45)
        if avg_overrun is not None and avg_overrun > 1.0:
            overrun_span = self.OVERRUN_RATIO_CRITICAL - 1.0
            score -= min(0.25, ((avg_overrun - 1.0) / overrun_span) * 0.25)
        if overrun_count > 0:
            score -= min(0.15, (overrun_count / self.OVERRUN_COUNT_CRITICAL) * 0.15)
        if severe_overrun_count > 0:
            score -= min(0.10, (severe_overrun_count / self.OVERRUN_COUNT_CRITICAL) * 0.10)

        friction_count = sum(int(value or 0) for value in feedback_stats.values())
        if friction_count > 0:
            score -= min(0.25, (friction_count / (self.FEEDBACK_COUNT_THRESHOLD + 1)) * 0.25)

        if severity == "critical":
            score = min(score, 0.49)
        elif severity == "warning":
            score = min(score, 0.79)

        return round(min(1.0, max(0.0, score)), 2)

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
            select(TaskFeedback.category)
            .join(Task, Task.id == TaskFeedback.task_id)
            .where(
                Task.plan_id == plan_id,
                Task.user_id == user_id,
            )
            .order_by(TaskFeedback.created_at.desc())
            .limit(self.feedback_window)
        )
        categories = list(result.scalars().all())
        stats = {
            "too_difficult": 0,
            "too_easy": 0,
            "too_long": 0,
            "too_short": 0,
        }
        for category in categories:
            if category == TaskFeedbackCategory.TOO_DIFFICULT.value:
                stats["too_difficult"] += 1
            elif category == TaskFeedbackCategory.TOO_EASY.value:
                stats["too_easy"] += 1
            elif category == TaskFeedbackCategory.TOO_LONG.value:
                stats["too_long"] += 1
            elif category == TaskFeedbackCategory.TOO_SHORT.value:
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
        elapsed_days = (_utcnow().date() - plan.created_at.date()).days
        return min(1.0, max(0.0, elapsed_days / total_days))

    async def _compute_days_since_last_activity(self, plan: Plan | None) -> int | None:
        """WT313 · comeback「离开」维度：距最后一次活动信号的整日数。

        活动信号与 mobile PlanStaleness.resolveLastActivityAt 同口径：
        plan.updated_at 与已完成任务的 updated_at 取最大（plan.updated_at 可能
        被服务端进度重算噪音提前，取最大只放宽、不收紧——宁可少报离开）。
        仅对活跃计划计算；归档计划与数据不足时返回 None（可选依据，不硬造数）。
        """
        if plan is None or not plan.is_active:
            return None
        last_activity = plan.updated_at
        result = await self.db.execute(
            select(func.max(Task.updated_at)).where(
                and_(
                    Task.plan_id == plan.id,
                    Task.user_id == plan.user_id,
                    Task.status == TaskStatus.COMPLETED,
                )
            )
        )
        latest_completed = result.scalar_one_or_none()
        if latest_completed is not None and (last_activity is None or latest_completed > last_activity):
            last_activity = latest_completed
        if last_activity is None:
            last_activity = plan.created_at
        if last_activity is None:
            return None
        return max(0, (_utcnow().date() - last_activity.date()).days)
