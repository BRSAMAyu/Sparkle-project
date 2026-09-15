from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.user_preferences import UserPreferencesCenter
from app.services.traits_coldstart_service import COLDSTART_QUESTIONS, TraitsColdStartService


@pytest.mark.asyncio
async def test_coldstart_service_maps_answers_into_big_five(db_session, test_user) -> None:
    settings.AURORA_TRAITS_MODE = "live"
    settings.AURORA_TRAITS_COLDSTART_MODE = "live"
    service = TraitsColdStartService(db_session)

    traits = await service.submit_answers(
        test_user.id,
        {"q1": "structured", "q2": "small_group", "q3": "replan"},
    )

    assert traits.conscientiousness is not None
    assert traits.conscientiousness.confidence <= 0.2
    assert traits.extraversion is not None


@pytest.mark.asyncio
async def test_coldstart_service_persists_traits_prior(db_session, test_user) -> None:
    settings.AURORA_TRAITS_MODE = "live"
    settings.AURORA_TRAITS_COLDSTART_MODE = "live"
    service = TraitsColdStartService(db_session)

    await service.submit_answers(test_user.id, {"q1": "explore", "q2": "group", "q3": "pause"})

    prefs = (await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == test_user.id))).scalar_one()
    assert "openness" in (prefs.traits_prior or {})


@pytest.mark.asyncio
async def test_coldstart_service_marks_completion_timestamp(db_session, test_user) -> None:
    settings.AURORA_TRAITS_MODE = "live"
    settings.AURORA_TRAITS_COLDSTART_MODE = "live"
    service = TraitsColdStartService(db_session)

    await service.submit_answers(test_user.id, {"q1": "mixed", "q2": "solo", "q3": "pause"})

    prefs = (await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == test_user.id))).scalar_one()
    assert isinstance(prefs.traits_coldstart_completed_at, datetime)


@pytest.mark.asyncio
async def test_coldstart_service_keeps_initial_confidence_below_point_two(db_session, test_user) -> None:
    settings.AURORA_TRAITS_MODE = "live"
    settings.AURORA_TRAITS_COLDSTART_MODE = "live"
    service = TraitsColdStartService(db_session)

    traits = await service.submit_answers(test_user.id, {"q1": "mixed", "q2": "small_group", "q3": "swing"})

    assert all(item["confidence"] <= 0.2 for item in traits.model_dump(mode="json", exclude_none=True).values())


def test_coldstart_question_bank_has_three_questions() -> None:
    assert len(COLDSTART_QUESTIONS) == 3
    assert all(any(option["id"] == "skip" for option in question["options"]) for question in COLDSTART_QUESTIONS)
