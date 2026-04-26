"""
Core: execution
Phase: sense→clarify→plan→execute→reflect→adapt
Stage: Signal-to-Action Spine M1 验收测试

验收 E1: 连续 2 张任务卡超时 → 产生 ActionableSignal → PolicyDecision →
        ExecutionDirective → 下一张任务卡 duration <= 25 → Audit applied=true → Receipt。
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.signals.types import (
    ActionableSignal,
    ActionableStatePacket,
    CausalTrace,
    DirectiveApplicationAudit,
    ExecutionDirective,
    PolicyDecision,
    StateEntry,
    UserVisibleReceipt,
    _uid,
)
from app.signals.task_timeout_detector import TaskTimeoutDetector
from app.signals.policy_engine import PolicyEngine
from app.signals.directive_applier import DirectiveApplier, DirectiveAuditor


# ── Fixtures ──────────────────────────────────────────────────────────

class FakeRedis:
    """Minimal Redis fake for unit tests."""

    def __init__(self):
        self._store: dict[str, str] = {}
        self._lists: dict[str, list[str]] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def lpush(self, key: str, value: str) -> None:
        self._lists.setdefault(key, []).insert(0, value)

    async def lrange(self, key: str, start: int, stop: int) -> list[str]:
        data = self._lists.get(key, [])
        if stop == -1:
            return data[start:]
        return data[start:stop + 1]

    async def ltrim(self, key: str, start: int, stop: int) -> None:
        data = self._lists.get(key, [])
        self._lists[key] = data[start:stop + 1]

    async def expire(self, key: str, seconds: int) -> None:
        pass

    async def lrem(self, key: str, count: int, value: str) -> None:
        data = self._lists.get(key, [])
        try:
            data.remove(value)
        except ValueError:
            pass


@pytest.fixture
def fake_redis():
    return FakeRedis()


# ── Test 1: Types serialization round-trip ─────────────────────────────

def test_actionable_signal_roundtrip():
    signal = ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=["evt_001"],
        source_system="task_service",
        state_key="task_granularity_fit",
        claim="recent_task_too_large",
        confidence=0.72,
        scope="current_sprint",
        ttl_hours=72,
        evidence_summary="连续 2 次任务超时",
        possible_effects=["cap_task_duration"],
        priority="high",
    )
    d = signal.to_dict()
    restored = ActionableSignal.from_dict(d)
    assert restored.signal_id == signal.signal_id
    assert restored.state_key == "task_granularity_fit"
    assert restored.confidence == 0.72


def test_causal_trace_roundtrip():
    trace = CausalTrace(trace_id=_uid("ct"), raw_event_ids=["evt_001"])
    d = trace.to_dict()
    restored = CausalTrace.from_dict(d)
    assert restored.trace_id == trace.trace_id
    assert restored.raw_event_ids == ["evt_001"]


# ── Test 2: TaskTimeoutDetector — no timeout ───────────────────────────

@pytest.mark.asyncio
async def test_no_timeout_no_signal(fake_redis):
    detector = TaskTimeoutDetector(fake_redis)
    signal = await detector.on_task_completed(
        user_id="u1",
        task_id="t1",
        estimated_minutes=30,
        actual_minutes=25,  # within threshold
    )
    assert signal is None


# ── Test 3: TaskTimeoutDetector — single timeout, no trigger ───────────

@pytest.mark.asyncio
async def test_single_timeout_no_trigger(fake_redis):
    detector = TaskTimeoutDetector(fake_redis)
    signal = await detector.on_task_completed(
        user_id="u1",
        task_id="t1",
        estimated_minutes=30,
        actual_minutes=50,  # > 140% = 42min
    )
    assert signal is None  # Need 2 consecutive


# ── Test 4: TaskTimeoutDetector — two consecutive timeouts → signal ────

@pytest.mark.asyncio
async def test_two_consecutive_timeouts_triggers_signal(fake_redis):
    detector = TaskTimeoutDetector(fake_redis)

    # First timeout
    s1 = await detector.on_task_completed(
        user_id="u1", task_id="t1",
        estimated_minutes=30, actual_minutes=50,
    )
    assert s1 is None  # Not yet

    # Second timeout
    s2 = await detector.on_task_completed(
        user_id="u1", task_id="t2",
        estimated_minutes=45, actual_minutes=65,
    )
    assert s2 is not None
    assert s2.state_key == "task_granularity_fit"
    assert s2.claim == "recent_task_too_large"
    assert s2.confidence >= 0.5
    assert s2.priority == "high"


# ── Test 5: PolicyEngine — rule match ──────────────────────────────────

@pytest.mark.asyncio
async def test_policy_engine_matches_timeout_signal():
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=["t1"],
        source_system="task_service",
        state_key="task_granularity_fit",
        claim="recent_task_too_large",
        confidence=0.72,
        scope="current_sprint",
        ttl_hours=72,
        evidence_summary="连续 2 次超时",
        possible_effects=["cap_task_duration"],
        priority="high",
    )
    result = await engine.evaluate(signal, context={"consecutive": 2})
    assert result is not None
    decision, directive = result
    assert decision.primary_strategy == "recover_execution_rhythm"
    assert directive.hard_constraints["max_task_duration_min"] == 25
    assert directive.hard_constraints["avoid_new_chapter"] is True
    assert directive.target_module == "task_generator"


# ── Test 6: DirectiveApplier — duration cap ────────────────────────────

def test_directive_caps_duration():
    directive = ExecutionDirective(
        directive_id="ed_001",
        policy_decision_id="pd_001",
        target_module="task_generator",
        scope="today",
        hard_constraints={"max_task_duration_min": 25},
        user_visible_reason="test",
    )
    capped, applied = DirectiveApplier.apply_duration_cap(
        directive=directive,
        estimated_minutes=60,
    )
    assert capped == 25
    assert applied is True


def test_directive_no_cap_when_below():
    directive = ExecutionDirective(
        directive_id="ed_001",
        policy_decision_id="pd_001",
        target_module="task_generator",
        scope="today",
        hard_constraints={"max_task_duration_min": 25},
        user_visible_reason="test",
    )
    capped, applied = DirectiveApplier.apply_duration_cap(
        directive=directive,
        estimated_minutes=20,
    )
    assert capped == 20
    assert applied is True


def test_directive_no_cap_when_no_directive():
    capped, applied = DirectiveApplier.apply_duration_cap(
        directive=None,
        estimated_minutes=60,
    )
    assert capped == 60
    assert applied is False


# ── Test 7: DirectiveAuditor — pass ────────────────────────────────────

def test_audit_passes_when_constraints_met():
    directive = ExecutionDirective(
        directive_id="ed_001",
        policy_decision_id="pd_001",
        target_module="task_generator",
        scope="today",
        hard_constraints={"max_task_duration_min": 25, "required_task_type": "worked_example_then_drill"},
        user_visible_reason="test",
    )
    audit = DirectiveAuditor.audit(
        directive=directive,
        generated_task={
            "task_id": "task_001",
            "estimated_minutes": 23,
            "task_kind": "worked_example_then_drill",
            "is_new_chapter": False,
        },
    )
    assert audit.applied is True
    assert len(audit.violations) == 0


# ── Test 8: DirectiveAuditor — fail (duration violation) ──────────────

def test_audit_fails_on_duration_violation():
    directive = ExecutionDirective(
        directive_id="ed_001",
        policy_decision_id="pd_001",
        target_module="task_generator",
        scope="today",
        hard_constraints={"max_task_duration_min": 25},
        user_visible_reason="test",
    )
    audit = DirectiveAuditor.audit(
        directive=directive,
        generated_task={
            "task_id": "task_002",
            "estimated_minutes": 40,
            "task_kind": "retrieval_drill",
        },
    )
    assert audit.applied is False
    assert len(audit.violations) == 1
    assert audit.violations[0]["constraint"] == "max_task_duration_min"


# ── Test 9: Full pipeline (E1 acceptance) ──────────────────────────────

@pytest.mark.asyncio
async def test_full_pipeline_e1_acceptance(fake_redis):
    """E1: 连续2次超时 → signal → policy → directive ≤ 25min → audit pass → receipt"""
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.causal_trace_store import CausalTraceStore

    spine = SpineOrchestrator(fake_redis)

    # Task 1: timeout (30 est → 50 actual)
    trace1 = await spine.on_task_completed(
        user_id="u1", task_id="t1",
        estimated_minutes=30, actual_minutes=50,
    )
    assert trace1 is not None
    # Only 1 timeout → no signal generated
    assert len(trace1.signal_ids) == 0

    # Task 2: timeout (45 est → 65 actual)
    trace2 = await spine.on_task_completed(
        user_id="u1", task_id="t2",
        estimated_minutes=45, actual_minutes=65,
    )
    assert trace2 is not None
    # 2 consecutive → signal + policy + directive
    assert len(trace2.signal_ids) >= 1
    assert trace2.policy_decision_id is not None
    assert len(trace2.directive_ids) >= 1
    assert len(trace2.receipt_ids) >= 1

    # Verify active directive exists
    directive = await spine.get_active_directive("u1")
    assert directive is not None
    assert directive.hard_constraints["max_task_duration_min"] == 25

    # Apply directive to a task spec
    task_spec = {"estimated_minutes": 60, "task_kind": "retrieval_drill"}
    modified_spec, audit = await spine.apply_directive_to_task_spec("u1", task_spec)

    assert modified_spec["estimated_minutes"] <= 25
    assert audit is not None
    assert audit.applied is True
    assert len(audit.violations) == 0

    # Verify receipt exists
    receipt = await spine.get_latest_receipt("u1")
    assert receipt is not None
    assert "25" in receipt.message or "超时" in receipt.message

    # After consumption, directive should be cleared
    directive2 = await spine.get_active_directive("u1")
    assert directive2 is None
