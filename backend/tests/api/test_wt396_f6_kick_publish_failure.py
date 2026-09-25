"""wt396 F6（S-05 轮3）· leave/kick 关闭通知无补偿 —— publish 失败即隐私缺口回归.

轮3判据（v3-output/WT391-HUNT-R3 REPORT F6）：成员行删除提交后，唯一关闭手段
是 ``kick_user_from_group`` 的单次 Redis publish。publish 失败（Redis 瞬断）→
异常穿透 → 500（成员变更已提交）→ 事后重试 leave/kick 一律 400「不是群组成员」
→ 已退成员的**存活 WS** 永久挂在 active_connections 持续收群广播——正是 S-05
要堵的缺口，且无补偿。

修法口径（卡面）：publish 失败降级不阻断成员变更结果——
1. ``ConnectionManager.kick_user_from_group``：publish 失败不再上抛，降级
   ``_kick_local``（本节点扇出仍生效）+ 日志（成员行已是权威事实）；
2. leave/kick 端点：提交后的广播与关闭通知整体 best-effort（失败记日志不 500）。
"""

from __future__ import annotations

import asyncio
import json
import types
import uuid as uuid_mod
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI, WebSocketDisconnect
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token
from app.core.websocket import ConnectionManager
from app.core.websocket import manager as global_ws_manager
from app.models.base import Base
from app.models.user import User

COMMUNITY_PREFIX = "/api/v1/community"
SQUAD_PREFIX = f"{COMMUNITY_PREFIX}/squads"

_OUTBOX_DDL = [
    """
    CREATE TABLE IF NOT EXISTS event_outbox (
        id CHAR(36) PRIMARY KEY,
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id CHAR(36) NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        event_version INTEGER NOT NULL DEFAULT 1,
        sequence_number INTEGER NOT NULL,
        payload JSON NOT NULL,
        metadata JSON
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS event_sequence_counters (
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id CHAR(36) NOT NULL,
        next_sequence INTEGER NOT NULL,
        PRIMARY KEY (aggregate_type, aggregate_id)
    )
    """,
]


class _FailingRedis:
    """Redis 瞬断注入：publish 一律抛 ConnectionError（F6 的失败窗口）。"""

    def __init__(self) -> None:
        self.publish_calls = 0

    async def publish(self, channel: str, message: str) -> int:
        self.publish_calls += 1
        raise ConnectionError(f"simulated redis outage (wt396 F6) on {channel}")


class _Env:
    def __init__(self, db: AsyncSession, app: FastAPI, current: dict):
        self.db = db
        self.app = app
        self.current = current

    async def client(self) -> AsyncClient:
        # raise_app_exceptions=False：捕获端点未处理异常的 500 响应（红测判 500 用）
        return AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False), base_url="http://test"
        )

    async def as_user(self, client: AsyncClient, user: User | None) -> None:
        self.current["user"] = user


@pytest.fixture(name="f6_env")
async def f6_env_fixture(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for ddl in _OUTBOX_DDL:
            await conn.execute(text(ddl))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        from app.api.v1.community import router as community_router
        from app.api.v1.community_squad import router as squad_router

        app = FastAPI()
        app.include_router(community_router, prefix=COMMUNITY_PREFIX)
        app.include_router(squad_router, prefix=COMMUNITY_PREFIX)

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
        monkeypatch.setattr(community_api, "AsyncSessionLocal", session_factory)

        yield _Env(db, app, current)

        app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture(name="ws_manager")
async def ws_manager_fixture():
    mgr = global_ws_manager
    mgr.redis = None
    mgr.pubsub = None
    mgr.listener_task = None
    mgr.active_connections.clear()
    mgr.user_connections.clear()
    mgr.friend_map.clear()
    mgr._ack_events.clear()
    yield mgr
    mgr.active_connections.clear()
    mgr.user_connections.clear()
    mgr.friend_map.clear()
    mgr._ack_events.clear()
    mgr.redis = None
    mgr.pubsub = None
    mgr.listener_task = None


class _WsClient:
    """可控双工假 WebSocket（S-05 e2e 同款边界注入）。"""

    def __init__(self, name: str):
        self.name = name
        self.headers: dict[str, str] = {}
        self.query_params: dict[str, str] = {}
        self.frames: list[dict] = []
        self.closed_codes: list[int] = []
        self.accepted = False
        self.state = types.SimpleNamespace()
        self.inbox: list[str] = []
        self.client_closed = False

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int = 1000) -> None:
        self.closed_codes.append(code)

    async def send_text(self, data: str) -> None:
        if self.closed_codes:
            raise RuntimeError(f"[{self.name}] send after server close")
        self.frames.append(json.loads(data))

    async def send_json(self, data, mode: str = "text") -> None:
        await self.send_text(json.dumps(data, default=str))

    async def receive_text(self) -> str:
        while True:
            if self.inbox:
                return self.inbox.pop(0)
            if self.client_closed:
                raise WebSocketDisconnect(code=1000)
            await asyncio.sleep(0.005)


async def _wait_until(predicate, timeout: float = 5.0, message: str = "condition not met") -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.005)
    pytest.fail(message)


async def _connect_group_ws(env: _Env, group_id: UUID, user: User, client: _WsClient, manager: ConnectionManager):
    import app.api.v1.community as community_api

    token = create_access_token({"sub": str(user.id)})
    client.headers = {"authorization": f"Bearer {token}"}
    task = asyncio.create_task(
        community_api.websocket_endpoint(websocket=client, group_id=group_id, token=None)  # type: ignore[arg-type]
    )
    await _wait_until(lambda: client.accepted or client.closed_codes, message="ws endpoint did not settle")
    await _wait_until(
        lambda: str(group_id) in manager.active_connections
        and client in manager.active_connections.get(str(group_id), []),
        message=f"[{client.name}] connection not registered",
    )
    return task


async def _make_user(env: _Env, prefix: str) -> User:
    user = User(
        username=f"{prefix}_{uuid_mod.uuid4().hex[:10]}",
        email=f"{prefix}_{uuid_mod.uuid4().hex[:10]}@t.example",
        hashed_password="x",
        photon_balance=0,
    )
    env.db.add(user)
    await env.db.commit()
    return user


async def _make_squad(env: _Env, client: AsyncClient, owner: User, name: str) -> str:
    await env.as_user(client, owner)
    resp = await client.post(
        SQUAD_PREFIX,
        json={
            "name": name,
            "deadline": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
            "max_members": 8,
            "sprint_goal": "wt396 F6 小队",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _join(env: _Env, client: AsyncClient, squad_id: str, member: User) -> None:
    await env.as_user(client, member)
    resp = await client.post(f"{SQUAD_PREFIX}/{squad_id}/join")
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# 红1：leave 时 publish 失败 → 不得 500、存活 WS 必须被本地降级关闭
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_leave_with_publish_failure_not_500_and_still_closes_live_socket(f6_env: _Env, ws_manager):
    env = f6_env
    async with await env.client() as ac:
        alice = await _make_user(env, "f6a")
        bob = await _make_user(env, "f6b")
        squad_id = await _make_squad(env, ac, alice, "f6 leave 小队")
        await _join(env, ac, squad_id, bob)

    bob_ws = _WsClient("bob")
    bob_task = await _connect_group_ws(env, UUID(squad_id), bob, bob_ws, ws_manager)

    # Redis 瞬断窗口（成员行删除尚未发生）
    failing = _FailingRedis()
    ws_manager.redis = failing

    async with await env.client() as ac:
        await env.as_user(ac, bob)
        leave = await ac.post(f"{COMMUNITY_PREFIX}/groups/{squad_id}/leave")
        # 成员行删除已提交 → 通知失败不得把结果变成 500（否则重试被 400 挡死）
        assert leave.status_code == 200, f"leave 不得因 publish 失败 500：{leave.status_code}"

    # publish 失败必须降级本地关闭：bob 的存活 WS 被关（4001），不再收群广播
    assert failing.publish_calls >= 1, "前提自证：publish 确实被尝试过"
    await _wait_until(lambda: bob_ws.closed_codes, message="publish 失败后必须降级本地关闭存活 WS")
    assert bob_ws.closed_codes == [4001]

    bob_ws.client_closed = True
    await asyncio.wait_for(bob_task, timeout=5)

    # 复位注入：后续步骤回到本地扇出模式（广播失败 500 是另一写面，非本卡范围）
    ws_manager.redis = None

    async with await env.client() as ac:
        await env.as_user(ac, alice)
        after = await ac.post(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages", json={"content": "退群后新消息"})
        assert after.status_code == 200
    await asyncio.sleep(0.05)
    assert not any(f.get("id") == after.json()["id"] for f in bob_ws.frames), "退群连接不得再收群广播"


# ---------------------------------------------------------------------------
# 红2：kick 时 publish 失败 → 同族补偿（不 500、目标 WS 本地关闭）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kick_with_publish_failure_not_500_and_still_closes_target_socket(f6_env: _Env, ws_manager):
    env = f6_env
    async with await env.client() as ac:
        owner = await _make_user(env, "f6own")
        mate = await _make_user(env, "f6mate")
        squad_id = await _make_squad(env, ac, owner, "f6 kick 小队")
        await _join(env, ac, squad_id, mate)

    mate_ws = _WsClient("mate")
    mate_task = await _connect_group_ws(env, UUID(squad_id), mate, mate_ws, ws_manager)

    failing = _FailingRedis()
    ws_manager.redis = failing

    async with await env.client() as ac:
        await env.as_user(ac, owner)
        kick = await ac.post(f"{COMMUNITY_PREFIX}/groups/{squad_id}/members/{mate.id}/kick")
        assert kick.status_code == 200, f"kick 不得因 publish 失败 500：{kick.status_code}"

    assert failing.publish_calls >= 1, "前提自证：publish 确实被尝试过"
    await _wait_until(lambda: mate_ws.closed_codes, message="publish 失败后必须降级本地关闭被踢成员 WS")
    assert mate_ws.closed_codes == [4001]
    mate_ws.client_closed = True
    await asyncio.wait_for(mate_task, timeout=5)

    async with await env.client() as ac:
        await env.as_user(ac, mate)
        read_after = await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages")
        assert read_after.status_code == 403, "被踢后读面必须关闭"


# ---------------------------------------------------------------------------
# 红3：manager 层单元——kick_user_from_group publish 失败不抛、本地扇出生效
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kick_user_from_group_publish_failure_falls_back_to_local(ws_manager):
    ws_manager.redis = _FailingRedis()
    ghost = _WsClient("ghost")
    ghost.state.user_id = "user-1"
    ws_manager.active_connections["group-1"] = [ghost]

    # 修前：ConnectionError 直接穿透 → 调用方（leave/kick/服务层容错）500
    await ws_manager.kick_user_from_group("group-1", "user-1", "wt396 F6")

    assert ghost.closed_codes == [4001], "publish 失败必须降级本地关闭（本节点扇出不因 Redis 瞬断失效）"
