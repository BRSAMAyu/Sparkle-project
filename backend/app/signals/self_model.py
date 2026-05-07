"""
Core: execution
Phase: reflect→adapt
Stage: Signal-to-Action Spine P1-5 SparkleSelfModel

Sparkle 自我模型 — 系统建模自己的策略效果。

DEPRECATED (2026-05-07): This module is now a compatibility shim over
app.aurora.runtime_v1.self_model.SparkleSelfModelService, which is the
authoritative self-model implementation. All Spine claims, outcomes, and
corrections are routed to the Aurora self-model's assumption framework.

Migration: New code should import from app.aurora.runtime_v1 directly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.signals.types import _uid


@dataclass
class SelfModelClaim:
    """Sparkle 关于自身策略的一个判断 (compat — mapped to Aurora assumptions)."""
    claim_id: str
    claim: str
    confidence: float
    scope: str
    evidence: list[str]
    counter_evidence: list[str]
    policy_effects: list[str]
    outcome: str | None = None
    retract_conditions: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim": self.claim,
            "confidence": self.confidence,
            "scope": self.scope,
            "evidence": self.evidence,
            "counter_evidence": self.counter_evidence,
            "policy_effects": self.policy_effects,
            "outcome": self.outcome,
            "retract_conditions": self.retract_conditions,
        }


@dataclass
class StrategyOutcome:
    """策略执行结果记录 (compat — mapped to Aurora outcomes)."""
    outcome_id: str
    directive_id: str
    claim_id: str
    expected_outcome: str
    actual_outcome: dict[str, Any]
    attribution: dict[str, Any]
    next_policy_suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "directive_id": self.directive_id,
            "claim_id": self.claim_id,
            "expected_outcome": self.expected_outcome,
            "actual_outcome": self.actual_outcome,
            "attribution": self.attribution,
            "next_policy_suggestion": self.next_policy_suggestion,
        }


class SparkleSelfModelService:
    """
    P1-5: Sparkle 自我模型服务 (compatibility shim).

    Delegates all operations to the authoritative Aurora self-model
    (app.aurora.runtime_v1.self_model.SparkleSelfModelService).

    The original Spine claim/outcome API is preserved for backward
    compatibility but internally maps to Aurora's assumption-based model.
    """

    def __init__(self, redis_client: Any):
        self.redis = redis_client
        self._aurora = None

    def _get_aurora(self):
        """Lazy-import and cache the Aurora self-model instance."""
        if self._aurora is None:
            from app.aurora.runtime_v1.self_model import (
                SparkleSelfModelService as AuroraSelfModelService,
            )
            self._aurora = AuroraSelfModelService(redis_client=self.redis)
        return self._aurora

    # ── Original Spine API (delegates to Aurora) ──

    async def record_claim(
        self,
        *,
        user_id: str,
        claim: str,
        confidence: float,
        scope: str,
        evidence: list[str] | None = None,
        counter_evidence: list[str] | None = None,
        policy_effects: list[str] | None = None,
        retract_conditions: list[str] | None = None,
    ) -> SelfModelClaim:
        """Record a self-model claim → routed to Aurora record_task_outcome."""
        from datetime import UTC, datetime

        claim_obj = SelfModelClaim(
            claim_id=_uid("smc"),
            claim=claim,
            confidence=confidence,
            scope=scope,
            evidence=evidence or [],
            counter_evidence=counter_evidence or [],
            policy_effects=policy_effects or [],
            retract_conditions=retract_conditions or [],
            created_at=datetime.now(UTC).isoformat(),
        )

        # Route to Aurora: claims are recorded as task outcomes with the claim
        # content as the outcome description
        try:
            aurora = self._get_aurora()
            await aurora.record_task_outcome(
                user_id=user_id,
                completed=confidence >= 0.5,
                feedback=claim,
                task_id=claim_obj.claim_id,
            )
        except Exception:
            logger.debug("Aurora self-model delegation failed (non-fatal)", exc_info=True)

        logger.info(
            "SelfModel claim (→Aurora): user={} claim_id={} scope={} conf={:.2f}",
            user_id, claim_obj.claim_id, scope, confidence,
        )
        return claim_obj

    async def record_outcome(
        self,
        *,
        user_id: str,
        directive_id: str,
        claim_id: str,
        expected_outcome: str,
        actual_outcome: dict[str, Any],
    ) -> StrategyOutcome:
        """Record a strategy outcome → routed to Aurora."""
        attribution = self._attribute(expected=expected_outcome, actual=actual_outcome)
        next_suggestion = self._suggest_next(attribution)

        outcome = StrategyOutcome(
            outcome_id=_uid("smo"),
            directive_id=directive_id,
            claim_id=claim_id,
            expected_outcome=expected_outcome,
            actual_outcome=actual_outcome,
            attribution=attribution,
            next_policy_suggestion=next_suggestion,
        )

        try:
            aurora = self._get_aurora()
            await aurora.record_task_outcome(
                user_id=user_id,
                completed=actual_outcome.get("completed", False),
                feedback=actual_outcome.get("user_feedback", ""),
                task_id=directive_id,
            )
        except Exception:
            logger.debug("Aurora outcome delegation failed (non-fatal)", exc_info=True)

        logger.info(
            "SelfModel outcome (→Aurora): user={} claim={} effect={} suggestion={}",
            user_id, claim_id, attribution.get("effect"), next_suggestion,
        )
        return outcome

    async def get_active_claims(self, user_id: str, limit: int = 10) -> list[SelfModelClaim]:
        """Get active self-model claims → converted from Aurora readout."""
        try:
            aurora = self._get_aurora()
            readout = await aurora.get_readout_summary(user_id=user_id)
        except Exception:
            logger.debug("Aurora readout failed, returning empty claims", exc_info=True)
            return []

        claims: list[SelfModelClaim] = []
        assumptions = readout.get("known_assumptions", {})
        for i, (assumption_id, assumption_data) in enumerate(assumptions.items()):
            if i >= limit:
                break
            if isinstance(assumption_data, dict):
                claims.append(SelfModelClaim(
                    claim_id=f"aurora:{assumption_id}",
                    claim=str(assumption_data.get("statement", assumption_id)),
                    confidence=float(assumption_data.get("confidence", 0.5)),
                    scope="user_pair",
                    evidence=assumption_data.get("evidence", []),
                    counter_evidence=[],
                    policy_effects=[],
                    outcome=None,
                ))

        return claims

    async def record_user_correction(
        self,
        *,
        user_id: str,
        signal_id: str,
        reason: str,
        source: str = "user_correction",
    ) -> SelfModelClaim:
        """Record a user correction → routed to Aurora."""
        try:
            aurora = self._get_aurora()
            await aurora.record_user_correction(
                user_id=user_id,
                correction_text=reason,
                source=source,
            )
        except Exception:
            logger.debug("Aurora correction delegation failed (non-fatal)", exc_info=True)

        return await self.record_claim(
            user_id=user_id,
            claim=f"用户纠正了系统判断: {reason}",
            confidence=0.90,
            scope="current_sprint",
            evidence=[f"source={source}", f"signal={signal_id}"],
            policy_effects=["retract_related_directive"],
        )

    def _attribute(self, expected: str, actual: dict[str, Any]) -> dict[str, Any]:
        """Attribution analysis — ported from original Spine implementation."""
        completed = actual.get("completed", False)
        feedback = actual.get("user_feedback", "")

        if completed and feedback in ("", "positive"):
            effect = "effective"
            new_confidence = 0.15
        elif completed and feedback == "negative":
            effect = "completed_but_resented"
            new_confidence = -0.10
        elif not completed and ("不会做" in feedback or "看不懂" in feedback):
            effect = "insufficient"
            new_confidence = -0.20
        else:
            effect = "inconclusive"
            new_confidence = 0.0

        hypothesis = None
        if effect == "insufficient":
            hypothesis = "problem_may_not_be_duration_but_understanding"
        elif effect == "completed_but_resented":
            hypothesis = "strategy_correct_but_tone_wrong"

        return {
            "effect": effect,
            "confidence_delta": new_confidence,
            "new_hypothesis": hypothesis,
        }

    def _suggest_next(self, attribution: dict[str, Any]) -> str | None:
        """Generate next suggestion from attribution."""
        effect = attribution.get("effect")
        hypothesis = attribution.get("new_hypothesis")

        if effect == "insufficient" and hypothesis:
            return f"switch_strategy:{hypothesis}"
        if effect == "completed_but_resented":
            return "adjust_tone"
        if effect == "effective":
            return "maintain_current_strategy"
        return None
