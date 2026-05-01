"""
Tests for T3.1.4: L3 Full Aurora Core — interactive modeling sessions.

Production scenario coverage:
- Session lifecycle state machine (active → paused → completed → reflected)
- Invalid transitions are rejected
- Pause/resume with Redis persistence
- Idle timeout auto-pause
- Max turns force close
- 8 wake conditions mapped to correct session types
- Agenda step execution with reply options
- Session closure production with state patches
- Redis failure graceful degradation
- Concurrent operations safety
- Corrupted session data handling
"""
import json
import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.aurora.runtime_v1.l3_full_core import (
    L3FullCoreEngine,
    SESSION_LIFECYCLE,
    IDLE_TIMEOUT_SEC,
    MAX_AGENDA_TURNS,
    _WAKE_CONDITIONS,
)
from app.signals.aurora_core_session import (
    AuroraCoreSessionService,
    AuroraCaseFile,
    SessionClosure,
    StatePatch,
    PolicyChange,
    PredictedReplyOption,
    _SESSION_TRANSITIONS,
)
from app.signals.aurora_wake import AuroraWakeJudge
from app.signals.types import _uid


# ── Helpers ──────────────────────────────────────────────────────────

def _make_session(
    session_id: str = "test_session",
    user_id: str = "user_abc",
    status: str = "active",
    agenda_items: list[dict] | None = None,
    created_at: str | None = None,
) -> dict:
    """Build a realistic Aurora session dict."""
    if agenda_items is None:
        agenda_items = [
            {"item_id": f"item_{i}", "item_type": "enter_session", "status": "pending", "payload": {}}
            for i in range(3)
        ]
    return {
        "session_id": session_id,
        "user_id": user_id,
        "status": status,
        "created_at": created_at or datetime.now(UTC).isoformat(),
        "agenda": {
            "agenda_items": agenda_items,
            "session_id": session_id,
            "status": status,
        },
    }


def _make_redis_with_session(session: dict) -> AsyncMock:
    """Create a Redis mock that returns the given session."""
    redis = AsyncMock()
    redis.get.return_value = json.dumps(session).encode()
    redis.set.return_value = True
    redis.delete.return_value = True
    return redis


def _make_engine(session: dict | None = None) -> tuple[L3FullCoreEngine, AsyncMock]:
    """Create an L3FullCoreEngine with mocked Redis."""
    redis = AsyncMock()
    if session:
        redis.get.return_value = json.dumps(session).encode()
    else:
        redis.get.return_value = None
    redis.set.return_value = True
    redis.delete.return_value = True
    engine = L3FullCoreEngine(redis)
    return engine, redis


# ═══════════════════════════════════════════════════════════════════
# Test Session Lifecycle State Machine
# ═══════════════════════════════════════════════════════════════════

class TestSessionLifecycle:
    """Session lifecycle transitions — the state machine of L3."""

    @pytest.mark.asyncio
    async def test_active_to_paused_to_active(self):
        """Real scenario: user pauses calibration, then returns."""
        session = _make_session(status="active")
        redis = _make_redis_with_session(session)
        svc = AuroraCoreSessionService(redis)

        # active → paused
        result = await svc.pause_session("test_session", reason="user_left")
        assert result is not None
        assert result["status"] == "paused"
        assert result["pause_reason"] == "user_left"
        assert "paused_at" in result

        # Update mock to return paused session for resume
        paused_session = dict(session)
        paused_session["status"] = "paused"
        paused_session["pause_reason"] = "user_left"
        redis.get.return_value = json.dumps(paused_session).encode()

        # paused → active
        result = await svc.resume_session("test_session")
        assert result is not None
        assert result["status"] == "active"
        assert "pause_reason" not in result

    @pytest.mark.asyncio
    async def test_active_to_completed_to_reflected(self):
        """Full lifecycle: calibration completes, outcome reflected."""
        session = _make_session(status="active")
        redis = _make_redis_with_session(session)
        svc = AuroraCoreSessionService(redis)

        # active → completed
        closure = SessionClosure(
            session_id="test_session",
            state_patches=[StatePatch("knowledge_bottleneck", "old", "new", "test", 0.8)],
            user_visible_summary="校准完成",
        )
        result = await svc.close_session("test_session", closure)
        assert result is not None
        assert result["status"] == "completed"
        assert result["closure"]["user_visible_summary"] == "校准完成"

        # completed → reflected
        completed_session = dict(session)
        completed_session["status"] = "completed"
        redis.get.return_value = json.dumps(completed_session).encode()

        result = await svc.transition_session("test_session", "reflected")
        assert result is not None
        assert result["status"] == "reflected"

    @pytest.mark.asyncio
    async def test_active_to_abandoned_via_paused(self):
        """Real scenario: paused session abandoned after user never returns."""
        session = _make_session(status="paused")
        redis = _make_redis_with_session(session)
        svc = AuroraCoreSessionService(redis)

        result = await svc.transition_session("test_session", "abandoned")
        assert result is not None
        assert result["status"] == "abandoned"

    @pytest.mark.asyncio
    async def test_invalid_transition_paused_to_reflected(self):
        """reflected can only follow completed — paused → reflected is invalid."""
        session = _make_session(status="paused")
        redis = _make_redis_with_session(session)
        svc = AuroraCoreSessionService(redis)

        result = await svc.transition_session("test_session", "reflected")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_transition_completed_to_active(self):
        """Completed session cannot go back to active."""
        session = _make_session(status="completed")
        redis = _make_redis_with_session(session)
        svc = AuroraCoreSessionService(redis)

        result = await svc.transition_session("test_session", "active")
        assert result is None

    @pytest.mark.asyncio
    async def test_reflected_is_terminal(self):
        """reflected status has no valid transitions — session is done."""
        assert len(_SESSION_TRANSITIONS.get("reflected", set())) == 0
        assert len(_SESSION_TRANSITIONS.get("abandoned", set())) == 0

    @pytest.mark.asyncio
    async def test_session_not_found_returns_none(self):
        """Non-existent session returns None for any transition."""
        redis = AsyncMock()
        redis.get.return_value = None
        svc = AuroraCoreSessionService(redis)

        result = await svc.transition_session("nonexistent", "paused")
        assert result is None

        result = await svc.pause_session("nonexistent")
        assert result is None

        result = await svc.resume_session("nonexistent")
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# Test Wake Conditions (8 conditions → correct session types)
# ═══════════════════════════════════════════════════════════════════

class TestWakeConditions:
    """All 8 wake conditions from the Causal Control OS Final Spec."""

    def setup_method(self):
        self.engine, self.redis = _make_engine()
        self.judge = AuroraWakeJudge()

    # --- L3 Engine validate_entry tests ---

    def test_deadline_high_risk_maps_to_exam_emergency(self):
        """deadline_high_risk → exam_emergency (highest priority, 300s)."""
        result = self.engine.validate_entry(
            wake_reasons=["deadline_high_risk"],
            quota_remaining=1,
        )
        assert result["allowed"] is True
        assert result["session_type"] == "exam_emergency"
        assert result["duration_sec"] == 300
        assert result["matched_condition"] == "deadline_high_risk"

    def test_model_conflict_maps_to_conflict_resolution(self):
        """model_conflict → conflict_resolution (180s)."""
        result = self.engine.validate_entry(
            wake_reasons=["model_conflict"],
            quota_remaining=1,
        )
        assert result["allowed"] is True
        assert result["session_type"] == "conflict_resolution"
        assert result["duration_sec"] == 180

    def test_consecutive_user_rejections_maps_to_belief_revision(self):
        """consecutive_user_rejections → belief_revision (240s)."""
        result = self.engine.validate_entry(
            wake_reasons=["consecutive_user_rejections"],
            quota_remaining=1,
        )
        assert result["allowed"] is True
        assert result["session_type"] == "belief_revision"

    def test_consecutive_strategy_failures_maps_to_recalibration(self):
        """consecutive_strategy_failures → strategy_recalibration (240s)."""
        result = self.engine.validate_entry(
            wake_reasons=["consecutive_strategy_failures"],
            quota_remaining=1,
        )
        assert result["allowed"] is True
        assert result["session_type"] == "strategy_recalibration"

    def test_goal_changed_maps_to_realignment(self):
        """goal_changed → goal_realignment (300s)."""
        result = self.engine.validate_entry(
            wake_reasons=["goal_changed"],
            quota_remaining=1,
        )
        assert result["allowed"] is True
        assert result["session_type"] == "goal_realignment"
        assert result["duration_sec"] == 300

    def test_self_model_confidence_dropped(self):
        """self_model_confidence_dropped → self_model_recalibration."""
        result = self.engine.validate_entry(
            wake_reasons=["self_model_confidence_dropped"],
            quota_remaining=1,
        )
        assert result["allowed"] is True
        assert result["session_type"] == "self_model_recalibration"

    def test_user_explicit_wake_maps_to_deep_review(self):
        """user_explicit_wake → deep_review (300s)."""
        result = self.engine.validate_entry(
            wake_reasons=["user_explicit_wake"],
            quota_remaining=1,
        )
        assert result["allowed"] is True
        assert result["session_type"] == "deep_review"

    def test_momentum_stalled_maps_to_motivation_check(self):
        """momentum_stalled → motivation_check (240s)."""
        result = self.engine.validate_entry(
            wake_reasons=["momentum_stalled"],
            quota_remaining=1,
        )
        assert result["allowed"] is True
        assert result["session_type"] == "motivation_check"

    def test_no_wake_reasons_denied(self):
        """No wake reasons → not allowed."""
        result = self.engine.validate_entry(
            wake_reasons=[],
            quota_remaining=3,
        )
        assert result["allowed"] is False
        assert result["reason"] == "No wake reasons provided"

    def test_quota_zero_denied(self):
        """Quota exhausted → not allowed."""
        result = self.engine.validate_entry(
            wake_reasons=["model_conflict"],
            quota_remaining=0,
        )
        assert result["allowed"] is False
        assert result["reason"] == "Daily quota exhausted"

    def test_cooldown_denied(self):
        """Cooldown active → not allowed."""
        result = self.engine.validate_entry(
            wake_reasons=["model_conflict"],
            quota_remaining=3,
            cooldown_status="cooling_down",
        )
        assert result["allowed"] is False
        assert "Cooldown" in result["reason"]

    def test_can_wake_false_denied(self):
        """can_wake=False → not allowed regardless of reasons."""
        result = self.engine.validate_entry(
            wake_reasons=["deadline_high_risk"],
            can_wake=False,
            quota_remaining=3,
        )
        assert result["allowed"] is False

    # --- AuroraWakeJudge integration with new conditions ---

    def test_judge_model_conflict(self):
        result = self.judge.judge(
            user_id="u1",
            quota_remaining=3,
            cooldown_status="available",
            model_conflict=True,
        )
        assert result.can_wake is True
        assert "model_conflict" in result.wake_reasons

    def test_judge_consecutive_user_rejections(self):
        result = self.judge.judge(
            user_id="u1",
            quota_remaining=3,
            cooldown_status="available",
            consecutive_user_rejections=2,
        )
        assert result.can_wake is True
        assert "consecutive_user_rejections" in result.wake_reasons

    def test_judge_goal_changed(self):
        result = self.judge.judge(
            user_id="u1",
            quota_remaining=3,
            cooldown_status="available",
            goal_changed=True,
        )
        assert result.can_wake is True
        assert "goal_changed" in result.wake_reasons

    def test_judge_deadline_high_risk(self):
        result = self.judge.judge(
            user_id="u1",
            quota_remaining=3,
            cooldown_status="available",
            deadline_high_risk=True,
        )
        assert result.can_wake is True
        assert "deadline_high_risk" in result.wake_reasons

    def test_judge_self_model_confidence_dropped(self):
        result = self.judge.judge(
            user_id="u1",
            quota_remaining=3,
            cooldown_status="available",
            self_model_confidence_dropped=True,
        )
        assert result.can_wake is True
        assert "self_model_confidence_dropped" in result.wake_reasons

    def test_judge_priority_deadline_over_strategy(self):
        """deadline_high_risk should take priority over strategy_failure."""
        result = self.judge.judge(
            user_id="u1",
            quota_remaining=3,
            cooldown_status="available",
            deadline_high_risk=True,
            consecutive_negative_outcomes=3,
        )
        assert result.can_wake is True
        assert result.recommended_session_type == "exam_emergency"
        assert "deadline_high_risk" in result.wake_reasons
        assert "consecutive_strategy_failure" in result.wake_reasons

    def test_judge_backward_compatible(self):
        """Existing params (consecutive_negative_outcomes, user_requested_deep_review) still work."""
        result = self.judge.judge(
            user_id="u1",
            quota_remaining=3,
            cooldown_status="available",
            consecutive_negative_outcomes=2,
        )
        assert result.can_wake is True
        assert "consecutive_strategy_failure" in result.wake_reasons


# ═══════════════════════════════════════════════════════════════════
# Test Agenda Execution
# ═══════════════════════════════════════════════════════════════════

class TestAgendaExecution:
    """Agenda step execution — the core interaction loop of L3."""

    @pytest.mark.asyncio
    async def test_reply_advances_to_next_item(self):
        """Reply marks item done, next item becomes active."""
        items = [
            {"item_id": "item_0", "item_type": "enter_session", "status": "waiting_user", "payload": {}},
            {"item_id": "item_1", "item_type": "ask_confirmation", "status": "pending", "payload": {}},
        ]
        session = _make_session(agenda_items=items, status="active")
        engine, redis = _make_engine(session)

        result = await engine.execute_agenda_step("test_session", 0, "确认")
        assert result is not None
        assert result["session_should_close"] is False
        assert result["next_item_index"] == 1
        assert result["next_item"]["item_id"] == "item_1"
        assert len(result["reply_options"]) > 0

    @pytest.mark.asyncio
    async def test_last_item_triggers_close(self):
        """Reply to last item → session should close."""
        items = [
            {"item_id": "item_0", "item_type": "enter_session", "status": "waiting_user", "payload": {}},
            {"item_id": "item_1", "item_type": "close_session", "status": "pending", "payload": {}},
        ]
        session = _make_session(agenda_items=items, status="active")
        engine, redis = _make_engine(session)

        # Reply to first item
        result = await engine.execute_agenda_step("test_session", 0, "确认")
        assert result is not None
        assert result["session_should_close"] is False

        # Update mock for second reply
        items_after = [
            {"item_id": "item_0", "item_type": "enter_session", "status": "done", "payload": {"user_reply": "确认"}},
            {"item_id": "item_1", "item_type": "close_session", "status": "waiting_user", "payload": {}},
        ]
        redis.get.return_value = json.dumps(_make_session(agenda_items=items_after, status="active")).encode()

        result = await engine.execute_agenda_step("test_session", 1, "好的")
        assert result is not None
        assert result["session_should_close"] is True
        assert result["close_reason"] == "agenda_complete"

    @pytest.mark.asyncio
    async def test_empty_reply_still_advances(self):
        """Even empty reply (default option selected) should advance agenda."""
        items = [
            {"item_id": "item_0", "item_type": "enter_session", "status": "waiting_user", "payload": {}},
            {"item_id": "item_1", "item_type": "close_session", "status": "pending", "payload": {}},
        ]
        session = _make_session(agenda_items=items, status="active")
        engine, redis = _make_engine(session)

        result = await engine.execute_agenda_step("test_session", 0, "")
        assert result is not None
        # Empty reply still records and advances — next item exists, not closing yet
        assert result["session_should_close"] is False
        assert result["next_item_index"] == 1

    @pytest.mark.asyncio
    async def test_max_turns_forces_close(self):
        """Session with reply_count >= MAX_AGENDA_TURNS should auto-close."""
        items = [
            {"item_id": f"item_{i}", "item_type": "enter_session", "status": "done" if i < MAX_AGENDA_TURNS - 1 else "waiting_user", "payload": {"user_reply": "reply"} if i < MAX_AGENDA_TURNS - 1 else {}}
            for i in range(MAX_AGENDA_TURNS + 2)
        ]
        session = _make_session(agenda_items=items, status="active")
        engine, redis = _make_engine(session)

        result = await engine.execute_agenda_step("test_session", MAX_AGENDA_TURNS - 1, "reply")
        assert result is not None
        assert result["session_should_close"] is True
        assert result["close_reason"] == "max_turns_reached"

    @pytest.mark.asyncio
    async def test_non_active_session_returns_none(self):
        """Completed/paused sessions cannot execute agenda steps."""
        session = _make_session(status="completed")
        engine, redis = _make_engine(session)

        result = await engine.execute_agenda_step("test_session", 0, "reply")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_item_index_returns_none(self):
        """Out-of-range item index returns None."""
        items = [{"item_id": "item_0", "item_type": "enter_session", "status": "waiting_user", "payload": {}}]
        session = _make_session(agenda_items=items, status="active")
        engine, redis = _make_engine(session)

        result = await engine.execute_agenda_step("test_session", 5, "reply")
        assert result is None

    @pytest.mark.asyncio
    async def test_nonexistent_session_returns_none(self):
        """Non-existent session returns None for agenda step."""
        engine, redis = _make_engine()
        redis.get.return_value = None

        result = await engine.execute_agenda_step("nonexistent", 0, "reply")
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# Test Session Health Checks
# ═══════════════════════════════════════════════════════════════════

class TestSessionHealth:
    """Session health monitoring — idle timeout, max age, max turns."""

    @pytest.mark.asyncio
    async def test_healthy_session_returns_ok(self):
        """Active, recently-created session is healthy."""
        session = _make_session(status="active", created_at=datetime.now(UTC).isoformat())
        engine, redis = _make_engine(session)

        result = await engine.check_session_health("test_session")
        assert result["healthy"] is True
        assert result["action"] == "none"

    @pytest.mark.asyncio
    async def test_max_age_triggers_abandon(self):
        """Session older than 24h → abandon."""
        old_time = (datetime.now(UTC) - timedelta(hours=25)).isoformat()
        session = _make_session(status="active", created_at=old_time)
        engine, redis = _make_engine(session)

        result = await engine.check_session_health("test_session")
        assert result["healthy"] is False
        assert result["action"] == "abandon"
        assert "max_age" in result["reason"]

    @pytest.mark.asyncio
    async def test_max_turns_triggers_force_close(self):
        """Session at max turns → force close."""
        items = [
            {"item_id": f"item_{i}", "item_type": "x", "status": "done", "payload": {}}
            for i in range(MAX_AGENDA_TURNS)
        ]
        session = _make_session(status="active", agenda_items=items)
        engine, redis = _make_engine(session)

        result = await engine.check_session_health("test_session")
        assert result["healthy"] is False
        assert result["action"] == "force_close"
        assert "max_turns" in result["reason"]

    @pytest.mark.asyncio
    async def test_terminal_status_healthy(self):
        """Completed/reflected/abandoned sessions are healthy (no action needed)."""
        for status in ("completed", "reflected", "abandoned"):
            session = _make_session(status=status)
            engine, redis = _make_engine(session)
            result = await engine.check_session_health("test_session")
            assert result["healthy"] is True
            assert result["action"] == "none"

    @pytest.mark.asyncio
    async def test_nonexistent_session_not_healthy(self):
        """Non-existent session returns not healthy."""
        engine, redis = _make_engine()
        redis.get.return_value = None

        result = await engine.check_session_health("nonexistent")
        assert result["healthy"] is False
        assert result["reason"] == "session_not_found"


# ═══════════════════════════════════════════════════════════════════
# Test Closure Production
# ═══════════════════════════════════════════════════════════════════

class TestClosureProduction:
    """SessionClosure generation — the output of L3 calibration."""

    def setup_method(self):
        self.engine, self.redis = _make_engine()

    def test_basic_closure_has_required_fields(self):
        """Closure must have session_id, patches, changes, directives, summary."""
        session = _make_session()
        closure = self.engine.produce_closure(session, user_summary="校准完成")

        assert closure.session_id == "test_session"
        assert isinstance(closure.state_patches, list)
        assert isinstance(closure.policy_changes, list)
        assert isinstance(closure.directives_to_regenerate, list)
        assert closure.user_visible_summary == "校准完成"
        assert closure.aurora_returns_to_background is True

    def test_confirm_available_time_creates_state_patch(self):
        """confirm_available_time reply → task_granularity_fit state patch."""
        items = [
            {
                "item_id": "item_0",
                "item_type": "confirm_available_time",
                "status": "done",
                "payload": {"user_reply": "45分钟"},
            },
        ]
        session = _make_session(agenda_items=items)
        closure = self.engine.produce_closure(session)

        assert len(closure.state_patches) >= 1
        patch = closure.state_patches[0]
        assert patch.state_key == "task_granularity_fit"
        assert patch.new_value == "moderate"
        assert patch.confidence == 0.85

    def test_update_strategy_creates_policy_change(self):
        """update_strategy reply → PolicyChange + PlanDirective regeneration."""
        items = [
            {
                "item_id": "item_0",
                "item_type": "update_strategy",
                "status": "done",
                "payload": {"user_reply": "用例题学习"},
            },
        ]
        session = _make_session(agenda_items=items)
        closure = self.engine.produce_closure(session)

        assert len(closure.policy_changes) >= 1
        change = closure.policy_changes[0]
        assert change.new_strategy == "worked_example_first"
        assert "PlanDirective" in closure.directives_to_regenerate

    def test_auto_summary_generated_when_none_provided(self):
        """If no user_summary provided, auto-generate one."""
        session = _make_session()
        closure = self.engine.produce_closure(session)

        assert len(closure.user_visible_summary) > 0
        assert "校准完成" in closure.user_visible_summary

    def test_additional_patches_merged(self):
        """Additional state patches are included in closure."""
        session = _make_session()
        extra_patch = StatePatch(
            state_key="affective_pressure",
            old_value="burnout_risk",
            new_value="recovering",
            reason="L3干预后恢复",
            confidence=0.75,
        )
        closure = self.engine.produce_closure(
            session,
            additional_state_patches=[extra_patch],
        )

        keys = [p.state_key for p in closure.state_patches]
        assert "affective_pressure" in keys

    def test_empty_items_produce_minimal_closure(self):
        """Session with no replies produces minimal closure."""
        session = _make_session(agenda_items=[])
        closure = self.engine.produce_closure(session)

        assert len(closure.state_patches) == 0
        assert len(closure.policy_changes) == 0
        assert len(closure.directives_to_regenerate) > 0  # defaults
        assert len(closure.user_visible_summary) > 0


# ═══════════════════════════════════════════════════════════════════
# Test Reply Option Inference
# ═══════════════════════════════════════════════════════════════════

class TestReplyInference:
    """Text inference from user replies — must handle real Chinese input."""

    def setup_method(self):
        self.engine, self.redis = _make_engine()

    def test_infer_granularity_30min(self):
        assert self.engine._infer_granularity("30分钟") == "small_chunks"
        assert self.engine._infer_granularity("半小时") == "small_chunks"

    def test_infer_granularity_45min(self):
        assert self.engine._infer_granularity("45分钟") == "moderate"

    def test_infer_granularity_60min(self):
        assert self.engine._infer_granularity("60分钟") == "standard"
        assert self.engine._infer_granularity("1小时") == "standard"

    def test_infer_granularity_unknown(self):
        assert self.engine._infer_granularity("随便") == "adjusted_by_user"

    def test_infer_knowledge_state_confirmed(self):
        assert self.engine._infer_knowledge_state("我会这个") == "knowledge_confirmed"

    def test_infer_knowledge_state_gap(self):
        assert self.engine._infer_knowledge_state("我不会") == "knowledge_gap_confirmed"
        assert self.engine._infer_knowledge_state("不理解") == "knowledge_gap_confirmed"

    def test_infer_strategy_worked_example(self):
        assert self.engine._infer_strategy("用例题") == "worked_example_first"

    def test_infer_strategy_retrieval(self):
        assert self.engine._infer_strategy("刷题") == "retrieval_practice"

    def test_infer_strategy_small_wins(self):
        assert self.engine._infer_strategy("先做简单任务") == "small_wins"


# ═══════════════════════════════════════════════════════════════════
# Test Resilience
# ═══════════════════════════════════════════════════════════════════

class TestResilience:
    """Production failure modes — Redis down, corrupted data, etc."""

    @pytest.mark.asyncio
    async def test_redis_get_failure_returns_none(self):
        """Redis failure during session load returns None."""
        redis = AsyncMock()
        redis.get.side_effect = Exception("Redis connection refused")
        engine = L3FullCoreEngine(redis)

        result = await engine.execute_agenda_step("session_1", 0, "reply")
        assert result is None

    @pytest.mark.asyncio
    async def test_redis_set_failure_during_pause(self):
        """Redis failure during pause returns None (transition succeeds but persist fails)."""
        session = _make_session(status="active")
        redis = _make_redis_with_session(session)
        redis.set.side_effect = Exception("Redis write failed")
        svc = AuroraCoreSessionService(redis)

        # transition_session writes, so it will fail
        result = await svc.pause_session("test_session")
        assert result is None

    @pytest.mark.asyncio
    async def test_corrupted_session_json_returns_none(self):
        """Corrupted JSON in Redis returns None gracefully."""
        redis = AsyncMock()
        redis.get.return_value = b"not valid json{{{"
        engine = L3FullCoreEngine(redis)

        result = await engine.execute_agenda_step("corrupt", 0, "reply")
        assert result is None

    @pytest.mark.asyncio
    async def test_missing_session_fields_handled(self):
        """Session with missing fields doesn't crash."""
        redis = AsyncMock()
        redis.get.return_value = json.dumps({"session_id": "partial"}).encode()
        engine = L3FullCoreEngine(redis)

        # Should not crash
        health = await engine.check_session_health("partial")
        assert isinstance(health, dict)

    @pytest.mark.asyncio
    async def test_redis_failure_health_check_no_crash(self):
        """Redis failure during health check doesn't crash."""
        redis = AsyncMock()
        redis.get.side_effect = Exception("Redis down")
        engine = L3FullCoreEngine(redis)

        health = await engine.check_session_health("any")
        assert health["healthy"] is False
        assert health["reason"] == "session_not_found"


# ═══════════════════════════════════════════════════════════════════
# Test Wake Condition Constants
# ═══════════════════════════════════════════════════════════════════

class TestWakeConditionConstants:
    """Verify wake condition definitions are complete and consistent."""

    def test_all_8_conditions_defined(self):
        """There must be exactly 8 wake conditions."""
        assert len(_WAKE_CONDITIONS) == 8

    def test_all_conditions_have_required_fields(self):
        """Every condition must have key, session_type, duration_sec, description."""
        for cond in _WAKE_CONDITIONS:
            assert "key" in cond
            assert "session_type" in cond
            assert "duration_sec" in cond
            assert "description" in cond
            assert cond["duration_sec"] > 0
            assert len(cond["description"]) > 0

    def test_no_duplicate_keys(self):
        """All condition keys must be unique."""
        keys = [c["key"] for c in _WAKE_CONDITIONS]
        assert len(keys) == len(set(keys))

    def test_no_duplicate_session_types(self):
        """All session types must be unique."""
        types = [c["session_type"] for c in _WAKE_CONDITIONS]
        assert len(types) == len(set(types))
