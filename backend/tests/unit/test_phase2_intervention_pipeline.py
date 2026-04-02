from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.models.card_protocol import (
    CardLifecycleStatus,
    CardType,
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
    InterventionTriggerType,
)
from app.services.behavior_signal_collector import BehaviorSignalCollector
from app.services.card_protocol.outcome_verifier import InterventionOutcomeVerifier
from app.services.card_service import CardService
from app.services.intervention_record_service import InterventionRecordService
from app.services.plan_health_event_consumer import PlanHealthEventConsumer


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        self.events.append((event_type, payload))
        return "event-id"


class _AsyncSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_intervention_record_service_enforces_acceptance_order(db_session, test_user):
    service = InterventionRecordService(db_session, FakeEventBus())
    record = await service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
    )

    with pytest.raises(ValueError):
        await service.mark_seen(record.id)

    delivered = await service.mark_delivered(record.id)
    assert delivered is not None
    assert delivered.acceptance_status == InterventionAcceptanceStatus.DELIVERED


@pytest.mark.asyncio
async def test_outcome_verifier_ignores_stale_plan_evidence_and_resolves_delivered(db_session, test_user):
    card_service = CardService(db_session)
    plan_card = await card_service.create_card(
        card_type=CardType.PLAN,
        owner_id=test_user.id,
        holder_id=test_user.id,
        metadata={
            "name": "Stale Recovery Plan",
            "latest_adjustment_evidence": {
                "timestamp": (datetime.utcnow() - timedelta(days=10)).isoformat(),
                "trigger": "task_feedback",
            },
        },
        lifecycle_status=CardLifecycleStatus.ACTIVE,
    )

    record_service = InterventionRecordService(db_session)
    record = await record_service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        plan_card_id=plan_card.id,
        outcome_window_days=1,
    )
    record.created_at = datetime.utcnow() - timedelta(days=2)
    await record_service.mark_delivered(record.id)
    await db_session.commit()

    verifier = InterventionOutcomeVerifier(db_session)
    summary = await verifier.verify_all_pending()
    await db_session.refresh(record)

    assert summary["resolved"] == 1
    assert summary["ineffective"] == 1
    assert record.outcome_status == InterventionOutcomeStatus.INEFFECTIVE
    assert record.evidence_payload["evaluation_method"] == "no_engagement"


@pytest.mark.asyncio
async def test_behavior_signal_collector_commits_created_interventions(monkeypatch):
    user_id = uuid4()
    plan_id = uuid4()

    class FakeBridge:
        instances: list["FakeBridge"] = []

        def __init__(self, db, event_bus=None):
            self.db = db
            self.event_bus = event_bus
            self.calls: list[dict] = []
            FakeBridge.instances.append(self)

        async def on_behavior_pattern(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(id=uuid4())

    db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    collector = BehaviorSignalCollector(db, redis=None, event_bus=FakeEventBus())
    collector.plan_state_service.get_active_plan_states = AsyncMock(
        return_value=[SimpleNamespace(plan_id=plan_id, status="active")]
    )

    on_detected = AsyncMock(return_value=[])
    monkeypatch.setattr(
        "app.services.behavior_signal_collector.AdaptiveReplanner.on_behavior_pattern_detected",
        on_detected,
    )
    monkeypatch.setattr(
        "app.services.card_protocol.behavior_intervention_bridge.BehaviorInterventionBridge",
        FakeBridge,
    )

    await collector.handle_behavior_pattern_event(
        {
            "user_id": str(user_id),
            "pattern_name": "Procrastination",
            "pattern_type": "execution",
            "confidence_score": 0.82,
            "frequency": 3,
        }
    )

    assert FakeBridge.instances
    assert FakeBridge.instances[0].event_bus is collector.event_bus
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_plan_health_consumer_persists_intervention_even_when_visible_update_is_skipped(monkeypatch):
    user_id = uuid4()
    plan_id = uuid4()
    fake_db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    consumer = PlanHealthEventConsumer(event_bus=FakeEventBus())

    class FakeBridge:
        instances: list["FakeBridge"] = []

        def __init__(self, db, event_bus=None):
            self.db = db
            self.event_bus = event_bus
            self.calls: list[dict] = []
            FakeBridge.instances.append(self)

        async def on_plan_health_signal(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(
        "app.services.plan_health_event_consumer.AsyncSessionLocal",
        lambda: _AsyncSessionContext(fake_db),
    )
    monkeypatch.setattr(
        "app.services.card_protocol.health_intervention_bridge.PlanHealthInterventionBridge",
        FakeBridge,
    )

    await consumer._handle_plan_health_alerted(
        {
            "event_type": "plan.health.alerted",
            "user_id": str(user_id),
            "plan_id": str(plan_id),
            "severity": "critical",
            "reasons": ["stall_detected"],
            "action_taken": "incremental_adjustment_applied",
        }
    )

    assert FakeBridge.instances
    assert FakeBridge.instances[0].event_bus is consumer.event_bus
    assert FakeBridge.instances[0].calls[0]["plan_id"] == plan_id
    fake_db.commit.assert_awaited_once()
