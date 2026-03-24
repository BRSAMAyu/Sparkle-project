from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_db
from app.api.v1 import accountability as accountability_api
from app.api.v1 import community as community_api
from app.api.v1.accountability import router as accountability_router
from app.api.v1.community import router as community_router
from app.api.v1.profile_transparency import router as profile_router
from app.api.v1 import profile_transparency as profile_api
from app.core.cache import cache_service
from app.models.accountability import (
    AccountabilityCheckin,
    AccountabilityPartnership,
    AccountabilitySlotType,
    AccountabilityStatus,
)
from app.models.community import Friendship, FriendshipStatus
from app.models.user import User
from app.services.accountability_notification_service import (
    accountability_notification_service,
)
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_context_service import ProfileContextService


def _make_user(*, username: str) -> User:
    suffix = uuid4().hex[:8]
    return User(
        username=f"{username}_{suffix}",
        email=f"{username}_{suffix}@example.com",
        hashed_password="hashed",
        password_login_enabled=True,
        nickname=username,
        registration_source="email",
        is_active=True,
    )


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def setex(self, key: str, _: int, value: str) -> None:
        self._store[key] = value


class _DummyProfileContext:
    def to_prompt_context(self) -> dict:
        return {
            "knowledge_summary": {},
            "cognitive_summary": {},
            "preferences": {},
        }


@pytest_asyncio.fixture
async def accountability_app(db_session, monkeypatch):
    app = FastAPI()
    app.include_router(accountability_router, prefix="/accountability")
    app.include_router(community_router, prefix="/community")
    app.include_router(profile_router)

    state = {"current_user": None}
    fake_redis = _FakeRedis()

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    async def _noop_notification(*args, **kwargs):
        return None

    async def _fake_leaderboard_summary(*args, **kwargs):
        return {
            "friends": {"title": "好友榜", "my_rank": 3, "partner_rank": 1},
            "weekly": {"title": "本周进步榜", "my_rank": 4, "partner_rank": 2},
            "streak": {"title": "连续打卡榜", "my_rank": 5, "partner_rank": 2},
        }

    async def _fake_achievement_payload(*args, **kwargs):
        return {
            "achievements": [],
            "my_achievements": [],
            "partner_achievements": [],
            "my_total_unlocked": 1,
            "partner_total_unlocked": 1,
        }

    async def _fake_profile_context(self, user_id):
        return _DummyProfileContext()

    async def _fake_preferences(self, user_id):
        return SimpleNamespace(
            explicit={"timezone": "Asia/Shanghai"},
            inferred={},
            version=1,
        )

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    monkeypatch.setattr(
        accountability_notification_service,
        "send_partner_request",
        _noop_notification,
    )
    monkeypatch.setattr(
        accountability_notification_service,
        "send_partner_accepted",
        _noop_notification,
    )
    monkeypatch.setattr(
        accountability_notification_service,
        "send_partner_declined",
        _noop_notification,
    )
    monkeypatch.setattr(
        accountability_notification_service,
        "send_manual_nudge",
        _noop_notification,
    )
    monkeypatch.setattr(
        accountability_api,
        "_build_leaderboard_summary",
        _fake_leaderboard_summary,
    )
    monkeypatch.setattr(
        community_api,
        "_build_leaderboard_summary",
        _fake_leaderboard_summary,
    )
    monkeypatch.setattr(
        accountability_api,
        "_build_partnership_achievements_payload",
        _fake_achievement_payload,
    )
    monkeypatch.setattr(
        community_api,
        "_build_partnership_achievements_payload",
        _fake_achievement_payload,
    )
    monkeypatch.setattr(ProfileContextService, "get_profile_context", _fake_profile_context)
    monkeypatch.setattr(PreferenceService, "get_preferences", _fake_preferences)
    monkeypatch.setattr(cache_service, "redis", fake_redis)

    yield app, state

    app.dependency_overrides = {}


async def _commit_all(db_session, *objects):
    db_session.add_all(list(objects))
    await db_session.commit()
    for obj in objects:
        await db_session.refresh(obj)


async def _create_friendship(db_session, user_a: User, user_b: User) -> Friendship:
    friendship = Friendship(
        user_id=user_a.id,
        friend_id=user_b.id,
        initiated_by=user_a.id,
        status=FriendshipStatus.ACCEPTED,
    )
    await _commit_all(db_session, friendship)
    return friendship


async def _create_partnership(
    db_session,
    *,
    initiator: User,
    partner: User,
    friendship: Friendship | None,
    status: AccountabilityStatus,
    initiator_goal: str = "每天完成重点任务",
    partner_goal: str | None = "每天复盘并反馈",
) -> AccountabilityPartnership:
    partnership = AccountabilityPartnership(
        initiator_id=initiator.id,
        partner_id=partner.id,
        friendship_id=friendship.id if friendship else None,
        initiator_goal=initiator_goal,
        partner_goal=partner_goal,
        check_in_days=1,
        slot_type=AccountabilitySlotType.CORE,
        status=status,
        started_at=datetime.utcnow() - timedelta(days=5)
        if status == AccountabilityStatus.ACTIVE
        else None,
        created_at=datetime.utcnow() - timedelta(days=5),
    )
    await _commit_all(db_session, partnership)
    return partnership


async def _create_checkin(
    db_session,
    *,
    partnership: AccountabilityPartnership,
    user: User,
    content: str,
    created_at: datetime,
) -> AccountabilityCheckin:
    checkin = AccountabilityCheckin(
        partnership_id=partnership.id,
        user_id=user.id,
        content=content,
        mood=4,
        minutes=45,
        likes=0,
        liked_by=[],
        encouragements=[],
        created_at=created_at,
    )
    await _commit_all(db_session, checkin)
    return checkin


@pytest.mark.asyncio
async def test_request_partnership_rejects_when_user_already_has_core_partner(
    accountability_app,
    db_session,
):
    app, state = accountability_app
    owner = _make_user(username="owner")
    active_partner = _make_user(username="active_partner")
    candidate = _make_user(username="candidate")
    await _commit_all(db_session, owner, active_partner, candidate)

    active_friendship = await _create_friendship(db_session, owner, active_partner)
    await _create_friendship(db_session, owner, candidate)
    await _create_partnership(
        db_session,
        initiator=owner,
        partner=active_partner,
        friendship=active_friendship,
        status=AccountabilityStatus.ACTIVE,
    )

    state["current_user"] = owner
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/accountability/request",
            json={
                "partner_id": str(candidate.id),
                "initiator_goal": "希望再拉一个责任伙伴",
                "check_in_days": 1,
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "One of the users already has a core accountability partner"


@pytest.mark.asyncio
async def test_accept_partnership_rejects_when_invited_user_already_has_core_partner(
    accountability_app,
    db_session,
):
    app, state = accountability_app
    inviter = _make_user(username="inviter")
    invitee = _make_user(username="invitee")
    existing_partner = _make_user(username="existing_partner")
    await _commit_all(db_session, inviter, invitee, existing_partner)

    pending_friendship = await _create_friendship(db_session, inviter, invitee)
    existing_friendship = await _create_friendship(db_session, invitee, existing_partner)
    pending = await _create_partnership(
        db_session,
        initiator=inviter,
        partner=invitee,
        friendship=pending_friendship,
        status=AccountabilityStatus.PENDING,
        partner_goal=None,
    )
    await _create_partnership(
        db_session,
        initiator=invitee,
        partner=existing_partner,
        friendship=existing_friendship,
        status=AccountabilityStatus.ACTIVE,
    )

    state["current_user"] = invitee
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/accountability/{pending.id}/respond",
            json={"accept": True, "partner_goal": "我也会每天反馈"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "One of the users already has a core accountability partner"


@pytest.mark.asyncio
async def test_friends_endpoint_enriches_and_sorts_accountability_relationships(
    accountability_app,
    db_session,
):
    app, state = accountability_app
    owner = _make_user(username="owner")
    active_partner = _make_user(username="active_partner")
    pending_partner = _make_user(username="pending_partner")
    plain_friend = _make_user(username="plain_friend")
    await _commit_all(db_session, owner, active_partner, pending_partner, plain_friend)

    active_friendship = await _create_friendship(db_session, owner, active_partner)
    pending_friendship = await _create_friendship(db_session, owner, pending_partner)
    await _create_friendship(db_session, owner, plain_friend)

    active_partnership = await _create_partnership(
        db_session,
        initiator=owner,
        partner=active_partner,
        friendship=active_friendship,
        status=AccountabilityStatus.ACTIVE,
    )
    await _create_partnership(
        db_session,
        initiator=owner,
        partner=pending_partner,
        friendship=pending_friendship,
        status=AccountabilityStatus.PENDING,
        partner_goal=None,
    )

    now = datetime.utcnow()
    await _create_checkin(
        db_session,
        partnership=active_partnership,
        user=owner,
        content="我完成了今日任务",
        created_at=now - timedelta(hours=2),
    )
    await _create_checkin(
        db_session,
        partnership=active_partnership,
        user=active_partner,
        content="我也完成了复盘",
        created_at=now - timedelta(hours=1),
    )

    state["current_user"] = owner
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/community/friends")

    assert response.status_code == 200
    payload = response.json()

    assert payload[0]["friend"]["id"] == str(active_partner.id)
    assert payload[0]["accountability"]["partnership_id"] == str(active_partnership.id)
    assert payload[0]["accountability"]["slot_type"] == "core"
    assert payload[0]["accountability"]["status"] == "active"

    assert payload[1]["friend"]["id"] == str(pending_partner.id)
    assert payload[1]["accountability"]["status"] == "pending"

    assert payload[2]["friend"]["id"] == str(plain_friend.id)
    assert payload[2]["accountability"] is None


@pytest.mark.asyncio
async def test_overview_dashboard_nudge_friend_profile_and_context_are_populated(
    accountability_app,
    db_session,
):
    app, state = accountability_app
    owner = _make_user(username="owner")
    partner = _make_user(username="partner")
    await _commit_all(db_session, owner, partner)

    friendship = await _create_friendship(db_session, owner, partner)
    partnership = await _create_partnership(
        db_session,
        initiator=owner,
        partner=partner,
        friendship=friendship,
        status=AccountabilityStatus.ACTIVE,
    )

    now = datetime.utcnow()
    await _create_checkin(
        db_session,
        partnership=partnership,
        user=owner,
        content="完成了英语精读",
        created_at=now - timedelta(hours=3),
    )
    await _create_checkin(
        db_session,
        partnership=partnership,
        user=partner,
        content="做了错题复盘",
        created_at=now - timedelta(hours=1),
    )

    state["current_user"] = owner
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        overview = await client.get("/accountability/overview")
        dashboard = await client.get(f"/accountability/{partnership.id}/dashboard")
        friend_profile = await client.get(f"/community/friends/{partner.id}/profile")
        first_nudge = await client.post(
            f"/accountability/{partnership.id}/nudge",
            json={"message": "今晚一起收尾"},
        )
        second_nudge = await client.post(
            f"/accountability/{partnership.id}/nudge",
            json={"message": "再次提醒"},
        )
        context = await client.get("/profile/context")

    assert overview.status_code == 200
    overview_payload = overview.json()
    assert overview_payload["slot_type"] == "core"
    assert overview_payload["active_partnership"]["id"] == str(partnership.id)
    assert overview_payload["relationship_summary"]["slot_type"] == "core"

    assert dashboard.status_code == 200
    dashboard_payload = dashboard.json()
    assert dashboard_payload["partnership"]["id"] == str(partnership.id)
    assert dashboard_payload["stats"]["total_checkins"] == 2
    assert len(dashboard_payload["timeline"]) == 2
    assert dashboard_payload["quick_actions"]["can_open_dashboard"] is True

    assert friend_profile.status_code == 200
    friend_profile_payload = friend_profile.json()
    assert friend_profile_payload["user"]["id"] == str(partner.id)
    assert friend_profile_payload["accountability"]["id"] == str(partnership.id)
    assert friend_profile_payload["relationship_summary"]["slot_type"] == "core"
    assert friend_profile_payload["quick_actions"]["can_open_dashboard"] is True

    assert first_nudge.status_code == 200
    assert first_nudge.json()["success"] is True
    assert second_nudge.status_code == 429
    assert second_nudge.json()["detail"] == "Nudge cooldown is still active"

    assert context.status_code == 200
    context_payload = context.json()
    assert context_payload["accountability_summary"]["has_core_partner"] is True
    assert context_payload["accountability_summary"]["slot_type"] == "core"
