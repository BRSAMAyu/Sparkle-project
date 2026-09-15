"""Trigger dispatch helpers for Aurora."""

from __future__ import annotations

from dataclasses import dataclass

from app.aurora.schemas import InitiationType


@dataclass(frozen=True)
class TriggerDispatch:
    """Derived dispatch metadata for a trigger type."""

    initiation_type: InitiationType
    trigger_point: str
    dispatch_mode: str
    soft_budget_ms: int
    hard_budget_ms: int
    priority: int


_TRIGGER_MAP: dict[InitiationType, TriggerDispatch] = {
    InitiationType.REACTIVE: TriggerDispatch(
        initiation_type=InitiationType.REACTIVE,
        trigger_point="pre-node-routing",
        dispatch_mode="immediate",
        soft_budget_ms=100,
        hard_budget_ms=900,
        priority=0,
    ),
    InitiationType.SCHEDULED: TriggerDispatch(
        initiation_type=InitiationType.SCHEDULED,
        trigger_point="pre-tool-selection",
        dispatch_mode="scheduled",
        soft_budget_ms=75,
        hard_budget_ms=500,
        priority=1,
    ),
    InitiationType.ON_DEMAND: TriggerDispatch(
        initiation_type=InitiationType.ON_DEMAND,
        trigger_point="pre-response-formatting",
        dispatch_mode="on_demand",
        soft_budget_ms=50,
        hard_budget_ms=240,
        priority=2,
    ),
    InitiationType.PROACTIVE: TriggerDispatch(
        initiation_type=InitiationType.PROACTIVE,
        trigger_point="pre-node-routing",
        dispatch_mode="immediate",
        soft_budget_ms=100,
        hard_budget_ms=900,
        priority=0,
    ),
}


def dispatch_trigger(trigger: InitiationType | str) -> TriggerDispatch:
    """Map a trigger type to its deterministic dispatch envelope."""

    normalized = trigger if isinstance(trigger, InitiationType) else InitiationType(trigger)
    return _TRIGGER_MAP[normalized]

