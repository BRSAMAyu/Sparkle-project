from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from app.api.v1.auth import register
from app.schemas.plan import PlanCreate
from app.schemas.user import UserRegister
from app.services.plan_service import PlanService
from app.services.stage33_journey_event_service import Stage33JourneyEventService


def _build_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/auth/register",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }
    )


@pytest.mark.asyncio
async def test_stage33_journey_event_service_publishes_shadow_event_with_audit_metadata() -> None:
    with (
        patch(
            "app.services.stage33_journey_event_service.AuroraStage33KillSwitchService.summary",
            AsyncMock(
                return_value={
                    "mode": "shadow",
                    "social": "shadow",
                    "srl": "shadow",
                    "wm_prompt": "shadow",
                    "events": "shadow",
                }
            ),
        ),
        patch(
            "app.services.stage33_journey_event_service.event_bus_reliable.publish",
            AsyncMock(return_value="1-0"),
        ) as publish_mock,
    ):
        result = await Stage33JourneyEventService.publish(
            "user.registered",
            {"user_id": "u-1", "metadata": {"registration_source": "email"}},
        )

    assert result == "1-0"
    publish_mock.assert_awaited_once()
    event_type, payload = publish_mock.await_args.args
    assert event_type == "user.registered"
    assert payload["event_type"] == "user.registered"
    assert payload["stage33_mode"] == "shadow"
    assert payload["metadata"]["stage"] == "stage33"
    assert payload["metadata"]["stage33_mode"] == "shadow"


@pytest.mark.asyncio
async def test_stage33_journey_event_service_skips_when_events_mode_is_off() -> None:
    with (
        patch(
            "app.services.stage33_journey_event_service.AuroraStage33KillSwitchService.summary",
            AsyncMock(
                return_value={
                    "mode": "off",
                    "social": "off",
                    "srl": "off",
                    "wm_prompt": "off",
                    "events": "off",
                }
            ),
        ),
        patch(
            "app.services.stage33_journey_event_service.event_bus_reliable.publish",
            AsyncMock(),
        ) as publish_mock,
    ):
        result = await Stage33JourneyEventService.publish(
            "plan.created",
            {"plan_id": "p-1"},
        )

    assert result is None
    publish_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_publishes_stage33_user_registered_event(db_session) -> None:
    request = _build_request()
    payload = UserRegister(
        username="stage33_user",
        email="stage33_user@example.com",
        password="securepass",
        nickname="Stage33",
        accepted_tos=True,
        accepted_privacy=True,
    )

    with (
        patch("app.api.v1.auth.cache_service.set", AsyncMock()),
        patch(
            "app.api.v1.auth._issue_auth_tokens",
            AsyncMock(return_value={"access_token": "a", "refresh_token": "r"}),
        ),
        patch("app.api.v1.auth.auth_audit_service.schedule_log"),
        patch(
            "app.api.v1.auth.Stage33JourneyEventService.publish",
            AsyncMock(return_value="1-0"),
        ) as publish_mock,
        patch("app.core.celery_tasks.send_verification_email_task", MagicMock(delay=MagicMock())),
    ):
        result = await register(request=request, data=payload, db=db_session)

    assert result["user"].username == "stage33_user"
    publish_mock.assert_awaited_once()
    event_type, message = publish_mock.await_args.args
    assert event_type == "user.registered"
    assert message["event_type"] == "user.registered"
    assert message["user_id"]
    assert message["registration_source"] == "email"
    assert message["metadata"]["nickname"] == "Stage33"


@pytest.mark.asyncio
async def test_plan_service_create_publishes_stage33_plan_created_event(db_session, test_user) -> None:
    payload = PlanCreate(
        name="Stage33 计划",
        type="growth",
        description="补事件流",
        daily_available_minutes=45,
    )

    with (
        patch("app.services.plan_service._sync_plan_card_projection", AsyncMock()),
        patch(
            "app.services.plan_quota_service.PlanQuotaService",
        ) as quota_service_cls,
        patch(
            "app.services.plan_service.Stage33JourneyEventService.publish",
            AsyncMock(return_value="1-0"),
        ) as publish_mock,
    ):
        quota_service_cls.return_value.get_quota_status = AsyncMock(
            return_value=SimpleNamespace(used=0)
        )
        plan = await PlanService.create(
            db=db_session,
            obj_in=payload,
            user_id=test_user.id,
            skip_quota_check=True,
        )

    assert str(plan.user_id) == str(test_user.id)
    publish_mock.assert_awaited_once()
    event_type, message = publish_mock.await_args.args
    assert event_type == "plan.created"
    assert message["event_type"] == "plan.created"
    assert message["user_id"] == str(test_user.id)
    assert message["plan_id"] == str(plan.id)
    assert message["source"] == "plan_service.create"
