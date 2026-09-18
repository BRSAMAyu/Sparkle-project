"""
推送文案生成解析链（F-2）单元测试。

红绿契约：
- LLM 返回带 markdown fence 的 JSON → 稳健解析成功，单次调用即返回，无降级
- LLM 返回散文包裹/空串/纯文本 → 以"只输出 JSON"修正提示重试一次 → 成功或降级
- 两次均失败 → 保留静态降级文案，但必须留下遥测：
  sparkle_llm_push_content_parse_failure_total{stage="initial"|"retry"} 自增 + error 日志
- LLMSecurityWrapper 监控记账不再因 LLMMonitor 属性名漂移（LLM_CALLS_TOTAL 等
  为模块级指标）而整体静默失效
"""
from __future__ import annotations

import json

import pytest
from prometheus_client import REGISTRY

from app.core.llm_security_wrapper import LLMSecurityWrapper, SecurityConfig
from app.services.llm_service import LLMService, _extract_json_payload

PARSE_FAILURE_METRIC = "sparkle_llm_push_content_parse_failure_total"


def _stage_count(stage: str) -> float:
    value = REGISTRY.get_sample_value(PARSE_FAILURE_METRIC, {"stage": stage})
    return value or 0.0


def _make_service() -> LLMService:
    return LLMService(agent_role="generation", enable_dynamic_routing=True)


# ---------------------------------------------------------------------------
# _extract_json_payload：fence / 散文包裹 / 空串
# ---------------------------------------------------------------------------


def test_extract_json_from_markdown_fence():
    raw = '```json\n{"title": "该复习啦", "body": "考研冲刺计划已就绪"}\n```'
    payload = _extract_json_payload(raw)
    assert payload is not None
    assert json.loads(payload)["title"] == "该复习啦"


def test_extract_json_from_prose_wrapped_output():
    raw = '好的，这是你的推送文案：\n{"title": "冲刺提醒", "body": "还有 40 天，加油！"}\n祝学习顺利。'
    payload = _extract_json_payload(raw)
    assert payload is not None
    assert json.loads(payload)["body"] == "还有 40 天，加油！"


def test_extract_json_handles_braces_inside_strings_and_empty_input():
    raw = '{"title": "复习 {冲} 刺", "body": "quote \\" ok"}'
    assert json.loads(_extract_json_payload(raw))["title"] == "复习 {冲} 刺"
    assert _extract_json_payload("") is None
    assert _extract_json_payload("   \n  ") is None
    assert _extract_json_payload("抱歉，我无法完成该请求。") is None


# ---------------------------------------------------------------------------
# generate_push_content：解析 → 重试 → 降级 + 指标
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fenced_json_output_parses_on_first_call():
    svc = _make_service()
    calls: list[list[dict]] = []

    async def fake_chat(messages, **kwargs):
        calls.append(messages)
        return '```json\n{"title": "40天冲刺", "body": "你的考研计划已生成，今天从极限开始。"}\n```'

    svc.chat = fake_chat  # type: ignore[method-assign]

    result = await svc.generate_push_content(
        user_nickname="小燃", persona="coach", trigger_type="sprint",
        context_data={"plan_name": "考研40天冲刺"},
    )
    assert result == {"title": "40天冲刺", "body": "你的考研计划已生成，今天从极限开始。"}
    assert len(calls) == 1  # 单次调用即解析成功，无重试


@pytest.mark.asyncio
async def test_plain_text_retries_once_with_correction_hint_then_succeeds():
    svc = _make_service()
    seen_user_prompts: list[str] = []

    async def fake_chat(messages, **kwargs):
        seen_user_prompts.append(str(messages[-1]["content"]))
        if len(seen_user_prompts) == 1:
            return "抱歉，我需要更多信息才能生成推送内容。"  # 纯文本，无 JSON
        return json.dumps({"title": "复习提醒", "body": "记忆节点临近衰减，现在巩固正当时。"})

    svc.chat = fake_chat  # type: ignore[method-assign]

    result = await svc.generate_push_content(
        user_nickname="小燃", persona="mentor", trigger_type="memory",
        context_data={"nodes": ["泰勒展开"]},
    )
    assert result["title"] == "复习提醒"
    assert len(seen_user_prompts) == 2  # 恰好重试一次
    assert "只输出一个 JSON 对象" in seen_user_prompts[1]  # 重试带修正提示


@pytest.mark.asyncio
async def test_double_failure_keeps_fallback_but_records_metrics_and_logs():
    svc = _make_service()

    async def fake_chat(messages, **kwargs):
        return "这是一段完全不含 JSON 的解释性文本。"

    svc.chat = fake_chat  # type: ignore[method-assign]

    initial_before = _stage_count("initial")
    retry_before = _stage_count("retry")

    result = await svc.generate_push_content(
        user_nickname="小燃", persona="coach", trigger_type="inactivity",
        context_data={},
    )
    assert result == {"title": "学习提醒", "body": "小燃，该复习了。"}  # 降级保留
    assert _stage_count("initial") == pytest.approx(initial_before + 1)
    assert _stage_count("retry") == pytest.approx(retry_before + 1)


@pytest.mark.asyncio
async def test_empty_output_retries_once_and_fenced_retry_wins():
    """空串（评测中 'Expecting value: line 1 column 1' 的典型来源）也触发重试。"""
    svc = _make_service()
    responses = ["", '```JSON\n{"title": "回来学习", "body": "超过24小时没打卡了，星星等你。"}\n```']

    async def fake_chat(messages, **kwargs):
        return responses.pop(0)

    svc.chat = fake_chat  # type: ignore[method-assign]

    result = await svc.generate_push_content(
        user_nickname="小燃", persona="friend", trigger_type="inactivity",
        context_data={},
    )
    assert result == {"title": "回来学习", "body": "超过24小时没打卡了，星星等你。"}
    assert not responses  # 恰好消耗两次调用


# ---------------------------------------------------------------------------
# LLMMonitor 属性名漂移修复
# ---------------------------------------------------------------------------


def test_security_wrapper_monitor_recording_no_longer_noop():
    """修复前：self.monitor.LLM_CALLS_TOTAL 触发 AttributeError 被 except 吞掉，
    llm_calls_total 样本永不增长。修复后必须真实记账。"""
    wrapper = LLMSecurityWrapper(
        llm_service=object(),
        redis_client=None,
        config=SecurityConfig(enable_quota_check=False, enable_monitoring=True),
    )
    assert wrapper.monitor is not None

    model = "drift-check-model"
    status = "success"
    endpoint = "drift_probe"
    labels = {"model": model, "status": status, "endpoint": endpoint}
    before = REGISTRY.get_sample_value("llm_calls_total", labels) or 0.0

    wrapper._record_call_metrics(
        endpoint=endpoint, model=model, status=status,
        latency_seconds=0.01, input_text="hello", output_text="world",
    )

    after = REGISTRY.get_sample_value("llm_calls_total", labels) or 0.0
    assert after == pytest.approx(before + 1)

    failure_labels = {"task_type": endpoint, "error_type": "ValueError"}
    before_fail = REGISTRY.get_sample_value("llm_task_failures_total", failure_labels) or 0.0
    wrapper._record_call_failure(endpoint=endpoint, model=model, exc=ValueError("boom"))
    after_fail = REGISTRY.get_sample_value("llm_task_failures_total", failure_labels) or 0.0
    assert after_fail == pytest.approx(before_fail + 1)
