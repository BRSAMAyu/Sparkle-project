from __future__ import annotations

from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest

from app.state_aggregator.schema import (
    AssociationPairValue,
    ChangePointItemValue,
    IdiographicSummaryValue,
    StateFieldEnvelope,
    UserStateV1,
)
from app.state_aggregator.service import StateAggregatorService
from app.services.idiographic_association_service import IdiographicAssociationService


def test_user_state_v1_12_exposes_idiographic_contract() -> None:
    state = UserStateV1(
        user_id="u-1",
        idiographic_summary=StateFieldEnvelope(
            value=IdiographicSummaryValue(
                top_associations=(
                    AssociationPairValue(
                        dim_pair="focus_duration_daily__study_pace",
                        dim_a="focus_duration_daily",
                        dim_b="study_pace",
                        correlation=0.42,
                        q_value=0.03,
                        confidence=0.71,
                        direction="positive_sync",
                        strength_label="中等",
                        rendered_text="在你最近 45 天的数据里，专注时长和学习节奏有同步变化的趋势（关联强度 中等）。这只是你数据中的模式，不代表因果关系。",
                        displayed=True,
                        density_insufficient=False,
                        sample_days=45,
                    ),
                ),
                change_points_30d=(
                    ChangePointItemValue(
                        dim="study_pace",
                        change_date=date(2026, 4, 1),
                        confidence=0.64,
                        rendered_text="在 2026-04-01 前后，你的学习节奏模式出现了明显变化。这是一个观察，不是评判。",
                    ),
                ),
                sample_days=45,
                confidence=0.71,
                disclaimer_text="这只是你数据中的模式，不代表因果关系。",
            ),
            computed_at=datetime(2026, 4, 22, 10, 0, 0),
            source_snapshot_ids=("idiographic:focus_duration_daily__study_pace",),
            freshness_seconds=0,
        ),
    )

    assert state.schema_version == "user_state.v1.12"
    assert state.idiographic_summary is not None
    assert state.idiographic_summary.value.top_associations[0].displayed is True
    assert state.idiographic_summary.value.disclaimer_text


@pytest.mark.asyncio
async def test_aggregator_builds_idiographic_summary_field(
    db_session, test_user, monkeypatch
) -> None:
    monkeypatch.setattr(
        IdiographicAssociationService,
        "build_aggregator_summary",
        AsyncMock(
            return_value=IdiographicSummaryValue(
                top_associations=(
                    AssociationPairValue(
                        dim_pair="focus_duration_daily__study_pace",
                        dim_a="focus_duration_daily",
                        dim_b="study_pace",
                        correlation=0.38,
                        q_value=0.04,
                        confidence=0.55,
                        direction="positive_sync",
                        strength_label="初步",
                        rendered_text="在你最近 45 天的数据里，专注时长和学习节奏有同步变化的趋势（关联强度 初步）。这只是你数据中的模式，不代表因果关系。",
                        displayed=True,
                        density_insufficient=False,
                        sample_days=41,
                    ),
                ),
                change_points_30d=(),
                sample_days=41,
                confidence=0.55,
                disclaimer_text="这只是你数据中的模式，不代表因果关系。",
            )
        ),
    )

    state = await StateAggregatorService(db_session).get_user_state(
        test_user.id,
        required_fields=("idiographic_summary",),
    )

    assert state.schema_version == "user_state.v1.12"
    assert state.idiographic_summary is not None
    assert state.idiographic_summary.value.top_associations[0].sample_days == 41
