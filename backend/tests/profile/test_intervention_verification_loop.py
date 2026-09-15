from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.card_protocol import (
    CardLifecycleStatus,
    CardType,
    DeliveryChannel,
    DeliveryStrategy,
    InterventionOutcomeStatus,
    InterventionTriggerType,
)
from app.services.card_protocol.outcome_verifier import InterventionOutcomeVerifier
from app.services.card_service import CardService
from app.services.intervention_record_service import InterventionRecordService
from app.services.plan_state_service import PlanStateService


class FakeEventBus:
    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        del event_type, payload, stream
        return "event-id"


@pytest.mark.asyncio
async def test_intervention_verification_loop_records_effective_verdict_payload(db_session, test_user):
    card_service = CardService(db_session)
    legacy_plan_id = uuid4()
    plan_card = await card_service.create_card(
        card_type=CardType.PLAN,
        owner_id=test_user.id,
        holder_id=test_user.id,
        metadata={"name": "Verification Demo Plan", "legacy_plan_id": str(legacy_plan_id)},
        lifecycle_status=CardLifecycleStatus.ACTIVE,
    )

    state = await PlanStateService(db_session, redis=None).get_or_create_plan_state(
        user_id=test_user.id,
        plan_id=legacy_plan_id,
    )
    state.feedback_log = [
        {
            "id": "fb-effective",
            "timestamp": datetime.utcnow().isoformat(),
            "type": "task_feedback",
            "content": "这个调整真的让我继续推进下去了。",
        }
    ]

    record_service = InterventionRecordService(db_session, FakeEventBus())
    record = await record_service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        plan_card_id=plan_card.id,
        diagnosis_payload={"reasons": ["progress_lag"]},
        outcome_window_days=1,
    )
    await record_service.mark_delivered(record.id)
    await record_service.mark_accepted(record.id)
    record.action_payload = {
        "parameter_compilation": {
            "applied": True,
            "result": "patched",
            "plan_id": str(legacy_plan_id),
            "affected_task_count": 1,
            "inserted_task_count": 0,
            "hidden_task_count": 0,
        }
    }
    record.created_at = datetime.utcnow() - timedelta(days=2)
    await record_service.mark_acted(record.id, action_payload={"cta": "continue"})
    await db_session.commit()

    summary = await InterventionOutcomeVerifier(db_session).verify_all_pending()
    await db_session.refresh(record)

    assert summary["effective"] == 1
    assert record.outcome_status == InterventionOutcomeStatus.EFFECTIVE
    assert record.evidence_payload["verification"]["verdict"] == "EFFECTIVE"
    assert record.evidence_payload["verification"]["resolved_via"] == "system_applied_and_measured"


@pytest.mark.asyncio
async def test_intervention_verification_loop_records_ineffective_verdict_payload(db_session, test_user):
    record_service = InterventionRecordService(db_session, FakeEventBus())
    record = await record_service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        outcome_window_days=0,
    )
    record.created_at = datetime.utcnow() - timedelta(days=2)
    await record_service.mark_delivered(record.id)
    await db_session.commit()

    summary = await InterventionOutcomeVerifier(db_session).verify_all_pending()
    await db_session.refresh(record)

    assert summary["ineffective"] == 1
    assert record.outcome_status == InterventionOutcomeStatus.INEFFECTIVE
    assert record.evidence_payload["verification"]["verdict"] == "INEFFECTIVE"
    assert record.evidence_payload["verification"]["resolved_via"] == "no_engagement"
