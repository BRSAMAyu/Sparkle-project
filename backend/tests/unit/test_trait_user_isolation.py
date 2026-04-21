from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.chat import ChatMessage, MessageRole
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter
from app.services.traits_merge_service import TraitsMergeService
from app.services.traits_nlp_observer_service import TraitsNlpObserverService


@pytest.mark.asyncio
async def test_text_collection_does_not_cross_user_boundary(db_session, test_user) -> None:
    other_user = User(username="other", email="other@example.com", hashed_password="hashed")
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)
    db_session.add_all(
        [
            ChatMessage(user_id=test_user.id, session_id=uuid4(), role=MessageRole.USER, content="my private text"),
            ChatMessage(user_id=other_user.id, session_id=uuid4(), role=MessageRole.USER, content="other private text"),
        ]
    )
    await db_session.commit()

    texts = await TraitsNlpObserverService(db_session).collect_recent_user_texts(test_user.id)
    assert texts == ["my private text"]


@pytest.mark.asyncio
async def test_register_observation_updates_only_target_user_state(db_session, test_user, monkeypatch) -> None:
    settings.AURORA_TRAITS_MODE = "live"
    settings.AURORA_TRAITS_NLP_MODE = "live"
    other_user = User(username="other2", email="other2@example.com", hashed_password="hashed")
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)
    observer = TraitsNlpObserverService(db_session)
    monkeypatch.setattr(observer, "_call_llm_candidate", lambda texts: __import__("asyncio").sleep(0, result=None))
    observation = await observer.observe_user(test_user.id, texts=["quiet and alone"])

    await TraitsMergeService(db_session).register_observation(test_user.id, observation)

    target = (await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == test_user.id))).scalar_one()
    other = (await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == other_user.id))).scalar_one_or_none()
    assert "history" in (target.trait_observation_state or {})
    assert other is None


@pytest.mark.asyncio
async def test_merge_does_not_write_other_user_traits(db_session, test_user) -> None:
    other_user = User(username="other3", email="other3@example.com", hashed_password="hashed")
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    await TraitsMergeService(db_session).pref_service.update_traits(
        test_user.id,
        traits_prior={"openness": {"value": 0.2, "confidence": 0.11, "evidence_count": 3, "last_observed_at": "2026-04-21T10:00:00", "source": "merged"}},
    )

    other = (await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == other_user.id))).scalar_one_or_none()
    assert other is None


@pytest.mark.asyncio
async def test_observer_returns_no_foreign_text_even_with_multiple_sessions(db_session, test_user) -> None:
    db_session.add_all(
        [
            ChatMessage(user_id=test_user.id, session_id=uuid4(), role=MessageRole.USER, content="session one"),
            ChatMessage(user_id=test_user.id, session_id=uuid4(), role=MessageRole.USER, content="session two"),
        ]
    )
    await db_session.commit()

    texts = await TraitsNlpObserverService(db_session).collect_recent_user_texts(test_user.id)
    assert set(texts) == {"session one", "session two"}
