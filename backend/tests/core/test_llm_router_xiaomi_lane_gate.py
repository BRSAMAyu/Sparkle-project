"""PROD-LOG2 ②-3（PROD-FIX-4）契约测试：小米 mimo 死车道代码侧门控.

缺陷：settings 默认 ``XIAOMI_*_MODEL="mimo-v2-flash"`` 被小米端点本身拒绝
（404 Unsupported model，生产 3 站×2 条），而 ``xiaomi_chat`` 挂在 FAST 降级链
第 3 位、``xiaomi_standard_thinking`` 挂在 STANDARD 链第 3 位——每次降级到它必
白打一跳（网络延迟+ERROR+熔断计数）。且无 key 环境（测试/CI）这些条目照样
注册（api_key=""），链上候选人人都带一个必炸 hop。

裁决（两层叠加，B-MODEL-SWITCH 开关注册先例）：
1. key-gate 注册：XIAOMI_MIMO_API_KEY 非空才注册 xiaomi_chat/xiaomi_standard_
   thinking（mimo_pro 走独立 token-plan key/端点，无故障证据，不动）；
2. 死模型名摘出自动降级链：404 是模型名被端点拒绝、与 key 是否有效无关
   （活栈 .env key 已配置仍 404），自动链不得包含确定性失败的 hop；
   小米更正模型名后一行即可回挂（llm_router fast_models/standard_models）。

钉住的契约：
- 无 key：条目不注册、显式选择回退 default（带「未注册」原因）、链无此 hop；
- 有 key：条目注册（credential_routing 契约不受影响），但默认 FAST/STANDARD
  链仍不含 xiaomi（模型名死）。
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier
from app.core.llm_router import LLMRouter, llm_router

XIAOMI_CHAT_KEY = "xiaomi_chat"
XIAOMI_STANDARD_KEY = "xiaomi_standard_thinking"


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


def test_xiaomi_entries_not_registered_without_key():
    """无 key 环境：小米条目不注册（基线行为：空 key 也注册=必炸 hop）。"""
    router = _rebuild_router(xiaomi_key="")
    assert XIAOMI_CHAT_KEY not in router._available_models
    assert XIAOMI_STANDARD_KEY not in router._available_models


def test_xiaomi_entries_registered_with_key():
    """有 key 环境：条目照常注册（credential_routing 契约保持）。"""
    router = _rebuild_router(xiaomi_key="test-xiaomi-key")
    assert XIAOMI_CHAT_KEY in router._available_models
    assert XIAOMI_STANDARD_KEY in router._available_models


def test_dead_mimo_hop_removed_from_default_fast_and_standard_chains():
    """FAST/STANDARD 默认降级链不得包含小米 hop（模型名被端点拒绝，与 key 无关）。"""
    router = _rebuild_router(xiaomi_key="test-xiaomi-key")
    assert XIAOMI_CHAT_KEY not in router._tier_mapping.get(ModelTier.FAST, [])
    assert XIAOMI_STANDARD_KEY not in router._tier_mapping.get(ModelTier.STANDARD, [])


def test_explicit_selection_of_unregistered_xiaomi_falls_back_cleanly():
    """无 key 时显式指定 xiaomi_chat：回退 default 并声明未注册（不炸、不误标）。"""
    router = _rebuild_router(xiaomi_key="")
    selection = router.select_specific_model(XIAOMI_CHAT_KEY, agent_role=AgentRole.ROUTER)
    assert selection.model_key != XIAOMI_CHAT_KEY
    assert "未注册" in selection.reason


def test_keyed_router_keeps_other_fast_chain_order_untouched():
    """门控只动小米：FAST 链首位（Qwen 主力）与其余位次零变化."""
    router = _rebuild_router(xiaomi_key="test-xiaomi-key")
    fast_chain = router._tier_mapping[ModelTier.FAST]
    assert fast_chain[0] == "dashscope_fast"
    assert "deepseek_fast" in fast_chain
    assert "glm_4_7_flash_no_thinking" in fast_chain
