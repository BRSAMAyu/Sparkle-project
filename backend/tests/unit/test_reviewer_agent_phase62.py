import asyncio

import pytest

from app.agents.reviewer_agent import ReviewerAgent


class _FakeReviewerLLM:
    def __init__(self):
        self.default_model = "review-model"
        self.model_key = "review_model_key"
        self.provider_name = "dashscope"
        self.messages = None

    async def chat_json(self, messages, temperature=0.2):
        self.messages = messages
        return {
            "overall_score": 0.82,
            "decision": "passed",
            "metrics": [
                {"metric": "completeness", "score": 0.82, "weight": 1.4, "threshold": 0.75},
            ],
            "issues": [],
            "improvement_suggestions": [],
            "requires_reflection": False,
            "timestamp": "2026-03-19T00:00:00",
        }


class _SlowReviewerLLM(_FakeReviewerLLM):
    async def chat_json(self, messages, temperature=0.2):
        await asyncio.sleep(0.05)
        return await super().chat_json(messages, temperature=temperature)


@pytest.mark.asyncio
async def test_reviewer_agent_uses_workflow_specific_profile():
    llm = _FakeReviewerLLM()
    reviewer = ReviewerAgent(reviewer_llm=llm)

    result = await reviewer.review_llm_response(
        user_query="帮我做离散数学复习计划",
        llm_response="先复习命题逻辑，再做真题。",
        review_profile_id="study_plan",
        workflow_context={"workflow_type": "task_decomposition", "chat_mode": "study_plan"},
    )

    assert llm.messages is not None
    assert "任务拆解/学习规划审查" in llm.messages[0]["content"]
    assert "profile_id: study_plan" in llm.messages[1]["content"]
    assert result.review_profile_id == "study_plan"
    assert result.workflow_context == {"workflow_type": "task_decomposition", "chat_mode": "study_plan"}


@pytest.mark.asyncio
async def test_reviewer_agent_falls_back_when_review_times_out(monkeypatch):
    monkeypatch.setattr("app.agents.reviewer_agent.settings.REVIEWER_LLM_TIMEOUT_SECONDS", 0.01)

    llm = _SlowReviewerLLM()
    reviewer = ReviewerAgent(reviewer_llm=llm)

    result = await reviewer.review_llm_response(
        user_query="帮我审查这段回答",
        llm_response="这是一段需要审查的回答。",
        review_profile_id="study_plan",
        workflow_context={"workflow_type": "task_decomposition", "chat_mode": "study_plan"},
    )

    assert result.decision == "needs_refinement"
    assert result.overall_score == 0.5
    assert any("审查过程出错" in issue.description for issue in result.issues)
