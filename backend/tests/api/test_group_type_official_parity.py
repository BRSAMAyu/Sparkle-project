"""V3-FIX-289 回归：GroupType API 副本（schemas GroupTypeEnum）缺 official 的 500 面。

models 真源 GroupType 含 official（V3-FIX-266 修复面），mobile 侧已同步补；
backend API 副本 schemas/community.py GroupTypeEnum 修复前仅 squad/sprint，
api/v1/community.py /groups/search 与 /groups/directory 的
`GroupTypeEnum(group_dict["type"].value)` 转换点遇 official 群组直接
ValueError → 500。本测试构造 type=official 公开群组锁定两个端点面：
修前 500（红），修后 200 且 official 群组在结果内（绿）。
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_db
from app.api.v1.community import router as community_router
from app.models.community import Group, GroupMember, GroupRole, GroupType
from app.models.user import User
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
async def official_group_app(db_session, monkeypatch):
    app = FastAPI()
    app.include_router(community_router, prefix="/community")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    async def _fake_recommendations(*args, **kwargs):
        return []

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    monkeypatch.setattr(
        GroupRecommendationService,
        "get_recommendations",
        _fake_recommendations,
    )

    yield app, state
    app.dependency_overrides = {}


async def _create_official_group(db_session, *, owner: User, name: str) -> Group:
    now = datetime.utcnow()
    group = Group(
        name=name,
        description="官方课程同步群",
        type=GroupType.OFFICIAL,
        focus_tags=["课程"],
        total_flame_power=100,
        today_checkin_count=1,
        total_tasks_completed=3,
        max_members=50,
        is_public=True,
        join_requires_approval=False,
        created_at=now,
        updated_at=now,
    )
    await _commit_all(db_session, group)
    member = GroupMember(
        group_id=group.id,
        user_id=owner.id,
        role=GroupRole.OWNER,
        joined_at=now,
        last_active_at=now,
    )
    await _commit_all(db_session, member)
    return group


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    ["/community/groups/search", "/community/groups/directory"],
)
async def test_official_group_listed_without_500(official_group_app, db_session, path):
    app, state = official_group_app
    current_user = _make_user(username="viewer")
    owner = _make_user(username="official_owner")
    await _commit_all(db_session, current_user, owner)
    group = await _create_official_group(
        db_session, owner=owner, name="高数期末官方群"
    )

    state["current_user"] = current_user
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(path)

    assert response.status_code == 200, response.text
    payload = response.json()
    items = payload if isinstance(payload, list) else payload["groups"]
    official_items = [item for item in items if item["id"] == str(group.id)]
    assert official_items, f"official 群组必须出现在 {path} 结果内"
    assert official_items[0]["type"] == "official"
