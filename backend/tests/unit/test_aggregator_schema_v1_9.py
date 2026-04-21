from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.user_preferences import UserPreferencesCenter
from app.state_aggregator.service import StateAggregatorService


@pytest.mark.asyncio
async def test_aggregator_schema_v1_9_exposes_traits_prior_summary(db_session) -> None:
    user_id = uuid4()
    db_session.add(
        UserPreferencesCenter(
            user_id=user_id,
            explicit={},
            inferred={},
            traits_prior={
                "conscientiousness": {
                    "value": 0.4,
                    "confidence": 0.12,
                    "evidence_count": 3,
                    "last_observed_at": "2026-04-21T10:00:00",
                    "source": "merged",
                }
            },
            trait_observation_state={"latest_evidence_ids": {"conscientiousness": "obs-1"}},
        )
    )
    await db_session.commit()

    state = await StateAggregatorService(db_session).get_user_state(user_id, required_fields=("traits_prior",))

    assert state.schema_version == "user_state.v1.9"
    assert state.traits_prior is not None
    assert state.traits_prior.value.items[0].dim == "conscientiousness"


@pytest.mark.asyncio
async def test_aggregator_traits_prior_keeps_thirty_second_ttl(db_session) -> None:
    state = await StateAggregatorService(db_session).get_user_state(uuid4(), required_fields=("traits_prior",))
    assert state.traits_prior is not None
    assert StateAggregatorService.FIELD_TTLS_SECONDS["traits_prior"] == 30


@pytest.mark.asyncio
async def test_aggregator_traits_prior_filters_low_confidence_dimensions(db_session) -> None:
    user_id = uuid4()
    db_session.add(
        UserPreferencesCenter(
            user_id=user_id,
            explicit={},
            inferred={},
            traits_prior={
                "openness": {
                    "value": 0.4,
                    "confidence": 0.09,
                    "evidence_count": 1,
                    "last_observed_at": "2026-04-21T10:00:00",
                    "source": "coldstart",
                }
            },
        )
    )
    await db_session.commit()

    state = await StateAggregatorService(db_session).get_user_state(user_id, required_fields=("traits_prior",))

    assert state.traits_prior is not None
    assert state.traits_prior.value.items == ()
