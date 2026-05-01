from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import (
    Card,
    CardCreatedBy,
    CardLifecycleStatus,
    CardType,
    EdgeType,
    OccurrenceStatus,
    TaskOccurrence,
)
from app.models.plan import Plan
from app.models.task import Task
from app.services.card_edge_service import CardEdgeService
from app.services.card_protocol.card_operations_service import CardOperationsService
from app.services.card_protocol.temporal_engine import TemporalEngine
from app.services.card_service import CardService


@dataclass
class PhaseCompletionResult:
    status: str
    phase_card_id: str
    feedback_required: bool
    retrospective: dict[str, Any]
    next_phase_card_id: str | None = None


@dataclass
class PhaseFeedbackResult:
    phase_card_id: str
    alignment_score: float
    trigger_compass_review: bool
    next_phase_card_id: str | None
    next_phase_activated: bool
    retrospective: dict[str, Any]


class PhaseService:
    """Real phase lifecycle and weighted-progress orchestration."""

    def __init__(self, db: AsyncSession, event_bus=None):
        self.db = db
        self.event_bus = event_bus
        self.card_service = CardService(db, event_bus)
        self.edge_service = CardEdgeService(db, event_bus)
        self.temporal_engine = TemporalEngine(db, event_bus)
        self.card_operations = CardOperationsService(db, event_bus)

    async def create_phase(
        self,
        *,
        plan_card_id: UUID,
        name: str,
        phase_index: int,
        user_id: UUID,
        estimated_start: date | None = None,
        estimated_end: date | None = None,
        entry_criteria: list[str] | None = None,
        exit_criteria: list[str] | None = None,
        feedback_gate_required: bool = True,
        phase_weight: float | None = None,
        objective: str | None = None,
    ) -> Card:
        plan_card = await self._get_owned_plan(plan_card_id, user_id)
        phases = await self.get_plan_phases(plan_card.id)
        insert_at = max(0, min(phase_index - 1, len(phases)))

        new_phase = await self.card_service.create_card(
            card_type=CardType.PHASE,
            owner_id=user_id,
            holder_id=user_id,
            metadata={
                "title": name,
                "objective": objective or name,
                "phase_index": insert_at + 1,
                "estimated_start": estimated_start.isoformat() if estimated_start else None,
                "estimated_end": estimated_end.isoformat() if estimated_end else None,
                "entry_criteria": list(entry_criteria or []),
                "exit_criteria": list(exit_criteria or []),
                "feedback_gate_required": feedback_gate_required,
                "phase_weight": phase_weight,
                "synthetic_phase": False,
            },
            created_by=CardCreatedBy.SYSTEM,
            lifecycle_status=CardLifecycleStatus.DRAFT,
        )

        await self.edge_service.create_edge(
            from_card_id=plan_card.id,
            to_card_id=new_phase.id,
            edge_type=EdgeType.CONTAINS,
            order_index=insert_at,
            metadata={"source": "phase_service"},
        )

        await self._reindex_phases(plan_card.id)
        await self._replace_synthetic_phase_if_needed(plan_card, new_phase)
        await self._refresh_plan_progress(plan_card, user_id)
        return new_phase

    async def reorder_phases(
        self,
        *,
        plan_card_id: UUID,
        ordered_phase_ids: list[UUID],
        user_id: UUID,
    ) -> list[Card]:
        plan_card = await self._get_owned_plan(plan_card_id, user_id)
        phases = await self.get_plan_phases(plan_card.id)
        existing_ids = {phase.id for phase in phases}
        if existing_ids != set(ordered_phase_ids):
            raise ValueError("ordered_phase_ids must match existing plan phases")

        for order_index, phase_id in enumerate(ordered_phase_ids):
            edges = await self.edge_service.get_parents(phase_id, edge_type=EdgeType.CONTAINS, active_only=True)
            for edge, parent in edges:
                if parent.id == plan_card.id:
                    edge.order_index = order_index
                    phase = await self.card_service.get_card(phase_id)
                    if phase:
                        metadata = dict(phase.metadata_ or {})
                        metadata["phase_index"] = order_index + 1
                        phase.metadata_ = metadata
                        phase.version += 1
        await self.db.flush()

        await self._sync_plan_phase_pointer(plan_card, ordered_phase_ids[0] if ordered_phase_ids else None)
        await self._refresh_plan_progress(plan_card, user_id)
        refreshed = await self.get_plan_phases(plan_card.id)
        return refreshed

    async def activate_phase(
        self,
        *,
        phase_card_id: UUID,
        user_id: UUID,
        skip_gate_check: bool = False,
    ) -> Card:
        phase_card = await self._get_owned_phase(phase_card_id, user_id)
        plan_card = await self._get_parent_plan(phase_card.id)
        if not plan_card:
            raise ValueError("Phase must belong to a plan")

        # Enforce feedback gate: the preceding phase must have submitted feedback
        # before the next phase can be activated (unless caller is internal/system).
        if not skip_gate_check:
            sibling_phases = await self.get_plan_phases(plan_card.id)
            phase_index = int((phase_card.metadata_ or {}).get("phase_index") or 0)
            if phase_index > 1:
                preceding = next(
                    (p for p in sibling_phases if int((p.metadata_ or {}).get("phase_index") or 0) == phase_index - 1),
                    None,
                )
                if preceding is not None:
                    pre_meta = dict(preceding.metadata_ or {})
                    gate_required = bool(pre_meta.get("feedback_gate_required", True))
                    gate_submitted = bool((pre_meta.get("feedback_gate") or {}).get("submitted_at"))
                    if gate_required and not gate_submitted:
                        raise ValueError(
                            f"Phase {phase_index - 1} requires a feedback gate submission before phase {phase_index} can be activated"
                        )

        sibling_phases = await self.get_plan_phases(plan_card.id)
        for sibling in sibling_phases:
            if sibling.id == phase_card.id:
                continue
            if sibling.lifecycle_status == CardLifecycleStatus.ACTIVE:
                await self.card_service.pause(sibling.id)

        activated = await self.card_service.activate(phase_card.id)
        if activated is None:
            raise ValueError("Phase not found")

        await self._sync_plan_phase_pointer(plan_card, phase_card.id)
        start_date, end_date = self.temporal_engine._resolve_phase_window(phase_card)
        tasks = await self._get_phase_tasks(phase_card.id)
        for task in tasks:
            await self.temporal_engine.generate_occurrences(
                task_card_id=task.id,
                phase_card_id=phase_card.id,
                from_date=start_date,
                to_date=end_date,
            )
        await self._refresh_plan_progress(plan_card, user_id)
        return activated

    async def complete_phase(
        self,
        *,
        phase_card_id: UUID,
        user_id: UUID,
    ) -> PhaseCompletionResult:
        phase_card = await self._get_owned_phase(phase_card_id, user_id)
        retrospective = await self._build_phase_retrospective(phase_card.id)
        metadata = dict(phase_card.metadata_ or {})
        feedback_required = bool(metadata.get("feedback_gate_required", True))
        if feedback_required and not ((metadata.get("feedback_gate") or {}).get("submitted_at")):
            return PhaseCompletionResult(
                status="NEEDS_FEEDBACK",
                phase_card_id=str(phase_card.id),
                feedback_required=True,
                retrospective=retrospective,
                next_phase_card_id=str(await self._find_next_phase_id(phase_card.id) or "") or None,
            )

        await self.card_service.complete(phase_card.id)
        plan_card = await self._get_parent_plan(phase_card.id)
        next_phase_id = await self._find_next_phase_id(phase_card.id)
        if plan_card and next_phase_id:
            await self.activate_phase(phase_card_id=next_phase_id, user_id=user_id, skip_gate_check=True)
        if plan_card:
            await self._refresh_plan_progress(plan_card, user_id)

        return PhaseCompletionResult(
            status="COMPLETED",
            phase_card_id=str(phase_card.id),
            feedback_required=feedback_required,
            retrospective=retrospective,
            next_phase_card_id=str(next_phase_id) if next_phase_id else None,
        )

    async def submit_phase_feedback(
        self,
        *,
        phase_card_id: UUID,
        user_id: UUID,
        feedback: dict[str, Any],
    ) -> PhaseFeedbackResult:
        phase_card = await self._get_owned_phase(phase_card_id, user_id)
        retrospective = await self._build_phase_retrospective(phase_card.id)
        alignment_score = self._compute_alignment_score(feedback)
        trigger_compass_review = bool(
            feedback.get("request_compass_review")
            or feedback.get("life_changed")
            or alignment_score < 0.5
        )

        metadata = dict(phase_card.metadata_ or {})
        metadata["feedback_gate"] = {
            "submitted_at": date.today().isoformat(),
            "alignment_score": alignment_score,
            "feedback": feedback,
            "retrospective": retrospective,
            "trigger_compass_review": trigger_compass_review,
        }
        phase_card.metadata_ = metadata
        phase_card.version += 1
        phase_card.updated_by = CardCreatedBy.SYSTEM
        await self.db.flush()

        await self.card_service.complete(phase_card.id)
        plan_card = await self._get_parent_plan(phase_card.id)
        next_phase_id = await self._find_next_phase_id(phase_card.id)
        next_phase_activated = False
        if plan_card and next_phase_id and not trigger_compass_review:
            await self.activate_phase(phase_card_id=next_phase_id, user_id=user_id, skip_gate_check=True)
            next_phase_activated = True
        if plan_card:
            plan_metadata = dict(plan_card.metadata_ or {})
            plan_metadata["last_phase_feedback"] = {
                "phase_card_id": str(phase_card.id),
                "alignment_score": alignment_score,
                "trigger_compass_review": trigger_compass_review,
            }
            plan_card.metadata_ = plan_metadata
            plan_card.version += 1
            await self.db.flush()
            await self._refresh_plan_progress(plan_card, user_id)

        return PhaseFeedbackResult(
            phase_card_id=str(phase_card.id),
            alignment_score=alignment_score,
            trigger_compass_review=trigger_compass_review,
            next_phase_card_id=str(next_phase_id) if next_phase_id else None,
            next_phase_activated=next_phase_activated,
            retrospective=retrospective,
        )

    async def get_plan_phases(self, plan_card_id: UUID) -> list[Card]:
        children = await self.edge_service.get_children(
            plan_card_id,
            edge_type=EdgeType.CONTAINS,
            active_only=True,
        )
        phases = [
            card
            for _, card in children
            if card.card_type == CardType.PHASE
            and not bool((card.metadata_ or {}).get("synthetic_replaced_by"))
        ]
        phases.sort(key=lambda phase: int((phase.metadata_ or {}).get("phase_index") or 0))
        return phases

    async def get_phase_summaries_for_legacy_plan(
        self,
        *,
        legacy_plan_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        plan_card = await self.get_plan_card_by_legacy_plan(legacy_plan_id, user_id)
        if not plan_card:
            return {
                "plan_card_id": None,
                "current_phase_card_id": None,
                "progress_mode": "legacy",
                "weighted_progress": None,
                "phases": [],
            }

        phases = await self.get_plan_phases(plan_card.id)
        weighted_progress = await self.sync_legacy_plan_progress(legacy_plan_id, user_id)
        summaries = []
        for phase in phases:
            retrospective = await self._build_phase_retrospective(phase.id)
            metadata = dict(phase.metadata_ or {})
            summaries.append(
                {
                    "card_id": str(phase.id),
                    "title": metadata.get("title") or metadata.get("objective") or "Untitled phase",
                    "phase_index": int(metadata.get("phase_index") or 0),
                    "objective": metadata.get("objective"),
                    "estimated_start": metadata.get("estimated_start"),
                    "estimated_end": metadata.get("estimated_end"),
                    "entry_criteria": list(metadata.get("entry_criteria") or []),
                    "exit_criteria": list(metadata.get("exit_criteria") or []),
                    "feedback_gate_required": bool(metadata.get("feedback_gate_required", True)),
                    "phase_weight": metadata.get("phase_weight"),
                    "synthetic_phase": bool(metadata.get("synthetic_phase", False)),
                    "lifecycle_status": phase.lifecycle_status.value,
                    "progress": retrospective["progress"],
                    "task_count": retrospective["task_count"],
                    "occurrence_count": retrospective["occurrence_count"],
                    "completed_occurrence_count": retrospective["completed_occurrence_count"],
                    "needs_feedback": bool(metadata.get("feedback_gate_required", True))
                    and not ((metadata.get("feedback_gate") or {}).get("submitted_at"))
                    and phase.lifecycle_status == CardLifecycleStatus.ACTIVE,
                    "alignment_score": (metadata.get("feedback_gate") or {}).get("alignment_score"),
                }
            )
        return {
            "plan_card_id": str(plan_card.id),
            "current_phase_card_id": (plan_card.metadata_ or {}).get("current_phase_card_id"),
            "progress_mode": "weighted_phase",
            "weighted_progress": weighted_progress,
            "phases": summaries,
        }

    async def get_plan_card_by_legacy_plan(self, legacy_plan_id: UUID, user_id: UUID) -> Card | None:
        stmt = select(Card).where(
            Card.card_type == CardType.PLAN,
            Card.owner_id == user_id,
            Card.metadata_["legacy_plan_id"].as_string() == str(legacy_plan_id),
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def sync_legacy_plan_progress(
        self,
        legacy_plan_id: UUID,
        user_id: UUID,
    ) -> float | None:
        plan_card = await self.get_plan_card_by_legacy_plan(legacy_plan_id, user_id)
        if not plan_card:
            return None
        if not await self._has_complete_weighted_progress_projection(
            plan_card=plan_card,
            legacy_plan_id=legacy_plan_id,
            user_id=user_id,
        ):
            return None
        weighted_progress = await self.calculate_plan_progress(plan_card.id)
        legacy_plan = await self.db.get(Plan, legacy_plan_id)
        if legacy_plan and legacy_plan.user_id == user_id:
            legacy_plan.progress = weighted_progress
        metadata = dict(plan_card.metadata_ or {})
        metadata["progress"] = weighted_progress
        metadata["progress_mode"] = "weighted_phase"
        plan_card.metadata_ = metadata
        plan_card.version += 1
        await self.db.flush()
        return weighted_progress

    async def calculate_plan_progress(self, plan_card_id: UUID) -> float:
        phases = await self.get_plan_phases(plan_card_id)
        if not phases:
            return 0.0

        weights = []
        progress_values = []
        for phase in phases:
            metadata = dict(phase.metadata_ or {})
            retrospective = await self._build_phase_retrospective(phase.id)
            weights.append(float(metadata.get("phase_weight") or 1.0))
            progress_values.append(retrospective["progress"])

        total_weight = sum(weights) or float(len(weights))
        normalized = [weight / total_weight for weight in weights]
        return round(sum(weight * progress for weight, progress in zip(normalized, progress_values, strict=False)), 4)

    async def _has_complete_weighted_progress_projection(
        self,
        *,
        plan_card: Card,
        legacy_plan_id: UUID,
        user_id: UUID,
    ) -> bool:
        legacy_task_result = await self.db.execute(
            select(Task.id).where(
                Task.plan_id == legacy_plan_id,
                Task.user_id == user_id,
            )
        )
        legacy_task_ids = {str(task_id) for task_id in legacy_task_result.scalars().all()}
        if not legacy_task_ids:
            return True

        projected_task_ids: set[str] = set()
        for phase in await self.get_plan_phases(plan_card.id):
            for task_card in await self._get_phase_tasks(phase.id):
                legacy_task_id = (task_card.metadata_ or {}).get("legacy_task_id")
                if legacy_task_id:
                    projected_task_ids.add(str(legacy_task_id))

        return projected_task_ids == legacy_task_ids

    async def _get_owned_plan(self, plan_card_id: UUID, user_id: UUID) -> Card:
        plan_card = await self.card_service.get_card(plan_card_id)
        if not plan_card or plan_card.card_type != CardType.PLAN or plan_card.owner_id != user_id:
            raise ValueError("Plan card not found")
        return plan_card

    async def _get_owned_phase(self, phase_card_id: UUID, user_id: UUID) -> Card:
        phase_card = await self.card_service.get_card(phase_card_id)
        if not phase_card or phase_card.card_type != CardType.PHASE or phase_card.owner_id != user_id:
            raise ValueError("Phase not found")
        return phase_card

    async def _get_parent_plan(self, phase_card_id: UUID) -> Card | None:
        parents = await self.edge_service.get_parents(
            phase_card_id,
            edge_type=EdgeType.CONTAINS,
            active_only=True,
        )
        for _, parent in parents:
            if parent.card_type == CardType.PLAN:
                return parent
        return None

    async def _get_phase_tasks(self, phase_card_id: UUID) -> list[Card]:
        children = await self.edge_service.get_children(
            phase_card_id,
            edge_type=EdgeType.CONTAINS,
            active_only=True,
        )
        return [card for _, card in children if card.card_type == CardType.TASK]

    async def _find_next_phase_id(self, phase_card_id: UUID) -> UUID | None:
        plan_card = await self._get_parent_plan(phase_card_id)
        if not plan_card:
            return None
        phases = await self.get_plan_phases(plan_card.id)
        ordered_ids = [phase.id for phase in phases]
        if phase_card_id not in ordered_ids:
            return None
        index = ordered_ids.index(phase_card_id)
        return ordered_ids[index + 1] if index + 1 < len(ordered_ids) else None

    async def _reindex_phases(self, plan_card_id: UUID) -> None:
        phase_pairs = await self.edge_service.get_children(
            plan_card_id,
            edge_type=EdgeType.CONTAINS,
            active_only=True,
        )
        phases = [(edge, card) for edge, card in phase_pairs if card.card_type == CardType.PHASE]
        phases.sort(key=lambda pair: (pair[0].order_index if pair[0].order_index is not None else 10_000, pair[1].created_at))
        for index, (edge, phase) in enumerate(phases):
            edge.order_index = index
            metadata = dict(phase.metadata_ or {})
            metadata["phase_index"] = index + 1
            phase.metadata_ = metadata
            phase.version += 1
        await self.db.flush()

    async def _replace_synthetic_phase_if_needed(self, plan_card: Card, new_phase: Card) -> None:
        phases = await self.get_plan_phases(plan_card.id)
        real_phases = [phase for phase in phases if not bool((phase.metadata_ or {}).get("synthetic_phase"))]
        synthetic_phases = [phase for phase in phases if bool((phase.metadata_ or {}).get("synthetic_phase"))]
        if len(real_phases) != 1 or not synthetic_phases:
            await self._sync_plan_phase_pointer(plan_card, new_phase.id)
            return

        synthetic = synthetic_phases[0]
        task_edges = await self.edge_service.get_children(
            synthetic.id,
            edge_type=EdgeType.CONTAINS,
            active_only=True,
        )
        for edge, task_card in task_edges:
            if task_card.card_type != CardType.TASK:
                continue
            await self.card_operations.move_card(
                card_id=task_card.id,
                new_parent_card_id=new_phase.id,
                user_id=task_card.owner_id,
            )
            edge.active = False

        parent_edges = await self.edge_service.get_parents(
            synthetic.id,
            edge_type=EdgeType.CONTAINS,
            active_only=True,
        )
        for edge, parent in parent_edges:
            if parent.id == plan_card.id:
                edge.active = False
        metadata = dict(synthetic.metadata_ or {})
        metadata["synthetic_replaced_by"] = str(new_phase.id)
        synthetic.metadata_ = metadata
        synthetic.lifecycle_status = CardLifecycleStatus.ARCHIVED
        synthetic.version += 1
        await self.db.flush()
        await self._sync_plan_phase_pointer(plan_card, new_phase.id)

    async def _sync_plan_phase_pointer(self, plan_card: Card, phase_card_id: UUID | None) -> None:
        metadata = dict(plan_card.metadata_ or {})
        phases = await self.get_plan_phases(plan_card.id)
        current_index = None
        if phase_card_id:
            for phase in phases:
                if phase.id == phase_card_id:
                    current_index = int((phase.metadata_ or {}).get("phase_index") or 0)
                    break
        metadata["current_phase_card_id"] = str(phase_card_id) if phase_card_id else None
        metadata["current_phase_index"] = current_index
        plan_card.metadata_ = metadata
        plan_card.version += 1
        await self.db.flush()

    async def _refresh_plan_progress(self, plan_card: Card, user_id: UUID) -> float:
        legacy_plan_id = (plan_card.metadata_ or {}).get("legacy_plan_id")
        if legacy_plan_id:
            return await self.sync_legacy_plan_progress(UUID(str(legacy_plan_id)), user_id) or 0.0
        return await self.calculate_plan_progress(plan_card.id)

    async def _build_phase_retrospective(self, phase_card_id: UUID) -> dict[str, Any]:
        phase_card = await self.card_service.get_card(phase_card_id)
        if not phase_card:
            raise ValueError("Phase not found")
        task_cards = await self._get_phase_tasks(phase_card_id)
        task_ids = [task.id for task in task_cards]

        occurrence_count = 0
        completed_occurrence_count = 0
        if task_ids:
            occurrence_stmt = select(TaskOccurrence).where(
                TaskOccurrence.phase_card_id == phase_card_id,
                TaskOccurrence.series_card_id.in_(task_ids),
                TaskOccurrence.occurrence_status != OccurrenceStatus.CANCELLED,
            )
            occurrence_result = await self.db.execute(occurrence_stmt)
            occurrences = list(occurrence_result.scalars().all())
            occurrence_count = len(occurrences)
            completed_occurrence_count = sum(
                1
                for occurrence in occurrences
                if occurrence.occurrence_status == OccurrenceStatus.COMPLETED
            )
        else:
            occurrences = []

        completed_task_count = sum(
            1 for task in task_cards if task.lifecycle_status == CardLifecycleStatus.COMPLETED
        )
        task_count = len(task_cards)

        if occurrence_count > 0:
            progress = completed_occurrence_count / occurrence_count
        elif task_count > 0:
            progress = completed_task_count / task_count
        elif phase_card.lifecycle_status == CardLifecycleStatus.COMPLETED:
            progress = 1.0
        else:
            progress = 0.0

        return {
            "task_count": task_count,
            "completed_task_count": completed_task_count,
            "occurrence_count": occurrence_count,
            "completed_occurrence_count": completed_occurrence_count,
            "progress": round(progress, 4),
            "missed_occurrence_count": sum(
                1
                for occurrence in occurrences
                if occurrence.occurrence_status == OccurrenceStatus.MISSED
            ),
            "deferred_occurrence_count": sum(
                1
                for occurrence in occurrences
                if occurrence.occurrence_status == OccurrenceStatus.DEFERRED
            ),
        }

    def _compute_alignment_score(self, feedback: dict[str, Any]) -> float:
        rating = float(feedback.get("rating") or 3)
        normalized_rating = max(0.0, min(1.0, rating / 5.0))
        if feedback.get("life_changed"):
            normalized_rating -= 0.15
        if feedback.get("blocked"):
            normalized_rating -= 0.2
        if feedback.get("request_compass_review"):
            normalized_rating -= 0.2
        return round(max(0.0, min(1.0, normalized_rating)), 2)
