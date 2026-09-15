from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.cache import cache_service
from app.models.aurora_stage20 import RoutingDecisionLog
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
async def test_force_reset_caps_confidence_and_writes_audit_log(
    db_session, test_user, monkeypatch
) -> None:
    await _enable_live(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)

    state = await tracker.force_reset(
        test_user.id, SRLPhase.PERFORMANCE, "manual override"
    )

    assert state.confidence == 0.8
    assert "force_reset:manual_override" in state.transition_evidence_ids

    row = (
        await db_session.execute(
            select(RoutingDecisionLog).where(
                RoutingDecisionLog.user_id == test_user.id,
                RoutingDecisionLog.decision_type == "aurora_srl_force_reset",
            )
        )
    ).scalar_one()
    assert row.decision_payload["justification"] == "manual override"
    assert row.decision_payload["confidence"] == 0.8


@pytest.mark.asyncio
async def test_force_reset_requires_non_blank_justification(
    db_session, test_user, monkeypatch
) -> None:
    await _enable_live(monkeypatch)
    tracker = SRLPhaseTrackerService(db_session)

    with pytest.raises(ValueError):
        await tracker.force_reset(test_user.id, SRLPhase.PERFORMANCE, "   ")
