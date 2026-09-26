"""V3-FIX-242：LLMFallbackWrapper json 链显式 falsy fallback 哨兵判空契约。

背景（台账 v3/06_agent_fleet/DYNAMIC_ISSUES.md V3-FIX-242，wt518 登记）：
- 旧实现两跳 ``or`` 真值链：构造侧 ``default_json_fallback or {}`` 把 plan_llm
  显式声明的 ``[]`` 收敛成 ``{}``；json_call 侧 ``fallback or self.default_json_fallback``
  再把调用方显式传入的 falsy fallback（``[]``/``{}``）静默换成单例默认——
  「调用方声明的降级值」与「实际生效降值」系统性错位。
- 修后语义：``is None`` 哨兵判空——仅当未提供（None）时才落默认；显式 falsy
  （``[]``/``{}``）原样保留。未提供 fallback 时仍取 default_json_fallback（防过修）。

可证伪判据（台账原文）：``LLMFallbackWrapper(default_json_fallback=[]).json_call(
msgs, fallback=[])`` 在 llm 失败时旧实现返回 ``{}`` 而非 ``[]``（确定性桩测）。

行为差异面裁决（wt518 盘点 + wt525 复盘，见台账 FIXED 行）：现网 json_call 28 面
消费中显式 falsy fallback 仅 plan_tools:660 与 focus_service:592 两处，两处下游
（``if not result`` / ``isinstance(result, list)``）今日终态行为均无差；本修属语义
诚实化，非行为变更。字符串侧 ``call``/``chat`` 的 ``fallback or default_fallback``
同型链不在本卡范围（另登记 V3-FIX-249）。
"""

from __future__ import annotations

from typing import Any

import pytest

from app.services.llm_fallback_utils import LLMFallbackWrapper, plan_llm

_MSGS = [{"role": "user", "content": "return json"}]


class _FailingService:
    """确定性失败桩：模拟 LLM 全尝试失败，逼出降级路径。"""

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        raise RuntimeError("llm-down-for-test")


_FAILING = _FailingService()


@pytest.mark.asyncio
async def test_explicit_list_fallback_preserved_on_llm_failure():
    """台账可证伪判据：显式 fallback=[] 失败路径必须返回 []，不得换成默认。"""
    wrapper = LLMFallbackWrapper(service_name="T", default_json_fallback=[])
    result = await wrapper.json_call(_MSGS, fallback=[], service=_FAILING)
    assert result == [], f"显式 [] fallback 被静默换成 {result!r}"


@pytest.mark.asyncio
async def test_explicit_empty_dict_fallback_preserved_on_llm_failure():
    """显式 fallback={} 是 falsy 但已提供——必须原样返回，不得换单例默认。"""
    wrapper = LLMFallbackWrapper(service_name="T", default_json_fallback={"type": "CHAT"})
    result = await wrapper.json_call(_MSGS, fallback={}, service=_FAILING)
    assert result == {}, f"显式 {{}} fallback 被静默换成 {result!r}"


def test_constructor_preserves_explicit_empty_list_default():
    """构造侧第一跳：default_json_fallback=[] 不得被 ``or {}`` 收敛成 {}。

    现网实证：plan_llm 声明 ``default_json_fallback=[]``（计划生成降级返回空列表），
    旧实现构造后实际是 {}。
    """
    wrapper = LLMFallbackWrapper(service_name="T", default_json_fallback=[])
    assert wrapper.default_json_fallback == []


def test_plan_llm_singleton_declares_empty_list_default():
    """生产单例 plan_llm 的降级值必须与声明一致（[] 而非被收敛的 {}）。"""
    assert plan_llm.default_json_fallback == []


@pytest.mark.asyncio
async def test_fallback_not_provided_still_uses_default():
    """防过修：未提供 fallback（None）时仍落 default_json_fallback。"""
    wrapper = LLMFallbackWrapper(service_name="T", default_json_fallback={"specific": True})
    result = await wrapper.json_call(_MSGS, service=_FAILING)
    assert result == {"specific": True}


@pytest.mark.asyncio
async def test_wrapper_without_default_json_fallback_still_defaults_to_empty_dict():
    """未声明 default_json_fallback 的单例（如 stt_llm 形态）默认仍是 {}。"""
    wrapper = LLMFallbackWrapper(service_name="T")
    result = await wrapper.json_call(_MSGS, service=_FAILING)
    assert result == {}


@pytest.mark.asyncio
async def test_explicit_fallback_wins_over_wrapper_default_on_parse_failure():
    """JSON 解析失败路径同样走哨兵判空：显式 fallback 优先于单例默认。"""
    from app.services.llm_fallback_utils import safe_llm_json_call

    class _GarbageService:
        async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
            return "这不是 JSON"

    result = await safe_llm_json_call(_MSGS, fallback=[], service=_GarbageService())
    assert result == []
