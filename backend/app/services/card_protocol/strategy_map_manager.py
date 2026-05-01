"""
StrategyMapManager — Manages the STRATEGY_MAP artifact lifecycle.

The strategy map defines adaptation rules: what to do when stall/overload/
difficulty resistance/fast progress is detected. It drives the ParameterCompiler.

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


# Default adaptation rules (sensible defaults for university students)
_DEFAULT_STRATEGY = {
    "adaptation_rules": {
        "on_stall": {
            "action": "reduce_concurrency",
            "params": {"max_tasks": 2},
        },
        "on_overload": {
            "action": "extend_timeline",
            "params": {"multiplier": 1.3},
        },
        "on_difficulty_resistance": {
            "action": "insert_prerequisite",
            "params": {},
        },
        "on_fast_progress": {
            "action": "increase_difficulty",
            "params": {"shift": 0.1},
        },
    },
    "execution_parameters": {
        "default_time_multiplier": 1.0,
        "default_difficulty_shift": 0.0,
        "max_concurrent_phases": 1,
        "checkpoint_frequency_days": 7,
    },
}

# Mapping from behavior pattern names to strategy triggers
_PATTERN_TO_TRIGGER = {
    "procrastination": "on_stall",
    "avoidance": "on_stall",
    "execution": "on_stall",
    "overload": "on_overload",
    "planning_fallacy": "on_overload",
    "perfectionism": "on_difficulty_resistance",
    "cognitive": "on_difficulty_resistance",
    "fast_progress": "on_fast_progress",
}

# Mapping from plan health reasons to strategy triggers
_HEALTH_REASON_TO_TRIGGER = {
    "stall_detected": "on_stall",
    "no_progress": "on_stall",
    "inactive": "on_stall",
    "overload": "on_overload",
    "too_many_tasks": "on_overload",
    "time_overrun": "on_overload",
    "low_completion_rate": "on_stall",
    "concept_gap": "on_difficulty_resistance",
    "high_completion_rate": "on_fast_progress",
}


class StrategyMapManager:
    """Manages STRATEGY_MAP artifact lifecycle for a plan."""

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
        self.artifact_service = PlanningArtifactService(db, event_bus)

    async def initialize(
        self,
        *,
        plan_card_id: uuid.UUID,
        user_id: uuid.UUID,
        plan_structure: dict | None = None,
    ) -> PlanningArtifact:
        """Create initial STRATEGY_MAP from plan structure.

        Auto-approves since this is a system-generated initial artifact.
        """
        payload = self._build_initial_payload(plan_structure)

        artifact = await self.artifact_service.create_artifact(
            plan_card_id=plan_card_id,
            artifact_type=ArtifactType.STRATEGY_MAP,
            payload=payload,
            created_by_agent="system_init",
        )
        await self.artifact_service.propose_artifact(artifact.id)
        approved = await self.artifact_service.auto_approve_artifact(artifact.id)
        if approved:
            await self._sync_plan_metadata(plan_card_id, approved.id, approved.version)
        logger.info(
            "StrategyMapManager: initialized strategy map v{} for plan {}",
            artifact.version,
            plan_card_id,
        )
        return approved or artifact

    async def get_parameters(self, plan_card_id: uuid.UUID) -> dict:
        """Return approved strategy map parameters, or empty dict."""
        artifact = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.STRATEGY_MAP
        )
        return dict(artifact.payload) if artifact else {}

    async def get_rule(self, plan_card_id: uuid.UUID, trigger: str) -> dict | None:
        """Look up the adaptation rule for a given trigger."""
        params = await self.get_parameters(plan_card_id)
        rules = params.get("adaptation_rules", {})
        return rules.get(trigger)

    async def get_execution_parameters(self, plan_card_id: uuid.UUID) -> dict:
        """Return execution_parameters section from approved strategy."""
        params = await self.get_parameters(plan_card_id)
        return dict(params.get("execution_parameters", {}))

    async def get_or_initialize(
        self,
        *,
        plan_card_id: uuid.UUID,
        user_id: uuid.UUID,
        plan_structure: dict | None = None,
    ) -> PlanningArtifact:
        """Get existing APPROVED strategy map or initialize a new one."""
        existing = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.STRATEGY_MAP
        )
        if existing:
            return existing
        return await self.initialize(
            plan_card_id=plan_card_id,
            user_id=user_id,
            plan_structure=plan_structure,
        )

    async def propose_update(
        self,
        plan_card_id: uuid.UUID,
        updates: dict,
        evidence: dict | None = None,
    ) -> PlanningArtifact | None:
        """Propose a strategy map update. Creates a new version."""
        current = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.STRATEGY_MAP
        )
        if not current:
            logger.warning(
                "StrategyMapManager: no current strategy map for plan {}, cannot update",
                plan_card_id,
            )
            return None

        merged_payload = _deep_merge(dict(current.payload), updates)

        based_on = {"STRATEGY_MAP": current.version}
        if evidence and evidence.get("compass_version"):
            based_on["GLOBAL_COMPASS"] = evidence["compass_version"]

        artifact = await self.artifact_service.create_artifact(
            plan_card_id=plan_card_id,
            artifact_type=ArtifactType.STRATEGY_MAP,
            payload=merged_payload,
            created_by_agent="system_adapt",
            based_on_versions=based_on,
        )

        await self.artifact_service.propose_artifact(artifact.id)
        approved = await self.artifact_service.auto_approve_artifact(artifact.id)
        if approved:
            await self._sync_plan_metadata(plan_card_id, approved.id, approved.version)
        return approved

    @staticmethod
    def resolve_trigger(
        *,
        pattern_name: str | None = None,
        health_reasons: list[str] | None = None,
        replanner_trigger: str | None = None,
    ) -> str | None:
        """Resolve a trigger name from various signal sources.

        Returns one of: on_stall, on_overload, on_difficulty_resistance, on_fast_progress
        """
        # Direct replanner trigger mapping
        if replanner_trigger:
            mapping = {
                "stall": "on_stall",
                "inactivity": "on_stall",
                "overrun": "on_overload",
                "overload": "on_overload",
                "difficulty": "on_difficulty_resistance",
                "resistance": "on_difficulty_resistance",
                "fast": "on_fast_progress",
            }
            for key, trigger in mapping.items():
                if key in replanner_trigger.lower():
                    return trigger

        # Pattern name mapping
        if pattern_name:
            return _PATTERN_TO_TRIGGER.get(pattern_name.lower())

        # Health reason mapping
        if health_reasons:
            for reason in health_reasons:
                trigger = _HEALTH_REASON_TO_TRIGGER.get(reason.lower())
                if trigger:
                    return trigger

        return None

    def _build_initial_payload(self, plan_structure: dict | None) -> dict:
        """Build strategy map payload from plan structure."""
        payload = deepcopy(_DEFAULT_STRATEGY)

        if plan_structure:
            phase_count = plan_structure.get("phase_count", 0)
            if phase_count <= 2:
                # Simple plan: allow concurrent phases
                payload["execution_parameters"]["max_concurrent_phases"] = min(phase_count, 2)
            task_density = plan_structure.get("task_density")  # tasks per phase
            if isinstance(task_density, (int, float)) and task_density > 5:
                # Dense plan: more frequent checkpoints
                payload["execution_parameters"]["checkpoint_frequency_days"] = 5

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
            "strategy_map_artifact_id": str(artifact_id),
            "strategy_map_version": version,
        }
        if any(metadata.get(key) != value for key, value in patch.items()):
            metadata.update(patch)
            plan_card.metadata_ = metadata
            plan_card.version += 1
            plan_card.updated_by = CardCreatedBy.SYSTEM
            await self.db.flush()


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Deep merge overlay into base (returns new dict, doesn't mutate)."""
    result = dict(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
