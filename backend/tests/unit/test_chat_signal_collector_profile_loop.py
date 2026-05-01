from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.cognitive import CognitiveFragment
from app.models.user import User
from app.services.chat_signal_collector import ChatSignalCollector
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_context_service import ProfileContextService


class _RedisListCache:
    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self._lists: dict[str, list[str]] = {}
        self._counts: dict[str, int] = {}

    async def get(self, key: str):
        return self._kv.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self._kv[key] = value

    async def delete(self, *keys: str):
        for key in keys:
            self._kv.pop(key, None)

    async def lpush(self, key: str, value: str):
        self._lists.setdefault(key, []).insert(0, value)

    async def ltrim(self, key: str, start: int, end: int):
        values = self._lists.get(key, [])
        self._lists[key] = values[start : end + 1]

    async def expire(self, key: str, ttl: int):
        return None

    async def lindex(self, key: str, index: int):
        values = self._lists.get(key, [])
        if index >= len(values):
            return None
        return values[index]

    async def incr(self, key: str):
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    async def lrange(self, key: str, start: int, end: int):
        values = self._lists.get(key, [])
        return values[start : end + 1]


@pytest.mark.asyncio
async def test_chat_turn_preference_writes_profile_and_cognitive_fragment(db_session):
    user = User(
        username="profile_loop",
        email="profile_loop@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    redis = _RedisListCache()
    collector = ChatSignalCollector(redis)
    conversation_id = str(uuid4())

    await collector.collect_signals(
        user_id=user.id,
        user_message="以后请简洁一点，别太长。",
        ai_response="好的，我会更简洁。",
        conversation_id=conversation_id,
        turn_index=1,
        db_session=db_session,
    )

    prefs = await PreferenceService(db_session, redis).get_preferences(user.id)
    assert prefs.explicit["ai_verbosity"] == "concise"

    fragment = (
        await db_session.execute(
            select(CognitiveFragment).where(CognitiveFragment.user_id == user.id)
        )
    ).scalar_one()
    assert fragment.source_type == "behavior"
    assert fragment.context_tags["preference_keys"] == ["ai_verbosity"]
    embedding = (
        await db_session.execute(
            select(CognitiveFragment.embedding).where(CognitiveFragment.id == fragment.id)
        )
    ).scalar_one()
    assert embedding is None

    profile_context = await ProfileContextService(db_session, redis=None).get_profile_context(user.id)
    assert profile_context.preferences["ai_verbosity"] == "concise"


@pytest.mark.asyncio
async def test_chat_signal_window_marks_low_confidence_inferred_preferences_tentative(db_session):
    user = User(
        username="profile_loop_window",
        email="profile_loop_window@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    redis = _RedisListCache()
    collector = ChatSignalCollector(redis)
    conversation_id = str(uuid4())

    for index in range(1, collector.WINDOW_SIZE + 1):
        await collector.collect_signals(
            user_id=user.id,
            user_message=f"How do I solve this algebra practice problem number {index}?",
            ai_response="Try isolating the variable.",
            conversation_id=conversation_id,
            turn_index=index,
            db_session=db_session,
        )

    prefs = await PreferenceService(db_session, redis).get_preferences(user.id)
    inferred = dict(prefs.inferred or {})

    assert "avg_question_complexity" in inferred
    assert inferred["avg_question_complexity_status"] == "tentative"
    assert inferred["avg_question_complexity_confidence"] < 0.7

    cached = await redis.get(f"user:prefs:center:{user.id}")
    assert cached is not None
    assert json.loads(cached)["inferred"]["avg_question_complexity_status"] == "tentative"
