"""小米 mimo 车道门控契约测试（PROD-FIX-4 立门，XIAOMI-MODEL 2026-09-22 回挂改约）.

历史缺陷（PROD-LOG2 ②-3 / PROD-FIX-4）：settings 默认 ``mimo-v2-flash`` 被小米
端点拒绝（404 Unsupported model），且无 key 环境这些条目照样注册——链上人人
带一个必炸 hop。PROD-FIX-4 两层处置：key-gate 注册 + 死模型名摘出默认链。

XIAOMI-MODEL 考证回挂（2026-09-22）：404 根因坐实为**模型名下线**——
``mimo-v2-flash`` 已于北京时间 2026-06-30 00:00 正式下线（官方 deprecate 公告，
mimo.mi.com/static/docs/updates/deprecate.md）。两车道模型名已更正为
``mimo-v2.6-flash``（V2.6 系列 2026-09-22 发布；官方替代品 mimo-v2.5 将于
2026-10-21 10:00 下线，故不挂它），FAST/STANDARD 默认链按摘除前原位次（第 3
位）回挂。

钉住的契约（新真值）：
- 模型名契约：注册条目的 model_name 必须是官方现行 id ``mimo-v2.6-flash``
  （防止再次漂移到不存在/已下线的 id）；
- 有 key：条目注册 + FAST/STANDARD 链第 3 位 = xiaomi hop（原位次）+ agent
  policy 候选可见（agent_profiles 三处 preferred_models 列 xiaomi_chat 的对齐面）；
- 无 key：条目不注册、显式选择回退 default（带「未注册」原因）、静态链虽含
  xiaomi 键但被消费面注册过滤跳过（候选链/策略选择均不可见）——PROD-FIX-4
  的「必炸 hop」防线语义保持。
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier
from app.core.llm_router import LLMRouter, llm_router

XIAOMI_CHAT_KEY = "xiaomi_chat"
XIAOMI_STANDARD_KEY = "xiaomi_standard_thinking"
XIAOMI_CURRENT_MODEL_ID = "mimo-v2.6-flash"  # 官方现行 id（考证见文件头）


def _rebuild_router(xiaomi_key: str = ""):
    """以指定小米 key 重建路由器（模拟引擎进程启动时的 settings 快照）。"""
    with patch.object(settings, "XIAOMI_MIMO_API_KEY", xiaomi_key):
        return LLMRouter()


@pytest.fixture(autouse=True)
def _deterministic_env(monkeypatch):
    """环境无关化：清空 .env 注入的 *_API_KEY 与 LLM_TIER_* override."""
    field_names = set(getattr(settings, "model_fields", None) or getattr(settings, "__fields__", {}))
    for k in field_names:
        if k.endswith("_API_KEY") or k.startswith("LLM_TIER_"):
            monkeypatch.setattr(settings, k, "")


@pytest.fixture(autouse=True)
def _restore_global_router():
    """恢复全局单例快照，防 key-gated 重建污染同进程后续测试。"""
    saved = dict(llm_router.__dict__)
    yield
    llm_router.__dict__.clear()
    llm_router.__dict__.update(saved)


# =============================================================================
# 1) 注册面（PROD-FIX-4 原契约，保持）
# =============================================================================


def test_xiaomi_entries_not_registered_without_key():
    """无 key 环境：小米条目不注册。"""
    router = _rebuild_router(xiaomi_key="")
    assert XIAOMI_CHAT_KEY not in router._available_models
    assert XIAOMI_STANDARD_KEY not in router._available_models


def test_xiaomi_entries_registered_with_key():
    """有 key 环境：条目照常注册（credential_routing 契约保持）。"""
    router = _rebuild_router(xiaomi_key="test-xiaomi-key")
    assert XIAOMI_CHAT_KEY in router._available_models
    assert XIAOMI_STANDARD_KEY in router._available_models


def test_registered_model_names_are_current_official_ids():
    """模型名契约：注册条目必须挂官方现行 id mimo-v2.6-flash（防再漂移）。

    已下线 id 清单实证：mimo-v2-flash（2026-06-30 下线）；mimo-v2.5/
    mimo-v2.5-pro（2026-10-21 10:00 下线）——三者都不得再出现在小米车道。
    """
    router = _rebuild_router(xiaomi_key="test-xiaomi-key")
    deprecated_ids = {"mimo-v2-flash", "mimo-v2.5", "mimo-v2.5-pro"}
    for key in (XIAOMI_CHAT_KEY, XIAOMI_STANDARD_KEY):
        cfg = router._available_models[key]
        assert cfg.model_name == XIAOMI_CURRENT_MODEL_ID
        assert cfg.model_name not in deprecated_ids
    # settings 默认值与注册面一致（.env 未覆盖时）
    assert settings.XIAOMI_CHAT_MODEL == XIAOMI_CURRENT_MODEL_ID
    assert settings.XIAOMI_STANDARD_MODEL == XIAOMI_CURRENT_MODEL_ID


# =============================================================================
# 2) 默认链回挂（XIAOMI-MODEL 新契约：原位次回挂）
# =============================================================================


def test_xiaomi_hops_rehooked_at_original_third_position():
    """有 key：FAST/STANDARD 链第 3 位 = xiaomi hop（PROD-FIX-4 摘除前原位次）。"""
    router = _rebuild_router(xiaomi_key="test-xiaomi-key")
    fast_chain = router._tier_mapping[ModelTier.FAST]
    standard_chain = router._tier_mapping[ModelTier.STANDARD]
    assert fast_chain[2] == XIAOMI_CHAT_KEY
    assert standard_chain[2] == XIAOMI_STANDARD_KEY


def test_unkeyed_chain_hop_is_filtered_from_resolved_candidates():
    """无 key：静态链虽含 xiaomi 键，但解析候选链必须被注册过滤跳过。

    钉的是 PROD-FIX-4 防线语义的等价物：死/未注册 hop 不进入任何实际
    降级序列（_append 的 ``model_key not in _available_models`` 过滤）。
    """
    router = _rebuild_router(xiaomi_key="")
    candidates = router.resolve_candidate_models(AgentRole.GENERATION, force_tier=ModelTier.FAST)
    assert XIAOMI_CHAT_KEY not in candidates
    candidates_std = router.resolve_candidate_models(AgentRole.GENERATION, force_tier=ModelTier.STANDARD)
    assert XIAOMI_STANDARD_KEY not in candidates_std


def test_keyed_policy_candidates_surface_xiaomi_chat():
    """有 key：agent policy（RETRIEVAL preferred_models 尾位 xiaomi_chat）候选可见。

    对齐 agent_profiles 三处（:243/:521/:612）preferred_models 列 xiaomi_chat
    的既有面——回挂后它们在活栈（key 已配）重新成为合法候选。
    """
    router = _rebuild_router(xiaomi_key="test-xiaomi-key")
    candidates = router.resolve_candidate_models(AgentRole.RETRIEVAL)
    assert XIAOMI_CHAT_KEY in candidates
    router_unkeyed = _rebuild_router(xiaomi_key="")
    assert XIAOMI_CHAT_KEY not in router_unkeyed.resolve_candidate_models(AgentRole.RETRIEVAL)


# =============================================================================
# 3) 显式选择与位次守护（PROD-FIX-4 原契约，保持/收严）
# =============================================================================


def test_explicit_selection_of_unregistered_xiaomi_falls_back_cleanly():
    """无 key 时显式指定 xiaomi_chat：回退 default 并声明未注册（不炸、不误标）。"""
    router = _rebuild_router(xiaomi_key="")
    selection = router.select_specific_model(XIAOMI_CHAT_KEY, agent_role=AgentRole.ROUTER)
    assert selection.model_key != XIAOMI_CHAT_KEY
    assert "未注册" in selection.reason


def test_keyed_router_keeps_other_fast_chain_order_untouched():
    """回挂只恢复小米原位：FAST 首位（Qwen 主力）与其余位次零变化.

    STANDARD 链经 LLM_PROVIDER=qwen 偏好把 dashscope_standard_thinking 置首
    （既有行为），小米 hop 仍居第 3 位（原位次）。
    """
    router = _rebuild_router(xiaomi_key="test-xiaomi-key")
    fast_chain = router._tier_mapping[ModelTier.FAST]
    assert fast_chain[0] == "dashscope_fast"
    assert fast_chain[1] == "deepseek_fast"
    assert fast_chain[3] == "glm_4_7_flash_no_thinking"
    assert len(fast_chain) == 4
    standard_chain = router._tier_mapping[ModelTier.STANDARD]
    assert standard_chain == ["dashscope_standard_thinking", "deepseek_chat", XIAOMI_STANDARD_KEY]
