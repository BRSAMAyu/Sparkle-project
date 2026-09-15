from __future__ import annotations

import json
from datetime import date

import pytest

from app.models.card_protocol import (
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
    InterventionRecord,
    InterventionTriggerType,
)
from app.models.plan import Plan, PlanStage, PlanType
from app.services.intervention_feedback_binding_service import InterventionFeedbackBindingService


class _FakeRedis:
    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self._ttl: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self._kv.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._kv[key] = value
        self._ttl[key] = ttl


@pytest.fixture
async def test_plan(db_session, test_user) -> Plan:
    plan = Plan(
        user_id=test_user.id,
        name="反馈绑定测试计划",
        type=PlanType.SPRINT,
        description="验证 Bridge 4 反馈绑定",
        plan_stage=PlanStage.SPRINT,
        target_date=date(2026, 4, 22),
        daily_available_minutes=60,
        progress=0.1,
        is_active=True,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


@pytest.mark.asyncio
async def test_positive_feedback_binding_marks_record_and_updates_learner(db_session, test_user):
    redis = _FakeRedis()
    service = InterventionFeedbackBindingService(db_session, redis=redis)
    record = InterventionRecord(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.STALL_PATTERN,
        delivery_strategy=DeliveryStrategy.MICRO_RESTART,
        delivery_channel=DeliveryChannel.CHAT,
        acceptance_status=InterventionAcceptanceStatus.DELIVERED,
        outcome_status=InterventionOutcomeStatus.PENDING,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    result = await service.bind_feedback(
        user_id=test_user.id,
        session_id="session-bind-positive",
        sentiment="helped",
        user_words="That actually helped me restart.",
        confidence=0.91,
        intervention_id=str(record.id),
        message_id="msg-positive",
    )
    await db_session.refresh(record)

    assert result["bound"] is True
    assert result["duplicate_suppressed"] is False
    assert record.acceptance_status == InterventionAcceptanceStatus.ACTED
    assert result["learner_recorded"] is True
    latest_feedback = (record.action_payload or {}).get("latest_feedback") or {}
    assert latest_feedback["sentiment"] == "helped"


@pytest.mark.asyncio
async def test_negative_feedback_binding_dismisses_record(db_session, test_user):
    redis = _FakeRedis()
    service = InterventionFeedbackBindingService(db_session, redis=redis)
    record = InterventionRecord(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.CONCEPT_GAP,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        acceptance_status=InterventionAcceptanceStatus.DELIVERED,
        outcome_status=InterventionOutcomeStatus.PENDING,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    result = await service.bind_feedback(
        user_id=test_user.id,
        session_id="session-bind-negative",
        sentiment="not_helped",
        user_words="No, that was not helpful.",
        confidence=0.88,
        intervention_id=str(record.id),
        message_id="msg-negative",
    )
    await db_session.refresh(record)

    assert result["bound"] is True
    assert record.acceptance_status == InterventionAcceptanceStatus.DISMISSED
    assert result["learner_recorded"] is True


@pytest.mark.asyncio
async def test_feedback_binding_returns_no_active_intervention_when_none_found(db_session, test_user):
    service = InterventionFeedbackBindingService(db_session, redis=_FakeRedis())

    result = await service.bind_feedback(
        user_id=test_user.id,
        session_id="session-no-active",
        sentiment="mixed",
        user_words="I am not sure that changed much.",
        confidence=0.62,
        message_id="msg-none",
    )

    assert result["bound"] is False
    assert result["duplicate_suppressed"] is False
    assert result["reason"] == "no_active_intervention"


@pytest.mark.asyncio
async def test_feedback_binding_suppresses_duplicate_message(db_session, test_user):
    redis = _FakeRedis()
    service = InterventionFeedbackBindingService(db_session, redis=redis)
    record = InterventionRecord(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.DIRECT,
        delivery_channel=DeliveryChannel.CHAT,
        acceptance_status=InterventionAcceptanceStatus.DELIVERED,
        outcome_status=InterventionOutcomeStatus.PENDING,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    first = await service.bind_feedback(
        user_id=test_user.id,
        session_id="session-dedupe",
        sentiment="accepted",
        user_words="Yes, this framing is better.",
        confidence=0.8,
        intervention_id=str(record.id),
        message_id="msg-dedupe",
    )
    second = await service.bind_feedback(
        user_id=test_user.id,
        session_id="session-dedupe",
        sentiment="accepted",
        user_words="Yes, this framing is better.",
        confidence=0.8,
        intervention_id=str(record.id),
        message_id="msg-dedupe",
    )

    assert first["bound"] is True
    assert second["bound"] is False
    assert second["duplicate_suppressed"] is True
    stored = json.loads(redis._kv[f"{service.LAST_FEEDBACK_BINDING_KEY_PREFIX}session-dedupe"])
    assert stored["message_id"] == "msg-dedupe"


@pytest.mark.asyncio
async def test_resolve_active_interventions_ignores_remembered_closed_records(db_session, test_user):
    redis = _FakeRedis()
    service = InterventionFeedbackBindingService(db_session, redis=redis)
    record = InterventionRecord(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.DIRECT,
        delivery_channel=DeliveryChannel.CHAT,
        acceptance_status=InterventionAcceptanceStatus.DISMISSED,
        outcome_status=InterventionOutcomeStatus.PENDING,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    await service.remember_active_interventions(
        "session-closed-memory",
        [{"intervention_id": str(record.id), "source": "session_memory"}],
    )

    result = await service.bind_feedback(
        user_id=test_user.id,
        session_id="session-closed-memory",
        sentiment="accepted",
        user_words="Actually this part was okay.",
        confidence=0.7,
        message_id="msg-closed",
    )

    assert result["bound"] is False
    assert result["reason"] == "no_active_intervention"
    remembered = json.loads(redis._kv[f"{service.ACTIVE_INTERVENTIONS_KEY_PREFIX}session-closed-memory"])
    assert remembered == []


@pytest.mark.asyncio
async def test_feedback_binding_suppresses_non_consecutive_duplicate_message(db_session, test_user):
    redis = _FakeRedis()
    service = InterventionFeedbackBindingService(db_session, redis=redis)
    record = InterventionRecord(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.DIRECT,
        delivery_channel=DeliveryChannel.CHAT,
        acceptance_status=InterventionAcceptanceStatus.DELIVERED,
        outcome_status=InterventionOutcomeStatus.PENDING,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    first = await service.bind_feedback(
        user_id=test_user.id,
        session_id="session-non-consecutive-dedupe",
        sentiment="accepted",
        user_words="Yes, this framing is better.",
        confidence=0.8,
        intervention_id=str(record.id),
        message_id="msg-a",
    )
    second = await service.bind_feedback(
        user_id=test_user.id,
        session_id="session-non-consecutive-dedupe",
        sentiment="mixed",
        user_words="I am still not fully sure.",
        confidence=0.6,
        intervention_id=str(record.id),
        message_id="msg-b",
    )
    third = await service.bind_feedback(
        user_id=test_user.id,
        session_id="session-non-consecutive-dedupe",
        sentiment="accepted",
        user_words="Yes, this framing is better.",
        confidence=0.8,
        intervention_id=str(record.id),
        message_id="msg-a",
    )

    assert first["bound"] is True
    assert second["bound"] is True
    assert third["bound"] is False
    assert third["duplicate_suppressed"] is True
