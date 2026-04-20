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


def test_push_policy_compiler_respects_dismissed_categories() -> None:
    compiler = PushPolicyCompiler()
    now = _utcnow()

    decision = compiler.compile(
        user_state=_commitment_state(now),
        push_opt_in=_build_opt_in(),
        recent_delivery_count_24h=0,
        dismissed_categories_7d={"commitment_follow_up"},
        now=now,
    )

    assert decision is None


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
