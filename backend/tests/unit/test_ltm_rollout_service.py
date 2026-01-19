from uuid import uuid4

import pytest

from app.config import settings
from app.models.user import User
from app.services.ltm_rollout_service import LtmRolloutService


@pytest.mark.asyncio
async def test_rollout_allowlist(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LTM_ROLLOUT", True, raising=False)
    user_id = uuid4()
    monkeypatch.setattr(settings, "LTM_ROLLOUT_USER_ALLOWLIST", [str(user_id)], raising=False)
    monkeypatch.setattr(settings, "LTM_ROLLOUT_PERCENT", 0, raising=False)
    monkeypatch.setattr(settings, "LTM_ROLLOUT_COHORT_TAGS", [], raising=False)

    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    service = LtmRolloutService(db_session)
    assert await service.is_enabled(user_id) is True


@pytest.mark.asyncio
async def test_rollout_cohort_tag(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LTM_ROLLOUT", True, raising=False)
    monkeypatch.setattr(settings, "LTM_ROLLOUT_USER_ALLOWLIST", [], raising=False)
    monkeypatch.setattr(settings, "LTM_ROLLOUT_PERCENT", 0, raising=False)
    monkeypatch.setattr(settings, "LTM_ROLLOUT_COHORT_TAGS", ["beta"], raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
        schedule_preferences={"cohort_tags": ["beta"]},
    )
    db_session.add(user)
    await db_session.commit()

    service = LtmRolloutService(db_session)
    assert await service.is_enabled(user_id) is True


@pytest.mark.asyncio
async def test_rollout_percent(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LTM_ROLLOUT", True, raising=False)
    monkeypatch.setattr(settings, "LTM_ROLLOUT_USER_ALLOWLIST", [], raising=False)
    monkeypatch.setattr(settings, "LTM_ROLLOUT_COHORT_TAGS", [], raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    service = LtmRolloutService(db_session)
    monkeypatch.setattr(settings, "LTM_ROLLOUT_PERCENT", 0, raising=False)
    assert await service.is_enabled(user_id) is False
    monkeypatch.setattr(settings, "LTM_ROLLOUT_PERCENT", 100, raising=False)
    assert await service.is_enabled(user_id) is True
