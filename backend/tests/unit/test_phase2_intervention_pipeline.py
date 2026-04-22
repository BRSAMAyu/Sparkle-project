from __future__ import annotations

from datetime import datetime, timedelta
import sys
import types
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select
from unittest.mock import AsyncMock

_gen_pkg = types.ModuleType("app.gen")
_sparkle_pkg = types.ModuleType("app.gen.sparkle")
_inference_pkg = types.ModuleType("app.gen.sparkle.inference")
_inference_v1_pkg = types.ModuleType("app.gen.sparkle.inference.v1")
_signals_pkg = types.ModuleType("app.gen.sparkle.signals")
_signals_v1_pkg = types.ModuleType("app.gen.sparkle.signals.v1")
_gateway_client_pkg = types.ModuleType("app.services.gateway_client")
_llm_dispatcher_pkg = types.ModuleType("app.services.llm_dispatcher")
_gen_pkg.__path__ = []
_sparkle_pkg.__path__ = []
_inference_pkg.__path__ = []
_signals_pkg.__path__ = []
_inference_v1_pkg.inference_pb2 = types.SimpleNamespace(
    InferenceRequest=object,
    Budgets=object,
    Message=object,
    PREDICT_NEXT_ACTIONS=0,
    P0=0,
)
_signals_v1_pkg.signals_pb2 = types.SimpleNamespace()
_gateway_client_pkg.GatewayClient = object
_llm_dispatcher_pkg.LLMDispatcher = object
sys.modules.setdefault("app.gen", _gen_pkg)
sys.modules.setdefault("app.gen.sparkle", _sparkle_pkg)
sys.modules.setdefault("app.gen.sparkle.inference", _inference_pkg)
sys.modules.setdefault("app.gen.sparkle.inference.v1", _inference_v1_pkg)
sys.modules.setdefault("app.gen.sparkle.signals", _signals_pkg)
sys.modules.setdefault("app.gen.sparkle.signals.v1", _signals_v1_pkg)
sys.modules.setdefault("app.services.gateway_client", _gateway_client_pkg)
sys.modules.setdefault("app.services.llm_dispatcher", _llm_dispatcher_pkg)

from app.models.card_protocol import (
    CardLifecycleStatus,
    CardType,
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
    InterventionTriggerType,
)
from app.models.notification import Notification, PushHistory
from app.models.notification_interaction import NotificationInteraction
from app.models.push_delivery_record import PushDeliveryRecord
from app.models.user import PushPreference
from app.services.behavior_signal_collector import BehaviorSignalCollector
from app.services.card_protocol.behavior_intervention_bridge import BehaviorInterventionBridge
from app.services.card_protocol.outcome_verifier import InterventionOutcomeVerifier
from app.services.card_service import CardService
from app.services.intervention_event_consumer import InterventionEventConsumer
from app.services.intervention_record_service import InterventionRecordService
from app.services.notification_center_service import NotificationCenterService
from app.services.notification_analytics_service import NotificationAnalyticsService
from app.services.plan_health_event_consumer import PlanHealthEventConsumer
from app.services.plan_adjustment_applier import PlanAdjustmentResult
from app.services.plan_state_service import PlanStateService


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
async def test_outcome_verifier_engaged_sweep_skips_created_only_records(db_session, test_user):
    record_service = InterventionRecordService(db_session)

    created_only = await record_service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        outcome_window_days=0,
    )
    created_only.created_at = datetime.utcnow() - timedelta(hours=25)

    engaged = await record_service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        outcome_window_days=0,
    )
    engaged.created_at = datetime.utcnow() - timedelta(hours=25)
    await record_service.mark_delivered(engaged.id)
    await db_session.commit()

    verifier = InterventionOutcomeVerifier(db_session)
    summary = await verifier.verify_engaged_pending()
    await db_session.refresh(created_only)
    await db_session.refresh(engaged)

    assert summary["resolved"] == 1
    assert created_only.outcome_status == InterventionOutcomeStatus.PENDING
    assert engaged.outcome_status == InterventionOutcomeStatus.INEFFECTIVE


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


@pytest.mark.asyncio
async def test_plan_health_consumer_enqueues_in_app_delivery_for_in_app_record(monkeypatch):
    user_id = uuid4()
    plan_id = uuid4()
    fake_db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    consumer = PlanHealthEventConsumer(event_bus=FakeEventBus())
    enqueue = AsyncMock()

    class FakeBridge:
        async def on_plan_health_signal(self, **kwargs):
            return SimpleNamespace(
                id=uuid4(),
                delivery_channel=DeliveryChannel.IN_APP,
                diagnosis_payload={"severity": "critical"},
            )

    monkeypatch.setattr(
        "app.services.plan_health_event_consumer.AsyncSessionLocal",
        lambda: _AsyncSessionContext(fake_db),
    )
    monkeypatch.setattr(
        "app.services.card_protocol.health_intervention_bridge.PlanHealthInterventionBridge",
        lambda db, event_bus=None: FakeBridge(),
    )
    monkeypatch.setattr(
        "app.services.plan_health_event_consumer.SystemUpdateService.enqueue",
        enqueue,
    )

    await consumer._handle_plan_health_alerted(
        {
            "event_type": "plan.health.alerted",
            "user_id": str(user_id),
            "plan_id": str(plan_id),
            "severity": "critical",
            "reasons": ["stall_detected"],
            "action_taken": "adjustment_cooldown_active",
        }
    )

    fake_db.commit.assert_awaited_once()
    assert enqueue.await_count == 2
    payload = enqueue.await_args_list[-1].kwargs["payload"]
    assert payload["metadata"]["payload"]["severity"] == "critical"


@pytest.mark.asyncio
async def test_plan_health_consumer_schedules_push_for_push_record(monkeypatch):
    user_id = uuid4()
    plan_id = uuid4()
    fake_db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    consumer = PlanHealthEventConsumer(event_bus=FakeEventBus())
    scheduled_calls: list[dict] = []

    class FakeBridge:
        async def on_plan_health_signal(self, **kwargs):
            return SimpleNamespace(
                id=uuid4(),
                delivery_channel=DeliveryChannel.PUSH,
                diagnosis_payload={"severity": "critical", "reason": "stall_detected"},
            )

    class _FakeTask:
        @staticmethod
        def delay(**kwargs):
            scheduled_calls.append(kwargs)

    monkeypatch.setattr(
        "app.services.plan_health_event_consumer.AsyncSessionLocal",
        lambda: _AsyncSessionContext(fake_db),
    )
    monkeypatch.setattr(
        "app.services.card_protocol.health_intervention_bridge.PlanHealthInterventionBridge",
        lambda db, event_bus=None: FakeBridge(),
    )
    monkeypatch.setattr(
        "app.core.celery_tasks.schedule_push_notification",
        _FakeTask(),
    )

    await consumer._handle_plan_health_alerted(
        {
            "event_type": "plan.health.alerted",
            "user_id": str(user_id),
            "plan_id": str(plan_id),
            "severity": "critical",
            "reasons": ["stall_detected"],
            "action_taken": "none",
        }
    )

    fake_db.commit.assert_awaited_once()
    assert len(scheduled_calls) == 1
    assert scheduled_calls[0]["user_id"] == str(user_id)
    assert scheduled_calls[0]["payload"]["reason"] == "stall_detected"


@pytest.mark.asyncio
async def test_behavior_bridge_creates_push_record_without_premarking_delivered(db_session, test_user):
    card_service = CardService(db_session)
    plan_card = await card_service.create_card(
        card_type=CardType.PLAN,
        owner_id=test_user.id,
        holder_id=test_user.id,
        metadata={"name": "Micro Restart Plan", "legacy_plan_id": str(uuid4())},
        lifecycle_status=CardLifecycleStatus.ACTIVE,
    )
    legacy_plan_id = uuid4()
    plan_card.metadata_ = {**(plan_card.metadata_ or {}), "legacy_plan_id": str(legacy_plan_id)}
    await db_session.commit()

    bridge = BehaviorInterventionBridge(db_session, FakeEventBus())
    record = await bridge.on_behavior_pattern(
        user_id=test_user.id,
        pattern_name="procrastination",
        pattern_type="execution",
        confidence=0.9,
        frequency=3,
        plan_id=legacy_plan_id,
        description="User keeps deferring start",
        solution_text="先开一个 5 分钟计时器",
    )
    await db_session.commit()

    assert record is not None
    assert record.delivery_channel == DeliveryChannel.PUSH
    assert record.acceptance_status == InterventionAcceptanceStatus.CREATED


@pytest.mark.asyncio
async def test_intervention_consumer_delivers_and_marks_record_delivered(db_session, test_user, monkeypatch):
    record_service = InterventionRecordService(db_session, FakeEventBus())
    record = await record_service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        diagnosis_payload={"reasons": ["progress_lag"]},
    )
    await db_session.commit()

    monkeypatch.setattr(
        "app.services.intervention_event_consumer.AsyncSessionLocal",
        lambda: _AsyncSessionContext(db_session),
    )
    monkeypatch.setattr(
        "app.services.notification_service.NotificationService._should_push_notification",
        AsyncMock(return_value=(False, None)),
    )

    consumer = InterventionEventConsumer(event_bus=FakeEventBus())
    await consumer._handle_record_created(
        {"event_type": "intervention_record.created", "record_id": str(record.id)}
    )
    await db_session.refresh(record)

    notif_result = await db_session.execute(
        select(Notification).where(Notification.user_id == test_user.id)
    )
    notifications = list(notif_result.scalars().all())

    assert record.acceptance_status == InterventionAcceptanceStatus.DELIVERED
    assert notifications
    assert notifications[-1].type == "intervention"
    assert record.action_payload["rendered_message"]
    assert record.action_payload["intent_type"] == "plan_path_soft_replan"


@pytest.mark.asyncio
async def test_intervention_consumer_records_push_history_for_push_channel(db_session, test_user, monkeypatch):
    prefs = PushPreference(user_id=test_user.id, timezone="Asia/Shanghai")
    db_session.add(prefs)
    await db_session.commit()

    record_service = InterventionRecordService(db_session, FakeEventBus())
    record = await record_service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.STALL_PATTERN,
        delivery_strategy=DeliveryStrategy.MICRO_RESTART,
        delivery_channel=DeliveryChannel.PUSH,
        diagnosis_payload={"solution_text": "先做 5 分钟最小入口"},
    )
    await db_session.commit()

    monkeypatch.setattr(
        "app.services.intervention_event_consumer.AsyncSessionLocal",
        lambda: _AsyncSessionContext(db_session),
    )
    monkeypatch.setattr(
        "app.services.notification_service.NotificationService._should_push_notification",
        AsyncMock(return_value=(False, None)),
    )

    consumer = InterventionEventConsumer(event_bus=FakeEventBus())
    await consumer._handle_record_created(
        {"event_type": "intervention_record.created", "record_id": str(record.id)}
    )
    await db_session.refresh(record)
    await db_session.refresh(prefs)

    history_result = await db_session.execute(
        select(PushHistory).where(PushHistory.user_id == test_user.id)
    )
    histories = list(history_result.scalars().all())

    assert record.acceptance_status == InterventionAcceptanceStatus.DELIVERED
    assert histories
    assert histories[-1].trigger_type == "behavior_intervention"
    assert prefs.last_push_time is not None


@pytest.mark.asyncio
async def test_intervention_consumer_compiles_parameters_for_plan_backed_record(
    db_session,
    test_user,
    monkeypatch,
):
    card_service = CardService(db_session)
    legacy_plan_id = uuid4()
    plan_card = await card_service.create_card(
        card_type=CardType.PLAN,
        owner_id=test_user.id,
        holder_id=test_user.id,
        metadata={"name": "Adaptive Thermodynamics", "legacy_plan_id": str(legacy_plan_id)},
        lifecycle_status=CardLifecycleStatus.ACTIVE,
    )
    await db_session.commit()

    record_service = InterventionRecordService(db_session, FakeEventBus())
    record = await record_service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        plan_card_id=plan_card.id,
        diagnosis_payload={"reasons": ["progress_lag"], "solution_text": "先压缩到两步"},
    )
    await db_session.commit()

    class FakeCompiler:
        def __init__(self, db, event_bus=None):
            self.db = db
            self.event_bus = event_bus

        async def can_compile(self, plan_card_id):
            return True

        async def compile(self, **kwargs):
            return SimpleNamespace(
                success=True,
                adaptive_adjustments={"time_multiplier": 1.2},
                compilation_meta={"trigger": kwargs["trigger"]},
                decision_log_entry_id="decision-1",
                error=None,
            )

    class FakePatcher:
        def __init__(self, db, redis=None):
            self.db = db
            self.redis = redis

        async def apply_incremental_changes(self, **kwargs):
            return PlanAdjustmentResult(
                applied=True,
                plan_id=legacy_plan_id,
                user_id=test_user.id,
                patch_summary={"time_scaled": {"tasks_affected": 2}},
                affected_task_ids=[uuid4(), uuid4()],
                user_facing_summary="接下来两步已经放缓",
            )

    monkeypatch.setattr(
        "app.services.intervention_event_consumer.AsyncSessionLocal",
        lambda: _AsyncSessionContext(db_session),
    )
    monkeypatch.setattr(
        "app.services.intervention_event_consumer.ParameterCompiler",
        FakeCompiler,
    )
    monkeypatch.setattr(
        "app.services.intervention_event_consumer.PlanAdjustmentApplier",
        FakePatcher,
    )
    monkeypatch.setattr(
        "app.services.notification_service.NotificationService._should_push_notification",
        AsyncMock(return_value=(False, None)),
    )

    consumer = InterventionEventConsumer(event_bus=FakeEventBus())
    await consumer._handle_record_created(
        {"event_type": "intervention_record.created", "record_id": str(record.id)}
    )
    await db_session.refresh(record)

    parameter_payload = record.action_payload["parameter_compilation"]
    assert parameter_payload["applied"] is True
    assert parameter_payload["result"] == "patched"
    assert parameter_payload["plan_id"] == str(legacy_plan_id)
    assert parameter_payload["affected_task_count"] == 2
    assert parameter_payload["compilation_meta"]["trigger"] == "plan_risk"


@pytest.mark.asyncio
async def test_notification_center_classifies_intervention_notifications(
    db_session,
    test_user,
):
    db_session.add_all(
        [
            Notification(
                user_id=test_user.id,
                title="成长提醒",
                content="先从 5 分钟最小入口开始",
                type="intervention_push",
                data={"intent_type": "micro_restart", "record_id": str(uuid4())},
            ),
            Notification(
                user_id=test_user.id,
                title="系统提醒",
                content="你有新的成就",
                type="achievement",
                data={"achievement_id": str(uuid4())},
            ),
        ]
    )
    await db_session.commit()

    service = NotificationCenterService(db_session)
    intervention_items = await service.get_unified_notifications(
        user_id=test_user.id,
        source_type="intervention",
    )
    system_items = await service.get_unified_notifications(
        user_id=test_user.id,
        source_type="system",
    )

    assert len(intervention_items) == 1
    assert intervention_items[0].source_type == "intervention"
    assert intervention_items[0].type == "intervention_push"
    assert intervention_items[0].metadata["intent_type"] == "micro_restart"

    assert len(system_items) == 1
    assert system_items[0].source_type == "system"
    assert system_items[0].type == "achievement"


@pytest.mark.asyncio
async def test_mark_notification_read_marks_linked_intervention_seen(
    db_session,
    test_user,
):
    record_service = InterventionRecordService(db_session, FakeEventBus())
    record = await record_service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
    )
    await record_service.mark_delivered(record.id)
    notification = Notification(
        user_id=test_user.id,
        title="成长提醒",
        content="先把今天的步子调轻一点",
        type="intervention",
        data={"record_id": str(record.id)},
    )
    db_session.add(notification)
    await db_session.commit()

    service = NotificationCenterService(db_session)
    success = await service.mark_notification_read(
        user_id=test_user.id,
        notification_id=notification.id,
        notification_type="intervention",
    )
    await db_session.refresh(record)
    await db_session.refresh(notification)

    assert success is True
    assert notification.is_read is True
    assert record.acceptance_status == InterventionAcceptanceStatus.SEEN


@pytest.mark.asyncio
async def test_notification_center_can_accept_and_act_on_intervention(
    db_session,
    test_user,
):
    record_service = InterventionRecordService(db_session, FakeEventBus())
    record = await record_service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.STALL_PATTERN,
        delivery_strategy=DeliveryStrategy.MICRO_RESTART,
        delivery_channel=DeliveryChannel.PUSH,
    )
    await record_service.mark_delivered(record.id)
    notification = Notification(
        user_id=test_user.id,
        title="先从 5 分钟开始",
        content="我帮你把门槛再降一点",
        type="intervention_push",
        data={"record_id": str(record.id)},
    )
    db_session.add(notification)
    await db_session.commit()

    service = NotificationCenterService(db_session)
    accepted = await service.transition_intervention_notification(
        user_id=test_user.id,
        notification_id=notification.id,
        action="accepted",
        action_payload={"surface": "notification_center"},
    )
    await db_session.refresh(record)
    assert accepted is True
    assert record.acceptance_status == InterventionAcceptanceStatus.ACCEPTED

    acted = await service.transition_intervention_notification(
        user_id=test_user.id,
        notification_id=notification.id,
        action="acted",
        action_payload={"cta": "start_now"},
    )
    await db_session.refresh(record)
    await db_session.refresh(notification)

    assert acted is True
    assert notification.is_read is True
    assert record.acceptance_status == InterventionAcceptanceStatus.ACTED
    assert record.action_payload["cta"] == "start_now"
    assert "acted_at" in record.action_payload


@pytest.mark.asyncio
async def test_notification_center_can_transition_intervention_record_directly(
    db_session,
    test_user,
):
    record_service = InterventionRecordService(db_session, FakeEventBus())
    record = await record_service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.OVERLOAD,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.FOCUS_MODE,
    )
    await record_service.mark_delivered(record.id)
    notification = Notification(
        user_id=test_user.id,
        title="先放轻一点",
        content="从一件小事开始",
        type="intervention_push",
        data={"record_id": str(record.id)},
    )
    db_session.add(notification)
    await db_session.commit()

    service = NotificationCenterService(db_session)
    transitioned = await service.transition_intervention_record(
        user_id=test_user.id,
        record_id=record.id,
        action="seen",
        action_payload={"surface": "push_open"},
    )
    await db_session.refresh(record)
    await db_session.refresh(notification)

    assert transitioned is True
    assert record.acceptance_status == InterventionAcceptanceStatus.SEEN
    assert notification.is_read is True


@pytest.mark.asyncio
async def test_clear_read_notifications_bulk_loads_linked_push_notifications(
    db_session,
    test_user,
    monkeypatch,
):
    linked_notification = Notification(
        user_id=test_user.id,
        title="推送提醒",
        content="今天还差最后一步",
        type="aurora_push",
        is_read=True,
        read_at=datetime.utcnow(),
    )
    system_notification = Notification(
        user_id=test_user.id,
        title="系统提醒",
        content="已读消息",
        type="achievement",
        is_read=True,
        read_at=datetime.utcnow(),
    )
    db_session.add_all([linked_notification, system_notification])
    await db_session.flush()

    push_record = PushDeliveryRecord(
        user_id=test_user.id,
        notification_id=linked_notification.id,
        policy_id="policy-1",
        category="follow_up",
        message_template_id="template-1",
        title="推送提醒",
        body="今天还差最后一步",
        evidence_token="evt-1",
        scheduled_send_at=datetime.utcnow(),
        sent_at=datetime.utcnow(),
        read_at=datetime.utcnow(),
        status="sent",
    )
    db_session.add(push_record)
    await db_session.commit()

    monkeypatch.setattr(
        db_session,
        "get",
        AsyncMock(side_effect=AssertionError("clear_read_notifications should not issue per-record db.get calls")),
    )

    service = NotificationCenterService(db_session)
    deleted_count = await service.clear_read_notifications(test_user.id)
    await db_session.refresh(push_record)
    await db_session.refresh(linked_notification)

    assert deleted_count == 2
    assert push_record.deleted_at is not None
    assert linked_notification.deleted_at is not None


@pytest.mark.asyncio
async def test_outcome_verifier_treats_parameter_compilation_with_positive_feedback_as_effective(
    db_session,
    test_user,
):
    card_service = CardService(db_session)
    legacy_plan_id = uuid4()
    plan_card = await card_service.create_card(
        card_type=CardType.PLAN,
        owner_id=test_user.id,
        holder_id=test_user.id,
        metadata={"name": "Thermo Rescue", "legacy_plan_id": str(legacy_plan_id)},
        lifecycle_status=CardLifecycleStatus.ACTIVE,
    )

    plan_state_service = PlanStateService(db_session, redis=None)
    state = await plan_state_service.get_or_create_plan_state(
        user_id=test_user.id,
        plan_id=legacy_plan_id,
    )
    state.feedback_log = [
        {
            "id": "fb-positive",
            "timestamp": datetime.utcnow().isoformat(),
            "type": "task_feedback",
            "content": "节奏更顺了，今天能继续往下做。",
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
            "affected_task_count": 2,
            "inserted_task_count": 0,
            "hidden_task_count": 0,
        }
    }
    record.created_at = datetime.utcnow() - timedelta(days=2)
    await record_service.mark_acted(record.id, action_payload={"cta": "start_now"})
    await db_session.commit()

    verifier = InterventionOutcomeVerifier(db_session)
    summary = await verifier.verify_all_pending()
    await db_session.refresh(record)

    assert summary["effective"] == 1
    assert record.outcome_status == InterventionOutcomeStatus.EFFECTIVE
    assert record.evidence_payload["improvement"]["parameter_strategy_effective"] is True


@pytest.mark.asyncio
async def test_unified_notifications_include_intervention_status_and_outcome_metadata(
    db_session,
    test_user,
):
    record_service = InterventionRecordService(db_session, FakeEventBus())
    record = await record_service.create_record(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        outcome_window_days=1,
    )
    await record_service.mark_delivered(record.id)
    await record_service.mark_accepted(record.id)
    await record_service.mark_acted(record.id, action_payload={"cta": "start_now"})
    await record_service.resolve_outcome(
        record.id,
        InterventionOutcomeStatus.EFFECTIVE,
        evidence_payload={"improvement": {"parameter_strategy_effective": True}},
    )
    db_session.add(
        Notification(
            user_id=test_user.id,
            title="节奏已经帮你放缓",
            content="现在可以继续往下走了",
            type="intervention",
            data={"record_id": str(record.id)},
        )
    )
    await db_session.commit()

    service = NotificationCenterService(db_session)
    notifications = await service.get_unified_notifications(
        user_id=test_user.id,
        source_type="intervention",
    )

    assert len(notifications) == 1
    assert notifications[0].metadata["acceptance_status"] == "ACTED"
    assert notifications[0].metadata["outcome_status"] == "EFFECTIVE"
    assert notifications[0].metadata["outcome_evidence"]["improvement"]["parameter_strategy_effective"] is True


@pytest.mark.asyncio
async def test_notification_analytics_counts_intervention_acceptance_and_action(
    db_session,
    test_user,
):
    notification = Notification(
        user_id=test_user.id,
        title="先把这一步收下",
        content="只做最小入口",
        type="intervention",
        is_read=True,
    )
    db_session.add(notification)
    await db_session.flush()
    now = datetime.utcnow()
    db_session.add_all(
        [
            NotificationInteraction(
                id=uuid4(),
                user_id=test_user.id,
                notification_type='intervention',
                notification_id=notification.id,
                action_type='viewed',
                action_time=now,
                time_to_action=20,
            ),
            NotificationInteraction(
                id=uuid4(),
                user_id=test_user.id,
                notification_type='intervention',
                notification_id=notification.id,
                action_type='accepted',
                action_time=now,
                time_to_action=45,
            ),
            NotificationInteraction(
                id=uuid4(),
                user_id=test_user.id,
                notification_type='intervention',
                notification_id=notification.id,
                action_type='acted',
                action_time=now,
                time_to_action=90,
            ),
        ]
    )
    await db_session.commit()

    service = NotificationAnalyticsService(db_session)
    analytics = await service.get_analytics(test_user.id, period='7d')

    assert analytics.summary.total_accepted == 1
    assert analytics.summary.total_acted == 1
    assert analytics.by_type['intervention'].accepted == 1
    assert analytics.by_type['intervention'].acted == 1
    assert analytics.trends[-1].accepted >= 1
    assert analytics.trends[-1].acted >= 1
    assert analytics.time_to_action_buckets
