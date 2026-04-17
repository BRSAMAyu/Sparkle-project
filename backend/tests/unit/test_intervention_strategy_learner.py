from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.card_protocol import (
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
    InterventionTriggerType,
)
from app.services.intervention_record_service import InterventionRecordService
from app.services.intervention_strategy_learner import InterventionStrategyLearner


async def _create_record(
    db_session,
    *,
    user_id,
    trigger_type: InterventionTriggerType,
    strategy: DeliveryStrategy,
    outcome: InterventionOutcomeStatus,
    acted: bool,
    diagnosis_payload: dict | None = None,
):
    service = InterventionRecordService(db_session)
    record = await service.create_record(
        user_id=user_id,
        trigger_type=trigger_type,
        delivery_strategy=strategy,
        delivery_channel=DeliveryChannel.CHAT,
        trigger_source_ref=f"test:{trigger_type.value.lower()}",
        diagnosis_payload=diagnosis_payload or {"context": {"completed_count": 1}},
        outcome_window_days=1,
    )
    record.created_at = datetime.utcnow() - timedelta(days=2)
    if acted:
        record.acceptance_status = InterventionAcceptanceStatus.ACTED
        record.action_payload = {
            "acted_at": (record.created_at + timedelta(hours=1)).isoformat(),
        }
    else:
        record.acceptance_status = InterventionAcceptanceStatus.DISMISSED
    record.outcome_status = outcome
    await db_session.flush()
    return record


@pytest.mark.asyncio
async def test_strategy_learner_prefers_tone_with_highest_acted_rate(db_session, test_user):
    learner = InterventionStrategyLearner(db_session)

    for _ in range(5):
        record = await _create_record(
            db_session,
            user_id=test_user.id,
            trigger_type=InterventionTriggerType.STALL_PATTERN,
            strategy=DeliveryStrategy.MICRO_RESTART,
            outcome=InterventionOutcomeStatus.EFFECTIVE,
            acted=True,
        )
        await learner.record_outcome(
            user_id=test_user.id,
            intervention_id=record.id,
            outcome_status=record.outcome_status,
        )

    for _ in range(5):
        record = await _create_record(
            db_session,
            user_id=test_user.id,
            trigger_type=InterventionTriggerType.STALL_PATTERN,
            strategy=DeliveryStrategy.CURIOUS,
            outcome=InterventionOutcomeStatus.INEFFECTIVE,
            acted=False,
        )
        await learner.record_outcome(
            user_id=test_user.id,
            intervention_id=record.id,
            outcome_status=record.outcome_status,
        )

    best = await learner.get_best_strategy(test_user.id, InterventionTriggerType.STALL_PATTERN)
    profile = await learner.get_user_response_profile(test_user.id)

    assert best == DeliveryStrategy.MICRO_RESTART
    assert profile.total_samples == 10
    assert profile.preferred_strategy == DeliveryStrategy.MICRO_RESTART
    assert profile.acted_rate_by_strategy["MICRO_RESTART"] == 1.0
    assert profile.acted_rate_by_strategy["CURIOUS"] == 0.0


@pytest.mark.asyncio
async def test_strategy_learner_returns_none_without_enough_samples(db_session, test_user):
    learner = InterventionStrategyLearner(db_session)
    record = await _create_record(
        db_session,
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        strategy=DeliveryStrategy.SUPPORTIVE,
        outcome=InterventionOutcomeStatus.EFFECTIVE,
        acted=True,
    )
    await learner.record_outcome(
        user_id=test_user.id,
        intervention_id=record.id,
        outcome_status=record.outcome_status,
    )

    best = await learner.get_best_strategy(test_user.id, InterventionTriggerType.PLAN_RISK)
    assert best is None


@pytest.mark.asyncio
async def test_strategy_learner_diverges_for_different_users(db_session, test_user):
    learner = InterventionStrategyLearner(db_session)
    other_user_id = uuid4()

    from app.models.user import User

    other_user = User(
        id=other_user_id,
        username="otheruser",
        email="other@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(other_user)
    await db_session.commit()

    for _ in range(5):
        record = await _create_record(
            db_session,
            user_id=test_user.id,
            trigger_type=InterventionTriggerType.CONCEPT_GAP,
            strategy=DeliveryStrategy.SUPPORTIVE,
            outcome=InterventionOutcomeStatus.EFFECTIVE,
            acted=True,
        )
        await learner.record_outcome(
            user_id=test_user.id,
            intervention_id=record.id,
            outcome_status=record.outcome_status,
        )

    for _ in range(5):
        record = await _create_record(
            db_session,
            user_id=other_user_id,
            trigger_type=InterventionTriggerType.CONCEPT_GAP,
            strategy=DeliveryStrategy.DIRECT,
            outcome=InterventionOutcomeStatus.EFFECTIVE,
            acted=True,
        )
        await learner.record_outcome(
            user_id=other_user_id,
            intervention_id=record.id,
            outcome_status=record.outcome_status,
        )

    assert await learner.get_best_strategy(test_user.id, InterventionTriggerType.CONCEPT_GAP) == DeliveryStrategy.SUPPORTIVE
    assert await learner.get_best_strategy(other_user_id, InterventionTriggerType.CONCEPT_GAP) == DeliveryStrategy.DIRECT


@pytest.mark.asyncio
async def test_strategy_learner_uses_cohort_profile_when_personal_data_is_sparse(db_session, test_user):
    learner = InterventionStrategyLearner(db_session)
    cohort_user_id = uuid4()

    from app.models.user import User

    cohort_user = User(
        id=cohort_user_id,
        username="cohort_user",
        email="cohort@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(cohort_user)
    await db_session.commit()

    cohort_profile = {
        "goal_type": "exam",
        "knowledge_level": "intermediate",
        "learning_style": "balanced",
    }

    for _ in range(5):
        record = await _create_record(
            db_session,
            user_id=cohort_user_id,
            trigger_type=InterventionTriggerType.CONCEPT_GAP,
            strategy=DeliveryStrategy.SUPPORTIVE,
            outcome=InterventionOutcomeStatus.EFFECTIVE,
            acted=True,
        )
        await learner.record_outcome(
            user_id=cohort_user_id,
            intervention_id=record.id,
            outcome_status=record.outcome_status,
            context_snapshot=cohort_profile,
        )

    best = await learner.get_best_strategy(
        test_user.id,
        InterventionTriggerType.CONCEPT_GAP,
        cohort_profile=cohort_profile,
    )

    assert best == DeliveryStrategy.SUPPORTIVE
