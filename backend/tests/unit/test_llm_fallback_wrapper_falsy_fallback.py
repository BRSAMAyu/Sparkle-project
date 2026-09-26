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


# ---------------------------------------------------------------------------
# V3-FIX-249：字符串侧 call/chat 的 ``fallback or default_fallback`` 真值链——
# 与 242 的 json 侧同型面。修后语义：``is None`` 哨兵判空，显式 "" 原样生效。
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_explicit_empty_string_call_fallback_preserved_on_llm_failure():
    """台账同型判据（call 侧）：显式 fallback="" 失败路径必须返回 ""，不得换默认。"""
    wrapper = LLMFallbackWrapper(service_name="T", default_fallback="默认句")
    result = await wrapper.call(_MSGS, fallback="", service=_FAILING)
    assert result == "", f"显式空串 fallback 被静默换成 {result!r}"


@pytest.mark.asyncio
async def test_explicit_empty_string_chat_fallback_preserved_on_llm_failure():
    """台账可证伪判据（chat 侧）：``chat("p", fallback="")`` 失败必须返回 ""。

    旧实现 ``fallback or self.default_fallback`` 把显式 "" 真值收敛成单例默认句。
    """
    wrapper = LLMFallbackWrapper(service_name="T", default_fallback="默认句")
    result = await wrapper.chat("p", fallback="", service=_FAILING)
    assert result == "", f"显式空串 fallback 被静默换成 {result!r}"


@pytest.mark.asyncio
async def test_string_fallback_not_provided_still_uses_default():
    """防过修：字符串侧未提供 fallback（None）时仍落 default_fallback。"""
    wrapper = LLMFallbackWrapper(service_name="T", default_fallback="默认句")
    assert await wrapper.call(_MSGS, service=_FAILING) == "默认句"
    assert await wrapper.chat("p", service=_FAILING) == "默认句"


@pytest.mark.asyncio
async def test_vocabulary_word_associations_failure_returns_empty_list_not_fake_word(
    monkeypatch: pytest.MonkeyPatch,
):
    """现网实证面：vocabulary_service.get_word_associations LLM 失败 → []。

    旧实现实际返回 vocabulary_llm.default_fallback 整句「词典服务暂时不可用」，
    下游 ``response.split(',')`` 把整句当一个联想词返回 ``["词典服务暂时不可用"]``
    ——失败时向用户展示假词。修后钉死新语义：response="" → ``if not response``
    → 返回空联想列表。
    """
    from app.services import llm_fallback_utils
    from app.services.vocabulary_service import VocabularyService

    assert llm_fallback_utils.vocabulary_llm.default_fallback == "词典服务暂时不可用"
    monkeypatch.setattr(llm_fallback_utils, "llm_service", _FAILING)
    result = await VocabularyService.get_word_associations("serendipity")
    assert result == [], f"失败路径返回了假联想词 {result!r} 而非空列表"
    assert "词典服务暂时不可用" not in result
