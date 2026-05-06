"""Unit tests for NudgeService per-channel delivery resolution (QA-P1-19).

Covers _resolve_channel() logic: push / in_app / silent decision-making
based on Spine NotificationDirective, and handle_nudge_triggered behavior
for each channel type.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.signals.types import NotificationDirective


def _make_directive(channel: str = "push") -> NotificationDirective:
    return NotificationDirective(
        directive_id="dir_1",
        policy_decision_id="pd_1",
        channel=channel,
    )


def _patch_cache_and_spine(directive=None, has_redis=True, spine_exc=None):
    """Helper to patch cache_service and SpineOrchestrator for _resolve_channel tests."""
    class Patcher:
        def __init__(self):
            self.cache_patcher = None
            self.spine_patcher = None
            self.mock_cache = None
            self.mock_spine_cls = None

        def __enter__(self):
            self.mock_cache = MagicMock()
            self.mock_cache.redis = MagicMock() if has_redis else None

            spine_instance = AsyncMock()
            spine_instance.get_notification_directive = AsyncMock(return_value=directive)

            self.mock_spine_cls = MagicMock(return_value=spine_instance)
            if spine_exc:
                self.mock_spine_cls = MagicMock(side_effect=spine_exc)

            self.cache_patcher = patch("app.core.cache.cache_service", self.mock_cache)
            self.spine_patcher = patch("app.signals.spine_orchestrator.SpineOrchestrator", self.mock_spine_cls)

            self.cache_patcher.start()
            self.spine_patcher.start()
            return self

        def __exit__(self, *args):
            self.cache_patcher.stop()
            self.spine_patcher.stop()

    return Patcher()


class TestResolveChannel:
    """Tests for NudgeService._resolve_channel()."""

    @pytest.mark.asyncio
    async def test_push_channel_from_directive(self):
        from app.services.nudge_service import NudgeService

        db = MagicMock()
        service = NudgeService(db)

        with _patch_cache_and_spine(directive=_make_directive("push")):
            result = await service._resolve_channel("user-1")
            assert result == "push"

    @pytest.mark.asyncio
    async def test_in_app_channel_from_directive(self):
        from app.services.nudge_service import NudgeService

        db = MagicMock()
        service = NudgeService(db)

        with _patch_cache_and_spine(directive=_make_directive("in_app")):
            result = await service._resolve_channel("user-1")
            assert result == "in_app"

    @pytest.mark.asyncio
    async def test_silent_channel_from_directive(self):
        from app.services.nudge_service import NudgeService

        db = MagicMock()
        service = NudgeService(db)

        with _patch_cache_and_spine(directive=_make_directive("silent")):
            result = await service._resolve_channel("user-1")
            assert result == "silent"

    @pytest.mark.asyncio
    async def test_default_push_when_no_directive(self):
        from app.services.nudge_service import NudgeService

        db = MagicMock()
        service = NudgeService(db)

        with _patch_cache_and_spine(directive=None):
            result = await service._resolve_channel("user-1")
            assert result == "push"

    @pytest.mark.asyncio
    async def test_default_push_when_no_redis(self):
        from app.services.nudge_service import NudgeService

        db = MagicMock()
        service = NudgeService(db)

        with _patch_cache_and_spine(has_redis=False):
            result = await service._resolve_channel("user-1")
            assert result == "push"

    @pytest.mark.asyncio
    async def test_default_push_on_exception(self):
        from app.services.nudge_service import NudgeService

        db = MagicMock()
        service = NudgeService(db)

        with _patch_cache_and_spine(spine_exc=Exception("redis connection refused")):
            result = await service._resolve_channel("user-1")
            assert result == "push"

    @pytest.mark.asyncio
    async def test_default_push_on_invalid_channel(self):
        from app.services.nudge_service import NudgeService

        db = MagicMock()
        service = NudgeService(db)

        with _patch_cache_and_spine(directive=_make_directive("email")):
            result = await service._resolve_channel("user-1")
            assert result == "push"


class TestHandleNudgeTriggered:
    """Tests for handle_nudge_triggered routing across channels."""

    @pytest.mark.asyncio
    async def test_skips_when_no_user_id(self):
        from app.services.nudge_service import NudgeService

        db = MagicMock()
        service = NudgeService(db)
        service._create_in_app_notification = AsyncMock()

        await service.handle_nudge_triggered({"message": "hello"})
        service._create_in_app_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_no_message(self):
        from app.services.nudge_service import NudgeService

        db = MagicMock()
        service = NudgeService(db)
        service._create_in_app_notification = AsyncMock()

        await service.handle_nudge_triggered({"user_id": "u1"})
        service._create_in_app_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_channel_triggers_mobile_push(self):
        from app.services.nudge_service import NudgeService

        db = MagicMock()
        service = NudgeService(db)
        service._resolve_channel = AsyncMock(return_value="push")

        notification = MagicMock()
        notification.id = uuid.uuid4()
        service._create_in_app_notification = AsyncMock(return_value=notification)
        service._send_mobile_push = AsyncMock()

        await service.handle_nudge_triggered({
            "user_id": str(uuid.uuid4()),
            "type": "growth_nudge",
            "message": "Keep it up!",
            "context": {"plan_id": "p1"},
        })
        service._send_mobile_push.assert_called_once()

    @pytest.mark.asyncio
    async def test_in_app_channel_skips_mobile_push(self):
        from app.services.nudge_service import NudgeService

        db = MagicMock()
        service = NudgeService(db)
        service._resolve_channel = AsyncMock(return_value="in_app")

        notification = MagicMock()
        notification.id = uuid.uuid4()
        service._create_in_app_notification = AsyncMock(return_value=notification)
        service._send_mobile_push = AsyncMock()

        await service.handle_nudge_triggered({
            "user_id": str(uuid.uuid4()),
            "type": "gentle_reminder",
            "message": "You have tasks waiting",
            "context": {},
        })
        service._create_in_app_notification.assert_called_once()
        service._send_mobile_push.assert_not_called()

    @pytest.mark.asyncio
    async def test_silent_channel_skips_notification_and_push(self):
        from app.services.nudge_service import NudgeService

        db = MagicMock()
        service = NudgeService(db)
        service._resolve_channel = AsyncMock(return_value="silent")
        service._create_in_app_notification = AsyncMock(return_value=None)
        service._send_mobile_push = AsyncMock()

        await service.handle_nudge_triggered({
            "user_id": str(uuid.uuid4()),
            "type": "background_signal",
            "message": "Silent update",
            "context": {},
        })
        service._create_in_app_notification.assert_called_once()
        service._send_mobile_push.assert_not_called()

    @pytest.mark.asyncio
    async def test_silent_notification_created_with_none(self):
        """When silent, _create_in_app_notification returns None (no DB record)."""
        from app.services.nudge_service import NudgeService

        db = MagicMock()
        service = NudgeService(db)
        user_id = str(uuid.uuid4())

        result = await service._create_in_app_notification(
            user_id=user_id,
            nudge_type="test",
            message="msg",
            context={},
            channel="silent",
        )
        assert result is None
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_passes_correct_channel_to_notification(self):
        """Notification creation receives the resolved channel string."""
        from app.services.nudge_service import NudgeService

        db = MagicMock()
        service = NudgeService(db)
        service._resolve_channel = AsyncMock(return_value="in_app")

        notification = MagicMock()
        notification.id = uuid.uuid4()
        service._create_in_app_notification = AsyncMock(return_value=notification)
        service._send_mobile_push = AsyncMock()

        await service.handle_nudge_triggered({
            "user_id": "u1",
            "type": "test",
            "message": "msg",
            "context": {},
        })

        call_args = service._create_in_app_notification.call_args
        assert call_args[0][4] == "in_app"  # channel is 5th positional arg
