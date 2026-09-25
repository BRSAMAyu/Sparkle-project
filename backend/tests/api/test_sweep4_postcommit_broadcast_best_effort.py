"""清扫轮4 · send_message 等社区面端点 post-commit 广播失败 500 同族 best-effort 化.

wt396 F6（commit 64e6cdff）修了 leave/kick 的同族缺口并在 DEFERRED 里点名：
「send_message 等其余端点 post-commit 广播失败 500 同族（未在卡面范围）」。
本卡把该族收口——消息已落库提交（权威事实），提交后的 WS 广播/私信推送
（Redis publish 瞬断即抛）不得把已成功的结果变成 500：客户端重试会造成
重复消息，不重试则用户看到发送失败但消息实际已发出。

修法口径（照抄 F6 先例）：提交后的广播/推送整体 try/except best-effort，
失败 ``logger.opt(exception=True).warning`` 记日志不 500。

红测（base 上红）：
1. 群消息 send_message：广播失败 → 仍 200（base 500：红）。
2. 私信 send_private_message：推送失败 → 仍 200（base 500：红）。
"""

from __future__ import annotations

import uuid as uuid_mod
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_db
from app.core.websocket import manager as global_ws_manager
from app.models.base import Base
from app.models.community import Group, GroupMember, GroupRole, GroupType
from app.models.user import User

COMMUNITY_PREFIX = "/api/v1/community"


class _Env:
    def __init__(self, db: AsyncSession, app: FastAPI, current: dict):
        self.db = db
        self.app = app
        self.current = current

    async def client(self) -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=self.app, raise_app_exceptions=False), base_url="http://test")


@pytest.fixture(name="family_env")
async def family_env_fixture(monkeypatch: pytest.MonkeyPatch):
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

        import app.api.v1.community as community_api

        async def _no_op_streak(_user_id: UUID) -> None:
            return None

        community_api._refresh_streak_signals = _no_op_streak  # type: ignore[method-assign]

        yield _Env(db, app, current)

        app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture(name="failing_ws_manager")
def failing_ws_manager_fixture(monkeypatch: pytest.MonkeyPatch):
    """WS 推送通道全断（Redis 瞬断等价面）：broadcast/推送一律抛 ConnectionError。"""
    mgr = global_ws_manager
    mgr.redis = None
    mgr.pubsub = None
    mgr.active_connections.clear()
    mgr.user_connections.clear()

    async def _boom_broadcast(*args, **kwargs):  # noqa: ANN002, ANN003
        raise ConnectionError("simulated redis outage (post-commit broadcast family)")

    async def _boom_push(*args, **kwargs):  # noqa: ANN002, ANN003
        raise ConnectionError("simulated redis outage (post-commit broadcast family)")

    monkeypatch.setattr(mgr, "broadcast", _boom_broadcast)
    monkeypatch.setattr(mgr, "send_personal_message", _boom_push)
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


async def _make_group_with_member(db: AsyncSession, owner: User) -> Group:
    group = Group(
        name=f"grp_{uuid_mod.uuid4().hex[:8]}",
        type=GroupType.SQUAD,
        focus_tags=[],
    )
    db.add(group)
    await db.flush()
    db.add(GroupMember(group_id=group.id, user_id=owner.id, role=GroupRole.OWNER))
    await db.commit()
    return group


# --- 红测 1：群消息广播失败 → 仍 200 ----------------------------------------------


@pytest.mark.asyncio
async def test_send_message_survives_broadcast_failure(
    family_env: _Env, failing_ws_manager, monkeypatch: pytest.MonkeyPatch
) -> None:
    sender = await _make_user(family_env.db, "sender")
    group = await _make_group_with_member(family_env.db, sender)
    family_env.current["user"] = sender

    async with await family_env.client() as client:
        resp = await client.post(
            f"{COMMUNITY_PREFIX}/groups/{group.id}/messages",
            json={"content": "广播断线也不该 500"},
        )

    assert (
        resp.status_code == 200
    ), f"消息已提交，广播失败必须 best-effort（base 500：红），实际 {resp.status_code}: {resp.text[:200]}"
    body = resp.json()
    assert body.get("content") == "广播断线也不该 500", f"消息本体必须返回，实际 keys: {list(body)}"


# --- 红测 2：私信推送失败 → 仍 200 ------------------------------------------------


@pytest.mark.asyncio
async def test_send_private_message_survives_push_failure(family_env: _Env, failing_ws_manager) -> None:
    sender = await _make_user(family_env.db, "psender")
    receiver = await _make_user(family_env.db, "preceiver")
    family_env.current["user"] = sender

    async with await family_env.client() as client:
        resp = await client.post(
            f"{COMMUNITY_PREFIX}/messages",
            json={"target_user_id": str(receiver.id), "content": "私信推送断线也不该 500"},
        )

    assert (
        resp.status_code == 200
    ), f"私信已提交，推送失败必须 best-effort（base 500：红），实际 {resp.status_code}: {resp.text[:200]}"
