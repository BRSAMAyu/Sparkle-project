from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import (
    ArtifactType,
    Card,
    CardType,
    EdgeType,
    TaskOccurrence,
)
from app.models.task import Task
from app.models.task_feedback import TaskFeedback
from app.services.card_edge_service import CardEdgeService
from app.services.card_protocol.decision_log_service import DecisionLogService
from app.services.card_protocol.main_chain_artifact_service import MainChainArtifactService
from app.services.planning_artifact_service import PlanningArtifactService


@dataclass
class DriftAssessment:
    drift_score: float
    drift_indicators: list[str]
    recommendation: str
    supporting_metrics: dict[str, Any]


@dataclass
class PlanningContext:
    plan_card_id: str
    global_compass: dict[str, Any]
    phase_archive: list[dict[str, Any]]
    rolling_context: dict[str, Any]
    relevant_decisions: list[dict[str, Any]]
    active_phase: dict[str, Any] | None


class PlanningMemoryService:
    """Long-horizon planning memory assembled from protocol artifacts and runtime state."""

    ROLLING_WINDOW_DAYS = 28

    def __init__(self, db: AsyncSession, event_bus=None):
        self.db = db
        self.event_bus = event_bus
        self.artifact_service = PlanningArtifactService(db, event_bus)
        self.edge_service = CardEdgeService(db, event_bus)
        self.decision_log_service = DecisionLogService(db, event_bus)
        self.main_chain_artifact_service = MainChainArtifactService(db, event_bus)

    async def load_planning_context(
        self,
        *,
        plan_card_id: UUID,
        user_id: UUID,
    ) -> PlanningContext:
        plan_card = await self._get_owned_plan(plan_card_id, user_id)
        global_compass_artifact = await self.artifact_service.get_approved(plan_card.id, ArtifactType.GLOBAL_COMPASS)
        phase_archive = await self._load_phase_archive(plan_card.id)
        rolling_context = await self._load_rolling_context(plan_card)
        relevant_decisions = await self._load_relevant_decisions(plan_card.id)
        active_phase = await self._load_active_phase(plan_card.id)
        return PlanningContext(
            plan_card_id=str(plan_card.id),
            global_compass=dict(global_compass_artifact.payload or {}) if global_compass_artifact else {},
            phase_archive=phase_archive,
            rolling_context=rolling_context,
            relevant_decisions=relevant_decisions,
            active_phase=active_phase,
        )

    async def archive_phase(
        self,
        *,
        phase_card_id: UUID,
        retrospective: dict,
        feedback_gate: dict,
    ) -> dict[str, Any]:
        phase_card = await self._get_phase(phase_card_id)
        metadata = dict(phase_card.metadata_ or {})
        archive_entry = {
            "archived_at": datetime.utcnow().isoformat(),
            "phase_card_id": str(phase_card.id),
            "title": metadata.get("title") or metadata.get("objective") or "Untitled phase",
            "objective": metadata.get("objective"),
            "phase_index": metadata.get("phase_index"),
            "retrospective": retrospective,
            "feedback_gate": feedback_gate,
            "lessons_for_future": self._extract_lessons(retrospective, feedback_gate),
        }
        archives = list(metadata.get("phase_archive_entries") or [])
        archives.append(archive_entry)
        metadata["phase_archive_entries"] = archives[-10:]
        metadata["archived_phase"] = True
        phase_card.metadata_ = metadata
        phase_card.version += 1
        await self.db.flush()
        return archive_entry

    async def compute_drift_score(
        self,
        *,
        plan_card_id: UUID,
        current_phase: dict | None = None,
    ) -> DriftAssessment:
        plan_card = await self._get_plan(plan_card_id)
        active_phase = current_phase or await self._load_active_phase(plan_card.id)
        rolling_context = await self._load_rolling_context(plan_card)
        compass_artifact = await self.artifact_service.get_approved(plan_card.id, ArtifactType.GLOBAL_COMPASS)
        compass = dict(compass_artifact.payload or {}) if compass_artifact else {}

        indicators: list[str] = []
        score = 0.0
        metrics = {
            "deferral_rate": rolling_context.get("deferral_rate", 0.0),
            "abandon_rate": rolling_context.get("abandon_rate", 0.0),
            "negative_feedback_ratio": rolling_context.get("negative_feedback_ratio", 0.0),
            "completion_rate": rolling_context.get("completion_rate", 0.0),
            "alignment_score": ((active_phase or {}).get("feedback_gate") or {}).get("alignment_score"),
        }

        deferral_rate = float(metrics["deferral_rate"] or 0.0)
        if deferral_rate >= 0.35:
            score += 0.3
            indicators.append("high_deferral_rate")

        abandon_rate = float(metrics["abandon_rate"] or 0.0)
        if abandon_rate >= 0.2:
            score += 0.2
            indicators.append("high_abandon_rate")

        negative_feedback_ratio = float(metrics["negative_feedback_ratio"] or 0.0)
        if negative_feedback_ratio >= 0.5:
            score += 0.2
            indicators.append("negative_feedback_trend")

        completion_rate = float(metrics["completion_rate"] or 0.0)
        if completion_rate <= 0.4:
            score += 0.2
            indicators.append("low_completion_rate")

        alignment_score = metrics["alignment_score"]
        if alignment_score is not None and float(alignment_score) < 0.5:
            score += 0.25
            indicators.append("phase_feedback_low_alignment")

        if compass.get("hard_constraints", {}).get("notes") and deferral_rate >= 0.35:
            score += 0.1
            indicators.append("constraints_not_respected")

        recommendation = "continue"
        if score >= 0.7:
            recommendation = "review_compass"
        elif score >= 0.4:
            recommendation = "adjust_next_phase"

        return DriftAssessment(
            drift_score=round(min(score, 1.0), 4),
            drift_indicators=indicators,
            recommendation=recommendation,
            supporting_metrics=metrics,
        )

    async def _load_phase_archive(self, plan_card_id: UUID) -> list[dict[str, Any]]:
        phase_cards = await self._get_plan_phases(plan_card_id)
        archive: list[dict[str, Any]] = []
        for phase in phase_cards:
            metadata = dict(phase.metadata_ or {})
            feedback_gate = dict(metadata.get("feedback_gate") or {})
            # Include all non-active phases regardless of whether feedback was submitted.
            # Phases without a feedback_gate are included with partial data so the AI
            # context never has silent gaps in the plan history.
            entry: dict[str, Any] = {
                "phase_card_id": str(phase.id),
                "title": metadata.get("title") or metadata.get("objective"),
                "phase_index": metadata.get("phase_index"),
                "lifecycle_status": phase.lifecycle_status.value,
                "feedback_submitted": bool(feedback_gate.get("submitted_at")),
            }
            if feedback_gate:
                entry["feedback_gate"] = feedback_gate
                entry["lessons_for_future"] = self._extract_lessons(
                    feedback_gate.get("retrospective") or {},
                    feedback_gate,
                )
            archive.append(entry)
        archive.sort(key=lambda item: int(item.get("phase_index") or 0))
        return archive

    async def _load_rolling_context(self, plan_card: Card) -> dict[str, Any]:
        now = datetime.utcnow()
        window_start = now - timedelta(days=self.ROLLING_WINDOW_DAYS)
        task_ids = await self._get_plan_task_ids(plan_card.id)

        occurrences = []
        if task_ids:
            occ_stmt = select(TaskOccurrence).where(
                TaskOccurrence.plan_card_id == plan_card.id,
                TaskOccurrence.series_card_id.in_(task_ids),
                TaskOccurrence.created_at >= window_start,
            )
            occ_result = await self.db.execute(occ_stmt)
            occurrences = list(occ_result.scalars().all())

        legacy_plan_id = (plan_card.metadata_ or {}).get("legacy_plan_id")
        tasks = []
        feedbacks = []
        if legacy_plan_id:
            task_stmt = select(Task).where(
                Task.plan_id == UUID(str(legacy_plan_id)),
                Task.created_at >= window_start,
            )
            task_result = await self.db.execute(task_stmt)
            tasks = list(task_result.scalars().all())

            feedback_stmt = (
                select(TaskFeedback)
                .join(Task, Task.id == TaskFeedback.task_id)
                .where(
                    Task.plan_id == UUID(str(legacy_plan_id)),
                    TaskFeedback.created_at >= window_start,
                )
                .order_by(desc(TaskFeedback.created_at))
            )
            feedback_result = await self.db.execute(feedback_stmt)
            feedbacks = list(feedback_result.scalars().all())

        completed_occurrences = [occ for occ in occurrences if occ.occurrence_status.value == "COMPLETED"]
        deferred_occurrences = [occ for occ in occurrences if occ.occurrence_status.value == "DEFERRED"]
        abandoned_tasks = [task for task in tasks if task.status.value == "ABANDONED"]
        negative_feedbacks = [
            feedback for feedback in feedbacks
            if str(feedback.category or "").lower() in {"too_difficult", "unclear", "abandoned"}
        ]
        total_occurrences = len(occurrences) or 1
        total_tasks = len(tasks) or 1
        total_feedbacks = len(feedbacks) or 1
        return {
            "window_days": self.ROLLING_WINDOW_DAYS,
            "recent_task_count": len(tasks),
            "recent_occurrence_count": len(occurrences),
            "recent_feedback_count": len(feedbacks),
            "completion_rate": round(len(completed_occurrences) / total_occurrences, 4),
            "deferral_rate": round(len(deferred_occurrences) / total_occurrences, 4),
            "abandon_rate": round(len(abandoned_tasks) / total_tasks, 4),
            "negative_feedback_ratio": round(len(negative_feedbacks) / total_feedbacks, 4),
            "recent_feedback_snippets": [
                {
                    "feedback_id": str(feedback.id),
                    "category": feedback.category,
                    "reflection": (feedback.reflection_payload or {}).get("free_text"),
                }
                for feedback in feedbacks[:8]
            ],
        }

    async def _load_relevant_decisions(self, plan_card_id: UUID) -> list[dict[str, Any]]:
        decisions = await self.decision_log_service.get_all_entries(plan_card_id, limit=20)
        return decisions[-8:]

    async def _load_active_phase(self, plan_card_id: UUID) -> dict[str, Any] | None:
        plan_card = await self._get_plan(plan_card_id)
        current_phase_id = (plan_card.metadata_ or {}).get("current_phase_card_id")
        if not current_phase_id:
            return None
        phase = await self._get_phase(UUID(str(current_phase_id)))
        metadata = dict(phase.metadata_ or {})
        return {
            "phase_card_id": str(phase.id),
            "title": metadata.get("title") or metadata.get("objective"),
            "objective": metadata.get("objective"),
            "phase_index": metadata.get("phase_index"),
            "feedback_gate": dict(metadata.get("feedback_gate") or {}),
            "lifecycle_status": phase.lifecycle_status.value,
        }

    async def _get_plan(self, plan_card_id: UUID) -> Card:
        stmt = select(Card).where(
            Card.id == plan_card_id,
            Card.card_type == CardType.PLAN,
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        plan_card = result.scalar_one_or_none()
        if not plan_card:
            raise ValueError("Plan card not found")
        return plan_card

    async def _get_owned_plan(self, plan_card_id: UUID, user_id: UUID) -> Card:
        plan_card = await self._get_plan(plan_card_id)
        if plan_card.owner_id != user_id:
            raise ValueError("Plan card not found")
        return plan_card

    async def _get_phase(self, phase_card_id: UUID) -> Card:
        stmt = select(Card).where(
            Card.id == phase_card_id,
            Card.card_type == CardType.PHASE,
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        phase = result.scalar_one_or_none()
        if not phase:
            raise ValueError("Phase card not found")
        return phase

    async def _get_plan_phases(self, plan_card_id: UUID) -> list[Card]:
        children = await self.edge_service.get_children(plan_card_id, edge_type=EdgeType.CONTAINS, active_only=True)
        phases = [card for _, card in children if card.card_type == CardType.PHASE]
        phases.sort(key=lambda card: int((card.metadata_ or {}).get("phase_index") or 0))
        return phases

    async def _get_plan_task_ids(self, plan_card_id: UUID) -> list[UUID]:
        phases = await self._get_plan_phases(plan_card_id)
        task_ids: list[UUID] = []
        for phase in phases:
            children = await self.edge_service.get_children(phase.id, edge_type=EdgeType.CONTAINS, active_only=True)
            task_ids.extend([card.id for _, card in children if card.card_type == CardType.TASK])
        return task_ids

    def _extract_lessons(self, retrospective: dict, feedback_gate: dict) -> list[str]:
        lessons: list[str] = []
        progress = float(retrospective.get("progress") or 0.0)
        if progress >= 0.75:
            lessons.append("High completion momentum can be sustained in the next phase.")
        elif progress <= 0.4:
            lessons.append("Scope or pacing should be reduced for the next phase.")
        if feedback_gate.get("life_changed"):
            lessons.append("Life circumstances changed and planning assumptions must be refreshed.")
        if feedback_gate.get("blocked"):
            lessons.append("A blocking constraint should be removed before expanding scope.")
        reflection = str(feedback_gate.get("reflection") or "").strip()
        if reflection:
            lessons.append(reflection[:180])
        return lessons[:4]
