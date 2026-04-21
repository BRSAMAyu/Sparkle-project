from __future__ import annotations

import pytest

from app.core.cache import cache_service
from app.services.aurora_stage29_srl_kill_switch_service import AuroraStage29SRLKillSwitchService
from app.services.srl_phase_tracker_service import SRLPhaseTrackerService
from app.services.srl_phase_types import SRLPhase


async def _enable_live(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    cache_service._local_cache.clear()
    await AuroraStage29SRLKillSwitchService().ordered_startup("live")


@pytest.mark.asyncio
async def test_tracker_handle_event_ignores_non_srl_messages(db_session, test_user, monkeypatch) -> None:
    await _enable_live(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)

    result = await tracker.handle_event({"event_type": "task.completed", "user_id": str(test_user.id)})

    assert result is None


@pytest.mark.asyncio
async def test_tracker_handle_event_consumes_transition_message(db_session, test_user, monkeypatch) -> None:
    await _enable_live(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)

    state = await tracker.handle_event(
        {
            "event_type": "srl.phase.transition",
            "user_id": str(test_user.id),
            "trigger_event_type": "task.started",
            "evidence_id": "task-1",
        }
    )

    assert state is not None
    assert state.current_phase == SRLPhase.PERFORMANCE


@pytest.mark.asyncio
async def test_tracker_handle_event_filters_self_published_non_transition_srl_events(db_session, test_user, monkeypatch) -> None:
    await _enable_live(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)

    state = await tracker.handle_event(
        {
            "event_type": "srl.phase.updated",
            "user_id": str(test_user.id),
            "trigger_event_type": "task.started",
            "evidence_id": "ignored",
        }
    )

    assert state is None


@pytest.mark.asyncio
async def test_tracker_handle_event_records_reflection_phase(db_session, test_user, monkeypatch) -> None:
    await _enable_live(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)

    await tracker.handle_event(
        {
            "event_type": "srl.phase.transition",
            "user_id": str(test_user.id),
            "trigger_event_type": "task.started",
            "evidence_id": "task-1",
        }
    )
    state = await tracker.handle_event(
        {
            "event_type": "srl.phase.transition",
            "user_id": str(test_user.id),
            "trigger_event_type": "task.completed",
            "evidence_id": "task-1",
        }
    )

    assert state is not None
    assert state.current_phase == SRLPhase.SELF_REFLECTION


@pytest.mark.asyncio
async def test_tracker_handle_event_accepts_published_at_for_lag_tracking(db_session, test_user, monkeypatch) -> None:
    await _enable_live(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)

    state = await tracker.handle_event(
        {
            "event_type": "srl.phase.transition",
            "user_id": str(test_user.id),
            "trigger_event_type": "plan.created",
            "evidence_id": "plan-1",
            "published_at": "2026-04-21T10:00:00+00:00",
        }
    )

    assert state is not None
    assert state.current_phase == SRLPhase.FORETHOUGHT
