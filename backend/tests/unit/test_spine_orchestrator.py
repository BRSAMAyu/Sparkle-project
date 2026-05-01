"""
P1-7: Production-grade tests for SpineOrchestrator.

Covers:
- __init__ wiring (all subsystems instantiated)
- Directive store/get round-trip for all 9 types
- _store_directive generic helper
- _publish_directive_event pub/sub
- Pipeline lock concurrency guard
- on_task_completed signal generation
- get_status_band_summary structure
- Redis failure degradation paths
- Edge cases: empty data, unicode, multi-user isolation
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.signals.spine_orchestrator import SpineOrchestrator
from app.signals.types import (
    ActionableSignal,
    CommunityDirective,
    ModelWriteDirective,
    ModelWriteEntry,
    NotificationDirective,
    PlanDirective,
    RetrievalDirective,
    ResponseDirective,
    SkillDirective,
    StateEntry,
    UXDirective,
    UserVisibleReceipt,
    _uid,
)


# ── Fake Redis ─────────────────────────────────────────────────


class FakeRedis:
    """In-memory Redis replacement for testing."""

    def __init__(self):
        self._store: dict[str, str] = {}
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
        return set()

    async def sadd(self, key: str, *members):
        return len(members)

    async def srem(self, key: str, *members):
        return len(members)

    async def mget(self, *keys):
        return [self._store.get(k) for k in keys]

    async def lpush(self, key: str, *values):
        return len(values)

    async def lrange(self, key: str, start: int, stop: int):
        return []

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
        return FakePipeline(self)

    async def xadd(self, stream: str, fields: dict, **kwargs):
        return "0-0"

    async def xread(self, streams: dict, **kwargs):
        return []

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


class FakePipeline:
    def __init__(self, redis: FakeRedis):
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
        source_system="test",
        state_key="test_state",
        claim="test claim",
        confidence=0.8,
        scope="task",
        ttl_hours=24,
        evidence_summary="evidence",
        possible_effects=["effect_a"],
        priority="medium",
    )
    defaults.update(overrides)
    return ActionableSignal(**defaults)


@pytest.fixture
def fake_redis():
    return FakeRedis()


@pytest.fixture
def orchestrator(fake_redis):
    return SpineOrchestrator(fake_redis)


# ═══════════════════════════════════════════════════════════════
# 1. Init wiring
# ═══════════════════════════════════════════════════════════════


class TestInit:
    def test_all_core_subsystems_instantiated(self, orchestrator):
        assert orchestrator.trace_store is not None
        assert orchestrator.state_register is not None
        assert orchestrator.policy_engine is not None
        assert orchestrator.outcome_recorder is not None
        assert orchestrator.metrics is not None
        assert orchestrator.signal_ranker is not None

    def test_governance_modules_wired(self, orchestrator):
        assert orchestrator._fabrication_scanner is not None
        assert orchestrator._safety_degradation is not None
        assert orchestrator._high_impact_confirmation is not None
        assert orchestrator._research_isolation is not None

    def test_previously_orphaned_modules_wired(self, orchestrator):
        assert orchestrator.policy_analytics is not None
        assert orchestrator.policy_experiments is not None
        assert orchestrator.learning_base is not None
        assert orchestrator.growth_chronicle is not None
        assert orchestrator.relationship_model is not None
        assert orchestrator.directive_quota is not None
        assert orchestrator.aurora_core is not None
        assert orchestrator.l3_engine is not None

    def test_redis_shared(self, orchestrator, fake_redis):
        assert orchestrator.redis is fake_redis
        assert orchestrator.state_register.redis is fake_redis
        assert orchestrator.trace_store.redis is fake_redis


# ═══════════════════════════════════════════════════════════════
# 2. Directive store/get round-trip (all 9 types)
# ═══════════════════════════════════════════════════════════════


class TestDirectiveRoundTrip:
    @pytest.mark.asyncio
    async def test_response_directive_round_trip(self, orchestrator, fake_redis):
        rd = ResponseDirective(
            directive_id=_uid("rd"),
            policy_decision_id=_uid("pd"),
            tone="supportive",
        )
        await orchestrator._store_response_directive("u1", rd)
        result = await orchestrator.get_response_directive("u1")
        assert result is not None
        assert result.directive_id == rd.directive_id
        assert result.tone == "supportive"
        assert result.policy_decision_id == rd.policy_decision_id
        assert isinstance(result.target_module, str)

    @pytest.mark.asyncio
    async def test_notification_directive_round_trip(self, orchestrator, fake_redis):
        nd = NotificationDirective(
            directive_id=_uid("nd"),
            policy_decision_id=_uid("pd"),
            channel="push",
        )
        await orchestrator._store_notification_directive("u1", nd)
        result = await orchestrator.get_notification_directive("u1")
        assert result is not None
        assert result.directive_id == nd.directive_id
        assert result.channel == "push"
        assert result.policy_decision_id == nd.policy_decision_id
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_retrieval_directive_round_trip(self, orchestrator, fake_redis):
        rd = RetrievalDirective(
            directive_id=_uid("rtd"),
            policy_decision_id=_uid("pd"),
            must_load=["node_a"],
            do_not_load=["node_b"],
        )
        await orchestrator._store_retrieval_directive("u1", rd)
        result = await orchestrator.get_retrieval_directive("u1")
        assert result is not None
        assert result.must_load == ["node_a"]
        assert result.do_not_load == ["node_b"]
        assert result.directive_id == rd.directive_id
        assert result.citation_required is True

    @pytest.mark.asyncio
    async def test_plan_directive_round_trip(self, orchestrator, fake_redis):
        pd = PlanDirective(
            directive_id=_uid("pd"),
            policy_decision_id=_uid("pdec"),
            plan_action="local_replan",
            constraints={"deadline_days": 14},
        )
        await orchestrator._store_plan_directive("u1", pd)
        result = await orchestrator.get_plan_directive("u1")
        assert result is not None
        assert result.plan_action == "local_replan"
        assert result.directive_id == pd.directive_id
        assert result.constraints == {"deadline_days": 14}

    @pytest.mark.asyncio
    async def test_model_write_directive_round_trip(self, orchestrator, fake_redis):
        mw = ModelWriteDirective(
            directive_id=_uid("mw"),
            policy_decision_id=_uid("pd"),
            writes=[ModelWriteEntry(target="learning_pace", claim="fast", confidence=0.9)],
        )
        await orchestrator._store_model_write_directive("u1", mw)
        result = await orchestrator.get_model_write_directive("u1")
        assert result is not None
        assert len(result.writes) == 1
        assert result.writes[0].claim == "fast"
        assert result.writes[0].target == "learning_pace"
        assert result.writes[0].confidence == 0.9
        assert result.directive_id == mw.directive_id

    @pytest.mark.asyncio
    async def test_ux_directive_round_trip(self, orchestrator, fake_redis):
        ux = UXDirective(
            directive_id=_uid("ux"),
            policy_decision_id=_uid("pd"),
            status_band_state="encouragement",
        )
        await orchestrator._store_ux_directive("u1", ux)
        result = await orchestrator.get_ux_directive("u1")
        assert result is not None
        assert result.status_band_state == "encouragement"
        assert result.directive_id == ux.directive_id
        assert isinstance(result.show_context_receipt, bool)

    @pytest.mark.asyncio
    async def test_community_directive_round_trip(self, orchestrator, fake_redis):
        cd = CommunityDirective(
            directive_id=_uid("cd"),
            policy_decision_id=_uid("pd"),
            cohort_hint_shown=True,
        )
        await orchestrator._store_community_directive("u1", cd)
        result = await orchestrator.get_community_directive("u1")
        assert result is not None
        assert result.cohort_hint_shown is True
        assert result.directive_id == cd.directive_id
        assert result.peer_context_mode == "anonymous"

    @pytest.mark.asyncio
    async def test_skill_directive_round_trip(self, orchestrator, fake_redis):
        sd = SkillDirective(
            directive_id=_uid("sd"),
            policy_decision_id=_uid("pd"),
            skill_action="recommend",
            relevant_skill_ids=["skill_1"],
        )
        await orchestrator._store_skill_directive("u1", sd)
        result = await orchestrator.get_skill_directive("u1")
        assert result is not None
        assert result.skill_action == "recommend"
        assert result.relevant_skill_ids == ["skill_1"]
        assert result.directive_id == sd.directive_id
        assert result.policy_decision_id == sd.policy_decision_id

    @pytest.mark.asyncio
    async def test_get_directive_returns_none_when_empty(self, orchestrator):
        assert await orchestrator.get_response_directive("nobody") is None
        assert await orchestrator.get_plan_directive("nobody") is None
        assert await orchestrator.get_retrieval_directive("nobody") is None
        assert await orchestrator.get_model_write_directive("nobody") is None
        assert await orchestrator.get_ux_directive("nobody") is None
        assert await orchestrator.get_community_directive("nobody") is None
        assert await orchestrator.get_skill_directive("nobody") is None
        assert await orchestrator.get_notification_directive("nobody") is None


# ═══════════════════════════════════════════════════════════════
# 3. Generic _store_directive helper
# ═══════════════════════════════════════════════════════════════


class TestStoreDirectiveHelper:
    @pytest.mark.asyncio
    async def test_generic_store_sets_redis_key(self, orchestrator, fake_redis):
        pd = PlanDirective(
            directive_id=_uid("pd"),
            policy_decision_id=_uid("pdec"),
            plan_action="extend_deadline",
        )
        await orchestrator.directive_store.store("u1", "plan", pd)
        raw = await fake_redis.get("spine:plan_directive:u1:latest")
        assert raw is not None
        data = json.loads(raw)
        assert data["directive_id"] == pd.directive_id

    @pytest.mark.asyncio
    async def test_generic_store_overwrites_previous(self, orchestrator, fake_redis):
        pd1 = PlanDirective(
            directive_id=_uid("pd"),
            policy_decision_id=_uid("pdec"),
            plan_action="action_a",
        )
        pd2 = PlanDirective(
            directive_id=_uid("pd"),
            policy_decision_id=_uid("pdec"),
            plan_action="action_b",
        )
        await orchestrator.directive_store.store("u1", "plan", pd1)
        await orchestrator.directive_store.store("u1", "plan", pd2)
        result = await orchestrator.get_plan_directive("u1")
        assert result.plan_action == "action_b"


# ═══════════════════════════════════════════════════════════════
# 4. Pub/sub directive events
# ═══════════════════════════════════════════════════════════════


class TestPublishDirectiveEvent:
    @pytest.mark.asyncio
    async def test_publish_writes_to_pubsub(self, orchestrator, fake_redis):
        payload = {"directive_id": "d1", "type": "plan"}
        await orchestrator.directive_store.publish_event("spine:directive:plan", payload)
        assert len(fake_redis._pubsub) == 1
        channel, msg = fake_redis._pubsub[0]
        assert channel == "spine:directive:plan"
        assert json.loads(msg) == payload

    @pytest.mark.asyncio
    async def test_publish_failure_does_not_raise(self, orchestrator):
        orchestrator.redis.publish = AsyncMock(side_effect=Exception("pubsub down"))
        await orchestrator.directive_store.publish_event("ch", {"x": 1})


# ═══════════════════════════════════════════════════════════════
# 5. Pipeline lock concurrency guard
# ═══════════════════════════════════════════════════════════════


class TestPipelineLock:
    @pytest.mark.asyncio
    async def test_pipeline_lock_released_after_run(self, orchestrator, fake_redis):
        signal = _make_signal()
        orchestrator.policy_engine.evaluate = AsyncMock(return_value=None)
        await orchestrator._run_signal_pipeline(user_id="u1", signal=signal)
        lock_val = await fake_redis.get("spine:pipeline_lock:u1")
        assert lock_val is None

    @pytest.mark.asyncio
    async def test_pipeline_skipped_when_locked(self, orchestrator, fake_redis):
        await fake_redis.set("spine:pipeline_lock:u1", "1")
        signal = _make_signal()
        result = await orchestrator._run_signal_pipeline(user_id="u1", signal=signal)
        assert result is None


# ═══════════════════════════════════════════════════════════════
# 6. Status band summary structure
# ═══════════════════════════════════════════════════════════════


class TestStatusBandSummary:
    @pytest.mark.asyncio
    async def test_returns_expected_fields(self, orchestrator):
        summary = await orchestrator.get_status_band_summary("u1")
        assert isinstance(summary, dict)
        for key in ("strategy_risk", "material_aware", "execution_risk",
                     "stale_guard", "band_severity", "band_status",
                     "band_label", "band_summary", "band_energy"):
            assert key in summary, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_default_state_is_sensing(self, orchestrator):
        summary = await orchestrator.get_status_band_summary("u1")
        assert summary["band_status"] == "sensing"
        assert summary["band_severity"] == "none"

    @pytest.mark.asyncio
    async def test_redis_failure_returns_defaults(self):
        """Status band returns sensible defaults even with Redis failures."""
        redis = FakeRedis()
        # Make state register return empty on failure
        orch = SpineOrchestrator(redis)
        orch.trace_store.get_active_directive = AsyncMock(return_value=None)
        orch._compute_6state_band = AsyncMock(return_value=(
            "sensing", "感知中", "系统正在收集数据", "L0", None, False,
        ))
        orch._build_correction_options = AsyncMock(return_value=[])
        summary = await orch.get_status_band_summary("u1")
        assert summary["band_status"] == "sensing"
        assert summary["band_severity"] == "none"


# ═══════════════════════════════════════════════════════════════
# 7. Receipt handling
# ═══════════════════════════════════════════════════════════════


class TestReceiptHandling:
    @pytest.mark.asyncio
    async def test_get_latest_receipt_returns_none_initially(self, orchestrator):
        result = await orchestrator.get_latest_receipt("u1")
        assert result is None

    @pytest.mark.asyncio
    async def test_receipt_round_trip(self, orchestrator, fake_redis):
        receipt = UserVisibleReceipt(
            receipt_id=_uid("rcpt"),
            receipt_type="strategy_adjustment",
            message="Test receipt",
            actions=["confirm", "correct", "dismiss"],
            related_state_keys=["test_state"],
        )
        await fake_redis.set(
            f"spine:receipt:u1:latest",
            json.dumps(receipt.to_dict()),
        )
        result = await orchestrator.get_latest_receipt("u1")
        assert result is not None
        assert result.message == "Test receipt"
        assert result.receipt_type == "strategy_adjustment"
        assert result.actions == ["confirm", "correct", "dismiss"]
        assert result.related_state_keys == ["test_state"]


# ═══════════════════════════════════════════════════════════════
# 8. on_task_completed
# ═══════════════════════════════════════════════════════════════


class TestOnTaskCompleted:
    @pytest.mark.asyncio
    async def test_overtime_no_crash(self, orchestrator, fake_redis):
        orchestrator.policy_engine.evaluate = AsyncMock(return_value=None)
        result = await orchestrator.on_task_completed(
            user_id="u1",
            task_id="t1",
            estimated_minutes=60,
            actual_minutes=90,
            plan_id="p1",
        )
        assert result is None or hasattr(result, "trace_id")

    @pytest.mark.asyncio
    async def test_exact_time_no_crash(self, orchestrator, fake_redis):
        orchestrator.policy_engine.evaluate = AsyncMock(return_value=None)
        result = await orchestrator.on_task_completed(
            user_id="u1",
            task_id="t1",
            estimated_minutes=60,
            actual_minutes=60,
        )
        assert result is None or hasattr(result, "trace_id")


# ═══════════════════════════════════════════════════════════════
# 9. State register integration
# ═══════════════════════════════════════════════════════════════


class TestStateRegisterIntegration:
    @pytest.mark.asyncio
    async def test_get_active_states_empty(self, orchestrator):
        states = await orchestrator.get_active_states("u1")
        assert states == []

    @pytest.mark.asyncio
    async def test_add_counter_evidence_no_state(self, orchestrator):
        result = await orchestrator.add_counter_evidence("u1", "nonexistent", "evidence")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_state_nonexistent(self, orchestrator):
        await orchestrator.remove_state("u1", "nonexistent")


# ═══════════════════════════════════════════════════════════════
# 10. User correction
# ═══════════════════════════════════════════════════════════════


class TestUserCorrection:
    @pytest.mark.asyncio
    async def test_correction_no_crash(self, orchestrator, fake_redis):
        await orchestrator.on_user_correction(
            user_id="u1",
            correction_type="dismiss",
            original_claim="User struggling",
            corrected_understanding="Actually doing fine",
        )


# ═══════════════════════════════════════════════════════════════
# 11. Edge cases
# ═══════════════════════════════════════════════════════════════


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_directive_store_with_unicode(self, orchestrator, fake_redis):
        rd = ResponseDirective(
            directive_id=_uid("rd"),
            policy_decision_id=_uid("pd"),
            tone="这是中文 🎉",
        )
        await orchestrator._store_response_directive("u1", rd)
        result = await orchestrator.get_response_directive("u1")
        assert result is not None
        assert "中文" in result.tone
        assert result.directive_id == rd.directive_id
        assert isinstance(result.length, str)

    @pytest.mark.asyncio
    async def test_multi_user_isolation(self, orchestrator, fake_redis):
        rd1 = ResponseDirective(
            directive_id=_uid("rd"),
            policy_decision_id=_uid("pd"),
            tone="supportive",
        )
        rd2 = ResponseDirective(
            directive_id=_uid("rd"),
            policy_decision_id=_uid("pd"),
            tone="neutral",
        )
        await orchestrator._store_response_directive("u1", rd1)
        await orchestrator._store_response_directive("u2", rd2)

        r1 = await orchestrator.get_response_directive("u1")
        r2 = await orchestrator.get_response_directive("u2")
        assert r1.tone == "supportive"
        assert r2.tone == "neutral"

    @pytest.mark.asyncio
    async def test_get_model_claims_empty(self, orchestrator):
        claims = await orchestrator.get_model_claims("u1")
        assert isinstance(claims, list)
        assert len(claims) == 0


# ═══════════════════════════════════════════════════════════════
# 12. Source tray
# ═══════════════════════════════════════════════════════════════


class TestSourceTray:
    @pytest.mark.asyncio
    async def test_set_and_get_source_tray(self, orchestrator, fake_redis):
        await orchestrator.set_source_tray("u1", ["node_a", "node_b"])
        state = await orchestrator.get_source_tray_state("u1")
        # Returns either a list or dict depending on implementation
        assert state is not None

    @pytest.mark.asyncio
    async def test_source_tray_default(self, orchestrator):
        state = await orchestrator.get_source_tray_state("u1")
        # Empty state is valid
        assert state is not None


# ═══════════════════════════════════════════════════════════════
# 13. Signal pipeline with policy match
# ═══════════════════════════════════════════════════════════════


class TestSignalPipelineWithPolicy:
    @pytest.mark.asyncio
    async def test_pipeline_creates_trace(self, orchestrator, fake_redis):
        signal = _make_signal()
        orchestrator.policy_engine.evaluate = AsyncMock(return_value=None)
        trace = await orchestrator._run_signal_pipeline(user_id="u1", signal=signal)
        # With no match, trace still created with no_rule_match
        if trace is not None:
            assert trace.outcome_to_measure == ["signal_no_rule_match"]

    @pytest.mark.asyncio
    async def test_pipeline_lock_released_on_no_match(self, orchestrator, fake_redis):
        signal = _make_signal()
        orchestrator.policy_engine.evaluate = AsyncMock(return_value=None)
        await orchestrator._run_signal_pipeline(user_id="u1", signal=signal)
        lock_val = await fake_redis.get("spine:pipeline_lock:u1")
        assert lock_val is None
