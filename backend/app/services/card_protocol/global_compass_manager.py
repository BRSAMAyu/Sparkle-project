"""
GlobalCompassManager — Manages the GLOBAL_COMPASS artifact lifecycle.

The compass is the user's persistent parameter source: north star goal,
success criteria, hard constraints, pacing philosophy, risk tolerance,
and learning style hints.

Phase 3 of the Card Protocol.
"""
from __future__ import annotations

from copy import deepcopy
import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import ArtifactType, Card, CardCreatedBy, CardType
from app.services.planning_artifact_service import PlanningArtifactService
from app.core.event_bus import EventBus


# Default compass payload when no user profile data is available
_DEFAULT_COMPASS = {
    "north_star": "",
    "success_criteria": [],
    "values": [],
    "hard_constraints": {
        "max_session_minutes": 90,
        "max_concurrent_tasks": 3,
        "preferred_time_slots": [],
    },
    "pacing_philosophy": "adaptive",
    "risk_tolerance": "moderate",
    "learning_style_hints": {
        "reflection_depth": "light",
        "feedback_preference": "regular",
    },
}


class GlobalCompassManager:
    """Manages GLOBAL_COMPASS artifact lifecycle for a plan."""

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
        self.artifact_service = PlanningArtifactService(db, event_bus)

    async def initialize(
        self,
        *,
        plan_card_id: uuid.UUID,
        user_id: uuid.UUID,
        user_profile: dict | None = None,
        plan_context: dict | None = None,
    ) -> "PlanningArtifact":
        """Create initial GLOBAL_COMPASS from user profile + plan context.

        Auto-approves since this is a system-generated initial artifact.
        """
        payload = self._build_initial_payload(user_profile, plan_context)

        artifact = await self.artifact_service.create_artifact(
            plan_card_id=plan_card_id,
            artifact_type=ArtifactType.GLOBAL_COMPASS,
            payload=payload,
            created_by_agent="system_init",
        )
        await self.artifact_service.propose_artifact(artifact.id)
        approved = await self.artifact_service.auto_approve_artifact(artifact.id)
        if approved:
            await self._sync_plan_metadata(plan_card_id, approved.id, approved.version)
        logger.info(
            "GlobalCompassManager: initialized compass v{} for plan {}",
            artifact.version,
            plan_card_id,
        )
        return approved or artifact

    async def get_parameters(self, plan_card_id: uuid.UUID) -> dict:
        """Return approved compass parameters, or empty dict if none."""
        artifact = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.GLOBAL_COMPASS
        )
        return dict(artifact.payload) if artifact else {}

    async def get_or_initialize(
        self,
        *,
        plan_card_id: uuid.UUID,
        user_id: uuid.UUID,
        user_profile: dict | None = None,
        plan_context: dict | None = None,
    ) -> "PlanningArtifact":
        """Get existing APPROVED compass or initialize a new one."""
        existing = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.GLOBAL_COMPASS
        )
        if existing:
            return existing
        return await self.initialize(
            plan_card_id=plan_card_id,
            user_id=user_id,
            user_profile=user_profile,
            plan_context=plan_context,
        )

    async def propose_update(
        self,
        plan_card_id: uuid.UUID,
        updates: dict,
        evidence: dict | None = None,
    ) -> "PlanningArtifact | None":
        """Propose a compass update. Creates a new version.

        The caller must resolve the plan_card_id from user_id + legacy_plan_id.
        """
        current = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.GLOBAL_COMPASS
        )
        if not current:
            logger.warning(
                "GlobalCompassManager: no current compass for plan {}, cannot update",
                plan_card_id,
            )
            return None

        merged_payload = _deep_merge(dict(current.payload or {}), updates)

        based_on = {"GLOBAL_COMPASS": current.version}

        artifact = await self.artifact_service.create_artifact(
            plan_card_id=plan_card_id,
            artifact_type=ArtifactType.GLOBAL_COMPASS,
            payload=merged_payload,
            created_by_agent="system_adapt",
            based_on_versions=based_on,
        )

        # System-generated updates are auto-approved
        await self.artifact_service.propose_artifact(artifact.id)
        approved = await self.artifact_service.auto_approve_artifact(artifact.id)
        if approved:
            await self._sync_plan_metadata(plan_card_id, approved.id, approved.version)
        return approved

    def _build_initial_payload(
        self, user_profile: dict | None, plan_context: dict | None
    ) -> dict:
        """Build compass payload from available user data."""
        payload = deepcopy(_DEFAULT_COMPASS)

        if user_profile:
            prefs = user_profile.get("preferences", {})
            inferred = user_profile.get("inferred", {})

            # Pacing from inferred data
            pacing = inferred.get("pacing_philosophy") or prefs.get("pacing_philosophy")
            if pacing in ("steady", "sprint", "adaptive"):
                payload["pacing_philosophy"] = pacing

            # Risk tolerance
            risk = inferred.get("risk_tolerance") or prefs.get("risk_tolerance")
            if risk in ("cautious", "moderate", "aggressive"):
                payload["risk_tolerance"] = risk

            # Reflection depth → learning style hints
            reflection = inferred.get("task_reflection_depth")
            if reflection in ("none", "light", "deep"):
                payload["learning_style_hints"]["reflection_depth"] = reflection

            # Max concurrent tasks from preferences
            max_concurrent = prefs.get("max_concurrent_tasks")
            if isinstance(max_concurrent, int) and max_concurrent > 0:
                payload["hard_constraints"]["max_concurrent_tasks"] = max_concurrent

            # Preferred time slots
            slots = prefs.get("preferred_time_slots")
            if isinstance(slots, list):
                payload["hard_constraints"]["preferred_time_slots"] = slots

        if plan_context:
            # North star from plan goal
            goal = plan_context.get("goal")
            if goal:
                payload["north_star"] = str(goal)

        return payload

    async def _sync_plan_metadata(
        self,
        plan_card_id: uuid.UUID,
        artifact_id: uuid.UUID,
        version: int,
    ) -> None:
        stmt = select(Card).where(
            Card.id == plan_card_id,
            Card.card_type == CardType.PLAN,
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        plan_card = result.scalar_one_or_none()
        if not plan_card:
            return

        metadata = dict(plan_card.metadata_ or {})
        patch = {
            "global_compass_artifact_id": str(artifact_id),
            "global_compass_version": version,
        }
        if any(metadata.get(key) != value for key, value in patch.items()):
            metadata.update(patch)
            plan_card.metadata_ = metadata
            plan_card.version += 1
            plan_card.updated_by = CardCreatedBy.SYSTEM
            await self.db.flush()


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Deep merge overlay into base (returns new dict, doesn't mutate inputs)."""
    result = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result
