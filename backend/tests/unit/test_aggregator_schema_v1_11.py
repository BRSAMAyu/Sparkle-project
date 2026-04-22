from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.state_aggregator.schema import (
    MetacognitionDimensionSummaryValue,
    MetacognitionProfileSummaryValue,
    StateFieldEnvelope,
    UserStateV1,
)
from app.state_aggregator.service import StateAggregatorService
from app.services.metacognition_service import MetacognitionService


def test_user_state_v1_11_exposes_metacognition_contract() -> None:
    state = UserStateV1(
        user_id="u-1",
        metacognition_profile=StateFieldEnvelope(
            value=MetacognitionProfileSummaryValue(
                items=(
                    MetacognitionDimensionSummaryValue(
                        dim="time_estimation_bias",
                        sample_size=20,
                        bias_mean=0.4,
                        trend="stable",
                    ),
                ),
            ),
            computed_at=datetime(2026, 4, 22, 10, 0, 0),
            source_snapshot_ids=("metacognition:time_estimation_bias",),
            freshness_seconds=0,
        ),
    )

    assert state.schema_version == "user_state.v1.12"
    assert state.metacognition_profile is not None
    assert state.metacognition_profile.value.items[0].dim == "time_estimation_bias"


@pytest.mark.asyncio
async def test_aggregator_builds_metacognition_profile_field(
    db_session, test_user, monkeypatch
) -> None:
    monkeypatch.setattr(
        MetacognitionService,
        "build_aggregator_summary",
        AsyncMock(
            return_value=MetacognitionProfileSummaryValue(
                items=(
                    MetacognitionDimensionSummaryValue(
                        dim="time_estimation_bias",
                        sample_size=24,
                        bias_mean=0.31,
                        trend="improving",
                    ),
                ),
            )
        ),
    )

    state = await StateAggregatorService(db_session).get_user_state(
        test_user.id,
        required_fields=("metacognition_profile",),
    )

    assert state.schema_version == "user_state.v1.12"
    assert state.metacognition_profile is not None
    assert state.metacognition_profile.value.items[0].sample_size == 24
