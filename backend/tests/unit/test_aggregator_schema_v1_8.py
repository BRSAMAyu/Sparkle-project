from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.schemas.foresight import ForesightSnapshot
from app.state_aggregator.service import StateAggregatorService
from app.services.predictive_service import PredictiveService


def _snapshot(*, hint_text: str | None = "你最近学习节奏低于常态，先把目标缩成 15 分钟再启动。") -> ForesightSnapshot:
    from app.schemas.foresight import AttractorState, ForesightHint

    now = datetime(2026, 4, 21, 9, 0, 0)
    hints = ()
    if hint_text is not None:
        hints = (
            ForesightHint(
                hint_id="hint-1",
                dim="study_pace",
                message=hint_text,
                z_score=-3.0,
                confidence=0.8,
                generated_at=now,
                template_id="study_pace_below",
            ),
        )
    return ForesightSnapshot(
        existing_predictions={},
        attractors={
            "study_pace": AttractorState(
                dim="study_pace",
                baseline=1.0,
                variability=0.2,
                recovery_rate=0.1,
                confidence=0.8,
                updated_at=now,
            )
        },
        deviations=(),
        hints=hints,
        generated_at=now,
        user_id=str(uuid4()),
    )


@pytest.mark.asyncio
async def test_aggregator_schema_v1_8_reports_foresight_hint(db_session, monkeypatch) -> None:
    monkeypatch.setattr(
        PredictiveService,
        "build_foresight_snapshot",
        AsyncMock(return_value=_snapshot()),
    )

    state = await StateAggregatorService(db_session).get_user_state(
        uuid4(),
        required_fields=("foresight_hint",),
    )

    assert state.schema_version == "user_state.v1.10"
    assert state.foresight_hint is not None
    assert state.foresight_hint.value.hint_text is not None


@pytest.mark.asyncio
async def test_aggregator_foresight_hint_keeps_thirty_second_ttl(db_session, monkeypatch) -> None:
    monkeypatch.setattr(
        PredictiveService,
        "build_foresight_snapshot",
        AsyncMock(return_value=_snapshot()),
    )

    state = await StateAggregatorService(db_session).get_user_state(
        uuid4(),
        required_fields=("foresight_hint",),
    )

    assert state.foresight_hint is not None
    assert StateAggregatorService.FIELD_TTLS_SECONDS["foresight_hint"] == 30


@pytest.mark.asyncio
async def test_aggregator_foresight_hint_zero_state_when_no_live_hint(db_session, monkeypatch) -> None:
    monkeypatch.setattr(
        PredictiveService,
        "build_foresight_snapshot",
        AsyncMock(return_value=_snapshot(hint_text=None)),
    )

    state = await StateAggregatorService(db_session).get_user_state(
        uuid4(),
        required_fields=("foresight_hint",),
    )

    assert state.foresight_hint is not None
    assert state.foresight_hint.value.hint_text is None
    assert state.foresight_hint.value.deviation_count == 0
