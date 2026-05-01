"""
Core: execution
Phase: adapt
Stage: P2-4 Learning Base — strategy learning infrastructure

Bayesian posterior update for strategy confidence, combined with
rule-based fallback for cold-start and low-data scenarios.

All operations are pure computation on in-memory data.
No direct Redis I/O — callers persist results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from app.signals.types import SkillEntry



@dataclass
class StrategyBelief:
    """Bayesian belief about a strategy's effectiveness."""
    strategy_key: str
    alpha: float = 1.0    # prior "successes" (Beta distribution)
    beta: float = 1.0     # prior "failures"
    evidence_count: int = 0
    last_updated: str = ""

    @property
    def expected_effectiveness(self) -> float:
        """Posterior mean: alpha / (alpha + beta)."""
        total = self.alpha + self.beta
        if total == 0:
            return 0.5
        return self.alpha / total

    @property
    def confidence(self) -> float:
        """How confident we are in the estimate (0-1)."""
        total = self.alpha + self.beta
        if total < 2:
            return 0.0
        # Confidence increases with evidence, asymptotically approaches 1
        return min(total / (total + 10), 1.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_key": self.strategy_key,
            "alpha": self.alpha,
            "beta": self.beta,
            "evidence_count": self.evidence_count,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> StrategyBelief:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class LearningSnapshot:
    """Point-in-time snapshot of learning state for a user."""
    user_id: str
    beliefs: list[StrategyBelief] = field(default_factory=list)
    rule_overrides: dict[str, str] = field(default_factory=dict)
    cold_start_strategies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "beliefs": [b.to_dict() for b in self.beliefs],
            "rule_overrides": self.rule_overrides,
            "cold_start_strategies": self.cold_start_strategies,
        }


class LearningBase:
    """
    Reusable strategy learning engine.

    Combines Bayesian posterior updates with rule-based fallback:
    - High evidence → trust Bayesian estimate
    - Low evidence (cold start) → fall back to default rules
    - Conflict → prefer the rule-based answer with Bayesian as advisory
    """

    # Prior strength — higher = more resistant to change
    PRIOR_STRENGTH = 2.0
    # Minimum evidence before trusting Bayesian over rules
    COLD_START_THRESHOLD = 5

    def update_belief(
        self,
        belief: StrategyBelief,
        outcome: str,  # "effective" | "insufficient"
        weight: float = 1.0,
    ) -> StrategyBelief:
        """Update a belief with a new observation."""
        if outcome == "effective":
            belief.alpha += weight
        elif outcome == "insufficient":
            belief.beta += weight
        else:
            return belief

        belief.evidence_count += 1
        return belief

    def batch_update(
        self,
        beliefs: list[StrategyBelief],
        outcomes: list[dict[str, Any]],
    ) -> list[StrategyBelief]:
        """Update multiple beliefs from a batch of outcomes.

        Each outcome: {"strategy_key": str, "attribution": str, "weight": float}
        """
        belief_map = {b.strategy_key: b for b in beliefs}

        for outcome in outcomes:
            key = outcome.get("strategy_key", "")
            attr = outcome.get("attribution", "")
            weight = outcome.get("weight", 1.0)

            if key not in belief_map:
                belief_map[key] = StrategyBelief(strategy_key=key)

            self.update_belief(belief_map[key], attr, weight)

        return list(belief_map.values())

    def select_strategy(
        self,
        beliefs: list[StrategyBelief],
        candidates: list[str],
        *,
        prefer_rules: bool = False,
        rule_ranking: list[str] | None = None,
    ) -> dict[str, Any]:
        """Select the best strategy from candidates.

        Args:
            beliefs: Current beliefs about strategies
            candidates: Available strategy keys
            prefer_rules: If True, use rule ranking for cold-start
            rule_ranking: Ordered list of strategy preferences (rules)

        Returns:
            {"strategy": str, "source": str, "confidence": float}
        """
        if not candidates:
            return {"strategy": "", "source": "no_candidates", "confidence": 0.0}

        if len(candidates) == 1:
            return {
                "strategy": candidates[0],
                "source": "only_candidate",
                "confidence": 0.5,
            }

        belief_map = {b.strategy_key: b for b in beliefs}
        candidate_beliefs = [
            belief_map.get(c, StrategyBelief(strategy_key=c))
            for c in candidates
        ]

        # Check if all candidates are cold-start
        all_cold = all(b.evidence_count < self.COLD_START_THRESHOLD for b in candidate_beliefs)

        if all_cold and prefer_rules and rule_ranking:
            # Fall back to rule ranking
            for ranked in rule_ranking:
                if ranked in candidates:
                    return {
                        "strategy": ranked,
                        "source": "rule_fallback",
                        "confidence": 0.3,
                    }

        # Bayesian selection: highest expected effectiveness
        best = max(candidate_beliefs, key=lambda b: b.expected_effectiveness)
        return {
            "strategy": best.strategy_key,
            "source": "bayesian" if best.evidence_count >= self.COLD_START_THRESHOLD else "prior",
            "confidence": best.confidence,
        }

    def compute_strategy_ranking(
        self,
        beliefs: list[StrategyBelief],
    ) -> list[dict[str, Any]]:
        """Rank all strategies by expected effectiveness."""
        sorted_beliefs = sorted(
            beliefs,
            key=lambda b: b.expected_effectiveness,
            reverse=True,
        )
        return [
            {
                "strategy_key": b.strategy_key,
                "expected_effectiveness": round(b.expected_effectiveness, 3),
                "confidence": round(b.confidence, 3),
                "evidence_count": b.evidence_count,
            }
            for b in sorted_beliefs
        ]

    def detect_stale_beliefs(
        self,
        beliefs: list[StrategyBelief],
        *,
        max_age_days: int = 30,
    ) -> list[str]:
        """Find beliefs that haven't been updated recently."""
        from datetime import UTC, datetime, timedelta

        cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).isoformat()
        stale = []
        for b in beliefs:
            if b.last_updated and b.last_updated < cutoff:
                stale.append(b.strategy_key)
        return stale

    def build_snapshot(
        self,
        user_id: str,
        beliefs: list[StrategyBelief],
        *,
        rule_overrides: dict[str, str] | None = None,
    ) -> LearningSnapshot:
        """Build a complete learning snapshot for a user."""
        cold_start = [
            b.strategy_key
            for b in beliefs
            if b.evidence_count < self.COLD_START_THRESHOLD
        ]
        return LearningSnapshot(
            user_id=user_id,
            beliefs=beliefs,
            rule_overrides=rule_overrides or {},
            cold_start_strategies=cold_start,
        )

    async def persist_beliefs(
        self, redis_client: Any, user_id: str, beliefs: list[StrategyBelief],
    ) -> None:
        """Persist beliefs to Redis for cross-session durability."""
        import json
        key = f"spine:learning_beliefs:{user_id}"
        data = json.dumps([b.to_dict() for b in beliefs])
        await redis_client.set(key, data, ex=7 * 86400)  # 7-day TTL

    async def load_beliefs(
        self, redis_client: Any, user_id: str,
    ) -> list[StrategyBelief]:
        """Load beliefs from Redis. Returns empty list on miss."""
        import json
        key = f"spine:learning_beliefs:{user_id}"
        raw = await redis_client.get(key)
        if not raw:
            return []
        try:
            items = json.loads(raw)
            return [StrategyBelief.from_dict(d) for d in items]
        except Exception:
            return []

    def check_skill_promotion_eligibility(
        self, beliefs: list[StrategyBelief], skill: SkillEntry,
    ) -> dict[str, Any]:
        """Check if a skill's underlying strategy belief supports promotion."""
        belief_map = {b.strategy_key: b for b in beliefs}
        source_key = skill.source_policy_key
        belief = belief_map.get(source_key)

        if belief is None:
            return {"eligible": False, "reason": "no_belief_data"}

        if belief.evidence_count < self.COLD_START_THRESHOLD:
            return {"eligible": False, "reason": "insufficient_evidence"}

        eff = belief.expected_effectiveness
        if eff < 0.7:
            return {"eligible": False, "reason": "low_effectiveness", "value": round(eff, 3)}

        return {
            "eligible": True,
            "strategy_key": source_key,
            "effectiveness": round(eff, 3),
            "evidence_count": belief.evidence_count,
        }
