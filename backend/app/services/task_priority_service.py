from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import CacheService, cache_service
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.plan import Plan
from app.models.plan_state import PlanState, PlanStateStatus
from app.models.task import Task, TaskStatus, TaskType
from app.services.daily_task_selection_service import DailyTaskSelectionService


class PrioritySignal(BaseModel):
    type: str
    weight: float = Field(ge=0.0, le=1.0)
    detail: str
    raw_score: float | None = None


class AlternativeOptionSkipped(BaseModel):
    task_id: str
    title: str
    score: float
    reason: str


class PriorityReasoning(BaseModel):
    task_id: str
    generated_at: datetime
    task_updated_at: datetime | None = None
    selected_score: float
    primary_reason: str
    supporting_signals: list[PrioritySignal]
    alternative_options_skipped: list[AlternativeOptionSkipped]


class TaskPriorityService:
    """Builds transparent "why this today" reasoning from task ranking signals."""

    CACHE_TTL_SECONDS = 10 * 60
    ACTIVE_STATUSES = (TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.STUCK)

    def __init__(
        self,
        db: AsyncSession,
        cache: CacheService | None = None,
        redis=None,
    ) -> None:
        self.db = db
        self.cache = cache or cache_service
        self.redis = redis if redis is not None else self.cache.redis

    @staticmethod
    def cache_key(user_id: UUID, task_id: UUID) -> str:
        return f"task_priority_reasoning:{user_id}:{task_id}"

    async def get_cached_reasoning(
        self,
        *,
        user_id: UUID,
        task: Task,
    ) -> dict[str, Any] | None:
        cached = await self.cache.get(self.cache_key(user_id, task.id))
        if not isinstance(cached, dict):
            return None

        cached_updated_at = cached.get("task_updated_at")
        task_updated_at = self._iso_or_none(task.updated_at)
        if cached_updated_at != task_updated_at:
            return None
        return cached

    async def generate_and_cache(
        self,
        *,
        user_id: UUID,
        task_id: UUID,
    ) -> PriorityReasoning:
        reasoning = await self.generate_priority_reasoning(user_id=user_id, task_id=task_id)
        await self.cache.set(
            self.cache_key(user_id, task_id),
            reasoning.model_dump(mode="json"),
            ttl=self.CACHE_TTL_SECONDS,
        )
        return reasoning

    async def generate_priority_reasoning(
        self,
        *,
        user_id: UUID,
        task_id: UUID,
        alternatives_limit: int = 3,
    ) -> PriorityReasoning:
        task, plan, plan_state = await self._load_task_context(user_id=user_id, task_id=task_id)
        selector = DailyTaskSelectionService(self.db, self.redis)
        aurora = await selector._load_aurora_energy(user_id)
        today = date.today()
        selected = DailyTaskSelectionService.score_candidate(
            task,
            plan=plan,
            plan_state=plan_state,
            aurora=aurora,
            today=today,
        )
        node, node_status = await self._load_node_context(user_id=user_id, task=task)
        signals = self._build_supporting_signals(
            task=task,
            plan=plan,
            plan_state=plan_state,
            node=node,
            node_status=node_status,
            ranking_signals=selected.signals,
            aurora=aurora,
            today=today,
        )
        alternatives = await self._build_alternative_options(
            user_id=user_id,
            selected_task=task,
            selected_score=selected.score,
            aurora=aurora,
            today=today,
            limit=alternatives_limit,
        )

        return PriorityReasoning(
            task_id=str(task.id),
            generated_at=datetime.now(UTC),
            task_updated_at=task.updated_at,
            selected_score=selected.score,
            primary_reason=self._primary_reason(
                task=task,
                selection_reason=selected.reason,
                node=node,
                node_status=node_status,
                today=today,
            ),
            supporting_signals=signals,
            alternative_options_skipped=alternatives,
        )

    async def _load_task_context(
        self,
        *,
        user_id: UUID,
        task_id: UUID,
    ) -> tuple[Task, Plan | None, PlanState | None]:
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
            .where(Task.id == task_id, Task.user_id == user_id)
            .limit(1)
        )
        row = result.one_or_none()
        if row is None:
            raise LookupError("Task not found")
        return row[0], row[1], row[2]

    async def _load_node_context(
        self,
        *,
        user_id: UUID,
        task: Task,
    ) -> tuple[KnowledgeNode | None, UserNodeStatus | None]:
        if task.knowledge_node_id is None:
            return None, None

        result = await self.db.execute(
            select(KnowledgeNode, UserNodeStatus)
            .outerjoin(
                UserNodeStatus,
                and_(
                    UserNodeStatus.node_id == KnowledgeNode.id,
                    UserNodeStatus.user_id == user_id,
                ),
            )
            .where(KnowledgeNode.id == task.knowledge_node_id)
            .limit(1)
        )
        row = result.one_or_none()
        if row is None:
            return None, None
        return row[0], row[1]

    def _build_supporting_signals(
        self,
        *,
        task: Task,
        plan: Plan | None,
        plan_state: PlanState | None,
        node: KnowledgeNode | None,
        node_status: UserNodeStatus | None,
        ranking_signals: dict[str, Any],
        aurora: dict[str, Any],
        today: date,
    ) -> list[PrioritySignal]:
        raw_signals = [
            (
                "spaced_repetition",
                self._spaced_repetition_raw_score(task, node, node_status, ranking_signals),
                self._spaced_repetition_detail(task, node, node_status, today),
            ),
            (
                "goal_progress",
                self._goal_progress_raw_score(plan, plan_state, ranking_signals),
                self._goal_progress_detail(task, plan, plan_state),
            ),
            (
                "energy_match",
                self._energy_raw_score(ranking_signals),
                self._energy_detail(task, ranking_signals, aurora),
            ),
            (
                "social_context",
                self._social_raw_score(task, plan),
                self._social_detail(task, plan),
            ),
        ]
        total = sum(max(raw, 0.0) for _, raw, _ in raw_signals)
        if total <= 0:
            total = 4.0
            raw_signals = [(signal_type, 1.0, detail) for signal_type, _, detail in raw_signals]

        signals = [
            PrioritySignal(
                type=signal_type,
                weight=round(max(raw, 0.0) / total, 3),
                detail=detail,
                raw_score=round(raw, 3),
            )
            for signal_type, raw, detail in raw_signals
        ]
        return self._rebalance_weights(signals)

    async def _build_alternative_options(
        self,
        *,
        user_id: UUID,
        selected_task: Task,
        selected_score: float,
        aurora: dict[str, Any],
        today: date,
        limit: int,
    ) -> list[AlternativeOptionSkipped]:
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
            .where(
                Task.user_id == user_id,
                Task.id != selected_task.id,
                Task.status.in_(self.ACTIVE_STATUSES),
            )
            .order_by(Task.order_index.asc(), desc(Task.priority), desc(Task.updated_at))
            .limit(max(limit * 4, 8))
        )

        scored = [
            DailyTaskSelectionService.score_candidate(
                row[0],
                plan=row[1],
                plan_state=row[2],
                aurora=aurora,
                today=today,
            )
            for row in result.all()
        ]
        scored.sort(key=lambda item: (-item.score, item.task.order_index or 0, item.task.created_at))

        alternatives: list[AlternativeOptionSkipped] = []
        for option in scored[:limit]:
            delta = round(selected_score - option.score, 1)
            if delta >= 0:
                reason = f"{delta:.1f} points lower than this task; {option.reason}"
            else:
                reason = f"scored {abs(delta):.1f} points higher, but this explanation is scoped to the open task"
            alternatives.append(
                AlternativeOptionSkipped(
                    task_id=str(option.task.id),
                    title=option.task.title,
                    score=option.score,
                    reason=reason,
                )
            )
        return alternatives

    @staticmethod
    def _spaced_repetition_raw_score(
        task: Task,
        node: KnowledgeNode | None,
        node_status: UserNodeStatus | None,
        ranking_signals: dict[str, Any],
    ) -> float:
        deadline_score = float(ranking_signals.get("deadline_score") or 0.0)
        if node is None:
            return max(deadline_score, float(ranking_signals.get("priority_score") or 0.0) * 0.35, 0.5)
        mastery_gap = 0.0
        if node_status is not None:
            mastery_gap = max(0.0, 100.0 - float(node_status.mastery_score or 0.0)) / 100.0 * 12.0
        importance = max(1, min(5, int(node.importance_level or 1))) * 1.5
        return max(deadline_score, 4.0) + mastery_gap + importance

    @staticmethod
    def _goal_progress_raw_score(
        plan: Plan | None,
        plan_state: PlanState | None,
        ranking_signals: dict[str, Any],
    ) -> float:
        plan_score = float(ranking_signals.get("plan_score") or 0.0)
        if plan is None:
            return max(0.5, plan_score)
        focus_bonus = 4.0 if plan_state is not None and bool(plan_state.is_focus) else 0.0
        progress_gap = max(0.0, 1.0 - float(plan.progress or 0.0)) * 8.0
        return max(plan_score, 4.0) + focus_bonus + progress_gap

    @staticmethod
    def _energy_raw_score(ranking_signals: dict[str, Any]) -> float:
        energy = max(0.0, float(ranking_signals.get("energy_score") or 0.0))
        duration = max(0.0, float(ranking_signals.get("duration_score") or 0.0))
        difficulty = max(0.0, float(ranking_signals.get("difficulty_score") or 0.0))
        return energy + duration * 0.45 + difficulty * 0.35

    @staticmethod
    def _social_raw_score(task: Task, plan: Plan | None) -> float:
        tags = {str(tag).lower() for tag in (task.tags or [])}
        social_tags = {"social", "community", "partner", "group", "cohort"}
        if task.type == TaskType.SOCIAL or tags.intersection(social_tags):
            return 8.0
        source_metadata = getattr(plan, "source_metadata", None) or {}
        if isinstance(source_metadata, dict) and source_metadata.get("community_signal"):
            return 5.0
        return 1.0

    @staticmethod
    def _spaced_repetition_detail(
        task: Task,
        node: KnowledgeNode | None,
        node_status: UserNodeStatus | None,
        today: date,
    ) -> str:
        if node is not None:
            mastery = f"{float(node_status.mastery_score or 0.0):.0f}%" if node_status is not None else "unknown"
            if node_status is not None and node_status.next_review_at is not None:
                days = (node_status.next_review_at.date() - today).days
                if days <= 0:
                    return f"{node.name} is due for spaced repetition; current mastery is {mastery}."
                return f"{node.name} is linked to this task; next review window opens in {days} days."
            return f"{node.name} is the bound knowledge node; current mastery is {mastery}."

        if task.due_date is not None:
            days = (task.due_date - today).days
            if days < 0:
                return "The task is overdue, so timing is carrying a strong review signal."
            if days == 0:
                return "The task is due today, so it should stay visible in today's plan."
            return f"The task is due in {days} days, giving it a moderate timing signal."
        return "No knowledge-node review is due; this signal is a low baseline."

    @staticmethod
    def _goal_progress_detail(
        task: Task,
        plan: Plan | None,
        plan_state: PlanState | None,
    ) -> str:
        if plan is None:
            return "No active goal plan is bound; progress impact is inferred from standalone task priority."

        progress = max(0.0, min(1.0, float(plan.progress or 0.0))) * 100
        projected = min(100.0, progress + max(4.0, min(12.0, float(task.priority or 0) * 2.0)))
        focus = " and is the current focus plan" if plan_state is not None and bool(plan_state.is_focus) else ""
        return (
            f"{plan.name} is {progress:.0f}% complete{focus}; finishing this task can move it toward {projected:.0f}%."
        )

    @staticmethod
    def _energy_detail(
        task: Task,
        ranking_signals: dict[str, Any],
        aurora: dict[str, Any],
    ) -> str:
        target = int(ranking_signals.get("target_energy") or 3)
        aurora_level = str(aurora.get("level") or ranking_signals.get("aurora_level") or "L0")
        wake = float(aurora.get("wake_score") or ranking_signals.get("aurora_wake_score") or 0.0)
        return (
            f"Aurora energy {aurora_level} (wake {wake:.2f}) maps to target effort {target}/5; "
            f"this task costs {int(task.energy_cost or 1)}/5 with difficulty {int(task.difficulty or 1)}/5."
        )

    @staticmethod
    def _social_detail(task: Task, plan: Plan | None) -> str:
        tags = {str(tag).lower() for tag in (task.tags or [])}
        if task.type == TaskType.SOCIAL or tags.intersection({"social", "community", "partner", "group", "cohort"}):
            return "Community or partner context is attached, so the task gets a peer-momentum boost."
        source_metadata = getattr(plan, "source_metadata", None) or {}
        if isinstance(source_metadata, dict) and source_metadata.get("community_signal"):
            return "The parent plan carries a community signal that slightly boosts this task."
        return "No peer signal outranked the personal timing, goal, and energy signals today."

    @staticmethod
    def _primary_reason(
        *,
        task: Task,
        selection_reason: str,
        node: KnowledgeNode | None,
        node_status: UserNodeStatus | None,
        today: date,
    ) -> str:
        if node is not None and node_status is not None and node_status.next_review_at is not None:
            if node_status.next_review_at.date() <= today:
                return f"{node.name} is due for spaced repetition today."
        if task.due_date is not None and task.due_date <= today:
            return f"{task.title} is time-sensitive for today."
        return selection_reason or "This task is the best balanced next step right now."

    @staticmethod
    def _rebalance_weights(signals: list[PrioritySignal]) -> list[PrioritySignal]:
        if not signals:
            return signals
        total = round(sum(signal.weight for signal in signals), 3)
        delta = round(1.0 - total, 3)
        if abs(delta) >= 0.001:
            last = signals[-1]
            signals[-1] = last.model_copy(update={"weight": max(0.0, min(1.0, round(last.weight + delta, 3)))})
        return signals

    @staticmethod
    def _iso_or_none(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()
