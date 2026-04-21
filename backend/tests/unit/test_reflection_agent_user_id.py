import pytest

from app.agents.reflection_agent import ReflectionAgent, TriggeredReflectionResult
from app.agents.reviewer_agent import (
    QuantifiedMetric,
    ReviewDecision,
    ReviewMetric,
    ReviewResult,
)


class _FakeGenerator:
    def __init__(self, trigger_response: str = '{"summary":"最近的执行阻力在重复出现。","reasoning":"同类结果反复出现。","confidence":0.88,"evidence":["e1","e2"]}'):
        self.trigger_response = trigger_response
        self.calls = []

    async def chat(self, system_prompt, user_message, temperature=0.3):
        self.calls.append((system_prompt, user_message, temperature))
        return self.trigger_response

    def get_current_selection(self):
        return type("Selection", (), {"estimated_cost_per_1k": 0.002})()


class _FakeReviewer:
    async def review_llm_response(self, **kwargs):
        return ReviewResult(
            review_id="review_2",
            target_type="response",
            target_id="target_1",
            decision=ReviewDecision.PASSED.value,
            overall_score=0.9,
            metrics=[QuantifiedMetric(metric=ReviewMetric.CLARITY, score=0.9)],
            issues=[],
            improvement_suggestions=[],
            requires_reflection=False,
            reviewer_model="reviewer",
            review_timestamp="2026-04-21T00:00:00",
        )


def _review_result() -> ReviewResult:
    return ReviewResult(
        review_id="review_1",
        target_type="response",
        target_id="target_1",
        decision=ReviewDecision.NEEDS_REFINEMENT.value,
        overall_score=0.6,
        metrics=[QuantifiedMetric(metric=ReviewMetric.CLARITY, score=0.6)],
        issues=[],
        improvement_suggestions=[],
        requires_reflection=True,
        reviewer_model="reviewer",
        review_timestamp="2026-04-21T00:00:00",
    )


@pytest.mark.asyncio
async def test_reflection_agent_requires_user_id() -> None:
    agent = ReflectionAgent(generator_llm=_FakeGenerator(), reviewer=_FakeReviewer())

    with pytest.raises(AssertionError):
        await agent.reflect(
            user_query="问题",
            original_content="原始内容",
            review_result=_review_result(),
        )


@pytest.mark.asyncio
async def test_reflection_agent_review_mode_accepts_user_id() -> None:
    agent = ReflectionAgent(generator_llm=_FakeGenerator(trigger_response="修正版"), reviewer=_FakeReviewer(), max_rounds=1)

    result = await agent.reflect(
        user_id="user-1",
        user_query="问题",
        original_content="原始内容",
        review_result=_review_result(),
    )

    assert result.review_profile_id == "default_response"
    assert result.total_rounds == 1


@pytest.mark.asyncio
async def test_reflection_agent_trigger_mode_returns_triggered_result() -> None:
    generator = _FakeGenerator()
    agent = ReflectionAgent(generator_llm=generator, reviewer=_FakeReviewer())

    result = await agent.reflect(
        user_id="user-1",
        trigger_category="plan_stall",
        trigger_payload={"decision_id": "abc"},
        context={
            "route_history_context": "- evidence line 1\n- evidence line 2",
            "route_history_context_tokens": 24,
            "route_history_context_truncated": False,
        },
    )

    assert isinstance(result, TriggeredReflectionResult)
    assert result.user_id == "user-1"
    assert result.category == "plan_stall"
    assert result.context_tokens == 24
    assert generator.calls[0][2] == 0.3


@pytest.mark.asyncio
async def test_reflection_agent_trigger_mode_falls_back_on_invalid_json() -> None:
    agent = ReflectionAgent(generator_llm=_FakeGenerator(trigger_response="not-json"), reviewer=_FakeReviewer())

    result = await agent.reflect(
        user_id="user-1",
        trigger_category="overload",
        trigger_payload={},
        context={"route_history_context": "- 最近失败集中在同一天"},
    )

    assert isinstance(result, TriggeredReflectionResult)
    assert "过载" in result.summary or "负荷" in result.summary
    assert result.confidence >= 0.55
