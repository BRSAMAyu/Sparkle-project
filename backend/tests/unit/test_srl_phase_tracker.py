from __future__ import annotations

from datetime import timedelta
from time import perf_counter

import pytest
from sqlalchemy import select

from app.config import settings
from app.core.cache import cache_service
from app.models.srl_phase_state import SRLPhaseStateRecord
from app.models.user_preferences import UserPreferencesCenter
from app.services.aurora_stage29_srl_kill_switch_service import (
    AuroraStage29SRLKillSwitchService,
)
from app.services.srl_phase_tracker_service import SRLPhaseTrackerService
from app.services.srl_phase_types import SRLPhase


async def _enable_live_modes(monkeypatch) -> AuroraStage29SRLKillSwitchService:
    monkeypatch.setattr(cache_service, "redis", None)
    cache_service._local_cache.clear()
    service = AuroraStage29SRLKillSwitchService()
    await service.ordered_startup("live")
    return service


@pytest.mark.asyncio
async def test_tracker_coldstarts_from_traits(
    db_session, test_user, monkeypatch
) -> None:
    await _enable_live_modes(monkeypatch)
    db_session.add(
        UserPreferencesCenter(
            user_id=test_user.id,
            explicit={},
            inferred={},
            traits_prior={
                "conscientiousness": {
                    "value": 0.8,
                    "confidence": 0.2,
                    "evidence_count": 3,
                    "source": "merged",
                }
            },
        )
    )
    await db_session.commit()

    state = await SRLPhaseTrackerService(db_session).get_current_phase(test_user.id)

    assert state.current_phase == SRLPhase.FORETHOUGHT


@pytest.mark.asyncio
async def test_tracker_handles_task_started_transition(
    db_session, test_user, monkeypatch
) -> None:
    await _enable_live_modes(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)

    state = await tracker.handle_transition_event(
        {
            "event_type": "srl.phase.transition",
            "user_id": str(test_user.id),
            "trigger_event_type": "task.started",
            "evidence_id": "task:1",
        }
    )

    assert state is not None
    assert state.current_phase == SRLPhase.PERFORMANCE


@pytest.mark.asyncio
async def test_tracker_rejects_illegal_jump(db_session, test_user, monkeypatch) -> None:
    await _enable_live_modes(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)
    await tracker.force_reset(test_user.id, SRLPhase.FORETHOUGHT, "seed")

    state = await tracker.handle_transition_event(
        {
            "event_type": "srl.phase.transition",
            "user_id": str(test_user.id),
            "trigger_event_type": "task.feedback_submitted",
            "evidence_id": "feedback:1",
        }
    )

    assert state is not None
    assert state.current_phase == SRLPhase.FORETHOUGHT


@pytest.mark.asyncio
async def test_tracker_preserves_phase_started_at_for_self_loop(
    db_session, test_user, monkeypatch
) -> None:
    await _enable_live_modes(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)
    initial = await tracker.handle_transition_event(
        {
            "event_type": "srl.phase.transition",
            "user_id": str(test_user.id),
            "trigger_event_type": "plan.created",
            "evidence_id": "plan:1",
        }
    )
    looped = await tracker.handle_transition_event(
        {
            "event_type": "srl.phase.transition",
            "user_id": str(test_user.id),
            "trigger_event_type": "plan.created",
            "evidence_id": "plan:2",
        }
    )

    assert initial is not None and looped is not None
    assert looped.current_phase == SRLPhase.FORETHOUGHT
    assert looped.phase_started_at == initial.phase_started_at


@pytest.mark.asyncio
async def test_tracker_force_reset_overrides_phase(
    db_session, test_user, monkeypatch
) -> None:
    await _enable_live_modes(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)

    reset_state = await tracker.force_reset(
        test_user.id, SRLPhase.SELF_REFLECTION, "manual"
    )

    assert reset_state.current_phase == SRLPhase.SELF_REFLECTION
    assert "force_reset:manual" in reset_state.transition_evidence_ids
    assert reset_state.confidence == 0.8


@pytest.mark.asyncio
async def test_tracker_marks_inactive_users_unknown(
    db_session, test_user, monkeypatch
) -> None:
    await _enable_live_modes(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)
    await tracker.force_reset(test_user.id, SRLPhase.PERFORMANCE, "seed")

    record = (
        await db_session.execute(
            select(SRLPhaseStateRecord).where(
                SRLPhaseStateRecord.user_id == test_user.id
            )
        )
    ).scalar_one()
    record.updated_at = record.updated_at - timedelta(hours=25)
    await db_session.commit()
    cache_service._local_cache.clear()

    state = await tracker.get_current_phase(test_user.id)
    assert state.current_phase == SRLPhase.UNKNOWN


@pytest.mark.asyncio
async def test_tracker_persists_to_database(db_session, test_user, monkeypatch) -> None:
    await _enable_live_modes(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)

    await tracker.handle_transition_event(
        {
            "event_type": "srl.phase.transition",
            "user_id": str(test_user.id),
            "trigger_event_type": "task.started",
            "evidence_id": "task:7",
        }
    )

    record = (
        await db_session.execute(
            select(SRLPhaseStateRecord).where(
                SRLPhaseStateRecord.user_id == test_user.id
            )
        )
    ).scalar_one()
    assert record.current_phase == SRLPhase.PERFORMANCE.value


@pytest.mark.asyncio
async def test_tracker_handle_transition_event_p95_under_budget(
    db_session, test_user, monkeypatch
) -> None:
    await _enable_live_modes(monkeypatch)
    settings.AURORA_SRL_TRACKER_P95_MS_BUDGET = 20
    tracker = SRLPhaseTrackerService(db_session)
    latencies_ms: list[float] = []

    for index in range(25):
        started = perf_counter()
        await tracker.handle_transition_event(
            {
                "event_type": "srl.phase.transition",
                "user_id": str(test_user.id),
                "trigger_event_type": (
                    "task.started" if index % 2 == 0 else "task.completed"
                ),
                "evidence_id": f"event:{index}",
            }
        )
        latencies_ms.append((perf_counter() - started) * 1000)

    ordered = sorted(latencies_ms)
    p95 = ordered[max(0, int(len(ordered) * 0.95) - 1)]
    assert p95 <= settings.AURORA_SRL_TRACKER_P95_MS_BUDGET
