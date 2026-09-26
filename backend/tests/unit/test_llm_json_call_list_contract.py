"""V3-FIX-238：json_call 契约收窄 vs safe_llm_json_call 可返 list。

底层 ``safe_llm_json_call`` 对 LLM 输出的 JSON array 合法返回 list（
test_learning_path_task_fallback.py 已实证），但 ``LLMFallbackWrapper.json_call``
谎称只返 ``dict | None``。类型谎言在消费面落地为两类真实故障：

- 真 list 消费面（plan_tools 计划生成 / focus_service 专注拆解 / theater 风险
  分级）prompt 明确要求 JSON array，运行时靠 ``isinstance(result, list)``
  工作——与声明类型矛盾；
- dict-only 消费面（意图路由 / 充分性检查 / omnibar / 学习报告等）拿到
  non-empty list 时 ``.get`` 直接 AttributeError：或崩溃、或被外层
  except 吞成静默降级（_llm_classify → routing_layer="llm_fallback"）。

修复裁决：json_call 契约诚实化为宽型 ``dict | list | None``（与底层对齐；
收窄会让三个要求 array 的消费面永远拿 fallback，属行为回归，禁止），
新增 ``json_as_dict`` / ``json_as_list`` 收窄助手，dict-only 调用方逐个补
isinstance 防御（崩溃路径 → 优雅降级）。LLM 调用行为零改动。

本文件测试在修复前红（调用方 AttributeError / 静默降级、助手不存在），
修复后全绿。
"""

from __future__ import annotations

from typing import Any

import pytest

from app.services.llm_fallback_utils import LLMFallbackWrapper

# =============================================================================
# 底层契约实录：json_call 对 LLM array 输出真实返回 list（诚实宽型）
# =============================================================================


def _stub_llm_chat(payload: str):
    async def _fake_chat(messages: list[dict[str, str]], **kwargs: Any) -> str:
        return payload

    return _fake_chat


@pytest.mark.asyncio
async def test_json_call_returns_llm_array_as_list(monkeypatch):
    """LLM 返回 JSON array 时 json_call 真实返回 list（非 dict）——契约实录。"""
    monkeypatch.setattr(
        "app.services.llm_fallback_utils.llm_service.chat",
        _stub_llm_chat('```json\n["low", "high", "medium"]\n```'),
    )
    wrapper = LLMFallbackWrapper(service_name="Test", default_json_fallback=[])
    result = await wrapper.json_call(
        [{"role": "user", "content": "rate risk"}],
        fallback=[],
    )
    assert isinstance(result, list)
    assert result == ["low", "high", "medium"]


@pytest.mark.asyncio
async def test_json_call_returns_llm_object_as_dict(monkeypatch):
    """对照面：LLM 返回 JSON object 时 json_call 返回 dict——原行为不变。"""
    monkeypatch.setattr(
        "app.services.llm_fallback_utils.llm_service.chat",
        _stub_llm_chat('{"specific": false}'),
    )
    wrapper = LLMFallbackWrapper(service_name="Test", default_json_fallback={"specific": True})
    result = await wrapper.json_call(
        [{"role": "user", "content": "check"}],
        fallback={"specific": True},
    )
    assert isinstance(result, dict)
    assert result["specific"] is False


# =============================================================================
# 收窄助手：消费面一行拿到目标形态（修复前不存在 → ImportError 红）
# =============================================================================


def test_json_as_dict_narrows_list_and_none_to_none():
    from app.services.llm_fallback_utils import json_as_dict

    assert json_as_dict({"a": 1}) == {"a": 1}
    assert json_as_dict(["a", 1]) is None
    assert json_as_dict(None) is None


def test_json_as_list_narrows_dict_and_none_to_none():
    from app.services.llm_fallback_utils import json_as_list

    assert json_as_list([1, 2]) == [1, 2]
    assert json_as_list({"a": 1}) is None
    assert json_as_list(None) is None


# =============================================================================
# 调用方防御实录：list 返回路径曾是 AttributeError / 静默降级（修复前红）
# =============================================================================


@pytest.mark.asyncio
async def test_sufficiency_checker_survives_list_response(monkeypatch):
    """充分性检查拿到 non-empty list 曾直接 AttributeError 崩溃；修复后优雅降级 True。"""
    from app.orchestration import sufficiency_checker as sc_module

    async def _no_fast_lane() -> None:
        return None

    monkeypatch.setattr(
        "app.services.llm_fallback_utils.llm_service.chat",
        _stub_llm_chat('["specific", true]'),
    )
    monkeypatch.setattr(sc_module, "_get_fast_lane_service", _no_fast_lane)
    checker = sc_module.SufficiencyChecker()
    assert await checker._llm_refinement("task", "帮我把数学错题订正一下") is True


@pytest.mark.asyncio
async def test_intent_router_list_response_no_longer_silent_degrades(monkeypatch):
    """意图路由拿到 list 曾被 except 吞成静默降级（routing_layer=llm_fallback）；
    修复后按 chat fallback dict 正常出 LLM 层结果。"""
    from app.core.unified_intent_router import IntentRoutingResult, UnifiedIntentRouter, UnifiedIntentType

    class _TruthyLLM:
        """仅用于让 router.self.llm_service 为真；真实调用走全局 llm_service 桩。"""

    monkeypatch.setattr(
        "app.services.llm_fallback_utils.llm_service.chat",
        _stub_llm_chat('["chat"]'),
    )
    router = UnifiedIntentRouter(redis_client=None, llm_service=_TruthyLLM())
    rule_hints = IntentRoutingResult(
        primary_intent=UnifiedIntentType.CHAT,
        confidence=0.4,
        routing_layer="rule",
        execution_mode="direct",
    )
    result = await router._llm_classify("你好呀", [], rule_hints)
    assert result.routing_layer == "llm"
    assert result.primary_intent == UnifiedIntentType.CHAT


@pytest.mark.asyncio
async def test_omnibar_classify_survives_list_response(monkeypatch):
    """omnibar 意图分类拿到 non-empty list 曾 AttributeError；修复后降级 CHAT。"""
    from app.services.omnibar_service import OmniBarService

    monkeypatch.setattr(
        "app.services.llm_fallback_utils.llm_service.chat",
        _stub_llm_chat('["TASK"]'),
    )
    service = OmniBarService(db=None)
    # 文案不含任务前缀/关键词（提醒/任务/待办/复习/学习…），走 LLM 分类路径
    result = await service._classify_intent("今天随便看看书挺好的")
    assert result["type"] == "CHAT"


@pytest.mark.asyncio
async def test_report_agent_compose_markdown_survives_list_response(monkeypatch):
    """学习报告 _compose_markdown 拿到 non-empty list 曾 ``(data or {}).get`` 崩溃；
    修复后回退纯本地 markdown。"""
    from app.services.report.learning_report_agent import LearningReportAgent

    monkeypatch.setattr(
        "app.services.llm_fallback_utils.llm_service.chat",
        _stub_llm_chat('["markdown"]'),
    )
    agent = LearningReportAgent(db=None)
    result = await agent._compose_markdown(
        sections=["总结速览"],
        mastery=[{"node_name": "牛顿第二定律", "mastery_score": 0.3}],
        patterns=[{"pattern_name": "畏难回避", "solution_text": "先做 5 分钟"}],
        timeline=[{"node_name": "牛顿第二定律", "mastery_delta": -0.1}],
        learner_voice={"learner_voice": "卡在力学"},
    )
    assert isinstance(result, str)
    assert result  # 回退到本地 fallback markdown，非空
