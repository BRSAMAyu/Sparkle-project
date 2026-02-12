from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.config import settings
from app.services.meta_learning_feature_service import MetaLearningFeatureService
from app.services.policy_registry_service import PolicyRegistryService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class MetaPolicyRecommendationService:
    """Build weekly tuning package with threshold suggestions and rollback template."""

    def __init__(self, redis_client=None):
        self.features = MetaLearningFeatureService(redis_client=redis_client)
        self.registry = PolicyRegistryService(redis_client=redis_client)

    async def build_weekly_tuning_package(self, *, days: int = 14) -> dict[str, Any]:
        vectors = await self.features.build_feature_vectors(days=days, channels=["routing", "prompt", "toolchain"])
        candidates = await self.registry.list_candidates(status="pending")
        recommendations = self._build_recommendations(vectors=vectors, candidates=candidates)
        package_id = f"mtp_{_utcnow().date().isoformat()}"
        return {
            "package_id": package_id,
            "generated_at": _utcnow().isoformat(),
            "window_days": days,
            "priority": ["quality_stability", "adoption", "fairness", "latency"],
            "recommendations": recommendations,
            "rollback_template": self._rollback_template(),
        }

    def _build_recommendations(
        self,
        *,
        vectors: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        by_channel: dict[str, list[dict[str, Any]]] = {"routing": [], "prompt": [], "toolchain": []}
        for row in vectors:
            channel = str(row.get("channel", "routing"))
            if channel in by_channel:
                by_channel[channel].append(row)

        recommendations: list[dict[str, Any]] = []
        for channel, items in by_channel.items():
            top = sorted(
                items,
                key=lambda r: (
                    float(r.get("q_global", 0.0)),
                    float(r.get("q_score", 0.0)),
                    -float(r.get("support", 0)),
                ),
            )[:3]
            for row in top:
                support = int(row.get("support", 0))
                risk = self._risk_level(channel=channel, row=row)
                suggestion = self._suggestion(channel=channel, row=row)
                scope_type = str(row.get("scope_type", "global"))
                scope_key = str(row.get("scope_key", "all"))
                strategy_pack = str(row.get("strategy_pack", "default"))
                recommendations.append(
                    {
                        "channel": channel,
                        "strategy_pack": strategy_pack,
                        "scope_type": scope_type,
                        "scope_key": scope_key,
                        "support_size": support,
                        "risk_level": risk,
                        "expected_delta": round(max(0.0, float(row.get("baseline_q_score", 0.0)) - float(row.get("q_score", 0.0))), 4),
                        "threshold_suggestions": suggestion.get("thresholds", {}),
                        "weight_suggestions": suggestion.get("weights", {}),
                        "param_suggestions": suggestion.get("params", {}),
                        "candidate_refs": [
                            str(item.get("id", ""))
                            for item in candidates
                            if str(item.get("channel", "routing")) == channel
                            and str(item.get("strategy_pack", "")) == strategy_pack
                            and str(item.get("scope_type", "global")) == scope_type
                            and str(item.get("scope_key", "all")) == scope_key
                        ][:5],
                        "rollback_plan": self._rollback_plan(channel=channel, risk_level=risk),
                    }
                )
        return recommendations

    @staticmethod
    def _risk_level(*, channel: str, row: dict[str, Any]) -> str:
        support = int(row.get("support", 0))
        fairness_gap = float(row.get("fairness_gap", 0.0))
        latency = float(row.get("normalized_latency", 0.0))
        if support < 40 or fairness_gap > float(getattr(settings, "FAIRNESS_STABLE_COHORT_Q_GAP_REDLINE", 0.08)):
            return "high"
        if channel == "toolchain" and latency > 0.6:
            return "high"
        if support < 100 or fairness_gap > 0.05:
            return "medium"
        return "low"

    @staticmethod
    def _suggestion(*, channel: str, row: dict[str, Any]) -> dict[str, dict[str, float]]:
        if channel == "prompt":
            apply_rate = float(row.get("prompt_apply_rate", 0.0))
            return {
                "thresholds": {"min_prompt_apply_rate": round(max(0.7, min(0.95, apply_rate + 0.05)), 4)},
                "params": {"exploration_ratio": 0.12 if apply_rate < 0.8 else 0.18},
            }
        if channel == "toolchain":
            degrade_rate = float(row.get("toolchain_degrade_rate", 0.0))
            return {
                "thresholds": {"max_degrade_rate": round(max(0.03, min(0.2, degrade_rate - 0.01)), 4)},
                "params": {
                    "max_parallel_experts": 1.0 if degrade_rate > 0.1 else 2.0,
                    "timeout_multiplier": 1.15 if float(row.get("normalized_latency", 0.0)) > 0.6 else 1.0,
                },
            }
        fallback_rate = float(row.get("fallback_rate", 0.0))
        return {
            "thresholds": {"min_selected_score": round(0.36 if fallback_rate > 0.08 else 0.34, 4)},
            "weights": {"decomposition_weight": 0.2 if float(row.get("q_score", 0.0)) < 0.6 else 0.12},
        }

    @staticmethod
    def _rollback_plan(*, channel: str, risk_level: str) -> dict[str, Any]:
        return {
            "trigger_rules": {
                "fallback_rate_max": 0.06 if channel == "routing" else None,
                "negative_feedback_rate_delta_max": 0.015,
                "p95_latency_delta_max": 0.12,
                "stable_cohort_q_gap_max": float(getattr(settings, "FAIRNESS_STABLE_COHORT_Q_GAP_REDLINE", 0.08)),
            },
            "actions": [
                "Disable channel canary first",
                "Rollback candidate policy to base_policy",
                "Freeze channel rollout for 24h and re-evaluate",
            ],
            "risk_level": risk_level,
        }

    @staticmethod
    def _rollback_template() -> dict[str, Any]:
        return {
            "global_trigger": [
                "fallback_rate exceeds threshold",
                "negative_feedback_rate degrades against baseline",
                "stable cohort fairness gap exceeds redline",
                "p95 latency exceeds budget",
            ],
            "rollback_order": ["toolchain", "prompt", "routing"],
            "owner_required": "human_approval",
            "postmortem_required_within_hours": 24,
        }
