"""Versioned Redis-backed parameter registry for DualCoreRouter.

Externalizes hardcoded routing parameters (precedence weights, thresholds,
profile defaults) so they can be observed, A/B tested, and meta-learned
without code changes. Falls back to hardcoded defaults when Redis is empty
or the meta-learning kill switch is off.

Core: bridge
Phase: adapt
Stage: meta_learning
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.core.kill_switch import KillSwitchBinding, is_enabled_mode, read_mode

REDIS_KEY_PREFIX = "aurora:"
PARAM_REGISTRY_KEY = "routing_params"
PARAM_EXPERIMENT_PREFIX = "meta_learning_param:"
META_LEARNING_BINDING = KillSwitchBinding(
    stage="meta_learning",
    feature="routing_parameters",
    redis_key="meta_learning:routing_params",
    settings_attr="AURORA_META_LEARNING_ROUTING_PARAMS_MODE",
    fallback_mode="off",
)

# ---------------------------------------------------------------------------
# Hardcoded defaults — must stay in sync with dual_core_router.py values
# ---------------------------------------------------------------------------

DEFAULT_PRECEDENCE_WEIGHTS: dict[str, float] = {
    "emotional_block": 9.0,
    "procrastination": 8.0,
    "cognitive_mode": 7.0,
    "low_metacognition": 6.0,
    "high_cognitive_load": 5.0,
    "spine_fatigue": 4.0,
    "reflection_phase": 3.0,
    "goal_clarity": 1.0,
    "scaffolding_frustration": 6.5,
    "scaffolding_boredom": 2.5,
}

DEFAULT_THRESHOLDS: dict[str, float | int] = {
    "goal_clear_threshold_base": 0.72,
    "goal_clear_threshold_sensitivity": 0.2,
    "low_confidence_threshold_base": 0.6,
    "low_confidence_threshold_sensitivity": 0.2,
    "high_cognitive_load_threshold": 0.55,
    "very_high_cognitive_load": 0.78,
    "spine_state_confidence_min": 0.45,
    "spine_fatigue_confidence_min": 0.6,
    "procrastination_friction_weight": 0.18,
    "emotional_block_negative_ratio": 0.6,
    "corrections_threshold": 3,
}

DEFAULT_PROFILE_DEFAULTS: dict[str, float] = {
    "procrastination_threshold": 0.6,
    "emotional_sensitivity": 0.5,
    "directness_preference": 0.5,
}

# Bounds enforce safety: no parameter can drift beyond these limits.
PARAMETER_BOUNDS: dict[str, tuple[float, float]] = {
    # Precedence weights: [0, 15]
    **{k: (0.0, 15.0) for k in DEFAULT_PRECEDENCE_WEIGHTS},
    # Thresholds: various
    "goal_clear_threshold_base": (0.3, 0.95),
    "goal_clear_threshold_sensitivity": (0.0, 0.5),
    "low_confidence_threshold_base": (0.2, 0.9),
    "low_confidence_threshold_sensitivity": (0.0, 0.5),
    "high_cognitive_load": (0.3, 0.9),
    "very_high_cognitive_load": (0.5, 0.99),
    "spine_state_confidence_min": (0.1, 0.8),
    "spine_fatigue_confidence_min": (0.2, 0.9),
    "procrastination_friction_weight": (0.01, 0.5),
    "emotional_block_negative_ratio": (0.3, 0.9),
    "corrections_threshold": (1, 10),
    # Profile defaults: [0.1, 0.95]
    **{k: (0.1, 0.95) for k in DEFAULT_PROFILE_DEFAULTS},
}

ALL_DEFAULT_PARAMETERS: dict[str, float | int] = {
    **DEFAULT_PRECEDENCE_WEIGHTS,
    **DEFAULT_THRESHOLDS,
    **DEFAULT_PROFILE_DEFAULTS,
}


def _config_hash(params: dict[str, Any]) -> str:
    """Deterministic hash of a parameter configuration for versioning."""
    payload = json.dumps(params, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def _clamp(value: float, param_name: str) -> float:
    lo, hi = PARAMETER_BOUNDS.get(param_name, (0.0, 15.0))
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Immutable snapshot returned to callers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoutingParameterSnapshot:
    """Immutable snapshot of routing parameters used for a single routing decision."""

    version: str
    source: str  # "defaults" | "redis" | "experiment"
    parameters: dict[str, float | int] = field(default_factory=dict)

    def get(self, key: str, default: float | int | None = None) -> float | int | None:
        return self.parameters.get(key, default)

    def precedence_weights(self) -> dict[str, float]:
        return {k: float(v) for k, v in self.parameters.items() if k in DEFAULT_PRECEDENCE_WEIGHTS}

    def threshold(self, key: str) -> float | int:
        return self.parameters.get(key, ALL_DEFAULT_PARAMETERS.get(key, 0))

    def profile_defaults(self) -> dict[str, float]:
        return {k: float(v) for k, v in self.parameters.items() if k in DEFAULT_PROFILE_DEFAULTS}

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "source": self.source,
            "parameters": dict(self.parameters),
        }


# ---------------------------------------------------------------------------
# Registry: reads from Redis with fallback to defaults
# ---------------------------------------------------------------------------


class RoutingParameterRegistry:
    """Reads routing parameters from a versioned Redis key with fallback.

    Not a singleton — construct per-request to avoid stale reads.
    Delegates to existing kill_switch infrastructure for the overall mode.
    """

    def __init__(self, redis_client=None, *, user_id: str | None = None):
        self._redis = redis_client
        self._user_id = user_id
        self._mode: str | None = None

    async def _resolve_mode(self) -> str:
        if self._mode is not None:
            return self._mode
        if self._redis is None:
            self._mode = "off"
            return "off"
        try:
            self._mode = await read_mode(
                redis_client=self._redis,
                prefix=REDIS_KEY_PREFIX,
                binding=META_LEARNING_BINDING,
            )
        except Exception:
            logger.warning("Failed to read meta-learning mode from Redis, defaulting to off")
            self._mode = "off"
        return self._mode

    async def load(self, *, db=None) -> RoutingParameterSnapshot:
        """Load parameters for the current context.

        Resolution order:
        1. If meta-learning is off → return hardcoded defaults
        2. If user_id set and active experiments exist → assign variant, overlay overrides
        3. Try Redis versioned key → return if found
        4. Fallback → return hardcoded defaults
        """
        mode = await self._resolve_mode()
        if not is_enabled_mode(mode):
            return self._defaults_snapshot()

        if self._redis is None:
            return self._defaults_snapshot()

        try:
            raw = await self._redis.get(f"{REDIS_KEY_PREFIX}{PARAM_REGISTRY_KEY}:current")
            if raw is None:
                base_params = dict(ALL_DEFAULT_PARAMETERS)
                base_version = "defaults"
            else:
                data = json.loads(raw)
                base_params = self._merge_with_defaults(data.get("parameters", {}))
                base_version = data.get("version") or _config_hash(base_params)

            # User-level experiment overlay
            if self._user_id and db is not None:
                experiment_overrides = await self._load_experiment_overrides(db)
                if experiment_overrides is not None:
                    for key, value in experiment_overrides.items():
                        if key in ALL_DEFAULT_PARAMETERS:
                            base_params[key] = _clamp(float(value), key)
                    return RoutingParameterSnapshot(
                        version=f"{base_version}:exp",
                        source="experiment",
                        parameters=base_params,
                    )

            source = "defaults" if raw is None else "redis"
            return RoutingParameterSnapshot(
                version=base_version,
                source=source,
                parameters=base_params,
            )
        except Exception:
            logger.warning("Failed to load routing parameters from Redis, using defaults")
            return self._defaults_snapshot()

    async def _load_experiment_overrides(self, db) -> dict[str, Any] | None:
        """Load parameter overrides from an active experiment for this user."""
        try:
            from app.learning.ab_test_framework_enhanced import ABTestFrameworkEnhanced
            from app.models.experiment import ABExperiment, ExperimentStatus

            ab = ABTestFrameworkEnhanced(db, self._redis)

            # Find active parameter experiments
            from sqlalchemy import select
            stmt = select(ABExperiment).where(
                ABExperiment.name.like(f"{PARAM_EXPERIMENT_PREFIX}%"),
                ABExperiment.status == ExperimentStatus.RUNNING,
            )
            result = await db.execute(stmt)
            experiments = result.scalars().all()

            for experiment in experiments:
                variant, _ = await ab.assign_variant(
                    experiment_id=str(experiment.id),
                    user_id=self._user_id,
                )
                if variant and not variant.is_control:
                    overrides = (variant.configuration or {}).get("overrides", {})
                    if overrides:
                        return overrides
        except Exception as exc:
            logger.warning("Failed to load experiment overrides: {}", exc)
        return None

    @staticmethod
    def _defaults_snapshot() -> RoutingParameterSnapshot:
        version = _config_hash(ALL_DEFAULT_PARAMETERS)
        return RoutingParameterSnapshot(
            version=version,
            source="defaults",
            parameters=dict(ALL_DEFAULT_PARAMETERS),
        )

    @staticmethod
    def _merge_with_defaults(overrides: dict[str, Any]) -> dict[str, float | int]:
        """Merge overrides into defaults, clamping each value to its bounds."""
        merged = dict(ALL_DEFAULT_PARAMETERS)
        for key, value in overrides.items():
            if key not in ALL_DEFAULT_PARAMETERS:
                continue
            if isinstance(value, (int, float)):
                merged[key] = _clamp(float(value), key)
        return merged
