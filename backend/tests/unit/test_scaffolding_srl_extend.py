from __future__ import annotations

import pytest

from app.core.cache import cache_service
from app.models.user_preferences import UserPreferencesCenter
from app.scaffolding.scaffolding_fsm import ScaffoldingFSM


def test_get_srl_phase_hint_defaults_to_unknown(db_session) -> None:
    assert ScaffoldingFSM(db_session).get_srl_phase_hint(None).value == "UNKNOWN"


@pytest.mark.asyncio
async def test_forethought_phase_raises_support_level_live(db_session, test_user) -> None:
    fsm = ScaffoldingFSM(db_session)
    state = await fsm.get_state(test_user.id)
    state.support_level = 2
    snapshot = fsm.snapshot(state, phase_value="FORETHOUGHT", consume_mode="live")
    assert snapshot["support_level"] == 3


@pytest.mark.asyncio
async def test_reflection_phase_raises_support_level_with_cap(db_session, test_user) -> None:
    fsm = ScaffoldingFSM(db_session)
    state = await fsm.get_state(test_user.id)
    state.support_level = 4
    snapshot = fsm.snapshot(state, phase_value="SELF_REFLECTION", consume_mode="live")
    assert snapshot["support_level"] == 4


@pytest.mark.asyncio
async def test_performance_phase_keeps_base_support_level(db_session, test_user) -> None:
    fsm = ScaffoldingFSM(db_session)
    state = await fsm.get_state(test_user.id)
    state.support_level = 3
    snapshot = fsm.snapshot(state, phase_value="PERFORMANCE", consume_mode="live")
    assert snapshot["support_level"] == 3


@pytest.mark.asyncio
async def test_shadow_mode_records_without_applying_adjustment(db_session, test_user) -> None:
    fsm = ScaffoldingFSM(db_session)
    state = await fsm.get_state(test_user.id)
    state.support_level = 2
    snapshot = fsm.snapshot(state, phase_value="FORETHOUGHT", consume_mode="shadow")
    assert snapshot["support_level"] == 2
    assert snapshot["srl_adjustment_applied"] is False


@pytest.mark.asyncio
async def test_initial_support_level_comes_from_traits(db_session, test_user, monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    db_session.add(
        UserPreferencesCenter(
            user_id=test_user.id,
            explicit={},
            inferred={},
            traits_prior={
                "conscientiousness": {
                    "value": 0.7,
                    "confidence": 0.2,
                    "source": "merged",
                }
            },
        )
    )
    await db_session.commit()

    state = await ScaffoldingFSM(db_session).get_state(test_user.id)

    assert state.support_level == 2
