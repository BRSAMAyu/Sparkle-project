from __future__ import annotations

import pytest

from app.core.cache import cache_service
from app.models.user import User
from app.services.aurora_stage29_srl_kill_switch_service import (
    AuroraStage29SRLKillSwitchService,
)
from app.services.srl_phase_tracker_service import SRLPhaseTrackerService
from app.services.srl_phase_types import SRLPhase


async def _enable_live(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    cache_service._local_cache.clear()
    await AuroraStage29SRLKillSwitchService().ordered_startup("live")


@pytest.mark.asyncio
async def test_tracker_keeps_user_states_isolated(
    db_session, test_user, monkeypatch
) -> None:
    await _enable_live(monkeypatch)
    other_user = User(
        username="tracker_other",
        email="tracker_other@example.com",
        hashed_password="hashed",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)
    tracker = SRLPhaseTrackerService(db_session)

    await tracker.handle_transition_event(
        {
            "event_type": "srl.phase.transition",
            "user_id": str(test_user.id),
            "trigger_event_type": "task.started",
            "evidence_id": "task:u1",
        }
    )
    await tracker.handle_transition_event(
        {
            "event_type": "srl.phase.transition",
            "user_id": str(other_user.id),
            "trigger_event_type": "plan.created",
            "evidence_id": "plan:u2",
        }
    )

    assert (
        await tracker.get_current_phase(test_user.id)
    ).current_phase == SRLPhase.PERFORMANCE
    assert (
        await tracker.get_current_phase(other_user.id)
    ).current_phase == SRLPhase.FORETHOUGHT


@pytest.mark.asyncio
async def test_tracker_rejects_empty_user_id(db_session, monkeypatch) -> None:
    await _enable_live(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)

    with pytest.raises(ValueError):
        await tracker.handle_transition_event(
            {
                "event_type": "srl.phase.transition",
                "user_id": "",
                "trigger_event_type": "task.started",
                "evidence_id": "bad",
            }
        )


@pytest.mark.asyncio
async def test_tracker_concurrent_events_for_same_user_are_deterministic(
    db_session, test_user, monkeypatch
) -> None:
    await _enable_live(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)

    await tracker.handle_transition_event(
        {
            "event_type": "srl.phase.transition",
            "user_id": str(test_user.id),
            "trigger_event_type": "task.started",
            "evidence_id": "task:a",
        }
    )
    await tracker.handle_transition_event(
        {
            "event_type": "srl.phase.transition",
            "user_id": str(test_user.id),
            "trigger_event_type": "task.completed",
            "evidence_id": "task:b",
        }
    )

    final_state = await tracker.get_current_phase(test_user.id)
    assert final_state.current_phase == SRLPhase.SELF_REFLECTION
