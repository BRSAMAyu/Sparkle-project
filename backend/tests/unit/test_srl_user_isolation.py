from __future__ import annotations

import subprocess
import sys
from uuid import uuid4
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.cache import cache_service
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter
from app.services.aurora_stage29_srl_kill_switch_service import AuroraStage29SRLKillSwitchService
from app.services.srl_phase_tracker_service import SRLPhaseTrackerService
from app.services.srl_phase_types import SRLPhase


REPO_ROOT = Path(__file__).resolve().parents[3]


async def _enable_live(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    cache_service._local_cache.clear()
    await AuroraStage29SRLKillSwitchService().ordered_startup("live")


@pytest.mark.asyncio
async def test_tracker_reads_only_target_user_state(db_session, test_user, monkeypatch) -> None:
    await _enable_live(monkeypatch)
    other_user = User(username="iso_other", email="iso_other@example.com", hashed_password="hashed")
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    tracker = SRLPhaseTrackerService(db_session)
    await tracker.force_reset(test_user.id, SRLPhase.FORETHOUGHT, "seed")
    await tracker.force_reset(other_user.id, SRLPhase.SELF_REFLECTION, "seed")

    assert (await tracker.get_current_phase(test_user.id)).current_phase == SRLPhase.FORETHOUGHT


@pytest.mark.asyncio
async def test_tracker_force_reset_does_not_write_other_user(db_session, test_user, monkeypatch) -> None:
    await _enable_live(monkeypatch)
    other_user = User(username="iso_other_two", email="iso_other_two@example.com", hashed_password="hashed")
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)
    tracker = SRLPhaseTrackerService(db_session)

    await tracker.force_reset(test_user.id, SRLPhase.PERFORMANCE, "seed")

    other_state = await tracker.get_current_phase(other_user.id)
    assert other_state.current_phase == SRLPhase.UNKNOWN


@pytest.mark.asyncio
async def test_tracker_loads_only_target_user_traits(db_session, test_user, monkeypatch) -> None:
    await _enable_live(monkeypatch)
    other_user = User(username="iso_other_three", email="iso_other_three@example.com", hashed_password="hashed")
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)
    db_session.add_all(
        [
            UserPreferencesCenter(
                user_id=test_user.id,
                explicit={},
                inferred={},
                traits_prior={"conscientiousness": {"value": 0.8, "confidence": 0.2, "source": "merged"}},
            ),
            UserPreferencesCenter(
                user_id=other_user.id,
                explicit={},
                inferred={},
                traits_prior={"conscientiousness": {"value": -0.8, "confidence": 0.2, "source": "merged"}},
            ),
        ]
    )
    await db_session.commit()

    state = await SRLPhaseTrackerService(db_session).get_current_phase(test_user.id)
    assert state.current_phase == SRLPhase.FORETHOUGHT


def test_user_isolation_guard_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "stage29" / "check_srl_user_isolation.py")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
