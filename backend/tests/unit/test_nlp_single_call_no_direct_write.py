from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.user_preferences import UserPreferencesCenter
from app.services.traits_merge_service import TraitsMergeService
from app.services.traits_nlp_observer_service import TraitsNlpObserverService


@pytest.mark.asyncio
async def test_single_observation_does_not_persist_traits_prior(db_session, test_user, monkeypatch) -> None:
    settings.AURORA_TRAITS_MODE = "live"
    settings.AURORA_TRAITS_NLP_MODE = "live"
    service = TraitsNlpObserverService(db_session)
    monkeypatch.setattr(service, "_call_llm_candidate", lambda texts: __import__("asyncio").sleep(0, result=None))

    observation = await service.observe_user(test_user.id, texts=["我喜欢安静地一个人想问题"])

    assert observation is not None
    prefs = (await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == test_user.id))).scalar_one_or_none()
    assert prefs is None or prefs.traits_prior in ({}, None)


@pytest.mark.asyncio
async def test_register_observation_writes_only_observation_state(db_session, test_user, monkeypatch) -> None:
    settings.AURORA_TRAITS_MODE = "live"
    settings.AURORA_TRAITS_NLP_MODE = "live"
    observer = TraitsNlpObserverService(db_session)
    monkeypatch.setattr(observer, "_call_llm_candidate", lambda texts: __import__("asyncio").sleep(0, result=None))
    observation = await observer.observe_user(test_user.id, texts=["brainstorm with people"])

    await TraitsMergeService(db_session).register_observation(test_user.id, observation)

    prefs = (await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == test_user.id))).scalar_one()
    assert prefs.traits_prior == {}
    assert "history" in (prefs.trait_observation_state or {})


def test_observer_source_contains_no_traits_prior_assignment() -> None:
    source = Path(__file__).resolve().parents[2] / "app" / "services" / "traits_nlp_observer_service.py"
    text = source.read_text(encoding="utf-8")
    assert ".traits_prior =" not in text
