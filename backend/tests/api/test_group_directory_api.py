from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_db
from app.api.v1.community import router as community_router
from app.models.community import (
    Group,
    GroupMember,
    GroupMessage,
    GroupRole,
    GroupType,
    MessageType,
)
from app.models.user import User
from app.schemas.community import (
    GroupListItem,
    GroupRecommendationItem,
    GroupRecommendationReason,
    GroupTypeEnum,
)
from app.services.group_recommendation_service import GroupRecommendationService


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


async def _commit_all(db_session, *objects):
    db_session.add_all(list(objects))
    await db_session.commit()
    for obj in objects:
        await db_session.refresh(obj)


@pytest_asyncio.fixture
async def community_directory_app(db_session, monkeypatch):
    app = FastAPI()
    app.include_router(community_router, prefix="/community")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    async def _fake_recommendations(*args, **kwargs):
        return [
            GroupRecommendationItem(
                group=GroupListItem(
                    id=uuid4(),
                    name="推荐刷题小队",
                    description="根据你的学习兴趣推荐的冲刺群",
                    type=GroupTypeEnum.SQUAD,
                    member_count=18,
                    total_flame_power=3200,
                    today_checkin_count=9,
                    deadline=None,
                    days_remaining=None,
                    focus_tags=["算法", "LeetCode"],
                    join_requires_approval=False,
                    is_public=True,
                ),
                score=0.88,
                reasons=[
                    GroupRecommendationReason(
                        type="tag_overlap",
                        data={"tags": ["算法", "LeetCode"]},
                    ),
                ],
                requires_approval=False,
            )
        ]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    monkeypatch.setattr(
        GroupRecommendationService,
        "get_recommendations",
        _fake_recommendations,
    )

    yield app, state

    app.dependency_overrides = {}


async def _create_group(
    db_session,
    *,
    owner: User,
    name: str,
    description: str,
    tags: list[str],
    created_at: datetime,
    updated_at: datetime,
    total_flame_power: int,
    today_checkin_count: int,
    member_count: int,
) -> Group:
    group = Group(
        name=name,
        description=description,
        type=GroupType.SQUAD,
        focus_tags=tags,
        total_flame_power=total_flame_power,
        today_checkin_count=today_checkin_count,
        total_tasks_completed=member_count * 3,
        max_members=50,
        is_public=True,
        join_requires_approval=False,
        created_at=created_at,
        updated_at=updated_at,
    )
    await _commit_all(db_session, group)

    members = [
        GroupMember(
            group_id=group.id,
            user_id=owner.id,
            role=GroupRole.OWNER,
            joined_at=created_at,
            last_active_at=updated_at,
        )
    ]
    for _ in range(max(member_count - 1, 0)):
        filler = _make_user(username=f"member_{uuid4().hex[:6]}")
        db_session.add(filler)
        await db_session.flush()
        members.append(
            GroupMember(
                group_id=group.id,
                user_id=filler.id,
                role=GroupRole.MEMBER,
                joined_at=created_at,
                last_active_at=updated_at,
            )
        )
    await _commit_all(db_session, *members)
    return group


@pytest.mark.asyncio
async def test_group_directory_returns_recommendations_and_browse_data(
    community_directory_app,
    db_session,
):
    app, state = community_directory_app
    current_user = _make_user(username="current_user")
    owner = _make_user(username="owner")
    await _commit_all(db_session, current_user, owner)

    now = datetime.utcnow()
    hot_group = await _create_group(
        db_session,
        owner=owner,
        name="算法晨练社",
        description="每天早晨一起刷算法题和复盘。",
        tags=["算法", "LeetCode", "面试"],
        created_at=now - timedelta(days=10),
        updated_at=now - timedelta(hours=1),
        total_flame_power=6400,
        today_checkin_count=16,
        member_count=8,
    )
    latest_group = await _create_group(
        db_session,
        owner=owner,
        name="大学物理互助会",
        description="期中前一起整理重点和题单。",
        tags=["物理", "期中"],
        created_at=now - timedelta(days=2),
        updated_at=now - timedelta(minutes=20),
        total_flame_power=1200,
        today_checkin_count=3,
        member_count=4,
    )
    joined_member = GroupMember(
        group_id=hot_group.id,
        user_id=current_user.id,
        role=GroupRole.MEMBER,
        joined_at=now - timedelta(days=5),
        last_active_at=now - timedelta(hours=2),
    )
    message = GroupMessage(
        group_id=hot_group.id,
        sender_id=owner.id,
        message_type=MessageType.TEXT,
        content="今晚继续冲题单",
        created_at=now - timedelta(days=1),
    )
    await _commit_all(db_session, joined_member, message)

    state["current_user"] = current_user
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/community/groups/directory")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sort_by"] == "hot"
    assert payload["total_count"] == 2
    assert payload["recommendations"][0]["group"]["name"] == "推荐刷题小队"
    assert "算法" in payload["available_tags"]
    assert payload["groups"][0]["name"] == "算法晨练社"
    assert payload["groups"][0]["description"] == "每天早晨一起刷算法题和复盘。"
    assert payload["groups"][0]["my_role"] == "member"
    assert payload["groups"][0]["today_checkin_count"] == 16
    assert latest_group.name in [group["name"] for group in payload["groups"]]


@pytest.mark.asyncio
async def test_group_search_supports_sort_filters_and_membership_state(
    community_directory_app,
    db_session,
):
    app, state = community_directory_app
    current_user = _make_user(username="searcher")
    owner = _make_user(username="owner_search")
    await _commit_all(db_session, current_user, owner)

    now = datetime.utcnow()
    hot_group = await _create_group(
        db_session,
        owner=owner,
        name="高数火力营",
        description="高数刷题和错题讨论。",
        tags=["数学", "高数"],
        created_at=now - timedelta(days=12),
        updated_at=now - timedelta(hours=1),
        total_flame_power=7200,
        today_checkin_count=18,
        member_count=10,
    )
    latest_group = await _create_group(
        db_session,
        owner=owner,
        name="高数新生社",
        description="刚开的高数入门社群。",
        tags=["数学", "入门"],
        created_at=now - timedelta(hours=6),
        updated_at=now - timedelta(hours=1),
        total_flame_power=300,
        today_checkin_count=1,
        member_count=2,
    )
    joined_member = GroupMember(
        group_id=hot_group.id,
        user_id=current_user.id,
        role=GroupRole.ADMIN,
        joined_at=now - timedelta(days=3),
        last_active_at=now - timedelta(hours=1),
    )
    hot_message = GroupMessage(
        group_id=hot_group.id,
        sender_id=owner.id,
        message_type=MessageType.TEXT,
        content="今天继续讲拉格朗日中值定理",
        created_at=now - timedelta(hours=8),
    )
    await _commit_all(db_session, joined_member, hot_message)

    state["current_user"] = current_user
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        hot_response = await client.get("/community/groups/search", params={"sort_by": "hot"})
        latest_response = await client.get(
            "/community/groups/search",
            params={"keyword": "高数", "sort_by": "latest"},
        )
        random_response = await client.get(
            "/community/groups/directory",
            params={"sort_by": "random", "keyword": "高数"},
        )

    assert hot_response.status_code == 200
    hot_payload = hot_response.json()
    assert hot_payload[0]["id"] == str(hot_group.id)
    assert hot_payload[0]["my_role"] == "admin"
    assert hot_payload[0]["activity_score"] > hot_payload[1]["activity_score"]

    assert latest_response.status_code == 200
    latest_payload = latest_response.json()
    assert latest_payload[0]["id"] == str(latest_group.id)
    assert {item["name"] for item in latest_payload} == {"高数火力营", "高数新生社"}

    assert random_response.status_code == 200
    random_payload = random_response.json()
    assert random_payload["sort_by"] == "random"
    assert random_payload["total_count"] == 2
