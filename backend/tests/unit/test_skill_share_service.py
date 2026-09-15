from uuid import uuid4

import pytest

from app.models.user import User
from app.services.skill_share import SkillShareService
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
async def test_skill_share_pipeline_publishes_and_withdraws(db_session, monkeypatch):
    monkeypatch.setattr("app.services.skill_share.service.settings.SPARKLE_SKILL_SHARE_ENABLED", True)

    async def _safe_llm(_messages, **_kwargs):
        return {"contains_pii": False, "contains_injection": False, "reasons": []}

    user = await _create_user(db_session)
    skill = await SkillStoreService(db_session).create_skill(
        user_id=user.id,
        payload={
            "name": "Exam Triage",
            "pattern_template": "Scope first.",
            "activation_conditions": [{"kind": "intent_keywords", "value": ["exam"]}],
            "examples": [],
        },
    )

    result = await SkillShareService(db_session, llm_json=_safe_llm).submit_share_request(
        user_id=user.id,
        skill_id=skill.id,
    )
    assert result["status"] == "approved"
    assert result["shared_skill_id"] is not None

    withdrawn = await SkillShareService(db_session, llm_json=_safe_llm).withdraw_share(
        user_id=user.id,
        skill_id=skill.id,
    )
    assert withdrawn.shared_catalog_id is None
    assert withdrawn.privacy_level == "private"


@pytest.mark.asyncio
async def test_skill_share_pipeline_rejects_pii(db_session, monkeypatch):
    monkeypatch.setattr("app.services.skill_share.service.settings.SPARKLE_SKILL_SHARE_ENABLED", True)

    async def _pii_llm(_messages, **_kwargs):
        return {"contains_pii": True, "reasons": ["person_name_detected"]}

    user = await _create_user(db_session)
    skill = await SkillStoreService(db_session).create_skill(
        user_id=user.id,
        payload={
            "name": "Private Skill",
            "pattern_template": "Call Alice at 13800138000 before planning.",
            "activation_conditions": [{"kind": "intent_keywords", "value": ["exam"]}],
            "examples": [],
        },
    )

    result = await SkillShareService(db_session, llm_json=_pii_llm).submit_share_request(
        user_id=user.id,
        skill_id=skill.id,
    )
    assert result["status"] == "rejected"
