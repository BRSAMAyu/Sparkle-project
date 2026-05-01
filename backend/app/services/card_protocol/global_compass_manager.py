"""
GlobalCompassManager — Manages the GLOBAL_COMPASS artifact lifecycle.

The compass is the user's persistent parameter source: north star goal,
success criteria, hard constraints, pacing philosophy, risk tolerance,
and learning style hints.

Phase 3 of the Card Protocol.
"""
from __future__ import annotations

import re
import uuid
from copy import deepcopy

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.models.card_protocol import ArtifactStatus, ArtifactType, Card, CardCreatedBy, CardType, PlanningArtifact
from app.services.planning_artifact_service import PlanningArtifactService

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
    ) -> PlanningArtifact:
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
    ) -> PlanningArtifact:
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
    ) -> PlanningArtifact | None:
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

    async def build_compass_from_dossier(
        self,
        *,
        plan_card_id: uuid.UUID,
        dossier: PlanningArtifact | dict,
        user_id: uuid.UUID,
    ) -> PlanningArtifact:
        """Build a reviewable GLOBAL_COMPASS from an approved discovery dossier."""
        await self._get_owned_plan(plan_card_id, user_id)
        dossier_payload, dossier_version, dossier_id = self._normalize_dossier(dossier)
        current = await self.artifact_service.get_approved(plan_card_id, ArtifactType.GLOBAL_COMPASS)
        based_on = {"DISCOVERY_DOSSIER": dossier_version}
        if current:
            based_on["GLOBAL_COMPASS"] = current.version

        payload = self._build_payload_from_dossier(dossier_payload)
        artifact = await self.artifact_service.create_artifact(
            plan_card_id=plan_card_id,
            artifact_type=ArtifactType.GLOBAL_COMPASS,
            payload=payload,
            created_by_agent="discovery_pipeline",
            based_on_versions=based_on,
        )
        await self.artifact_service.propose_artifact(artifact.id)
        await self._sync_plan_metadata(
            plan_card_id,
            artifact.id,
            artifact.version,
            patch={
                "pending_global_compass_artifact_id": str(artifact.id),
                "workflow_state": "COMPASS_REVIEW",
                "discovery_dossier_artifact_id": str(dossier_id) if dossier_id else None,
            },
        )
        logger.info(
            "GlobalCompassManager: proposed dossier-driven compass v{} for plan {}",
            artifact.version,
            plan_card_id,
        )
        return artifact

    async def present_compass_for_review(
        self,
        *,
        plan_card_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        """Return the current compass review payload for UI/API consumption."""
        await self._get_owned_plan(plan_card_id, user_id)
        proposed = await self._get_latest_artifact_by_status(
            plan_card_id,
            ArtifactType.GLOBAL_COMPASS,
            ArtifactStatus.PROPOSED,
        )
        current = await self.artifact_service.get_approved(plan_card_id, ArtifactType.GLOBAL_COMPASS)
        artifact = proposed or current
        if artifact is None:
            raise ValueError("No compass artifact available for review")

        proposed_payload = dict(artifact.payload or {})
        current_payload = dict(current.payload or {}) if current else {}
        changed_fields = sorted(
            {
                key
                for key in set(current_payload.keys()) | set(proposed_payload.keys())
                if current_payload.get(key) != proposed_payload.get(key)
            }
        )
        return {
            "workflow_state": "COMPASS_REVIEW",
            "artifact_id": str(artifact.id),
            "artifact_status": artifact.status.value,
            "version": artifact.version,
            "proposed_payload": proposed_payload,
            "current_payload": current_payload,
            "changed_fields": changed_fields,
            "based_on_versions": dict(artifact.based_on_versions or {}),
        }

    async def user_approve_compass(
        self,
        *,
        artifact_id: uuid.UUID,
        user_id: uuid.UUID,
        edits: dict | None = None,
    ) -> PlanningArtifact:
        """Approve a dossier-driven compass after optional user edits."""
        artifact = await self.artifact_service.get_artifact(artifact_id)
        if artifact is None or artifact.artifact_type != ArtifactType.GLOBAL_COMPASS:
            raise ValueError("Compass artifact not found")
        await self._get_owned_plan(artifact.plan_card_id, user_id)

        if edits:
            artifact.payload = _deep_merge(dict(artifact.payload or {}), edits)

        if artifact.status == ArtifactStatus.DRAFT:
            await self.artifact_service.propose_artifact(artifact.id)
        elif artifact.status not in {ArtifactStatus.PROPOSED, ArtifactStatus.APPROVED}:
            raise ValueError("Compass artifact is not approvable")

        approved = artifact
        if artifact.status != ArtifactStatus.APPROVED:
            maybe_approved = await self.artifact_service.approve_artifact(artifact.id, approved_by_user_id=user_id)
            approved = maybe_approved or artifact

        await self._sync_plan_metadata(
            approved.plan_card_id,
            approved.id,
            approved.version,
            patch={
                "pending_global_compass_artifact_id": None,
                "workflow_state": "COMPASS_APPROVED",
            },
        )
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

    def _build_payload_from_dossier(self, dossier_payload: dict) -> dict:
        constraints = list(dossier_payload.get("constraints") or [])
        available_time = dossier_payload.get("available_time")
        hard_constraints = {
            "max_session_minutes": self._estimate_max_session_minutes(available_time),
            "max_concurrent_tasks": 3,
            "preferred_time_slots": [],
            "notes": constraints,
        }
        return {
            "north_star": dossier_payload.get("goal_statement") or "",
            "success_criteria": self._derive_success_criteria(dossier_payload),
            "values": list(dossier_payload.get("values") or []),
            "hard_constraints": hard_constraints,
            "pacing_philosophy": self._derive_pacing_philosophy(dossier_payload),
            "risk_tolerance": self._derive_risk_tolerance(dossier_payload),
            "learning_style_hints": {
                "reflection_depth": "deep" if dossier_payload.get("prior_attempts") else "light",
                "feedback_preference": "regular",
            },
            "source": {
                "type": "discovery_dossier",
                "summary": dossier_payload.get("summary"),
                "available_time": available_time,
            },
        }

    def _derive_success_criteria(self, dossier_payload: dict) -> list[str]:
        criteria = []
        goal = dossier_payload.get("goal_statement")
        timeline = dossier_payload.get("timeline")
        available_time = dossier_payload.get("available_time")
        if goal:
            criteria.append(f"Make consistent progress toward {goal}")
        if timeline:
            criteria.append(f"Reach a visible milestone within {timeline}")
        if available_time:
            criteria.append(f"Stay sustainable within {available_time}")
        if not criteria:
            criteria.append("Keep execution aligned with the user's self-defined growth direction")
        return criteria

    def _derive_pacing_philosophy(self, dossier_payload: dict) -> str:
        available_time = str(dossier_payload.get("available_time") or "")
        timeline = str(dossier_payload.get("timeline") or "")
        if any(token in available_time for token in ("30分钟", "45分钟", "30 min", "45 min")):
            return "steady"
        if any(token in timeline for token in ("30天", "60天", "3个月", "30 days", "60 days")):
            return "sprint"
        return "adaptive"

    def _derive_risk_tolerance(self, dossier_payload: dict) -> str:
        prior_attempts = " ".join(dossier_payload.get("prior_attempts") or []).lower()
        if any(token in prior_attempts for token in ("失败", "放弃", "burnout", "quit")):
            return "cautious"
        timeline = str(dossier_payload.get("timeline") or "")
        if any(token in timeline for token in ("30天", "60天", "30 days", "60 days")):
            return "aggressive"
        return "moderate"

    def _estimate_max_session_minutes(self, available_time: str | None) -> int:
        if not available_time:
            return 90
        minute_match = re.search(r"(\d+)\s*(分钟|min)", available_time, re.IGNORECASE)
        if minute_match:
            return max(30, min(180, int(minute_match.group(1))))
        hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(小时|hour|hours|h)", available_time, re.IGNORECASE)
        if hour_match:
            return max(30, min(180, int(float(hour_match.group(1)) * 60)))
        return 90

    def _normalize_dossier(self, dossier: PlanningArtifact | dict) -> tuple[dict, int, uuid.UUID | None]:
        if isinstance(dossier, PlanningArtifact):
            return dict(dossier.payload or {}), dossier.version, dossier.id
        payload = dict(dossier or {})
        version = int(payload.get("version") or payload.get("artifact_version") or 1)
        dossier_id = payload.get("artifact_id")
        return payload, version, uuid.UUID(str(dossier_id)) if dossier_id else None

    async def _get_latest_artifact_by_status(
        self,
        plan_card_id: uuid.UUID,
        artifact_type: ArtifactType,
        status: ArtifactStatus,
    ) -> PlanningArtifact | None:
        stmt = (
            select(PlanningArtifact)
            .where(
                PlanningArtifact.plan_card_id == plan_card_id,
                PlanningArtifact.artifact_type == artifact_type,
                PlanningArtifact.status == status,
                PlanningArtifact.not_deleted_filter(),
            )
            .order_by(PlanningArtifact.version.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_owned_plan(self, plan_card_id: uuid.UUID, user_id: uuid.UUID) -> Card:
        stmt = select(Card).where(
            Card.id == plan_card_id,
            Card.card_type == CardType.PLAN,
            Card.owner_id == user_id,
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        plan_card = result.scalar_one_or_none()
        if not plan_card:
            raise ValueError("Plan card not found")
        return plan_card

    async def _sync_plan_metadata(
        self,
        plan_card_id: uuid.UUID,
        artifact_id: uuid.UUID,
        version: int,
        patch: dict | None = None,
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
            **(patch or {}),
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
