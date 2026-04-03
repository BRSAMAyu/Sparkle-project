from __future__ import annotations

import pytest

from app.services.routing_profile_service import RoutingProfileService


@pytest.mark.asyncio
async def test_routing_profile_service_returns_defaults_for_new_user(db_session, test_user) -> None:
    profile = await RoutingProfileService(db_session).get_profile(test_user.id)

    assert profile == RoutingProfileService.DEFAULT_PROFILE


@pytest.mark.asyncio
async def test_routing_profile_service_slowly_lowers_threshold_after_execution_miss(db_session, test_user) -> None:
    service = RoutingProfileService(db_session)

    for _ in range(20):
        profile = await service.record_session_outcome(
            test_user.id,
            route_mode="execution_first",
            execution_suggestion_ignored=True,
        )

    assert profile["procrastination_threshold"] < RoutingProfileService.DEFAULT_PROFILE["procrastination_threshold"]
    assert profile["procrastination_threshold"] > RoutingProfileService.MIN_VALUE
