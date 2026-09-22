"""B4-INBOX 回归：Aurora 确认队列 → notification-center 数据桥。

覆盖三面：
1. 桥接服务（AuroraConfirmBridgeService）：pending 卡投影 + 未处理计数；
2. notification-center 合并（source_type=aurora_confirm）+ 派生项 no-op；
3. 端点：aurora-confirm-action 委托既有确认 API、pending-count 徽标计数。

红-绿证明：修复前 notification-center 无 aurora_confirm 源（400）、
无动作端点（404）、控制面/计数端点不存在——新增行为全部为增量面。
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.v1.notification_center as notification_center_module
from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.unified_notification import UnifiedNotificationResponse
from app.services.aurora_confirm_bridge_service import (
    AURORA_CONFIRM_SOURCE_TYPE,
    AuroraConfirmBridgeService,
)
from app.services.notification_center_service import NotificationCenterService


def _card(card_id: str = "claim-1", **overrides) -> dict:
    payload = {
        "id": card_id,
        "title": "我注意到你最近在晚上复习",
        "statement": "我有一个判断需要你确认。",
        "confidence": 0.72,
        "confidence_label": "72%",
        "status": "candidate",
        "needs_confirmation": True,
        "evidence_summary": "证据：最近 3 天任务都排在晚上。",
        "plan_id": None,
        "source": None,
        "last_observed_at": "2026-09-20T10:00:00",
        "trial_expires_at": None,
    }
    payload.update(overrides)
    return payload


class _FakeCalibrationService:
    """替换真实校准卡服务，隔离 DB；返回可辨识的固定卡面。"""

    calls: list[dict] = []

    def __init__(self, db, redis=None):
        self.db = db
        self.redis = redis

    async def list_cards(self, *, user_id, plan_id=None):
        self.calls.append({"user_id": user_id, "plan_id": plan_id})
        return {"items": [_card()], "surface": {"state": "needs_confirmation"}}

    async def respond(self, *, user_id, card_id, response, reason=None, corrected_assumption=None):
        self.calls.append(
            {
                "user_id": user_id,
                "card_id": card_id,
                "response": response,
                "reason": reason,
                "corrected_assumption": corrected_assumption,
            }
        )
        return {"status": "ok", "card": _card(card_id, status="confirmed", needs_confirmation=False)}


# ---------- 1. bridge service ----------


@pytest.mark.asyncio
async def test_pending_cards_projects_calibration_cards(monkeypatch):
    monkeypatch.setattr(
        "app.services.aurora_confirm_bridge_service.AuroraCalibrationCardService",
        _FakeCalibrationService,
    )
    bridge = AuroraConfirmBridgeService(MagicMock())
    user_id = uuid4()

    cards = await bridge.pending_cards(user_id=user_id)

    assert len(cards) == 1
    assert cards[0]["id"] == "claim-1"


@pytest.mark.asyncio
async def test_pending_cards_swallow_calibration_failures(monkeypatch):
    class _Broken(_FakeCalibrationService):
        async def list_cards(self, *, user_id, plan_id=None):
            raise RuntimeError("prefs unavailable")

    monkeypatch.setattr(
        "app.services.aurora_confirm_bridge_service.AuroraCalibrationCardService",
        _Broken,
    )
    bridge = AuroraConfirmBridgeService(MagicMock())

    assert await bridge.pending_cards(user_id=uuid4()) == []


def test_bridge_to_unified_mapping():
    unified = AuroraConfirmBridgeService(MagicMock()).to_unified(_card())

    assert isinstance(unified, UnifiedNotificationResponse)
    assert unified.id == "claim-1"
    assert unified.source_type == AURORA_CONFIRM_SOURCE_TYPE == "aurora_confirm"
    assert unified.type == "aurora_confirm"
    assert unified.priority == "high"
    assert unified.is_read is False
    assert unified.read_at is None
    assert unified.title == "我注意到你最近在晚上复习"
    assert unified.metadata["needs_confirmation"] is True
    assert unified.metadata["confidence_label"] == "72%"


def test_bridge_to_unified_defaults_and_priority():
    unified = AuroraConfirmBridgeService(MagicMock()).to_unified(
        _card("claim-2", title="", statement="", needs_confirmation=False, last_observed_at=None)
    )

    assert unified.priority == "medium"
    assert unified.title  # non-empty fallback
    assert unified.content  # non-empty fallback
    assert unified.created_at is not None


def test_count_visible_from_inferred_pure_logic():
    inferred = {
        "self_model": {
            "known_assumptions": [
                {"id": "a", "status": "candidate", "confidence": 0.5},  # visible
                {"id": "b", "needs_confirmation": True},  # visible
                {"id": "c", "status": "confirmed"},  # handled
                {"id": "d", "status": "trial"},  # never visible
                {"id": "e", "suppressed_by_user": True, "needs_confirmation": True},
                {"id": "", "needs_confirmation": True},  # id-less junk
            ]
        }
    }

    assert AuroraConfirmBridgeService.count_visible_from_inferred(inferred) == 2


@pytest.mark.asyncio
async def test_pending_count_reads_preferences_without_writes(monkeypatch):
    class _FakePrefs:
        inferred = {
            "self_model": {
                "known_assumptions": [
                    {"id": "a", "needs_confirmation": True},
                    {"id": "b", "status": "confirmed"},
                ]
            }
        }

    class _FakePreferenceService:
        def __init__(self, db, redis=None):
            pass

        async def get_preferences(self, user_id):
            return _FakePrefs()

    db = MagicMock()
    monkeypatch.setattr(
        "app.services.personalization.preference_service.PreferenceService",
        _FakePreferenceService,
    )

    assert await AuroraConfirmBridgeService(db).pending_count(user_id=uuid4()) == 1
    db.commit.assert_not_called()
    db.execute.assert_not_called()


# ---------- 2. notification-center merge ----------


@pytest.mark.asyncio
async def test_unified_list_includes_aurora_confirm_items(monkeypatch):
    service = NotificationCenterService(MagicMock())

    async def _fake_db_scalars(*args, **kwargs):
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result

    service.db.execute = AsyncMock(side_effect=_fake_db_scalars)

    async def _fake_aurora(user_id):
        return [AuroraConfirmBridgeService(MagicMock()).to_unified(_card())]

    monkeypatch.setattr(service, "_load_aurora_confirm_notifications", _fake_aurora)

    unified = await service.get_unified_notifications(user_id=uuid4())

    aurora_items = [n for n in unified if n.source_type == "aurora_confirm"]
    assert len(aurora_items) == 1
    assert aurora_items[0].id == "claim-1"


@pytest.mark.asyncio
async def test_unified_list_keeps_aurora_items_when_unread_only(monkeypatch):
    service = NotificationCenterService(MagicMock())

    async def _fake_db_scalars(*args, **kwargs):
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result

    service.db.execute = AsyncMock(side_effect=_fake_db_scalars)

    async def _fake_aurora(user_id):
        return [AuroraConfirmBridgeService(MagicMock()).to_unified(_card())]

    monkeypatch.setattr(service, "_load_aurora_confirm_notifications", _fake_aurora)

    unified = await service.get_unified_notifications(user_id=uuid4(), unread_only=True)

    assert any(n.source_type == "aurora_confirm" for n in unified)


@pytest.mark.asyncio
async def test_unified_list_survives_aurora_bridge_failure(monkeypatch):
    service = NotificationCenterService(MagicMock())

    async def _fake_db_scalars(*args, **kwargs):
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result

    service.db.execute = AsyncMock(side_effect=_fake_db_scalars)

    async def _broken(self, *, user_id, plan_id=None):
        raise RuntimeError("bridge down")

    monkeypatch.setattr(AuroraConfirmBridgeService, "pending_cards", _broken)

    unified = await service.get_unified_notifications(user_id=uuid4())

    assert all(n.source_type != "aurora_confirm" for n in unified)


@pytest.mark.asyncio
async def test_mark_read_and_delete_are_noop_for_aurora_items():
    service = NotificationCenterService(MagicMock())

    assert await service.mark_notification_read(uuid4(), uuid4(), "aurora_confirm") is True
    assert await service.delete_notification(uuid4(), uuid4(), "aurora_confirm") is True
    service.db.execute.assert_not_called()


# ---------- 3. endpoints ----------


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(notification_center_module, "AuroraCalibrationCardService", _FakeCalibrationService)

    class _FakeCenterService:
        def __init__(self, db):
            self.db = db

        async def get_unified_notifications(self, user_id, skip=0, limit=50, unread_only=False, source_type=None):
            return []

        async def mark_notification_read(self, user_id, notification_id, notification_type):
            return True

        async def delete_notification(self, user_id, notification_id, notification_type):
            return True

    monkeypatch.setattr(notification_center_module, "NotificationCenterService", _FakeCenterService)

    app = FastAPI()
    app.include_router(notification_center_module.router)

    async def _override_get_db():
        yield MagicMock(spec=AsyncSession)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())

    with TestClient(app) as test_client:
        yield test_client


def test_aurora_confirm_action_delegates_to_existing_respond_api(client):
    resp = client.post(
        "/notification-center/notifications/claim-1/aurora-confirm-action",
        json={"action": "confirm"},
    )

    assert resp.status_code == 200
    call = _FakeCalibrationService.calls[-1]
    assert call["response"] == "confirm"
    assert call["card_id"] == "claim-1"


def test_aurora_confirm_action_passes_correction_payload(client):
    resp = client.post(
        "/notification-center/notifications/claim-1/aurora-confirm-action",
        json={
            "action": "incorrect",
            "reason": "我通常在早上复习",
            "corrected_assumption": "我在早上复习",
        },
    )

    assert resp.status_code == 200
    call = _FakeCalibrationService.calls[-1]
    assert call["response"] == "incorrect"
    assert call["reason"] == "我通常在早上复习"
    assert call["corrected_assumption"] == "我在早上复习"


def test_aurora_confirm_action_rejects_unknown_action(client):
    resp = client.post(
        "/notification-center/notifications/claim-1/aurora-confirm-action",
        json={"action": "maybe"},
    )

    assert resp.status_code == 422


def test_aurora_confirm_source_type_is_accepted(client):
    resp = client.get(
        "/notification-center/notifications",
        params={"source_type": "aurora_confirm"},
    )

    assert resp.status_code == 200


def test_invalid_source_type_still_rejected(client):
    resp = client.get(
        "/notification-center/notifications",
        params={"source_type": "aurora"},
    )

    assert resp.status_code == 400


def test_aurora_mark_read_is_accepted_noop(client):
    resp = client.put(
        f"/notification-center/notifications/{uuid4()}/read",
        params={"notification_type": "aurora_confirm"},
    )

    assert resp.status_code == 200


def test_aurora_pending_count_endpoint(monkeypatch):
    import app.api.v1.aurora as aurora_module

    async def _fake_pending_count(self, *, user_id):
        return 3

    monkeypatch.setattr(AuroraConfirmBridgeService, "pending_count", _fake_pending_count)

    app = FastAPI()
    app.include_router(aurora_module.router)

    async def _override_get_db():
        yield MagicMock(spec=AsyncSession)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())

    with TestClient(app) as test_client:
        resp = test_client.get("/aurora/calibration-cards/pending-count")

    assert resp.status_code == 200
    assert resp.json() == {"pending_count": 3}
