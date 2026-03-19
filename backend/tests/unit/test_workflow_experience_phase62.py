import pytest

from app.agents.workflow_experience import (
    build_handoff_packet,
    format_handoff_packets,
    resolve_few_shot_examples,
    resolve_review_profile_id,
)


def test_resolve_review_profile_id_maps_workflows():
    assert resolve_review_profile_id(workflow_context={"chat_mode": "study_plan"}, target_type="response") == "study_plan"
    assert resolve_review_profile_id(workflow_context={"chat_mode": "deep_analysis"}, target_type="response") == "deep_analysis"
    assert resolve_review_profile_id(workflow_context={"chat_mode": "error_diagnosis"}, target_type="response") == "error_diagnosis"
    assert (
        resolve_review_profile_id(
            workflow_context={"workflow_type": "explicit_expert_collaboration"},
            target_type="response",
        )
        == "explicit_expert_collaboration"
    )


@pytest.mark.asyncio
async def test_build_handoff_packet_compresses_long_content(monkeypatch):
    async def _fake_summary(response_text: str, workflow_type: str) -> str:
        return f"{workflow_type} 摘要"

    monkeypatch.setattr("app.agents.workflow_experience._summarize_with_fast_model", _fake_summary)

    packet = await build_handoff_packet(
        agent="MathExpert",
        response_text="这是一个很长的输出。" * 120,
        workflow_type="progressive_exploration",
        reasoning="先推导，再解释适用条件。",
    )

    rendered = format_handoff_packets([packet])

    assert packet.summary == "progressive_exploration 摘要"
    assert len(packet.summary) <= 180
    assert "MathExpert" in rendered
    assert "依据/推理" in rendered
    assert "这是一个很长的输出" not in rendered


@pytest.mark.asyncio
async def test_resolve_few_shot_examples_falls_back_to_builtin():
    examples = await resolve_few_shot_examples(
        db_session=None,
        user_id=None,
        workflow_type="error_diagnosis",
        chat_mode="error_diagnosis",
        agent_role="problem_solver",
        stage="collaboration",
        count=1,
    )

    assert len(examples) == 1
    assert "根因" in examples[0]["output"] or "根因" in (examples[0].get("explanation") or "")
