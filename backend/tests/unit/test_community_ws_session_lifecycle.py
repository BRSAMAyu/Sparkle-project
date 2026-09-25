"""S-01 段一：群聊 WS 连接期不得长持连接池连接（红测先行）。

缺陷（审计发现，见 v3-output/WT361-S01-READMODEL/REPORT.md §3.2）：
`community.py` 的群组 WebSocket 端点曾通过 `Depends(get_db)` 注入请求级会话，
会员校验的一次 SELECT 开启隐式事务后，连接在整个 WS 连接期被占住
（会话随 handler 返回才关闭，而 handler 只在客户端断开时返回）。
每个挂机的群成员 = 一条被占的池连接 → DB_POOL_SIZE+max_overflow 之下
群聊在线即池耗尽，拖垮引擎全库访问面。

钉三条面：
1. 依赖面——群聊 WS 路由的依赖列表里不得出现 `get_db`（结构断言）；
2. 行为面（成员路径）——会话必须在 `manager.connect` 之前关闭
   （事件顺序断言），断开后有 disconnect 清理；
3. 行为面（非成员路径）——4003 拒绝且绝不 connect。
"""

from __future__ import annotations

import uuid as uuid_mod

import pytest
from fastapi import WebSocketDisconnect

from app.api.v1 import community as community_module
from app.db.session import get_db


def _find_group_ws_route():
    for route in community_module.router.routes:
        path = getattr(route, "path", "")
        if path.endswith("/groups/{group_id}/ws"):
            return route
    raise AssertionError("community group ws route not found")


def test_group_ws_route_does_not_depend_on_request_scoped_db() -> None:
    """依赖面：群聊 WS 路由不得注入 get_db（会话生命周期必须短于连接生命周期）。"""
    route = _find_group_ws_route()
    for dep in route.dependant.dependencies:
        assert dep.call is not get_db, (
            "群聊 WS 端点注入了请求级 get_db：WS 连接期会占住连接池连接"
            "（S-01 段一审计缺陷），会员校验应改用短生命周期 AsyncSessionLocal。"
        )


class _FakeResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _FakeSession:
    """记录开/关与查询事件的假会话（异步上下文管理器）。"""

    def __init__(self, events: list[str], member: object) -> None:
        self._events = events
        self._member = member

    async def __aenter__(self) -> _FakeSession:
        self._events.append("session_open")
        return self

    async def __aexit__(self, *args: object) -> None:
        self._events.append("session_close")

    async def execute(self, stmt: object) -> _FakeResult:
        self._events.append("query")
        return _FakeResult(self._member)


class _FakeWebSocket:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.query_params: dict[str, str] = {}
        self.closed_codes: list[int] = []
        self.accepted = False

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int = 1000) -> None:
        self.closed_codes.append(code)

    async def receive_text(self) -> str:
        raise WebSocketDisconnect(code=1000)


class _FakeManager:
    def __init__(self, events: list[str]) -> None:
        self._events = events
        self.connected: list[tuple[object, str, str]] = []
        self.disconnected: list[tuple[object, str, str]] = []

    async def connect(self, websocket: object, group_id: str, user_id: str) -> None:
        self._events.append("manager_connect")
        # 与真实 ConnectionManager.connect 同契约：accept 在 connect 内发生
        accept = getattr(websocket, "accept", None)
        if accept is not None:
            await accept()
        self.connected.append((websocket, group_id, user_id))

    def disconnect(self, websocket: object, group_id: str, user_id: str) -> None:
        self._events.append("manager_disconnect")
        self.disconnected.append((websocket, group_id, user_id))

    async def broadcast(self, message: object, group_id: str) -> None:  # pragma: no cover
        raise AssertionError("broadcast 不应在本测试中被触达")


async def _fake_decode_token(token: str, expected_type: str = "access") -> dict[str, str]:
    return {"sub": "11111111-1111-1111-1111-111111111111"}


def _patch_common(monkeypatch: pytest.MonkeyPatch, events: list[str], member: object) -> _FakeManager:
    monkeypatch.setattr(community_module.settings, "WS_ALLOW_QUERY_TOKEN", True)
    monkeypatch.setattr(community_module, "AsyncSessionLocal", lambda: _FakeSession(events, member))
    monkeypatch.setattr(community_module, "decode_token", _fake_decode_token)
    manager = _FakeManager(events)
    monkeypatch.setattr(community_module, "manager", manager)
    return manager


@pytest.mark.asyncio
async def test_ws_session_closed_before_connect_member_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """行为面（成员）：会话先关、连接后建；断开时 disconnect 清理。"""
    events: list[str] = []
    ws = _FakeWebSocket()
    _patch_common(monkeypatch, events, member=object())

    group_id = uuid_mod.uuid4()
    await community_module.websocket_endpoint(websocket=ws, group_id=group_id, token="tok")

    assert ws.accepted is True, "成员应被 accept"
    assert "query" in events, "会员校验应执行成员查询"
    assert "session_close" in events, "会话必须显式关闭"
    assert "manager_connect" in events, "成员应被记录连接"
    # 会话必须在建立 WS 连接前关闭（归还池连接）
    assert events.index("session_close") < events.index("manager_connect"), (
        f"会话关闭必须先于 manager.connect（事件序列={events}）"
    )
    assert "manager_disconnect" in events, "断开后应清理连接"


@pytest.mark.asyncio
async def test_ws_non_member_rejected_without_connect(monkeypatch: pytest.MonkeyPatch) -> None:
    """行为面（非成员）：4003 拒绝、绝不 connect。"""
    events: list[str] = []
    ws = _FakeWebSocket()
    manager = _patch_common(monkeypatch, events, member=None)

    group_id = uuid_mod.uuid4()
    await community_module.websocket_endpoint(websocket=ws, group_id=group_id, token="tok")

    assert ws.closed_codes == [4003]
    assert not manager.connected
    assert "manager_connect" not in events
