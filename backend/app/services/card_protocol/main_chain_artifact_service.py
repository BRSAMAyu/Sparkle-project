"""
Phase 4 main-chain artifact hardening.

This service materializes the runtime state of the single main growth loop into
deterministic, versioned planning artifacts:

- ACTIVE_PHASE_PACK: what the user should work on right now
- REFLECTION_REPORT: what happened, what worked, what failed, and what the
  system learned

The implementation is intentionally pragmatic: it does not try to model every
possible future artifact field, but it does make the main scenario stable,
inspectable, and replayable.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import (
    ArtifactType,
    Card,
    CardEdge,
    CardType,
    EdgeType,
    InterventionOutcomeStatus,
    InterventionRecord,
    PlanningArtifact,
    TaskOccurrence,
)
from app.models.task import Task
from app.models.task_feedback import TaskFeedback
from app.services.card_protocol.decision_log_service import DecisionLogService
from app.services.card_protocol.risk_register_service import RiskRegisterService
from app.services.card_service import CardService
from app.services.plan_state_service import PlanStateService
from app.services.planning_artifact_service import PlanningArtifactService
from app.core.event_bus import EventBus


class MainChainArtifactService:
    """Build and refresh deterministic main-chain artifacts for a plan."""

    ACTIVE_PHASE_PACK_COMPARE_IGNORE = {"generated_at", "generated_reason"}
    REFLECTION_REPORT_COMPARE_IGNORE = {"generated_at", "generated_reason"}

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
        self.artifact_service = PlanningArtifactService(db, event_bus)
        self.card_service = CardService(db, event_bus)
        self.plan_state_service = PlanStateService(db, redis=None)
        self.decision_log_service = DecisionLogService(db, event_bus)
        self.risk_register_service = RiskRegisterService(db, event_bus)

    async def refresh_active_phase_pack(
        self,
        *,
        plan_card_id: UUID,
        generated_reason: str = "system_refresh",
    ) -> PlanningArtifact | None:
        plan_card = await self.card_service.get_card(plan_card_id)
        if not plan_card or plan_card.card_type != CardType.PLAN:
            return None

        payload = await self._build_active_phase_pack_payload(
            plan_card=plan_card,
            generated_reason=generated_reason,
        )
        based_on_versions = await self._collect_based_on_versions(
            plan_card_id,
            artifact_types=(
                ArtifactType.GLOBAL_COMPASS,
                ArtifactType.STRATEGY_MAP,
                ArtifactType.DECISION_LOG,
                ArtifactType.RISK_REGISTER,
            ),
        )
        artifact = await self._upsert_approved_artifact(
            plan_card_id=plan_card_id,
            artifact_type=ArtifactType.ACTIVE_PHASE_PACK,
            payload=payload,
            created_by_agent="phase4_main_chain",
            based_on_versions=based_on_versions,
            compare_ignore=self.ACTIVE_PHASE_PACK_COMPARE_IGNORE,
        )
        if artifact:
            await self._sync_plan_metadata(
                plan_card_id=plan_card_id,
                metadata_patch={
                    "active_phase_pack_artifact_id": str(artifact.id),
                    "active_phase_pack_version": artifact.version,
                },
            )
        return artifact

    async def refresh_reflection_report(
        self,
        *,
        plan_card_id: UUID,
        generated_reason: str = "system_refresh",
        linked_intervention_id: str | None = None,
        linked_feedback_id: str | None = None,
    ) -> PlanningArtifact | None:
        plan_card = await self.card_service.get_card(plan_card_id)
        if not plan_card or plan_card.card_type != CardType.PLAN:
            return None

        payload = await self._build_reflection_report_payload(
            plan_card=plan_card,
            generated_reason=generated_reason,
            linked_intervention_id=linked_intervention_id,
            linked_feedback_id=linked_feedback_id,
        )
        based_on_versions = await self._collect_based_on_versions(
            plan_card_id,
            artifact_types=(
                ArtifactType.ACTIVE_PHASE_PACK,
                ArtifactType.DECISION_LOG,
                ArtifactType.RISK_REGISTER,
                ArtifactType.GLOBAL_COMPASS,
                ArtifactType.STRATEGY_MAP,
            ),
        )
        artifact = await self._upsert_approved_artifact(
            plan_card_id=plan_card_id,
            artifact_type=ArtifactType.REFLECTION_REPORT,
            payload=payload,
            created_by_agent="phase4_reflection",
            based_on_versions=based_on_versions,
            compare_ignore=self.REFLECTION_REPORT_COMPARE_IGNORE,
        )
        if artifact:
            await self._sync_plan_metadata(
                plan_card_id=plan_card_id,
                metadata_patch={
                    "latest_reflection_report_id": str(artifact.id),
                    "latest_reflection_report_version": artifact.version,
                },
            )
        return artifact

    async def refresh_for_legacy_plan(
        self,
        *,
        legacy_plan_id: UUID,
        generated_reason: str,
        include_reflection: bool = False,
        linked_intervention_id: str | None = None,
        linked_feedback_id: str | None = None,
    ) -> dict[str, PlanningArtifact | None]:
        plan_card = await self._find_plan_card(legacy_plan_id)
        if not plan_card:
            return {"active_phase_pack": None, "reflection_report": None}

        active = await self.refresh_active_phase_pack(
            plan_card_id=plan_card.id,
            generated_reason=generated_reason,
        )
        reflection = None
        if include_reflection:
            reflection = await self.refresh_reflection_report(
                plan_card_id=plan_card.id,
                generated_reason=generated_reason,
                linked_intervention_id=linked_intervention_id,
                linked_feedback_id=linked_feedback_id,
            )
        return {
            "active_phase_pack": active,
            "reflection_report": reflection,
        }

    async def _build_active_phase_pack_payload(
        self,
        *,
        plan_card: Card,
        generated_reason: str,
    ) -> dict[str, Any]:
        phase_card = await self._resolve_current_phase(plan_card)
        task_cards = await self._get_phase_tasks(phase_card.id) if phase_card else []
        knowledge_refs = await self._collect_task_knowledge_refs(task_cards)
        occurrences = await self._get_plan_occurrences(plan_card.id)
        pending_interventions = await self._get_pending_interventions(plan_card.id)
        active_risks = await self.risk_register_service.get_active_risks(plan_card.id)
        plan_state = await self._get_plan_state_for_card(plan_card)
        adaptive_adjustments = dict(((plan_state.facts or {}).get("adaptive_adjustments")) or {}) if plan_state else {}
        feedback_log = list((plan_state.feedback_log or [])[-10:]) if plan_state else []

        task_status_counts = Counter(card.lifecycle_status.value for card in task_cards)
        occurrence_status_counts = Counter(occurrence.occurrence_status.value for occurrence in occurrences)

        tasks_payload = []
        for card in task_cards[:20]:
            metadata = dict(card.metadata_ or {})
            tasks_payload.append(
                {
                    "card_id": str(card.id),
                    "legacy_task_id": metadata.get("legacy_task_id"),
                    "title": metadata.get("title") or metadata.get("name") or "",
                    "description": metadata.get("description") or "",
                    "lifecycle_status": card.lifecycle_status.value,
                    "due_date": metadata.get("due_date"),
                    "order_index": metadata.get("order_index"),
                    "difficulty": metadata.get("difficulty"),
                    "effort_minutes_default": metadata.get("effort_minutes_default"),
                    "knowledge_refs": knowledge_refs.get(card.id, []),
                }
            )

        occurrences_payload = [
            {
                "occurrence_id": str(occ.id),
                "series_card_id": str(occ.series_card_id),
                "scheduled_for": occ.scheduled_for.isoformat() if occ.scheduled_for else None,
                "window_start": occ.window_start.isoformat() if occ.window_start else None,
                "window_end": occ.window_end.isoformat() if occ.window_end else None,
                "status": occ.occurrence_status.value,
                "deferral_count": occ.deferral_count,
            }
            for occ in occurrences[:20]
        ]

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "generated_reason": generated_reason,
            "plan": {
                "card_id": str(plan_card.id),
                "legacy_plan_id": (plan_card.metadata_ or {}).get("legacy_plan_id"),
                "name": (plan_card.metadata_ or {}).get("name") or "",
                "description": (plan_card.metadata_ or {}).get("description") or "",
                "lifecycle_status": plan_card.lifecycle_status.value,
                "progress": (plan_card.metadata_ or {}).get("progress"),
                "legacy_plan_stage": (plan_card.metadata_ or {}).get("legacy_plan_stage"),
            },
            "phase": {
                "card_id": str(phase_card.id) if phase_card else None,
                "title": (phase_card.metadata_ or {}).get("title") if phase_card else "",
                "objective": (phase_card.metadata_ or {}).get("objective") if phase_card else "",
                "lifecycle_status": phase_card.lifecycle_status.value if phase_card else None,
                "task_count": len(task_cards),
            },
            "execution_parameters": {
                "adaptive_adjustments": adaptive_adjustments,
                "has_active_compilation": bool(adaptive_adjustments.get("compilation_meta")),
                "plan_state_version": plan_state.version if plan_state else None,
            },
            "tasks": tasks_payload,
            "occurrences": occurrences_payload,
            "pending_interventions": pending_interventions,
            "active_risks": active_risks[:10],
            "recent_feedback": feedback_log,
            "metrics": {
                "task_status_counts": dict(task_status_counts),
                "occurrence_status_counts": dict(occurrence_status_counts),
                "pending_intervention_count": len(pending_interventions),
                "active_risk_count": len(active_risks),
                "recent_feedback_count": len(feedback_log),
            },
            "next_focus_candidates": [
                task["title"]
                for task in tasks_payload
                if task.get("lifecycle_status") == "ACTIVE"
            ][:3],
        }

    async def _build_reflection_report_payload(
        self,
        *,
        plan_card: Card,
        generated_reason: str,
        linked_intervention_id: str | None,
        linked_feedback_id: str | None,
    ) -> dict[str, Any]:
        plan_state = await self._get_plan_state_for_card(plan_card)
        feedback_log = list((plan_state.feedback_log or [])[-20:]) if plan_state else []
        task_feedbacks = await self._get_recent_task_feedbacks(plan_card)
        interventions = await self._get_recent_interventions(plan_card.id)
        decision_entries = await self.decision_log_service.get_all_entries(plan_card.id, limit=50)
        active_risks = await self.risk_register_service.get_active_risks(plan_card.id)
        active_phase_pack = await self.artifact_service.get_approved(plan_card.id, ArtifactType.ACTIVE_PHASE_PACK)

        what_worked: list[dict[str, Any]] = []
        what_failed: list[dict[str, Any]] = []
        effective_by_trigger: dict[str, int] = defaultdict(int)
        effective_by_strategy: dict[str, int] = defaultdict(int)

        for intervention in interventions:
            item = {
                "record_id": str(intervention.id),
                "trigger_type": intervention.trigger_type.value,
                "delivery_strategy": intervention.delivery_strategy.value,
                "outcome_status": intervention.outcome_status.value,
                "acceptance_status": intervention.acceptance_status.value,
                "created_at": intervention.created_at.isoformat() if intervention.created_at else None,
            }
            if intervention.outcome_status == InterventionOutcomeStatus.EFFECTIVE:
                what_worked.append(item)
                effective_by_trigger[intervention.trigger_type.value] += 1
                effective_by_strategy[intervention.delivery_strategy.value] += 1
            elif intervention.outcome_status == InterventionOutcomeStatus.INEFFECTIVE:
                what_failed.append(item)

        for entry in feedback_log:
            if self._feedback_is_positive(entry):
                what_worked.append(
                    {
                        "type": "feedback_signal",
                        "content": entry.get("content", ""),
                        "timestamp": entry.get("timestamp"),
                    }
                )
            elif self._feedback_is_negative(entry):
                what_failed.append(
                    {
                        "type": "feedback_signal",
                        "content": entry.get("content", ""),
                        "timestamp": entry.get("timestamp"),
                    }
                )

        reflection_snippets = []
        for feedback in task_feedbacks[:10]:
            reflection_payload = feedback.reflection_payload or {}
            reflection_snippets.append(
                {
                    "feedback_id": str(feedback.id),
                    "task_id": str(feedback.task_id),
                    "category": feedback.category,
                    "selected_option": reflection_payload.get("selected_option"),
                    "free_text": reflection_payload.get("free_text"),
                    "submitted_at": reflection_payload.get("submitted_at"),
                }
            )

        decision_summary = Counter(entry.get("confirmation_status", "PENDING") for entry in decision_entries)
        for status in ("PENDING", "CONFIRMED", "CONTRADICTED", "LEARNING"):
            decision_summary.setdefault(status, 0)
        recommended_next_focus = self._recommended_next_focus(
            what_failed=what_failed,
            active_risks=active_risks,
            active_phase_pack=active_phase_pack.payload if active_phase_pack else {},
        )

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "generated_reason": generated_reason,
            "linked_intervention_id": linked_intervention_id,
            "linked_feedback_id": linked_feedback_id,
            "plan": {
                "card_id": str(plan_card.id),
                "legacy_plan_id": (plan_card.metadata_ or {}).get("legacy_plan_id"),
                "name": (plan_card.metadata_ or {}).get("name") or "",
                "lifecycle_status": plan_card.lifecycle_status.value,
            },
            "summary": {
                "intervention_count": len(interventions),
                "effective_intervention_count": len(
                    [
                        item
                        for item in interventions
                        if item.outcome_status == InterventionOutcomeStatus.EFFECTIVE
                    ]
                ),
                "ineffective_intervention_count": len(
                    [
                        item
                        for item in interventions
                        if item.outcome_status == InterventionOutcomeStatus.INEFFECTIVE
                    ]
                ),
                "task_feedback_count": len(task_feedbacks),
                "active_risk_count": len(active_risks),
            },
            "what_worked": what_worked[:12],
            "what_failed": what_failed[:12],
            "reflection_signals": reflection_snippets,
            "decision_summary": dict(decision_summary),
            "system_learning": {
                "effective_by_trigger": dict(effective_by_trigger),
                "effective_by_strategy": dict(effective_by_strategy),
            },
            "active_risks_snapshot": active_risks[:10],
            "recommended_next_focus": recommended_next_focus,
            "recent_feedback": feedback_log[-10:],
        }

    async def _upsert_approved_artifact(
        self,
        *,
        plan_card_id: UUID,
        artifact_type: ArtifactType,
        payload: dict[str, Any],
        created_by_agent: str,
        based_on_versions: dict[str, int],
        compare_ignore: set[str],
    ) -> PlanningArtifact | None:
        current = await self.artifact_service.get_approved(plan_card_id, artifact_type)
        if current and self._normalized_payload(current.payload, compare_ignore) == self._normalized_payload(payload, compare_ignore):
            return current

        artifact = await self.artifact_service.create_artifact(
            plan_card_id=plan_card_id,
            artifact_type=artifact_type,
            payload=payload,
            created_by_agent=created_by_agent,
            based_on_versions=based_on_versions,
        )
        await self.artifact_service.propose_artifact(artifact.id)
        return await self.artifact_service.auto_approve_artifact(artifact.id)

    async def _collect_based_on_versions(
        self,
        plan_card_id: UUID,
        *,
        artifact_types: tuple[ArtifactType, ...],
    ) -> dict[str, int]:
        versions: dict[str, int] = {}
        for artifact_type in artifact_types:
            artifact = await self.artifact_service.get_approved(plan_card_id, artifact_type)
            if artifact:
                versions[artifact_type.value] = artifact.version
        return versions

    async def _resolve_current_phase(self, plan_card: Card) -> Card | None:
        current_phase_id = (plan_card.metadata_ or {}).get("current_phase_card_id")
        if current_phase_id:
            try:
                return await self.card_service.get_card(UUID(str(current_phase_id)))
            except (TypeError, ValueError):
                pass

        stmt = (
            select(Card)
            .join(CardEdge, CardEdge.to_card_id == Card.id)
            .where(
                CardEdge.from_card_id == plan_card.id,
                CardEdge.edge_type == EdgeType.CONTAINS,
                CardEdge.active.is_(True),
                Card.card_type == CardType.PHASE,
                Card.not_deleted_filter(),
            )
            .order_by(CardEdge.order_index.asc(), Card.created_at.asc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_phase_tasks(self, phase_card_id: UUID) -> list[Card]:
        stmt = (
            select(Card)
            .join(CardEdge, CardEdge.to_card_id == Card.id)
            .where(
                CardEdge.from_card_id == phase_card_id,
                CardEdge.edge_type == EdgeType.CONTAINS,
                CardEdge.active.is_(True),
                Card.card_type == CardType.TASK,
                Card.not_deleted_filter(),
            )
            .order_by(CardEdge.order_index.asc(), Card.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _collect_task_knowledge_refs(
        self,
        task_cards: list[Card],
    ) -> dict[UUID, list[dict[str, Any]]]:
        if not task_cards:
            return {}
        task_ids = [task.id for task in task_cards]
        stmt = (
            select(CardEdge, Card)
            .join(Card, Card.id == CardEdge.to_card_id)
            .where(
                CardEdge.from_card_id.in_(task_ids),
                CardEdge.edge_type == EdgeType.REFERENCES,
                CardEdge.active.is_(True),
                Card.card_type == CardType.KNOWLEDGE,
                Card.not_deleted_filter(),
            )
        )
        result = await self.db.execute(stmt)
        refs: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
        for edge, knowledge_card in result.all():
            refs[edge.from_card_id].append(
                {
                    "card_id": str(knowledge_card.id),
                    "name": (knowledge_card.metadata_ or {}).get("name") or "",
                    "mastery_state": (knowledge_card.metadata_ or {}).get("mastery_state"),
                }
            )
        return refs

    async def _get_plan_occurrences(self, plan_card_id: UUID) -> list[TaskOccurrence]:
        stmt = (
            select(TaskOccurrence)
            .where(TaskOccurrence.plan_card_id == plan_card_id)
            .order_by(
                TaskOccurrence.scheduled_for.asc(),
                TaskOccurrence.window_start.asc(),
                TaskOccurrence.created_at.desc(),
            )
            .limit(30)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_pending_interventions(self, plan_card_id: UUID) -> list[dict[str, Any]]:
        stmt = (
            select(InterventionRecord)
            .where(
                InterventionRecord.plan_card_id == plan_card_id,
                InterventionRecord.outcome_status == InterventionOutcomeStatus.PENDING,
                InterventionRecord.not_deleted_filter(),
            )
            .order_by(desc(InterventionRecord.created_at))
            .limit(10)
        )
        result = await self.db.execute(stmt)
        records = list(result.scalars().all())
        return [
            {
                "record_id": str(record.id),
                "trigger_type": record.trigger_type.value,
                "acceptance_status": record.acceptance_status.value,
                "delivery_strategy": record.delivery_strategy.value,
                "delivery_channel": record.delivery_channel.value,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
            for record in records
        ]

    async def _get_recent_interventions(self, plan_card_id: UUID) -> list[InterventionRecord]:
        stmt = (
            select(InterventionRecord)
            .where(
                InterventionRecord.plan_card_id == plan_card_id,
                InterventionRecord.not_deleted_filter(),
            )
            .order_by(desc(InterventionRecord.created_at))
            .limit(20)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_recent_task_feedbacks(self, plan_card: Card) -> list[TaskFeedback]:
        legacy_plan_id = (plan_card.metadata_ or {}).get("legacy_plan_id")
        if not legacy_plan_id:
            return []
        try:
            legacy_plan_uuid = UUID(str(legacy_plan_id))
        except (TypeError, ValueError):
            return []

        stmt = (
            select(TaskFeedback)
            .join(Task, Task.id == TaskFeedback.task_id)
            .where(Task.plan_id == legacy_plan_uuid)
            .order_by(desc(TaskFeedback.created_at))
            .limit(20)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_plan_state_for_card(self, plan_card: Card):
        legacy_plan_id = (plan_card.metadata_ or {}).get("legacy_plan_id")
        if not legacy_plan_id:
            return None
        try:
            plan_id = UUID(str(legacy_plan_id))
        except (TypeError, ValueError):
            return None
        return await self.plan_state_service.get_plan_state(plan_card.owner_id, plan_id)

    async def _find_plan_card(self, legacy_plan_id: UUID) -> Card | None:
        stmt = (
            select(Card)
            .where(
                Card.card_type == CardType.PLAN,
                Card.metadata_["legacy_plan_id"].as_string() == str(legacy_plan_id),
                Card.not_deleted_filter(),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _sync_plan_metadata(
        self,
        *,
        plan_card_id: UUID,
        metadata_patch: dict[str, Any],
    ) -> None:
        plan_card = await self.card_service.get_card(plan_card_id)
        if not plan_card:
            return
        current = dict(plan_card.metadata_ or {})
        if all(current.get(key) == value for key, value in metadata_patch.items()):
            return
        current.update(metadata_patch)
        plan_card.metadata_ = current
        plan_card.version += 1
        await self.db.flush()

    @staticmethod
    def _normalized_payload(payload: dict[str, Any] | None, ignore_keys: set[str]) -> dict[str, Any]:
        payload = deepcopy(payload or {})
        for key in ignore_keys:
            payload.pop(key, None)
        return payload

    @staticmethod
    def _feedback_is_positive(entry: dict[str, Any]) -> bool:
        content = str(entry.get("content", "")).lower()
        positive_markers = ("better", "improved", "顺了", "更顺", "更好", "继续", "能做下去", "容易")
        return any(marker in content for marker in positive_markers)

    @staticmethod
    def _feedback_is_negative(entry: dict[str, Any]) -> bool:
        content = str(entry.get("content", "")).lower()
        negative_markers = ("too hard", "failed", "aborted", "卡住", "太难", "超时", "放弃", "不懂")
        return any(marker in content for marker in negative_markers)

    @staticmethod
    def _recommended_next_focus(
        *,
        what_failed: list[dict[str, Any]],
        active_risks: list[dict[str, Any]],
        active_phase_pack: dict[str, Any],
    ) -> list[str]:
        recommendations: list[str] = []
        for risk in active_risks[:3]:
            description = str(risk.get("description") or "").strip()
            if description:
                recommendations.append(description)
        for item in what_failed[:3]:
            content = str(item.get("content") or item.get("trigger_type") or "").strip()
            if content:
                recommendations.append(content)
        for candidate in list((active_phase_pack or {}).get("next_focus_candidates") or [])[:3]:
            text = str(candidate).strip()
            if text:
                recommendations.append(f"Resume: {text}")
        deduped: list[str] = []
        seen: set[str] = set()
        for item in recommendations:
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        return deduped[:5]
