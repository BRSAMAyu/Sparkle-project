"""
Card Protocol Service Package.

Phase 1: Core data layer (CardService, CardEdgeService, TaskOccurrenceService, legacy adapters, bridges)
Phase 2: Intervention records, health/behavior bridges, outcome verification
Phase 3: Parameter compiler, decision log, risk register, global compass, strategy map

Import policy (V3-FIX-274): submodule exports below are lazy (PEP 562).
The previous eager imports pulled the whole service graph into every
importer of any submodule — including ``app.gen`` (generated gRPC code,
not tracked in the repo, present only where ``make proto-gen`` has run).
That made the CARD-DUAL-WRITE guard (which only needs
``consistency_validator`` + ``legacy_adapter``) unrunnable in fresh
checkouts. Lazy exports keep ``from app.services.card_protocol import X``
working everywhere while dropping the transitive import cost.
"""

from __future__ import annotations

import importlib
from typing import Any

_LAZY_EXPORTS: dict[str, str] = {
    "BehaviorInterventionBridge": "app.services.card_protocol.behavior_intervention_bridge",
    "CardSnapshotService": "app.services.card_protocol.card_snapshot_service",
    "DecisionLogService": "app.services.card_protocol.decision_log_service",
    "ErrorMasteryBridge": "app.services.card_protocol.mastery_bridge",
    "FeedbackGateEngine": "app.services.card_protocol.feedback_gate_engine",
    "GlobalCompassManager": "app.services.card_protocol.global_compass_manager",
    "InterventionOutcomeVerifier": "app.services.card_protocol.outcome_verifier",
    "MainChainArtifactService": "app.services.card_protocol.main_chain_artifact_service",
    "ParameterCompiler": "app.services.card_protocol.parameter_compiler",
    "PhaseDesignService": "app.services.card_protocol.phase_design_service",
    "PhaseService": "app.services.card_protocol.phase_service",
    "PlanningMemoryService": "app.services.card_protocol.planning_memory_service",
    "PlanAdapter": "app.services.card_protocol.legacy_adapter",
    "PlanHealthInterventionBridge": "app.services.card_protocol.health_intervention_bridge",
    "ReplannerCardBridge": "app.services.card_protocol.replanner_bridge",
    "RiskRegisterService": "app.services.card_protocol.risk_register_service",
    "ShareService": "app.services.card_protocol.share_service",
    "StrategyMapManager": "app.services.card_protocol.strategy_map_manager",
    "TaskAdapter": "app.services.card_protocol.legacy_adapter",
    "TemporalEngine": "app.services.card_protocol.temporal_engine",
}

__all__ = list(_LAZY_EXPORTS)


def __getattr__(name: str) -> Any:
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(module_name)
    attribute = getattr(module, name)
    globals()[name] = attribute  # cache: subsequent lookups skip the hook
    return attribute


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
