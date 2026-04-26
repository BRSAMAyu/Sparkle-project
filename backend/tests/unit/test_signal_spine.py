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
