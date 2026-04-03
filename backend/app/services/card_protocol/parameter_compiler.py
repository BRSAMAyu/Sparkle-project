"""
ParameterCompiler — Compiles approved artifacts into concrete execution parameters.

This is the core Phase 3 component. It reads GLOBAL_COMPASS and STRATEGY_MAP
artifacts, applies adaptation rules based on the trigger context, and writes
compiled parameters to PlanState.facts["adaptive_adjustments"].

Breakpoint 5 fix: "cognitive_adjustments stay too prompt-level" ->
    parameter compiler writes real strategy parameters.

Anti-drift enforcement: Every compilation records based_on_versions.
Stale compilations are rejected.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import ArtifactType, PlanningArtifact
from app.services.card_protocol.global_compass_manager import GlobalCompassManager
from app.services.card_protocol.strategy_map_manager import StrategyMapManager
from app.services.plan_state_service import PlanStateService
from app.services.planning_artifact_service import PlanningArtifactService
from app.core.event_bus import EventBus


@dataclass
class ParameterCompilationResult:
    """Result of a parameter compilation."""
    success: bool
    adaptive_adjustments: dict = field(default_factory=dict)
    compilation_meta: dict = field(default_factory=dict)
    decision_log_entry_id: str | None = None
    error: str | None = None


class ParameterCompiler:
    """Compiles GLOBAL_COMPASS + STRATEGY_MAP -> PlanState.facts['adaptive_adjustments']."""

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
        self.artifact_service = PlanningArtifactService(db, event_bus)
        self.compass_manager = GlobalCompassManager(db, event_bus)
        self.strategy_manager = StrategyMapManager(db, event_bus)
        self.plan_state_service = PlanStateService(db, redis=None)

    async def compile(
        self,
        *,
        user_id: uuid.UUID,
        plan_card_id: uuid.UUID,
        plan_id: uuid.UUID,
        trigger: str,
        context: dict | None = None,
    ) -> ParameterCompilationResult:
        """Compile artifacts into execution parameters.

        Steps:
        1. Read APPROVED GLOBAL_COMPASS
        2. Read APPROVED STRATEGY_MAP
        3. Resolve the adaptation rule for the trigger
        4. Merge compass constraints + rule params
        5. Write to PlanState.facts["adaptive_adjustments"]
        6. Record compilation_meta + DecisionLog entry
        """
        context = context or {}

        # 1. Read APPROVED GLOBAL_COMPASS
        compass_artifact = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.GLOBAL_COMPASS
        )
        if not compass_artifact:
            return ParameterCompilationResult(
                success=False, error="No APPROVED GLOBAL_COMPASS found"
            )
        compass_payload = dict(compass_artifact.payload or {})

        # 2. Read APPROVED STRATEGY_MAP
        strategy_artifact = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.STRATEGY_MAP
        )
        if not strategy_artifact:
            return ParameterCompilationResult(
                success=False, error="No APPROVED STRATEGY_MAP found"
            )
        strategy_payload = dict(strategy_artifact.payload or {})

        # 3. Resolve the adaptation rule for the trigger
        strategy_trigger = StrategyMapManager.resolve_trigger(
            replanner_trigger=trigger,
            pattern_name=context.get("pattern_name"),
            health_reasons=context.get("health_reasons"),
        )
        rule = None
        if strategy_trigger:
            rules = strategy_payload.get("adaptation_rules", {})
            rule = rules.get(strategy_trigger)

        # 4. Merge compass constraints + rule params + execution defaults
        adjustments = self._merge_parameters(
            compass_payload=compass_payload,
            strategy_payload=strategy_payload,
            rule=rule,
            context=context,
        )

        # 5. Build compilation_meta
        compilation_meta = {
            "compiled_at": datetime.utcnow().isoformat(),
            "compass_version": compass_artifact.version,
            "strategy_map_version": strategy_artifact.version,
            "trigger": trigger,
            "strategy_trigger": strategy_trigger,
            "rule_applied": rule.get("action") if rule else None,
        }
        adjustments["compilation_meta"] = compilation_meta

        # 6. Write to PlanState.facts["adaptive_adjustments"]
        try:
            await self.plan_state_service.upsert_plan_state(
                user_id=user_id,
                plan_id=plan_id,
                patch={"facts": {"adaptive_adjustments": adjustments}},
                bump_version=True,
            )
        except Exception as exc:
            logger.warning("ParameterCompiler: PlanState write failed: {}", exc)
            return ParameterCompilationResult(
                success=False, error=f"PlanState write failed: {exc}"
            )

        # 7. Create DecisionLog entry
        decision_entry_id = None
        try:
            from app.services.card_protocol.decision_log_service import DecisionLogService
            decision_log = DecisionLogService(self.db, self.event_bus)
            decision_text = self._describe_decision(adjustments, trigger, rule)
            rationale = self._describe_rationale(trigger, context, compass_payload, rule)

            entry = await decision_log.record_decision(
                plan_card_id=plan_card_id,
                decision=decision_text,
                rationale=rationale,
                trigger=trigger,
                input_artifacts={
                    "GLOBAL_COMPASS": f"v{compass_artifact.version}",
                    "STRATEGY_MAP": f"v{strategy_artifact.version}",
                },
                expected_observation=self._expected_observation(adjustments, trigger),
                linked_intervention_id=context.get("intervention_id"),
            )
            decision_entry_id = entry.get("id") if entry else None

            # Link decision log entry id back into compilation_meta
            if decision_entry_id:
                compilation_meta["decision_log_entry_id"] = decision_entry_id
                adjustments["compilation_meta"] = compilation_meta
                await self.plan_state_service.upsert_plan_state(
                    user_id=user_id,
                    plan_id=plan_id,
                    patch={"facts": {"adaptive_adjustments": adjustments}},
                    bump_version=False,
                )
        except Exception as exc:
            logger.warning("ParameterCompiler: DecisionLog write failed (non-fatal): {}", exc)

        logger.info(
            "ParameterCompiler: compiled for plan {} (compass v{}, strategy v{}, trigger={})",
            plan_card_id,
            compass_artifact.version,
            strategy_artifact.version,
            trigger,
        )

        return ParameterCompilationResult(
            success=True,
            adaptive_adjustments=adjustments,
            compilation_meta=compilation_meta,
            decision_log_entry_id=decision_entry_id,
        )

    async def can_compile(self, plan_card_id: uuid.UUID) -> bool:
        """Check whether both compass and strategy map exist for a plan."""
        compass = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.GLOBAL_COMPASS
        )
        strategy = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.STRATEGY_MAP
        )
        return compass is not None and strategy is not None

    # ------------------------------------------------------------------
    # Parameter merging logic
    # ------------------------------------------------------------------

    def _merge_parameters(
        self,
        *,
        compass_payload: dict,
        strategy_payload: dict,
        rule: dict | None,
        context: dict,
    ) -> dict[str, Any]:
        """Merge compass constraints + strategy defaults + adaptation rule."""
        exec_params = dict(strategy_payload.get("execution_parameters", {}))
        hard_constraints = dict(compass_payload.get("hard_constraints", {}))

        # Start with strategy defaults
        adjustments: dict[str, Any] = {
            "time_multiplier": float(exec_params.get("default_time_multiplier", 1.0)),
            "difficulty_shift": float(exec_params.get("default_difficulty_shift", 0.0)),
            "max_concurrent_tasks": int(hard_constraints.get("max_concurrent_tasks", 3)),
            "insert_prerequisite_review": False,
        }

        # Apply adaptation rule if found
        if rule:
            action = rule.get("action", "")
            params = rule.get("params", {})

            if action == "extend_timeline":
                multiplier = float(params.get("multiplier", 1.3))
                adjustments["time_multiplier"] = round(
                    adjustments["time_multiplier"] * multiplier, 3
                )
            elif action == "reduce_concurrency":
                max_tasks = int(params.get("max_tasks", 2))
                adjustments["max_concurrent_tasks"] = max_tasks
            elif action == "insert_prerequisite":
                adjustments["insert_prerequisite_review"] = True
            elif action == "increase_difficulty":
                shift = float(params.get("shift", 0.1))
                adjustments["difficulty_shift"] = round(
                    adjustments["difficulty_shift"] + shift, 3
                )
            elif action == "decrease_difficulty":
                shift = float(params.get("shift", -0.1))
                adjustments["difficulty_shift"] = round(
                    adjustments["difficulty_shift"] + shift, 3
                )

        # Apply compass constraints (override)
        max_tasks = hard_constraints.get("max_concurrent_tasks")
        if isinstance(max_tasks, int):
            adjustments["max_concurrent_tasks"] = min(
                adjustments["max_concurrent_tasks"], max_tasks
            )

        # Pacing philosophy adjustments
        pacing = compass_payload.get("pacing_philosophy", "adaptive")
        if pacing == "steady":
            adjustments["time_multiplier"] = max(adjustments["time_multiplier"], 1.1)
        elif pacing == "sprint":
            adjustments["time_multiplier"] = min(adjustments["time_multiplier"], 0.9)

        # Risk tolerance adjustments
        risk = compass_payload.get("risk_tolerance", "moderate")
        if risk == "cautious":
            adjustments["time_multiplier"] = max(adjustments["time_multiplier"], 1.05)
        elif risk == "aggressive":
            adjustments["time_multiplier"] = min(adjustments["time_multiplier"], 0.95)

        # Clamp to safe ranges
        adjustments["time_multiplier"] = max(0.5, min(3.0, adjustments["time_multiplier"]))
        adjustments["difficulty_shift"] = max(-0.5, min(0.5, adjustments["difficulty_shift"]))
        adjustments["max_concurrent_tasks"] = max(1, min(10, adjustments["max_concurrent_tasks"]))

        return adjustments

    # ------------------------------------------------------------------
    # Decision description helpers
    # ------------------------------------------------------------------

    def _describe_decision(
        self, adjustments: dict, trigger: str, rule: dict | None
    ) -> str:
        parts = []
        tm = adjustments.get("time_multiplier", 1.0)
        if tm != 1.0:
            parts.append(f"time_multiplier={tm:.2f}")
        ds = adjustments.get("difficulty_shift", 0.0)
        if ds != 0.0:
            parts.append(f"difficulty_shift={ds:+.2f}")
        mc = adjustments.get("max_concurrent_tasks")
        if mc and mc != 3:
            parts.append(f"max_concurrent_tasks={mc}")
        if adjustments.get("insert_prerequisite_review"):
            parts.append("insert_prerequisite_review=true")

        if not parts:
            return f"No parameter change for trigger '{trigger}'"
        return f"Compiled parameters for '{trigger}': {', '.join(parts)}"

    def _describe_rationale(
        self,
        trigger: str,
        context: dict,
        compass_payload: dict,
        rule: dict | None,
    ) -> str:
        parts = [f"Triggered by: {trigger}"]
        if context.get("pattern_name"):
            parts.append(f"Pattern: {context['pattern_name']}")
        if context.get("health_reasons"):
            parts.append(f"Health reasons: {', '.join(context['health_reasons'])}")
        if rule:
            parts.append(f"Applied rule: {rule.get('action', 'unknown')}")
        pacing = compass_payload.get("pacing_philosophy")
        if pacing:
            parts.append(f"Pacing: {pacing}")
        risk = compass_payload.get("risk_tolerance")
        if risk:
            parts.append(f"Risk tolerance: {risk}")
        return "; ".join(parts)

    def _expected_observation(self, adjustments: dict, trigger: str) -> str:
        tm = adjustments.get("time_multiplier", 1.0)
        if tm > 1.0:
            return "Tasks complete closer to or within estimated time"
        if tm < 1.0:
            return "Tasks feel appropriately timed without rushing"
        ds = adjustments.get("difficulty_shift", 0.0)
        if ds < 0:
            return "User completes tasks without difficulty resistance feedback"
        if ds > 0:
            return "User maintains engagement with appropriately challenging tasks"
        return f"Improvement in trigger condition: {trigger}"
