"""
Free-tier model downgrade (free_tier_downgrade) unit tests.

红绿契约：
- free 用户请求高于 ceiling（默认 fast）的能力层时，selection 落到 ceiling 层
  （2026-09 主力切 Qwen 后 FAST 首位 = dashscope_fast/qwen3.7-flash），reason 含
  free_tier_downgrade 标记，Prometheus 计数器自增
- pro / 未标记用户不受影响（付费全能力，premium → 重模型不变）
- 网关信号：ChatRequest.user_profile.is_pro（已在链路），extra_context.user_tier 可显式覆盖
"""
from __future__ import annotations

import pytest
from prometheus_client import REGISTRY

from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.core.llm_router import (
    LLMRouter,
    get_request_user_tier,
    reset_request_user_tier,
    set_request_user_tier,
)

METRIC_FREE_DOWNGRADE = "sparkle_llm_router_free_tier_downgrade_total"


@pytest.fixture(autouse=True)
def _deterministic_env(monkeypatch):
    """环境无关化（E-06 同款坑）：清空 .env 泄漏的 *_API_KEY/LLM_TIER_*，
    使 LLMRouter() 构造出确定性默认池（无 key 环境）。"""
    from app.config import settings as _s

    for k in [k for k in vars(_s) if k.endswith("_API_KEY") or k.startswith("LLM_TIER_")]:
        monkeypatch.setattr(_s, k, "")


@pytest.fixture
def router() -> LLMRouter:
    """Create a fresh LLMRouter instance (isolated health state)."""
    return LLMRouter()


@pytest.fixture(autouse=True)
def _clean_user_tier():
    token = set_request_user_tier(None)
    yield
    reset_request_user_tier(token)


def _free_downgrade_count(labels: dict[str, str]) -> float:
    # O-04：counter 增加 plan 有界维度；本文件的钳制计数断言均在 free plan 下发生。
    value = REGISTRY.get_sample_value(METRIC_FREE_DOWNGRADE, {**labels, "plan": "free"})
    return value or 0.0


# ---------------------------------------------------------------------------
# 核心红绿：free 用户 max 请求 → flash + reason 标记；premium → 重模型不变
# ---------------------------------------------------------------------------


def test_free_user_forced_max_clamps_to_fast_with_reason(router: LLMRouter):
    set_request_user_tier("free")
    labels = {"agent_role": "generation", "from_tier": "max", "to_tier": "fast"}
    before = _free_downgrade_count(labels)

    selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.MAX)

    assert selection.config.tier == ModelTier.FAST
    assert selection.model_key == "dashscope_fast"  # 默认 FAST 层首位（2026-09 主力切 Qwen）
    assert selection.free_tier_downgrade is True
    assert "free_tier_downgrade(max->fast)" in selection.reason
    assert _free_downgrade_count(labels) == pytest.approx(before + 1)


def test_pro_user_forced_max_unchanged(router: LLMRouter):
    set_request_user_tier("pro")

    selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.MAX)

    # 池条目自带 tier 标签可能是 MAX 或 PRO；本质断言是 model 与钳制语义
    assert selection.config.tier in (ModelTier.MAX, ModelTier.PRO)
    assert selection.model_key == "qwen3_8_max"  # 默认 MAX 层首位（2026-09 主力切 Qwen）
    assert selection.free_tier_downgrade is False
    assert "free_tier_downgrade" not in selection.reason


def test_unset_tier_keeps_legacy_behavior(router: LLMRouter):
    """未标记分层的调用面（内部批量/定时任务）保持现状不钳制。"""
    assert get_request_user_tier() is None

    selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.MAX)

    # 池条目自带 tier 标签可能是 MAX 或 PRO；本质断言是 model 与钳制语义
    assert selection.config.tier in (ModelTier.MAX, ModelTier.PRO)
    assert selection.free_tier_downgrade is False


# ---------------------------------------------------------------------------
# 策略路径（AgentModelPolicy）与普通任务路径
# ---------------------------------------------------------------------------


def test_free_user_deep_reasoning_task_lands_fast_via_policy(router: LLMRouter):
    set_request_user_tier("free")

    selection = router.select_model(
        AgentRole.DEEP_ANALYST, TaskType.DEEP_REASONING, reasoning_mode="deep"
    )

    assert selection.config.tier == ModelTier.FAST
    assert selection.free_tier_downgrade is True
    assert "free_tier_downgrade(pro->fast)" in selection.reason


def test_pro_user_deep_reasoning_task_keeps_heavy_tier(router: LLMRouter):
    set_request_user_tier("pro")

    selection = router.select_model(
        AgentRole.DEEP_ANALYST, TaskType.DEEP_REASONING, reasoning_mode="deep"
    )

    assert selection.config.tier in {ModelTier.PRO, ModelTier.PLUS, ModelTier.MAX}
    assert selection.free_tier_downgrade is False


def test_free_user_standard_task_clamps_to_fast(router: LLMRouter):
    set_request_user_tier("free")

    selection = router.select_model(AgentRole.GENERATION, TaskType.STANDARD_RESPONSE)

    assert selection.config.tier == ModelTier.FAST
    assert selection.free_tier_downgrade is True


def test_pro_user_standard_task_keeps_standard(router: LLMRouter):
    set_request_user_tier("pro")

    selection = router.select_model(AgentRole.GENERATION, TaskType.STANDARD_RESPONSE)

    assert selection.config.tier == ModelTier.STANDARD
    assert selection.free_tier_downgrade is False


# ---------------------------------------------------------------------------
# 候选链一致性（fallback 链不再回到重模型）
# ---------------------------------------------------------------------------


def test_free_user_candidate_chain_has_no_heavy_tiers(router: LLMRouter):
    set_request_user_tier("free")

    candidates = router.resolve_candidate_models(
        AgentRole.DEEP_ANALYST, TaskType.DEEP_REASONING
    )

    assert candidates
    for model_key in candidates:
        assert router._available_models[model_key].tier == ModelTier.FAST


def test_free_user_forced_max_candidate_chain_clamped(router: LLMRouter):
    set_request_user_tier("free")

    candidates = router.resolve_candidate_models(
        AgentRole.GENERATION, force_tier=ModelTier.MAX
    )

    assert candidates == list(router._tier_mapping[ModelTier.FAST])


# ---------------------------------------------------------------------------
# 配置面：ceiling 可调 + 总开关
# ---------------------------------------------------------------------------


def test_ceiling_standard_allows_standard_for_free(router: LLMRouter, monkeypatch):
    monkeypatch.setattr(settings, "FREE_TIER_MODEL_CEILING", "standard", raising=False)
    set_request_user_tier("free")

    selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.MAX)

    assert selection.config.tier == ModelTier.STANDARD
    assert "free_tier_downgrade(max->standard)" in selection.reason


def test_invalid_ceiling_falls_back_to_fast(router: LLMRouter, monkeypatch):
    monkeypatch.setattr(settings, "FREE_TIER_MODEL_CEILING", "nonsense", raising=False)
    set_request_user_tier("free")

    selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.MAX)

    assert selection.config.tier == ModelTier.FAST
    assert selection.free_tier_downgrade is True


def test_kill_switch_disables_clamp(router: LLMRouter, monkeypatch):
    monkeypatch.setattr(settings, "FREE_TIER_DOWNGRADE_ENABLED", False, raising=False)
    set_request_user_tier("free")

    selection = router.select_model(AgentRole.GENERATION, force_tier=ModelTier.MAX)

    # 池条目自带 tier 标签可能是 MAX 或 PRO；本质断言是 model 与钳制语义
    assert selection.config.tier in (ModelTier.MAX, ModelTier.PRO)
    assert selection.free_tier_downgrade is False


# ---------------------------------------------------------------------------
# 网关信号消费（StreamChat 入口，ChatRequest.user_profile.is_pro）
# ---------------------------------------------------------------------------


def test_streamchat_entry_resolves_tier_from_user_profile():
    from app.gen.agent.v1 import agent_service_pb2
    from app.services.agent_grpc_service import AgentServiceImpl

    req_free = agent_service_pb2.ChatRequest(user_id="u")
    assert AgentServiceImpl._resolve_request_user_tier(req_free) == "free"

    req_pro = agent_service_pb2.ChatRequest(
        user_id="u",
        user_profile=agent_service_pb2.UserProfile(is_pro=True),
    )
    assert AgentServiceImpl._resolve_request_user_tier(req_pro) == "pro"


def test_streamchat_entry_extra_context_tier_override():
    from google.protobuf.struct_pb2 import Struct

    from app.gen.agent.v1 import agent_service_pb2
    from app.services.agent_grpc_service import AgentServiceImpl

    extra = Struct()
    extra.update({"user_tier": "free"})
    req_override_free = agent_service_pb2.ChatRequest(
        user_id="u",
        user_profile=agent_service_pb2.UserProfile(is_pro=True),
        extra_context=extra,
    )
    assert AgentServiceImpl._resolve_request_user_tier(req_override_free) == "free"

    extra_pro = Struct()
    extra_pro.update({"user_tier": "premium"})
    req_override_pro = agent_service_pb2.ChatRequest(
        user_id="u",
        extra_context=extra_pro,
    )
    assert AgentServiceImpl._resolve_request_user_tier(req_override_pro) == "pro"
