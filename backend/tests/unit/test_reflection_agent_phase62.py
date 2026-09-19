import pytest

from app.agents.reflection_agent import ReflectionAgent
from app.agents.reviewer_agent import (
    Issue,
    QuantifiedMetric,
    ReviewDecision,
    ReviewMetric,
    ReviewResult,
    ReviewSeverity,
)


class _FakeGenerator:
    def __init__(self):
        self.calls = []

    async def chat(self, messages, temperature=0.3):
        # wave5 对齐：5416b1d3 N2 修复后 reflection 的生成器调用改为
        # messages-first 签名（chat([{"role":...},...], temperature=...)），
        # 与 app/core/llm_client.py 裸服务签名一致；旧
        # chat(system_prompt=, user_message=) 在任何真实实现上都不存在。
        self.calls.append((messages, temperature))
        return f"修正版{len(self.calls)}"


class _SequencedReviewer:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    async def review_llm_response(self, **kwargs):
        self.calls.append(kwargs)
        return self.results.pop(0)


def _review_result(review_id: str, score: float, issue_count: int) -> ReviewResult:
    issues = [
        Issue(
            category="clarity",
            severity=ReviewSeverity.WARNING.value,
            location="段落1",
            description=f"问题{i}",
            affected_content="片段",
            suggested_fix="补充说明",
            confidence=0.8,
        )
        for i in range(issue_count)
    ]
    return ReviewResult(
        review_id=review_id,
        target_type="response",
        target_id=review_id,
        decision=ReviewDecision.NEEDS_REFINEMENT.value,
        overall_score=score,
        metrics=[QuantifiedMetric(metric=ReviewMetric.CLARITY, score=score)],
        issues=issues,
        improvement_suggestions=["补充解释"],
        requires_reflection=True,
        reviewer_model="reviewer",
        review_timestamp="2026-03-19T00:00:00",
        review_profile_id="deep_analysis",
        workflow_context={"workflow_type": "progressive_exploration", "chat_mode": "deep_analysis"},
    )


@pytest.mark.asyncio
async def test_reflection_agent_stops_early_on_low_second_round_gain():
    initial_review = _review_result("review_1", 0.60, 2)
    round_1_review = _review_result("review_2", 0.66, 2)
    round_2_review = _review_result("review_3", 0.68, 2)

    reviewer = _SequencedReviewer([round_1_review, round_2_review])
    generator = _FakeGenerator()
    reflector = ReflectionAgent(generator_llm=generator, reviewer=reviewer, max_rounds=3, min_improvement=0.05)

    result = await reflector.reflect(
        user_id="user-1",
        user_query="解释反向传播为什么这样推导",
        original_content="原始回答",
        review_result=initial_review,
        review_profile_id="deep_analysis",
        workflow_context={"workflow_type": "progressive_exploration", "chat_mode": "deep_analysis"},
    )

    assert result.total_rounds == 2
    assert result.initial_score == 0.60
    assert result.final_score == 0.68
    assert result.score_delta == pytest.approx(0.08, rel=1e-6)
    assert result.early_stop_reason == "low_marginal_gain"
    assert result.best_round_number == 2
    assert result.review_profile_id == "deep_analysis"
    assert result.best_review_result is not None
    assert result.best_review_result["overall_score"] == pytest.approx(0.68, rel=1e-6)
    assert reviewer.calls[0]["review_profile_id"] == "deep_analysis"
    # messages-first：calls[0] = (messages, temperature)，system 在 messages[0]
    assert generator.calls[0][0][0]["role"] == "system"
    assert "讲解/深度分析审查" in generator.calls[0][0][0]["content"]
