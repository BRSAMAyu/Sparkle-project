from uuid import uuid4

import pytest

from app.schemas.analysis import AnalysisTaskInput
from app.services.analysis.orchestrator import AnalysisOrchestrator
from app.services.llm_service import llm_service


@pytest.mark.asyncio
async def test_analysis_orchestrator_behavior_task(monkeypatch):
    async def _fake_chat(messages, model=None, temperature=0.5, **kwargs):
        return (
            '{"root_cause":"scope creep","pattern_name":"Overplanning","pattern_type":"execution",'
            '"description":"too much planning","solution_text":"timebox","confidence_score":0.72}'
        )

    monkeypatch.setattr(llm_service, "chat", _fake_chat)

    task = AnalysisTaskInput(
        task_id="task-123",
        task_type="behavior_pattern_from_fragment",
        user_id=uuid4(),
        source_type="capsule",
        payload={
            "fragment_content": "I keep polishing the plan instead of starting.",
            "context_tags": {"mood": "anxious"},
            "error_tags": ["planning"],
            "severity": 3,
            "similar_text": "",
            "user_summary": "Active learner",
        },
    )

    orchestrator = AnalysisOrchestrator()
    result = await orchestrator.run_task(task)

    assert result.status == "ok"
    assert result.primary_output["pattern_name"] == "Overplanning"
    assert result.confidence == 0.72
