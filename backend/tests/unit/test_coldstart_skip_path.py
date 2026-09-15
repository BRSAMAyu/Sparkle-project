from __future__ import annotations

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.user_preferences import UserPreferencesCenter
from app.services.traits_coldstart_service import TraitsColdStartService


@pytest.mark.asyncio
async def test_coldstart_skip_path_keeps_traits_empty(db_session, test_user) -> None:
    settings.AURORA_TRAITS_MODE = "live"
    settings.AURORA_TRAITS_COLDSTART_MODE = "live"
    service = TraitsColdStartService(db_session)

    traits = await service.submit_answers(test_user.id, {})

    assert traits.active_dimensions() == {}
    prefs = (await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == test_user.id))).scalar_one()
    assert prefs.traits_prior == {}


@pytest.mark.asyncio
async def test_coldstart_skip_path_still_marks_completion(db_session, test_user) -> None:
    settings.AURORA_TRAITS_MODE = "live"
    settings.AURORA_TRAITS_COLDSTART_MODE = "live"
    service = TraitsColdStartService(db_session)

    await service.submit_answers(test_user.id, {"q1": "skip", "q2": "skip", "q3": "skip"})

    prefs = (await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == test_user.id))).scalar_one()
    assert prefs.traits_coldstart_completed_at is not None
