"""L1 Light Aurora: deterministic per-turn sensing.

This module is intentionally LLM-free. It turns each chat turn into a cheap,
structured readout that downstream RAG, status-band UI, and escalation logic can
consume without invoking the heavier Aurora decision loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.aurora.runtime_v1.energy_controller import EnergyLevelDecider
from app.aurora.runtime_v1.l0_rules import L0RuleEngine
from app.aurora.runtime_v1.state import AuroraEnergyStore
from app.orchestration.retrieval_intent import ContextPlan, RetrievalIntentClassifier
from app.signals.state_register import StateRegister


@dataclass(slots=True)
class L1TurnResult:
    energy_level: str
    upgrade_reason: str
    retrieval_mode: str
    should_retrieve: bool
    budget_tokens: int
    source_scope: str
    status_band_hint: str
    should_escalate: bool = False
    escalation_reason: str = "not_upgraded"
    l0_signal_ids: list[str] = field(default_factory=list)
    context_plan: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "energy_level": self.energy_level,
            "upgrade_reason": self.upgrade_reason,
            "retrieval_mode": self.retrieval_mode,
            "should_retrieve": self.should_retrieve,
            "budget_tokens": self.budget_tokens,
            "source_scope": self.source_scope,
            "status_band_hint": self.status_band_hint,
            "should_escalate": self.should_escalate,
            "escalation_reason": self.escalation_reason,
            "l0_signal_ids": self.l0_signal_ids,
            "context_plan": self.context_plan,
        }


class L1LightAurora:
    """Per-turn lightweight Aurora cognition."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client
        self.l0_rules = L0RuleEngine(redis_client)
        self.retrieval_classifier = RetrievalIntentClassifier()
        self.energy_decider = EnergyLevelDecider()
        self.energy_store = AuroraEnergyStore(redis_client)
        self.state_register = StateRegister(redis_client)

    async def run_turn(
        self,
        *,
        user_id: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> L1TurnResult:
        context = context if isinstance(context, dict) else {}
        l0_signals = await self.l0_rules.evaluate_all(
            user_id,
            upcoming_deadlines=self._extract_upcoming_deadlines(context),
            quiet_start=str(context.get("quiet_start") or "22:00"),
            quiet_end=str(context.get("quiet_end") or "08:00"),
        )
        context_plan = self.retrieval_classifier.classify(
            message,
            route_intent=self._extract_route_intent(context),
            context=context,
        )
        active_states = await self._load_active_states(user_id)
        active_states.extend(signal.to_dict() for signal in l0_signals)
        energy = await self.energy_store.load_energy(user_id)
        energy_decision = self.energy_decider.decide(
            user_id=user_id,
            energy=energy,
            active_states=active_states,
            aurora_active=bool(context.get("aurora_active", True)),
            l3_wake_eligible=bool(context.get("l3_wake_eligible", False)),
        )
        status_band = self._compute_status_band_hint(
            context_plan=context_plan,
            energy_level=energy_decision.current_level,
            l0_signal_count=len(l0_signals),
        )
        should_escalate = energy_decision.current_level in {"L2", "L3"}
        return L1TurnResult(
            energy_level=energy_decision.current_level,
            upgrade_reason=energy_decision.upgrade_reason,
            retrieval_mode=context_plan.retrieval_mode,
            should_retrieve=context_plan.should_retrieve,
            budget_tokens=context_plan.budget_tokens,
            source_scope=context_plan.source_scope,
            status_band_hint=status_band,
            should_escalate=should_escalate,
            escalation_reason=energy_decision.upgrade_reason if should_escalate else "not_upgraded",
            l0_signal_ids=[signal.signal_id for signal in l0_signals],
            context_plan=context_plan.to_dict(),
        )

    async def _load_active_states(self, user_id: str) -> list[dict[str, Any]]:
        try:
            states = await self.state_register.get_active_states(user_id)
        except Exception as exc:
            logger.debug("L1 active state load skipped for user={}: {}", user_id, exc)
            return []
        normalized: list[dict[str, Any]] = []
        for state in states or []:
            if hasattr(state, "to_dict"):
                normalized.append(state.to_dict())
            elif isinstance(state, dict):
                normalized.append(dict(state))
        return normalized

    @staticmethod
    def _extract_upcoming_deadlines(context: dict[str, Any]) -> list[dict[str, Any]]:
        for key in ("upcoming_deadlines", "deadlines", "calendar_deadlines"):
            value = context.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []

    @staticmethod
    def _extract_route_intent(context: dict[str, Any]) -> str | None:
        for key in ("route_intent", "intent", "chat_intent"):
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _compute_status_band_hint(
        *,
        context_plan: ContextPlan,
        energy_level: str,
        l0_signal_count: int,
    ) -> str:
        if energy_level == "L3":
            return "calibration_available"
        if energy_level == "L2" or l0_signal_count > 0:
            return "risk_found"
        if context_plan.calibration_needed:
            return "needs_confirm"
        if context_plan.should_retrieve:
            return "sensing"
        return "calibrated"
