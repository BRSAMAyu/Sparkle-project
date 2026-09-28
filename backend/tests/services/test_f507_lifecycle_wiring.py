"""V3-FIX-507 · lifecycle 生产接线 focused 守卫（映射/幂等/韧性壳/调用点/注册）。

接线的三个真实节点（交付面转场、spine 管线 directive 下发、D-02 ledger 关联
扫描定时任务）的机制性约束。读侧数据流红绿实录见
test_f507_readface_dataflow.py 与 v3-output/WT797-F507/notes.md。
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.aurora_decision import AURORA_INTERVENTION_TYPES
from app.core.intervention_lifecycle import LifecycleEventType
from app.models.card_protocol import (
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionTriggerType,
)
from app.services.intervention_lifecycle_wiring import (
    TRIGGER_TO_CATALOG_INTERVENTION,
    build_directive_decision_contract,
    build_record_decision_contract,
    record_record_response,
)
from app.services.intervention_record_service import InterventionRecordService
from app.signals.spine_orchestrator import SpineOrchestrator
from app.signals.types import ActionableSignal, _uid


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        self.events.append((event_type, payload))
        return "event-id"


async def _make_record(db, user_id, **overrides) -> object:
    service = InterventionRecordService(db, FakeEventBus())
    return await service.create_record(
        user_id=user_id,
        trigger_type=overrides.get("trigger_type", InterventionTriggerType.PLAN_RISK),
        delivery_strategy=overrides.get("delivery_strategy", DeliveryStrategy.SUPPORTIVE),
        delivery_channel=overrides.get("delivery_channel", DeliveryChannel.CHAT),
        diagnosis_payload=overrides.get("diagnosis_payload", {"reasons": ["progress_lag"]}),
    )


def _spine_signal(state_key: str = "task_granularity_fit") -> ActionableSignal:
    return ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=[],
        source_system="test",
        state_key=state_key,
        claim="recent_task_too_large",
        confidence=0.85,
        scope="task",
        ttl_hours=24,
        evidence_summary="recent tasks too large",
        possible_effects=[],
        priority="medium",
    )


# ---------------------------------------------------------------------------
# 投影映射（冻结纪律：全员覆盖、词表内、非 inert）
# ---------------------------------------------------------------------------


class TestTriggerProjection:
    def test_every_trigger_type_is_mapped_to_catalog_member(self):
        """新增 InterventionTriggerType 未登记映射 → 测试红（A-02 同款纪律）。"""
        for trigger in InterventionTriggerType:
            catalog_type = TRIGGER_TO_CATALOG_INTERVENTION.get(trigger)
            assert catalog_type is not None, f"trigger {trigger} missing catalog projection"
            assert catalog_type in AURORA_INTERVENTION_TYPES
            assert catalog_type not in {
                "no_action",
                "abstain",
            }, f"trigger {trigger} must not project to an inert intervention"
        assert len(AURORA_INTERVENTION_TYPES) >= len(TRIGGER_TO_CATALOG_INTERVENTION)


@pytest.mark.asyncio
async def test_decision_id_stability_and_vocabulary(db_session, test_user):
    record_a = await _make_record(db_session, test_user.id)
    record_b = await _make_record(db_session, test_user.id)
    contract_a1 = build_record_decision_contract(record_a)
    contract_a2 = build_record_decision_contract(record_a)
    contract_b = build_record_decision_contract(record_b)
    assert contract_a1 is not None and contract_b is not None
    id_a1 = contract_a1.decision_id_or_compute()
    assert id_a1 == contract_a2.decision_id_or_compute(), "same record must yield same decision_id"
    assert id_a1 != contract_b.decision_id_or_compute(), "distinct deliveries are distinct decisions"
    assert id_a1.startswith("aurora_")
    assert contract_a1.validate() == ()
    assert contract_a1.intervention_type == "rescope"


# ---------------------------------------------------------------------------
# 幂等与韧性壳（交付面）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delivery_exposure_idempotent_on_repeated_mark(db_session, test_user):
    from sqlalchemy import func, select

    from app.models.intervention_lifecycle import InterventionLifecycleEvent

    service = InterventionRecordService(db_session, FakeEventBus())
    record = await _make_record(db_session, test_user.id)

    first = await service.mark_delivered(record.id)
    assert first is not None
    again = await service.mark_delivered(record.id)  # 同状态转场 no-op
    assert again is not None

    count = (
        await db_session.execute(
            select(func.count())
            .select_from(InterventionLifecycleEvent)
            .where(InterventionLifecycleEvent.decision_id.is_not(None))
        )
    ).scalar()
    assert count == 1, f"repeated delivery marking must keep exactly one exposure row, got {count}"


@pytest.mark.asyncio
async def test_lifecycle_failure_does_not_break_delivery_transition(db_session, test_user, monkeypatch):
    """韧性壳（FIX-530 判例）：lifecycle 写失败只留痕，交付转场照常返回。"""
    service = InterventionRecordService(db_session, FakeEventBus())
    record = await _make_record(db_session, test_user.id)

    import app.services.intervention_lifecycle_wiring as wiring

    async def _boom(*args, **kwargs):
        raise RuntimeError("simulated lifecycle outage")

    monkeypatch.setattr(wiring.InterventionLifecycleService, "record_exposure", _boom)
    delivered = await service.mark_delivered(record.id)

    assert delivered is not None
    assert delivered.acceptance_status == InterventionAcceptanceStatus.DELIVERED


@pytest.mark.asyncio
async def test_response_without_exposure_is_refused_not_raised(db_session, test_user):
    """D-05 漏斗完整性：无 exposure 的响应 refused（可观测降级），不炸转场。"""
    record = await _make_record(db_session, test_user.id)
    contract = build_record_decision_contract(record)
    assert contract is not None
    result = await record_record_response(db_session, record, LifecycleEventType.ACCEPTED)
    assert result is not None
    assert result.recorded is False
    assert result.reason == "no_exposure"
    del contract


# ---------------------------------------------------------------------------
# spine 面契约构造（inert/未映射短路；friction 锚真实归因）
# ---------------------------------------------------------------------------


def test_spine_contract_maps_strategy_and_carries_signal_anchor():
    class _Decision:
        primary_strategy = "recover_execution_rhythm"
        policy_decision_id = "pd_1"
        reasoning_summary = "恢复可完成节奏"
        risk_level = "medium"

    class _Directive:
        directive_id = "ed_abc123"

    contract = build_directive_decision_contract(
        user_id=uuid4(), signal=_spine_signal(), decision=_Decision(), directive=_Directive()
    )
    assert contract is not None
    assert contract.intervention_type == "rescope"
    assert contract.governance_mode == "live"
    assert contract.cognition_tier == "l1_light"
    assert contract.evidence_refs == ("signal://task_granularity_fit",)
    assert contract.validate() == ()


def test_spine_contract_skips_inert_and_unmapped_strategies():
    class _Decision:
        primary_strategy = "sustain_momentum"  # SPINE 映射 → no_action（inert）
        policy_decision_id = "pd_2"
        reasoning_summary = "维持动量"
        risk_level = "low"

    class _Directive:
        directive_id = "ed_def456"

    assert (
        build_directive_decision_contract(
            user_id=uuid4(), signal=_spine_signal(), decision=_Decision(), directive=_Directive()
        )
        is None
    ), "inert-mapped strategy must short-circuit to no contract"

    class _UnknownDecision(_Decision):
        primary_strategy = "totally_unknown_strategy"

    assert (
        build_directive_decision_contract(
            user_id=uuid4(), signal=_spine_signal(), decision=_UnknownDecision(), directive=_Directive()
        )
        is None
    ), "unmapped strategy must short-circuit to no contract"


# ---------------------------------------------------------------------------
# spine 管线调用点证明（下发节点真实调用 hook）
# ---------------------------------------------------------------------------


class _FakePipelineLite:
    def __init__(self, redis):
        self._redis = redis
        self._cmds: list[tuple] = []

    def set(self, *args, **kwargs):
        self._cmds.append(("set",) + args)
        return self

    def incr(self, *args, **kwargs):
        self._cmds.append(("incr",) + args)
        return self

    def expire(self, *args, **kwargs):
        self._cmds.append(("expire",) + args)
        return self

    async def execute(self):
        return [1] * len(self._cmds)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeRedisLite:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def pipeline(self):
        return _FakePipelineLite(self)

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value, **kwargs):
        self._store[key] = str(value)
        return True

    async def delete(self, *keys):
        for k in keys:
            self._store.pop(k, None)
        return len(keys)

    async def expire(self, key, ttl):
        return None

    def __getattr__(self, name):
        async def _noop(*args, **kwargs):
            return None

        return _noop


@pytest.mark.asyncio
async def test_pipeline_directive_dispatch_invokes_lifecycle_hook():
    orchestrator = SpineOrchestrator(_FakeRedisLite())
    orchestrator._record_intervention_lifecycle_exposure = AsyncMock(return_value=None)

    await orchestrator._run_signal_pipeline(user_id=str(uuid4()), signal=_spine_signal())

    orchestrator._record_intervention_lifecycle_exposure.assert_awaited_once()
    call = orchestrator._record_intervention_lifecycle_exposure.await_args.kwargs
    assert call["signal"].state_key == "task_granularity_fit"
    assert call["decision"].primary_strategy == "recover_execution_rhythm"
    assert call["directive"].directive_id


# ---------------------------------------------------------------------------
# 写面 3：定时任务注册（beat + 路由）
# ---------------------------------------------------------------------------


def test_association_scan_task_is_registered_in_beat_and_routes():
    from app.core.celery_app import celery_app

    task_name = "app.core.celery_tasks.associate_intervention_lifecycle_outcomes"
    assert task_name in celery_app.conf.task_routes, "association scan must ride low_priority lane"
    assert celery_app.conf.task_routes[task_name] == {"queue": "low_priority"}

    entries = celery_app.conf.beat_schedule.values()
    scheduled_tasks = {entry["task"] for entry in entries}
    assert task_name in scheduled_tasks, "association scan must be scheduled via beat"
