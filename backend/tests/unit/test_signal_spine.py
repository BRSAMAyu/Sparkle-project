"""
Core: execution
Phase: sense→clarify→plan→execute→reflect→adapt
Stage: Signal-to-Action Spine M1 验收测试

验收 E1: 连续 2 张任务卡超时 → 产生 ActionableSignal → PolicyDecision →
        ExecutionDirective → 下一张任务卡 duration <= 25 → Audit applied=true → Receipt。
"""

from __future__ import annotations

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
        self._sets: dict[str, set[str]] = {}

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

    async def smembers(self, key: str) -> set[str]:
        return self._sets.get(key, set())

    async def sadd(self, key: str, *members: str) -> int:
        s = self._sets.setdefault(key, set())
        before = len(s)
        for m in members:
            s.add(m)
        return len(s) - before

    async def srem(self, key: str, *members: str) -> int:
        s = self._sets.get(key, set())
        before = len(s)
        for m in members:
            s.discard(m)
        return before - len(s)


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


# ── M2: Material Signal Tests ────────────────────────────────────────

from app.signals.material_signal import MaterialSignalDetector


class FakeRedisWithHset(FakeRedis):
    """Extended fake Redis with hash operations for M2 tests."""

    def __init__(self):
        super().__init__()
        self._hashes: dict[str, dict[str, str]] = {}

    async def hset(self, key: str, field: str, value: str) -> None:
        self._hashes.setdefault(key, {})[field] = value

    async def hgetall(self, key: str) -> dict[str, str]:
        return self._hashes.get(key, {})


@pytest.mark.asyncio
async def test_material_signal_no_files():
    redis = FakeRedisWithHset()
    detector = MaterialSignalDetector(redis)
    signal = await detector.on_turn_completed(user_id="u1", context_receipt=None)
    assert signal is None


@pytest.mark.asyncio
async def test_material_signal_underutilized_after_threshold():
    redis = FakeRedisWithHset()
    detector = MaterialSignalDetector(redis)

    # Register uploaded file
    await detector.register_uploaded_file(
        user_id="u1", file_id="f1", filename="计网传输层.pdf", node_ids=["cn.tcp"]
    )

    # 3 turns with no usage
    for _ in range(3):
        signal = await detector.on_turn_completed(
            user_id="u1", context_receipt={"used_count": 0, "decision_reason": "graph_only"}
        )

    # After 3 turns: signal should be generated
    assert signal is not None
    assert signal.state_key == "material_utilization"
    assert signal.claim == "material_underutilized"
    assert "计网传输层" in signal.evidence_summary


@pytest.mark.asyncio
async def test_material_signal_resets_when_used():
    redis = FakeRedisWithHset()
    detector = MaterialSignalDetector(redis)

    await detector.register_uploaded_file(user_id="u1", file_id="f1", filename="test.pdf")

    # 2 turns unused
    for _ in range(2):
        await detector.on_turn_completed(user_id="u1", context_receipt={"used_count": 0})

    # 1 turn with usage → should NOT trigger
    signal = await detector.on_turn_completed(
        user_id="u1", context_receipt={"used_count": 3}
    )
    assert signal is None


# ── M2: Retrieval Override Test ──────────────────────────────────────

def test_retrieval_intent_respects_spine_override_when_upgrading():
    from app.orchestration.retrieval_intent import build_retrieval_decision

    # Test with a simple greeting where normal classifier returns graph_only or no_retrieval
    # Spine override should upgrade to targeted_source_rag
    decision = build_retrieval_decision(
        message="你好",
        context={
            "spine_retrieval_override": {
                "retrieval_mode": "targeted_source_rag",
                "source_scope": "user_selected",
            }
        },
    )
    assert decision.retrieval_mode == "targeted_source_rag"
    assert decision.source_scope == "user_selected"
    assert decision.should_retrieve is True
    assert "课件" in decision.reason_for_user


def test_retrieval_intent_normal_without_override():
    from app.orchestration.retrieval_intent import build_retrieval_decision

    decision = build_retrieval_decision(
        message="TCP 拥塞控制是什么？",
        context={},
    )
    # Should follow normal classification (not spine override)
    assert decision.retrieval_mode != "no_retrieval" or decision.reason != "spine_material_directive"


# ── M3: Mistake Signal Tests ─────────────────────────────────────────

from app.signals.mistake_signal import MistakeSignalDetector


@pytest.mark.asyncio
async def test_mistake_no_signal_below_threshold():
    redis = FakeRedis()
    detector = MistakeSignalDetector(redis)
    signals = await detector.on_error_created(
        user_id="u1", error_id="e1",
        linked_node_ids=["cn.tcp.congestion_control"],
    )
    assert len(signals) == 0  # Need 3 consecutive


@pytest.mark.asyncio
async def test_mistake_signal_after_three_errors():
    redis = FakeRedis()
    detector = MistakeSignalDetector(redis)

    all_signals = []
    for i in range(3):
        signals = await detector.on_error_created(
            user_id="u1", error_id=f"e{i+1}",
            linked_node_ids=["cn.tcp.congestion_control"],
            error_type="concept_confusion",
        )
        all_signals.extend(signals)

    assert len(all_signals) == 1
    sig = all_signals[0]
    assert sig.state_key == "knowledge_transfer"
    assert sig.claim == "transfer_failure"
    assert sig.priority == "high"


@pytest.mark.asyncio
async def test_mistake_no_duplicate_signal():
    redis = FakeRedis()
    detector = MistakeSignalDetector(redis)

    # 3 errors → first signal
    for i in range(3):
        await detector.on_error_created(
            user_id="u1", error_id=f"e{i+1}",
            linked_node_ids=["cn.tcp.congestion_control"],
        )
    # 4th error → should NOT generate duplicate signal
    signals = await detector.on_error_created(
        user_id="u1", error_id="e4",
        linked_node_ids=["cn.tcp.congestion_control"],
    )
    assert len(signals) == 0


@pytest.mark.asyncio
async def test_mistake_policy_generates_avoid_new_chapter():
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=["e1"],
        source_system="error_book",
        state_key="knowledge_transfer",
        claim="transfer_failure",
        confidence=0.8,
        scope="current_sprint",
        ttl_hours=72,
        evidence_summary="TCP 拥塞控制连续 3 次出错",
        possible_effects=["avoid_new_chapter"],
        priority="high",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, directive = result
    assert decision.primary_strategy == "repair_knowledge_bottleneck"
    assert directive.hard_constraints["avoid_new_chapter"] is True
    assert directive.hard_constraints["required_task_type"] == "worked_example_then_drill"


# ── P0-1: FirstMinuteSnapshot / ExamRescueDetector Tests ─────────────

from app.signals.exam_rescue_detector import ExamRescueDetector, FirstMinuteSnapshot


def test_exam_rescue_detects_7_day_urgent():
    """E4: '我 7 天后计网考试，零基础，想先别挂' → exam_rescue."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我 7 天后计网考试，零基础，想先别挂")

    assert snapshot is not None
    assert snapshot.detected_mode == "exam_rescue"
    assert snapshot.path_mode == "minimum_pass"
    assert snapshot.deadline_days == 7
    assert snapshot.baseline == "near_zero"
    assert snapshot.subject == "computer_networks"
    assert snapshot.confidence >= 0.6
    assert "抢救" in snapshot.first_user_visible_hypothesis


def test_exam_rescue_detects_english_exam():
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我后天英语四六级考试，基本不会")

    assert snapshot is not None
    assert snapshot.detected_mode == "exam_rescue"
    assert snapshot.subject == "english_cet"
    assert snapshot.baseline == "near_zero"


def test_exam_rescue_high_score_target():
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我 14 天后高数考试，零基础，想冲高分")

    assert snapshot is not None
    assert snapshot.path_mode == "high_score"


def test_exam_rescue_no_signal_for_normal_chat():
    """Normal chat should not trigger exam rescue."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("你好，我想了解一下这个产品")

    assert snapshot is None


def test_exam_rescue_no_signal_for_empty():
    detector = ExamRescueDetector()
    assert detector.analyze_first_message("") is None


def test_exam_rescue_to_actionable_signal():
    """Snapshot → ActionableSignal conversion."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我 7 天后计网考试，零基础，想先别挂")

    signal = detector.to_actionable_signal(snapshot, user_id="u1", message_id="msg_001")
    assert signal is not None
    assert signal.state_key == "goal_mode"
    assert signal.claim == "exam_rescue_detected"
    assert signal.confidence >= 0.5
    assert signal.priority == "high"
    assert snapshot.signal_id == signal.signal_id


def test_exam_rescue_no_signal_for_build_mode():
    """exam_build mode should not generate ActionableSignal."""
    detector = ExamRescueDetector()
    snapshot = FirstMinuteSnapshot(
        detected_mode="exam_build",
        path_mode="solid_pass",
        deadline_days=30,
        baseline="unknown",
        subject=None,
        next_best_action="standard_onboarding",
        first_user_visible_hypothesis="test",
        confidence=0.5,
    )
    signal = detector.to_actionable_signal(snapshot, user_id="u1")
    assert signal is None


@pytest.mark.asyncio
async def test_exam_rescue_policy_rule():
    """PolicyEngine has exam_rescue rule."""
    engine = PolicyEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=["msg_001"],
        source_system="first_minute",
        state_key="goal_mode",
        claim="exam_rescue_detected",
        confidence=0.85,
        scope="current_sprint",
        ttl_hours=168,
        evidence_summary="新用户首次消息检测到 7 天计网考试抢救",
        possible_effects=["exam_rescue_mode"],
        priority="high",
    )
    result = await engine.evaluate(signal)
    assert result is not None
    decision, directive = result
    assert decision.primary_strategy == "exam_rescue_sprint"
    assert directive.hard_constraints["sprint_policy"] == "seven_day_survival"
    assert directive.hard_constraints["defer_low_roi_topics"] is True


def test_exam_rescue_deadline_extraction():
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我还有3天就考线代了什么都不会")
    assert snapshot is not None
    assert snapshot.deadline_days == 3
    assert snapshot.subject == "linear_algebra"


def test_exam_rescue_relative_date_houtian():
    """Chinese relative date '后天' should give deadline_days=2."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我后天考高数，什么都不会")
    assert snapshot is not None
    assert snapshot.deadline_days == 2
    assert snapshot.confidence >= 0.5


def test_exam_rescue_relative_date_xiazhou():
    """Chinese relative date '下周' should give deadline_days=7."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我下周考数据结构，零基础")
    assert snapshot is not None
    assert snapshot.deadline_days == 7


def test_exam_rescue_no_false_positive_no_exam():
    """弱基础没有考试意图不触发 exam_rescue (C2 fix)."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我零基础，想学一下计网")
    assert snapshot is None


def test_exam_rescue_english_subject():
    """English subject names should be detected (C3 fix)."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("I have a calculus exam in 5 days, I know nothing")
    assert snapshot is not None
    assert snapshot.subject == "calculus"
    assert snapshot.deadline_days == 5


@pytest.mark.asyncio
async def test_first_minute_to_policy_pipeline():
    """E2E: Detector → Signal → PolicyEngine must produce result (W2 fix)."""
    detector = ExamRescueDetector()
    snapshot = detector.analyze_first_message("我 7 天后计网考试，零基础，想先别挂")
    signal = detector.to_actionable_signal(snapshot, user_id="u1")
    assert signal is not None
    assert signal.confidence >= 0.5, f"Confidence {signal.confidence} below policy threshold 0.5"

    engine = PolicyEngine()
    result = await engine.evaluate(signal)
    assert result is not None, "Signal was rejected by PolicyEngine (below threshold?)"
    decision, directive = result
    assert decision.primary_strategy == "exam_rescue_sprint"
    assert "seven_day_survival" in str(directive.hard_constraints)


# ── P0-2: TimeContext + StaleStateGuard Tests ─────────────────────────

from app.signals.stale_state_guard import StaleStateGuard, TimeContext, TimeDeltaPacket


def test_stale_guard_triggers_after_2_hours():
    """E5: 用户离开 2 小时 → TimeDeltaPacket."""
    guard = StaleStateGuard()
    ctx = TimeContext(
        now="2026-04-26T22:00:00+08:00",
        last_user_interaction_at="2026-04-26T20:00:00+08:00",
        elapsed_since_last_interaction_min=120,
        active_task_id="task_tcp_001",
        active_task_status="no_completion",
    )
    packet = guard.check(ctx, user_id="u1")

    assert packet is not None
    assert packet.elapsed_since_last_seen_min == 120
    assert packet.pending_task_status == "expected_finished_but_no_feedback"
    assert len(packet.resume_options) == 4
    assert packet.message_template != ""


def test_stale_guard_no_trigger_under_threshold():
    """用户只离开 30 分钟，不触发。"""
    guard = StaleStateGuard()
    ctx = TimeContext(
        now="2026-04-26T20:30:00+08:00",
        elapsed_since_last_interaction_min=30,
    )
    packet = guard.check(ctx)
    assert packet is None


def test_stale_guard_no_active_task():
    """离开时间长但没有活跃任务。"""
    guard = StaleStateGuard()
    ctx = TimeContext(
        now="2026-04-26T22:00:00+08:00",
        elapsed_since_last_interaction_min=120,
    )
    packet = guard.check(ctx)

    assert packet is not None
    assert packet.pending_task_status == "no_active_task"
    assert packet.resume_options[0]["value"] == "continue"


def test_stale_guard_resume_options_format():
    """恢复选项必须包含 4 个标准选项。"""
    guard = StaleStateGuard()
    ctx = TimeContext(
        now="2026-04-26T22:00:00+08:00",
        elapsed_since_last_interaction_min=130,
        active_task_id="task_001",
        active_task_status="started",
    )
    packet = guard.check(ctx)

    assert packet is not None
    labels = [opt["label"] for opt in packet.resume_options]
    assert "做完了，补记录" in labels
    assert "做了一半，卡住了" in labels
    assert "没开始" in labels
    assert "换个小任务" in labels


def test_stale_guard_message_contains_time():
    """返回消息必须包含时间信息。"""
    guard = StaleStateGuard()
    ctx = TimeContext(
        now="2026-04-26T22:00:00+08:00",
        elapsed_since_last_interaction_min=130,
        active_task_id="task_001",
        active_task_status="no_completion",
    )
    packet = guard.check(ctx)

    assert packet is not None
    assert "2 小时" in packet.message_template
    assert "任务" in packet.message_template


def test_stale_guard_time_context_serialization():
    """TimeContext to_dict round-trip."""
    ctx = TimeContext(
        now="2026-04-26T22:00:00+08:00",
        elapsed_since_last_interaction_min=120,
        active_task_id="task_001",
        deadline_phase="high_pressure",
    )
    d = ctx.to_dict()
    assert d["deadline_phase"] == "high_pressure"
    assert d["active_task_id"] == "task_001"


# ── P0-3: ActionableStatePacket v1 Tests ─────────────────────────

from app.signals.state_packet_builder import ActionableStatePacketBuilder


def test_state_packet_builds_from_signals():
    """从活跃信号构建 ActionableStatePacket。"""
    builder = ActionableStatePacketBuilder()
    signals = [
        ActionableSignal(
            signal_id=_uid("sig"), source_event_ids=["e1"], source_system="task_service",
            state_key="task_granularity_fit", claim="recent_task_too_large",
            confidence=0.72, scope="current_sprint", ttl_hours=72,
            evidence_summary="连续 2 次超时", possible_effects=["cap_duration"],
            priority="high",
        ),
    ]
    packet = builder.build(user_id="u1", active_signals=signals)

    assert packet.user_id == "u1"
    assert len(packet.top_states) == 1
    assert packet.top_states[0].state_key == "task_granularity_fit"
    assert packet.top_states[0].confidence == 0.72
    assert "task_granularity_fit:recent_task_too_large" in packet.risk_flags


def test_state_packet_with_directive():
    """有活跃 directive 时 next_best_action 应该引用它。"""
    builder = ActionableStatePacketBuilder()
    directive = ExecutionDirective(
        directive_id="ed_001", policy_decision_id="pd_001",
        target_module="task_generator", scope="today",
        hard_constraints={"max_task_duration_min": 25},
        user_visible_reason="test",
    )
    packet = builder.build(user_id="u1", active_directive=directive)

    assert packet.next_best_action is not None
    assert packet.next_best_action["type"] == "apply_directive"
    assert packet.next_best_action["directive_id"] == "ed_001"
    assert "task_duration_capped:25min" in packet.risk_flags


def test_state_packet_deduplicates_state_keys():
    """多个同 state_key 的信号只保留一个。"""
    builder = ActionableStatePacketBuilder()
    signals = [
        ActionableSignal(
            signal_id=_uid("sig"), source_event_ids=["e1"], source_system="task_service",
            state_key="task_granularity_fit", claim="too_large",
            confidence=0.6, scope="sprint", ttl_hours=72,
            evidence_summary="test", possible_effects=[], priority="high",
        ),
        ActionableSignal(
            signal_id=_uid("sig"), source_event_ids=["e2"], source_system="task_service",
            state_key="task_granularity_fit", claim="too_large_v2",
            confidence=0.8, scope="sprint", ttl_hours=72,
            evidence_summary="test2", possible_effects=[], priority="high",
        ),
    ]
    packet = builder.build(user_id="u1", active_signals=signals)
    assert len(packet.top_states) == 1


def test_state_packet_bottleneck_from_mistake():
    """知识迁移失败信号应该产生瓶颈。"""
    builder = ActionableStatePacketBuilder()
    signals = [
        ActionableSignal(
            signal_id=_uid("sig"), source_event_ids=["e1"], source_system="error_book",
            state_key="knowledge_transfer", claim="transfer_failure",
            confidence=0.8, scope="current_sprint", ttl_hours=72,
            evidence_summary="知识节点 cn.tcp.congestion_control 连续 3 次出错",
            possible_effects=["avoid_new_chapter"], priority="high",
        ),
    ]
    packet = builder.build(user_id="u1", active_signals=signals)

    assert packet.current_bottleneck is not None
    assert packet.current_bottleneck["type"] == "transfer_failure"
    assert packet.current_bottleneck["node_id"] == "cn.tcp.congestion_control"


def test_state_packet_goal_frame_from_exam_rescue():
    """exam_rescue 信号应该填充 goal_frame。"""
    builder = ActionableStatePacketBuilder()
    signals = [
        ActionableSignal(
            signal_id=_uid("sig"), source_event_ids=["m1"], source_system="first_minute",
            state_key="goal_mode", claim="exam_rescue_detected",
            confidence=0.85, scope="current_sprint", ttl_hours=168,
            evidence_summary="7 天计网抢救", possible_effects=["exam_rescue_mode"],
            priority="high",
        ),
    ]
    packet = builder.build(user_id="u1", active_signals=signals)

    assert packet.goal_frame.get("mode") == "exam_rescue"
    assert packet.goal_frame.get("target") == "minimum_pass"


def test_state_packet_empty_inputs():
    """无信号无 directive 应该产生空包。"""
    builder = ActionableStatePacketBuilder()
    packet = builder.build(user_id="u1")

    assert packet.user_id == "u1"
    assert len(packet.top_states) == 0
    assert len(packet.risk_flags) == 0
    assert packet.current_bottleneck is None
    assert packet.next_best_action is None


def test_state_packet_serialization():
    """ActionableStatePacket to_dict 可序列化。"""
    builder = ActionableStatePacketBuilder()
    signals = [
        ActionableSignal(
            signal_id="sig_001", source_event_ids=[], source_system="test",
            state_key="test_key", claim="test_claim",
            confidence=0.5, scope="test", ttl_hours=1,
            evidence_summary="test", possible_effects=[], priority="low",
        ),
    ]
    packet = builder.build(user_id="u1", active_signals=signals)
    d = packet.to_dict()

    assert d["user_id"] == "u1"
    assert len(d["top_states"]) == 1
    assert d["top_states"][0]["state_key"] == "test_key"


# ── P1-3: PredictedReplyOption Engine Tests ────────────────────────

from app.signals.predicted_reply_options import SpineReplyOptionEngine


def test_reply_options_for_task_granularity():
    """任务颗粒度信号应生成假设确认选项。"""
    engine = SpineReplyOptionEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="task_service",
        state_key="task_granularity_fit", claim="recent_task_too_large",
        confidence=0.72, scope="current_sprint", ttl_hours=72,
        evidence_summary="连续 2 次超时", possible_effects=["cap_duration"],
        priority="high",
    )
    question = engine.generate_options(signal)

    assert question is not None
    assert question.question_type == "hypothesis_confirm"
    assert question.state_key == "task_granularity_fit"
    assert len(question.options) >= 4  # 3 specific + 1 freeform


def test_reply_options_always_has_freeform():
    """每组选项必须包含自由输入选项。"""
    engine = SpineReplyOptionEngine()
    for state_key in ["task_granularity_fit", "knowledge_transfer", "material_utilization", "goal_mode"]:
        signal = ActionableSignal(
            signal_id=_uid("sig"), source_event_ids=[], source_system="test",
            state_key=state_key, claim="test",
            confidence=0.7, scope="test", ttl_hours=1,
            evidence_summary="test", possible_effects=[], priority="high",
        )
        question = engine.generate_options(signal)
        if question is None:
            continue
        freeform = [o for o in question.options if o.is_freeform]
        assert len(freeform) == 1, f"state_key={state_key} missing freeform option"
        assert "都不对" in freeform[0].label


def test_reply_options_disconfirming_exists():
    """每组至少有一个反驳选项。"""
    engine = SpineReplyOptionEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="test",
        confidence=0.7, scope="test", ttl_hours=1,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    question = engine.generate_options(signal)
    disconfirming = [o for o in question.options if o.is_disconfirming and not o.is_freeform]
    assert len(disconfirming) >= 1


def test_reply_options_no_template_returns_none():
    """没有模板的 state_key 应返回 None。"""
    engine = SpineReplyOptionEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key="unknown_state_key", claim="test",
        confidence=0.7, scope="test", ttl_hours=1,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    assert engine.generate_options(signal) is None


def test_reply_options_process_selection():
    """用户选择后应返回正确的状态补丁。"""
    engine = SpineReplyOptionEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="test",
        confidence=0.7, scope="test", ttl_hours=1,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    question = engine.generate_options(signal)

    # Select the "确实排大了" option
    confirm_opt = [o for o in question.options if o.semantic_value == "task_too_large"][0]
    patch = engine.process_user_selection(question, confirm_opt.option_id)

    assert patch["task_granularity_fit"] == "too_large"


def test_reply_options_process_freeform():
    """自由输入选项应包含用户文本。"""
    engine = SpineReplyOptionEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="test",
        confidence=0.7, scope="test", ttl_hours=1,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    question = engine.generate_options(signal)

    freeform = [o for o in question.options if o.is_freeform][0]
    patch = engine.process_user_selection(
        question, freeform.option_id,
        freeform_text="其实是我最近心情不好，学不进去",
    )

    assert patch["open_free_input"] is True
    assert patch["freeform_text"] == "其实是我最近心情不好，学不进去"


def test_reply_options_process_invalid_selection():
    """无效选项 ID 应返回空补丁。"""
    engine = SpineReplyOptionEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key="task_granularity_fit", claim="test",
        confidence=0.7, scope="test", ttl_hours=1,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    question = engine.generate_options(signal)
    patch = engine.process_user_selection(question, "nonexistent_id")
    assert patch == {}


def test_reply_options_serialization():
    """PredictedReplyQuestion to_dict 包含完整信息。"""
    engine = SpineReplyOptionEngine()
    signal = ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key="knowledge_transfer", claim="transfer_failure",
        confidence=0.8, scope="test", ttl_hours=1,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    question = engine.generate_options(signal)
    d = question.to_dict()

    assert d["question_type"] == "hypothesis_confirm"
    assert d["state_key"] == "knowledge_transfer"
    assert len(d["options"]) >= 4
    assert all("label" in o for o in d["options"])


# ── P1-5: SparkleSelfModel Tests ──────────────────────────────────

from app.signals.self_model import SparkleSelfModelService, SelfModelClaim, StrategyOutcome
import pytest


@pytest.fixture
def fake_redis():
    return FakeRedis()


@pytest.fixture
def self_model_svc(fake_redis):
    return SparkleSelfModelService(redis_client=fake_redis)


@pytest.mark.asyncio
async def test_self_model_record_claim(self_model_svc):
    """记录一个自我模型判断。"""
    claim = await self_model_svc.record_claim(
        user_id="u1",
        claim="任务拆小策略在 deadline<7 天时有效",
        confidence=0.65,
        scope="strategy",
        evidence=["task_timeout → reduce_duration → completion_rate_up"],
        policy_effects=["recover_execution_rhythm"],
    )
    assert claim.claim_id.startswith("smc_")
    assert claim.confidence == 0.65
    assert claim.scope == "strategy"
    assert claim.outcome is None


@pytest.mark.asyncio
async def test_self_model_record_outcome(self_model_svc):
    """记录策略执行结果并更新 claim。"""
    claim = await self_model_svc.record_claim(
        user_id="u1",
        claim="exam_rescue 策略有效",
        confidence=0.70,
        scope="current_sprint",
    )
    outcome = await self_model_svc.record_outcome(
        user_id="u1",
        directive_id="dir_001",
        claim_id=claim.claim_id,
        expected_outcome="用户完成抢救任务",
        actual_outcome={"completed": True, "user_feedback": ""},
    )
    assert outcome.outcome_id.startswith("smo_")
    assert outcome.attribution["effect"] == "effective"
    assert outcome.next_policy_suggestion == "maintain_current_strategy"


@pytest.mark.asyncio
async def test_self_model_outcome_negative_feedback(self_model_svc):
    """用户完成了但反馈负面 → completed_but_resented。"""
    claim = await self_model_svc.record_claim(
        user_id="u1",
        claim="pushy 策略",
        confidence=0.60,
        scope="current_sprint",
    )
    outcome = await self_model_svc.record_outcome(
        user_id="u1",
        directive_id="dir_002",
        claim_id=claim.claim_id,
        expected_outcome="用户完成任务",
        actual_outcome={"completed": True, "user_feedback": "negative"},
    )
    assert outcome.attribution["effect"] == "completed_but_resented"
    assert outcome.next_policy_suggestion == "adjust_tone"


@pytest.mark.asyncio
async def test_self_model_outcome_insufficient(self_model_svc):
    """用户不会做 → insufficient。"""
    claim = await self_model_svc.record_claim(
        user_id="u1",
        claim="任务难度合理",
        confidence=0.50,
        scope="current_sprint",
    )
    outcome = await self_model_svc.record_outcome(
        user_id="u1",
        directive_id="dir_003",
        claim_id=claim.claim_id,
        expected_outcome="用户完成练习",
        actual_outcome={"completed": False, "user_feedback": "不会做"},
    )
    assert outcome.attribution["effect"] == "insufficient"
    assert "switch_strategy:" in (outcome.next_policy_suggestion or "")


@pytest.mark.asyncio
async def test_self_model_confidence_adjustment(self_model_svc):
    """策略有效时置信度上升，无效时下降。"""
    claim = await self_model_svc.record_claim(
        user_id="u1",
        claim="初始策略",
        confidence=0.50,
        scope="current_sprint",
    )
    # 有效结果 → 置信度上升
    await self_model_svc.record_outcome(
        user_id="u1",
        directive_id="dir_010",
        claim_id=claim.claim_id,
        expected_outcome="ok",
        actual_outcome={"completed": True, "user_feedback": ""},
    )
    claims = await self_model_svc.get_active_claims("u1")
    updated = [c for c in claims if c.claim_id == claim.claim_id][0]
    assert updated.confidence > 0.50
    assert updated.outcome == "effective"


@pytest.mark.asyncio
async def test_self_model_get_active_claims(self_model_svc):
    """获取用户活跃 claims。"""
    await self_model_svc.record_claim(
        user_id="u2", claim="c1", confidence=0.5, scope="strategy",
    )
    await self_model_svc.record_claim(
        user_id="u2", claim="c2", confidence=0.6, scope="current_sprint",
    )
    claims = await self_model_svc.get_active_claims("u2")
    assert len(claims) == 2


@pytest.mark.asyncio
async def test_self_model_user_correction(self_model_svc):
    """用户纠正记录为高置信度 claim。"""
    claim = await self_model_svc.record_user_correction(
        user_id="u1",
        signal_id="sig_001",
        reason="不是任务太大，是我不知道前置知识",
    )
    assert claim.confidence == 0.90
    assert "retract_related_directive" in claim.policy_effects


@pytest.mark.asyncio
async def test_self_model_max_claims_cap(self_model_svc):
    """claims 列表不超过 _MAX_CLAIMS。"""
    for i in range(55):
        await self_model_svc.record_claim(
            user_id="u3", claim=f"claim_{i}", confidence=0.5, scope="strategy",
        )
    claims = await self_model_svc.get_active_claims("u3", limit=100)
    assert len(claims) <= 50


@pytest.mark.asyncio
async def test_self_model_serialization():
    """SelfModelClaim 和 StrategyOutcome to_dict 完整。"""
    claim = SelfModelClaim(
        claim_id="smc_test", claim="test", confidence=0.8, scope="strategy",
        evidence=["e1"], counter_evidence=["ce1"], policy_effects=["p1"],
    )
    d = claim.to_dict()
    assert d["claim_id"] == "smc_test"
    assert d["confidence"] == 0.8

    outcome = StrategyOutcome(
        outcome_id="smo_test", directive_id="dir", claim_id="smc_test",
        expected_outcome="ok", actual_outcome={"completed": True},
        attribution={"effect": "effective"},
    )
    d2 = outcome.to_dict()
    assert d2["outcome_id"] == "smo_test"
    assert d2["attribution"]["effect"] == "effective"


# ── P1-1: AchievementReinforcementConsumer Tests ──────────────────

from app.signals.achievement_reinforcement import AchievementReinforcementConsumer


@pytest.fixture
def achievement_consumer():
    return AchievementReinforcementConsumer()


def test_achievement_high_momentum(achievement_consumer):
    """7天解锁3个成就+2连击 → momentum >= 0.7 → high signal。"""
    signal = achievement_consumer.process_achievement_event(
        user_id="u1",
        event_type="achievement.unlocked",
        recent_unlocks=3,
        active_streaks=2,
        in_progress_count=4,
    )
    assert signal is not None
    assert signal.claim == "momentum_high"
    assert signal.state_key == "growth_momentum"
    assert signal.priority == "low"


def test_achievement_stalled_momentum(achievement_consumer):
    """0解锁但有进行中 → stalled signal。"""
    signal = achievement_consumer.process_achievement_event(
        user_id="u1",
        event_type="achievement.progress",
        recent_unlocks=0,
        active_streaks=0,
        in_progress_count=3,
    )
    assert signal is not None
    assert signal.claim == "momentum_stalled"
    assert signal.priority == "medium"


def test_achievement_moderate_no_signal(achievement_consumer):
    """中等动量 → 不产生信号。"""
    signal = achievement_consumer.process_achievement_event(
        user_id="u1",
        event_type="achievement.progress",
        recent_unlocks=1,
        active_streaks=1,
        in_progress_count=2,
    )
    assert signal is None


def test_achievement_zero_no_signal(achievement_consumer):
    """零活跃零进度 → 不产生 stalled（in_progress=0）。"""
    signal = achievement_consumer.process_achievement_event(
        user_id="u1",
        event_type="achievement.progress",
        recent_unlocks=0,
        active_streaks=0,
        in_progress_count=0,
    )
    assert signal is None


def test_achievement_momentum_score_calculation(achievement_consumer):
    """动量分数计算验证。"""
    m = achievement_consumer.compute_momentum(
        user_id="u1", recent_unlocks=4, active_streaks=3, in_progress_count=5,
    )
    assert m.momentum_score == 1.0  # 全部满分
    assert m.recent_unlocks == 4
    assert m.active_streaks == 3


def test_achievement_momentum_serialization(achievement_consumer):
    """AchievementMomentum to_dict。"""
    m = achievement_consumer.compute_momentum(
        user_id="u1", recent_unlocks=1, active_streaks=0, in_progress_count=1,
    )
    d = m.to_dict()
    assert d["user_id"] == "u1"
    assert "momentum_score" in d


# ── P1-4: RecallOpportunity Tests ─────────────────────────────────

from app.signals.recall_opportunity import RecallOpportunityDetector


@pytest.fixture
def recall_detector():
    return RecallOpportunityDetector()


def test_recall_undigested_material(recall_detector):
    """上传了资料但没诊断 → 触发召回。"""
    trigger = recall_detector.check_undigested_material(
        user_id="u1", uploaded_files_count=3, diagnosed_files_count=1,
        hours_since_upload=2.0,
    )
    assert trigger is not None
    assert trigger.trigger_type == "undigested_material"
    assert trigger.context["undigested"] == 2


def test_recall_no_trigger_all_diagnosed(recall_detector):
    """所有资料都诊断了 → 不触发。"""
    trigger = recall_detector.check_undigested_material(
        user_id="u1", uploaded_files_count=2, diagnosed_files_count=2,
        hours_since_upload=5.0,
    )
    assert trigger is None


def test_recall_task_not_started(recall_detector):
    """任务超过 1 小时未启动 → 触发召回。"""
    trigger = recall_detector.check_task_not_started(
        user_id="u1", task_id="t1", hours_since_assignment=2.0,
        has_started=False,
    )
    assert trigger is not None
    assert trigger.trigger_type == "task_not_started"


def test_recall_task_started_no_trigger(recall_detector):
    """任务已启动 → 不触发。"""
    trigger = recall_detector.check_task_not_started(
        user_id="u1", task_id="t1", hours_since_assignment=5.0,
        has_started=True,
    )
    assert trigger is None


def test_recall_task_too_recent(recall_detector):
    """任务分配不到 1 小时 → 不触发。"""
    trigger = recall_detector.check_task_not_started(
        user_id="u1", task_id="t1", hours_since_assignment=0.5,
        has_started=False,
    )
    assert trigger is None


def test_recall_task_missed(recall_detector):
    """任务错过 deadline → 高优先级召回。"""
    trigger = recall_detector.check_task_missed(
        user_id="u1", task_id="t1", deadline_hours=-3.0,
        is_completed=False,
    )
    assert trigger is not None
    assert trigger.urgency == "high"


def test_recall_pre_exam_silence(recall_detector):
    """考前 48h 沉默 → 触发召回。"""
    trigger = recall_detector.check_pre_exam_silence(
        user_id="u1", exam_deadline_days=1.5,
        hours_since_last_activity=5.0,
    )
    assert trigger is not None
    assert trigger.trigger_type == "pre_exam_silence"


def test_recall_pre_exam_still_active(recall_detector):
    """考前但用户还活跃 → 不触发。"""
    trigger = recall_detector.check_pre_exam_silence(
        user_id="u1", exam_deadline_days=1.0,
        hours_since_last_activity=0.5,
    )
    assert trigger is None


def test_recall_to_actionable_signal(recall_detector):
    """RecallTrigger → ActionableSignal 转换。"""
    trigger = recall_detector.check_pre_exam_silence(
        user_id="u1", exam_deadline_days=0.5,
        hours_since_last_activity=10.0,
    )
    signal = recall_detector.to_actionable_signal(trigger)
    assert signal.state_key == "recall_needed"
    assert signal.claim == "pre_exam_silence"
    assert signal.confidence == 0.80


def test_recall_cooldown(recall_detector):
    """冷却期返回正确值。"""
    assert recall_detector.get_cooldown_seconds("pre_exam_silence") == 1800
    assert recall_detector.get_cooldown_seconds("task_not_started") == 7200


# ── P1-2: AuroraWakeEligibility Tests ─────────────────────────────

from app.signals.aurora_wake import AuroraWakeJudge


@pytest.fixture
def wake_judge():
    return AuroraWakeJudge()


def test_wake_strategy_failure(wake_judge):
    """连续 2 次负向 → strategy_recalibration。"""
    result = wake_judge.judge(
        user_id="u1",
        quota_remaining=2,
        cooldown_status="available",
        consecutive_negative_outcomes=2,
    )
    assert result.can_wake is True
    assert result.recommended_session_type == "strategy_recalibration"
    assert "consecutive_strategy_failure" in result.wake_reasons


def test_wake_user_requested(wake_judge):
    """用户主动请求 → deep_review。"""
    result = wake_judge.judge(
        user_id="u1",
        quota_remaining=1,
        cooldown_status="available",
        user_requested_deep_review=True,
    )
    assert result.can_wake is True
    assert result.recommended_session_type == "deep_review"


def test_wake_momentum_stalled(wake_judge):
    """动量停滞 → motivation_check。"""
    result = wake_judge.judge(
        user_id="u1",
        quota_remaining=3,
        cooldown_status="available",
        momentum_stalled=True,
    )
    assert result.can_wake is True
    assert "momentum_stalled" in result.wake_reasons


def test_wake_no_reason(wake_judge):
    """无唤醒理由 → 不可唤醒。"""
    result = wake_judge.judge(
        user_id="u1",
        quota_remaining=3,
        cooldown_status="available",
    )
    assert result.can_wake is False
    assert result.wake_reasons == []


def test_wake_quota_exhausted(wake_judge):
    """配额耗尽 → 不可唤醒（即使有理由）。"""
    result = wake_judge.judge(
        user_id="u1",
        quota_remaining=0,
        cooldown_status="available",
        consecutive_negative_outcomes=3,
    )
    assert result.can_wake is False
    assert result.cooldown_status == "exhausted"


def test_wake_cooldown_active(wake_judge):
    """冷却中 → 不可唤醒。"""
    result = wake_judge.judge(
        user_id="u1",
        quota_remaining=2,
        cooldown_status="cooling",
        cooldown_minutes_left=30,
        consecutive_negative_outcomes=2,
    )
    assert result.can_wake is False
    assert result.cooldown_minutes_left == 30


def test_wake_serialization(wake_judge):
    """AuroraWakeEligibility to_dict。"""
    result = wake_judge.judge(
        user_id="u1",
        quota_remaining=1,
        cooldown_status="available",
        user_requested_deep_review=True,
    )
    d = result.to_dict()
    assert d["can_wake"] is True
    assert d["quota_remaining"] == 1


# ── P1-6: CommunitySignal v1 Tests ────────────────────────────────

from app.signals.community_signal import CommunitySignalDetector


@pytest.fixture
def community_detector():
    return CommunitySignalDetector()


def test_community_cohort_mistake(community_detector):
    """群体 >= 5 + 出错率 >= 40% → 检测到共性错因。"""
    pattern = community_detector.detect_cohort_mistake(
        knowledge_node_id="tcp_congestion",
        subject="computer_networks",
        mistake_type="concept_confusion",
        cohort_size=10,
        error_count=6,
        common_misconception="混淆拥塞控制和流量控制",
    )
    assert pattern is not None
    assert pattern.frequency_ratio == 0.6


def test_community_cohort_too_small(community_detector):
    """群体 < 5 → 不检测（隐私保护）。"""
    pattern = community_detector.detect_cohort_mistake(
        knowledge_node_id="tcp",
        subject="cn", mistake_type="test",
        cohort_size=3, error_count=3,
        common_misconception="test",
    )
    assert pattern is None


def test_community_cohort_low_ratio(community_detector):
    """出错率 < 40% → 不检测。"""
    pattern = community_detector.detect_cohort_mistake(
        knowledge_node_id="tcp", subject="cn", mistake_type="test",
        cohort_size=10, error_count=3,
        common_misconception="test",
    )
    assert pattern is None


def test_community_shared_resource(community_detector):
    """使用人数 >= 3 + 相关度 >= 0.5 → 推荐资料。"""
    rec = community_detector.detect_shared_resource(
        resource_id="r1",
        resource_title="计网速通笔记",
        subject="computer_networks",
        recommendation_reason="highly_rated_by_cohort",
        peer_count=8,
        relevance_score=0.75,
    )
    assert rec is not None
    assert rec.peer_count == 8


def test_community_shared_resource_low_relevance(community_detector):
    """相关度 < 0.5 → 不推荐。"""
    rec = community_detector.detect_shared_resource(
        resource_id="r2", resource_title="test", subject="cn",
        recommendation_reason="test", peer_count=5, relevance_score=0.3,
    )
    assert rec is None


def test_community_shared_resource_too_few_peers(community_detector):
    """使用人数 < 3 → 不推荐。"""
    rec = community_detector.detect_shared_resource(
        resource_id="r3", resource_title="test", subject="cn",
        recommendation_reason="test", peer_count=1, relevance_score=0.9,
    )
    assert rec is None


def test_community_mistake_to_signal(community_detector):
    """CohortMistakePattern → ActionableSignal，priority <= medium。"""
    pattern = community_detector.detect_cohort_mistake(
        knowledge_node_id="tcp",
        subject="cn", mistake_type="confusion",
        cohort_size=10, error_count=7,
        common_misconception="test",
    )
    signal = community_detector.to_actionable_signal(pattern)
    assert signal.state_key == "community_cohort_pattern"
    assert signal.priority == "medium"
    assert signal.confidence <= 0.85


def test_community_resource_to_signal(community_detector):
    """SharedResourceRecommendation → ActionableSignal，priority=low。"""
    rec = community_detector.detect_shared_resource(
        resource_id="r1", resource_title="test", subject="cn",
        recommendation_reason="test", peer_count=5, relevance_score=0.8,
    )
    signal = community_detector.to_actionable_signal(rec)
    assert signal.state_key == "community_resource_recommendation"
    assert signal.priority == "low"


def test_community_no_high_priority(community_detector):
    """社群信号优先级永远不超过 medium（铁律验证）。"""
    # 构造极端情况
    pattern = community_detector.detect_cohort_mistake(
        knowledge_node_id="x", subject="s", mistake_type="m",
        cohort_size=100, error_count=99,
        common_misconception="extreme",
    )
    signal = community_detector.to_actionable_signal(pattern)
    assert signal.priority in ("low", "medium")


# ── PolicyEngine gap coverage: growth_momentum + recall_needed rules ──

from app.signals.policy_engine import PolicyEngine


@pytest.fixture
def policy_engine():
    return PolicyEngine()


@pytest.mark.asyncio
async def test_policy_growth_momentum_high(policy_engine):
    """growth_momentum/momentum_high → sustain_momentum strategy。"""
    from app.signals.types import ActionableSignal
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="growth_momentum", claim="momentum_high",
        confidence=0.80, scope="current_sprint", ttl_hours=48,
        evidence_summary="test", possible_effects=[], priority="low",
    )
    result = await policy_engine.evaluate(signal)
    assert result is not None
    decision, directive = result
    assert decision.primary_strategy == "sustain_momentum"
    assert "tone" in decision.soft_biases
    assert decision.visibility == "status_band"


@pytest.mark.asyncio
async def test_policy_growth_momentum_stalled(policy_engine):
    """growth_momentum/momentum_stalled → rekindle_engagement。"""
    from app.signals.types import ActionableSignal
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="growth_momentum", claim="momentum_stalled",
        confidence=0.70, scope="current_sprint", ttl_hours=24,
        evidence_summary="test", possible_effects=[], priority="medium",
    )
    result = await policy_engine.evaluate(signal)
    assert result is not None
    assert result[0].primary_strategy == "rekindle_engagement"


@pytest.mark.asyncio
async def test_policy_recall_pre_exam(policy_engine):
    """recall_needed/pre_exam_silence → urgent_exam_prep + hard constraints。"""
    from app.signals.types import ActionableSignal
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="recall_needed", claim="pre_exam_silence",
        confidence=0.80, scope="current_sprint", ttl_hours=6,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    result = await policy_engine.evaluate(signal)
    assert result is not None
    decision, directive = result
    assert decision.primary_strategy == "urgent_exam_prep"
    assert directive.hard_constraints.get("prefer_high_yield_review") is True


@pytest.mark.asyncio
async def test_policy_recall_task_missed(policy_engine):
    """recall_needed/task_missed → requires_user_confirmation。"""
    from app.signals.types import ActionableSignal
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="recall_needed", claim="task_missed",
        confidence=0.80, scope="current_sprint", ttl_hours=6,
        evidence_summary="test", possible_effects=[], priority="high",
    )
    result = await policy_engine.evaluate(signal)
    assert result is not None
    assert result[0].requires_user_confirmation is True


@pytest.mark.asyncio
async def test_policy_recall_undigested_material(policy_engine):
    """recall_needed/undigested_material → prompt_diagnostic。"""
    from app.signals.types import ActionableSignal
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="recall_needed", claim="undigested_material",
        confidence=0.80, scope="current_sprint", ttl_hours=6,
        evidence_summary="test", possible_effects=[], priority="medium",
    )
    result = await policy_engine.evaluate(signal)
    assert result is not None
    assert result[0].primary_strategy == "prompt_diagnostic"


@pytest.mark.asyncio
async def test_policy_growth_momentum_no_rule_for_other_claims(policy_engine):
    """growth_momentum/unknown_claim → no match。"""
    from app.signals.types import ActionableSignal
    signal = ActionableSignal(
        signal_id="sig_test", source_event_ids=[], source_system="test",
        state_key="growth_momentum", claim="some_other_claim",
        confidence=0.80, scope="current_sprint", ttl_hours=48,
        evidence_summary="test", possible_effects=[], priority="low",
    )
    result = await policy_engine.evaluate(signal)
    assert result is None


# ── P2 Integration: SpineOrchestrator P1 wiring ─────────────────────

from unittest.mock import AsyncMock, MagicMock

from app.signals.spine_orchestrator import SpineOrchestrator


def _make_redis_mock():
    redis = AsyncMock()
    redis._store: dict[str, str] = {}
    redis._sets: dict[str, set] = {}

    async def _set(key, value, ex=None):
        redis._store[key] = value

    async def _get(key):
        return redis._store.get(key)

    async def _delete(key):
        redis._store.pop(key, None)

    async def _smembers(key):
        return redis._sets.get(key, set())

    async def _sadd(key, *members):
        s = redis._sets.setdefault(key, set())
        for m in members:
            s.add(m)

    async def _srem(key, *members):
        s = redis._sets.get(key, set())
        for m in members:
            s.discard(m)

    redis.set = _set
    redis.get = _get
    redis.delete = _delete
    redis.smembers = _smembers
    redis.sadd = _sadd
    redis.srem = _srem
    redis.lpush = AsyncMock()
    redis.lrange = AsyncMock(return_value=[])
    redis.ltrim = AsyncMock()
    return redis


@pytest.fixture
def spine():
    return SpineOrchestrator(_make_redis_mock())


@pytest.mark.asyncio
async def test_spine_achievement_high_momentum_pipeline(spine):
    """on_achievement_event → high momentum → trace with policy。"""
    trace = await spine.on_achievement_event(
        user_id="u1",
        achievement_type="streak",
        achievement_id="seven_day_streak",
        recent_unlocks=3,
        active_streaks=2,
        in_progress_count=4,
    )
    assert trace is not None
    assert "achievement_seven_day_streak" in trace.raw_event_ids
    assert "user_response" in trace.outcome_to_measure


@pytest.mark.asyncio
async def test_spine_achievement_moderate_no_trace(spine):
    """on_achievement_event → moderate momentum → no signal → None。"""
    trace = await spine.on_achievement_event(
        user_id="u1",
        achievement_type="task_complete",
        achievement_id="first_task",
        recent_unlocks=1,
        active_streaks=1,
        in_progress_count=2,
    )
    assert trace is None


@pytest.mark.asyncio
async def test_spine_recall_undigested_pipeline(spine):
    """on_recall_check(undigested_material) → trace with policy。"""
    trace = await spine.on_recall_check(
        user_id="u1",
        trigger_type="undigested_material",
        uploaded_files_count=3,
        diagnosed_files_count=1,
        hours_since_upload=2.0,
    )
    assert trace is not None
    assert "recall_undigested_material" in trace.raw_event_ids


@pytest.mark.asyncio
async def test_spine_recall_task_missed_pipeline(spine):
    """on_recall_check(task_missed) → trace with high urgency policy。"""
    trace = await spine.on_recall_check(
        user_id="u1",
        trigger_type="task_missed",
        task_id="t1",
        deadline_hours=-3.0,
        is_completed=False,
    )
    assert trace is not None


@pytest.mark.asyncio
async def test_spine_recall_pre_exam_pipeline(spine):
    """on_recall_check(pre_exam_silence) → trace with hard constraints。"""
    trace = await spine.on_recall_check(
        user_id="u1",
        trigger_type="pre_exam_silence",
        exam_deadline_days=1.0,
        hours_since_last_activity=6.0,
    )
    assert trace is not None


@pytest.mark.asyncio
async def test_spine_recall_no_trigger(spine):
    """on_recall_check with no trigger condition met → None。"""
    trace = await spine.on_recall_check(
        user_id="u1",
        trigger_type="task_not_started",
        task_id="t1",
        hours_since_assignment=0.5,
        has_started=False,
    )
    assert trace is None


# ── P2 Extended Integration Tests ─────────────────────────────────

@pytest.mark.asyncio
async def test_spine_exam_rescue_pipeline(spine):
    """on_first_message → exam rescue → trace with policy。"""
    trace = await spine.on_first_message(
        user_id="u1",
        message="我7天后计网考试，零基础，想先别挂",
    )
    assert trace is not None
    assert "first_message_exam_rescue" in trace.raw_event_ids


@pytest.mark.asyncio
async def test_spine_exam_no_rescue(spine):
    """on_first_message → normal chat → None。"""
    trace = await spine.on_first_message(
        user_id="u1",
        message="你好，我想学一下编程",
    )
    assert trace is None


@pytest.mark.asyncio
async def test_spine_stale_return(spine):
    """on_user_return → stale → trace。"""
    trace = await spine.on_user_return(
        user_id="u1",
        time_context={
            "now": "2026-04-27T12:00:00Z",
            "timezone": "Asia/Shanghai",
            "goal_deadline": None,
            "last_user_interaction_at": "2026-04-27T10:00:00Z",
            "elapsed_since_last_interaction_min": 120,
            "active_task_id": "t1",
            "deadline_phase": "normal_sprint",
        },
    )
    assert trace is not None


@pytest.mark.asyncio
async def test_spine_not_stale(spine):
    """on_user_return → not stale → None。"""
    trace = await spine.on_user_return(
        user_id="u1",
        time_context={
            "now": "2026-04-27T12:00:00Z",
            "timezone": "Asia/Shanghai",
            "goal_deadline": None,
            "last_user_interaction_at": "2026-04-27T11:30:00Z",
            "elapsed_since_last_interaction_min": 30,
            "active_task_id": "t1",
            "deadline_phase": "normal_sprint",
        },
    )
    assert trace is None


@pytest.mark.asyncio
async def test_spine_build_state_packet(spine):
    """build_state_packet → ActionableStatePacket。"""
    packet = await spine.build_state_packet(user_id="u1")
    assert packet.user_id == "u1"
    assert isinstance(packet.top_states, list)


@pytest.mark.asyncio
async def test_spine_community_cohort_pipeline(spine):
    """on_community_cohort_data → pattern detected → trace。"""
    trace = await spine.on_community_cohort_data(
        user_id="u1",
        knowledge_node_id="tcp",
        subject="cn",
        mistake_type="confusion",
        cohort_size=10,
        error_count=7,
        common_misconception="test",
    )
    assert trace is not None
    assert "community_cohort_mistake" in trace.raw_event_ids


@pytest.mark.asyncio
async def test_spine_community_no_pipeline(spine):
    """on_community_cohort_data → too few peers → None。"""
    trace = await spine.on_community_cohort_data(
        user_id="u1",
        knowledge_node_id="tcp",
        subject="cn",
        mistake_type="confusion",
        cohort_size=3,
        error_count=2,
        common_misconception="test",
    )
    assert trace is None


@pytest.mark.asyncio
async def test_spine_community_resource_pipeline(spine):
    """on_community_resource_data → resource recommended → trace。"""
    trace = await spine.on_community_resource_data(
        user_id="u1",
        resource_id="r1",
        resource_title="计网速通",
        subject="cn",
        peer_count=8,
        relevance_score=0.8,
    )
    assert trace is not None


def test_spine_aurora_wake_check(spine):
    """check_aurora_wake → eligible。"""
    result = spine.check_aurora_wake(
        user_id="u1",
        quota_remaining=2,
        cooldown_status="available",
        consecutive_negative_outcomes=3,
    )
    assert result.can_wake is True


def test_spine_aurora_wake_denied(spine):
    """check_aurora_wake → no reason → denied。"""
    result = spine.check_aurora_wake(
        user_id="u1",
        quota_remaining=2,
        cooldown_status="available",
    )
    assert result.can_wake is False


@pytest.mark.asyncio
async def test_spine_self_model_outcome(spine):
    """record_strategy_outcome → outcome recorded。"""
    claim = await spine.self_model.record_claim(
        user_id="u1", claim="test strategy", confidence=0.6, scope="current_sprint",
    )
    outcome = await spine.record_strategy_outcome(
        user_id="u1",
        directive_id="dir_001",
        claim_id=claim.claim_id,
        expected_outcome="user completes task",
        actual_outcome={"completed": True, "user_feedback": ""},
    )
    assert outcome.attribution["effect"] == "effective"


# ── P3: Production Wiring Tests ───────────────────────────────────────


def test_achievement_consumer_imports_spine():
    """Verify achievement_event_consumer has spine import path."""
    import ast
    import inspect
    from app.services.achievement_event_consumer import AchievementEventConsumer
    source = inspect.getsource(AchievementEventConsumer._handle_achievement_unlocked)
    assert "SpineOrchestrator" in source
    assert "on_achievement_event" in source


def test_orchestrator_imports_spine():
    """Verify orchestrator has spine exam rescue + stale guard wiring."""
    import inspect
    from app.orchestration.orchestrator import ChatOrchestrator
    source = inspect.getsource(ChatOrchestrator.process_stream)
    assert "on_first_message" in source
    assert "on_user_return" in source
    assert "SpineOrchestrator" in source


@pytest.mark.asyncio
async def test_spine_on_achievement_event_from_consumer():
    """Simulate achievement_event_consumer calling spine.on_achievement_event."""
    spine = SpineOrchestrator(FakeRedis())
    trace = await spine.on_achievement_event(
        user_id="u_ach",
        achievement_type="streak",
        achievement_id="ach_123",
        recent_unlocks=5,
        active_streaks=3,
        in_progress_count=2,
    )
    # High momentum (5 unlocks + 3 streaks) should produce a signal
    assert trace is not None
    assert "user_response" in trace.outcome_to_measure


@pytest.mark.asyncio
async def test_spine_on_first_message_exam_rescue():
    """Simulate first-message exam rescue via spine."""
    spine = SpineOrchestrator(FakeRedis())
    trace = await spine.on_first_message(
        user_id="u_exam",
        message="我7天后计网考试，零基础，想先别挂",
    )
    assert trace is not None
    assert "user_response" in trace.outcome_to_measure


@pytest.mark.asyncio
async def test_spine_on_user_return_stale():
    """Simulate user return after 2 hours."""
    spine = SpineOrchestrator(FakeRedis())
    trace = await spine.on_user_return(
        user_id="u_stale",
        time_context={
            "now": "2026-04-27T12:00:00",
            "elapsed_since_last_interaction_min": 120,
            "active_task_id": None,
        },
    )
    assert trace is not None
    assert "user_responded_to_stale_check" in trace.outcome_to_measure


# ── Layer 3: SignalRanker Tests ────────────────────────────────────────

from app.signals.signal_ranker import SignalRanker


@pytest.fixture
def ranker():
    return SignalRanker()


def _make_signal(state_key: str, claim: str, confidence: float, priority: str = "medium") -> ActionableSignal:
    return ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=[], source_system="test",
        state_key=state_key, claim=claim,
        confidence=confidence, scope="current_sprint", ttl_hours=1,
        evidence_summary="test", possible_effects=[], priority=priority,
    )


def test_rank_empty_signals(ranker):
    """空信号列表 → 空 result。"""
    result = ranker.rank([])
    assert result.ranked == []
    assert result.suppressed == []


def test_rank_single_signal(ranker):
    """单个信号 → 直接 ranked。"""
    s = _make_signal("task_granularity_fit", "too_large", 0.8, "high")
    result = ranker.rank([s])
    assert len(result.ranked) == 1
    assert result.ranked[0].signal.state_key == "task_granularity_fit"


def test_rank_orders_by_tier(ranker):
    """exam_rescue (tier 2) 排在 growth_momentum (tier 7) 之前。"""
    momentum = _make_signal("growth_momentum", "momentum_high", 0.9, "low")
    exam = _make_signal("goal_mode", "exam_rescue_detected", 0.7, "high")
    result = ranker.rank([momentum, exam])
    assert result.ranked[0].signal.state_key == "goal_mode"
    assert result.ranked[1].signal.state_key == "growth_momentum"


def test_rank_max_signals(ranker):
    """max_signals=3 时只保留前 3 个。"""
    signals = [_make_signal(f"key_{i}", f"claim_{i}", 0.5) for i in range(6)]
    result = ranker.rank(signals, max_signals=3)
    assert len(result.ranked) == 3
    assert len(result.suppressed) >= 3


def test_rank_conflict_momentum_vs_task(ranker):
    """growth_momentum + task_granularity_fit 冲突 → task_granularity_fit wins。"""
    momentum = _make_signal("growth_momentum", "momentum_high", 0.8, "low")
    task = _make_signal("task_granularity_fit", "too_large", 0.7, "high")
    result = ranker.rank([momentum, task])
    # task_granularity_fit has higher priority tier (4 vs 7)
    ranked_keys = [r.signal.state_key for r in result.ranked]
    assert "task_granularity_fit" in ranked_keys
    assert len(result.conflicts_resolved) >= 1


def test_rank_composite_score(ranker):
    """high priority + high confidence → higher composite score。"""
    high = _make_signal("task_granularity_fit", "test", 0.9, "high")
    low = _make_signal("task_granularity_fit", "test", 0.3, "low")
    result = ranker.rank([low, high])
    assert result.ranked[0].signal.confidence == 0.9


def test_rank_serialization(ranker):
    """RankingResult to_dict。"""
    s = _make_signal("knowledge_transfer", "transfer_failure", 0.8)
    result = ranker.rank([s])
    d = result.to_dict()
    assert len(d["ranked"]) == 1
    assert d["ranked"][0]["state_key"] == "knowledge_transfer"


def test_spine_rank_signals(spine):
    """SpineOrchestrator.rank_signals 委托到 SignalRanker。"""
    signals = [
        _make_signal("growth_momentum", "high", 0.9, "low"),
        _make_signal("task_granularity_fit", "too_large", 0.7, "high"),
    ]
    result = spine.rank_signals(signals)
    assert len(result.ranked) >= 1


@pytest.mark.asyncio
async def test_build_state_packet_ranks_signals(spine):
    """build_state_packet 通过 SignalRanker 排序后再构建。"""
    signals = [
        _make_signal("growth_momentum", "momentum_high", 0.9, "low"),
        _make_signal("task_granularity_fit", "too_large", 0.8, "high"),
        _make_signal("recall_needed", "task_missed", 0.7, "high"),
    ]
    packet = await spine.build_state_packet(
        user_id="u_rank",
        active_signals=signals,
    )
    # task_granularity_fit (tier 4) should rank before growth_momentum (tier 7)
    # and conflict rule suppresses growth_momentum when task_granularity_fit present
    state_keys = [s.state_key for s in packet.top_states]
    assert "task_granularity_fit" in state_keys or len(state_keys) >= 1


def test_rank_duplicate_state_keys(ranker):
    """同 state_key 的多个信号都被保留，各自独立评分。"""
    s1 = _make_signal("task_granularity_fit", "too_large", 0.9, "high")
    s2 = _make_signal("task_granularity_fit", "too_small", 0.6, "medium")
    result = ranker.rank([s1, s2])
    assert len(result.ranked) == 2
    # higher confidence should rank first
    assert result.ranked[0].signal.confidence == 0.9


def test_rank_conflict_rules_explicit(ranker):
    """冲突规则显式指定 winner/loser，不依赖排序顺序。"""
    # Pass in "wrong" order — growth_momentum first, task_granularity_fit second
    momentum = _make_signal("growth_momentum", "momentum_high", 0.9, "low")
    task = _make_signal("task_granularity_fit", "too_large", 0.7, "high")
    result = ranker.rank([momentum, task])
    ranked_keys = [r.signal.state_key for r in result.ranked]
    assert "task_granularity_fit" in ranked_keys
    assert "growth_momentum" not in ranked_keys
    assert len(result.conflicts_resolved) == 1
    assert result.conflicts_resolved[0]["winner"] == "task_granularity_fit"
    assert result.conflicts_resolved[0]["loser"] == "growth_momentum"


# ── Layer 4: StateRegister ─────────────────────────────────────────────

from app.signals.state_register import StateRegister


@pytest.fixture
def state_register(fake_redis):
    return StateRegister(fake_redis)


def _sig(state_key: str = "task_granularity_fit", claim: str = "too_large",
         confidence: float = 0.8, priority: str = "high", scope: str = "current_sprint",
         ttl: int = 72, evidence: str = "test evidence") -> ActionableSignal:
    return ActionableSignal(
        signal_id=_uid("sig"), source_event_ids=[], source_system="test",
        state_key=state_key, claim=claim, confidence=confidence,
        scope=scope, ttl_hours=ttl, evidence_summary=evidence,
        possible_effects=[], priority=priority,
    )


@pytest.mark.asyncio
async def test_state_register_upsert_new(state_register):
    """新信号 → 创建新状态。"""
    signal = _sig(confidence=0.8)
    entry = await state_register.upsert_from_signal("u1", signal)
    assert entry.state_key == "task_granularity_fit"
    assert entry.value == "too_large"
    assert entry.confidence == 0.8
    assert "test evidence" in entry.supporting_evidence


@pytest.mark.asyncio
async def test_state_register_upsert_merge_higher(state_register):
    """同 state_key 更高 confidence → 更新。"""
    await state_register.upsert_from_signal("u1", _sig(confidence=0.6, evidence="first evidence"))
    entry = await state_register.upsert_from_signal("u1", _sig(confidence=0.9, evidence="second evidence"))
    assert entry.confidence == 0.9
    # Evidence merged
    assert len(entry.supporting_evidence) == 2


@pytest.mark.asyncio
async def test_state_register_upsert_keep_lower(state_register):
    """同 state_key 更低 confidence → 保留旧的 confidence 和 value。"""
    await state_register.upsert_from_signal("u1", _sig(confidence=0.9, claim="original_claim"))
    entry = await state_register.upsert_from_signal("u1", _sig(confidence=0.5, claim="new_claim"))
    assert entry.confidence == 0.9
    assert entry.value == "original_claim"  # value NOT overwritten


@pytest.mark.asyncio
async def test_state_register_get_active(state_register):
    """获取所有活跃状态。"""
    await state_register.upsert_from_signal("u1", _sig(state_key="task_granularity_fit"))
    await state_register.upsert_from_signal("u1", _sig(state_key="knowledge_transfer", claim="transfer_failure"))
    states = await state_register.get_active_states("u1")
    assert len(states) == 2
    keys = {s.state_key for s in states}
    assert "task_granularity_fit" in keys
    assert "knowledge_transfer" in keys


@pytest.mark.asyncio
async def test_state_register_get_single(state_register):
    """获取单个状态。"""
    await state_register.upsert_from_signal("u1", _sig())
    entry = await state_register.get_state("u1", "task_granularity_fit")
    assert entry is not None
    assert entry.value == "too_large"


@pytest.mark.asyncio
async def test_state_register_get_missing(state_register):
    """不存在的状态 → None。"""
    entry = await state_register.get_state("u1", "nonexistent")
    assert entry is None


@pytest.mark.asyncio
async def test_state_register_counter_evidence(state_register):
    """添加反证。"""
    await state_register.upsert_from_signal("u1", _sig())
    ok = await state_register.add_counter_evidence("u1", "task_granularity_fit", "user completed 90min task")
    assert ok is True
    entry = await state_register.get_state("u1", "task_granularity_fit")
    assert "user completed 90min task" in entry.counter_evidence


@pytest.mark.asyncio
async def test_state_register_counter_evidence_missing(state_register):
    """为不存在的状态添加反证 → False。"""
    ok = await state_register.add_counter_evidence("u1", "nonexistent", "evidence")
    assert ok is False


@pytest.mark.asyncio
async def test_state_register_remove(state_register):
    """移除状态。"""
    await state_register.upsert_from_signal("u1", _sig())
    await state_register.remove_state("u1", "task_granularity_fit")
    entry = await state_register.get_state("u1", "task_granularity_fit")
    assert entry is None


@pytest.mark.asyncio
async def test_state_register_clear_scope(state_register):
    """清除特定 scope 的所有状态。"""
    await state_register.upsert_from_signal("u1", _sig(state_key="a", scope="turn"))
    await state_register.upsert_from_signal("u1", _sig(state_key="b", scope="sprint"))
    count = await state_register.clear_scope("u1", "turn")
    assert count == 1
    states = await state_register.get_active_states("u1")
    assert len(states) == 1
    assert states[0].state_key == "b"


@pytest.mark.asyncio
async def test_state_register_can_affect(state_register):
    """state_key 映射到正确的 can_affect。"""
    await state_register.upsert_from_signal("u1", _sig(state_key="task_granularity_fit"))
    entry = await state_register.get_state("u1", "task_granularity_fit")
    assert "ExecutionDirective" in entry.can_affect


@pytest.mark.asyncio
async def test_state_register_high_impact_confirmation(state_register):
    """低置信 + 高优先级 → requires_confirmation_if_high_impact。"""
    signal = _sig(confidence=0.3, priority="high")
    entry = await state_register.upsert_from_signal("u1", signal)
    assert entry.requires_confirmation_if_high_impact is True


@pytest.mark.asyncio
async def test_state_register_serialization(state_register):
    """StateEntry 序列化/反序列化正确。"""
    await state_register.upsert_from_signal("u1", _sig())
    entry = await state_register.get_state("u1", "task_granularity_fit")
    d = entry.to_dict()
    restored = StateEntry.from_dict(d)
    assert restored.state_key == entry.state_key
    assert restored.confidence == entry.confidence
    assert restored.ttl_hours == entry.ttl_hours
    assert restored.supporting_evidence == entry.supporting_evidence


@pytest.mark.asyncio
async def test_state_register_no_cross_user(state_register):
    """不同用户的状态互不影响。"""
    await state_register.upsert_from_signal("u1", _sig())
    states = await state_register.get_active_states("u2")
    assert len(states) == 0


@pytest.mark.asyncio
async def test_spine_get_active_states(spine):
    """SpineOrchestrator.get_active_states 委托到 StateRegister。"""
    states = await spine.get_active_states("u_test")
    assert isinstance(states, list)


@pytest.mark.asyncio
async def test_spine_pipeline_updates_state_register(spine):
    """Spine pipeline 处理信号后 StateRegister 有记录。"""
    signal = _sig()
    await spine._run_signal_pipeline(user_id="u_reg", signal=signal)
    entry = await spine.state_register.get_state("u_reg", "task_granularity_fit")
    assert entry is not None
    assert entry.value == "too_large"


@pytest.mark.asyncio
async def test_state_register_scope_ttl_clamp(state_register):
    """scope=turn ttl=999 → 被 clamp 到 1h。"""
    signal = _sig(scope="turn", ttl=999)
    entry = await state_register.upsert_from_signal("u1", signal)
    assert entry.ttl_hours == 1  # turn max is 1h


@pytest.mark.asyncio
async def test_state_register_scope_ttl_no_clamp(state_register):
    """scope=sprint ttl=72 → 不被 clamp。"""
    signal = _sig(scope="current_sprint", ttl=72)
    entry = await state_register.upsert_from_signal("u1", signal)
    assert entry.ttl_hours == 72


@pytest.mark.asyncio
async def test_state_register_evidence_cap(state_register):
    """证据列表不超过上限。"""
    for i in range(25):
        await state_register.upsert_from_signal("u1", _sig(
            confidence=0.5, evidence=f"evidence_{i}",
        ))
    entry = await state_register.get_state("u1", "task_granularity_fit")
    assert len(entry.supporting_evidence) <= 20


@pytest.mark.asyncio
async def test_state_register_expire_stale(state_register, monkeypatch):
    """expire_stale 移除过期状态。"""
    from app.signals.state_register import _parse_iso
    from datetime import timedelta

    await state_register.upsert_from_signal("u1", _sig(ttl=1))

    # Patch _is_expired to always return True
    monkeypatch.setattr(state_register, "_is_expired", lambda entry: True)
    count = await state_register.expire_stale("u1")
    assert count == 1
    states = await state_register.get_active_states("u1")
    assert len(states) == 0


@pytest.mark.asyncio
async def test_state_register_clear_scope_empty(state_register):
    """clear_scope 无匹配 → 0。"""
    await state_register.upsert_from_signal("u1", _sig(scope="sprint"))
    count = await state_register.clear_scope("u1", "turn")
    assert count == 0


