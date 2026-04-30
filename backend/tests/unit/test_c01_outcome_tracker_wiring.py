"""
Tests for C-01-FIX: OutcomeTracker wired to production code paths.
Verifies register_expected, record_actual, and verify_pending integration.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# --- Test 1: SpineOrchestrator calls register_expected after directive ---

@pytest.mark.asyncio
async def test_spine_orchestrator_registers_expected_outcome():
    """Verify SpineOrchestrator.on_task_completed calls OutcomeTracker.register_expected."""
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.types import ActionableSignal, CausalTrace, ExecutionDirective, PolicyDecision

    signal = ActionableSignal(
        signal_id="sig1",
        source_event_ids=["e1"],
        source_system="timeout_detector",
        state_key="timeout:u1",
        claim="task_timeout",
        confidence=0.8,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="Task took 3x estimated time",
        possible_effects=["adjust_task_size"],
        priority="medium",
    )
    trace = CausalTrace(trace_id="t1", raw_event_ids=[], signal_ids=[], directive_ids=[])

    mock_tracker = AsyncMock()
    mock_redis = AsyncMock()

    spine = SpineOrchestrator.__new__(SpineOrchestrator)
    spine.redis = mock_redis
    spine.outcome_tracker = mock_tracker
    spine.trace_store = AsyncMock()
    spine.timeout_detector = AsyncMock()
    spine.state_register = AsyncMock()
    spine.outcome_recorder = AsyncMock()
    spine.metrics = AsyncMock()
    spine.policy_engine = AsyncMock()
    spine.directive_quota = AsyncMock()
    spine.self_model = AsyncMock()
    spine.relationship_model = AsyncMock()
    spine.exam_sprint_policy = AsyncMock()
    spine.skill_lifecycle_manager = AsyncMock()
    spine.core_session_manager = AsyncMock()
    spine._safety_degradation = AsyncMock()
    from app.signals.safety_degradation import SafetyDegradationLevel
    spine._safety_degradation.get_current_level = AsyncMock(return_value=SafetyDegradationLevel.NORMAL)
    spine._safety_degradation.get_restricted_capabilities = AsyncMock(return_value=[])
    spine._high_impact_confirmation = AsyncMock()
    spine._high_impact_confirmation.is_high_impact = MagicMock(return_value=False)
    spine._research_isolation = AsyncMock()
    spine._research_isolation.is_research_allowed = MagicMock(return_value=True)

    spine.trace_store.create_trace = AsyncMock(return_value=trace)
    spine.trace_store._save_trace = AsyncMock()
    spine.trace_store.link_to_user = AsyncMock()
    spine.trace_store.append_policy = AsyncMock()
    spine.trace_store.append_directive = AsyncMock()
    spine.trace_store.append_signal = AsyncMock()
    spine.trace_store.store_signal = AsyncMock()
    spine.trace_store.set_active_directive = AsyncMock()

    spine.timeout_detector.on_task_completed = AsyncMock(return_value=signal)
    spine.timeout_detector._get_consecutive_timeouts = AsyncMock(return_value=0)
    spine.outcome_recorder.get_recent_policy_effects = AsyncMock(return_value=[])

    decision = PolicyDecision(
        policy_decision_id="pd1",
        primary_strategy="timeout_warning",
        secondary_strategy=None,
        hard_constraints={},
        soft_biases={},
        visibility="silent",
        requires_user_confirmation=False,
        reasoning_summary="test",
        risk_level="medium",
        which_directives={"execution": True},
    )
    directive = ExecutionDirective(
        directive_id="d1",
        policy_decision_id="pd1",
        target_module="task_generator",
        scope="today",
        hard_constraints={},
        user_visible_reason="Test reason",
    )
    spine.policy_engine.evaluate = AsyncMock(return_value=(decision, directive))
    spine.policy_engine.build_response_directive = MagicMock(return_value=None)
    spine.policy_engine.build_retrieval_directive = MagicMock(return_value=None)
    spine.policy_engine.build_plan_directive = MagicMock(return_value=None)
    spine.policy_engine.build_model_write_directive = MagicMock(return_value=None)
    spine.policy_engine.build_ux_directive = MagicMock(return_value=None)
    spine.policy_engine.build_community_directive = MagicMock(return_value=None)
    spine.policy_engine.build_skill_directive = MagicMock(return_value=None)
    spine.policy_engine.build_notification_directive = MagicMock(return_value=None)

    spine._store_response_directive = AsyncMock()
    spine._store_notification_directive = AsyncMock()
    spine._store_retrieval_directive = AsyncMock()
    spine._store_plan_directive = AsyncMock()
    spine._store_model_write_directive = AsyncMock()
    spine._store_ux_directive = AsyncMock()
    spine._store_community_directive = AsyncMock()
    spine._store_skill_directive = AsyncMock()
    spine._apply_exam_sprint_overlay = AsyncMock(return_value=directive)
    spine._link_directive_to_active_session = AsyncMock()
    spine.check_aurora_wake = MagicMock(return_value=MagicMock(can_wake=False))

    await spine.on_task_completed(
        user_id="u1", task_id="task1",
        estimated_minutes=30, actual_minutes=90,
    )

    mock_tracker.register_expected.assert_called_once()
    call_kwargs = mock_tracker.register_expected.call_args[1]
    assert call_kwargs["user_id"] == "u1"
    assert call_kwargs["trace"] is trace
    assert call_kwargs["verification_window_hours"] == 48
    assert call_kwargs["context"]["signal_claim"] == "task_timeout"
    assert call_kwargs["context"]["task_id"] == "task1"


# --- Test 2: _record_task_outcome resolves pending outcome ---

@pytest.mark.asyncio
async def test_record_task_outcome_resolves_pending():
    """Verify _record_task_outcome finds pending outcome and calls record_actual."""
    from app.services.task_event_consumer import TaskEventConsumer

    store = {
        "spine:pending_outcomes:po123": json.dumps({
            "outcome_id": "po123",
            "user_id": "u1",
            "directive_type": "timeout_warning",
            "trace_id": "t1",
            "expected_outcome": "task_started_and_completed",
            "context": {},
            "registered_at": "2026-01-01T00:00:00",
            "verification_window_hours": 48,
            "resolved": False,
        }),
    }

    class FakeRedis:
        async def get(self, key):
            return store.get(key)

        async def set(self, key, value, ex=None):
            store[key] = value

        async def lrange(self, key, start, stop):
            return [b"po123"]

    consumer = TaskEventConsumer(event_bus=AsyncMock())

    with patch("app.services.task_event_consumer.cache_service") as mock_cache:
        mock_cache.redis = FakeRedis()
        from app.signals.outcome_tracker import OutcomeTracker
        mock_record = AsyncMock(return_value=None)
        with patch.object(OutcomeTracker, "record_actual", mock_record):
            await consumer._record_task_outcome(
                user_id="u1",
                task_id="task-old",
                plan_id="plan1",
                completed=True,
                actual_minutes=25, estimated_minutes=30,
                completion_rate=0.83,
            )

            assert mock_record.called
            actual = mock_record.call_args[1]["actual_outcome"]
            assert actual["completed"] is True
            assert actual["completion_rate"] == 0.83


# --- Test 3: _record_task_outcome handles abandoned tasks ---

@pytest.mark.asyncio
async def test_record_task_outcome_abandoned():
    """Verify _record_task_outcome records abandoned = not completed."""
    from app.services.task_event_consumer import TaskEventConsumer

    store = {
        "spine:pending_outcomes:po456": json.dumps({
            "outcome_id": "po456",
            "user_id": "u2",
            "directive_type": "timeout_warning",
            "trace_id": "t2",
            "expected_outcome": "behavioral_change",
            "context": {},
            "registered_at": "2026-01-01T00:00:00",
            "verification_window_hours": 48,
            "resolved": False,
        }),
    }

    class FakeRedis:
        async def get(self, key):
            return store.get(key)

        async def set(self, key, value, ex=None):
            store[key] = value

        async def lrange(self, key, start, stop):
            return [b"po456"]

    consumer = TaskEventConsumer(event_bus=AsyncMock())

    with patch("app.services.task_event_consumer.cache_service") as mock_cache:
        mock_cache.redis = FakeRedis()
        from app.signals.outcome_tracker import OutcomeTracker
        mock_ra = AsyncMock(return_value=None)
        with patch.object(OutcomeTracker, "record_actual", mock_ra):
            await consumer._record_task_outcome(
                user_id="u2",
                task_id="task-old",
                plan_id=None,
                completed=False,
                actual_minutes=5, estimated_minutes=30,
                completion_rate=0.0,
            )

            actual = mock_ra.call_args[1]["actual_outcome"]
            assert actual["completed"] is False
            assert actual["user_responded"] is False
            assert actual["behavior_changed"] is False


# --- Test 4: SchedulerService has outcome verification job ---

def test_scheduler_registers_outcome_verification():
    """Verify SchedulerService.start() registers run_outcome_verification."""
    from app.services.scheduler_service import SchedulerService

    # Verify the method exists and is a coroutine
    svc = SchedulerService()
    assert hasattr(svc, "run_outcome_verification")
    assert callable(svc.run_outcome_verification)

    # Verify it's referenced in the start method's source
    import inspect
    source = inspect.getsource(svc.start)
    assert "run_outcome_verification" in source
    assert "hours=6" in source
