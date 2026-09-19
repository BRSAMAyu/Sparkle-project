"""X-05B · execution_run_producer 契约测试（EXECUTING 步进 producer 钩子）.

零新事件名 / 封闭里程碑词表 / 永不抛出 / 进程内流量消减 —— 数据面全部桩测；
真实总线交付与投影见 test_x05b_e2e_execution_projection / F6 首部署测试。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

import app.services.execution_run_producer as producer
from app.core.run_state_machine import RunEventName, RunStatus
from tests.unit.test_agent_run_service import (  # noqa: F401 — 复用 helpers
    _make_intent,
    _make_user,
)


class _CaptureBus:
    def __init__(self, *, fail: bool = False):
        self.published: list[tuple[str, dict, str]] = []
        self._fail = fail

    async def publish(self, event_type: str, payload: dict, stream: str = "sparkle_events"):
        if self._fail:
            raise RuntimeError("bus down")
        self.published.append((str(event_type), dict(payload), stream))
        return f"msg-{len(self.published)}"


@pytest.fixture(autouse=True)
def _clean_dedup():
    producer._recently_published.clear()
    yield
    producer._recently_published.clear()


async def test_step_event_protocol_reuses_run_status_changed(db_session, monkeypatch):
    """漏斗协议：event_type=run.status_changed（冻结词表既有名，零新名），
    payload 带 intent/user/task 定位键 + milestone/run 扩展块（schema 扩展）。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    bus = _CaptureBus()
    monkeypatch.setattr(producer, "event_bus", bus)

    await producer.publish_execution_step_event(intent, "execution_started")

    assert len(bus.published) == 1
    event_type, payload, stream = bus.published[0]
    assert event_type == RunEventName.STATUS_CHANGED.value == "run.status_changed"
    assert stream == producer.RUN_EVENT_STREAM == "sparkle_events"
    assert payload["event_type"] == "run.status_changed"
    assert payload["execution_intent_id"] == str(intent.id)
    assert payload["user_id"] == str(user.id)
    assert payload["task_id"] == str(intent.task_id)
    assert payload["milestone"] == "execution_started"
    assert payload["run"]["to_status"] == RunStatus.EXECUTING.value
    assert payload["run"]["step"]["ordinal"] == 1
    assert payload["run"]["step"]["steps_total"] == 4


async def test_milestone_ordinals_form_closed_progression(db_session, monkeypatch):
    """里程碑→绝对序号封闭递增（UI「正在执行 2/4」语义）。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    bus = _CaptureBus()
    monkeypatch.setattr(producer, "event_bus", bus)

    for milestone in ("execution_started", "tool_in_use", "producing_output", "finishing"):
        await producer.publish_execution_step_event(intent, milestone)

    ordinals = [p[1]["run"]["step"]["ordinal"] for p in bus.published]
    assert ordinals == [1, 2, 3, 4]
    stages = [p[1]["run"]["step"]["stage"] for p in bus.published]
    assert stages == ["openclaw_start", "openclaw_tool", "openclaw_output", "openclaw_finish"]


async def test_unknown_milestone_is_skipped(db_session, monkeypatch):
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    bus = _CaptureBus()
    monkeypatch.setattr(producer, "event_bus", bus)

    await producer.publish_execution_step_event(intent, "not_a_milestone")
    assert bus.published == []


async def test_publish_never_raises(db_session, monkeypatch):
    """钩子永不抛出：bus 彻底故障也只记日志，执行链守卫零影响。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    monkeypatch.setattr(producer, "event_bus", _CaptureBus(fail=True))

    await producer.publish_execution_step_event(intent, "execution_started")  # 不抛即通过


async def test_once_per_intent_milestone(db_session, monkeypatch):
    """进程内流量消减：同 intent+milestone 只发一次；跨 intent 独立。

    （正确性锚在消费侧幂等；本测试只钉流量语义。）
    """
    user = await _make_user(db_session)
    intent_a = await _make_intent(db_session, user)
    intent_b = await _make_intent(db_session, user)
    bus = _CaptureBus()
    monkeypatch.setattr(producer, "event_bus", bus)

    for _ in range(3):  # tool/assistant 流逐帧触发的真实形状
        await producer.publish_execution_step_event(intent_a, "tool_in_use")
    await producer.publish_execution_step_event(intent_b, "tool_in_use")

    assert len(bus.published) == 2
    assert {p[1]["execution_intent_id"] for p in bus.published} == {str(intent_a.id), str(intent_b.id)}


async def test_intent_id_typed_as_uuid_safe(db_session, monkeypatch):
    """防御：intent.id 为 UUID 对象时 str 化正常（生产形状）。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    assert isinstance(intent.id, uuid4().__class__)
    bus = _CaptureBus()
    monkeypatch.setattr(producer, "event_bus", bus)
    await producer.publish_execution_step_event(intent, "finishing")
    assert bus.published[0][1]["run"]["step"]["ordinal"] == 4
