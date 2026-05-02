from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.models.user import User, UserDevice
from app.models.user_push_opt_in import UserPushOptIn
from app.services.push_policy_compiler import PushDecision
from app.services.state_driven_push_service import StateDrivenPushService
from app.state_aggregator.schema import CommitmentSummaryValue, StateFieldEnvelope, UserStateV1


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_state_driven_push_service_preview_returns_none_when_aggregator_disabled(db_session) -> None:
    service = StateDrivenPushService(db_session)
    service.kill_switches.is_enabled = AsyncMock(side_effect=[False])

    decision = await service.preview_decision(uuid4(), now=_utcnow())

    assert decision is None


@pytest.mark.asyncio
async def test_state_driven_push_service_compile_and_deliver_happy_path(db_session) -> None:
    service = StateDrivenPushService(db_session)
    user_id = uuid4()
    now = _utcnow()

    service.kill_switches.is_enabled = AsyncMock(side_effect=[True, True, True])
    service.aggregator.get_user_state = AsyncMock(
        return_value=UserStateV1(
            user_id=user_id,
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
    )
    service.opt_in_service.get_or_create = AsyncMock(
        return_value=UserPushOptIn(
            user_id=user_id,
            enabled=True,
            allow_commitment_follow_up=True,
            allow_engagement_recovery=False,
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
            timezone="Asia/Shanghai",
        )
    )
    service.delivery_service.recent_delivery_count_24h = AsyncMock(return_value=0)
    service.delivery_service.category_dismissal_counts_7d = AsyncMock(return_value={})
    expected = PushDecision(
        policy_id="CommitmentFollowUp",
        category="commitment_follow_up",
        evidence_token="commitment:commitment-1",
        message_template_id="commitment_follow_up_gentle",
        scheduled_send_at=now,
        title="主动提醒",
        body="body",
        metadata={},
    )
    service.compiler.compile = Mock(return_value=expected)
    service.delivery_service.deliver_decision = AsyncMock(return_value="delivered")

    result = await service.compile_and_deliver(user_id, now=now)

    assert result == "delivered"
    service.delivery_service.deliver_decision.assert_awaited_once_with(user_id=user_id, decision=expected)


@pytest.mark.asyncio
async def test_state_driven_push_service_passes_dismissal_and_device_context(db_session) -> None:
    service = StateDrivenPushService(db_session)
    user_id = uuid4()
    now = _utcnow()
    user = User(
        id=user_id,
        username="proactive_multi_device_user",
        email="proactive-multi-device@example.com",
        hashed_password="test",
    )
    db_session.add_all(
        [
            user,
            UserDevice(
                user_id=user_id,
                device_id="phone-1",
                push_token="token-phone",
                platform="ios",
                token_type="fcm",
                device_name="Phone",
                is_active=True,
                last_used_at=now,
            ),
            UserDevice(
                user_id=user_id,
                device_id="tablet-1",
                push_token="token-tablet",
                platform="android",
                token_type="fcm",
                device_name="Tablet",
                is_active=True,
                last_used_at=now - timedelta(minutes=20),
            ),
        ]
    )
    await db_session.commit()

    service.kill_switches.is_enabled = AsyncMock(side_effect=[True, True])
    service.aggregator.get_user_state = AsyncMock(
        return_value=UserStateV1(
            user_id=user_id,
            commitment_summary=StateFieldEnvelope(
                value=CommitmentSummaryValue(
                    overdue_count=1,
                    next_due_at=now - timedelta(hours=1),
                    pending_commitment_ids=("commitment-1",),
                ),
                computed_at=now,
                source_snapshot_ids=("episodic:1",),
                freshness_seconds=0,
            ),
        )
    )
    service.opt_in_service.get_or_create = AsyncMock(
        return_value=UserPushOptIn(
            user_id=user_id,
            enabled=True,
            allow_commitment_follow_up=True,
            allow_engagement_recovery=True,
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
            timezone="Asia/Shanghai",
        )
    )
    service.delivery_service.recent_delivery_count_24h = AsyncMock(return_value=0)
    service.delivery_service.category_dismissal_counts_7d = AsyncMock(return_value={"commitment_follow_up": 1})

    decision = await service.preview_decision(user_id, now=now)

    assert decision is not None
    assert decision.category == "commitment_follow_up"
    assert decision.metadata["intrusiveness_level"] == "reduced"
    assert decision.metadata["target_device_count"] == 2
    assert decision.metadata["target_platforms"] == ["android", "ios"]
    assert decision.metadata["last_active_device_id"] == "phone-1"
    assert decision.metadata["proactive_reason"]
