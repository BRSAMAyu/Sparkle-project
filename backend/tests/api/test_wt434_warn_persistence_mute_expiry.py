"""V3-FIX-116/117 · 社区通知双 P2（wt424 审查轮 CONFIRMED）.

- V3-FIX-116：warn_group_member 的「warned」WS 推送是被警告用户唯一告知通道，
  wt420 best-effort 化后推送失败=警告静默丢失且不可补偿（warn_member 全文无
  第二写点）。修=警告事实持久化（notifications 通知中心行，与警告同事务提交，
  仓内既有通知真源），WS 推送保持 best-effort（不再回 500）。
- V3-FIX-117：is_muted 无到期解除——mute_until 只写不比、无到期 job，禁言实际
  永久且与 mute 推送载荷「禁言至 X」语义相反。修=执行点读面改为
  ``muted AND (mute_until IS NULL OR mute_until > now)``（最诚实最小修）。

红测口径（base 上红）：
- FIX-116：WS 推送通道全断后 warn 仍 200（wt420 已保），但被警告用户侧必须
  存在可查询的警告 artifact（notifications 行）——base 无任何持久化（红）。
- FIX-117：三形态——mute_until 过期后发言恢复（base 仍拒：红）、未过期仍拒
  （守卫形态）、无 mute_until 永久（守卫形态）。
"""

from __future__ import annotations

import uuid as uuid_mod
from datetime import timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_db
from app.core.datetime_utils import _utcnow
from app.core.websocket import manager as global_ws_manager
from app.models.base import Base
from app.models.community import Group, GroupMember, GroupRole, GroupType
from app.models.notification import Notification
from app.models.user import User

COMMUNITY_PREFIX = "/api/v1/community"


class _Env:
    def __init__(self, db: AsyncSession, app: FastAPI, current: dict):
        self.db = db
        self.app = app
        self.current = current

    async def client(self) -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=self.app, raise_app_exceptions=False), base_url="http://test")


@pytest.fixture(name="warn_env")
async def warn_env_fixture():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        from app.api.v1.community import router as community_router

        app = FastAPI()
        app.include_router(community_router, prefix=COMMUNITY_PREFIX)

        current: dict = {"user": None}

        async def _override_get_db():
            yield db

        async def _override_get_current_user():
            return current["user"]

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_current_user] = _override_get_current_user

        yield _Env(db, app, current)

        app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture(name="failing_ws_manager")
def failing_ws_manager_fixture(monkeypatch: pytest.MonkeyPatch):
    """WS 推送通道全断（Redis 瞬断等价面）：私信推送一律抛 ConnectionError。"""
    mgr = global_ws_manager
    mgr.redis = None
    mgr.pubsub = None
    mgr.active_connections.clear()
    mgr.user_connections.clear()

    def _boom(*args, **kwargs):  # noqa: ANN002, ANN003
        raise ConnectionError("simulated redis outage (V3-FIX-116 warn persistence)")

    monkeypatch.setattr(mgr, "broadcast", _boom)
    monkeypatch.setattr(mgr, "send_personal_message", _boom)
    yield mgr
    mgr.active_connections.clear()
    mgr.user_connections.clear()
    mgr.redis = None
    mgr.pubsub = None


async def _make_user(db: AsyncSession, prefix: str) -> User:
    user = User(
        username=f"{prefix}_{uuid_mod.uuid4().hex[:10]}",
        email=f"{prefix}_{uuid_mod.uuid4().hex[:10]}@t.example",
        hashed_password="x",
        photon_balance=0,
    )
    db.add(user)
    await db.commit()
    return user


async def _make_group_with_member(db: AsyncSession, owner: User, member: User | None = None) -> Group:
    group = Group(
        name=f"grp_{uuid_mod.uuid4().hex[:8]}",
        type=GroupType.SQUAD,
        focus_tags=[],
    )
    db.add(group)
    await db.flush()
    db.add(GroupMember(group_id=group.id, user_id=owner.id, role=GroupRole.OWNER))
    if member is not None:
        db.add(GroupMember(group_id=group.id, user_id=member.id, role=GroupRole.MEMBER))
    await db.commit()
    return group


async def _mute_member(db: AsyncSession, group: Group, member: User) -> None:
    """直接置位禁言（服务层同形：is_muted=True + mute_until=now+30min）。"""
    result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group.id, GroupMember.user_id == member.id)
    )
    row = result.scalar_one()
    row.is_muted = True
    row.mute_until = _utcnow() + timedelta(minutes=30)
    await db.commit()


async def _get_member(db: AsyncSession, group: Group, member: User) -> GroupMember:
    result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group.id, GroupMember.user_id == member.id)
    )
    return result.scalar_one()


# --- V3-FIX-116：warn 推送失败后警告 artifact 必须可查询 ---------------------------


@pytest.mark.asyncio
async def test_warn_push_failure_still_persists_notification(
    warn_env: _Env, failing_ws_manager  # noqa: ARG001
) -> None:
    """推送通道全断：warn 仍 200（wt420 best-effort 保留），且被警告用户侧
    必须有可查询的警告 artifact（notifications 行，含 group/reason/warn_count）。"""
    owner = await _make_user(warn_env.db, "wpowner")
    target = await _make_user(warn_env.db, "wptarget")
    group = await _make_group_with_member(warn_env.db, owner, target)

    warn_env.current["user"] = owner
    async with await warn_env.client() as client:
        resp = await client.post(
            f"{COMMUNITY_PREFIX}/groups/{group.id}/members/{target.id}/warn",
            json={"user_id": str(target.id), "reason": "刷屏警告红测"},
        )

    assert (
        resp.status_code == 200
    ), f"warn 推送失败必须 best-effort（wt420 已保），实际 {resp.status_code}: {resp.text[:200]}"
    warn_count = resp.json().get("warn_count")
    assert warn_count == 1, f"warn_count 必须返回，实际 {resp.json()}"

    # 可证伪判据：被警告用户侧存在可查询的警告 artifact
    rows = (await warn_env.db.execute(select(Notification).where(Notification.user_id == target.id))).scalars().all()
    assert rows, "推送失败后被警告用户侧零持久化 artifact（base：红）——警告静默丢失不可补偿"
    artifact = rows[0]
    assert (artifact.data or {}).get("group_id") == str(
        group.id
    ), f"artifact 必须可追溯到群组，实际 data={artifact.data}"
    assert "刷屏警告红测" in artifact.content, f"artifact 必须携带警告原因，实际 content={artifact.content!r}"
    assert (artifact.data or {}).get("warn_count") == 1


@pytest.mark.asyncio
async def test_warn_success_path_also_persists_notification(warn_env: _Env) -> None:
    """正常路径（不人为断推送）同样持久化警告 artifact——持久化不依赖推送成败。"""
    owner = await _make_user(warn_env.db, "wsowner")
    target = await _make_user(warn_env.db, "wstarget")
    group = await _make_group_with_member(warn_env.db, owner, target)

    warn_env.current["user"] = owner
    async with await warn_env.client() as client:
        resp = await client.post(
            f"{COMMUNITY_PREFIX}/groups/{group.id}/members/{target.id}/warn",
            json={"user_id": str(target.id), "reason": "正常路径警告红测"},
        )

    assert resp.status_code == 200, f"实际 {resp.status_code}: {resp.text[:200]}"
    rows = (await warn_env.db.execute(select(Notification).where(Notification.user_id == target.id))).scalars().all()
    assert rows, "正常路径也必须持久化警告 artifact（与推送成败解耦）"


# --- V3-FIX-117：mute_until 到期三形态 --------------------------------------------


@pytest.mark.asyncio
async def test_mute_expired_allows_send(warn_env: _Env) -> None:
    """mute_until 已过：发言必须恢复（base：无比较点仍拒 → 红）。"""
    owner = await _make_user(warn_env.db, "meowner")
    member = await _make_user(warn_env.db, "memember")
    group = await _make_group_with_member(warn_env.db, owner, member)
    await _mute_member(warn_env.db, group, member)

    # 回拨 mute_until 到过去
    row = await _get_member(warn_env.db, group, member)
    row.mute_until = _utcnow() - timedelta(minutes=1)
    await warn_env.db.commit()

    warn_env.current["user"] = member
    async with await warn_env.client() as client:
        resp = await client.post(
            f"{COMMUNITY_PREFIX}/groups/{group.id}/messages",
            json={"content": "禁言到期后应可发言"},
        )

    assert (
        resp.status_code == 200
    ), f"mute_until 已过期，禁言必须自动解除（base 无比较点：红），实际 {resp.status_code}: {resp.text[:200]}"


@pytest.mark.asyncio
async def test_mute_active_still_rejects_send(warn_env: _Env) -> None:
    """mute_until 未到：发言仍拒（守卫形态，修后不得松动）。"""
    owner = await _make_user(warn_env.db, "maowner")
    member = await _make_user(warn_env.db, "mamember")
    group = await _make_group_with_member(warn_env.db, owner, member)
    await _mute_member(warn_env.db, group, member)

    warn_env.current["user"] = member
    async with await warn_env.client() as client:
        resp = await client.post(
            f"{COMMUNITY_PREFIX}/groups/{group.id}/messages",
            json={"content": "禁言期内应被拒"},
        )

    assert resp.status_code == 400, f"mute_until 未到期必须仍拒发，实际 {resp.status_code}: {resp.text[:200]}"
    assert "禁言" in resp.text, f"拒绝原因必须指向禁言，实际 {resp.text[:200]}"


@pytest.mark.asyncio
async def test_mute_without_until_is_permanent(warn_env: _Env) -> None:
    """is_muted=True 且无 mute_until：永久禁言（守卫形态）。"""
    owner = await _make_user(warn_env.db, "mpowner")
    member = await _make_user(warn_env.db, "mpmember")
    group = await _make_group_with_member(warn_env.db, owner, member)

    row = await _get_member(warn_env.db, group, member)
    row.is_muted = True
    row.mute_until = None
    await warn_env.db.commit()

    warn_env.current["user"] = member
    async with await warn_env.client() as client:
        resp = await client.post(
            f"{COMMUNITY_PREFIX}/groups/{group.id}/messages",
            json={"content": "永久禁言应被拒"},
        )

    assert resp.status_code == 400, f"无 mute_until 的禁言必须永久生效，实际 {resp.status_code}: {resp.text[:200]}"
    assert "禁言" in resp.text, f"拒绝原因必须指向禁言，实际 {resp.text[:200]}"
