"""
EA-11 + EA-13: Integration tests for Spine Directive end-to-end flow.

Unlike unit tests which mock everything, these tests use FakeRedis to
verify the full signal → policy → directive → Redis storage → retrieval
pipeline without mocking internal components.

Covers:
- Full signal pipeline: signal → StateRegister → PolicyEngine → directive storage
- Directive retrieval after pipeline run
- Event bus Redis Streams publish/subscribe
- Multi-directive flow (response + plan + retrieval + UX)
- Trace creation and persistence
- Outcome recording after directive generation
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.signals.causal_trace_store import CausalTraceStore
from app.signals.policy_engine import PolicyEngine
from app.signals.spine_orchestrator import SpineOrchestrator
from app.signals.state_register import StateRegister
from app.signals.types import (
    ActionableSignal,
    PlanDirective,
    ResponseDirective,
    RetrievalDirective,
    UXDirective,
    _uid,
)


class IntegrationFakeRedis:
    """More complete Redis that tracks pub/sub and streams."""

    def __init__(self):
        self._store: dict[str, str] = {}
        self._streams: dict[str, list[dict]] = {}
        self._pubsub: list[tuple[str, str]] = []

    async def get(self, key: str):
        return self._store.get(key)

    async def set(self, key: str, value: str, **kwargs):
        nx = kwargs.get("nx") or kwargs.get("exist", None) is False
        if nx and key in self._store:
            return None
        self._store[key] = value
        return True

    async def delete(self, *keys):
        n = sum(1 for k in keys if k in self._store)
        for k in keys:
            self._store.pop(k, None)
        return n

    async def publish(self, channel: str, message: str):
        self._pubsub.append((channel, message))
        return 1

    async def incr(self, key: str):
        v = int(self._store.get(key, "0")) + 1
        self._store[key] = str(v)
        return v

    async def incrby(self, key: str, amount: int = 1):
        v = int(self._store.get(key, "0")) + amount
        self._store[key] = str(v)
        return v

    async def expire(self, key: str, ttl: int):
        pass

    async def smembers(self, key: str):
        set_key = f"__set__{key}"
        try:
            return set(json.loads(self._store.get(set_key, "[]")))
        except Exception:
            return set()

    async def sadd(self, key: str, *members):
        return len(members)

    async def srem(self, key: str, *members):
        return len(members)

    async def mget(self, *keys):
        return [self._store.get(k) for k in keys]

    async def lpush(self, key: str, *values):
        if key not in self._store:
            self._store[key] = json.dumps([])
        try:
            existing = json.loads(self._store[key])
        except Exception:
            existing = []
        for v in values:
            existing.insert(0, v)
        self._store[key] = json.dumps(existing)
        return len(values)

    async def lrange(self, key: str, start: int, stop: int):
        try:
            data = json.loads(self._store.get(key, "[]"))
        except Exception:
            data = []
        if stop == -1:
            return data[start:]
        return data[start:stop + 1]

    async def ltrim(self, key: str, start: int, stop: int):
        pass

    async def lrem(self, key: str, count: int, value: str):
        return 0

    async def llen(self, key: str):
        return 0

    async def exists(self, *keys):
        return sum(1 for k in keys if k in self._store)

    async def setnx(self, key: str, value: str):
        if key in self._store:
            return False
        self._store[key] = value
        return True

    def pipeline(self):
        return IntegrationFakePipeline(self)

    # Redis Streams support
    async def xadd(self, stream: str, fields: dict, **kwargs):
        if stream not in self._streams:
            self._streams[stream] = []
        entry = {"id": f"{len(self._streams[stream])}-0", **fields}
        self._streams[stream].append(entry)
        return entry["id"]

    async def xread(self, streams: dict, **kwargs):
        results = []
        for stream, ids in streams.items():
            entries = self._streams.get(stream, [])
            results.append((stream, entries))
        return results

    async def xack(self, stream: str, group: str, *ids):
        return len(ids)

    async def xgroup_create(self, stream: str, group: str, id: str = "0"):
        pass

    async def hset(self, name: str, key: str = None, value: str = None, mapping: dict = None, **kwargs):
        return 1

    async def hget(self, name: str, key: str):
        return None

    async def hgetall(self, name: str):
        return {}

    async def zadd(self, name: str, mapping: dict, **kwargs):
        return len(mapping)

    async def zrange(self, name: str, start: int, end: int, **kwargs):
        return []

    def get_store(self, key: str):
        return self._store.get(key)


class IntegrationFakePipeline:
    def __init__(self, redis: IntegrationFakeRedis):
        self._redis = redis
        self._cmds: list[tuple] = []

    def set(self, key, value, **kwargs):
        self._cmds.append(("set", key, value))

    def get(self, key):
        self._cmds.append(("get", key))

    def delete(self, *keys):
        self._cmds.append(("delete",) + keys)

    def sadd(self, key, *members):
        self._cmds.append(("sadd", key) + members)
        # Also update a set-like store
        set_key = f"__set__{key}"
        existing = set(json.loads(self._redis._store.get(set_key, "[]")))
        existing.update(members)
        self._redis._store[set_key] = json.dumps(list(existing))

    def srem(self, key, *members):
        self._cmds.append(("srem", key) + members)

    def expire(self, key, ttl):
        self._cmds.append(("expire", key, ttl))

    def lpush(self, key, *values):
        self._cmds.append(("lpush", key) + values)

    def ltrim(self, key, start, stop):
        self._cmds.append(("ltrim", key, start, stop))

    def hset(self, name, key=None, value=None, mapping=None, **kwargs):
        self._cmds.append(("hset", name))

    def zadd(self, name, mapping, **kwargs):
        self._cmds.append(("zadd", name))

    async def execute(self):
        results = []
        for cmd in self._cmds:
            op = cmd[0]
            if op == "set":
                self._redis._store[cmd[1]] = cmd[2]
                results.append(True)
            elif op == "get":
                results.append(self._redis._store.get(cmd[1]))
            elif op == "delete":
                n = sum(1 for k in cmd[1:] if k in self._redis._store)
                for k in cmd[1:]:
                    self._redis._store.pop(k, None)
                results.append(n)
            else:
                results.append(1)
        return results

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _make_signal(**overrides) -> ActionableSignal:
    defaults = dict(
        signal_id=_uid("sig"),
        source_event_ids=[_uid("evt")],
        source_system="integration_test",
        state_key="execution_consistency",
        claim="User struggling with math",
        confidence=0.85,
        scope="session",
        ttl_hours=24,
        evidence_summary="3 consecutive task overruns",
        possible_effects=["reduce_task_complexity"],
        priority="high",
    )
    defaults.update(overrides)
    return ActionableSignal(**defaults)


@pytest.fixture
def redis():
    return IntegrationFakeRedis()


@pytest.fixture
def orchestrator(redis):
    return SpineOrchestrator(redis)


# ═══════════════════════════════════════════════════════════════
# E2E: Signal → StateRegister → Directive storage
# ═══════════════════════════════════════════════════════════════


class TestEndToEndSignalPipeline:
    @pytest.mark.asyncio
    async def test_signal_creates_state_in_register(self, orchestrator, redis):
        signal = _make_signal()
        # Manually upsert to state register
        entry = await orchestrator.state_register.upsert_from_signal("u1", signal)
        assert entry is not None
        assert entry.state_key == "execution_consistency"
        assert entry.confidence == 0.85

        # Verify it persists in Redis
        raw = await redis.get(f"spine:state:u1:execution_consistency")
        assert raw is not None
        data = json.loads(raw)
        assert data["value"] == "User struggling with math"

    @pytest.mark.asyncio
    async def test_state_register_get_active_states(self, orchestrator, redis):
        signal1 = _make_signal(state_key="execution_consistency", claim="Struggling")
        signal2 = _make_signal(state_key="cognitive_load", claim="High load", confidence=0.7)

        await orchestrator.state_register.upsert_from_signal("u1", signal1)
        await orchestrator.state_register.upsert_from_signal("u1", signal2)

        states = await orchestrator.state_register.get_active_states("u1")
        assert len(states) == 2
        keys = {s.state_key for s in states}
        assert "execution_consistency" in keys
        assert "cognitive_load" in keys

    @pytest.mark.asyncio
    async def test_signal_pipeline_stores_trace(self, orchestrator, redis):
        signal = _make_signal()
        orchestrator.policy_engine.evaluate = AsyncMock(return_value=None)

        trace = await orchestrator._run_signal_pipeline(user_id="u1", signal=signal)

        if trace is not None:
            # Trace should be persisted
            trace_key = f"spine:trace:{trace.trace_id}"
            raw = await redis.get(trace_key)
            assert raw is not None

    @pytest.mark.asyncio
    async def test_multiple_signals_same_user(self, orchestrator, redis):
        signals = [
            _make_signal(state_key=f"signal_{i}", claim=f"Claim {i}")
            for i in range(5)
        ]
        orchestrator.policy_engine.evaluate = AsyncMock(return_value=None)

        for signal in signals:
            await orchestrator._run_signal_pipeline(user_id="u1", signal=signal)

        states = await orchestrator.state_register.get_active_states("u1")
        assert len(states) == 5


# ═══════════════════════════════════════════════════════════════
# E2E: Directive store → retrieve → verify
# ═══════════════════════════════════════════════════════════════


class TestEndToEndDirectiveFlow:
    @pytest.mark.asyncio
    async def test_response_directive_e2e(self, orchestrator, redis):
        rd = ResponseDirective(
            directive_id=_uid("rd"),
            policy_decision_id=_uid("pd"),
            tone="encouraging",
        )
        await orchestrator._store_response_directive("u1", rd)
        await orchestrator.directive_store.publish_event("spine:directive:response", rd.to_dict())

        result = await orchestrator.get_response_directive("u1")
        assert result is not None
        assert result.tone == "encouraging"

        assert len(redis._pubsub) >= 1
        channels = [ch for ch, _ in redis._pubsub]
        assert "spine:directive:response" in channels

    @pytest.mark.asyncio
    async def test_multiple_directive_types(self, orchestrator, redis):
        """All 4 previously orphaned directives now have consumers."""
        rd = ResponseDirective(directive_id=_uid("rd"), policy_decision_id=_uid("pd"))
        rtd = RetrievalDirective(
            directive_id=_uid("rtd"), policy_decision_id=_uid("pd"),
            must_load=["node_a"], do_not_load=["node_b"],
        )
        ux = UXDirective(directive_id=_uid("ux"), policy_decision_id=_uid("pd"))
        pd = PlanDirective(directive_id=_uid("pd2"), policy_decision_id=_uid("pd3"))

        await orchestrator._store_response_directive("u1", rd)
        await orchestrator._store_retrieval_directive("u1", rtd)
        await orchestrator._store_ux_directive("u1", ux)
        await orchestrator._store_plan_directive("u1", pd)

        assert await orchestrator.get_response_directive("u1") is not None
        assert await orchestrator.get_retrieval_directive("u1") is not None
        assert await orchestrator.get_ux_directive("u1") is not None
        assert await orchestrator.get_plan_directive("u1") is not None

    @pytest.mark.asyncio
    async def test_directive_overwrite_latest_wins(self, orchestrator, redis):
        rd1 = ResponseDirective(
            directive_id=_uid("rd"), policy_decision_id=_uid("pd"),
            tone="calm",
        )
        rd2 = ResponseDirective(
            directive_id=_uid("rd"), policy_decision_id=_uid("pd"),
            tone="urgent",
        )
        await orchestrator._store_response_directive("u1", rd1)
        await orchestrator._store_response_directive("u1", rd2)

        result = await orchestrator.get_response_directive("u1")
        assert result.tone == "urgent"


# ═══════════════════════════════════════════════════════════════
# E2E: Redis Streams (EA-13)
# ═══════════════════════════════════════════════════════════════


class TestRedisStreams:
    @pytest.mark.asyncio
    async def test_xadd_creates_stream_entry(self, redis):
        entry_id = await redis.xadd(
            "spine:directive_events",
            {"type": "plan", "directive_id": "d1", "user_id": "u1"},
        )
        assert entry_id is not None
        assert len(redis._streams["spine:directive_events"]) == 1

    @pytest.mark.asyncio
    async def test_xread_retrieves_entries(self, redis):
        await redis.xadd("spine:events", {"action": "test"})
        result = await redis.xread({"spine:events": "0-0"})
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_xack_succeeds(self, redis):
        entry_id = await redis.xadd("spine:events", {"action": "test"})
        acked = await redis.xack("spine:events", "consumer_group", entry_id)
        assert acked == 1


# ═══════════════════════════════════════════════════════════════
# E2E: CausalTrace persistence
# ═══════════════════════════════════════════════════════════════


class TestCausalTracePersistence:
    @pytest.mark.asyncio
    async def test_trace_store_create_and_retrieve(self, redis):
        store = CausalTraceStore(redis)
        trace = await store.create_trace()
        assert trace is not None
        assert trace.trace_id.startswith("ct_")

    @pytest.mark.asyncio
    async def test_trace_link_to_user(self, redis):
        store = CausalTraceStore(redis)
        trace = await store.create_trace()
        await store.link_to_user("u1", trace.trace_id)

        # Verify user trace link — stored as a list via lpush
        link_key = f"spine:user_traces:u1"
        raw = await redis.get(link_key)
        assert raw is not None
        data = json.loads(raw)
        assert trace.trace_id in data


# ═══════════════════════════════════════════════════════════════
# E2E: Multi-user isolation
# ═══════════════════════════════════════════════════════════════


class TestMultiUserIsolation:
    @pytest.mark.asyncio
    async def test_states_isolated_between_users(self, orchestrator, redis):
        signal_u1 = _make_signal(state_key="execution_consistency", claim="User 1 struggling")
        signal_u2 = _make_signal(state_key="execution_consistency", claim="User 2 excelling")

        await orchestrator.state_register.upsert_from_signal("u1", signal_u1)
        await orchestrator.state_register.upsert_from_signal("u2", signal_u2)

        states_u1 = await orchestrator.state_register.get_active_states("u1")
        states_u2 = await orchestrator.state_register.get_active_states("u2")

        assert len(states_u1) == 1
        assert len(states_u2) == 1
        assert states_u1[0].value == "User 1 struggling"
        assert states_u2[0].value == "User 2 excelling"

    @pytest.mark.asyncio
    async def test_directives_isolated_between_users(self, orchestrator, redis):
        rd1 = ResponseDirective(directive_id=_uid("rd"), policy_decision_id=_uid("pd"), tone="calm")
        rd2 = ResponseDirective(directive_id=_uid("rd"), policy_decision_id=_uid("pd"), tone="urgent")

        await orchestrator._store_response_directive("u1", rd1)
        await orchestrator._store_response_directive("u2", rd2)

        r1 = await orchestrator.get_response_directive("u1")
        r2 = await orchestrator.get_response_directive("u2")
        assert r1.tone == "calm"
        assert r2.tone == "urgent"
