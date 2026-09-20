"""演示缺陷 ❌#6 · 生成后审查链的 done 前延迟治理（A1/A2）契约测试.

背景（docs/competition/大创市赛/演示路径盘点_2026-09-20.md §❌#6）：
末 delta 之后、done 之前，图内同步执行 generation_review → reflection：
- 审查 LLM 不可用时 review 烧满 45s 超时 → fail-closed（requires_reflection）
  → reflection 对同一不可用 LLM 栈再烧多轮 45s+ → done 尾延迟 120-145s。

A1：review_error（reviewer 基础设施故障）不再触发 reflection——正文已流出、
    reflection 必然再次失败，纯属延迟；
A2：新增 settings.ENABLE_GENERATION_REVIEW 部署开关，可整体跳过生成后审查。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agents.graph.nodes import review_nodes
from app.agents.reviewer_agent import Issue, QuantifiedMetric, ReviewMetric, ReviewResult
from app.config import settings


def _error_review_result(*, review_error: bool) -> ReviewResult:
    """fail-closed 的 ReviewResult（与 ReviewerAgent 异常路径产物同构）。"""
    return ReviewResult(
        review_id="rev_test",
        target_type="response",
        target_id="rev_test",
        decision="failed",
        overall_score=0.0,
        metrics=[QuantifiedMetric(ReviewMetric.SAFETY, 0.0)],
        issues=[
            Issue(
                category="system" if review_error else "accuracy",
                severity="critical",
                location="reviewer_agent" if review_error else "content",
                description="x",
                affected_content="",
                suggested_fix="y",
                confidence=1.0,
            )
        ],
        improvement_suggestions=[],
        requires_reflection=True,
        reviewer_model="qwen3.8-flash",
        review_timestamp="",
        review_error=review_error,
    )


def _state() -> SimpleNamespace:
    return SimpleNamespace(
        context_data={},
        messages=[
            {"role": "user", "content": "讲解一下梯度下降"},
            {"role": "assistant", "content": "梯度下降是一种一阶优化算法" * 20},
        ],
        next_step="generation_review",
    )


def _install_reviewer(monkeypatch: pytest.MonkeyPatch, result: ReviewResult) -> None:
    class _StubReviewer:
        model_key = "stub"
        provider_name = "stub"

        async def review_llm_response(self, **kwargs):
            return result

    monkeypatch.setattr(review_nodes, "_get_reviewer", lambda *a, **kw: _StubReviewer())


@pytest.mark.asyncio
async def test_review_error_skips_reflection(monkeypatch: pytest.MonkeyPatch):
    """A1：reviewer 基础设施故障 → 不进 reflection，直接收尾."""
    _install_reviewer(monkeypatch, _error_review_result(review_error=True))
    result = await review_nodes.generation_review_node(_state())
    assert result["next_step"] == "__end__"
    assert result["review_context"]["status"] != review_nodes.ReviewStatus.REFLECTING


@pytest.mark.asyncio
async def test_genuine_quality_failure_still_enters_reflection(monkeypatch: pytest.MonkeyPatch):
    """真实内容质量失败（reviewer 正常工作）→ reflection 语义保持不变."""
    _install_reviewer(monkeypatch, _error_review_result(review_error=False))
    result = await review_nodes.generation_review_node(_state())
    assert result["next_step"] == "reflection"
    assert result["review_context"]["status"] == review_nodes.ReviewStatus.REFLECTING


def test_settings_gate_disables_generation_review(monkeypatch: pytest.MonkeyPatch):
    """A2：ENABLE_GENERATION_REVIEW=False 时整体跳过生成后审查."""
    state = _state()
    monkeypatch.setattr(settings, "ENABLE_GENERATION_REVIEW", True, raising=False)
    assert review_nodes._should_skip_review(state) is False

    monkeypatch.setattr(settings, "ENABLE_GENERATION_REVIEW", False, raising=False)
    assert review_nodes._should_skip_review(state) is True


def test_settings_gate_defaults_to_enabled():
    """默认开启审查——不带开关的部署行为不回退."""
    assert settings.ENABLE_GENERATION_REVIEW is True
