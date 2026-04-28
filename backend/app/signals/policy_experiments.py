"""
Core: execution
Phase: reflect→adapt
Stage: P2-2 Policy Experiments — shadow A/B experiment framework

Shadow experiment: same signal evaluated by two policy strategies in parallel.
Primary strategy goes live; shadow strategy's hypothetical outcome is logged.
When shadow outperforms primary, a promotion suggestion is generated.

Does NOT modify global _RULE_TABLE. Pure read-only analysis.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.signals.types import PolicyEffectEntry, _uid


_EXPERIMENT_KEY = "spine:experiment:{experiment_id}"
_USER_EXPERIMENTS_KEY = "spine:experiments:{user_id}"
_EXPERIMENT_TTL = 30 * 24 * 3600  # 30 days
_MAX_EXPERIMENTS_PER_USER = 20


@dataclass
class PolicyExperiment:
    experiment_id: str
    user_id: str
    signal_state_key: str
    signal_claim: str
    primary_strategy: str
    shadow_strategy: str
    status: str = "running"  # "running" | "concluded" | "promoted" | "abandoned"
    primary_wins: int = 0
    shadow_wins: int = 0
    total_trials: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    conclusion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "user_id": self.user_id,
            "signal_state_key": self.signal_state_key,
            "signal_claim": self.signal_claim,
            "primary_strategy": self.primary_strategy,
            "shadow_strategy": self.shadow_strategy,
            "status": self.status,
            "primary_wins": self.primary_wins,
            "shadow_wins": self.shadow_wins,
            "total_trials": self.total_trials,
            "created_at": self.created_at,
            "conclusion": self.conclusion,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PolicyExperiment:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Shadow strategy alternatives ──────────────────────────────────

_SHADOW_ALTERNATIVES: dict[str, dict[str, str]] = {
    "recover_execution_rhythm": {
        "shadow": "recover_execution_rhythm_gentle",
        "description": "Same recovery but with encouragement tone instead of directive",
    },
    "repair_knowledge_gap": {
        "shadow": "repair_knowledge_gap_guided",
        "description": "Guided exploration instead of direct worked example",
    },
    "recognize_effort_but_repair_quality": {
        "shadow": "recognize_effort_quality_pause",
        "description": "Pause and reflect instead of immediate repair",
    },
    "protect_sustainability": {
        "shadow": "protect_sustainability_break",
        "description": "Suggest a break instead of reducing task duration",
    },
    "encourage_momentum": {
        "shadow": "encourage_momentum_challenge",
        "description": "Offer a challenge task instead of simple encouragement",
    },
    "reduce_cognitive_pressure": {
        "shadow": "reduce_cognitive_pressure_micro",
        "description": "Break tasks into micro-steps instead of shortening duration",
    },
    "reduce_affective_pressure": {
        "shadow": "reduce_affective_pressure_social",
        "description": "Suggest community support instead of reducing difficulty",
    },
    "prevent_burnout": {
        "shadow": "prevent_burnout_achievement",
        "description": "Highlight recent achievements instead of suggesting break",
    },
    "exam_rescue_mode": {
        "shadow": "exam_rescue_mode_selective",
        "description": "Focus on high-yield topics only instead of full rescue plan",
    },
}


class PolicyExperimentManager:
    """Manage shadow A/B experiments for policy strategies."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def create_experiment(
        self,
        *,
        user_id: str,
        signal_state_key: str,
        signal_claim: str,
        primary_strategy: str,
    ) -> PolicyExperiment | None:
        """Create a new shadow experiment for a policy strategy."""
        alt = _SHADOW_ALTERNATIVES.get(primary_strategy)
        if not alt:
            return None

        experiment = PolicyExperiment(
            experiment_id=_uid("exp"),
            user_id=user_id,
            signal_state_key=signal_state_key,
            signal_claim=signal_claim,
            primary_strategy=primary_strategy,
            shadow_strategy=alt["shadow"],
        )
        await self._save(experiment)
        await self._link_to_user(user_id, experiment.experiment_id)
        logger.info(
            "PolicyExperiment: created {} primary={} shadow={}",
            experiment.experiment_id, primary_strategy, alt["shadow"],
        )
        return experiment

    async def record_trial(
        self,
        experiment_id: str,
        *,
        primary_outcome: str,  # "effective" | "insufficient"
        shadow_hypothesis: str,  # hypothetical shadow outcome
    ) -> PolicyExperiment | None:
        """Record a trial outcome for both primary and shadow strategies."""
        experiment = await self.get_experiment(experiment_id)
        if not experiment or experiment.status != "running":
            return None

        experiment.total_trials += 1
        if primary_outcome == "effective":
            experiment.primary_wins += 1
        if shadow_hypothesis == "effective":
            experiment.shadow_wins += 1

        # Auto-conclude after 10 trials
        if experiment.total_trials >= 10:
            experiment = self._conclude(experiment)

        await self._save(experiment)
        return experiment

    async def get_experiment(self, experiment_id: str) -> PolicyExperiment | None:
        raw = await self.redis.get(_EXPERIMENT_KEY.format(experiment_id=experiment_id))
        if not raw:
            return None
        return PolicyExperiment.from_dict(json.loads(raw))

    async def get_user_experiments(self, user_id: str) -> list[PolicyExperiment]:
        key = _USER_EXPERIMENTS_KEY.format(user_id=user_id)
        ids = await self.redis.lrange(key, 0, _MAX_EXPERIMENTS_PER_USER - 1)
        experiments = []
        for eid in ids:
            exp = await self.get_experiment(eid)
            if exp:
                experiments.append(exp)
        return experiments

    async def get_active_experiment_for_strategy(
        self,
        user_id: str,
        strategy: str,
    ) -> PolicyExperiment | None:
        """Find a running experiment for a specific strategy."""
        experiments = await self.get_user_experiments(user_id)
        for exp in experiments:
            if exp.status == "running" and exp.primary_strategy == strategy:
                return exp
        return None

    def evaluate_shadow_outcome(
        self,
        primary_outcome: str,
        primary_strategy: str,
        context: dict[str, Any],
    ) -> str:
        """
        Hypothetically evaluate what the shadow strategy would have produced.
        Uses simple heuristic rules — not a real LLM call.
        """
        alt = _SHADOW_ALTERNATIVES.get(primary_strategy)
        if not alt:
            return primary_outcome

        shadow_strategy = alt["shadow"]

        # Heuristic: if primary was insufficient, shadow might do better if context
        # suggests the primary's approach was wrong-fit
        if primary_outcome == "effective":
            # Primary worked — shadow probably wouldn't do better
            # But give shadow some chance if user feedback was mixed
            user_signal = context.get("user_feedback_signal", "")
            if user_signal in ("completed", "positive"):
                return "effective"
            return "effective"  # primary worked, shadow is same or worse

        # Primary was insufficient — shadow might have done better
        insufficient_reason = context.get("new_hypothesis", "")
        if "understanding" in insufficient_reason.lower() or "knowledge" in insufficient_reason.lower():
            if "guided" in shadow_strategy or "worked_example" in shadow_strategy:
                return "effective"  # shadow is better suited
        if "pressure" in insufficient_reason.lower() or "overwhelm" in insufficient_reason.lower():
            if "gentle" in shadow_strategy or "break" in shadow_strategy:
                return "effective"
        if "cognitive" in insufficient_reason.lower() or "complex" in insufficient_reason.lower():
            if "micro" in shadow_strategy or "guided" in shadow_strategy:
                return "effective"
        if "affective" in insufficient_reason.lower() or "stress" in insufficient_reason.lower() or "anxiety" in insufficient_reason.lower():
            if "social" in shadow_strategy or "achievement" in shadow_strategy:
                return "effective"
        if "exam" in insufficient_reason.lower() or "deadline" in insufficient_reason.lower():
            if "selective" in shadow_strategy:
                return "effective"

        # Default: shadow also insufficient
        return "insufficient"

    def suggest_promotions(
        self,
        experiments: list[PolicyExperiment],
    ) -> list[dict[str, Any]]:
        """Suggest strategies that should be promoted based on experiment results."""
        suggestions = []
        for exp in experiments:
            if exp.status != "concluded":
                continue
            if exp.total_trials < 5:
                continue

            primary_rate = exp.primary_wins / max(exp.total_trials, 1)
            shadow_rate = exp.shadow_wins / max(exp.total_trials, 1)

            if shadow_rate > primary_rate + 0.2:
                suggestions.append({
                    "experiment_id": exp.experiment_id,
                    "current_strategy": exp.primary_strategy,
                    "suggested_strategy": exp.shadow_strategy,
                    "current_rate": round(primary_rate, 2),
                    "shadow_rate": round(shadow_rate, 2),
                    "confidence": min(exp.total_trials / 10, 1.0),
                    "action": "promote_shadow_to_primary",
                })

        return suggestions

    async def conclude_all_for_user(self, user_id: str) -> list[PolicyExperiment]:
        """Conclude all running experiments for a user."""
        experiments = await self.get_user_experiments(user_id)
        concluded = []
        for exp in experiments:
            if exp.status == "running" and exp.total_trials >= 3:
                exp = self._conclude(exp)
                await self._save(exp)
                concluded.append(exp)
        return concluded

    async def get_best_strategy_for_signal(
        self,
        user_id: str,
        signal_state_key: str,
    ) -> dict[str, Any] | None:
        """Find the best-performing strategy for a given signal type across experiments."""
        experiments = await self.get_user_experiments(user_id)
        best: dict[str, Any] | None = None
        best_rate = -1.0

        for exp in experiments:
            if exp.signal_state_key != signal_state_key or exp.total_trials < 3:
                continue
            primary_rate = exp.primary_wins / max(exp.total_trials, 1)
            shadow_rate = exp.shadow_wins / max(exp.total_trials, 1)
            winner_strategy = exp.primary_strategy if primary_rate >= shadow_rate else exp.shadow_strategy
            winner_rate = max(primary_rate, shadow_rate)

            if winner_rate > best_rate:
                best_rate = winner_rate
                best = {
                    "strategy": winner_strategy,
                    "win_rate": round(winner_rate, 3),
                    "trials": exp.total_trials,
                    "experiment_id": exp.experiment_id,
                }

        return best

    @staticmethod
    def _conclude(experiment: PolicyExperiment) -> PolicyExperiment:
        """Auto-conclude an experiment based on results."""
        if experiment.total_trials == 0:
            experiment.status = "abandoned"
            experiment.conclusion = "no_trials"
            return experiment

        primary_rate = experiment.primary_wins / experiment.total_trials
        shadow_rate = experiment.shadow_wins / experiment.total_trials

        if shadow_rate > primary_rate + 0.15:
            experiment.status = "concluded"
            experiment.conclusion = "shadow_outperforms"
        elif primary_rate > shadow_rate + 0.15:
            experiment.status = "concluded"
            experiment.conclusion = "primary_outperforms"
        else:
            experiment.status = "concluded"
            experiment.conclusion = "no_significant_difference"

        return experiment

    async def _save(self, experiment: PolicyExperiment) -> None:
        key = _EXPERIMENT_KEY.format(experiment_id=experiment.experiment_id)
        await self.redis.set(key, json.dumps(experiment.to_dict()), ex=_EXPERIMENT_TTL)

    async def _link_to_user(self, user_id: str, experiment_id: str) -> None:
        key = _USER_EXPERIMENTS_KEY.format(user_id=user_id)
        await self.redis.lrem(key, 0, experiment_id)
        await self.redis.lpush(key, experiment_id)
        await self.redis.ltrim(key, 0, _MAX_EXPERIMENTS_PER_USER - 1)
        await self.redis.expire(key, _EXPERIMENT_TTL)
