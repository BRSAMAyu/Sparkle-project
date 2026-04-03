"""
DecisionLogService — Records parameter compilation decisions for traceability.

Each decision log is stored as a PlanningArtifact(DECISION_LOG) with an entries
array. Every parameter compilation appends an entry describing what changed,
why, what was expected, and later whether it was confirmed or contradicted.

Phase 3 of the Card Protocol.
"""
from __future__ import annotations

from copy import deepcopy
import uuid
from datetime import datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import ArtifactType, PlanningArtifact
from app.services.planning_artifact_service import PlanningArtifactService
from app.core.event_bus import EventBus


class DecisionLogService:
    """Records parameter compilation decisions in DECISION_LOG artifacts."""

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
        self.artifact_service = PlanningArtifactService(db, event_bus)

    async def record_decision(
        self,
        *,
        plan_card_id: uuid.UUID,
        decision: str,
        rationale: str,
        trigger: str,
        input_artifacts: dict[str, str] | None = None,
        expected_observation: str | None = None,
        linked_intervention_id: str | None = None,
    ) -> dict | None:
        """Append a decision entry to the plan's DECISION_LOG artifact.

        Returns the entry dict (with id) or None on failure.
        """
        entry_id = str(uuid.uuid4())
        entry = {
            "id": entry_id,
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision,
            "rationale": rationale,
            "trigger": trigger,
            "input_artifacts": input_artifacts or {},
            "expected_observation": expected_observation or "",
            "confirmation_status": "PENDING",
            "linked_intervention_id": linked_intervention_id,
        }

        # Get or create the DECISION_LOG artifact
        artifact = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.DECISION_LOG
        )

        if artifact:
            # Append to existing
            payload = deepcopy(artifact.payload or {})
            entries = list(payload.get("entries", []))
            entries.append(entry)
            payload["entries"] = entries
            await self.artifact_service.update_payload(artifact.id, payload)
        else:
            # Create new DECISION_LOG with this entry
            await self.artifact_service.get_or_create_approved(
                plan_card_id=plan_card_id,
                artifact_type=ArtifactType.DECISION_LOG,
                default_payload={"entries": [entry]},
                created_by_agent="parameter_compiler",
            )

        logger.debug(
            "DecisionLogService: recorded decision '{}' for plan {}",
            decision[:60],
            plan_card_id,
        )
        return entry

    async def confirm_entry(
        self,
        plan_card_id: uuid.UUID,
        entry_id: str,
        evidence: dict | None = None,
    ) -> bool:
        """Mark a decision log entry as CONFIRMED."""
        return await self._update_confirmation(
            plan_card_id, entry_id, "CONFIRMED", evidence
        )

    async def contradict_entry(
        self,
        plan_card_id: uuid.UUID,
        entry_id: str,
        evidence: dict | None = None,
    ) -> bool:
        """Mark a decision log entry as CONTRADICTED."""
        return await self._update_confirmation(
            plan_card_id, entry_id, "CONTRADICTED", evidence
        )

    async def mark_learning(
        self,
        plan_card_id: uuid.UUID,
        entry_id: str,
        learning_note: str,
    ) -> bool:
        """Mark a decision log entry as LEARNING with a note."""
        return await self._update_confirmation(
            plan_card_id, entry_id, "LEARNING", {"learning_note": learning_note}
        )

    async def get_pending_confirmations(
        self, plan_card_id: uuid.UUID
    ) -> list[dict]:
        """Get all entries with confirmation_status == PENDING."""
        artifact = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.DECISION_LOG
        )
        if not artifact:
            return []
        entries = list(deepcopy((artifact.payload or {}).get("entries", [])))
        return [e for e in entries if e.get("confirmation_status") == "PENDING"]

    async def get_all_entries(
        self, plan_card_id: uuid.UUID, limit: int = 50
    ) -> list[dict]:
        """Get all entries for a plan's decision log."""
        artifact = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.DECISION_LOG
        )
        if not artifact:
            return []
        entries = list(deepcopy((artifact.payload or {}).get("entries", [])))
        return entries[-limit:]

    async def find_entry_by_intervention(
        self, plan_card_id: uuid.UUID, intervention_id: str
    ) -> dict | None:
        """Find the decision entry linked to a specific intervention."""
        entries = await self.get_all_entries(plan_card_id)
        for entry in entries:
            if entry.get("linked_intervention_id") == intervention_id:
                return entry
        return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _update_confirmation(
        self,
        plan_card_id: uuid.UUID,
        entry_id: str,
        status: str,
        evidence: dict | None = None,
    ) -> bool:
        """Update confirmation_status of a specific entry."""
        artifact = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.DECISION_LOG
        )
        if not artifact:
            return False

        payload = deepcopy(artifact.payload or {})
        entries = list(payload.get("entries", []))
        found = False
        for entry in entries:
            if entry.get("id") == entry_id:
                entry["confirmation_status"] = status
                if evidence:
                    entry["confirmation_evidence"] = evidence
                entry["confirmed_at"] = datetime.utcnow().isoformat()
                found = True
                break

        if not found:
            return False

        payload["entries"] = entries
        await self.artifact_service.update_payload(artifact.id, payload)

        logger.info(
            "DecisionLogService: entry {} marked as {} for plan {}",
            entry_id[:8],
            status,
            plan_card_id,
        )
        return True
