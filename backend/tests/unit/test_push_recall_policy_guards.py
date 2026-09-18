"""Regression tests for recall push policy guards and None preference (P2')."""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.push_scheduler import _RECALL_QUEUE_PREFIX, PushScheduler


class _StubRedis:
    def __init__(self, keys: list[str], items: list[str]) -> None:
        self._keys = keys
        self._items = items
        self.deleted: list[str] = []

    async def scan_iter(self, match=None):
        for key in self._keys:
            yield key

    async def lrange(self, key, start, end):
        return self._items

    async def delete(self, key):
        self.deleted.append(key)


def _make_scheduler(monkeypatch, *, silent_during_focus: bool):
    db = AsyncMock()
    user = SimpleNamespace(id=uuid.uuid4(), push_preference=SimpleNamespace(last_push_time=None))
    db.get = AsyncMock(return_value=user)

    scheduler = PushScheduler(db, redis=_StubRedis([f"{_RECALL_QUEUE_PREFIX}{user.id}"], [json.dumps({"trigger_type": "task_not_started"})]))
    scheduler.push_service._send_push = AsyncMock()
    scheduler.notif_builder.check_cooldown_async = AsyncMock(return_value=False)
    scheduler.notif_builder.record_sent_async = AsyncMock()
    scheduler._get_spine_directive = AsyncMock(return_value=None)

    policy = SimpleNamespace(
        silent_during_focus=silent_during_focus,
        timezone="Asia/Shanghai",
        daily_cap=5,
        min_interval_minutes=120,
        preference_version="v1",
    )
    engine = SimpleNamespace(get_push_policy_profile=AsyncMock(return_value=policy))
    monkeypatch.setattr("app.services.push_scheduler.get_personalization_engine", lambda db_, redis_: engine)
    return scheduler, user


@pytest.mark.asyncio
async def test_recall_queue_blocks_send_when_policy_suppresses(monkeypatch):
    """P2': recall 处理必须复用推送策略守卫，不得绕过静默/专注模式。"""
    scheduler, user = _make_scheduler(monkeypatch, silent_during_focus=True)

    stats = await scheduler.process_recall_queue()

    assert stats["processed"] == 1
    assert stats["skipped_policy"] == 1
    assert stats["sent"] == 0
    scheduler.push_service._send_push.assert_not_called()
    assert scheduler.redis.deleted, "queue key should be cleaned up after skip"


@pytest.mark.asyncio
async def test_recall_queue_sends_when_policy_allows(monkeypatch):
    """P2' 对照：策略放行时 recall 照常发送。"""
    scheduler, user = _make_scheduler(monkeypatch, silent_during_focus=False)
    # 放行所有守卫
    scheduler.push_service._is_active_time = lambda policy: True
    scheduler.push_service._check_frequency_cap = AsyncMock(return_value=False)
    scheduler.push_service._check_schedule_and_quiet_hours = AsyncMock(return_value=False)

    stats = await scheduler.process_recall_queue()

    assert stats["sent"] == 1
    scheduler.push_service._send_push.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_push_tolerates_missing_push_preference(monkeypatch):
    """P2': 用户没有 PushPreference 行时 _send_push 不得 AttributeError。"""
    from app.services import push_service as push_service_mod
    from app.services.notification_service import NotificationService

    db = AsyncMock()
    db.add = MagicMock()
    service = push_service_mod.PushService(db)
    user = SimpleNamespace(id=uuid.uuid4(), push_preference=None, nickname="nick", username="user")
    monkeypatch.setattr(NotificationService, "create", AsyncMock())

    class _StubOptInService:
        def __init__(self, db_: object) -> None:
            pass

        async def get_or_create(self, user_id: uuid.UUID):
            return SimpleNamespace(enabled=True)

    monkeypatch.setattr(push_service_mod, "UserPushOptInService", _StubOptInService)

    await service._send_push(
        user,
        "recall",
        {"title": "t", "body": "b"},
        {"type": "recall"},
        SimpleNamespace(preference_version="v1", daily_cap=5),
    )

    db.commit.assert_awaited_once()
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_send_push_respects_aurora_opt_in_switch(monkeypatch):
    """P3': PushService 出口必须尊重 UserPushOptIn.enabled 总开关（默认不推）。"""
    from app.services import push_service as push_service_mod
    from app.services.notification_service import NotificationService

    db = AsyncMock()
    db.add = MagicMock()
    service = push_service_mod.PushService(db)
    user = SimpleNamespace(id=uuid.uuid4(), push_preference=SimpleNamespace(last_push_time=None), nickname="n", username="u")
    monkeypatch.setattr(NotificationService, "create", AsyncMock())

    class _StubOptInService:
        def __init__(self, db_: object) -> None:
            self.enabled_value = False

        async def get_or_create(self, user_id: uuid.UUID):
            return SimpleNamespace(enabled=self.enabled_value)

    stub = _StubOptInService(db)
    monkeypatch.setattr(push_service_mod, "UserPushOptInService", lambda db_: stub)

    await service._send_push(
        user,
        "memory",
        {"title": "t", "body": "b"},
        {"type": "memory"},
        SimpleNamespace(preference_version="v1", daily_cap=5),
    )
    assert NotificationService.create.await_count == 0, "opt-out 用户不得收到 PushService 推送"
    db.add.assert_not_called()

    stub.enabled_value = True
    await service._send_push(
        user,
        "memory",
        {"title": "t", "body": "b"},
        {"type": "memory"},
        SimpleNamespace(preference_version="v1", daily_cap=5),
    )
    assert NotificationService.create.await_count == 1
