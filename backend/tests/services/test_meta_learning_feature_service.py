from __future__ import annotations

import pytest

from app.services.meta_learning_feature_service import MetaLearningFeatureService


@pytest.mark.asyncio
async def test_meta_learning_feature_vectors_channel_scope():
    service = MetaLearningFeatureService(redis_client=None)

    async def _fake_rollups(*, days: int):
        _ = days
        return [
            {
                "strategy_pack": "general_v2",
                "cohort_id": "cohort::study::medium::high_engagement::rhythm_steady",
                "user_scope": "usr::111111111111",
                "q_score": 0.61,
                "normalized_latency": 0.42,
                "feedback_up_rate": 0.64,
                "fallback_rate": 0.08,
                "prompt_apply_rate": 0.84,
                "toolchain_degrade_rate": 0.05,
                "counts": {
                    "expert_selected": 110,
                    "prompt_selected": 100,
                    "prompt_applied": 82,
                    "toolchain_selected": 95,
                    "route_decision": 140,
                },
            }
        ]

    service.rollup_service.list_rollups = _fake_rollups  # type: ignore[method-assign]
    vectors = await service.build_feature_vectors(days=7, channels=["routing", "prompt", "toolchain"])
    assert vectors
    channels = {str(v["channel"]) for v in vectors}
    assert {"routing", "prompt", "toolchain"}.issubset(channels)
    sample = vectors[0]
    assert "q_global" in sample
    assert 0.0 <= float(sample["q_global"]) <= 1.0
