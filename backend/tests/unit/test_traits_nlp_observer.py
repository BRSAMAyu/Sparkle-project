from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.chat import ChatMessage, MessageRole
from app.models.user_preferences import UserPreferencesCenter
from app.services.traits_nlp_observer_service import TraitsNlpObserverService


@pytest.mark.asyncio
async def test_collect_recent_user_texts_isolated_by_user_id(db_session, test_user) -> None:
    other_user_id = uuid4()
    db_session.add_all(
        [
            ChatMessage(user_id=test_user.id, session_id=test_user.id, role=MessageRole.USER, content="my text"),
            ChatMessage(user_id=other_user_id, session_id=other_user_id, role=MessageRole.USER, content="other text"),
        ]
    )
    await db_session.commit()

    texts = await TraitsNlpObserverService(db_session).collect_recent_user_texts(test_user.id)

    assert texts == ["my text"]


@pytest.mark.asyncio
async def test_observer_returns_none_when_main_mode_off(db_session, test_user) -> None:
    settings.AURORA_TRAITS_MODE = "off"
    settings.AURORA_TRAITS_NLP_MODE = "live"

    result = await TraitsNlpObserverService(db_session).observe_user(test_user.id, texts=["hello"])

    assert result is None


@pytest.mark.asyncio
async def test_observer_returns_none_when_nlp_mode_off(db_session, test_user) -> None:
    settings.AURORA_TRAITS_MODE = "live"
    settings.AURORA_TRAITS_NLP_MODE = "off"

    result = await TraitsNlpObserverService(db_session).observe_user(test_user.id, texts=["hello"])

    assert result is None


@pytest.mark.asyncio
async def test_observer_skips_when_in_cooldown(db_session, test_user) -> None:
    settings.AURORA_TRAITS_MODE = "live"
    settings.AURORA_TRAITS_NLP_MODE = "live"
    prefs = UserPreferencesCenter(
        user_id=test_user.id,
        explicit={},
        inferred={},
        trait_observation_state={"last_nlp_observed_at": datetime.utcnow().isoformat()},
    )
    db_session.add(prefs)
    await db_session.commit()

    result = await TraitsNlpObserverService(db_session).observe_user(test_user.id, texts=["hello"])

    assert result is None


@pytest.mark.asyncio
async def test_observer_builds_candidate_from_llm_payload(db_session, test_user, monkeypatch) -> None:
    settings.AURORA_TRAITS_MODE = "live"
    settings.AURORA_TRAITS_NLP_MODE = "live"
    service = TraitsNlpObserverService(db_session)
    monkeypatch.setattr(
        service,
        "_call_llm_candidate",
        lambda texts: __import__("asyncio").sleep(0, result={"openness": {"value": 0.18, "confidence": 0.05}}),
    )

    observation = await service.observe_user(test_user.id, texts=["I like new ideas"])

    assert observation is not None
    assert observation.openness is not None
    assert observation.openness.value == 0.18


@pytest.mark.asyncio
async def test_observer_falls_back_to_heuristic_payload(db_session, test_user, monkeypatch) -> None:
    settings.AURORA_TRAITS_MODE = "live"
    settings.AURORA_TRAITS_NLP_MODE = "live"
    service = TraitsNlpObserverService(db_session)
    monkeypatch.setattr(service, "_call_llm_candidate", lambda texts: __import__("asyncio").sleep(0, result=None))

    observation = await service.observe_user(test_user.id, texts=["我喜欢先写清单再开始"])

    assert observation is not None
    assert observation.conscientiousness is not None


@pytest.mark.asyncio
async def test_observer_clamps_large_values_to_small_candidate_delta(db_session, test_user, monkeypatch) -> None:
    settings.AURORA_TRAITS_MODE = "live"
    settings.AURORA_TRAITS_NLP_MODE = "live"
    service = TraitsNlpObserverService(db_session)
    monkeypatch.setattr(
        service,
        "_call_llm_candidate",
        lambda texts: __import__("asyncio").sleep(0, result={"neuroticism": {"value": 0.9, "confidence": 0.09}}),
    )

    observation = await service.observe_user(test_user.id, texts=["panic"])

    assert observation is not None
    assert observation.neuroticism is not None
    assert observation.neuroticism.value == 0.2


@pytest.mark.asyncio
async def test_observer_does_not_write_traits_prior_directly(db_session, test_user, monkeypatch) -> None:
    settings.AURORA_TRAITS_MODE = "live"
    settings.AURORA_TRAITS_NLP_MODE = "live"
    service = TraitsNlpObserverService(db_session)
    monkeypatch.setattr(service, "_call_llm_candidate", lambda texts: __import__("asyncio").sleep(0, result=None))

    await service.observe_user(test_user.id, texts=["alone and quiet"])

    prefs = (await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == test_user.id))).scalar_one_or_none()
    assert prefs is None or prefs.traits_prior in ({}, None)
