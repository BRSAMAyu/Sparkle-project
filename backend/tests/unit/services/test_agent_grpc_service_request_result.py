"""V3-FIX-334: GetRequestResult 三态解析（引擎侧）单元测试。

网关去重命中后向引擎查询原请求结果：completed（回放 payload）/ running（ack）/
unknown（网关保留 duplicate_request 兜底）。权威源裁决：响应缓存
（state_manager.get_cached_response）为 completed 判定与回放体的唯一权威源；
run ledger 会话索引作为 running/状态 fallback。
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import grpc
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "app" / "gen" / "agent" / "v1"))

from app.gen.agent.v1 import agent_service_pb2
from app.services.agent_grpc_service import (
    REQUEST_RESULT_COMPLETED,
    REQUEST_RESULT_RUNNING,
    REQUEST_RESULT_UNKNOWN,
    AgentServiceImpl,
    resolve_request_result,
)

_SESSION_KEY_PREFIX = "run_ledger:session:"
_RESPONSE_KEY_TEMPLATE = "session:{session_id}:response:{request_id}"


class _FakeStateManager:
    """Mirrors SessionStateManager.get_cached_response for (session_id, request_id)."""

    def __init__(self) -> None:
        self.cached: dict[tuple[str, str], dict[str, object]] = {}

    async def get_cached_response(self, session_id: str, request_id: str) -> dict[str, object] | None:
        return self.cached.get((session_id, request_id))


class _FakeRedis:
    """Minimal get/setex store mirroring the run ledger key contract."""

    def __init__(self) -> None:
        self.kv: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.kv.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> bool:
        self.kv[key] = value
        return True


def _make_service(
    state_manager: _FakeStateManager | None = None,
    redis_client: _FakeRedis | None = None,
) -> AgentServiceImpl:
    orchestrator = SimpleNamespace(
        state_manager=state_manager if state_manager is not None else _FakeStateManager(),
        redis=redis_client if redis_client is not None else _FakeRedis(),
    )
    return AgentServiceImpl(orchestrator=orchestrator, db_session_factory=lambda: None)  # type: ignore[arg-type]


class _FakeContext:
    def __init__(self, metadata: list[tuple[str, str]] | None = None) -> None:
        self._metadata = metadata or []
        self.code: grpc.StatusCode | None = None
        self.details: str | None = None

    def invocation_metadata(self):
        return self._metadata

    def set_code(self, code: grpc.StatusCode) -> None:
        self.code = code

    def set_details(self, details: str) -> None:
        self.details = details


def _seed_ledger(
    redis_client: _FakeRedis,
    *,
    session_id: str,
    trace_id: str,
    request_id: str,
    status: str,
) -> None:
    redis_client.kv[f"{_SESSION_KEY_PREFIX}{session_id}"] = trace_id
    summary = {
        "trace_id": trace_id,
        "session_id": session_id,
        "request_id": request_id,
        "status": status,
    }
    import json

    redis_client.kv[f"run_ledger:summary:{trace_id}"] = json.dumps(summary)


_COMPLETED_BODY = {
    "message": "已完成的回答全文",
    "tool_results": [],
    "metadata": {"foo": "bar"},
}


# ---------------------------------------------------------------------------
# resolve_request_result（纯裁决逻辑）
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_cache_hit_is_completed_with_replay_payload() -> None:
    sm = _FakeStateManager()
    sm.cached[("sess-1", "req-1")] = dict(_COMPLETED_BODY)

    status, message, payload, trace_id = await resolve_request_result(
        state_manager=sm, redis_client=_FakeRedis(), session_id="sess-1", request_id="req-1"
    )

    assert status == REQUEST_RESULT_COMPLETED
    assert message == "已完成的回答全文"
    assert payload == _COMPLETED_BODY
    assert trace_id == ""


@pytest.mark.unit
async def test_cache_is_authoritative_over_ledger() -> None:
    """缓存命中时直接 completed，即使 ledger 里同请求还是 running（缓存为权威源）。"""
    sm = _FakeStateManager()
    sm.cached[("sess-1", "req-1")] = dict(_COMPLETED_BODY)
    redis_client = _FakeRedis()
    _seed_ledger(redis_client, session_id="sess-1", trace_id="t-1", request_id="req-1", status="running")

    status, message, payload, _ = await resolve_request_result(
        state_manager=sm, redis_client=redis_client, session_id="sess-1", request_id="req-1"
    )

    assert status == REQUEST_RESULT_COMPLETED
    assert message == "已完成的回答全文"
    assert payload == _COMPLETED_BODY


@pytest.mark.unit
async def test_ledger_running_fallback_ack() -> None:
    sm = _FakeStateManager()
    redis_client = _FakeRedis()
    _seed_ledger(redis_client, session_id="sess-1", trace_id="t-1", request_id="req-1", status="running")

    status, message, payload, trace_id = await resolve_request_result(
        state_manager=sm, redis_client=redis_client, session_id="sess-1", request_id="req-1"
    )

    assert status == REQUEST_RESULT_RUNNING
    assert message == ""
    assert payload is None
    assert trace_id == "t-1"


@pytest.mark.unit
async def test_ledger_completed_without_payload_is_honest_unknown() -> None:
    """ledger 说 completed 但回放体缺失（缓存写失败/过期）：不空手回放，诚实 unknown。"""
    sm = _FakeStateManager()
    redis_client = _FakeRedis()
    _seed_ledger(redis_client, session_id="sess-1", trace_id="t-1", request_id="req-1", status="completed")

    status, message, payload, trace_id = await resolve_request_result(
        state_manager=sm, redis_client=redis_client, session_id="sess-1", request_id="req-1"
    )

    assert status == REQUEST_RESULT_UNKNOWN
    assert message == ""
    assert payload is None
    assert trace_id == "t-1"


@pytest.mark.unit
async def test_ledger_request_id_mismatch_is_unknown() -> None:
    """会话索引只存最新 trace：旧请求等值失配 → unknown（网关走 duplicate 兜底）。"""
    sm = _FakeStateManager()
    redis_client = _FakeRedis()
    _seed_ledger(redis_client, session_id="sess-1", trace_id="t-latest", request_id="req-new", status="running")

    status, _, _, _ = await resolve_request_result(
        state_manager=sm, redis_client=redis_client, session_id="sess-1", request_id="req-old"
    )

    assert status == REQUEST_RESULT_UNKNOWN


@pytest.mark.unit
async def test_no_record_anywhere_is_unknown() -> None:
    status, message, payload, trace_id = await resolve_request_result(
        state_manager=_FakeStateManager(), redis_client=_FakeRedis(), session_id="sess-1", request_id="req-x"
    )

    assert status == REQUEST_RESULT_UNKNOWN
    assert message == ""
    assert payload is None
    assert trace_id == ""


@pytest.mark.unit
async def test_ledger_summary_missing_is_unknown() -> None:
    """session 索引指向的 summary 已过期（TTL 内索引先行过期不一致）：诚实 unknown。"""
    sm = _FakeStateManager()
    redis_client = _FakeRedis()
    redis_client.kv[f"{_SESSION_KEY_PREFIX}sess-1"] = "t-gone"

    status, _, _, _ = await resolve_request_result(
        state_manager=sm, redis_client=redis_client, session_id="sess-1", request_id="req-1"
    )

    assert status == REQUEST_RESULT_UNKNOWN


@pytest.mark.unit
async def test_state_manager_absent_is_unknown_not_crash() -> None:
    redis_client = _FakeRedis()

    status, _, _, _ = await resolve_request_result(
        state_manager=None, redis_client=redis_client, session_id="sess-1", request_id="req-1"
    )

    assert status == REQUEST_RESULT_UNKNOWN


# ---------------------------------------------------------------------------
# AgentServiceImpl.GetRequestResult（handler 契约：鉴权/参数/状态映射）
# ---------------------------------------------------------------------------


def _completed_pb_response() -> agent_service_pb2.GetRequestResultResponse:
    return agent_service_pb2.GetRequestResultResponse(
        status=agent_service_pb2.RequestResultStatus.REQUEST_RESULT_COMPLETED,
        message="已完成的回答全文",
    )


@pytest.mark.unit
async def test_handler_requires_user_id_metadata() -> None:
    service = _make_service()
    ctx = _FakeContext(metadata=[])

    resp = await service.GetRequestResult(
        agent_service_pb2.GetRequestResultRequest(user_id="u-1", session_id="sess-1", request_id="req-1"),
        ctx,  # type: ignore[arg-type]
    )

    assert ctx.code == grpc.StatusCode.UNAUTHENTICATED
    assert resp.status == agent_service_pb2.RequestResultStatus.REQUEST_RESULT_UNKNOWN


@pytest.mark.unit
async def test_handler_blocks_user_id_spoofing() -> None:
    service = _make_service()
    ctx = _FakeContext(metadata=[("user-id", "real-user")])

    resp = await service.GetRequestResult(
        agent_service_pb2.GetRequestResultRequest(user_id="spoofed-user", session_id="sess-1", request_id="req-1"),
        ctx,  # type: ignore[arg-type]
    )

    assert ctx.code == grpc.StatusCode.PERMISSION_DENIED
    assert resp.status == agent_service_pb2.RequestResultStatus.REQUEST_RESULT_UNKNOWN


@pytest.mark.unit
async def test_handler_requires_session_and_request_id() -> None:
    service = _make_service()
    ctx = _FakeContext(metadata=[("user-id", "u-1")])

    resp = await service.GetRequestResult(
        agent_service_pb2.GetRequestResultRequest(user_id="u-1", session_id="", request_id="req-1"),
        ctx,  # type: ignore[arg-type]
    )

    assert ctx.code == grpc.StatusCode.INVALID_ARGUMENT
    assert resp.status == agent_service_pb2.RequestResultStatus.REQUEST_RESULT_UNKNOWN


@pytest.mark.unit
async def test_handler_maps_completed_state() -> None:
    sm = _FakeStateManager()
    sm.cached[("sess-1", "req-1")] = dict(_COMPLETED_BODY)
    service = _make_service(state_manager=sm)
    ctx = _FakeContext(metadata=[("user-id", "u-1")])

    resp = await service.GetRequestResult(
        agent_service_pb2.GetRequestResultRequest(user_id="u-1", session_id="sess-1", request_id="req-1"),
        ctx,  # type: ignore[arg-type]
    )

    assert ctx.code is None
    assert resp.status == agent_service_pb2.RequestResultStatus.REQUEST_RESULT_COMPLETED
    assert resp.message == "已完成的回答全文"
    assert resp.payload.fields["message"].string_value == "已完成的回答全文"


@pytest.mark.unit
async def test_handler_maps_running_state_with_trace_id() -> None:
    redis_client = _FakeRedis()
    _seed_ledger(redis_client, session_id="sess-1", trace_id="t-9", request_id="req-1", status="running")
    service = _make_service(redis_client=redis_client)
    ctx = _FakeContext(metadata=[("user-id", "u-1")])

    resp = await service.GetRequestResult(
        agent_service_pb2.GetRequestResultRequest(user_id="u-1", session_id="sess-1", request_id="req-1"),
        ctx,  # type: ignore[arg-type]
    )

    assert ctx.code is None
    assert resp.status == agent_service_pb2.RequestResultStatus.REQUEST_RESULT_RUNNING
    assert resp.trace_id == "t-9"
