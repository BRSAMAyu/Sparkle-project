from datetime import datetime
from uuid import uuid4

import pytest

from app.services.sufficiency_judge_schema import CurrentTurnParseResult
from app.state_aggregator.service import StateAggregatorService


@pytest.mark.asyncio
async def test_state_aggregator_returns_sufficiency_summaries_only_when_requested(db_session) -> None:
    user_id = uuid4()
    service = StateAggregatorService(db_session)

    state = await service.get_user_state(
        user_id,
        required_fields=("task_sufficiency_summary", "context_sufficiency_summary"),
        current_turn_parse=CurrentTurnParseResult(
            intent="plan",
            intent_confidence=0.42,
            information_sufficient=False,
            target_object_resolved=False,
            constraint_explicit=False,
        ),
        now=datetime(2026, 4, 21, 12, 0, 0),
    )

    assert state.task_sufficiency_summary is not None
    assert state.task_sufficiency_summary.value.score < 0.6
    assert len(state.task_sufficiency_summary.value.top_missing_dimensions) <= 3

    assert state.context_sufficiency_summary is not None
    assert len(state.context_sufficiency_summary.value.top_missing_dimensions) <= 3
    assert state.commitment_summary is None
