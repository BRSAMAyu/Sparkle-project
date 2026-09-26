"""V3-FIX-20: group discovery faces must exclude guest/seed cohort groups.

FIX-08 adjacent-face evidence (wt6 V3-FIX-08 REPORT §0): every public group in
the seeded DB (171) is owned by a guest/seed account and carries 350 fully
cohort messages, while real users discover groups through ``GET /groups/search``,
``GET /groups/directory`` and ``GET /groups/recommendations`` — none of which
had any cohort predicate (search_groups lived at community_service.py:461).

Two-user/two-group isolation probes (real sqlite DB): one email user owning a
real group vs one guest user owning a seed-styled public group. Before the fix
every discovery face surfaced the seed group (and its tags) to real users.

Boundary kept (documented, not regressed here): feed relational scopes
(squad/goal_mates/following) and in-group faces stay explicit-relationship per
FIX-08; a user's own joined groups stay visible in discovery faces (self
visibility parity with FIX-08 feed), via the my_role escape.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_db
from app.api.v1.community import router as community_router
from app.core.telemetry_boundary import EXCLUDED_COHORT_REGISTRATION_SOURCES
from app.models.community import (
    Group,
    GroupMember,
    GroupMessage,
    GroupRole,
    GroupType,
    MessageType,
)
from app.models.user import User
from app.services.community_service import GroupService
from app.services.group_recommendation_service import GroupRecommendationService

REAL_GROUP_NAME = "期末冲刺互助组"
SEED_GROUP_NAME = "算法冲刺小队"
SEED_ONLY_TAG = "种子独占标签"

# 假 DB（statement capture，FIX-07/08 家族手法）：只捕获语句不执行。


class _EmptyResult:
    def all(self):
        return []

    def first(self):
        return None

    def scalars(self):
        return self


class _StatementCaptureDB:
    def __init__(self):
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _EmptyResult()


def _bound_scalars(compiled) -> set:
    values: set = set()
    for value in (compiled.params or {}).values():
        if isinstance(value, (list, tuple, set)):
            values.update(value)
        else:
            values.add(value)
    return values


def _make_user(*, username: str, registration_source: str) -> User:
    suffix = uuid4().hex[:8]
    return User(
        username=f"{username}_{suffix}",
        email=f"{username}_{suffix}@example.com",
        hashed_password="hashed",
        password_login_enabled=True,
        nickname=username,
        registration_source=registration_source,
        is_active=True,
    )


async def _commit_all(db_session, *objects):
    db_session.add_all(list(objects))
    await db_session.commit()
    for obj in objects:
        await db_session.refresh(obj)


async def _create_group(
    db_session,
    *,
    owner: User,
    name: str,
    tags: list[str],
    description: str = "探针群组",
) -> Group:
    group = Group(
        name=name,
        description=description,
        type=GroupType.SQUAD,
        focus_tags=tags,
        total_flame_power=900,
        today_checkin_count=6,
        total_tasks_completed=12,
        max_members=50,
        is_public=True,
        join_requires_approval=False,
    )
    await _commit_all(db_session, group)
    member = GroupMember(
        group_id=group.id,
        user_id=owner.id,
        role=GroupRole.OWNER,
    )
    message = GroupMessage(
        group_id=group.id,
        sender_id=owner.id,
        message_type=MessageType.TEXT,
        content="种子群广播消息",
    )
    await _commit_all(db_session, member, message)
    return group


@pytest_asyncio.fixture
async def discovery_app(db_session):
    app = FastAPI()
    app.include_router(community_router, prefix="/community")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    yield app, state
    app.dependency_overrides = {}


@pytest_asyncio.fixture
async def two_users_two_groups(db_session):
    """两用户/两群隔离探针布景：email 群主 + guest 群主，各持一个公开群。"""
    real_owner = _make_user(username="real_owner", registration_source="email")
    guest_owner = _make_user(username="guest_owner", registration_source="guest")
    await _commit_all(db_session, real_owner, guest_owner)

    real_group = await _create_group(
        db_session,
        owner=real_owner,
        name=REAL_GROUP_NAME,
        tags=["期末", "冲刺"],
    )
    seed_group = await _create_group(
        db_session,
        owner=guest_owner,
        name=SEED_GROUP_NAME,
        tags=["算法", SEED_ONLY_TAG],
        description="种子内容：一起冲刺算法与数据结构的学习群",
    )
    return real_owner, seed_group, real_group


# ── 行为探针：污染实录（修前全红） ──


@pytest.mark.asyncio
async def test_group_search_hides_seed_cohort_group(discovery_app, db_session, two_users_two_groups):
    app, state = discovery_app
    real_owner, seed_group, _ = two_users_two_groups
    state["current_user"] = real_owner

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/community/groups/search")

    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert names == {REAL_GROUP_NAME}, f"群搜索面把 guest/seed 群暴露给真实用户（V3-FIX-20）：{names}"
    assert str(seed_group.id) not in {item["id"] for item in response.json()}


@pytest.mark.asyncio
async def test_group_directory_excludes_seed_group_and_tags(discovery_app, db_session, two_users_two_groups):
    app, state = discovery_app
    real_owner, _, _ = two_users_two_groups
    state["current_user"] = real_owner

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/community/groups/directory")

    assert response.status_code == 200
    payload = response.json()
    names = {item["name"] for item in payload["groups"]}
    assert names == {REAL_GROUP_NAME}, f"群目录面把 guest/seed 群暴露给真实用户（V3-FIX-20）：{names}"
    assert payload["total_count"] == 1
    assert SEED_ONLY_TAG not in payload["available_tags"], "群目录标签云混入 seed 群标签（V3-FIX-20）"


@pytest.mark.asyncio
async def test_group_recommendations_exclude_seed_group(db_session, two_users_two_groups):
    real_owner, seed_group, real_group = two_users_two_groups

    # 群主视角：自己的群不进召回（既有语义），种子群更不得进。
    owner_recommendations = await GroupRecommendationService.get_recommendations(
        db_session, real_owner.id, limit=10, cursor=0
    )
    owner_ids = {item.group.id for item in owner_recommendations}
    assert seed_group.id not in owner_ids, "群推荐面把 guest/seed 群推给真实用户（V3-FIX-20）"
    assert real_group.id not in owner_ids  # 自己的群不推荐（既有语义钉）

    # 另一真实用户（两群皆非成员）：只应被推荐真实群，不得被推荐种子群。
    other_real = _make_user(username="other_reco", registration_source="email")
    await _commit_all(db_session, other_real)
    recommendations = await GroupRecommendationService.get_recommendations(
        db_session, other_real.id, limit=10, cursor=0
    )
    recommended_ids = {item.group.id for item in recommendations}
    assert seed_group.id not in recommended_ids, "群推荐面把 guest/seed 群推给真实用户（V3-FIX-20）"
    assert real_group.id in recommended_ids


@pytest.mark.asyncio
async def test_public_group_count_and_tags_service_level(db_session, two_users_two_groups):
    real_owner, seed_group, _ = two_users_two_groups

    count = await GroupService.count_public_groups(db_session)
    assert count == 1, f"公开群计数混入 guest/seed 群（V3-FIX-20）：count={count}"

    tags = await GroupService.get_public_group_tags(db_session)
    assert SEED_ONLY_TAG not in tags

    found = await GroupService.search_groups(db_session, keyword="算法", user_id=real_owner.id)
    assert all(group["id"] != seed_group.id for group in found)


# ── 本人所在群豁免（与 FIX-08「本人帖始终可见」同形） ──


@pytest.mark.asyncio
async def test_own_membership_stays_visible_but_not_to_other_real_users(
    discovery_app, db_session, two_users_two_groups
):
    app, state = discovery_app
    real_owner, seed_group, _ = two_users_two_groups

    # 真实用户此前加入了种子群（存量成员）。
    membership = GroupMember(
        group_id=seed_group.id,
        user_id=real_owner.id,
        role=GroupRole.MEMBER,
    )
    await _commit_all(db_session, membership)

    # 本人：所在群仍在发现面可见（my_role 豁免）。
    state["current_user"] = real_owner
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        own_response = await client.get("/community/groups/search")
    own_names = {item["name"] for item in own_response.json()}
    assert SEED_GROUP_NAME in own_names
    own_row = next(item for item in own_response.json() if item["name"] == SEED_GROUP_NAME)
    assert own_row["my_role"] == "member"

    # 另一真实用户（非成员）：种子群必须不可见。
    other_real = _make_user(username="other_real", registration_source="email")
    await _commit_all(db_session, other_real)
    state["current_user"] = other_real
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        other_response = await client.get("/community/groups/search")
    other_names = {item["name"] for item in other_response.json()}
    assert SEED_GROUP_NAME not in other_names, "种子群对非成员真实用户仍然可见（V3-FIX-20 污染）"


# ── 谓词钉测（statement capture，FIX-07/08 家族形制） ──


@pytest.mark.asyncio
async def test_search_groups_query_carries_cohort_predicate():
    db = _StatementCaptureDB()

    await GroupService.search_groups(db, keyword="算法", user_id=uuid4())

    assert len(db.statements) == 1
    compiled = db.statements[0].compile()
    sql = str(compiled).upper()
    assert "FROM GROUPS" in sql
    assert "REGISTRATION_SOURCE" in sql, "search_groups 无 cohort 谓词——guest/seed 群暴露给真实用户（V3-FIX-20）"
    assert "NOT" in sql and "EXISTS" in sql
    assert {"guest", "seed"}.issubset(_bound_scalars(compiled))
    # 本人所在群豁免：OR + my_role IS NOT NULL。
    assert "OR" in sql and "MY_ROLE" in sql


def test_cohort_vocabulary_shared_constant():
    assert EXCLUDED_COHORT_REGISTRATION_SOURCES == ("guest", "seed")
