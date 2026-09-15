from datetime import datetime
from uuid import uuid4

import pytest

from app.models.user import User
from app.services.skill_schema import SkillSelectionContext
from app.services.skill_store import SkillStoreService
from app.state_aggregator.service import StateAggregatorService


@pytest.mark.asyncio
async def test_state_aggregator_returns_active_skills_summary(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    await SkillStoreService(db_session).create_skill(
        user_id=user.id,
        payload={
            "name": "Exam Triage",
            "pattern_template": "Scope first.",
            "activation_conditions": [{"kind": "intent_keywords", "value": ["exam"]}],
            "examples": [],
        },
    )

    state = await StateAggregatorService(db_session).get_user_state(
        user.id,
        required_fields=("active_skills_summary",),
        skill_selection_context=SkillSelectionContext(
            intent="exam prep",
            tool_category="direct",
            current_time=datetime(2026, 4, 21, 10, 0, 0),
        ),
        now=datetime(2026, 4, 21, 10, 0, 0),
    )

    assert state.active_skills_summary is not None
    assert len(state.active_skills_summary.value.items) == 1
    assert state.active_skills_summary.value.items[0].name == "Exam Triage"
