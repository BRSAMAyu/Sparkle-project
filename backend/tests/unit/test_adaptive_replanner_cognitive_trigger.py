from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.orchestration.adaptive_replanner import CognitivePatternTrigger


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


@pytest.mark.asyncio
async def test_cognitive_pattern_trigger_maps_patterns_and_respects_explicit_preferences():
    db = SimpleNamespace(execute=AsyncMock(return_value=_ScalarResult([
        SimpleNamespace(
            pattern_name="Planning Optimism",
            pattern_type="cognitive",
            confidence_score=0.85,
            description="planning.underestimate",
            evidence_ids=["node-1"],
            frequency=3,
        ),
        SimpleNamespace(
            pattern_name="焦虑驱动的过度规划",
            pattern_type="emotional",
            confidence_score=0.78,
            description="用户在反复调整计划",
            evidence_ids=[],
            frequency=2,
        ),
        SimpleNamespace(
            pattern_name="番茄钟逃避",
            pattern_type="execution",
            confidence_score=0.82,
            description="启动困难",
            evidence_ids=[],
            frequency=4,
        ),
    ])))
    trigger = CognitivePatternTrigger(db, redis=None)
    trigger.preference_service.get_preferences = AsyncMock(
        return_value=SimpleNamespace(explicit={"focus_duration_preference": 25})
    )

    adjustments = await trigger.build_adjustments(
        user_id=uuid4(),
        existing_constraints={},
    )

    params = {item.parameter: item for item in adjustments}
    assert "task_duration_multiplier" in params
    assert params["task_duration_multiplier"].value == 1.3
    assert "max_concurrent_tasks" in params
    assert params["max_concurrent_tasks"].value == 3
    assert "max_session_minutes" not in params
    assert len(adjustments) <= trigger.MAX_ADJUSTMENTS_PER_RUN
