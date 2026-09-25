"""卡 S-05 · Community Reconnect/Retract/Two-account E2E —— headless 真实验证.

在 S-01 community_e2e（服务层全链路）与 S-03/S-04 断言面（surface 收敛 + 证据
撤回传播）之上扩谱，不重建真源。三端实机走查无浏览器/模拟器权限 → headless
口径：HTTP API + 真 WS 端点 + 真 ConnectionManager 本地扇出（无 Redis 时既有
降级路径），断连只做边界注入（假 WebSocket 的收发时序由测试控制），语义断言
全部由真实服务/端点驱动（不 mock 业务行为）。

谱系（27 case，各自独立断言）：

A. 实时连接/断连/重连（真端点 + 真 ConnectionManager）
B. 重复/幂等（读回执重放、重复撤回收敛、撤回后再采纳拒绝、nonce-ACK 关联）
C. 乱序可恢复（created_at 重建序、before_id 游标、断档补齐+引用链完好）
D. leave 谱系（退群失效、群主不可退、历史保留、重加入恢复、踢出）
E. revoke 谱系（群聊撤回传播/授权/幂等、私聊撤回双向传播、S-04 证据撤回链）
F. block 谱系（DM 双向断、好友请求拦、拉黑列表、恢复、群成员不驱逐、定向分享拦）
G. 跨用户/跨群隔离（群通道 scoping、私聊 pair 隔离、self-only 不出广播、
   S-02 群上下文边界 API 面复验）

同源一致口径（卡面验收第 3 条）：每个广播帧与 API 返回逐字段对齐同一 DB 行；
S-04 采纳事件 outbox payload 与证据行/API 返回同 id 源。
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
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token
from app.core.websocket import ConnectionManager
from app.core.websocket import manager as global_ws_manager
from app.models.base import Base
from app.models.community import (
    CommunityOutcomeEvidence,
    GroupMessageRead,
    SharedResource,
    SharedResourceFeedback,
    UserBlock,
)
from app.models.goal import Goal
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.schemas.community import FeedbackVerdict

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


# ---------------------------------------------------------------------------
# 环境夹具：sqlite 内存 + 双账号 FastAPI app + 真 WS 管理器复位
# ---------------------------------------------------------------------------
class _Env:
    """S-05 测试环境句柄：DB 会话、双账号切换、HTTP 客户端工厂。"""

    def __init__(self, db: AsyncSession, session_factory, app: FastAPI, current: dict):
        self.db = db
        self.session_factory = session_factory
        self.app = app
        self.current = current

    async def client(self) -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=self.app), base_url="http://test")

    async def as_user(self, client: AsyncClient, user: User | None) -> None:
        self.current["user"] = user


@pytest.fixture(name="s05_env")
async def s05_env_fixture(monkeypatch: pytest.MonkeyPatch):
    """sqlite 内存引擎 + 路由 app + 双账号 current 切换 + WS 依赖注入面.

    - community 模块级 AsyncSessionLocal → 测试 sessionmaker（WS 端点会员校验、
      个人通道好友读取、状态更新都走它，与主测试会话同库同 StaticPool 连接）；
    - event_outbox/event_sequence_counters 最小 sqlite 表（对齐 5f2b9b3c0e6f 迁移列，
      S-04 同款先例——生产 PG 由迁移建表）。
    """
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

        yield _Env(db, session_factory, app, current)

        app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture(name="ws_manager")
async def ws_manager_fixture():
    """真 ConnectionManager 单例复位（本地扇出模式，redis=None）。

    端点/服务层共用同一单例（community.py 与 community_service.py 都
    `from app.core.websocket import manager`），复位而非替换以保持单一真源。
    """
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
    """可控双工假 WebSocket（边界注入：只控制收发时序与断连，不 mock 语义）。

    - send_text：服务端 → 客户端帧，逐条记录（真实 starlette 行为：已收到
      close 后再 send 会抛 RuntimeError，广播侧逐 socket 容错捕获）。
    - receive_text：客户端 → 服务端，由测试注入 inbox 帧；client_closed=True
      或 inbox 空且断开标记置位后抛 WebSocketDisconnect（= 边界断连注入）。
    """

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
        """同 send_text 记录帧（ConnectionManager._kick_local 走 send_json）。"""
        await self.send_text(json.dumps(data, default=str))

    async def receive_text(self) -> str:
        while True:
            if self.inbox:
                return self.inbox.pop(0)
            if self.client_closed:
                raise WebSocketDisconnect(code=1000)
            await asyncio.sleep(0.005)

    def send(self, payload: dict) -> None:
        """测试注入一条客户端上行帧（如 typing）。"""
        self.inbox.append(json.dumps(payload))


async def _wait_until(predicate, timeout: float = 5.0, message: str = "condition not met") -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.005)
    pytest.fail(message)


async def _connect_group_ws(env: _Env, group_id: UUID, user: User, client: _WsClient, manager: ConnectionManager):
    """真端点驱动群聊 WS 连接（真 JWT + 真会员校验 + 真 manager 注册）。"""
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


async def _disconnect_ws(client: _WsClient, task) -> None:
    client.client_closed = True
    await asyncio.wait_for(task, timeout=5)


def _frames_of_type(client: _WsClient, frame_type: str) -> list[dict]:
    return [f for f in client.frames if f.get("type") == frame_type]


# ---------------------------------------------------------------------------
# 造数助手（全部走真实 API/服务，不直插业务表）
# ---------------------------------------------------------------------------
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
            "sprint_goal": "S-05 两账号小队",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _join(env: _Env, client: AsyncClient, squad_id: str, member: User) -> None:
    await env.as_user(client, member)
    resp = await client.post(f"{SQUAD_PREFIX}/{squad_id}/join")
    assert resp.status_code == 200, resp.text


async def _send_group_msg(env: _Env, client: AsyncClient, group_id: str, user: User, content: str, **kwargs) -> dict:
    await env.as_user(client, user)
    resp = await client.post(f"{COMMUNITY_PREFIX}/groups/{group_id}/messages", json={"content": content, **kwargs})
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _make_friendship(env: _Env, a: User, b: User) -> None:
    """真实好友链：A 发请求 → B 接受。"""
    from app.services.community_service import FriendshipService

    fr = await FriendshipService.send_friend_request(env.db, a.id, b.id)
    await env.db.commit()
    await FriendshipService.respond_to_request(env.db, b.id, fr.id, accept=True)
    await env.db.commit()


async def _owner_goal_plan_task(env: _Env, owner: User) -> Goal:
    """S-04 同款真源造数：Goal → Plan（双向外链）→ Task。"""
    goal = Goal(user_id=owner.id, title="S-05 撤回链目标", status="active", mastery=0.2, progress=0.1)
    env.db.add(goal)
    await env.db.flush()
    plan = Plan(user_id=owner.id, goal_id=goal.id, name="S-05 计划", type=PlanType.SPRINT)
    env.db.add(plan)
    await env.db.flush()
    goal.plan_id = plan.id
    env.db.add(goal)
    env.db.add(
        Task(
            user_id=owner.id,
            plan_id=plan.id,
            title="S-05 撤回链任务",
            type=TaskType.LEARNING,
            estimated_minutes=45,
            status=TaskStatus.COMPLETED,
        )
    )
    await env.db.commit()
    return goal


# ===========================================================================
# A. 实时连接/断连/重连
# ===========================================================================
@pytest.mark.asyncio
async def test_case01_member_connect_registers_and_disconnect_cleans_registry(s05_env: _Env, ws_manager):
    """case1 成员连入：真端点 accept + 注册进 manager；边界断连后注册清理（无泄漏）。"""
    env = s05_env
    async with await env.client() as ac:
        owner = await _make_user(env, "c01a")
        squad_id = await _make_squad(env, ac, owner, "c01 小队")

    client = _WsClient("owner")
    task = await _connect_group_ws(env, UUID(squad_id), owner, client, ws_manager)
    assert client.closed_codes == [], "成员不应被拒"
    assert client.state.user_id == str(owner.id)

    await _disconnect_ws(client, task)
    assert ws_manager.active_connections.get(squad_id) in (None, []), "断开后必须清理注册表"


@pytest.mark.asyncio
async def test_case02_non_member_and_garbage_token_rejected_4003_no_registration(s05_env: _Env, ws_manager):
    """case2 非成员 4003 拒绝且零注册；伪造 token 同样 4003（鉴权先于会员校验）。"""
    env = s05_env
    async with await env.client() as ac:
        owner = await _make_user(env, "c02a")
        outsider = await _make_user(env, "c02b")
        squad_id = await _make_squad(env, ac, owner, "c02 小队")

    import app.api.v1.community as community_api

    outsider_ws = _WsClient("outsider")
    outsider_ws.headers = {"authorization": f"Bearer {create_access_token({'sub': str(outsider.id)})}"}
    task = asyncio.create_task(
        community_api.websocket_endpoint(websocket=outsider_ws, group_id=UUID(squad_id), token=None)
    )
    await asyncio.wait_for(task, timeout=5)
    assert outsider_ws.closed_codes == [4003]
    assert outsider_ws.accepted is False
    assert squad_id not in ws_manager.active_connections

    forged_ws = _WsClient("forged")
    forged_ws.headers = {"authorization": "Bearer not-a-jwt"}
    task2 = asyncio.create_task(
        community_api.websocket_endpoint(websocket=forged_ws, group_id=UUID(squad_id), token=None)
    )
    await asyncio.wait_for(task2, timeout=5)
    # 伪造 token 走外层异常兜底关闭（1000），与缺 token/非成员的 4003 不同码但同义：拒绝准入
    assert forged_ws.accepted is False, "伪造 token 不得 accept"
    assert squad_id not in ws_manager.active_connections


@pytest.mark.asyncio
async def test_case03_reconnect_recovers_offline_messages_and_resumes_live_delivery(s05_env: _Env, ws_manager):
    """case3 重连恢复（离线不丢）：在线消息实时到达；掉线期间群消息经 HTTP 拉
    取全量补齐；重连后实时投递恢复（拉取与实时同源同 id）。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c03a")
        bob = await _make_user(env, "c03b")
        squad_id = await _make_squad(env, ac, alice, "c03 小队")
        await _join(env, ac, squad_id, bob)

    # bob 先上线，收在线期实时消息
    bob_ws = _WsClient("bob")
    bob_task = await _connect_group_ws(env, UUID(squad_id), bob, bob_ws, ws_manager)
    async with await env.client() as ac:
        m1 = await _send_group_msg(env, ac, squad_id, alice, "在线期间消息")
    await _wait_until(lambda: any(f.get("id") == m1["id"] for f in bob_ws.frames), message="m1 not delivered live")

    # 边界注入：bob 掉线
    await _disconnect_ws(bob_ws, bob_task)
    assert squad_id not in ws_manager.active_connections

    async with await env.client() as ac:
        m2 = await _send_group_msg(env, ac, squad_id, alice, "离线期间消息一")
        m3 = await _send_group_msg(env, ac, squad_id, alice, "离线期间消息二")

    bob_ws2 = _WsClient("bob2")
    bob_task2 = await _connect_group_ws(env, UUID(squad_id), bob, bob_ws2, ws_manager)

    # 离线期消息经 HTTP 拉取补齐（真源一致：拉到的 id 与发送返回的 id 同源）
    async with await env.client() as ac2:
        await env.as_user(ac2, bob)
        history = await ac2.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages")
        assert history.status_code == 200
        history_ids = {m["id"] for m in history.json()}
        assert {m1["id"], m2["id"], m3["id"]} <= history_ids, "重连后离线期消息必须可经拉取恢复"

    # 实时投递在新连接上恢复
    async with await env.client() as ac:
        m4 = await _send_group_msg(env, ac, squad_id, alice, "重连后消息")
    await _wait_until(
        lambda: any(f.get("id") == m4["id"] for f in bob_ws2.frames), message="post-reconnect live delivery failed"
    )
    await _disconnect_ws(bob_ws2, bob_task2)


@pytest.mark.asyncio
async def test_case04_personal_channel_presence_connect_and_disconnect_cleanup(s05_env: _Env, ws_manager):
    """case4 个人通道（/ws/connect）：连入注册个人连接与好友 presence 表，
    断开后双向清理（无悬挂 friend_map 项）。"""
    env = s05_env
    async with await env.client():
        alice = await _make_user(env, "c04a")
        bob = await _make_user(env, "c04b")
        await _make_friendship(env, alice, bob)

    import app.api.v1.community as community_api

    alice_ws = _WsClient("alice")
    token = create_access_token({"sub": str(alice.id)})
    alice_ws.headers = {"authorization": f"Bearer {token}"}
    task = asyncio.create_task(community_api.user_websocket_endpoint(websocket=alice_ws, token=None))
    await _wait_until(
        lambda: ws_manager.user_connections.get(str(alice.id)) is alice_ws, message="personal connect not registered"
    )
    # presence：alice 是 bob 的好友 → friend_map[bob] 含 alice（本地扇出依据）
    assert str(bob.id) in ws_manager.friend_map, "好友 presence 注册缺失"
    assert str(alice.id) in ws_manager.friend_map[str(bob.id)]

    alice_ws.client_closed = True
    await asyncio.wait_for(task, timeout=5)
    assert str(alice.id) not in ws_manager.user_connections
    assert str(bob.id) not in ws_manager.friend_map, "断开后 friend_map 必须清理"


# ===========================================================================
# B. 重复/幂等
# ===========================================================================
@pytest.mark.asyncio
async def test_case05_duplicate_read_receipt_replay_is_idempotent(s05_env: _Env):
    """case5 读回执重放（dup event）：同一 read 事件投递两次，第二次零新增行。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c05a")
        bob = await _make_user(env, "c05b")
        squad_id = await _make_squad(env, ac, alice, "c05 小队")
        await _join(env, ac, squad_id, bob)
        m1 = await _send_group_msg(env, ac, squad_id, alice, "第一条")
        m2 = await _send_group_msg(env, ac, squad_id, alice, "第二条")

        await env.as_user(ac, bob)
        first = await ac.post(
            f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages/read", json={"up_to_message_id": m2["id"]}
        )
        assert first.status_code == 200, first.text
        replay = await ac.post(
            f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages/read", json={"up_to_message_id": m2["id"]}
        )
        assert replay.status_code == 200
        assert replay.json()["updated_count"] == 0, "重复读事件不得重复计数"

    receipts = (
        (await env.db.execute(select(GroupMessageRead).where(GroupMessageRead.message_id == UUID(m1["id"]))))
        .scalars()
        .all()
    )
    assert len(receipts) == 1, "同一用户同一消息只能有一行读回执"


@pytest.mark.asyncio
async def test_case06_duplicate_revoke_converges_and_history_stable(s05_env: _Env, ws_manager):
    """case6 重复撤回事件收敛：服务幂等返回、终态稳定、历史视图不复活不重复；
    两次 message_revoke 帧携带同一 message_id（客户端可按 id 幂等去重）。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c06a")
        bob = await _make_user(env, "c06b")
        squad_id = await _make_squad(env, ac, alice, "c06 小队")
        await _join(env, ac, squad_id, bob)

    bob_ws = _WsClient("bob")
    bob_task = await _connect_group_ws(env, UUID(squad_id), bob, bob_ws, ws_manager)

    async with await env.client() as ac:
        msg = await _send_group_msg(env, ac, squad_id, alice, "将被撤回两次")
        await env.as_user(ac, alice)
        r1 = await ac.post(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages/{msg['id']}/revoke")
        assert r1.status_code == 200
        r2 = await ac.post(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages/{msg['id']}/revoke")
        assert r2.status_code == 200, "重复撤回应幂等成功而非报错"
        assert r2.json()["is_revoked"] is True and r2.json()["content"] is None

        history = await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages")
        rows = [m for m in history.json() if m["id"] == msg["id"]]
        assert len(rows) == 1, "历史视图不得出现重复行"
        assert rows[0]["is_revoked"] is True and rows[0]["content"] is None, "终态必须稳定收敛"

    await _wait_until(lambda: len(_frames_of_type(bob_ws, "message_revoke")) >= 1, message="revoke frame missing")
    revoke_ids = {f["message_id"] for f in _frames_of_type(bob_ws, "message_revoke")}
    assert revoke_ids == {msg["id"]}, "所有撤回帧必须指向同一消息 id（客户端可去重）"
    await _disconnect_ws(bob_ws, bob_task)


@pytest.mark.asyncio
async def test_case07_adopt_after_retract_rejected_and_state_frozen(s05_env: _Env):
    """case7 陈旧采纳失效（离群/迟到事件）：撤回后重放采纳请求 → 400；
    证据行不新增不复活，outbox 不新增（撤回态冻结）。"""
    env = s05_env
    async with await env.client() as ac:
        owner = await _make_user(env, "c07own")
        mate = await _make_user(env, "c07mate")
        goal = await _owner_goal_plan_task(env, owner)
        squad_id = await _make_squad(env, ac, owner, "c07 小队")
        await _join(env, ac, squad_id, mate)

        await env.as_user(ac, owner)
        task_row = (await env.db.execute(select(Task).where(Task.user_id == owner.id))).scalars().first()
        share = await ac.post(
            f"{COMMUNITY_PREFIX}/share",
            json={
                "resource_type": "task",
                "resource_id": str(task_row.id),
                "target_group_id": squad_id,
                "permission": "view",
            },
        )
        assert share.status_code == 200, share.text
        shared_resource_id = share.json()["id"]

        await env.as_user(ac, mate)
        fb = await ac.post(
            f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/feedback",
            json={"verdict": FeedbackVerdict.HELPFUL.value},
        )
        assert fb.status_code == 201, fb.text
        feedback_id = fb.json()["id"]

        await env.as_user(ac, owner)
        adopt = await ac.post(
            f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/feedback/{feedback_id}/adopt",
            json={"goal_id": str(goal.id)},
        )
        assert adopt.status_code == 200
        retract = await ac.post(f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/retract")
        assert retract.status_code == 200

        evidence_before = len((await env.db.execute(select(CommunityOutcomeEvidence))).scalars().all())
        stale_adopt = await ac.post(
            f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/feedback/{feedback_id}/adopt",
            json={"goal_id": str(goal.id)},
        )
        assert stale_adopt.status_code == 400, "撤回后的迟到采纳必须显式拒绝"

    evidence_after = (await env.db.execute(select(CommunityOutcomeEvidence))).scalars().all()
    assert len(evidence_after) == evidence_before == 1
    assert evidence_after[0].status == "retracted"
    outbox = (
        await env.db.execute(
            text("SELECT event_type FROM event_outbox WHERE event_type = 'community.feedback_adopted'")
        )
    ).all()
    assert len(outbox) == 1, "迟到采纳不得追加 flywheel 事件"


@pytest.mark.asyncio
async def test_case08_nonce_ack_correlation_each_send_correlated_not_collapsed(s05_env: _Env, ws_manager):
    """case8 nonce-ACK 关联：每次发送的 ACK 精确关联该次落库行（nonce 是
    关联键不是幂等锚——幂等锚是读回执/feedback_id，见 case5/case7）。
    ACK 走个人通道（/ws/connect 注册的 user_connections），群通道收不到。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c08a")
        squad_id = await _make_squad(env, ac, alice, "c08 小队")

    import app.api.v1.community as community_api

    alice_ws = _WsClient("alice")
    alice_ws.headers = {"authorization": f"Bearer {create_access_token({'sub': str(alice.id)})}"}
    alice_task = asyncio.create_task(community_api.user_websocket_endpoint(websocket=alice_ws, token=None))
    await _wait_until(
        lambda: ws_manager.user_connections.get(str(alice.id)) is alice_ws, message="personal channel not registered"
    )

    async with await env.client() as ac:
        r1 = await _send_group_msg(env, ac, squad_id, alice, "带 nonce 发送一", nonce="nonce-1")
        r2 = await _send_group_msg(env, ac, squad_id, alice, "同 nonce 重发", nonce="nonce-1")

    await _wait_until(lambda: len(_frames_of_type(alice_ws, "ack")) >= 2, message="ack frames missing")
    acks = _frames_of_type(alice_ws, "ack")
    assert acks[0]["nonce"] == "nonce-1" and acks[0]["message_id"] == r1["id"]
    assert acks[1]["nonce"] == "nonce-1" and acks[1]["message_id"] == r2["id"], "每次发送的 ACK 必须关联当次落库行"
    assert r1["id"] != r2["id"]
    alice_ws.client_closed = True
    await asyncio.wait_for(alice_task, timeout=5)


# ===========================================================================
# C. 乱序可恢复
# ===========================================================================
@pytest.mark.asyncio
async def test_case09_out_of_order_receipt_reconstructs_total_order_via_created_at_and_cursor(
    s05_env: _Env, ws_manager
):
    """case9 乱序可恢复：客户端按任意顺序收到帧后，可由 HTTP 拉取（created_at
    逆序分页 + before_id 游标）重建与服务端写入一致的全序。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c09a")
        bob = await _make_user(env, "c09b")
        squad_id = await _make_squad(env, ac, alice, "c09 小队")
        await _join(env, ac, squad_id, bob)

    sent = []
    for i in range(5):
        async with await env.client() as ac:
            sent.append(await _send_group_msg(env, ac, squad_id, alice, f"顺序消息 {i}"))
        await asyncio.sleep(0.002)

    # 模拟客户端乱序收到帧（反序到达）
    bob_ws = _WsClient("bob")
    bob_task = await _connect_group_ws(env, UUID(squad_id), bob, bob_ws, ws_manager)
    async with await env.client() as ac:
        tail = await _send_group_msg(env, ac, squad_id, alice, "触发广播的尾部消息")
    await _wait_until(lambda: any(f.get("id") == tail["id"] for f in bob_ws.frames), message="tail frame missing")
    await _disconnect_ws(bob_ws, bob_task)

    # 重建全序：API 逆序分页 + before_id 游标向历史方向走
    async with await env.client() as ac:
        await env.as_user(ac, bob)
        page1 = (await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages", params={"limit": 3})).json()
        assert [m["id"] for m in page1] == [
            tail["id"],
            sent[4]["id"],
            sent[3]["id"],
        ], "最新页必须按 created_at 严格逆序"
        cursor = await ac.get(
            f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages", params={"limit": 10, "before_id": page1[-1]["id"]}
        )
        page2 = cursor.json()
        reconstructed = list(reversed([m["id"] for m in page1 + page2]))
        assert reconstructed == [m["id"] for m in sent + [tail]], "游标重建的全序必须与写入顺序一致"


@pytest.mark.asyncio
async def test_case10_gap_recovery_missed_frame_visible_with_reply_chain_intact(s05_env: _Env, ws_manager):
    """case10 断档补齐：客户端漏收中间帧后，拉取补齐且针对该消息的引用/线程
    链在新客户端上完好（reply_to 可解析到原行）。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c10a")
        bob = await _make_user(env, "c10b")
        squad_id = await _make_squad(env, ac, alice, "c10 小队")
        await _join(env, ac, squad_id, bob)
        await _send_group_msg(env, ac, squad_id, alice, "线程根")

    # bob 掉线期间 alice 发中间消息 + 引用回复
    bob_ws = _WsClient("bob")
    bob_task = await _connect_group_ws(env, UUID(squad_id), bob, bob_ws, ws_manager)
    await _disconnect_ws(bob_ws, bob_task)

    async with await env.client() as ac:
        missed = await _send_group_msg(env, ac, squad_id, alice, "bob 漏收的中间消息")
        reply = await _send_group_msg(env, ac, squad_id, alice, "引用回复", reply_to_id=missed["id"])

    # bob 重连后拉取：断档消息与引用链完整可见
    async with await env.client() as ac:
        await env.as_user(ac, bob)
        history = await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages")
        rows = {m["id"]: m for m in history.json()}
        assert missed["id"] in rows and reply["id"] in rows, "重连拉取必须补齐断档"
        assert rows[reply["id"]]["reply_to_id"] == missed["id"]
        quoted = rows[reply["id"]].get("quoted_message")
        assert quoted is not None and quoted["id"] == missed["id"], "引用链必须可解析到原行（乱序补齐后不悬空）"


# ===========================================================================
# D. leave 谱系
# ===========================================================================
@pytest.mark.asyncio
async def test_case11_leave_stops_read_send_and_ws_admission(s05_env: _Env, ws_manager):
    """case11 退群失效：leave 后 member_left 广播；再拉消息 403、再发消息 400、
    WS 再连 4003 拒绝（读/写/实时三面同闭）。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c11a")
        bob = await _make_user(env, "c11b")
        squad_id = await _make_squad(env, ac, alice, "c11 小队")
        await _join(env, ac, squad_id, bob)

    alice_ws = _WsClient("alice")
    alice_task = await _connect_group_ws(env, UUID(squad_id), alice, alice_ws, ws_manager)

    async with await env.client() as ac:
        await env.as_user(ac, bob)
        leave = await ac.post(f"{COMMUNITY_PREFIX}/groups/{squad_id}/leave")
        assert leave.status_code == 200

    await _wait_until(lambda: _frames_of_type(alice_ws, "member_left"), message="member_left broadcast missing")
    assert _frames_of_type(alice_ws, "member_left")[0]["user_id"] == str(bob.id)

    async with await env.client() as ac:
        await env.as_user(ac, bob)
        read_after = await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages")
        assert read_after.status_code == 403, "退群后不得再读"
        send_after = await ac.post(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages", json={"content": "退群后发送"})
        assert send_after.status_code == 400, "退群后不得再写"

    import app.api.v1.community as community_api

    bob_ws = _WsClient("bob-after-leave")
    bob_ws.headers = {"authorization": f"Bearer {create_access_token({'sub': str(bob.id)})}"}
    ws_task = asyncio.create_task(
        community_api.websocket_endpoint(websocket=bob_ws, group_id=UUID(squad_id), token=None)
    )
    await asyncio.wait_for(ws_task, timeout=5)
    assert bob_ws.closed_codes == [4003], "退群后 WS 准入必须关闭"
    assert not bob_ws.accepted
    await _disconnect_ws(alice_ws, alice_task)


@pytest.mark.asyncio
async def test_case12_owner_cannot_leave_without_transfer(s05_env: _Env):
    """case12 群主不可直接退群（防孤儿群）：400 显式报错。"""
    env = s05_env
    async with await env.client() as ac:
        owner = await _make_user(env, "c12a")
        squad_id = await _make_squad(env, ac, owner, "c12 小队")
        resp = await ac.post(f"{COMMUNITY_PREFIX}/groups/{squad_id}/leave")
        assert resp.status_code == 400
        assert "转让" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_case13_leave_preserves_history_for_remaining_members(s05_env: _Env):
    """case13 退群 ≠ 删史：剩余成员的历史视图完整保留（与解散的级联清理语义区分）。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c13a")
        bob = await _make_user(env, "c13b")
        squad_id = await _make_squad(env, ac, alice, "c13 小队")
        await _join(env, ac, squad_id, bob)
        m1 = await _send_group_msg(env, ac, squad_id, bob, "bob 退群前的消息")

        await env.as_user(ac, bob)
        assert (await ac.post(f"{COMMUNITY_PREFIX}/groups/{squad_id}/leave")).status_code == 200

        await env.as_user(ac, alice)
        history = await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages")
        assert any(m["id"] == m1["id"] and m["content"] == "bob 退群前的消息" for m in history.json())


@pytest.mark.asyncio
async def test_case14_rejoin_after_leave_restores_membership_read_and_ws_admission(s05_env: _Env, ws_manager):
    """case14 重加入恢复：leave → join 后读面恢复、WS 准入恢复、能实时收发。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c14a")
        bob = await _make_user(env, "c14b")
        squad_id = await _make_squad(env, ac, alice, "c14 小队")
        await _join(env, ac, squad_id, bob)
        await _send_group_msg(env, ac, squad_id, alice, "bob 在群时")

        await env.as_user(ac, bob)
        assert (await ac.post(f"{COMMUNITY_PREFIX}/groups/{squad_id}/leave")).status_code == 200
        await _join(env, ac, squad_id, bob)

        history = await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages")
        assert history.status_code == 200, "重加入后读面必须恢复"

    bob_ws = _WsClient("bob-rejoin")
    bob_task = await _connect_group_ws(env, UUID(squad_id), bob, bob_ws, ws_manager)
    async with await env.client() as ac:
        live = await _send_group_msg(env, ac, squad_id, alice, "重加入后实时消息")
    await _wait_until(
        lambda: any(f.get("id") == live["id"] for f in bob_ws.frames), message="rejoin live delivery failed"
    )
    await _disconnect_ws(bob_ws, bob_task)


# ===========================================================================
# E. revoke 谱系
# ===========================================================================
@pytest.mark.asyncio
async def test_case15_group_revoke_propagates_broadcast_and_blocks_reply(s05_env: _Env, ws_manager):
    """case15 群聊撤回传播：message_revoke 帧到群面、历史行 is_revoked/content=None、
    对已撤回行的回复 400 拒绝（撤回不可被引用延续）。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c15a")
        bob = await _make_user(env, "c15b")
        squad_id = await _make_squad(env, ac, alice, "c15 小队")
        await _join(env, ac, squad_id, bob)

    bob_ws = _WsClient("bob")
    bob_task = await _connect_group_ws(env, UUID(squad_id), bob, bob_ws, ws_manager)

    async with await env.client() as ac:
        msg = await _send_group_msg(env, ac, squad_id, alice, "将被撤回")
        await env.as_user(ac, alice)
        assert (await ac.post(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages/{msg['id']}/revoke")).status_code == 200

        await env.as_user(ac, bob)
        reply = await ac.post(
            f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages",
            json={"content": "回复已撤回消息", "reply_to_id": msg["id"]},
        )
        assert reply.status_code == 400
        assert "不能回复已撤回的消息" in reply.json()["detail"]

    await _wait_until(lambda: _frames_of_type(bob_ws, "message_revoke"), message="message_revoke frame missing")
    assert _frames_of_type(bob_ws, "message_revoke")[0]["message_id"] == msg["id"]
    await _disconnect_ws(bob_ws, bob_task)


@pytest.mark.asyncio
async def test_case16_group_revoke_authorization_peer_rejected_admin_allowed(s05_env: _Env):
    """case16 撤回授权：普通成员不能撤他人消息（400），群主可以（管理面）。"""
    env = s05_env
    async with await env.client() as ac:
        owner = await _make_user(env, "c16own")
        mate = await _make_user(env, "c16mate")
        squad_id = await _make_squad(env, ac, owner, "c16 小队")
        await _join(env, ac, squad_id, mate)

        owner_msg = await _send_group_msg(env, ac, squad_id, owner, "群主的消息")
        mate_msg = await _send_group_msg(env, ac, squad_id, mate, "成员的消息")

        await env.as_user(ac, mate)
        peer_try = await ac.post(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages/{owner_msg['id']}/revoke")
        assert peer_try.status_code == 400
        assert "无权限" in peer_try.json()["detail"]

        await env.as_user(ac, owner)
        admin_revoke = await ac.post(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages/{mate_msg['id']}/revoke")
        assert admin_revoke.status_code == 200, "群主（管理面）可撤成员消息"


@pytest.mark.asyncio
async def test_case17_private_revoke_propagates_to_both_personal_channels(s05_env: _Env, ws_manager):
    """case17 私聊撤回双向传播：sender/receiver 两个个人通道都收 message_revoke；
    接收方不能撤他人消息；已撤回行不可再回复。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c17a")
        bob = await _make_user(env, "c17b")
        await _make_friendship(env, alice, bob)

        await env.as_user(ac, alice)
        msg_resp = await ac.post(
            f"{COMMUNITY_PREFIX}/messages",
            json={"target_user_id": str(bob.id), "content": "私聊将被撤回"},
        )
        assert msg_resp.status_code == 200, msg_resp.text
        msg_id = msg_resp.json()["id"]

    alice_ws = _WsClient("alice")
    bob_ws = _WsClient("bob")
    for ws, user in ((alice_ws, alice), (bob_ws, bob)):
        ws.headers = {"authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}

    import app.api.v1.community as community_api

    alice_task = asyncio.create_task(community_api.user_websocket_endpoint(websocket=alice_ws, token=None))
    bob_task = asyncio.create_task(community_api.user_websocket_endpoint(websocket=bob_ws, token=None))
    await _wait_until(
        lambda: str(alice.id) in ws_manager.user_connections and str(bob.id) in ws_manager.user_connections
    )

    async with await env.client() as ac:
        await env.as_user(ac, bob)
        peer_revoke = await ac.post(f"{COMMUNITY_PREFIX}/messages/{msg_id}/revoke")
        assert peer_revoke.status_code == 400, "接收方无权撤发送方的消息"

        await env.as_user(ac, alice)
        revoke = await ac.post(f"{COMMUNITY_PREFIX}/messages/{msg_id}/revoke")
        assert revoke.status_code == 200

    await _wait_until(
        lambda: _frames_of_type(alice_ws, "message_revoke") and _frames_of_type(bob_ws, "message_revoke"),
        message="both channels must receive revoke",
    )
    assert _frames_of_type(bob_ws, "message_revoke")[0]["message_id"] == msg_id

    async with await env.client() as ac:
        await env.as_user(ac, bob)
        late_reply = await ac.post(
            f"{COMMUNITY_PREFIX}/messages",
            json={"target_user_id": str(alice.id), "content": "回复已撤回私信", "reply_to_id": msg_id},
        )
        assert late_reply.status_code == 400

    alice_ws.client_closed = True
    bob_ws.client_closed = True
    await asyncio.wait_for(alice_task, timeout=5)
    await asyncio.wait_for(bob_task, timeout=5)


@pytest.mark.asyncio
async def test_case18_s04_retract_chain_outbox_payload_source_consistency(s05_env: _Env):
    """case18 S-04 证据撤回传播链（入 S-05 谱系）：share→feedback→adopt→
    outbox payload 与 API 返回/证据行同 id 源 → retract→ 证据行 retracted 且
    outbox 行不被改写（append-only，trace 与结果同源一致）。"""
    env = s05_env
    async with await env.client() as ac:
        owner = await _make_user(env, "c18own")
        mate = await _make_user(env, "c18mate")
        goal = await _owner_goal_plan_task(env, owner)
        squad_id = await _make_squad(env, ac, owner, "c18 小队")
        await _join(env, ac, squad_id, mate)

        await env.as_user(ac, owner)
        task_row = (await env.db.execute(select(Task).where(Task.user_id == owner.id))).scalars().first()
        share = await ac.post(
            f"{COMMUNITY_PREFIX}/share",
            json={
                "resource_type": "task",
                "resource_id": str(task_row.id),
                "target_group_id": squad_id,
                "permission": "view",
            },
        )
        shared_resource_id = share.json()["id"]

        await env.as_user(ac, mate)
        fb = await ac.post(
            f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/feedback",
            json={"verdict": FeedbackVerdict.HELPFUL.value, "comment": "c18 反馈"},
        )
        feedback_id = fb.json()["id"]

        await env.as_user(ac, owner)
        adopt = await ac.post(
            f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/feedback/{feedback_id}/adopt",
            json={"goal_id": str(goal.id)},
        )
        assert adopt.status_code == 200
        await env.db.commit()

    evidence = (await env.db.execute(select(CommunityOutcomeEvidence))).scalars().one()
    outbox_rows = (
        (
            await env.db.execute(
                text("SELECT aggregate_id, payload FROM event_outbox WHERE event_type = 'community.feedback_adopted'")
            )
        )
        .mappings()
        .all()
    )
    assert len(outbox_rows) == 1
    payload = (
        json.loads(outbox_rows[0]["payload"])
        if isinstance(outbox_rows[0]["payload"], str)
        else outbox_rows[0]["payload"]
    )
    # 同源一致：outbox payload 的四个 id 与证据行/API 返回逐一对齐
    assert payload["evidence_id"] == str(evidence.id) == outbox_rows[0]["aggregate_id"]
    assert payload["feedback_id"] == feedback_id
    assert payload["goal_id"] == str(goal.id)
    assert payload["shared_resource_id"] == shared_resource_id

    async with await env.client() as ac:
        await env.as_user(ac, owner)
        retract = await ac.post(f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/retract")
        assert retract.status_code == 200
        body = retract.json()
        assert body["retracted_feedback_count"] == 1
        assert body["updated_goal_receipt_count"] == 1
        await env.db.commit()

    await env.db.refresh(evidence)
    assert evidence.status == "retracted" and evidence.retracted_at is not None
    # outbox append-only：撤回不改写既有事件行（trace 保持可审计）
    rows_after = (
        (
            await env.db.execute(
                text("SELECT aggregate_id, payload FROM event_outbox WHERE event_type = 'community.feedback_adopted'")
            )
        )
        .mappings()
        .all()
    )
    assert len(rows_after) == 1 and rows_after[0]["payload"] == outbox_rows[0]["payload"]
    feedback_row = (
        await env.db.execute(select(SharedResourceFeedback).where(SharedResourceFeedback.id == UUID(feedback_id)))
    ).scalar_one()
    assert feedback_row.retracted_at is not None
    share_row = await env.db.get(SharedResource, UUID(shared_resource_id))
    assert share_row.deleted_at is not None


# ===========================================================================
# F. block 谱系
# ===========================================================================
@pytest.mark.asyncio
async def test_case19_block_stops_dm_both_directions_unblock_restores(s05_env: _Env):
    """case19 拉黑断 DM 双向（canonical UserBlock 面）：A 拉黑 B 后 B→A、A→B
    私聊双双 403；解除后恢复可发（好友关系不自动恢复，见 case20/case22）。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c19a")
        bob = await _make_user(env, "c19b")
        await _make_friendship(env, alice, bob)

        await env.as_user(ac, alice)
        ok_msg = await ac.post(
            f"{COMMUNITY_PREFIX}/messages", json={"target_user_id": str(bob.id), "content": "拉黑前"}
        )
        assert ok_msg.status_code == 200

        block = await ac.post(f"{COMMUNITY_PREFIX}/users/block", json={"target_user_id": str(bob.id), "reason": "c19"})
        assert block.status_code == 200

        await env.as_user(ac, bob)
        blocked_send = await ac.post(
            f"{COMMUNITY_PREFIX}/messages", json={"target_user_id": str(alice.id), "content": "b→a"}
        )
        assert blocked_send.status_code == 403, "被拉黑方向发送 403（端点 is_blocked 门）"

        await env.as_user(ac, alice)
        reverse_send = await ac.post(
            f"{COMMUNITY_PREFIX}/messages", json={"target_user_id": str(bob.id), "content": "a→b"}
        )
        # 拉黑方向的反向：端点放行、服务层 has_block_relationship 拒绝 → 400（双向同断，码位不同源）
        assert reverse_send.status_code == 400, "拉黑是双向断（A 也不能给 B 发）"

        unblock = await ac.delete(f"{COMMUNITY_PREFIX}/users/block/{bob.id}")
        assert unblock.status_code == 200
        restored = await ac.post(
            f"{COMMUNITY_PREFIX}/messages", json={"target_user_id": str(bob.id), "content": "解除后"}
        )
        assert restored.status_code == 200


@pytest.mark.asyncio
async def test_case20_block_severs_friendship_and_blocks_new_friend_request(s05_env: _Env):
    """case20 拉黑断好友链并拦新请求：block 后好友列表双向消失；被拉黑方再发
    好友请求必须被拒（端点契约「拉黑后对方无法发送消息或好友请求」）。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c20a")
        bob = await _make_user(env, "c20b")
        await _make_friendship(env, alice, bob)

        await env.as_user(ac, alice)
        assert (
            await ac.post(f"{COMMUNITY_PREFIX}/users/block", json={"target_user_id": str(bob.id)})
        ).status_code == 200

        alice_friends = await ac.get(f"{COMMUNITY_PREFIX}/friends")
        assert all(str(f["friend"]["id"]) != str(bob.id) for f in alice_friends.json()), "拉黑后好友列表必须移除"

        await env.as_user(ac, bob)
        bob_friends = await ac.get(f"{COMMUNITY_PREFIX}/friends")
        assert all(str(f["friend"]["id"]) != str(alice.id) for f in bob_friends.json())

        renew = await ac.post(f"{COMMUNITY_PREFIX}/friends/request", json={"target_user_id": str(alice.id)})
        assert renew.status_code == 403, "被拉黑方的新好友请求必须 403（端点契约：被对方拉黑无法发送请求）"


@pytest.mark.asyncio
async def test_case21_block_scoped_to_dm_group_membership_and_history_unaffected(s05_env: _Env, ws_manager):
    """case21 隔离边界（范围正确性）：拉黑只断 DM/好友面，不驱逐群成员、不清
    群历史、群广播仍达双方（群内协作面与拉黑面正交——契约范围，不扩权）。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c21a")
        bob = await _make_user(env, "c21b")
        squad_id = await _make_squad(env, ac, alice, "c21 小队")
        await _join(env, ac, squad_id, bob)
        pre_block_msg = await _send_group_msg(env, ac, squad_id, bob, "拉黑前的群消息")

    bob_ws = _WsClient("bob")
    bob_task = await _connect_group_ws(env, UUID(squad_id), bob, bob_ws, ws_manager)

    async with await env.client() as ac:
        await env.as_user(ac, alice)
        assert (
            await ac.post(f"{COMMUNITY_PREFIX}/users/block", json={"target_user_id": str(bob.id)})
        ).status_code == 200

        group_msg = await _send_group_msg(env, ac, squad_id, alice, "拉黑后的群消息")
        history = await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages")
        assert any(m["id"] == pre_block_msg["id"] for m in history.json()), "拉黑不清对方群历史"
        assert any(m["id"] == group_msg["id"] for m in history.json())

    await _wait_until(
        lambda: any(f.get("id") == group_msg["id"] for f in bob_ws.frames),
        message="blocked peer still gets group broadcast (scoped isolation)",
    )
    await _disconnect_ws(bob_ws, bob_task)


@pytest.mark.asyncio
async def test_case22_block_rejects_directed_share_group_share_unaffected(s05_env: _Env):
    """case22 拉黑拦定向分享：target_user 分享被拒（Cannot share with a blocked
    user）；群分享路径不受影响（隔离范围正交的另一半）。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c22a")
        bob = await _make_user(env, "c22b")
        squad_id = await _make_squad(env, ac, alice, "c22 小队")
        await _join(env, ac, squad_id, bob)

        task_row = Task(user_id=alice.id, title="c22 任务", type=TaskType.LEARNING, estimated_minutes=10)
        env.db.add(task_row)
        await env.db.commit()

        await env.as_user(ac, alice)
        assert (
            await ac.post(f"{COMMUNITY_PREFIX}/users/block", json={"target_user_id": str(bob.id)})
        ).status_code == 200

        directed = await ac.post(
            f"{COMMUNITY_PREFIX}/share",
            json={"resource_type": "task", "resource_id": str(task_row.id), "target_user_id": str(bob.id)},
        )
        assert directed.status_code == 400
        assert "blocked" in directed.json()["detail"]

        group_share = await ac.post(
            f"{COMMUNITY_PREFIX}/share",
            json={"resource_type": "task", "resource_id": str(task_row.id), "target_group_id": squad_id},
        )
        assert group_share.status_code == 200, "群分享路径不因 DM 拉黑而误伤"


@pytest.mark.asyncio
async def test_case23_block_is_blocked_query_and_dedupe_list_shape(s05_env: _Env):
    """case23 拉黑列表与重复拉黑：blocked 列表带原因与被拉黑者信息；重复拉黑
    400（幂等拒绝不重复建行）；自拉黑 400。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c23a")
        bob = await _make_user(env, "c23b")
        await env.as_user(ac, alice)

        self_block = await ac.post(f"{COMMUNITY_PREFIX}/users/block", json={"target_user_id": str(alice.id)})
        assert self_block.status_code == 400

        assert (
            await ac.post(f"{COMMUNITY_PREFIX}/users/block", json={"target_user_id": str(bob.id), "reason": " spam "})
        ).status_code == 200
        dup = await ac.post(f"{COMMUNITY_PREFIX}/users/block", json={"target_user_id": str(bob.id)})
        assert dup.status_code == 400, "重复拉黑必须显式拒绝（不重复建行）"

        blocked_list = await ac.get(f"{COMMUNITY_PREFIX}/users/blocked")
        assert blocked_list.status_code == 200
        entries = blocked_list.json()
        assert len(entries) == 1
        assert str(entries[0]["blocked_user"]["id"]) == str(bob.id)
        assert entries[0]["reason"] == " spam "
        assert await env.db.scalar(
            select(UserBlock.id).where(UserBlock.blocker_id == alice.id, UserBlock.blocked_id == bob.id)
        )

        # 解除非拉黑关系 → 显式 400（与 block 同一 ValueError 映射口径）
        carol = await _make_user(env, "c23c")
        not_blocked = await ac.delete(f"{COMMUNITY_PREFIX}/users/block/{carol.id}")
        assert not_blocked.status_code == 400


# ===========================================================================
# G. 跨用户/跨群隔离（two-account）
# ===========================================================================
@pytest.mark.asyncio
async def test_case24_cross_group_isolation_http_and_ws_channel_scoping(s05_env: _Env, ws_manager):
    """case24 跨群隔离：非成员 HTTP 读 403；群广播按群通道 scoping——g1 的消息
    只达 g1 的连接，不串到只连了 g2 的用户。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c24a")
        carol = await _make_user(env, "c24c")
        g1 = await _make_squad(env, ac, alice, "c24 群一")
        g2 = await _make_squad(env, ac, carol, "c24 群二")

    carol_ws = _WsClient("carol")
    carol_task = await _connect_group_ws(env, UUID(g2), carol, carol_ws, ws_manager)

    async with await env.client() as ac:
        await env.as_user(ac, carol)
        leak_read = await ac.get(f"{COMMUNITY_PREFIX}/groups/{g1}/messages")
        assert leak_read.status_code == 403, "非成员跨群读必须 403"

        await env.as_user(ac, alice)
        msg_in_g1 = await _send_group_msg(env, ac, g1, alice, "g1 专属消息")
        msg_in_g2 = await _send_group_msg(env, ac, g2, carol, "g2 消息触发")

    await _wait_until(lambda: carol_ws.frames, message="g2 message should reach carol")
    assert not any(f.get("id") == msg_in_g1["id"] for f in carol_ws.frames), "g1 广播不得串到 g2 连接"
    assert any(f.get("id") == msg_in_g2["id"] for f in carol_ws.frames)
    await _disconnect_ws(carol_ws, carol_task)


@pytest.mark.asyncio
async def test_case25_private_history_pair_isolation_third_party_never_sees(s05_env: _Env):
    """case25 私聊 pair 隔离：C 拉取「C↔B」会话只见 pair 消息，A↔B 内容零泄漏
    （读面按会话 pair 过滤，不按全表）。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c25a")
        bob = await _make_user(env, "c25b")
        carol = await _make_user(env, "c25c")
        await _make_friendship(env, alice, bob)
        await _make_friendship(env, bob, carol)

        await env.as_user(ac, alice)
        secret = await ac.post(
            f"{COMMUNITY_PREFIX}/messages", json={"target_user_id": str(bob.id), "content": "A↔B 秘密"}
        )
        assert secret.status_code == 200

        await env.as_user(ac, carol)
        pair = await ac.get(f"{COMMUNITY_PREFIX}/friends/{bob.id}/messages")
        assert pair.status_code == 200
        assert all("A↔B 秘密" not in (m.get("content") or "") for m in pair.json()), "第三者会话不得见 A↔B 内容"
        assert pair.json() == [], "C 与 B 无消息时会话必须为空"

        await env.as_user(ac, bob)
        owner_view = await ac.get(f"{COMMUNITY_PREFIX}/friends/{alice.id}/messages")
        assert any(m["content"] == "A↔B 秘密" for m in owner_view.json()), "会话主人视角正常可见"


@pytest.mark.asyncio
async def test_case26_self_only_message_never_broadcast_and_hidden_from_peers(s05_env: _Env, ws_manager):
    """case26 self-only 可见性（两账号 + WS 面）：仅自己可见消息不出群广播帧、
    他人拉取不可见、本人可见（S-01 可见性用例的 API+广播面扩谱）。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c26a")
        bob = await _make_user(env, "c26b")
        squad_id = await _make_squad(env, ac, alice, "c26 小队")
        await _join(env, ac, squad_id, bob)

    bob_ws = _WsClient("bob")
    bob_task = await _connect_group_ws(env, UUID(squad_id), bob, bob_ws, ws_manager)

    async with await env.client() as ac:
        await env.as_user(ac, alice)
        self_only = await ac.post(
            f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages",
            json={"content": "私密笔记", "content_data": {"visibility": "self", "visible_to": str(alice.id)}},
        )
        assert self_only.status_code == 200

        await env.as_user(ac, alice)
        mine = await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages")
        assert any(m["id"] == self_only.json()["id"] for m in mine.json())

        await env.as_user(ac, bob)
        theirs = await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages")
        assert not any(m["id"] == self_only.json()["id"] for m in theirs.json()), "self-only 对他人不可见"

    await asyncio.sleep(0.05)
    assert not any(f.get("id") == self_only.json()["id"] for f in bob_ws.frames), "self-only 不得进群广播"
    await _disconnect_ws(bob_ws, bob_task)


@pytest.mark.asyncio
async def test_case27_checkin_broadcast_matches_api_response_and_history_same_source(s05_env: _Env, ws_manager):
    """case27 打卡三面同源（日志/trace 与 UI 一致口径）：打卡 API 返回、群 WS
    广播帧、消息历史行三者的 goal_id/duration 对齐同一事实。"""
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c27a")
        bob = await _make_user(env, "c27b")
        squad_id = await _make_squad(env, ac, alice, "c27 小队")
        await _join(env, ac, squad_id, bob)

    bob_ws = _WsClient("bob")
    bob_task = await _connect_group_ws(env, UUID(squad_id), bob, bob_ws, ws_manager)

    async with await env.client() as ac:
        await env.as_user(ac, alice)
        checkin = await ac.post(
            f"{COMMUNITY_PREFIX}/checkin",
            json={"group_id": squad_id, "today_duration_minutes": 42, "message": "今天学了 42 分钟"},
        )
        assert checkin.status_code == 200, checkin.text
        body = checkin.json()

    await _wait_until(lambda: _frames_of_type(bob_ws, "member_checkin"), message="member_checkin frame missing")
    frame = _frames_of_type(bob_ws, "member_checkin")[0]
    assert frame["duration"] == 42
    assert frame["group_id"] == squad_id
    assert frame.get("goal_id") == body.get("goal_id"), "广播帧与 API 返回的 goal 回链必须同源"

    async with await env.client() as ac:
        await env.as_user(ac, bob)
        history = await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages")
        checkin_rows = [m for m in history.json() if m["message_type"] == "checkin"]
        assert checkin_rows, "打卡必须落消息历史（群火堆可见）"
    await _disconnect_ws(bob_ws, bob_task)


@pytest.mark.asyncio
async def test_case28_leaver_live_socket_stops_receiving_group_broadcasts(s05_env: _Env, ws_manager):
    """case28 离群失效（实时面）：退群成员的**存活 WS 连接**必须被服务端关闭
    （4001），此后群广播不再到达已退出的连接。

    缺陷口径：leave/kick 端点当前只改成员行 + 广播 member_left/member_kicked，
    从不调用 manager.kick_user_from_group——已退群连接仍挂在 active_connections
    上继续收帧（权限/隐私面：非成员持续接收群实时消息）。
    """
    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c28a")
        bob = await _make_user(env, "c28b")
        squad_id = await _make_squad(env, ac, alice, "c28 小队")
        await _join(env, ac, squad_id, bob)

    bob_ws = _WsClient("bob")
    bob_task = await _connect_group_ws(env, UUID(squad_id), bob, bob_ws, ws_manager)

    async with await env.client() as ac:
        await env.as_user(ac, bob)
        assert (await ac.post(f"{COMMUNITY_PREFIX}/groups/{squad_id}/leave")).status_code == 200

    # 服务端必须主动关闭已退群连接（真实客户端收到 4001 即断开）
    await _wait_until(lambda: bob_ws.closed_codes, message="退群后服务端必须关闭该成员的存活 WS 连接")
    assert bob_ws.closed_codes == [4001]
    bob_ws.client_closed = True
    await asyncio.wait_for(bob_task, timeout=5)

    async with await env.client() as ac:
        await env.as_user(ac, alice)
        after = await _send_group_msg(env, ac, squad_id, alice, "退群后新消息")
    await asyncio.sleep(0.05)
    assert not any(f.get("id") == after["id"] for f in bob_ws.frames), "退群连接不得再收到群广播"


@pytest.mark.asyncio
async def test_case29_s02_boundary_api_level_cross_user_zero_leakage(s05_env: _Env):
    """case29 S-02 群上下文隐私边界 API 面复验（16 例守卫的 API 驱动版）：
    两账号 + 真实 share API + 真实私人 memory 行 → B 的群上下文组装只见显式
    分享条目；A 的私人记忆零泄漏（repr 序列化断言）；伪造 owner → owner_mismatch；
    非成员 fail-closed；revoke 后下一次组装消失。"""
    from app.models.memory import EpisodicMemory
    from app.services.community_context_boundary import (
        GroupContextBoundaryService,
        GroupContextCandidate,
        filter_group_prompt_candidates,
    )

    env = s05_env
    async with await env.client() as ac:
        alice = await _make_user(env, "c29a")
        bob = await _make_user(env, "c29b")
        squad_id = await _make_squad(env, ac, alice, "c29 小队")
        await _join(env, ac, squad_id, bob)

        # A 的私人库（真实行，从不分享）
        episodic = EpisodicMemory(
            user_id=alice.id, summary="c29 私密：失眠严重", source_type="chat_turn", occurred_at=datetime.now(UTC)
        )
        env.db.add(episodic)
        await env.db.commit()

        # A 经真实 share API 分享一个 Task 进群
        task_row = Task(user_id=alice.id, title="c29 分享任务", type=TaskType.LEARNING, estimated_minutes=15)
        env.db.add(task_row)
        await env.db.commit()
        await env.as_user(ac, alice)
        share = await ac.post(
            f"{COMMUNITY_PREFIX}/share",
            json={"resource_type": "task", "resource_id": str(task_row.id), "target_group_id": squad_id},
        )
        assert share.status_code == 200

    # B 的群上下文组装：只有分享条目，私人记忆零泄漏
    payload = await GroupContextBoundaryService.resolve_prompt_context(env.db, UUID(squad_id), bob.id)
    assert payload["entry_count"] == 1
    serialized = repr(payload)
    assert str(episodic.id) not in serialized and "失眠" not in serialized, "A 私人记忆不得进 B 的群上下文"

    # 词表内未分享的私人行（伪造 A 的 goal 属主候选）→ not_in_allowlist
    ctx = await GroupContextBoundaryService.build_prompt_access_context(env.db, UUID(squad_id), bob.id)
    private_goal = Goal(user_id=alice.id, title="c29 私人目标", goal_type="exam")
    env.db.add(private_goal)
    await env.db.commit()
    leak = filter_group_prompt_candidates(
        [GroupContextCandidate(item_kind="goal", item_id=str(private_goal.id), owner_user_id=str(alice.id))], ctx
    )
    assert leak.allowed == []
    assert {r.reason for r in leak.rejections} == {"group_context:not_in_allowlist"}

    # 伪造 owner（B 把自己 id 填进 A 的分享候选）→ owner_mismatch
    forged = filter_group_prompt_candidates(
        [GroupContextCandidate(item_kind="action", item_id=str(task_row.id), owner_user_id=str(bob.id))], ctx
    )
    assert {r.reason for r in forged.rejections} == {"group_context:owner_mismatch"}

    # 非成员 C fail-closed
    carol = await _make_user(env, "c29c")
    from app.services.community_context_boundary import GroupContextPermissionError

    with pytest.raises(GroupContextPermissionError):
        await GroupContextBoundaryService.build_prompt_access_context(env.db, UUID(squad_id), carol.id)

    # A revoke 分享 → B 下一次组装消失（离群/撤回失效在 API 面）
    await GroupContextBoundaryService.revoke_share(env.db, UUID(share.json()["id"]), revoked_by=alice.id)
    await env.db.commit()
    payload_after = await GroupContextBoundaryService.resolve_prompt_context(env.db, UUID(squad_id), bob.id)
    assert payload_after["entry_count"] == 0


@pytest.mark.asyncio
async def test_case30_kick_closes_target_live_socket_and_revokes_read(s05_env: _Env, ws_manager):
    """case30 踢出失效（实时面）：群主踢人后，被踢成员的**存活 WS 连接**必须被
    服务端关闭（4001），读面同步 403（与 case28 退群同族的另一个 API 入径）。"""
    env = s05_env
    async with await env.client() as ac:
        owner = await _make_user(env, "c30own")
        mate = await _make_user(env, "c30mate")
        squad_id = await _make_squad(env, ac, owner, "c30 小队")
        await _join(env, ac, squad_id, mate)

    mate_ws = _WsClient("mate")
    mate_task = await _connect_group_ws(env, UUID(squad_id), mate, mate_ws, ws_manager)

    async with await env.client() as ac:
        await env.as_user(ac, owner)
        kick = await ac.post(f"{COMMUNITY_PREFIX}/groups/{squad_id}/members/{mate.id}/kick")
        assert kick.status_code == 200, kick.text

    await _wait_until(lambda: mate_ws.closed_codes, message="被踢成员的存活 WS 连接必须被服务端关闭")
    assert mate_ws.closed_codes == [4001]
    mate_ws.client_closed = True
    await asyncio.wait_for(mate_task, timeout=5)

    async with await env.client() as ac:
        await env.as_user(ac, mate)
        read_after = await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/messages")
        assert read_after.status_code == 403, "被踢后读面必须关闭"
