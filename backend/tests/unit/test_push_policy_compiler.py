from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.user_push_opt_in import UserPushOptIn
from app.services.push_policy_compiler import PushPolicyCompiler
from app.state_aggregator.schema import (
    CommitmentSummaryValue,
    EngagementStateValue,
    StateFieldEnvelope,
    UserStateV1,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _build_opt_in(**overrides) -> UserPushOptIn:
    payload = {
        "user_id": uuid4(),
        "enabled": True,
        "allow_commitment_follow_up": True,
        "allow_engagement_recovery": True,
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "08:00",
        "timezone": "Asia/Shanghai",
    }
    payload.update(overrides)
    return UserPushOptIn(**payload)


def _commitment_state(now: datetime) -> UserStateV1:
    return UserStateV1(
        user_id=uuid4(),
        commitment_summary=StateFieldEnvelope(
            value=CommitmentSummaryValue(
                overdue_count=1,
                next_due_at=now - timedelta(days=1),
                pending_commitment_ids=("commitment-1",),
            ),
            computed_at=now,
            source_snapshot_ids=("episodic:1",),
            freshness_seconds=0,
        ),
    )


def _engagement_state(now: datetime) -> UserStateV1:
    return UserStateV1(
        user_id=uuid4(),
        engagement_state=StateFieldEnvelope(
            value=EngagementStateValue(
                last_active_at=now - timedelta(hours=80),
                session_count_7d=4,
                streak=5,
            ),
            computed_at=now,
            source_snapshot_ids=("focus:1", "streak:1"),
            freshness_seconds=0,
        ),
    )


def test_push_policy_compiler_returns_none_when_opted_out() -> None:
    compiler = PushPolicyCompiler()
    now = _utcnow()

    decision = compiler.compile(
        user_state=_commitment_state(now),
        push_opt_in=_build_opt_in(enabled=False),
        recent_delivery_count_24h=0,
        dismissed_categories_7d=set(),
        now=now,
    )

    assert decision is None


def test_push_policy_compiler_builds_commitment_follow_up_decision() -> None:
    compiler = PushPolicyCompiler()
    now = _utcnow().replace(hour=10, minute=0, second=0, microsecond=0)

    decision = compiler.compile(
        user_state=_commitment_state(now),
        push_opt_in=_build_opt_in(),
        recent_delivery_count_24h=0,
        dismissed_categories_7d=set(),
        now=now,
    )

    assert decision is not None
    assert decision.policy_id == "CommitmentFollowUp"
    assert decision.category == "commitment_follow_up"
    assert decision.evidence_token == "commitment:commitment-1"
    assert decision.scheduled_send_at == now
    assert decision.metadata["proactive_reason"]
    assert decision.metadata["destination_route"].startswith("/chat?")
    assert decision.metadata["intrusiveness_level"] == "standard"


def test_push_policy_compiler_applies_daily_cap() -> None:
    compiler = PushPolicyCompiler()
    now = _utcnow()

    decision = compiler.compile(
        user_state=_commitment_state(now),
        push_opt_in=_build_opt_in(),
        recent_delivery_count_24h=2,
        dismissed_categories_7d=set(),
        now=now,
    )

    assert decision is None


def test_push_policy_compiler_reduces_after_one_dismissal_and_suppresses_after_repeated_dismissals() -> None:
    compiler = PushPolicyCompiler()
    now = _utcnow()

    reduced = compiler.compile(
        user_state=_commitment_state(now),
        push_opt_in=_build_opt_in(),
        recent_delivery_count_24h=0,
        dismissed_categories_7d={"commitment_follow_up"},
        category_dismissal_counts_7d={"commitment_follow_up": 1},
        now=now,
    )

    assert reduced is not None
    assert reduced.metadata["intrusiveness_level"] == "reduced"
    assert reduced.metadata["respectfulness_reason"] == "recent_dismissal"

    suppressed = compiler.compile(
        user_state=_commitment_state(now),
        push_opt_in=_build_opt_in(),
        recent_delivery_count_24h=0,
        dismissed_categories_7d={"commitment_follow_up"},
        category_dismissal_counts_7d={"commitment_follow_up": 2},
        now=now,
    )

    assert suppressed is None


def test_push_policy_compiler_carries_multi_device_context() -> None:
    compiler = PushPolicyCompiler()
    now = _utcnow().replace(hour=11, minute=30, second=0, microsecond=0)

    decision = compiler.compile(
        user_state=_engagement_state(now),
        push_opt_in=_build_opt_in(allow_commitment_follow_up=False),
        recent_delivery_count_24h=0,
        dismissed_categories_7d=set(),
        category_dismissal_counts_7d={},
        device_context={
            "active_device_count": 2,
            "platforms": ["android", "ios"],
            "last_active_device_id": "phone-1",
            "last_active_at": now.isoformat(),
        },
        now=now,
    )

    assert decision is not None
    assert decision.metadata["target_device_count"] == 2
    assert decision.metadata["target_platforms"] == ["android", "ios"]
    assert decision.metadata["last_active_device_id"] == "phone-1"
    assert decision.metadata["cross_device_state_key"] == "aurora_push:engagement_recovery"


def test_push_policy_compiler_builds_engagement_recovery_when_no_commitment_trigger() -> None:
    compiler = PushPolicyCompiler()
    now = _utcnow().replace(hour=11, minute=30, second=0, microsecond=0)

    decision = compiler.compile(
        user_state=_engagement_state(now),
        push_opt_in=_build_opt_in(allow_commitment_follow_up=False),
        recent_delivery_count_24h=0,
        dismissed_categories_7d=set(),
        now=now,
    )

    assert decision is not None
    assert decision.policy_id == "EngagementRecovery"
    assert decision.category == "engagement_recovery"
    assert decision.message_template_id == "engagement_recovery_soft"


def test_push_policy_compiler_delays_into_quiet_hour_exit() -> None:
    compiler = PushPolicyCompiler()
    now = _utcnow().replace(hour=22, minute=15, second=0, microsecond=0)

    decision = compiler.compile(
        user_state=_commitment_state(now),
        push_opt_in=_build_opt_in(),
        recent_delivery_count_24h=0,
        dismissed_categories_7d=set(),
        now=now,
    )

    assert decision is not None
    assert decision.scheduled_send_at.hour == 8
    assert decision.scheduled_send_at.minute == 0
