"""Regression tests for LLM fallback tier order (E3: FREE-tier failure must not upgrade to PRO)."""

from __future__ import annotations

import pytest

from app.core.agent_profiles import AgentRole, ModelTier
from app.core.llm_router import LLMSelection, ModelConfig, ModelProvider, llm_router
from app.services.llm.fallback import LLMModelFallbackManager

# 规范成本序（降序）：排在后面 = 更便宜
COST_ORDER = [
    ModelTier.MAX,
    ModelTier.TOP,
    ModelTier.PRO,
    ModelTier.REASONING,
    ModelTier.PLUS,
    ModelTier.STANDARD,
    ModelTier.FAST,
    ModelTier.SPECIALIST,
    ModelTier.GLM_BATCH,
    ModelTier.FREE_FAST,
    ModelTier.FREE_REASONING,
    ModelTier.FREE,
]


def _rank(tier: ModelTier) -> int:
    return COST_ORDER.index(tier)


def _cfg(tier: ModelTier) -> ModelConfig:
    return ModelConfig(
        provider=ModelProvider.ZHIPU,
        model_name=f"model-{tier.value}",
        base_url="https://test.example",
        api_key="key",
        tier=tier,
    )


def _selection(model_key: str, config: ModelConfig) -> LLMSelection:
    return LLMSelection(
        model_key=model_key,
        config=config,
        agent_role=AgentRole.GENERATION,
        task_type=None,
        reason="test",
    )


@pytest.mark.parametrize(
    ("failed_tier", "model_key", "expect_candidates"),
    [
        (ModelTier.FREE, "m_free", False),  # FREE 已是最低层，同层候选被排除后可为空
        (ModelTier.TOP, "m_top", True),
        (ModelTier.GLM_BATCH, "m_batch", True),
        (ModelTier.SPECIALIST, "m_spec", True),
        (ModelTier.STANDARD, "m_std", True),
    ],
)
def test_fallback_candidates_never_upgrade_to_expensive_tiers(monkeypatch, failed_tier, model_key, expect_candidates):
    """E3: tier_order 缺 FREE/TOP/GLM_BATCH/SPECIALIST 时 .index() 落到 0，失败后从最贵层起候选。"""
    models = {
        "m_max": _cfg(ModelTier.MAX),
        "m_top": _cfg(ModelTier.TOP),
        "m_pro": _cfg(ModelTier.PRO),
        "m_plus": _cfg(ModelTier.PLUS),
        "m_std": _cfg(ModelTier.STANDARD),
        "m_fast": _cfg(ModelTier.FAST),
        "m_batch": _cfg(ModelTier.GLM_BATCH),
        "m_spec": _cfg(ModelTier.SPECIALIST),
        "m_ffast": _cfg(ModelTier.FREE_FAST),
        "m_free": _cfg(ModelTier.FREE),
    }
    mapping = {
        ModelTier.MAX: ["m_max"],
        ModelTier.TOP: ["m_top"],
        ModelTier.PRO: ["m_pro"],
        ModelTier.PLUS: ["m_plus"],
        ModelTier.STANDARD: ["m_std"],
        ModelTier.FAST: ["m_fast"],
        ModelTier.GLM_BATCH: ["m_batch"],
        ModelTier.SPECIALIST: ["m_spec"],
        ModelTier.FREE_FAST: ["m_ffast"],
        ModelTier.FREE: ["m_free"],
    }
    monkeypatch.setattr(llm_router, "_available_models", models)
    monkeypatch.setattr(llm_router, "_tier_mapping", mapping)

    manager = LLMModelFallbackManager()
    candidates = manager._get_fallback_candidates(
        _selection(model_key, models[model_key]),
        exclude_models={model_key},
    )

    if expect_candidates:
        assert candidates, f"expected fallback candidates for {failed_tier}"
    for candidate in candidates:
        assert _rank(candidate.config.tier) >= _rank(failed_tier), (
            f"{failed_tier} failure produced more expensive candidate "
            f"{candidate.config.tier} (model_key={candidate.model_key})"
        )
