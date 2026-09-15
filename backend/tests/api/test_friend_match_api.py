from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.deps import get_current_user, get_db
from app.api.v1.community import router as community_router
from app.core.profile_context import (
    ActivePattern,
    CognitiveSummary,
    KnowledgeSummary,
    ProfileContext,
)
from app.models.community import Friendship, FriendshipStatus, Group, GroupMember, GroupRole, GroupType
from app.models.recommendation import UserItemInteraction
from app.models.user import SearchVisibility, User, UserStatus
from app.services.profile_context_service import ProfileContextService


def _make_user(
    *,
    username: str,
    searchable_by: SearchVisibility = SearchVisibility.EVERYONE,
    flame_level: int = 5,
    last_login_hours_ago: int = 4,
) -> User:
    suffix = uuid4().hex[:8]
    return User(
        username=f"{username}_{suffix}",
        email=f"{username}_{suffix}@example.com",
        hashed_password="hashed",
        password_login_enabled=True,
        nickname=username,
        registration_source="email",
        is_active=True,
        status=UserStatus.ONLINE,
        searchable_by=searchable_by,
        flame_level=flame_level,
        last_login_at=datetime.utcnow() - timedelta(hours=last_login_hours_ago),
    )


async def _commit_all(db_session, *objects):
    db_session.add_all(list(objects))
    await db_session.commit()
    for obj in objects:
        await db_session.refresh(obj)


def _profile_context(
    *,
    subjects: list[str],
    depth: float,
    curiosity: float,
    focus: int,
    learning_style: str = "balanced",
    feedback_style: str = "balanced",
    mastery: float = 0.5,
    pattern_name: str = "steady learner",
    pattern_type: str = "execution",
    risk_signals: list[str] | None = None,
) -> ProfileContext:
    return ProfileContext(
        preferences={
            "depth_preference": depth,
            "curiosity_preference": curiosity,
            "focus_duration_preference": focus,
            "learning_style": learning_style,
            "feedback_style": feedback_style,
        },
        preference_version=1,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=mastery,
            active_learning_subjects=subjects,
        ),
        cognitive_summary=CognitiveSummary(
            active_patterns=[
                ActivePattern(
                    pattern_name=pattern_name,
                    pattern_type=pattern_type,
                    confidence=0.85,
                    policy_signals=[],
                )
            ],
            dominant_pattern_type=pattern_type,
            risk_signals=risk_signals or [],
        ),
    )


@pytest_asyncio.fixture
async def friend_match_app(db_session, monkeypatch):
    app = FastAPI()
    app.include_router(community_router, prefix="/community")

    state = {"current_user": None, "contexts": {}}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    async def _fake_profile_context(self, user_id):
        return state["contexts"][str(user_id)]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    monkeypatch.setattr(ProfileContextService, "get_profile_context", _fake_profile_context)

    yield app, state

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_friend_recommendations_support_strategy_and_privacy_filter(
    friend_match_app,
    db_session,
):
    app, state = friend_match_app
    current = _make_user(username="current", flame_level=4)
    similar_friend = _make_user(username="similar_friend", flame_level=6, last_login_hours_ago=2)
    complementary_candidate = _make_user(username="complementary_candidate", flame_level=9, last_login_hours_ago=1)
    hidden_candidate = _make_user(
        username="hidden_candidate",
        searchable_by=SearchVisibility.NOBODY,
        flame_level=8,
        last_login_hours_ago=1,
    )
    await _commit_all(
        db_session,
        current,
        similar_friend,
        complementary_candidate,
        hidden_candidate,
    )
    friendship_pair = sorted(
        [str(current.id), str(similar_friend.id)],
    )

    friendship = Friendship(
        user_id=UUID(friendship_pair[0]),
        friend_id=UUID(friendship_pair[1]),
        initiated_by=current.id,
        status=FriendshipStatus.ACCEPTED,
    )
    group = Group(
        name="匹配测试群",
        description="test",
        type=GroupType.SQUAD,
        focus_tags=["算法", "数学"],
        is_public=True,
        max_members=20,
    )
    await _commit_all(db_session, friendship, group)
    await _commit_all(
        db_session,
        GroupMember(group_id=group.id, user_id=current.id, role=GroupRole.MEMBER),
        GroupMember(group_id=group.id, user_id=similar_friend.id, role=GroupRole.MEMBER),
    )

    state["current_user"] = current
    state["contexts"] = {
        str(current.id): _profile_context(
            subjects=["算法", "数学"],
            depth=0.72,
            curiosity=0.64,
            focus=32,
            mastery=0.46,
            pattern_name="steady learner",
            pattern_type="execution",
            risk_signals=["risk.planning_overrun"],
        ),
        str(similar_friend.id): _profile_context(
            subjects=["算法", "数学"],
            depth=0.75,
            curiosity=0.61,
            focus=30,
            mastery=0.49,
            pattern_name="steady learner",
            pattern_type="execution",
            risk_signals=["risk.planning_overrun"],
        ),
        str(complementary_candidate.id): _profile_context(
            subjects=["算法", "数学"],
            depth=0.9,
            curiosity=0.55,
            focus=42,
            mastery=0.78,
            pattern_name="disciplined finisher",
            pattern_type="planning",
            risk_signals=[],
        ),
        str(hidden_candidate.id): _profile_context(
            subjects=["算法", "数学"],
            depth=0.7,
            curiosity=0.6,
            focus=35,
            mastery=0.75,
            pattern_name="quiet achiever",
            pattern_type="execution",
            risk_signals=[],
        ),
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        compatibility = await client.get(
            "/community/friends/recommendations",
            params={"strategy": "compatibility", "target": "accountability", "limit": 5},
        )
        complementary = await client.get(
            "/community/friends/recommendations",
            params={"strategy": "complementary", "target": "accountability", "limit": 5},
        )

    assert compatibility.status_code == 200
    compatibility_payload = compatibility.json()
    assert compatibility_payload[0]["user"]["id"] == str(similar_friend.id)
    assert compatibility_payload[0]["is_existing_friend"] is True
    assert compatibility_payload[0]["can_invite_accountability"] is True
    assert compatibility_payload[0]["recommended_action"] == "invite_accountability"
    assert all(item["user"]["id"] != str(hidden_candidate.id) for item in compatibility_payload)

    assert complementary.status_code == 200
    complementary_payload = complementary.json()
    assert complementary_payload[0]["user"]["id"] == str(complementary_candidate.id)
    assert complementary_payload[0]["recommended_action"] == "send_friend_request"
    assert any("监督" in reason or "执行" in reason for reason in complementary_payload[0]["match_reasons"])


@pytest.mark.asyncio
async def test_friend_recommendation_feedback_is_recorded(
    friend_match_app,
    db_session,
):
    app, state = friend_match_app
    current = _make_user(username="feedback_owner")
    candidate = _make_user(username="feedback_candidate", flame_level=8)
    await _commit_all(db_session, current, candidate)
    state["current_user"] = current
    state["contexts"] = {
        str(current.id): _profile_context(
            subjects=["英语"],
            depth=0.4,
            curiosity=0.5,
            focus=18,
            mastery=0.35,
            pattern_name="delay pattern",
            pattern_type="execution",
            risk_signals=["risk.execution_delay"],
        ),
        str(candidate.id): _profile_context(
            subjects=["英语"],
            depth=0.82,
            curiosity=0.55,
            focus=40,
            mastery=0.76,
            pattern_name="steady finisher",
            pattern_type="planning",
            risk_signals=[],
        ),
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/community/friends/recommendations/feedback",
            json={
                "target_user_id": str(candidate.id),
                "strategy": "complementary",
                "target": "accountability",
                "action": "friend_request",
                "source": "friends_tab",
                "score": 0.91,
            },
        )

    assert response.status_code == 200
    result = await db_session.execute(select(UserItemInteraction))
    interaction = result.scalar_one()
    assert str(interaction.user_id) == str(current.id)
    assert str(interaction.item_id) == str(candidate.id)
    assert interaction.interaction_type == "friend_match_friend_request"
    assert interaction.meta["strategy"] == "complementary"
