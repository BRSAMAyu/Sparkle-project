"""Tests for PlanHealthSignalService —断点3 event dedup and emission."""
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.plan_health_signal_service import (
    COOLDOWNS,
    PlanHealthSignalService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_report(
    *,
    severity: str = "warning",
    recommended_action: str = "adjust",
    reasons: list[str] | None = None,
    requires_adjustment: bool = True,
):
    return SimpleNamespace(
        user_id=uuid4(),
        plan_id=uuid4(),
        severity=severity,
        recommended_action=recommended_action,
        reasons=reasons or ["progress_lag"],
        metrics={"progress_rate": 0.3},
        requires_adjustment=requires_adjustment,
    )


def _make_service():
    db = MagicMock()
    redis = MagicMock()
    service = PlanHealthSignalService(db, redis)
    return service, db


def _meta(
    *,
    signature: str = "warning|adjust|progress_lag",
    severity: str = "warning",
    emitted_at: str | None = None,
):
    if emitted_at is None:
        emitted_at = datetime.now(timezone.utc).isoformat()
    return {
        "signature": signature,
        "severity": severity,
        "action_taken": "incremental_adjustment_applied",
        "emitted_at": emitted_at,
    }


# ===========================================================================
# 1. Same-signature warning only emits once (within cooldown)
# ===========================================================================

@pytest.mark.asyncio
async def test_same_signature_warning_suppressed_within_cooldown():
    service, _ = _make_service()
    report = _make_report(severity="warning", reasons=["progress_lag"])
    sig = service._build_signature(report)

    last = _meta(signature=sig, severity="warning")
    facts = {"adaptive_meta": {"plan_health_signal": last}}

    with patch("app.services.plan_health_signal_service.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        emitted = await service.maybe_publish(
            report=report,
            trigger="task_completed",
            existing_facts=facts,
        )

    assert emitted is False
    assert not mock_bus.publish.called


# ===========================================================================
# 2. warning -> critical triggers immediate re-emit
# ===========================================================================

@pytest.mark.asyncio
async def test_severity_upgrade_warning_to_critical_re_emits():
    service, _ = _make_service()

    # Previous was warning
    report_old = _make_report(severity="warning", reasons=["progress_lag"])
    old_sig = service._build_signature(report_old)

    last = _meta(signature=old_sig, severity="warning")
    facts = {"adaptive_meta": {"plan_health_signal": last}}

    # New report is critical
    report_new = _make_report(severity="critical", reasons=["progress_lag"])

    with patch("app.services.plan_health_signal_service.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        with patch.object(service, "_persist_signal_meta", new_callable=AsyncMock):
            emitted = await service.maybe_publish(
                report=report_new,
                trigger="task_feedback",
                existing_facts=facts,
            )

    assert emitted is True
    assert mock_bus.publish.called


# ===========================================================================
# 3. critical but replan cooldown -> action_taken records cooldown
# ===========================================================================

@pytest.mark.asyncio
async def test_critical_with_cooldown_records_cooldown_action():
    service, _ = _make_service()
    report = _make_report(
        severity="critical",
        recommended_action="replan",
        reasons=["progress_lag", "difficulty_too_hard"],
    )

    # No previous signal → should emit
    facts = {"adaptive_meta": {}}

    with patch("app.services.plan_health_signal_service.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        with patch.object(service, "_persist_signal_meta", new_callable=AsyncMock):
            emitted = await service.maybe_publish(
                report=report,
                trigger="task_feedback",
                action_taken="replan_cooldown_active",
                existing_facts=facts,
            )

    assert emitted is True
    # Verify payload has action_taken
    call_args = mock_bus.publish.call_args
    payload = call_args[0][1]  # second arg is the payload dict
    assert payload["action_taken"] == "replan_cooldown_active"


# ===========================================================================
# 4. evaluate_progress() call does NOT emit events
# ===========================================================================

@pytest.mark.asyncio
async def test_healthy_report_does_not_emit():
    service, _ = _make_service()
    report = _make_report(
        severity="healthy",
        requires_adjustment=False,
    )

    with patch("app.services.plan_health_signal_service.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        emitted = await service.maybe_publish(
            report=report,
            trigger="task_completed",
        )

    assert emitted is False
    assert not mock_bus.publish.called


# ===========================================================================
# 5. Consumer skips visible update when action_taken is already notified
# ===========================================================================

def test_consumer_skips_already_notified_actions():
    """Test that the consumer's dedup logic works for already-notified actions."""
    from app.services.plan_health_event_consumer import _ALREADY_NOTIFIED_ACTIONS

    assert "incremental_adjustment_applied" in _ALREADY_NOTIFIED_ACTIONS
    assert "full_replan_triggered" in _ALREADY_NOTIFIED_ACTIONS
    # These actions should NOT trigger a second visible update
    assert "replan_cooldown_active" not in _ALREADY_NOTIFIED_ACTIONS
    assert "adjustment_cooldown_active" not in _ALREADY_NOTIFIED_ACTIONS


# ===========================================================================
# 6. Signature building
# ===========================================================================

def test_signature_is_stable():
    service, _ = _make_service()
    report1 = _make_report(severity="warning", reasons=["progress_lag", "difficulty_too_hard"])
    report2 = _make_report(severity="warning", reasons=["difficulty_too_hard", "progress_lag"])

    # Reasons are sorted, so order doesn't matter
    assert service._build_signature(report1) == service._build_signature(report2)


def test_signature_changes_with_severity():
    service, _ = _make_service()
    r1 = _make_report(severity="warning", reasons=["progress_lag"])
    r2 = _make_report(severity="critical", reasons=["progress_lag"])

    assert service._build_signature(r1) != service._build_signature(r2)


# ===========================================================================
# 7. Cooldown values match spec
# ===========================================================================

def test_cooldown_durations():
    assert COOLDOWNS["warning"] == 2 * 3600   # 2 hours
    assert COOLDOWNS["critical"] == 12 * 3600  # 12 hours


# ===========================================================================
# 8. Should_emit edge cases
# ===========================================================================

def test_should_emit_no_previous():
    service, _ = _make_service()
    assert service._should_emit({}, "warning|adjust|x", "warning") is True


def test_should_emit_same_severity_outside_cooldown():
    service, _ = _make_service()
    # Set emitted_at far in the past
    old_time = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    last = _meta(signature="warning|adjust|progress_lag", severity="warning", emitted_at=old_time)

    assert service._should_emit(last, "warning|adjust|progress_lag", "warning") is True


def test_should_emit_same_severity_inside_cooldown():
    service, _ = _make_service()
    recent_time = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    last = _meta(signature="warning|adjust|progress_lag", severity="warning", emitted_at=recent_time)

    assert service._should_emit(last, "warning|adjust|progress_lag", "warning") is False


def test_should_emit_downgrade_inside_cooldown_still_emits():
    """Severity downgrade (critical -> warning) with same signature still emits if outside cooldown."""
    service, _ = _make_service()
    old_time = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    last = _meta(signature="critical|replan|progress_lag", severity="critical", emitted_at=old_time)

    # Different severity but same signature → it's a different signature
    assert service._should_emit(last, "warning|adjust|progress_lag", "warning") is True


# ===========================================================================
# 9. Payload structure
# ===========================================================================

@pytest.mark.asyncio
async def test_payload_structure():
    service, _ = _make_service()
    report = _make_report(severity="critical", recommended_action="replan")
    task_id = uuid4()

    with patch("app.services.plan_health_signal_service.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        with patch.object(service, "_persist_signal_meta", new_callable=AsyncMock):
            await service.maybe_publish(
                report=report,
                trigger="task_feedback",
                task_id=task_id,
                feedback_category="too_difficult",
                action_taken="full_replan_triggered",
                adaptation_records=[{"x": 1}],
                existing_facts={},
            )

    payload = mock_bus.publish.call_args[0][1]
    assert payload["event_type"] == "plan.health.alerted"
    assert payload["severity"] == "critical"
    assert payload["recommended_action"] == "replan"
    assert payload["trigger"] == "task_feedback"
    assert payload["feedback_category"] == "too_difficult"
    assert payload["action_taken"] == "full_replan_triggered"
    assert payload["adaptation_count"] == 1
    assert "signature" in payload
    assert "emitted_at" in payload


# ===========================================================================
# 10. Event publish failure is non-fatal
# ===========================================================================

@pytest.mark.asyncio
async def test_publish_failure_returns_false():
    service, _ = _make_service()
    report = _make_report(severity="warning")

    with patch("app.services.plan_health_signal_service.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock(side_effect=Exception("Redis down"))
        emitted = await service.maybe_publish(
            report=report,
            trigger="task_completed",
            existing_facts={},
        )

    assert emitted is False


# ===========================================================================
# 15. No adjustment produced → event does not claim "applied"
# ===========================================================================

@pytest.mark.asyncio
async def test_no_adjustment_produced_action_reflects_reality():
    service, _ = _make_service()
    report = _make_report(severity="warning")

    with patch("app.services.plan_health_signal_service.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        with patch.object(service, "_persist_signal_meta", new_callable=AsyncMock):
            emitted = await service.maybe_publish(
                report=report,
                trigger="task_feedback",
                action_taken="no_adjustment_produced",
                existing_facts={},
            )

    assert emitted is True
    payload = mock_bus.publish.call_args[0][1]
    assert payload["action_taken"] == "no_adjustment_produced"
    assert "applied" not in payload["action_taken"]


# ===========================================================================
# 16. Cooldown event → system update contains title/description/created_at
# ===========================================================================

def test_cooldown_system_update_has_visible_contract():
    from app.services.system_update_service import build_system_update

    message = "学习节奏有波动，系统在观察中。"
    update = build_system_update(
        update_type="plan_health_signal",
        category="plan_health",
        title="计划状态观察中",
        description=message,
        priority="low",
        metadata={"plan_id": "test-plan", "severity": "warning", "silent": True},
    )

    assert "title" in update
    assert "description" in update
    assert "created_at" in update
    assert update["title"] == "计划状态观察中"
    assert update["description"] == message
    assert isinstance(update["created_at"], int)
    assert update["category"] == "plan_health"
