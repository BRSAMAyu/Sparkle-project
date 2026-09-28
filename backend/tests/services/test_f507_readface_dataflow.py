"""V3-FIX-507 · D-05 lifecycle 生产接线读侧数据流守卫（红先行）。

修法（台账 T-d05-lifecycle-production-wiring）：交付面（mark_delivered/响应转场）、
spine 管线 directive 下发点、D-02 ledger 增量扫描（定时任务调用的服务入口）三处
真实节点挂 record_exposure / record_response / associate_pending_outcomes。

本文件只通过**既有生产入口**驱动写路径，对三读侧消费方各写一测 + 写面事实一测：
- D-07 洞察卡（EvidenceInsightService.build_cards）
- M-06 经验投影（ExperienceMemoryProjector.project）
- North Star intervention 面（NorthStarWVPLService._intervention_lifecycle）
- lifecycle 行事实（交付面 exposure+response；spine 面 friction 归因 exposure）

修前（生产零调用）：真实交付/下发流程跑完后 lifecycle 表零行 → 全红；
接线后同一数据流翻转全绿（红→绿实录见 v3-output/WT797-F507/notes.md）。
spine 面测试经 ``app.services.intervention_lifecycle_wiring`` 接线模块换装测试
session——修前该模块不存在即 ImportError，本身即「spine 写路径不存在」的红。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.card_protocol import (
    CardType,
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionTriggerType,
)
from app.models.intervention_lifecycle import InterventionLifecycleEvent
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.card_service import CardService
from app.services.evidence_insight_service import EvidenceInsightService
from app.services.experience_memory_projector import ExperienceMemoryProjector
from app.services.intervention_event_consumer import InterventionEventConsumer
from app.services.intervention_lifecycle_service import InterventionLifecycleService
from app.services.intervention_record_service import InterventionRecordService
from app.signals.spine_orchestrator import SpineOrchestrator
from app.signals.types import ActionableSignal, _uid


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


class _FakePipelineLite:
    """pipeline() 的最小异步 CM 形态（state_register upsert 用）。"""

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
    """spine 管线单测的最小 redis 桩（既有管线对 redis 缺项按降级容错推进）。"""

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


async def _make_user(db_session) -> User:
    user = User(
        username=f"f507{uuid4().hex[:8]}",
        email=f"f507{uuid4().hex[:8]}@t.co",
        hashed_password="x",
        registration_source="email",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _sig(state_key: str = "task_granularity_fit", claim: str = "recent_task_too_large") -> ActionableSignal:
    return ActionableSignal(
        signal_id=_uid("sig"),
        source_event_ids=[_uid("evt")],
        source_system="test",
        state_key=state_key,
        claim=claim,
        confidence=0.85,
        scope="task",
        ttl_hours=24,
        evidence_summary="recent tasks too large",
        possible_effects=["split"],
        priority="medium",
    )


async def _lifecycle_rows(db_session, user_id) -> list[InterventionLifecycleEvent]:
    return list(
        (
            await db_session.execute(
                select(InterventionLifecycleEvent).where(InterventionLifecycleEvent.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )


async def _drive_delivery_face(db_session, user: User):
    """真实交付面写路径：创建 → 消费者投递（mark_delivered）→ 用户接受。

    只用既有生产入口组合（InterventionEventConsumer + InterventionRecordService）。
    返回 (record_service, record, legacy_plan_id)。
    """
    legacy_plan_id = uuid4()
    card_service = CardService(db_session)
    plan_card = await card_service.create_card(
        card_type=CardType.PLAN,
        owner_id=user.id,
        holder_id=user.id,
        metadata={"name": "F507 plan", "legacy_plan_id": str(legacy_plan_id)},
    )

    record_service = InterventionRecordService(db_session, FakeEventBus())
    record = await record_service.create_record(
        user_id=user.id,
        trigger_type=InterventionTriggerType.PLAN_RISK,
        delivery_strategy=DeliveryStrategy.SUPPORTIVE,
        delivery_channel=DeliveryChannel.CHAT,
        plan_card_id=plan_card.id,
        diagnosis_payload={"reasons": ["progress_lag"]},
    )
    await db_session.commit()

    # 消费者真实投递路径（test_phase2 惯例：session 上下文替换 + 推送抑制）
    from unittest.mock import AsyncMock

    import app.services.intervention_event_consumer as consumer_mod

    original_factory = consumer_mod.AsyncSessionLocal
    consumer_mod.AsyncSessionLocal = lambda: _AsyncSessionContext(db_session)
    try:
        consumer = InterventionEventConsumer(event_bus=FakeEventBus())
        await consumer._handle_record_created(
            {"event_type": "intervention_record.created", "record_id": str(record.id)}
        )
    finally:
        consumer_mod.AsyncSessionLocal = original_factory
    del AsyncMock

    await db_session.refresh(record)
    assert record.acceptance_status == InterventionAcceptanceStatus.DELIVERED

    # 用户响应（既有反馈面同款转场：DELIVERED → ACCEPTED）
    await record_service.mark_accepted(record.id)
    await db_session.commit()
    return record_service, record, legacy_plan_id


async def _drive_spine_face(db_session, user: User) -> None:
    """真实 spine 管线下发路径：规则命中信号 → _run_signal_pipeline directive 定稿。

    经接线模块换装测试 session；修前模块不存在 → ImportError（红本体）。
    """
    import app.services.intervention_lifecycle_wiring as wiring

    original_factory = wiring.AsyncSessionLocal
    wiring.AsyncSessionLocal = lambda: _AsyncSessionContext(db_session)
    try:
        orchestrator = SpineOrchestrator(_FakeRedisLite())
        await orchestrator._run_signal_pipeline(user_id=str(user.id), signal=_sig())
    finally:
        wiring.AsyncSessionLocal = original_factory


# ---------------------------------------------------------------------------
# 写面事实（修前红：生产零调用 → lifecycle 零行）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delivery_face_writes_exposure_and_response_rows(db_session):
    """交付面：真实投递 + 用户接受后 lifecycle 有 exposure + accepted 行。"""
    user = await _make_user(db_session)
    await _drive_delivery_face(db_session, user)

    rows = await _lifecycle_rows(db_session, user.id)
    by_type: dict[str, int] = {}
    for row in rows:
        by_type[row.event_type] = by_type.get(row.event_type, 0) + 1

    assert by_type.get("exposed", 0) >= 1, "delivery face must write an exposure row"
    assert by_type.get("accepted", 0) >= 1, "user acceptance must write a response row"

    exposures = [r for r in rows if r.event_type == "exposed"]
    assert all(
        r.decision_id.startswith("aurora_") for r in exposures
    ), "delivery exposure decision_id must be A-01 content-addressed"


@pytest.mark.asyncio
async def test_spine_pipeline_writes_friction_attributed_exposure(db_session):
    """spine 面：管线 directive 下发后 lifecycle 有 friction 归因的 exposure 行。"""
    user = await _make_user(db_session)
    await _drive_spine_face(db_session, user)

    rows = await _lifecycle_rows(db_session, user.id)
    spine_rows = [r for r in rows if r.event_type == "exposed" and r.friction_tag not in (None, "", "unattributed")]
    assert spine_rows, "spine directive dispatch must write a friction-attributed exposure"
    assert (
        spine_rows[0].intervention_type == "rescope"
    ), "task_granularity_fit/too_large maps to rescope via SPINE_STRATEGY_TO_INTERVENTION"


# ---------------------------------------------------------------------------
# 三读侧消费方数据流（修前恒空 → 红；接线后 → 绿）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_readface_d07_cards_fed_by_production_writes(db_session):
    """D-07：真实写路径 + 关联扫描后，两类洞察卡出现。"""
    user = await _make_user(db_session)
    await _drive_delivery_face(db_session, user)
    await _drive_spine_face(db_session, user)

    now = datetime.utcnow().replace(tzinfo=None)
    _service, _record, legacy_plan_id = await _drive_delivery_face(db_session, user)

    task = Task(
        user_id=user.id,
        title="f507 outcome task",
        type=TaskType.LEARNING,
        estimated_minutes=30,
        status=TaskStatus.COMPLETED,
        completed_at=now + timedelta(hours=1),
        actual_minutes=25,
        plan_id=legacy_plan_id,
    )
    db_session.add(task)
    await db_session.commit()

    new_links = await InterventionLifecycleService(db_session).associate_pending_outcomes(
        user_id=user.id, now=now + timedelta(hours=2)
    )
    assert new_links >= 1, "plan-linked task completion must associate to the delivery exposure"

    cards_result = await EvidenceInsightService(db_session).build_cards(user_id=user.id, now=now + timedelta(hours=2))
    cards = cards_result["data"]["cards"]
    kinds = {card["kind"] for card in cards}
    assert "friction_pattern" in kinds, "spine-fed exposures must surface friction pattern cards"
    assert "interventions_that_helped" in kinds, "associated outcomes must surface helped cards"


@pytest.mark.asyncio
async def test_readface_m06_projection_fed_by_production_writes(db_session):
    """M-06：真实交付面写路径后经验投影非空。"""
    user = await _make_user(db_session)
    await _drive_delivery_face(db_session, user)

    projection = await ExperienceMemoryProjector(db_session).project(user_id=user.id, use_cache=False)
    assert len(projection.records) >= 1, "delivered interventions must project into experience memory"


@pytest.mark.asyncio
async def test_readface_north_star_counts_fed_by_production_writes(db_session):
    """North Star：真实交付面写路径后 lifecycle 计数非零。"""
    user = await _make_user(db_session)
    await _drive_delivery_face(db_session, user)

    now = datetime.utcnow().replace(tzinfo=None)
    seed_subq = select(User.id).where(User.registration_source.in_(("seed", "guest", "demo")))
    by_type, _started_by_mode = await _north_star_lifecycle_face(db_session)(
        now - timedelta(days=1), now + timedelta(days=1), seed_subq
    )
    assert by_type.get("exposed", 0) >= 1, "delivered interventions must count into north star lifecycle face"


def _north_star_lifecycle_face(db):
    """North Star lifecycle 私有面的最小委托（避免拉起全量 WVPL 快照）。"""
    from app.services.north_star_wvpl_service import NorthStarWvplService

    async def _call(start, end, seed_ids_subq):
        svc = NorthStarWvplService.__new__(NorthStarWvplService)
        svc.db = db
        return await svc._intervention_lifecycle(start, end, seed_ids_subq)

    return _call
