from datetime import datetime
from uuid import uuid4

import pytest

from app.models.aurora_stage20 import UnresolvedConflict
from app.models.user import User
from app.services.skill_schema import SkillSelectionContext
from app.services.skill_store import SkillStoreService
from app.services.skill_selection_service import SkillSelectionService


async def _create_user(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_skill_selection_matches_top_skills(db_session):
    user = await _create_user(db_session)
    store = SkillStoreService(db_session)
    await store.create_skill(
        user_id=user.id,
        payload={
            "name": "Exam Triage",
            "pattern_template": "Scope first.",
            "activation_conditions": [
                {"kind": "intent_keywords", "value": ["exam"]},
                {"kind": "tool_category", "value": ["direct"]},
            ],
            "examples": [],
        },
    )

    matches, caveats = await SkillSelectionService(db_session).resolve_prompt_payload(
        user_id=user.id,
        selection_context=SkillSelectionContext(
            intent="exam planning",
            tool_category="direct",
            current_time=datetime(2026, 4, 21, 9, 0, 0),
        ),
    )

    assert caveats == []
    assert len(matches) == 1
    assert matches[0].activation_match_score == 1.0


@pytest.mark.asyncio
async def test_skill_selection_blocks_on_unresolved_conflict(db_session):
    user = await _create_user(db_session)
    store = SkillStoreService(db_session)
    skill = await store.create_skill(
        user_id=user.id,
        payload={
            "name": "Exam Triage",
            "pattern_template": "Scope first.",
            "activation_conditions": [{"kind": "intent_keywords", "value": ["exam-plan"]}],
            "examples": [],
        },
    )
    db_session.add(
        UnresolvedConflict(
            user_id=user.id,
            conflict_key="exam-plan",
            left_summary="A",
            right_summary="B",
            left_lane="explicit",
            right_lane="inferred_extraction",
            surfaced_at=datetime(2026, 4, 21, 8, 0, 0),
        )
    )
    await db_session.commit()

    matches, caveats = await SkillSelectionService(db_session).resolve_prompt_payload(
        user_id=user.id,
        selection_context=SkillSelectionContext(
            intent="exam-plan",
            tool_category="direct",
            current_time=datetime(2026, 4, 21, 9, 0, 0),
        ),
    )

    assert matches == []
    assert skill.name in caveats[0]
