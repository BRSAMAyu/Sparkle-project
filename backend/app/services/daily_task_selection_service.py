from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.runtime_v1.state import AuroraRuntimeStore
from app.core.cache import cache_service
from app.models.plan import Plan, PlanPriority, PlanStage
from app.models.plan_state import PlanState, PlanStateStatus
from app.models.task import Task, TaskStatus


@dataclass(frozen=True)
class DailyTaskSelection:
    task: Task
    score: float
    reason: str
    signals: dict[str, Any]
    plan: Plan | None = None
    plan_state: PlanState | None = None


@dataclass(frozen=True)
class _TaskCandidate:
    task: Task
    plan: Plan | None = None
    plan_state: PlanState | None = None


def _is_today_relevant(task: Task, today: date) -> bool:
    if task.status in {TaskStatus.IN_PROGRESS, TaskStatus.STUCK}:
        return True
    if task.status == TaskStatus.COMPLETED:
        return task.completed_at is not None and task.completed_at.date() == today
    return task.due_date is None or task.due_date <= today


class DailyTaskSelectionService:
    """Ranks the next executable task from plan, deadline, Aurora, and energy signals."""

    ACTIVE_STATUSES = (TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.STUCK)

    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis if redis is not None else cache_service.redis

    async def select_tasks(
        self,
        *,
        user_id: UUID,
        limit: int = 5,
        include_completed_today: bool = False,
        only_today_relevant: bool = False,
    ) -> list[DailyTaskSelection]:
        today = date.today()
        statuses = list(self.ACTIVE_STATUSES)
        if include_completed_today:
            statuses.append(TaskStatus.COMPLETED)

        result = await self.db.execute(
            select(Task, Plan, PlanState)
            .outerjoin(Plan, Task.plan_id == Plan.id)
            .outerjoin(
                PlanState,
                and_(
                    PlanState.plan_id == Task.plan_id,
                    PlanState.user_id == user_id,
                    PlanState.status == PlanStateStatus.ACTIVE.value,
                ),
            )
            .where(Task.user_id == user_id, Task.status.in_(statuses))
            .where(
                or_(
                    Task.status != TaskStatus.COMPLETED,
                    Task.completed_at.is_not(None),
                )
            )
            .order_by(Task.order_index.asc(), desc(Task.priority), desc(Task.updated_at))
            .limit(max(limit * 4, 20))
        )
        candidates = [_TaskCandidate(task=row[0], plan=row[1], plan_state=row[2]) for row in result.all()]

        if include_completed_today:
            candidates = [
                candidate
                for candidate in candidates
                if candidate.task.status != TaskStatus.COMPLETED
                or (
                    candidate.task.completed_at is not None
                    and candidate.task.completed_at.date() == today
                )
            ]
        if only_today_relevant:
            candidates = [
                candidate
                for candidate in candidates
                if _is_today_relevant(candidate.task, today)
            ]

        aurora = await self._load_aurora_energy(user_id)
        ranked = [
            self.score_candidate(
                candidate.task,
                plan=candidate.plan,
                plan_state=candidate.plan_state,
                aurora=aurora,
                today=today,
            )
            for candidate in candidates
        ]
        ranked.sort(
            key=lambda item: (
                item.task.status == TaskStatus.COMPLETED,
                -item.score,
                item.task.order_index or 0,
                item.task.due_date or date.max,
                item.task.created_at,
            )
        )
        return ranked[:limit]

    async def _load_aurora_energy(self, user_id: UUID) -> dict[str, Any]:
        try:
            energy = await AuroraRuntimeStore(self.redis).load_energy(user_id)
            return {
                "level": energy.current_level,
                "wake_score": float(energy.wake_score or 0.0),
                "cooling_down": bool(energy.is_cooling_down),
            }
        except Exception as exc:
            logger.debug("Daily task selection could not load Aurora energy for {}: {}", user_id, exc)
            return {"level": "L0", "wake_score": 0.0, "cooling_down": False}

    @classmethod
    def score_candidate(
        cls,
        task: Task,
        *,
        plan: Plan | None = None,
        plan_state: PlanState | None = None,
        aurora: dict[str, Any] | None = None,
        today: date | None = None,
    ) -> DailyTaskSelection:
        today = today or date.today()
        aurora = aurora or {}
        score = 0.0
        reasons: list[str] = []
        signals: dict[str, Any] = {}

        status_score = cls._status_score(task.status)
        score += status_score
        signals["status_score"] = status_score
        if task.status == TaskStatus.IN_PROGRESS:
            reasons.append("it is already in motion")
        elif task.status == TaskStatus.STUCK:
            reasons.append("Aurora can help unblock the current stuck point")

        deadline_score, deadline_reason, days_to_due = cls._deadline_score(task, plan, today)
        score += deadline_score
        signals["deadline_score"] = deadline_score
        signals["days_to_due"] = days_to_due
        if deadline_reason:
            reasons.append(deadline_reason)

        plan_score, plan_reason = cls._plan_score(plan, plan_state)
        score += plan_score
        signals["plan_score"] = plan_score
        if plan_reason:
            reasons.append(plan_reason)

        priority_score = min(max(int(task.priority or 0), 0), 5) * 5.0
        score += priority_score
        signals["priority_score"] = priority_score
        if priority_score >= 15:
            reasons.append("it carries high task priority")

        energy_score, energy_reason, target_energy = cls._energy_fit_score(task, aurora)
        score += energy_score
        signals["energy_score"] = energy_score
        signals["target_energy"] = target_energy
        signals["aurora_level"] = aurora.get("level") or "L0"
        signals["aurora_wake_score"] = round(float(aurora.get("wake_score") or 0.0), 3)
        if energy_reason:
            reasons.append(energy_reason)

        duration_score = cls._duration_score(task)
        score += duration_score
        signals["duration_score"] = duration_score

        difficulty_score, difficulty_reason = cls._difficulty_score(task, target_energy)
        score += difficulty_score
        signals["difficulty_score"] = difficulty_score
        if difficulty_reason:
            reasons.append(difficulty_reason)

        if task.status == TaskStatus.COMPLETED:
            score -= 100.0
            reasons = ["already completed today"]

        reason = cls._reason_sentence(reasons)
        signals["score"] = round(score, 3)
        return DailyTaskSelection(
            task=task,
            score=round(score, 3),
            reason=reason,
            signals=signals,
            plan=plan,
            plan_state=plan_state,
        )

    @staticmethod
    def _status_score(status: TaskStatus) -> float:
        if status == TaskStatus.IN_PROGRESS:
            return 38.0
        if status == TaskStatus.STUCK:
            return 28.0
        if status == TaskStatus.PENDING:
            return 16.0
        return 0.0

    @staticmethod
    def _deadline_score(task: Task, plan: Plan | None, today: date) -> tuple[float, str | None, int | None]:
        due_reference = task.due_date or getattr(plan, "target_date", None)
        if due_reference is None:
            return 0.0, None, None
        days = (due_reference - today).days
        if days < 0:
            return 34.0, "it is overdue", days
        if days == 0:
            return 28.0, "it is due today", days
        if days <= 2:
            return 20.0, "its deadline is close", days
        if days <= 7:
            return 10.0, "it protects this week's plan", days
        return 2.0, None, days

    @staticmethod
    def _plan_score(plan: Plan | None, plan_state: PlanState | None) -> tuple[float, str | None]:
        score = 0.0
        reasons: list[str] = []
        if plan is not None:
            score += 8.0
            priority = str(getattr(plan.priority, "value", plan.priority) or "").lower()
            score += {
                PlanPriority.CRITICAL.value: 18.0,
                PlanPriority.HIGH.value: 12.0,
                PlanPriority.NORMAL.value: 6.0,
                PlanPriority.LOW.value: 0.0,
            }.get(priority, 4.0)
            if bool(plan.is_primary):
                score += 12.0
                reasons.append("it belongs to the primary plan")
            stage = getattr(plan.plan_stage, "value", plan.plan_stage)
            if stage == PlanStage.SPRINT.value:
                score += 6.0
                reasons.append("the plan is in sprint mode")

        if plan_state is not None:
            if bool(plan_state.is_focus):
                score += 10.0
                reasons.append("its plan is currently in focus")
            score += min(max(int(plan_state.parallel_priority or 0), 0), 5) * 2.0

        return score, reasons[0] if reasons else None

    @staticmethod
    def _energy_fit_score(task: Task, aurora: dict[str, Any]) -> tuple[float, str | None, int]:
        level = str(aurora.get("level") or "L0").upper()
        wake_score = float(aurora.get("wake_score") or 0.0)
        cooling_down = bool(aurora.get("cooling_down"))

        if cooling_down or level in {"L2", "L3"} or wake_score >= 0.7:
            target = 2
        elif level == "L1" or wake_score >= 0.35:
            target = 3
        else:
            target = 4

        energy_cost = max(1, min(5, int(task.energy_cost or 1)))
        delta = abs(energy_cost - target)
        score = max(0.0, 18.0 - delta * 7.0)
        if energy_cost <= target:
            return score, "it fits the current energy window", target
        return score - 8.0, "it may need a smaller first step if energy dips", target

    @staticmethod
    def _duration_score(task: Task) -> float:
        minutes = int(task.estimated_minutes or 0)
        if 5 <= minutes <= 25:
            return 10.0
        if minutes <= 45:
            return 6.0
        if minutes <= 90:
            return 1.0
        return -6.0

    @staticmethod
    def _difficulty_score(task: Task, target_energy: int) -> tuple[float, str | None]:
        difficulty = max(1, min(5, int(task.difficulty or 1)))
        if difficulty <= target_energy:
            return 8.0, "its difficulty is doable from here"
        if difficulty == target_energy + 1:
            return 0.0, None
        return -8.0, "it is high difficulty, so Sparkle should offer support"

    @staticmethod
    def _reason_sentence(reasons: list[str]) -> str:
        unique = []
        for reason in reasons:
            if reason and reason not in unique:
                unique.append(reason)
        if not unique:
            return "It is the best balanced next step right now."
        if len(unique) == 1:
            return f"Recommended because {unique[0]}."
        return f"Recommended because {unique[0]} and {unique[1]}."
