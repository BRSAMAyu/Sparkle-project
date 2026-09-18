"""审查系统错误（review_error）不向用户流追加"内容审查未通过"文案。

背景（V2.5 deep_analysis qwen3.8-flash 复验实证）：
reviewer 预算 REVIEWER_LLM_TIMEOUT_SECONDS=12s，而 qwen3.8-flash 思考模式
真实审查耗时 ~67s（非流式）→ 每轮 deep_analysis 审查恒超时 fail-closed，
且用户可见文本被追加 "[内容审查: 未通过] 发现 1 个严重问题需要处理"——
审查从未真实执行，却向用户宣称内容未通过审查。

修复语义：review_error=True 仍 fail-closed（reflection 触发、决策 failed），
但用户可见 delta 由 _should_emit_review_failure_delta 抑制。
"""
from __future__ import annotations

import asyncio

import pytest

from app.agents.graph.nodes.review_nodes import _should_emit_review_failure_delta
from app.agents.reviewer_agent import Issue, QuantifiedMetric, ReviewMetric, ReviewResult


def _make_result(review_error: bool = False, decision: str = "failed") -> ReviewResult:
    return ReviewResult(
        review_id="rev_test",
        target_type="response",
        target_id="rev_test",
        decision=decision,
        overall_score=0.0 if decision == "failed" else 0.9,
        metrics=[QuantifiedMetric(ReviewMetric.SAFETY, 0.0 if decision == "failed" else 1.0)],
        issues=[
            Issue(
                category="system" if review_error else "accuracy",
                severity="critical" if decision == "failed" else "info",
                location="reviewer_agent" if review_error else "content",
                description="x",
                affected_content="",
                suggested_fix="y",
                confidence=1.0,
            )
        ],
        improvement_suggestions=[],
        requires_reflection=decision == "failed",
        reviewer_model="qwen3.8-flash",
        review_timestamp="",
        review_error=review_error,
    )


def test_review_error_result_is_not_emitted_to_user_stream() -> None:
    assert _should_emit_review_failure_delta(_make_result(review_error=True)) is False


def test_genuine_failed_review_is_still_emitted_to_user_stream() -> None:
    assert _should_emit_review_failure_delta(_make_result(review_error=False)) is True


def test_passed_review_is_not_emitted() -> None:
    assert _should_emit_review_failure_delta(_make_result(review_error=False, decision="passed")) is False


def test_review_result_roundtrip_preserves_review_error() -> None:
    data = _make_result(review_error=True).to_dict()
    assert data["review_error"] is True
    restored = ReviewResult.from_dict(data)
    assert restored.review_error is True


class _ExplodingLLM:
    """chat_json 直接抛错，模拟审查系统超时/异常。"""

    model_key = "dashscope_reason"
    provider_name = "dashscope"
    default_model = "qwen3.8-flash"

    async def chat_json(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise TimeoutError()


def test_reviewer_exception_path_flags_review_error() -> None:
    from app.agents.reviewer_agent import ReviewerAgent

    agent = ReviewerAgent(reviewer_llm=_ExplodingLLM())
    result = asyncio.run(agent.review_llm_response("用户问题", "回答内容"))
    assert result.decision == "failed"  # fail-closed 保持
    assert result.requires_reflection is True
    assert result.review_error is True


def test_reviewer_exception_result_is_suppressed_from_user_stream() -> None:
    from app.agents.reviewer_agent import ReviewerAgent

    agent = ReviewerAgent(reviewer_llm=_ExplodingLLM())
    result = asyncio.run(agent.review_llm_response("用户问题", "回答内容"))
    assert _should_emit_review_failure_delta(result) is False


def test_reviewer_timeout_uses_budget_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.agents.reviewer_agent import ReviewerAgent
    from app.config import settings

    monkeypatch.setattr(settings, "REVIEWER_LLM_TIMEOUT_SECONDS", 7, raising=False)
    agent = ReviewerAgent(reviewer_llm=_ExplodingLLM())
    assert agent.llm_timeout_seconds == 7.0
