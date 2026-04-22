from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.cache import cache_service
from app.services.aurora_stage29_srl_kill_switch_service import (
    AuroraStage29SRLKillSwitchService,
)
from app.services.srl_phase_tracker_service import SRLPhaseTrackerService


async def _enable_live(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    cache_service._local_cache.clear()
    await AuroraStage29SRLKillSwitchService().ordered_startup("live")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "evidence_id",
    ["task:1", "plan:abc-123", "reflection:2026-04-22T09:00:00", str(uuid4())],
)
async def test_tracker_accepts_valid_evidence_ids(
    db_session, test_user, monkeypatch, evidence_id: str
) -> None:
    await _enable_live(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)

    state = await tracker.handle_transition_event(
        {
            "event_type": "srl.phase.transition",
            "user_id": str(test_user.id),
            "trigger_event_type": "plan.created",
            "evidence_id": evidence_id,
        }
    )

    assert state is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("evidence_id", ["task-1", "plan created", "bad/slug", "??"])
async def test_tracker_rejects_invalid_evidence_ids(
    db_session, test_user, monkeypatch, evidence_id: str
) -> None:
    await _enable_live(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)

    with pytest.raises(ValueError):
        await tracker.handle_transition_event(
            {
                "event_type": "srl.phase.transition",
                "user_id": str(test_user.id),
                "trigger_event_type": "plan.created",
                "evidence_id": evidence_id,
            }
        )
