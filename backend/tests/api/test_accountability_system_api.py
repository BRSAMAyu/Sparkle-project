from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
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
from app.core.cache import cache_service
from app.core.event_types import ACCOUNTABILITY_CHECKIN_CREATED, ACCOUNTABILITY_PARTNERSHIP_UPDATED
from app.models.accountability import (
    AccountabilityCheckin,
    AccountabilityPartnership,
    AccountabilitySlotType,
    AccountabilityStatus,
)
from app.models.cognitive import BehaviorPattern, CognitiveFragment
from app.models.community import (
    Friendship,
    FriendshipStatus,
    Group,
    GroupMember,
    GroupRole,
    GroupType,
    SharedResource,
    UserBlock,
)
from app.models.curiosity_capsule import CuriosityCapsule
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode
from app.models.group_files import GroupFile
from app.models.seed_content import SeedItem, SeedLibrary
from app.models.task import Task, TaskType
from app.models.user import User
from app.services.accountability_notification_service import (
    accountability_notification_service,
)
from app.services.notification_service import NotificationService
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

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
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


async def _create_task(
    db_session,
    *,
    user: User,
    title: str = "共享任务",
) -> Task:
    task = Task(
        user_id=user.id,
        title=title,
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=30,
        difficulty=1,
        energy_cost=1,
        priority=1,
    )
    await _commit_all(db_session, task)
    return task


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


@pytest.mark.asyncio
async def test_dashboard_returns_recent_shares_without_lazy_load_errors(
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
    shared_task = await _create_task(db_session, user=owner, title="一起完成演示彩排")
    shared_resource = SharedResource(
        shared_by=owner.id,
        target_user_id=partner.id,
        task_id=shared_task.id,
        comment="今晚一起过一遍",
    )
    await _commit_all(db_session, shared_resource)

    state["current_user"] = owner
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        dashboard = await client.get(f"/accountability/{partnership.id}/dashboard")

    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert len(payload["recent_shares"]) == 1
    assert payload["recent_shares"][0]["resource_type"] == "task"
    assert payload["recent_shares"][0]["title"] == "一起完成演示彩排"
    assert payload["recent_shares"][0]["comment"] == "今晚一起过一遍"


@pytest.mark.asyncio
async def test_send_friend_request_creates_notification_for_target(
    accountability_app,
    db_session,
    monkeypatch,
):
    app, state = accountability_app
    requester = _make_user(username="requester")
    target = _make_user(username="target")
    await _commit_all(db_session, requester, target)

    recorded: dict[str, object] = {}

    async def _fake_notification_create(db, user_id, obj_in, push_via_websocket=True):
        recorded["user_id"] = user_id
        recorded["title"] = obj_in.title
        recorded["content"] = obj_in.content
        recorded["type"] = obj_in.type
        recorded["data"] = obj_in.data
        return None

    monkeypatch.setattr(NotificationService, "create", staticmethod(_fake_notification_create))

    state["current_user"] = requester
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/community/friends/request",
            json={"target_user_id": str(target.id), "message": "一起学习吧"},
        )

    assert response.status_code == 200
    assert recorded["user_id"] == target.id
    assert recorded["title"] == "新的好友请求"
    assert recorded["type"] == "friend_request"
    assert recorded["data"]["from_user_id"] == str(requester.id)


@pytest.mark.asyncio
async def test_block_user_ends_partnership_and_hides_dashboard(
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

    state["current_user"] = owner
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        block_response = await client.post(
            "/community/users/block",
            json={"target_user_id": str(partner.id), "reason": "停止联系"},
        )
        dashboard_response = await client.get(f"/accountability/{partnership.id}/dashboard")

    await db_session.refresh(partnership)

    assert block_response.status_code == 200
    assert partnership.status == AccountabilityStatus.ENDED
    assert partnership.ended_at is not None
    assert dashboard_response.status_code == 403
    assert dashboard_response.json()["detail"] in {
        "Partnership access is no longer available",
        "Partnership is no longer active",
    }


@pytest.mark.asyncio
async def test_nudge_partner_rejects_when_block_relationship_exists(
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
    await _commit_all(
        db_session,
        UserBlock(blocker_id=partner.id, blocked_id=owner.id, reason="不再联系"),
    )

    state["current_user"] = owner
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/accountability/{partnership.id}/nudge",
            json={"message": "今天别忘了打卡"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Partnership access is no longer available"


@pytest.mark.asyncio
async def test_adopt_shared_resource_rejects_non_target_user(
    accountability_app,
    db_session,
):
    app, state = accountability_app
    owner = _make_user(username="owner")
    target = _make_user(username="target")
    intruder = _make_user(username="intruder")
    await _commit_all(db_session, owner, target, intruder)

    task = await _create_task(db_session, user=owner)
    shared = SharedResource(
        shared_by=owner.id,
        target_user_id=target.id,
        task_id=task.id,
        permission="view",
    )
    await _commit_all(db_session, shared)

    state["current_user"] = intruder
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(f"/community/shared-resources/{shared.id}/adopt")

    assert response.status_code == 403
    assert response.json()["detail"] == "无权采纳该共享资源"


@pytest.mark.asyncio
async def test_adopt_shared_resource_supports_extended_resource_types(
    accountability_app,
    db_session,
):
    app, state = accountability_app
    owner = _make_user(username="owner")
    target = _make_user(username="target")
    await _commit_all(db_session, owner, target)

    knowledge_node = KnowledgeNode(name="二叉树", description="树结构", importance_level=2)
    fragment = CognitiveFragment(
        user_id=owner.id,
        source_type="capsule",
        resource_type="text",
        content="注意力会在晚间下滑",
        severity=2,
    )
    capsule = CuriosityCapsule(
        user_id=owner.id,
        title="为什么树会退化",
        content="当插入顺序特殊时，树会退化成链表。",
        is_read=False,
    )
    library = SeedLibrary(
        name="算法例题库",
        description="常见算法题",
        category="few_shot",
        visibility="private",
        owner_id=owner.id,
        language="zh",
    )
    pattern = BehaviorPattern(
        user_id=owner.id,
        pattern_name="Planning Fallacy",
        pattern_type="cognitive",
        description="总是低估任务耗时",
    )
    db_session.add_all([knowledge_node, fragment, capsule, library, pattern])
    await db_session.flush()

    seed_item = SeedItem(
        library_id=library.id,
        item_type="example",
        title="双指针",
        content="用双指针缩小搜索区间",
        order_index=0,
        is_active=True,
    )
    db_session.add(seed_item)
    await db_session.flush()

    shared_resources = [
        SharedResource(shared_by=owner.id, target_user_id=target.id, knowledge_node_id=knowledge_node.id),
        SharedResource(shared_by=owner.id, target_user_id=target.id, cognitive_fragment_id=fragment.id),
        SharedResource(shared_by=owner.id, target_user_id=target.id, curiosity_capsule_id=capsule.id),
        SharedResource(shared_by=owner.id, target_user_id=target.id, seed_library_id=library.id),
        SharedResource(shared_by=owner.id, target_user_id=target.id, behavior_pattern_id=pattern.id),
    ]
    db_session.add_all(shared_resources)
    await db_session.commit()

    state["current_user"] = target
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        responses = [
            await client.post(f"/community/shared-resources/{shared_resources[0].id}/adopt"),
            await client.post(f"/community/shared-resources/{shared_resources[1].id}/adopt"),
            await client.post(f"/community/shared-resources/{shared_resources[2].id}/adopt"),
            await client.post(f"/community/shared-resources/{shared_resources[3].id}/adopt"),
            await client.post(f"/community/shared-resources/{shared_resources[4].id}/adopt"),
        ]

    for response in responses:
        assert response.status_code == 200
        assert response.json()["success"] is True

    assert responses[0].json()["resource_type"] == "knowledge_node"
    assert responses[1].json()["resource_type"] == "cognitive_fragment"
    assert responses[2].json()["resource_type"] == "curiosity_capsule"
    assert responses[3].json()["resource_type"] == "seed_library"
    assert responses[4].json()["resource_type"] == "cognitive_prism_pattern"

    cloned_library = await db_session.get(SeedLibrary, responses[3].json()["new_resource_id"])
    await db_session.refresh(cloned_library, attribute_names=["items"])
    assert cloned_library.owner_id == target.id
    assert len(list(cloned_library.items)) == 1


@pytest.mark.asyncio
async def test_update_group_file_permissions_rejects_non_admin_before_service(
    accountability_app,
    db_session,
    monkeypatch,
):
    app, state = accountability_app
    owner = _make_user(username="owner")
    member = _make_user(username="member")
    await _commit_all(db_session, owner, member)

    group = Group(name="文件权限测试群", type=GroupType.SQUAD, max_members=10)
    db_session.add(group)
    await db_session.flush()
    db_session.add_all(
        [
            GroupMember(group_id=group.id, user_id=owner.id, role=GroupRole.OWNER),
            GroupMember(group_id=group.id, user_id=member.id, role=GroupRole.MEMBER),
        ]
    )
    stored_file = StoredFile(
        user_id=owner.id,
        file_name="doc.txt",
        mime_type="text/plain",
        file_size=16,
        bucket="test",
        object_key=f"permissions-{uuid4()}",
        status="ready",
        visibility="group",
        retention_policy="keep",
    )
    db_session.add(stored_file)
    await db_session.flush()
    db_session.add(
        GroupFile(
            group_id=group.id,
            file_id=stored_file.id,
            shared_by_id=owner.id,
            category="notes",
            tags=["x"],
            view_role=GroupRole.MEMBER,
            download_role=GroupRole.MEMBER,
            manage_role=GroupRole.ADMIN,
        )
    )
    await db_session.commit()

    update_permissions = AsyncMock()
    monkeypatch.setattr(community_api.GroupFileService, "update_permissions", update_permissions)

    state["current_user"] = member
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.put(
            f"/community/groups/{group.id}/files/{stored_file.id}/permissions",
            json={
                "permissions": {
                    "view_role": "member",
                    "download_role": "member",
                    "manage_role": "admin",
                }
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "无权限修改群文件权限"
    update_permissions.assert_not_awaited()


@pytest.mark.asyncio
async def test_accountability_routes_publish_profile_refresh_events(
    accountability_app,
    db_session,
    monkeypatch,
):
    app, state = accountability_app
    publish = AsyncMock()
    monkeypatch.setattr(accountability_api.event_bus, "publish", publish)

    initiator = _make_user(username="initiator")
    partner = _make_user(username="partner")
    await _commit_all(db_session, initiator, partner)
    await _create_friendship(db_session, initiator, partner)

    state["current_user"] = initiator
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        request_response = await client.post(
            "/accountability/request",
            json={
                "partner_id": str(partner.id),
                "initiator_goal": "一起盯住考试周节奏",
                "check_in_days": 1,
            },
        )

    assert request_response.status_code == 201
    partnership_id = request_response.json()["id"]
    first_call = publish.await_args_list[0]
    assert first_call.args[0] == ACCOUNTABILITY_PARTNERSHIP_UPDATED
    assert set(first_call.args[1]["user_ids"]) == {str(initiator.id), str(partner.id)}
    assert first_call.args[1]["action"] == "requested"

    publish.reset_mock()
    state["current_user"] = partner
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        respond_response = await client.post(
            f"/accountability/{partnership_id}/respond",
            json={"accept": True, "partner_goal": "每天晚间互相确认进度"},
        )

    assert respond_response.status_code == 200
    second_call = publish.await_args_list[0]
    assert second_call.args[0] == ACCOUNTABILITY_PARTNERSHIP_UPDATED
    assert second_call.args[1]["action"] == "accepted"

    publish.reset_mock()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        checkin_response = await client.post(
            f"/accountability/{partnership_id}/checkin",
            json={"content": "今天完成了重点复盘", "mood": 4, "minutes": 35},
        )

    assert checkin_response.status_code == 201
    third_call = publish.await_args_list[0]
    assert third_call.args[0] == ACCOUNTABILITY_CHECKIN_CREATED
    assert third_call.args[1]["user_ids"] == [str(partner.id)]
    assert third_call.args[1]["action"] == "created"
    assert third_call.args[1]["partnership_id"] == partnership_id
