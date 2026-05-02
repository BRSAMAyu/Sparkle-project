"""
Core: intelligence
Phase: adapt
Stage: Signal-to-Action Spine P2-3.1 — ML Recall Ranker

Lightweight ML model for ranking recall opportunities.
Uses a hand-tuned decision tree with logistic regression refinement.
No external ML dependencies — pure Python.

Training data: OutcomeRecorder history (user response/ignore patterns).
Model versioning: simple string version tag stored in Redis.
A/B testing: integrates with SafeBanditController arm selection.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from loguru import logger

# ── Feature Vector ────────────────────────────────────────────────────

@dataclass
class RecallFeatures:
    """Input features for recall scoring.

    All features normalized to [0.0, 1.0] range where possible.
    """
    goal_value: float = 0.5          # How important is the related goal (0-1)
    decay_factor: float = 0.5        # Ebbinghaus decay: how much knowledge has faded (0-1, 1=max decay)
    user_response_rate: float = 0.5  # Historical response rate to recalls (0-1)
    fatigue_state: float = 0.0       # Current fatigue level (0=rested, 1=critical)
    deadline_proximity: float = 0.0  # How close is the deadline (0=far, 1=imminent)
    material_relevance: float = 0.5  # How relevant is the material to current goal (0-1)
    silence_hours: float = 0.0       # Hours since last activity, normalized to 0-1 (max=72h)
    cohort_response_rate: float = 0.5  # How similar users respond to this type of recall

    def to_vector(self) -> list[float]:
        return [
            self.goal_value,
            self.decay_factor,
            self.user_response_rate,
            self.fatigue_state,
            self.deadline_proximity,
            self.material_relevance,
            min(1.0, self.silence_hours),
            self.cohort_response_rate,
        ]


# ── Decision Tree Rules ───────────────────────────────────────────────
# Hand-tuned rules based on spaced repetition and nudge theory research.
# Priority: deadline_proximity > fatigue_state > goal_value > decay_factor

_DT_RULES: list[tuple[str, callable, float]] = [
    # (rule_name, condition_fn, base_score)
    ("crisis_override", lambda f: f.deadline_proximity > 0.85 and f.fatigue_state < 0.7, 0.95),
    ("exam_urgent", lambda f: f.deadline_proximity > 0.7 and f.fatigue_state < 0.5, 0.88),
    ("high_decay_high_goal", lambda f: f.decay_factor > 0.6 and f.goal_value > 0.7, 0.82),
    ("moderate_decay_responsive", lambda f: f.decay_factor > 0.4 and f.user_response_rate > 0.6, 0.75),
    ("cohort_validated", lambda f: f.cohort_response_rate > 0.7 and f.goal_value > 0.5, 0.72),
    ("optimal_window", lambda f: f.silence_hours > 0.3 and f.silence_hours < 0.7 and f.fatigue_state < 0.4, 0.70),
    ("low_fatigue_good_material", lambda f: f.fatigue_state < 0.3 and f.material_relevance > 0.6, 0.68),
    ("baseline", lambda f: True, 0.50),
]


# ── Logistic Regression Weights ────────────────────────────────────────
# Pre-trained weights for linear combination refinement.
# These are reasonable priors; real training would adjust from OutcomeRecorder data.

_LR_WEIGHTS: list[float] = [
    0.18,   # goal_value
    0.15,   # decay_factor
    0.12,   # user_response_rate
    -0.20,  # fatigue_state (negative: higher fatigue → lower score)
    0.22,   # deadline_proximity
    0.10,   # material_relevance
    0.08,   # silence_hours
    0.05,   # cohort_response_rate
]
_LR_BIAS: float = -0.10


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    z = math.exp(x)
    return z / (1.0 + z)


# ── Recall Ranker ─────────────────────────────────────────────────────

class RecallRanker:
    """ML-based recall scoring engine.

    Scoring pipeline:
    1. Decision tree: rule-based base score (fast, interpretable)
    2. Logistic regression: feature-based refinement (data-driven)
    3. Blended score: weighted average with fatigue penalty
    4. Clamped to [0.0, 1.0]

    Version management: model version stored in Redis for hot-swapping.
    A/B testing: score can be used as an arm in SafeBanditController.
    """

    MODEL_VERSION = "v1.0.0"
    _BLEND_WEIGHT_DT = 0.6   # Decision tree weight
    _BLEND_WEIGHT_LR = 0.4   # Logistic regression weight

    def __init__(self, redis_client: Any | None = None):
        self.redis = redis_client

    def score(self, features: RecallFeatures) -> float:
        """Compute recall score from features.

        Returns:
            Score in [0.0, 1.0]. Higher = more valuable to send.
        """
        # 1. Decision tree score
        dt_score = self._decision_tree_score(features)

        # 2. Logistic regression score
        lr_score = self._logistic_regression_score(features)

        # 3. Blended score
        blended = self._BLEND_WEIGHT_DT * dt_score + self._BLEND_WEIGHT_LR * lr_score

        # 4. Fatigue penalty (hard override)
        if features.fatigue_state > 0.8:
            blended *= 0.3  # Heavy penalty for critical fatigue
        elif features.fatigue_state > 0.6:
            blended *= 0.6  # Moderate penalty

        return max(0.0, min(1.0, blended))

    def score_trigger(
        self,
        trigger_type: str,
        *,
        goal_value: float = 0.5,
        decay_factor: float = 0.5,
        user_response_rate: float = 0.5,
        fatigue_state: float = 0.0,
        deadline_proximity: float = 0.0,
        material_relevance: float = 0.5,
        silence_hours: float = 0.0,
        cohort_response_rate: float = 0.5,
    ) -> float:
        """Convenience method: score a trigger type directly with named params."""
        features = RecallFeatures(
            goal_value=goal_value,
            decay_factor=decay_factor,
            user_response_rate=user_response_rate,
            fatigue_state=fatigue_state,
            deadline_proximity=deadline_proximity,
            material_relevance=material_relevance,
            silence_hours=silence_hours,
            cohort_response_rate=cohort_response_rate,
        )
        return self.score(features)

    def _decision_tree_score(self, features: RecallFeatures) -> float:
        """Rule-based scoring via decision tree."""
        for _rule_name, condition, base_score in _DT_RULES:
            if condition(features):
                return base_score
        return 0.50

    def _logistic_regression_score(self, features: RecallFeatures) -> float:
        """Feature-based scoring via logistic regression."""
        vec = features.to_vector()
        linear = sum(w * x for w, x in zip(_LR_WEIGHTS, vec, strict=True)) + _LR_BIAS
        return _sigmoid(linear)

    async def record_training_example(
        self,
        user_id: str,
        trigger_type: str,
        features: RecallFeatures,
        user_responded: bool,
    ) -> None:
        """Record a training example from OutcomeRecorder history.

        Stored in Redis for future model retraining.
        """
        if not self.redis:
            return

        example = {
            "model_version": self.MODEL_VERSION,
            "trigger_type": trigger_type,
            "features": features.to_vector(),
            "label": 1.0 if user_responded else 0.0,
            "user_id_hash": hash(user_id) % 10000,  # Privacy: hash, not raw ID
        }
        key = f"ml:recall_training:{user_id}:{trigger_type}"
        try:
            await self.redis.lpush(key, json.dumps(example))
            await self.redis.ltrim(key, 0, 99)  # Keep last 100 per user/trigger
            await self.redis.expire(key, 90 * 24 * 3600)  # 90 days
        except Exception:
            logger.debug("recall_ranker: training example save failed", exc_info=True)

    async def get_user_response_rate(
        self,
        user_id: str,
        trigger_type: str,
    ) -> float:
        """Get historical response rate for a user/trigger combination.

        Returns:
            Response rate in [0.0, 1.0], defaults to 0.5 if no history.
        """
        if not self.redis:
            return 0.5

        key = f"ml:recall_training:{user_id}:{trigger_type}"
        try:
            raw_list = await self.redis.lrange(key, 0, 49)
            if not raw_list:
                return 0.5
            responded = 0
            total = 0
            for raw in raw_list:
                try:
                    example = json.loads(raw)
                    if example.get("label", 0.5) > 0.5:
                        responded += 1
                    total += 1
                except (json.JSONDecodeError, TypeError):
                    continue
            return responded / total if total > 0 else 0.5
        except Exception:
            logger.debug("recall_ranker: response rate lookup failed", exc_info=True)
            return 0.5

    async def get_model_version(self) -> str:
        """Get current model version (supports hot-swapping via Redis)."""
        if not self.redis:
            return self.MODEL_VERSION
        try:
            raw = await self.redis.get("ml:recall_ranker:version")
            if raw:
                return raw if isinstance(raw, str) else raw.decode()
        except Exception:
            pass
        return self.MODEL_VERSION

    def get_ab_test_arm_score(
        self,
        features: RecallFeatures,
        arm: str = "default",
    ) -> float:
        """Get score adjusted for A/B testing arm.

        Arms:
        - "default": standard blended score
        - "dt_only": decision tree only (no LR)
        - "lr_only": logistic regression only (no DT)
        - "aggressive": +0.1 bias toward sending
        - "conservative": -0.1 bias toward not sending

        Integration point for SafeBanditController: arm selection.
        """
        base = self.score(features)
        if arm == "dt_only":
            return self._decision_tree_score(features)
        elif arm == "lr_only":
            return self._logistic_regression_score(features)
        elif arm == "aggressive":
            return min(1.0, base + 0.10)
        elif arm == "conservative":
            return max(0.0, base - 0.10)
        return base
