from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.card_protocol import DeliveryChannel, DeliveryStrategy, InterventionOutcomeStatus, InterventionTriggerType
from app.services.card_protocol.outcome_verifier import InterventionOutcomeVerifier
from app.services.intervention_record_service import InterventionRecordService


@pytest.mark.asyncio
async def test_strategy_context_snapshot_flattens_persisted_cohort_profile(db_session, test_user):
    record = await InterventionRecordService(db_session).create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        trigger_source_ref=f"test:{uuid4()}",
        diagnosis_payload={
            "context": {"completed_count": 2},
            "cohort_profile": {
                "goal_type": "exam",
                "knowledge_level": "intermediate",
                "learning_style": "balanced",
            },
        },
        outcome_window_days=1,
    )

    snapshot = InterventionOutcomeVerifier._strategy_context_snapshot(
        record,
        {
            "evaluation_method": "test",
            "improvement": {"plan_health_recovered": True},
        },
    )

    assert snapshot["completed_count"] == 2
    assert snapshot["goal_type"] == "exam"
    assert snapshot["knowledge_level"] == "intermediate"
    assert snapshot["learning_style"] == "balanced"
