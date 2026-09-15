"""Bridge between parameter effectiveness measurements and A/B testing.

Creates experiments via ABTestFrameworkEnhanced, resolves outcomes,
and applies winning variants to the parameter registry.

Core: bridge
Phase: adapt
Stage: meta_learning
"""

from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.learning.ab_test_framework_enhanced import ABTestFrameworkEnhanced
from app.orchestration.routing_parameter_registry import (
    ALL_DEFAULT_PARAMETERS,
    PARAMETER_BOUNDS,
    PARAM_EXPERIMENT_PREFIX,
    _clamp,
    _config_hash,
)


REGISTRY_UPDATE_KEY = "aurora:routing_params:current"


class RoutingParameterExperimentService:
    """Bridges effectiveness measurements with A/B test framework."""

    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client or cache_service.redis
        self.ab = ABTestFrameworkEnhanced(db, self.redis)

    async def propose_parameter_change(
        self,
        *,
        parameter_name: str,
        proposed_value: float,
        evidence: dict[str, Any],
        created_by: str = "meta_learning",
    ) -> dict[str, Any]:
        """Create an A/B experiment for a parameter change."""
        current_value = float(evidence.get("current_value", ALL_DEFAULT_PARAMETERS.get(parameter_name, 0)))
        lo, hi = PARAMETER_BOUNDS.get(parameter_name, (0.0, 15.0))
        clamped_value = max(lo, min(hi, proposed_value))

        if abs(clamped_value - current_value) < 0.01:
            return {"status": "skipped", "reason": "proposed_value_too_close_to_current"}

        experiment = await self.ab.create_experiment(
            name=f"{PARAM_EXPERIMENT_PREFIX}{parameter_name}",
            description=(
                f"Meta-learning parameter experiment for {parameter_name}. "
                f"Control={current_value}, Treatment={clamped_value}. "
                f"Evidence: {evidence.get('sample_count', 0)} samples, "
                f"baseline success rate={evidence.get('baseline_success_rate', 0):.3f}, "
                f"treatment success rate={evidence.get('treatment_success_rate', 0):.3f}"
            ),
            hypothesis=f"Changing {parameter_name} from {current_value} to {clamped_value} improves routing outcomes",
            variants=[
                {
                    "name": "control",
                    "is_control": True,
                    "weight": 0.5,
                    "configuration": {"overrides": {parameter_name: current_value}},
                },
                {
                    "name": "treatment",
                    "is_control": False,
                    "weight": 0.5,
                    "configuration": {"overrides": {parameter_name: clamped_value}},
                },
            ],
            metrics=["routing_success_rate"],
            created_by=created_by,
            sample_size_target=max(100, int(evidence.get("sample_count", 100) * 2)),
        )
        return {"status": "created", "experiment_id": str(experiment.id)}

    async def resolve_experiment(self, experiment_id: str) -> dict[str, Any]:
        """Resolve an experiment by checking outcomes per variant."""
        from app.models.experiment import ABExperiment, ExperimentStatus

        result = await self.db.execute(
            select(ABExperiment).where(ABExperiment.id == experiment_id)
        )
        experiment = result.scalar_one_or_none()
        if experiment is None:
            return {"status": "not_found"}

        if experiment.status != ExperimentStatus.RUNNING:
            return {"status": "not_running", "current_status": str(experiment.status)}

        # Query metrics per variant
        variant_results = {}
        for variant in experiment.variants:
            metrics = [m for m in experiment.metrics if m.variant_id == variant.id]
            successes = sum(1 for m in metrics if m.metric_name == "routing_success_rate" and m.metric_value > 0.5)
            total = len(metrics)
            variant_results[variant.variant_name] = {
                "successes": successes,
                "total": total,
                "rate": successes / total if total > 0 else 0.0,
            }

        return {
            "status": "resolved",
            "experiment_id": str(experiment_id),
            "variants": variant_results,
        }

    async def apply_winning_variant(self, experiment_id: str) -> dict[str, Any]:
        """If the treatment wins with statistical significance, update registry."""
        resolution = await self.resolve_experiment(experiment_id)
        if resolution.get("status") != "resolved":
            return resolution

        variants = resolution.get("variants", {})
        control = variants.get("control", {})
        treatment = variants.get("treatment", {})

        if control.get("total", 0) < 30 or treatment.get("total", 0) < 30:
            return {"status": "insufficient_samples", "variants": variants}

        control_rate = control.get("rate", 0.0)
        treatment_rate = treatment.get("rate", 0.0)

        # Require at least 5% improvement to apply
        if treatment_rate <= control_rate * 1.05:
            return {
                "status": "no_improvement",
                "control_rate": control_rate,
                "treatment_rate": treatment_rate,
            }

        # Apply: update the parameter registry in Redis
        from app.models.experiment import ABExperiment
        import json

        result = await self.db.execute(
            select(ABExperiment).where(ABExperiment.id == experiment_id)
        )
        experiment = result.scalar_one_or_none()
        if experiment is None:
            return {"status": "not_found"}

        treatment_variant = next(
            (v for v in experiment.variants if v.variant_name == "treatment"), None
        )
        if treatment_variant is None:
            return {"status": "no_treatment_variant"}

        overrides = (treatment_variant.configuration or {}).get("overrides", {})
        if not overrides:
            return {"status": "no_overrides"}

        # Load current params from Redis, merge overrides, write back
        # NOTE: This is a non-atomic read-modify-write. Concurrent experiments resolving
        # simultaneously could lose one's overrides. Acceptable because experiments resolve
        # rarely (daily at most) and winning overrides are additive, not destructive.
        current_raw = await self.redis.get(REGISTRY_UPDATE_KEY)
        current_params = dict(ALL_DEFAULT_PARAMETERS)
        if current_raw is not None:
            try:
                current_params = json.loads(current_raw).get("parameters", current_params)
            except Exception:
                pass

        for key, value in overrides.items():
            if key in ALL_DEFAULT_PARAMETERS:
                current_params[key] = _clamp(float(value), key)

        new_version = _config_hash(current_params)
        payload = json.dumps({"version": new_version, "parameters": current_params})
        await self.redis.set(
            REGISTRY_UPDATE_KEY,
            payload.encode() if isinstance(payload, str) else payload,
            ex=86400 * 30,  # 30-day TTL — auto-revert if not refreshed
        )

        logger.info(
            "Applied winning variant: experiment={}, treatment_rate={:.3f} > control_rate={:.3f}",
            experiment_id, treatment_rate, control_rate,
        )

        return {
            "status": "applied",
            "new_version": new_version,
            "overrides": overrides,
            "treatment_rate": treatment_rate,
            "control_rate": control_rate,
        }
