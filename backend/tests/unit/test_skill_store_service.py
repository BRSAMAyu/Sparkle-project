from uuid import uuid4

import pytest

from app.models.user import User
from app.services.skill_store import SkillStoreService


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
async def test_skill_store_crud_and_usage_reset(db_session):
    user = await _create_user(db_session)
    service = SkillStoreService(db_session)

    skill = await service.create_skill(
        user_id=user.id,
        payload={
            "name": "Exam Triage",
            "pattern_template": "Start with the exam scope and compress into three next actions.",
            "activation_conditions": [{"kind": "intent_keywords", "value": ["exam"]}],
            "examples": ["先缩小范围，再给三步行动。"],
        },
    )
    await service.increment_usage(user_id=user.id, skill_ids=[skill.id])

    updated = await service.update_skill(
        user_id=user.id,
        skill_id=skill.id,
        payload={
            "pattern_template": "Start with scope, blockers, and the smallest next step.",
        },
    )

    assert updated.usage_count == 0
    assert updated.last_activated_at is None

    items = await service.list_user_skills(user_id=user.id)
    assert len(items) == 1

    await service.delete_skill(user_id=user.id, skill_id=skill.id)
    assert await service.list_user_skills(user_id=user.id) == []


@pytest.mark.asyncio
async def test_skill_store_enforces_user_limit(db_session):
    user = await _create_user(db_session)
    service = SkillStoreService(db_session)

    for index in range(50):
        await service.create_skill(
            user_id=user.id,
            payload={
                "name": f"Skill {index}",
                "pattern_template": f"Pattern {index}",
                "activation_conditions": [{"kind": "intent_keywords", "value": [f"intent-{index}"]}],
                "examples": [],
            },
        )

    with pytest.raises(ValueError, match="Skill limit reached"):
        await service.create_skill(
            user_id=user.id,
            payload={
                "name": "Overflow",
                "pattern_template": "Overflow pattern",
                "activation_conditions": [{"kind": "intent_keywords", "value": ["overflow"]}],
                "examples": [],
            },
        )
