"""Exam sprint dashboard aggregation service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import UserStreakStats
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus
from app.models.user_preferences import UserPreferencesCenter
from app.schemas.exam_sprint import (
    ExamSprintDashboardProgress,
    ExamSprintDashboardResponse,
    ExamSprintDashboardTaskGroup,
    ExamSprintDashboardTaskItem,
)
from app.services.error_book_service import ErrorBookService
from app.sprint_packs.sprint_pack_loader import load_pack


@dataclass(frozen=True)
class _CoverageNode:
    label: str
    mastery: float
    exam_weight: float


class ExamSprintDashboardService:
    """Build the dedicated home dashboard payload for exam sprint mode."""

    HIGH_FREQ_EXAM_WEIGHT_THRESHOLD = 0.7
    HIGH_FREQ_MASTERY_THRESHOLD = 60.0

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard(self, user_id: UUID) -> ExamSprintDashboardResponse:
        plan = await self._get_active_exam_sprint_plan(user_id)
        if plan is None:
            return ExamSprintDashboardResponse(active=False)

        metadata = self._exam_sprint_metadata(plan)
        goal_model = self._as_dict(metadata.get("goal_model"))
        assessment = self._as_dict(metadata.get("initial_assessment"))
        diagnostic = await self._get_latest_diagnostic(user_id)

        tasks = await self._list_plan_tasks(plan.id)
        initial_days_left = self._derive_initial_days_left(plan=plan, goal_model=goal_model, tasks=tasks)
        days_left = self._days_left(plan.target_date, fallback=initial_days_left)
        current_day_index = self._current_day_index(
            initial_days_left=initial_days_left,
            days_left=days_left,
            tasks=tasks,
        )
        task_groups = self._build_task_groups(
            tasks=tasks,
            target_date=plan.target_date,
            initial_days_left=initial_days_left,
            current_day_index=current_day_index,
        )
        today_group = next((group for group in task_groups if group.is_today), None)
        today_progress = ExamSprintDashboardProgress(
            completed=today_group.completed_count if today_group else 0,
            total=today_group.total_count if today_group else 0,
            completion_rate=(
                round(today_group.completed_count / today_group.total_count, 4)
                if today_group and today_group.total_count
                else 0.0
            ),
        )

        coverage_stats = await self._get_high_frequency_coverage(user_id=user_id, plan=plan)
        mistake_stats = await self._get_mistake_fix_rate(user_id)
        streak_days = await self._get_streak_days(user_id)

        baseline_estimated_score = self._optional_float(goal_model.get("estimated_score_now"))
        baseline_pass_probability = self._optional_float(assessment.get("pass_probability"))
        current_estimated_score = self._optional_float(
            diagnostic.get("diagnostic_estimated_score") or diagnostic.get("estimated_score_now")
        )
        current_pass_probability = self._optional_float(
            diagnostic.get("diagnostic_pass_probability") or diagnostic.get("pass_probability")
        )
        if current_estimated_score is None:
            current_estimated_score = baseline_estimated_score
        if current_pass_probability is None:
            current_pass_probability = baseline_pass_probability

        return ExamSprintDashboardResponse(
            active=True,
            plan_id=str(plan.id),
            plan_name=str(plan.name or ""),
            subject=str(plan.subject or ""),
            days_left=days_left,
            target_mode=self._nullable_string(goal_model.get("target_mode")),
            estimated_score_now=current_estimated_score,
            baseline_estimated_score=baseline_estimated_score,
            pass_probability=current_pass_probability,
            baseline_pass_probability=baseline_pass_probability,
            today_progress=today_progress,
            high_freq_coverage=coverage_stats["coverage"],
            high_freq_covered_count=coverage_stats["covered_count"],
            high_freq_total_count=coverage_stats["total_count"],
            mistake_fix_rate=mistake_stats["rate"],
            fixed_mistake_count=mistake_stats["fixed_count"],
            total_mistake_count=mistake_stats["total_count"],
            streak_days=streak_days,
            high_yield_low_mastery_topics=coverage_stats["weak_topics"],
            task_groups=task_groups,
            sleep_guard_hint=self._extract_sleep_guard_hint(metadata),
        )

    async def _get_active_exam_sprint_plan(self, user_id: UUID) -> Plan | None:
        stmt = (
            select(Plan)
            .where(
                and_(
                    Plan.user_id == user_id,
                    Plan.is_active.is_(True),
                    Plan.type == PlanType.SPRINT,
                    Plan.not_deleted_filter(),
                )
            )
            .order_by(
                Plan.target_date.is_(None),
                Plan.target_date.asc(),
                Plan.created_at.desc(),
            )
        )
        result = await self.db.execute(stmt)
        for plan in result.scalars().all():
            if self._exam_sprint_metadata(plan):
                return plan
        return None

    async def _get_latest_diagnostic(self, user_id: UUID) -> dict[str, Any]:
        stmt = select(UserPreferencesCenter.explicit).where(UserPreferencesCenter.user_id == user_id)
        explicit = (await self.db.execute(stmt)).scalar_one_or_none() or {}
        explicit = explicit if isinstance(explicit, dict) else {}
        cold_start = explicit.get("cold_start_context")
        return cold_start if isinstance(cold_start, dict) else {}

    async def _list_plan_tasks(self, plan_id: UUID) -> list[Task]:
        stmt = (
            select(Task)
            .where(and_(Task.plan_id == plan_id, Task.not_deleted_filter()))
            .order_by(Task.order_index.asc(), Task.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _build_task_groups(
        self,
        *,
        tasks: list[Task],
        target_date: date | None,
        initial_days_left: int,
        current_day_index: int,
    ) -> list[ExamSprintDashboardTaskGroup]:
        grouped: dict[int, list[Task]] = {}
        for task in tasks:
            day_index = self._task_day_index(task)
            if day_index < current_day_index:
                continue
            grouped.setdefault(day_index, []).append(task)

        groups: list[ExamSprintDashboardTaskGroup] = []
        for day_index in sorted(grouped):
            day_tasks = grouped[day_index]
            completed_count = sum(1 for task in day_tasks if self._task_status(task) == TaskStatus.COMPLETED.value)
            groups.append(
                ExamSprintDashboardTaskGroup(
                    day_index=day_index,
                    date=self._task_group_date(
                        target_date=target_date,
                        initial_days_left=initial_days_left,
                        day_index=day_index,
                    ),
                    is_today=day_index == current_day_index,
                    completed_count=completed_count,
                    total_count=len(day_tasks),
                    tasks=[
                        ExamSprintDashboardTaskItem(
                            id=str(task.id),
                            title=str(task.title or ""),
                            status=self._task_status(task),
                            estimated_minutes=max(int(task.estimated_minutes or 0), 0),
                            is_completed=self._task_status(task) == TaskStatus.COMPLETED.value,
                            knowledge_node_id=str(task.knowledge_node_id) if task.knowledge_node_id else None,
                            due_date=task.due_date,
                            compressed=bool(self._as_dict(task.guide_json).get("compressed")),
                            compression_reason=self._nullable_string(
                                self._as_dict(task.guide_json).get("compression_reason")
                            ),
                        )
                        for task in day_tasks
                    ],
                )
            )
        return groups

    async def _get_high_frequency_coverage(self, *, user_id: UUID, plan: Plan) -> dict[str, Any]:
        pack = load_pack(str(plan.subject or ""))
        if pack:
            nodes = await self._resolve_pack_coverage_nodes(user_id=user_id, pack=pack)
            if nodes:
                return self._summarize_coverage(nodes)
        return await self._fallback_plan_coverage(user_id=user_id, plan=plan)

    async def _resolve_pack_coverage_nodes(self, *, user_id: UUID, pack: dict[str, Any]) -> list[_CoverageNode]:
        raw_nodes = [
            item
            for item in list(pack.get("knowledge_nodes") or [])
            if self._as_float(item.get("exam_weight")) > self.HIGH_FREQ_EXAM_WEIGHT_THRESHOLD
        ]
        if not raw_nodes:
            return []

        labels: list[str] = []
        weights_by_label: dict[str, float] = {}
        for item in raw_nodes:
            label = str(item.get("label") or item.get("node_id") or "").strip()
            if not label:
                continue
            lowered = label.lower()
            if lowered not in weights_by_label:
                labels.append(label)
            weights_by_label[lowered] = max(
                self._as_float(item.get("exam_weight")),
                weights_by_label.get(lowered, 0.0),
            )

        if not labels:
            return []

        stmt = (
            select(KnowledgeNode.name, UserNodeStatus.mastery_score)
            .outerjoin(
                UserNodeStatus,
                and_(
                    UserNodeStatus.node_id == KnowledgeNode.id,
                    UserNodeStatus.user_id == user_id,
                ),
            )
            .where(
                and_(
                    KnowledgeNode.not_deleted_filter(),
                    func.lower(KnowledgeNode.name).in_([label.lower() for label in labels]),
                )
            )
        )
        rows = (await self.db.execute(stmt)).all()
        mastery_by_label: dict[str, float] = {}
        for name, mastery_score in rows:
            lowered = str(name or "").strip().lower()
            mastery_by_label[lowered] = max(
                self._as_float(mastery_score),
                mastery_by_label.get(lowered, 0.0),
            )

        return [
            _CoverageNode(
                label=label,
                mastery=mastery_by_label.get(label.lower(), 0.0),
                exam_weight=weights_by_label.get(label.lower(), 0.0),
            )
            for label in labels
        ]

    async def _fallback_plan_coverage(self, *, user_id: UUID, plan: Plan) -> dict[str, Any]:
        stmt = (
            select(KnowledgeNode.name, UserNodeStatus.mastery_score)
            .join(Task, Task.knowledge_node_id == KnowledgeNode.id)
            .outerjoin(
                UserNodeStatus,
                and_(
                    UserNodeStatus.node_id == KnowledgeNode.id,
                    UserNodeStatus.user_id == user_id,
                ),
            )
            .where(
                and_(
                    Task.plan_id == plan.id,
                    Task.knowledge_node_id.is_not(None),
                    Task.not_deleted_filter(),
                    KnowledgeNode.not_deleted_filter(),
                )
            )
        )
        rows = (await self.db.execute(stmt)).all()
        deduped: dict[str, _CoverageNode] = {}
        for name, mastery_score in rows:
            label = str(name or "").strip()
            if not label:
                continue
            lowered = label.lower()
            mastery = self._as_float(mastery_score)
            existing = deduped.get(lowered)
            if existing is None or mastery > existing.mastery:
                deduped[lowered] = _CoverageNode(
                    label=label,
                    mastery=mastery,
                    exam_weight=1.0,
                )
        return self._summarize_coverage(list(deduped.values()))

    def _summarize_coverage(self, nodes: list[_CoverageNode]) -> dict[str, Any]:
        total_count = len(nodes)
        if total_count == 0:
            return {
                "coverage": 0.0,
                "covered_count": 0,
                "total_count": 0,
                "weak_topics": [],
            }

        covered_count = sum(1 for node in nodes if node.mastery >= self.HIGH_FREQ_MASTERY_THRESHOLD)
        weak_topics = [
            node.label
            for node in sorted(
                (item for item in nodes if item.mastery < self.HIGH_FREQ_MASTERY_THRESHOLD),
                key=lambda item: (-item.exam_weight, item.mastery, item.label),
            )[:3]
        ]
        return {
            "coverage": round(covered_count / total_count, 4),
            "covered_count": covered_count,
            "total_count": total_count,
            "weak_topics": weak_topics,
        }

    async def _get_mistake_fix_rate(self, user_id: UUID) -> dict[str, Any]:
        stats = await ErrorBookService(self.db).get_review_stats(user_id)
        total_count = int(stats.get("total_errors") or 0)
        fixed_count = int(stats.get("mastered_count") or 0)
        return {
            "rate": round(fixed_count / total_count, 4) if total_count else 0.0,
            "fixed_count": fixed_count,
            "total_count": total_count,
        }

    async def _get_streak_days(self, user_id: UUID) -> int:
        stmt = select(UserStreakStats.current_streak).where(UserStreakStats.user_id == user_id)
        result = await self.db.execute(stmt)
        return max(int(result.scalar_one_or_none() or 0), 0)

    def _derive_initial_days_left(self, *, plan: Plan, goal_model: dict[str, Any], tasks: list[Task]) -> int:
        from_goal_model = self._as_int(goal_model.get("days_left"))
        if from_goal_model > 0:
            return from_goal_model

        max_task_day = max((self._task_day_index(task) for task in tasks), default=0)
        if max_task_day > 0:
            return max_task_day

        if plan.target_date and plan.created_at:
            return max((plan.target_date - plan.created_at.date()).days, 1)
        return 1

    def _current_day_index(self, *, initial_days_left: int, days_left: int, tasks: list[Task]) -> int:
        max_task_day = max((self._task_day_index(task) for task in tasks), default=initial_days_left)
        derived = max(initial_days_left - days_left + 1, 1)
        return min(derived, max(max_task_day, 1))

    def _days_left(self, target_date: date | None, *, fallback: int) -> int:
        if target_date is None:
            return max(fallback, 0)
        return max((target_date - date.today()).days, 0)

    def _task_group_date(
        self,
        *,
        target_date: date | None,
        initial_days_left: int,
        day_index: int,
    ) -> date | None:
        if target_date is None:
            return None
        offset = max(initial_days_left - day_index, 0)
        return target_date - timedelta(days=offset)

    def _task_day_index(self, task: Task) -> int:
        order_index = int(task.order_index or 0)
        if order_index >= 1000:
            return max(order_index // 1000, 1)

        for tag in list(task.tags or []):
            tag_text = str(tag or "").strip().lower()
            if not tag_text.startswith("day:"):
                continue
            raw_value = tag_text.split(":", maxsplit=1)[1]
            value = self._as_int(raw_value)
            if value > 0:
                return value
        return 1

    def _task_status(self, task: Task) -> str:
        raw = getattr(task.status, "value", task.status)
        return str(raw or TaskStatus.PENDING.value)

    def _exam_sprint_metadata(self, plan: Plan) -> dict[str, Any]:
        metadata = self._as_dict(plan.source_metadata)
        exam_sprint = metadata.get("exam_sprint_intake")
        return exam_sprint if isinstance(exam_sprint, dict) else {}

    def _extract_sleep_guard_hint(self, metadata: dict[str, Any]) -> str | None:
        sprint_policy = self._as_dict(metadata.get("sprint_policy"))
        if not sprint_policy:
            return None
        hint = self._nullable_string(sprint_policy.get("sleep_guard_hint"))
        return hint

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _nullable_string(value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return ExamSprintDashboardService._as_float(value)

    @staticmethod
    def _as_int(value: Any, *, fallback: int = 0) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value))
            except ValueError:
                return fallback
        return fallback

    @staticmethod
    def _as_float(value: Any, *, fallback: float = 0.0) -> float:
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return fallback
        return fallback
