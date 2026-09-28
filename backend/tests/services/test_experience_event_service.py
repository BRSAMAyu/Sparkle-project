"""V4-D01 · 真实呈现（rendered exposure）三态集成守卫（sqlite 隔离，不触 dev DB）。

验收对照（卡 V4-D01）：
- **曝光**：mark_seen 真实转场 → experience_event.v1 投影，receipt_ref 必指 D-05
  权威 exposed 回执（I2），既有总线单主题发布；下发路径永不产呈现事件；
- **未曝光**：仅 mark_delivered（后台/不可见下发）→ 只有交付回执（detail
  exposure_basis=delivered），无任何 experience_event；
- **回执缺失降级**：渲染上报但权威回执不在 → 可观测降级、不产事件、不炸转场；
- **重复 render 不重复曝光**：重复 mark_seen 短路；SNOOZED→SEEN 再渲染同
  event_id（内容寻址身份恒一）；
- **丢事件可重放**：重放恒同 id；**不拖主业务**：发布失败 SEEN 转场照常。
"""

from __future__ import annotations

import pytest
from sqlalchemy import delete, select

from app.core.experience_event import EXPERIENCE_EVENT_SCHEMA_VERSION
from app.models.card_protocol import (
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionTriggerType,
)
from app.models.intervention_lifecycle import InterventionLifecycleEvent
from app.services.experience_event_service import (
    EXPERIENCE_EVENT_TOPIC,
    ExperienceEventService,
)
from app.services.intervention_lifecycle_wiring import (
    DELIVERY_EXPOSURE_BASIS,
    EXPOSURE_BASIS_DETAIL_KEY,
)
from app.services.intervention_record_service import InterventionRecordService


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []
        self.fail_topics: set[str] = set()

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events") -> str | None:
        if event_type in self.fail_topics:
            raise RuntimeError("simulated bus outage")
        self.events.append((event_type, payload))
        return "event-id"

    def of_topic(self, topic: str) -> list[dict]:
        return [payload for name, payload in self.events if name == topic]


async def _make_record(db, user_id, **overrides):
    service = InterventionRecordService(db, FakeEventBus())
    return await service.create_record(
        user_id=user_id,
        trigger_type=overrides.get("trigger_type", InterventionTriggerType.PLAN_RISK),
        delivery_strategy=overrides.get("delivery_strategy", DeliveryStrategy.SUPPORTIVE),
        delivery_channel=overrides.get("delivery_channel", DeliveryChannel.CHAT),
        diagnosis_payload=overrides.get("diagnosis_payload", {"reasons": ["progress_lag"]}),
    )


def _delivered_record_service(db, bus) -> InterventionRecordService:
    return InterventionRecordService(db, bus)


# ---------------------------------------------------------------------------
# 状态一：曝光（真实呈现 → 事件投影）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rendered_exposure_projects_event_anchored_to_authoritative_receipt(db_session, test_user):
    bus = FakeEventBus()
    service = InterventionRecordService(db_session, bus)
    record = await _make_record(db_session, test_user.id)

    await service.mark_delivered(record.id)  # 交付面：D-05 权威 exposed 回执落账
    seen = await service.mark_seen(record.id)  # 真实呈现转场

    assert seen is not None and seen.acceptance_status == InterventionAcceptanceStatus.SEEN
    rendered_events = bus.of_topic(EXPERIENCE_EVENT_TOPIC)
    assert len(rendered_events) == 1, "exactly one presentation event for one real render"
    payload = rendered_events[0]
    assert payload["schema_version"] == EXPERIENCE_EVENT_SCHEMA_VERSION
    event = payload["event"]
    assert event["kind"] == "state_confirmed"
    assert event["commit_state"] == "committed"
    assert event["error_state"] is None
    assert event["receipt_ref"] is not None and event["receipt_ref"].startswith("intervention_lifecycle://aurora_")
    assert event["subject"] == {
        "type": "intervention",
        "id": str(record.id),
        "version_token": record.content_version,
    }
    assert event["presentation"]["copy_key"] == "intervention.rendered"
    assert event["presentation"]["modalities"] == ["visual"]
    assert payload["rendered_surface"] == "visual"

    # receipt_ref 必指真实存在的权威回执（I2 双门第二门可验证）
    decision_id = event["receipt_ref"].split("intervention_lifecycle://", 1)[1]
    row = (
        await db_session.execute(
            select(InterventionLifecycleEvent).where(
                InterventionLifecycleEvent.decision_id == decision_id,
                InterventionLifecycleEvent.event_type == "exposed",
            )
        )
    ).scalar_one()
    assert row.user_id == test_user.id


@pytest.mark.asyncio
async def test_accessibility_surface_maps_to_audio_modality(db_session, test_user):
    bus = FakeEventBus()
    service = InterventionRecordService(db_session, bus)
    record = await _make_record(db_session, test_user.id)
    await service.mark_delivered(record.id)

    result = await ExperienceEventService(db_session, bus).record_rendered_exposure(
        record, rendered_surface="accessibility"
    )

    assert result.projected is True
    assert result.event is not None and result.event["presentation"]["modalities"] == ["audio"]


# ---------------------------------------------------------------------------
# 状态二：未曝光（后台/不可见下发 ≠ 看到）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delivery_alone_never_projects_presentation_event(db_session, test_user):
    bus = FakeEventBus()
    service = InterventionRecordService(db_session, bus)
    record = await _make_record(db_session, test_user.id)

    await service.mark_delivered(record.id)

    assert bus.of_topic(EXPERIENCE_EVENT_TOPIC) == [], "dispatch must never count as seen"
    # 交付回执在（FIX-507 不回退），且显式携带 delivered 基准
    row = (
        await db_session.execute(
            select(InterventionLifecycleEvent).where(
                InterventionLifecycleEvent.user_id == test_user.id,
                InterventionLifecycleEvent.event_type == "exposed",
            )
        )
    ).scalar_one()
    assert row.detail is not None
    assert row.detail.get(EXPOSURE_BASIS_DETAIL_KEY) == DELIVERY_EXPOSURE_BASIS


@pytest.mark.asyncio
async def test_invalid_rendered_surface_is_refused_not_normalized(db_session, test_user):
    bus = FakeEventBus()
    record = await _make_record(db_session, test_user.id)
    await InterventionRecordService(db_session, bus).mark_delivered(record.id)

    result = await ExperienceEventService(db_session, bus).record_rendered_exposure(
        record, rendered_surface="background_push"
    )

    assert result.projected is False
    assert result.reason == "rendered_surface_invalid"
    assert bus.of_topic(EXPERIENCE_EVENT_TOPIC) == []


# ---------------------------------------------------------------------------
# 状态三：回执缺失降级（I2：无 committed 权威回执不产成功类呈现）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_authoritative_receipt_degrades_observably(db_session, test_user):
    bus = FakeEventBus()
    service = InterventionRecordService(db_session, bus)
    record = await _make_record(db_session, test_user.id)
    await service.mark_delivered(record.id)

    # 权威回执丢失（模拟：交付面 exposed 行被清）
    await db_session.execute(delete(InterventionLifecycleEvent).where(InterventionLifecycleEvent.user_id == test_user.id))
    await db_session.commit()

    result = await ExperienceEventService(db_session, bus).record_rendered_exposure(record)

    assert result.projected is False
    assert result.reason == "no_authoritative_receipt"
    assert result.event is None
    assert bus.of_topic(EXPERIENCE_EVENT_TOPIC) == [], "no receipt → no success-class presentation event"


@pytest.mark.asyncio
async def test_missing_receipt_does_not_break_seen_transition(db_session, test_user):
    """降级不拖主业务：回执缺失时 SEEN 转场照常成立。"""
    service = InterventionRecordService(db_session, FakeEventBus())
    record = await _make_record(db_session, test_user.id)
    await service.mark_delivered(record.id)
    await db_session.execute(
        delete(InterventionLifecycleEvent).where(InterventionLifecycleEvent.user_id == test_user.id)
    )
    await db_session.commit()

    seen = await service.mark_seen(record.id)

    assert seen is not None and seen.acceptance_status == InterventionAcceptanceStatus.SEEN


@pytest.mark.asyncio
async def test_unprojectable_decision_contract_is_refused(db_session, test_user, monkeypatch):
    """决策契约不可投影（未登记 trigger / inert 的守卫分支）→ 无呈现事件。"""
    import app.services.experience_event_service as ee_service

    bus = FakeEventBus()
    record = await _make_record(db_session, test_user.id)
    await InterventionRecordService(db_session, bus).mark_delivered(record.id)

    monkeypatch.setattr(ee_service, "build_record_decision_contract", lambda _record: None)
    result = await ExperienceEventService(db_session, bus).record_rendered_exposure(record)

    assert result.projected is False
    assert result.reason == "decision_contract_unprojectable"
    assert bus.of_topic(EXPERIENCE_EVENT_TOPIC) == []


# ---------------------------------------------------------------------------
# 幂等：重复 render 不重复曝光；重放恒同身份
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repeated_mark_seen_does_not_repeat_exposure(db_session, test_user):
    bus = FakeEventBus()
    service = InterventionRecordService(db_session, bus)
    record = await _make_record(db_session, test_user.id)
    await service.mark_delivered(record.id)

    await service.mark_seen(record.id)
    await service.mark_seen(record.id)  # 已 SEEN：短路

    assert len(bus.of_topic(EXPERIENCE_EVENT_TOPIC)) == 1


@pytest.mark.asyncio
async def test_re_render_after_snooze_keeps_single_exposure_identity(db_session, test_user):
    """SNOOZED→SEEN 是新的真实渲染，但内容寻址身份恒一（不构成第二次曝光）。"""
    bus = FakeEventBus()
    service = InterventionRecordService(db_session, bus)
    record = await _make_record(db_session, test_user.id)
    await service.mark_delivered(record.id)

    await service.mark_seen(record.id)
    await service.mark_snoozed(record.id)
    await service.mark_seen(record.id)

    events = bus.of_topic(EXPERIENCE_EVENT_TOPIC)
    assert len(events) == 2, "two renders published twice"
    assert events[0]["event_id"] == events[1]["event_id"], "identity is content-addressed: unique exposure count == 1"
    assert events[0]["dedupe_key"] == events[1]["dedupe_key"]


@pytest.mark.asyncio
async def test_lost_event_replays_to_identical_identity(db_session, test_user):
    bus = FakeEventBus()
    service = InterventionRecordService(db_session, bus)
    record = await _make_record(db_session, test_user.id)
    await service.mark_delivered(record.id)
    first = await ExperienceEventService(db_session, bus).record_rendered_exposure(record)

    replay_bus = FakeEventBus()
    replayed = await ExperienceEventService(db_session, replay_bus).replay_rendered_exposure(record)

    assert replayed.projected is True
    assert replayed.event_id == first.event_id
    assert replayed.dedupe_key == first.dedupe_key
    # 事件体逐字段恒等（issued_at 是投影时点，重放可异；身份键恒同）
    assert replayed.event is not None and first.event is not None
    assert {k: v for k, v in replayed.event.items() if k != "issued_at"} == {
        k: v for k, v in first.event.items() if k != "issued_at"
    }
    assert replay_bus.of_topic(EXPERIENCE_EVENT_TOPIC)[0]["event_id"] == first.event_id


# ---------------------------------------------------------------------------
# 韧性壳与旧接线不回退
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_failure_does_not_break_seen_transition(db_session, test_user):
    bus = FakeEventBus()
    bus.fail_topics = {EXPERIENCE_EVENT_TOPIC}  # 仅呈现事件通道故障；宿主总线照常
    service = InterventionRecordService(db_session, bus)
    record = await _make_record(db_session, test_user.id)
    await service.mark_delivered(record.id)

    seen = await service.mark_seen(record.id)

    assert seen is not None and seen.acceptance_status == InterventionAcceptanceStatus.SEEN
    assert bus.of_topic(EXPERIENCE_EVENT_TOPIC) == []
    assert len(bus.of_topic("intervention_record.status_changed")) >= 1


@pytest.mark.asyncio
async def test_mark_seen_without_event_bus_still_transitions_and_projects(db_session, test_user):
    """notification center 路径（无 bus 构造）不回退：转场成立，投影可重放。"""
    service = InterventionRecordService(db_session)  # event_bus=None（生产 notification 面形态）
    record = await _make_record(db_session, test_user.id)
    await service.mark_delivered(record.id)

    seen = await service.mark_seen(record.id)
    assert seen is not None and seen.acceptance_status == InterventionAcceptanceStatus.SEEN

    # 事件可随后按权威事实重放（丢事件可重放）
    replay = await ExperienceEventService(db_session).replay_rendered_exposure(seen)
    assert replay.projected is True and replay.event_id.startswith("eev_")


@pytest.mark.asyncio
async def test_delivery_wiring_regression_guard_still_green(db_session, test_user):
    """旧生产接线不回退：mark_delivered → D-05 exposed 行恰一条（幂等）。"""
    from sqlalchemy import func

    service = InterventionRecordService(db_session, FakeEventBus())
    record = await _make_record(db_session, test_user.id)
    await service.mark_delivered(record.id)
    await service.mark_delivered(record.id)

    count = (
        await db_session.execute(
            select(func.count())
            .select_from(InterventionLifecycleEvent)
            .where(
                InterventionLifecycleEvent.user_id == test_user.id,
                InterventionLifecycleEvent.event_type == "exposed",
            )
        )
    ).scalar()
    assert count == 1
