from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_service
from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.growth_dashboard_service import GrowthDashboardService
from app.services.progress_narrative_service import ProgressNarrativeService
from app.signals.growth_chronicle import GrowthChronicleService

router = APIRouter(prefix="/experience", tags=["experience"])


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# route-tier: authed
@router.get("/growth-dashboard")
async def get_growth_experience_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return the closeout Growth Chronicle + Learning Dashboard aggregate."""
    service = _GrowthExperienceDashboardBuilder(db)
    return await service.build(current_user.id, user=current_user)


class _GrowthExperienceDashboardBuilder:
    LOOKBACK_DAYS = 7

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build(self, user_id: UUID, *, user: User) -> dict[str, Any]:
        since = _utcnow() - timedelta(days=self.LOOKBACK_DAYS)
        growth_snapshot = await GrowthDashboardService(self.db).build_snapshot(user_id, user=user)
        weekly_narrative = await self._weekly_narrative(user_id)
        chronicle_entries = await self._chronicle_entries(user_id)
        time_distribution = await self._time_distribution(user_id, since)
        efficiency_metrics = await self._efficiency_metrics(user_id, since)
        weakness_radar = await self._weakness_radar(user_id)
        knowledge_changes = await self._knowledge_changes(user_id, since)
        plan_stability = await self._plan_stability(user_id, since)

        return {
            "chronicle_entries": chronicle_entries,
            "weekly_narrative": self._story_weekly_narrative(weekly_narrative, growth_snapshot),
            "time_distribution": time_distribution,
            "efficiency_metrics": efficiency_metrics,
            "weakness_radar": weakness_radar,
            "knowledge_changes": knowledge_changes,
            "plan_stability": plan_stability,
            "model_updates": self._model_updates(
                chronicle_entries=chronicle_entries,
                knowledge_changes=knowledge_changes,
                growth_snapshot=growth_snapshot,
            ),
        }

    async def _weekly_narrative(self, user_id: UUID) -> dict[str, Any]:
        narrative = await ProgressNarrativeService(
            self.db,
            redis=cache_service.redis,
            cache=cache_service,
        ).get_weekly_narrative(user_id)
        return narrative.to_dict() if hasattr(narrative, "to_dict") else dict(narrative or {})

    async def _chronicle_entries(self, user_id: UUID) -> list[dict[str, Any]]:
        redis = getattr(cache_service, "redis", None)
        if redis is None:
            return []
        entries = await GrowthChronicleService(redis, self.db).get_chronicle(str(user_id), limit=40)
        return [
            {
                "entry_id": entry.entry_id,
                "entry_type": entry.entry_type,
                "title": entry.title,
                "narrative": entry.narrative,
                "evidence_refs": entry.evidence_refs,
                "timestamp": entry.timestamp,
                "user_status": entry.user_status,
                "confidence": entry.confidence,
            }
            for entry in entries
        ]

    async def _time_distribution(self, user_id: UUID, since: datetime) -> list[dict[str, Any]]:
        stmt = (
            select(Task.type, func.coalesce(func.sum(FocusSession.duration_minutes), 0))
            .join(Task, FocusSession.task_id == Task.id, isouter=True)
            .where(FocusSession.user_id == user_id, FocusSession.start_time >= since)
            .group_by(Task.type)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        if not rows:
            return []
        total_hours = sum(float(minutes or 0) for _, minutes in rows) / 60.0
        distribution: list[dict[str, Any]] = []
        for task_type, minutes in rows:
            hours = round(float(minutes or 0) / 60.0, 1)
            if hours <= 0:
                continue
            share = hours / total_hours if total_hours else 0.0
            distribution.append(
                {
                    "category": str(getattr(task_type, "value", task_type) or "unassigned"),
                    "hours": hours,
                    "trend": "up" if share >= 0.34 else "steady",
                }
            )
        return distribution

    async def _efficiency_metrics(self, user_id: UUID, since: datetime) -> dict[str, Any]:
        stmt = (
            select(Task)
            .where(Task.user_id == user_id, Task.completed_at >= since, Task.status == TaskStatus.COMPLETED)
            .order_by(desc(Task.completed_at))
        )
        result = await self.db.execute(stmt)
        tasks = list(result.scalars().all())
        tasks_completed = len(tasks)
        actual_minutes = [int(task.actual_minutes or task.estimated_minutes or 0) for task in tasks]
        avg_completion_time = round(sum(actual_minutes) / max(len(actual_minutes), 1), 1) if actual_minutes else 0.0
        due_tasks = [task for task in tasks if task.due_date is not None and task.completed_at is not None]
        on_time_count = sum(1 for task in due_tasks if task.completed_at.date() <= task.due_date)
        on_time_rate = round(on_time_count / len(due_tasks), 2) if due_tasks else 1.0 if tasks_completed else 0.0
        return {
            "tasks_completed": tasks_completed,
            "avg_completion_time": avg_completion_time,
            "on_time_rate": on_time_rate,
        }

    async def _weakness_radar(self, user_id: UUID) -> list[dict[str, Any]]:
        stmt = (
            select(KnowledgeNode.name, UserNodeStatus.mastery_score, UserNodeStatus.bkt_mastery_prob)
            .join(KnowledgeNode, UserNodeStatus.node_id == KnowledgeNode.id)
            .where(UserNodeStatus.user_id == user_id)
            .order_by(UserNodeStatus.mastery_score.asc(), UserNodeStatus.bkt_mastery_prob.asc())
            .limit(6)
        )
        result = await self.db.execute(stmt)
        radar: list[dict[str, Any]] = []
        for name, mastery_score, bkt_mastery in result.all():
            current = _normalize_mastery(mastery_score, bkt_mastery)
            target = 0.78
            radar.append(
                {
                    "area": str(name or "Knowledge area"),
                    "current_score": round(current, 2),
                    "target_score": target,
                    "gap": round(max(target - current, 0.0), 2),
                }
            )
        return radar

    async def _knowledge_changes(self, user_id: UUID, since: datetime) -> list[dict[str, Any]]:
        stmt = (
            select(StudyRecord, KnowledgeNode.name)
            .join(KnowledgeNode, StudyRecord.node_id == KnowledgeNode.id)
            .where(StudyRecord.user_id == user_id, StudyRecord.created_at >= since)
            .order_by(desc(StudyRecord.created_at))
            .limit(12)
        )
        result = await self.db.execute(stmt)
        by_node: dict[str, dict[str, Any]] = {}
        for record, node_name in result.all():
            label = str(node_name or "Knowledge node")
            before = float(record.initial_mastery or 0.0)
            after = max(0.0, min(1.0, before + float(record.mastery_delta or 0.0)))
            existing = by_node.get(label)
            if existing is None:
                by_node[label] = {
                    "node_label": label,
                    "mastery_before": round(before, 2),
                    "mastery_after": round(after, 2),
                    "reason": str(record.record_type or "task_complete"),
                }
            else:
                existing["mastery_before"] = min(existing["mastery_before"], round(before, 2))
                existing["mastery_after"] = max(existing["mastery_after"], round(after, 2))
        return list(by_node.values())[:6]

    async def _plan_stability(self, user_id: UUID, since: datetime) -> dict[str, Any]:
        focus_stmt = select(func.count(FocusSession.id)).where(
            FocusSession.user_id == user_id,
            FocusSession.start_time >= since,
            FocusSession.status == FocusStatus.INTERRUPTED,
        )
        interrupted = int((await self.db.execute(focus_stmt)).scalar() or 0)
        task_stmt = (
            select(Task.status, func.count(Task.id))
            .where(Task.user_id == user_id, Task.created_at >= since)
            .group_by(Task.status)
        )
        result = await self.db.execute(task_stmt)
        status_counts = {str(getattr(status, "value", status)): int(count or 0) for status, count in result.all()}
        abandoned = status_counts.get(TaskStatus.ABANDONED.value, 0)
        total = sum(status_counts.values())
        adjustments = (
            status_counts.get(TaskStatus.PAUSED.value, 0)
            + status_counts.get(TaskStatus.RESTORE.value, 0)
            + status_counts.get(TaskStatus.STUCK.value, 0)
        )
        return {
            "interruptions": interrupted,
            "adjustments": adjustments,
            "abandonment_rate": round(abandoned / total, 2) if total else 0.0,
        }

    @staticmethod
    def _story_weekly_narrative(narrative: dict[str, Any], growth_snapshot: dict[str, Any]) -> dict[str, Any]:
        title = str(narrative.get("period") or "This week's growth story")
        highlights = [str(item) for item in narrative.get("highlights") or [] if str(item).strip()]
        body = str(narrative.get("body") or "").strip()
        next_move = ((growth_snapshot.get("next_move_card") or {}) if isinstance(growth_snapshot, dict) else {})
        next_suggestion = str(narrative.get("next_week_suggestion") or next_move.get("summary") or "").strip()
        pattern = highlights[0] if highlights else body or "A new learning pattern is still forming."
        action = str(
            next_move.get("headline")
            or next_suggestion
            or "Keep one focused learning action visible."
        ).strip()
        outcome = body or "Sparkle will connect the next completed task, reflection, or correction into this story."
        return {
            "title": title,
            "story": f"Pattern: {pattern}\nAction: {action}\nOutcome: {outcome}",
            "key_insights": highlights[:4],
            "rejected_insights": [],
            "next_week_suggestion": next_suggestion,
        }

    @staticmethod
    def _model_updates(
        *,
        chronicle_entries: list[dict[str, Any]],
        knowledge_changes: list[dict[str, Any]],
        growth_snapshot: dict[str, Any],
    ) -> list[dict[str, str]]:
        updates: list[dict[str, str]] = []
        for entry in chronicle_entries[:2]:
            updates.append(
                {
                    "trigger_event": str(entry.get("title") or "Growth chronicle entry"),
                    "what_sparkle_learned": str(entry.get("narrative") or "A visible growth pattern may matter."),
                    "what_changed": "Sparkle can use this as a soft planning signal after you confirm it.",
                    "what_was_not_written": "No private raw notes or hidden debug trace were stored in this receipt.",
                }
            )
        for item in knowledge_changes[:2]:
            label = str(item.get("node_label") or "a knowledge node")
            updates.append(
                {
                    "trigger_event": f"Mastery changed on {label}",
                    "what_sparkle_learned": (
                        f"{label} moved from {item.get('mastery_before')} "
                        f"to {item.get('mastery_after')}."
                    ),
                    "what_changed": "Dashboard weakness and next-step ranking can adjust around this signal.",
                    "what_was_not_written": (
                        "Sparkle did not write an identity-level memory from this learning metric."
                    ),
                }
            )
        if not updates:
            next_move = growth_snapshot.get("next_move_card") if isinstance(growth_snapshot, dict) else None
            summary = str((next_move or {}).get("summary") or "No durable model update was needed yet.")
            updates.append(
                {
                    "trigger_event": "Dashboard refresh",
                    "what_sparkle_learned": summary,
                    "what_changed": "Only the visible dashboard recommendation was refreshed.",
                    "what_was_not_written": "No long-term memory was created from an empty week.",
                }
            )
        return updates[:4]


def _normalize_mastery(mastery_score: Any, bkt_mastery: Any) -> float:
    if bkt_mastery is not None and float(bkt_mastery or 0.0) > 0:
        return max(0.0, min(1.0, float(bkt_mastery)))
    raw = float(mastery_score or 0.0)
    return max(0.0, min(1.0, raw / 100.0 if raw > 1.0 else raw))
