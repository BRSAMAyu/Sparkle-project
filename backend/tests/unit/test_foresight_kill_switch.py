from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.schemas.foresight import AttractorState, Deviation, ForesightHint
from app.services.aurora_stage27_foresight_kill_switch_service import AuroraStage27ForesightKillSwitchService
from app.services.jitai_trigger_service import JITAITrigger
from app.services.persdyn_attractor_service import PersDynAttractorService
from app.services.predictive_service import PredictiveService
from app.services.foresight_deviation_service import DeviationDetector


def _forecast():
    return type(
        "Forecast",
        (),
        {"to_dict": lambda self: {"next_active_time": "2026-04-22T09:00:00", "confidence": 0.8, "recommended_intervention": None, "risk_level": "low"}},
    )()


async def _configure(
    *,
    mode: str,
    attractor: str = "live",
    deviation: str = "live",
    jitai: str = "live",
) -> None:
    kill_switch = AuroraStage27ForesightKillSwitchService()
    await kill_switch.set_mode(mode)
    await kill_switch.set_feature_mode("attractor", attractor)
    await kill_switch.set_feature_mode("deviation", deviation)
    await kill_switch.set_feature_mode("jitai", jitai)


async def _build_snapshot(service: PredictiveService, monkeypatch) -> None:
    monkeypatch.setattr(service, "predict_engagement", AsyncMock(return_value=_forecast()))
    monkeypatch.setattr(service, "recommend_optimal_time", AsyncMock(return_value={"best_hours": [9]}))
    monkeypatch.setattr(service, "detect_dropout_risk", AsyncMock(return_value={"risk_level": "low"}))
    monkeypatch.setattr(service, "get_next_intent_forecast", AsyncMock(return_value={"predicted_action_type": "resume_priority_task"}))
    monkeypatch.setattr(service, "_build_subject_difficulty_projection", AsyncMock(return_value=None))
    monkeypatch.setattr(
        PersDynAttractorService,
        "get_snapshot_attractors",
        AsyncMock(
            return_value={
                "study_pace": AttractorState(
                    dim="study_pace",
                    baseline=1.0,
                    variability=0.2,
                    recovery_rate=0.1,
                    confidence=0.8,
                    updated_at=datetime(2026, 4, 21, 9, 0, 0),
                )
            }
        ),
    )
    monkeypatch.setattr(PersDynAttractorService, "build_current_observation", AsyncMock(return_value={"study_pace": 0.4}))
    monkeypatch.setattr(
        DeviationDetector,
        "detect",
        lambda self, *, attractors, current_observations: (
            Deviation(
                dim="study_pace",
                current_value=0.4,
                baseline=1.0,
                z_score=-3.0,
                direction="below",
                projected_3d=0.7,
                confidence=0.8,
            ),
        ),
    )
    monkeypatch.setattr(
        JITAITrigger,
        "generate_hints",
        AsyncMock(
            return_value=(
                ForesightHint(
                    hint_id="hint-1",
                    dim="study_pace",
                    message="你最近学习节奏低于常态，先把目标缩成 15 分钟再启动。",
                    z_score=-3.0,
                    confidence=0.8,
                    generated_at=datetime(2026, 4, 21, 9, 0, 0),
                    template_id="study_pace_below",
                ),
            )
        ),
    )


@pytest.mark.asyncio
async def test_foresight_kill_switch_master_off(db_session, monkeypatch) -> None:
    await _configure(mode="off")
    service = PredictiveService(db_session)
    await _build_snapshot(service, monkeypatch)

    snapshot = await service.build_foresight_snapshot(uuid4())

    assert snapshot.attractors == {}
    assert snapshot.deviations == ()
    assert snapshot.hints == ()


@pytest.mark.asyncio
async def test_foresight_kill_switch_attractor_off(db_session, monkeypatch) -> None:
    await _configure(mode="live", attractor="off")
    service = PredictiveService(db_session)
    await _build_snapshot(service, monkeypatch)

    snapshot = await service.build_foresight_snapshot(uuid4())

    assert snapshot.attractors == {}
    assert snapshot.deviations == ()


@pytest.mark.asyncio
async def test_foresight_kill_switch_deviation_off(db_session, monkeypatch) -> None:
    await _configure(mode="live", deviation="off")
    service = PredictiveService(db_session)
    await _build_snapshot(service, monkeypatch)

    snapshot = await service.build_foresight_snapshot(uuid4())

    assert snapshot.attractors
    assert snapshot.deviations == ()
    assert snapshot.hints == ()


@pytest.mark.asyncio
async def test_foresight_kill_switch_jitai_off(db_session, monkeypatch) -> None:
    await _configure(mode="live", jitai="off")
    service = PredictiveService(db_session)
    await _build_snapshot(service, monkeypatch)

    snapshot = await service.build_foresight_snapshot(uuid4())

    assert snapshot.attractors
    assert snapshot.deviations
    assert snapshot.hints == ()
