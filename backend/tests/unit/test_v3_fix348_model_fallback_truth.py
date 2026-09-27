"""V3-FIX-348 · model_fallback 降级决策如实化契约测试.

背景（wt652 深查亲证，台账 V3-FIX-348）：
- 服务 docstring 宣称「触发模型切换」，chat 审查失败路径给用户流发
  「检测到质量问题，切换到更强大的模型重新生成...」delta——但决策产物
  （review_context.fallback_model / context_data.suggested_model）全仓
  零读取方，模型从不被切换。用户可见承诺与运行时行为直接矛盾。
- 裁决（wt655）：如实化（FIX-330/339 先例）——
  ① 用户 delta 按真实后续行为分路：reflection 路径=「正在尝试自动修正」
    （reflection 紧随其后真实发生）；critical 路径=「未通过质量审查」
    （回合直接收尾，无任何重新生成）；两路均不得宣称切换模型/重新生成。
  ② docstring 降级为「追踪/检测/建议」，切换宣称删除。
  ③ 死助手 _get_fallback_model 与死选择策略 get_model_for_task 族删除。
  ④ 检测/记录/建议链保留（真实宣称，测试钉死防误删）。
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import app.services.model_fallback_service as mfs
from app.agents.graph.nodes import review_nodes
from app.agents.reviewer_agent import Issue, QuantifiedMetric, ReviewMetric, ReviewResult

FALLBACK_MODEL = "deepseek_chat"
# MODEL_ALTERNATIVES["deepseek_chat"][0]（quality 偏好取首选替代）
SUGGESTED_MODEL = "dashscope_chat"

# 用户可见文案的诚实红线：降级链路中禁止出现的虚假承诺词
FORBIDDEN_PROMISES = ("切换到更强大", "重新生成")


@pytest.fixture
def fresh_fallback_service():
    """隔离进程内单例：测试内取全新实例，不动真实单例状态。"""
    old = mfs._fallback_service_instance
    mfs._fallback_service_instance = None
    yield
    mfs._fallback_service_instance = old


def _seed_consecutive_failures(count: int, model_name: str = FALLBACK_MODEL) -> None:
    service = mfs.get_model_fallback_service()
    for _ in range(count):
        service.record_performance(
            model_name=model_name,
            task_type="generation",
            review_passed=False,
            review_score=0.1,
            issues_count=3,
        )


class _DeltaCollector:
    def __init__(self) -> None:
        self.texts: list[str] = []

    async def __call__(self, response) -> None:  # noqa: ANN001
        self.texts.append(response.delta or "")


def _state(*, context_extra: dict | None = None) -> SimpleNamespace:
    context_data = {"model_used": FALLBACK_MODEL}
    if context_extra:
        context_data.update(context_extra)
    return SimpleNamespace(
        context_data=context_data,
        messages=[
            {"role": "user", "content": "讲解一下梯度下降"},
            {"role": "assistant", "content": "梯度下降是一种一阶优化算法" * 20},
        ],
        next_step="generation_review",
        db_session=object(),  # _get_fallback_service 需要 db_session 在场才激活
    )


def _critical_failed_review(*, requires_reflection: bool) -> ReviewResult:
    """审查失败产物（非基础设施错误，真实质量问题路径）。"""
    return ReviewResult(
        review_id="rev_348",
        target_type="response",
        target_id="rev_348",
        decision="failed",
        overall_score=0.2,
        metrics=[QuantifiedMetric(ReviewMetric.SAFETY, 0.2)],
        issues=[
            Issue(
                category="accuracy",
                severity="critical",
                location="content",
                description="事实错误",
                affected_content="",
                suggested_fix="更正",
                confidence=1.0,
            )
        ],
        improvement_suggestions=[],
        requires_reflection=requires_reflection,
        reviewer_model="qwen3.8-flash",
        review_timestamp="",
        review_error=False,
    )


def _assert_no_false_promise(texts: list[str]) -> None:
    for text in texts:
        for promise in FORBIDDEN_PROMISES:
            assert promise not in text, (
                f"降级链路用户文案含虚假承诺 {promise!r}: {text!r}"
            )


# ---------------------------------------------------------------
# ① 用户 delta 如实化（核心红线：不许诺不发生的切换/重新生成）
# ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_fallback_delta_never_promises_switch_or_regeneration(
    fresh_fallback_service,
) -> None:
    """should_fallback 命中时，用户 delta 不得宣称「切换模型/重新生成」."""
    _seed_consecutive_failures(3)
    collector = _DeltaCollector()
    state = _state(context_extra={"stream_callback": collector})

    suggested = await review_nodes._check_and_execute_fallback(
        state=state,
        current_model=FALLBACK_MODEL,
        review_score=0.1,
        review_passed=False,
    )

    # 建议仍产出（记录与建议是真实能力）
    assert suggested == SUGGESTED_MODEL
    assert collector.texts, "降级命中应给用户一条如实提示"
    _assert_no_false_promise(collector.texts)
    # 默认（未声明将重新生成）只告知质量审查未通过
    assert any("质量审查" in t for t in collector.texts)


@pytest.mark.asyncio
async def test_fallback_delta_reflection_path_announces_correction(
    fresh_fallback_service,
) -> None:
    """reflection 路径（will_regenerate=True）：如实宣告「自动修正」——它确实紧随发生."""
    _seed_consecutive_failures(3)
    collector = _DeltaCollector()
    state = _state(context_extra={"stream_callback": collector})

    suggested = await review_nodes._check_and_execute_fallback(
        state=state,
        current_model=FALLBACK_MODEL,
        review_score=0.1,
        review_passed=False,
        will_regenerate=True,
    )

    assert suggested == SUGGESTED_MODEL
    assert collector.texts
    _assert_no_false_promise(collector.texts)
    assert any("修正" in t for t in collector.texts)


@pytest.mark.asyncio
async def test_fallback_not_triggered_sends_nothing(fresh_fallback_service) -> None:
    """检测判据未命中（最近窗口全通过）：零 delta、零建议（不虚发）."""
    service = mfs.get_model_fallback_service()
    service.record_performance(
        model_name=FALLBACK_MODEL,
        task_type="generation",
        review_passed=True,
        review_score=0.9,
        issues_count=0,
    )
    collector = _DeltaCollector()
    state = _state(context_extra={"stream_callback": collector})

    suggested = await review_nodes._check_and_execute_fallback(
        state=state,
        current_model=FALLBACK_MODEL,
        review_score=0.1,
        review_passed=False,
    )

    assert suggested is None
    assert collector.texts == []


# ---------------------------------------------------------------
# ② critical 收尾路径：建议落账（记录），回合结束（不切换不重生成）
# ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_critical_path_records_suggestion_without_switch(
    monkeypatch: pytest.MonkeyPatch, fresh_fallback_service,
) -> None:
    """critical 无反思路径：建议写入留痕键，next_step=__end__，文案无虚假承诺."""
    _seed_consecutive_failures(2)  # 节点内 _record_model_performance 再记 1 次 → 达阈值
    collector = _DeltaCollector()
    state = _state(context_extra={"stream_callback": collector})

    class _StubReviewer:
        model_key = "stub"
        provider_name = "stub"

        async def review_llm_response(self, **kwargs):  # noqa: ANN003
            return _critical_failed_review(requires_reflection=False)

    monkeypatch.setattr(review_nodes, "_get_reviewer", lambda *a, **kw: _StubReviewer())

    result = await review_nodes.generation_review_node(state)

    # 回合收尾：不存在任何重新生成
    assert result["next_step"] == "__end__"
    # 建议留痕两键（零消费方如实标注，见 state.py ReviewContext 注释）
    assert result["review_context"]["fallback_model"] == SUGGESTED_MODEL
    assert state.context_data["suggested_model"] == SUGGESTED_MODEL
    _assert_no_false_promise(collector.texts)


# ---------------------------------------------------------------
# ③ 死面随裁决退役（FIX-339 先例）
# ---------------------------------------------------------------


def test_dead_fallback_helpers_removed() -> None:
    """零调用方死助手/死选择策略已删；误挂回即红."""
    assert not hasattr(review_nodes, "_get_fallback_model")
    service_cls = mfs.ModelFallbackService
    assert not hasattr(service_cls, "get_model_for_task")
    assert not hasattr(service_cls, "_get_highest_quality_model")
    assert not hasattr(service_cls, "_get_balanced_model")
    assert not hasattr(service_cls, "_get_fastest_model")
    assert not hasattr(mfs, "ModelTierPreference")


# ---------------------------------------------------------------
# ④ 保留面（真实宣称）钉死：追踪/检测/建议仍在
# ---------------------------------------------------------------


def test_should_fallback_detection_still_real(fresh_fallback_service) -> None:
    """检测判据真实：连续 3 次审查失败 → 建议降级 + 原因一致；通过后清零."""
    service = mfs.get_model_fallback_service()
    decision = service.should_fallback(FALLBACK_MODEL, task_type="generation")
    assert decision.should_fallback is False

    _seed_consecutive_failures(3)
    decision = service.should_fallback(FALLBACK_MODEL, task_type="generation")
    assert decision.should_fallback is True
    assert decision.reason is not None and decision.reason.value == "consistent_rejection"
    assert decision.suggested_model == SUGGESTED_MODEL

    # 通过后连续失败计数清零（注意：窗口失败率分支按 1h 性能窗独立判定，
    # 此处只钉连续计数语义）
    service.record_performance(
        model_name=FALLBACK_MODEL,
        task_type="generation",
        review_passed=True,
        review_score=0.9,
        issues_count=0,
    )
    summary = service.get_performance_summary()
    assert summary["consecutive_failures"].get(FALLBACK_MODEL, 0) == 0


def test_docstring_no_longer_claims_switching() -> None:
    """宣称面如实：服务源码不得再宣称「触发模型切换」（模块 docstring 位于
    __future__ 之后非真实 docstring，故扫源文件全文）."""
    source = Path(mfs.__file__).read_text(encoding="utf-8")
    assert "触发模型切换" not in source
