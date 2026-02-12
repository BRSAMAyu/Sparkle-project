from __future__ import annotations

import pytest

from app.services.meta_policy_recommendation_service import MetaPolicyRecommendationService


@pytest.mark.asyncio
async def test_meta_policy_recommendation_package_structure():
    service = MetaPolicyRecommendationService(redis_client=None)

    async def _fake_vectors(*, days: int, channels: list[str] | None = None):
        _ = days
        _ = channels
        return [
            {
                "channel": "routing",
                "strategy_pack": "general_v2",
                "scope_type": "global",
                "scope_key": "all",
                "support": 120,
                "q_score": 0.55,
                "baseline_q_score": 0.62,
                "fairness_gap": 0.04,
                "normalized_latency": 0.45,
                "fallback_rate": 0.09,
                "q_global": 0.58,
            },
            {
                "channel": "prompt",
                "strategy_pack": "general_v2",
                "scope_type": "cohort",
                "scope_key": "cohort::study",
                "support": 88,
                "q_score": 0.57,
                "baseline_q_score": 0.61,
                "fairness_gap": 0.03,
                "normalized_latency": 0.33,
                "prompt_apply_rate": 0.79,
                "q_global": 0.6,
            },
        ]

    async def _fake_candidates(*, status: str | None = None):
        _ = status
        return [
            {
                "id": "pc_prompt_1",
                "channel": "prompt",
                "strategy_pack": "general_v2",
                "scope_type": "cohort",
                "scope_key": "cohort::study",
            }
        ]

    service.features.build_feature_vectors = _fake_vectors  # type: ignore[method-assign]
    service.registry.list_candidates = _fake_candidates  # type: ignore[method-assign]
    package = await service.build_weekly_tuning_package(days=14)
    assert package["package_id"].startswith("mtp_")
    assert "recommendations" in package
    assert "rollback_template" in package
    assert len(package["recommendations"]) >= 2
