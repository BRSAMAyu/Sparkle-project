from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.schemas.foresight import AttractorState, Deviation, ForesightHint
from app.services.aurora_stage27_foresight_kill_switch_service import AuroraStage27ForesightKillSwitchService
from app.services.jitai_trigger_service import JITAITrigger
from app.services.persdyn_attractor_service import PersDynAttractorService
from app.services.predictive_service import PredictiveService
from app.services.foresight_deviation_service import DeviationDetector


def _attractor(dim: str = "study_pace") -> AttractorState:
    return AttractorState(
        dim=dim,
        baseline=1.0,
        variability=0.2,
        recovery_rate=0.1,
        confidence=0.8,
        updated_at=datetime(2026, 4, 21, 9, 0, 0),
    )


def _deviation(dim: str = "study_pace") -> Deviation:
    return Deviation(
        dim=dim,
        current_value=0.4,
        baseline=1.0,
        z_score=-3.0,
        direction="below",
        projected_3d=0.7,
        confidence=0.8,
    )


def _hint(dim: str = "study_pace") -> ForesightHint:
    return ForesightHint(
        hint_id="hint-1",
        dim=dim,
        message="你最近学习节奏低于常态，先把目标缩成 15 分钟再启动。",
        z_score=-3.0,
        confidence=0.8,
        generated_at=datetime(2026, 4, 21, 9, 0, 0),
        template_id="study_pace_below",
    )


async def _configure_modes(
    *,
    mode: str,
    attractor: str = "live",
    deviation: str = "live",
    jitai: str = "live",
) -> None:
    service = AuroraStage27ForesightKillSwitchService()
    await service.set_mode(mode)
    await service.set_feature_mode("attractor", attractor)
    await service.set_feature_mode("deviation", deviation)
    await service.set_feature_mode("jitai", jitai)


@pytest.mark.asyncio
async def test_foresight_snapshot_returns_expected_contract(db_session, monkeypatch) -> None:
    user_id = uuid4()
    await _configure_modes(mode="live")
    service = PredictiveService(db_session)

    monkeypatch.setattr(service, "predict_engagement", AsyncMock(return_value=type("Forecast", (), {"to_dict": lambda self: {"next_active_time": "2026-04-22T09:00:00", "confidence": 0.8, "recommended_intervention": None, "risk_level": "low"}})()))
    monkeypatch.setattr(service, "recommend_optimal_time", AsyncMock(return_value={"best_hours": [9], "confidence": 0.7}))
    monkeypatch.setattr(service, "detect_dropout_risk", AsyncMock(return_value={"risk_level": "low"}))
    monkeypatch.setattr(service, "get_next_intent_forecast", AsyncMock(return_value={"predicted_action_type": "resume_priority_task"}))
    monkeypatch.setattr(service, "_build_subject_difficulty_projection", AsyncMock(return_value={"difficulty_level": "medium"}))
    monkeypatch.setattr(PersDynAttractorService, "get_snapshot_attractors", AsyncMock(return_value={"study_pace": _attractor()}))
    monkeypatch.setattr(PersDynAttractorService, "build_current_observation", AsyncMock(return_value={"study_pace": 0.4}))
    monkeypatch.setattr(DeviationDetector, "detect", lambda self, *, attractors, current_observations: (_deviation(),))
    monkeypatch.setattr(JITAITrigger, "generate_hints", AsyncMock(return_value=(_hint(),)))

    snapshot = await service.build_foresight_snapshot(user_id)

    assert snapshot.version == "v1"
    assert snapshot.user_id == str(user_id)
    assert set(snapshot.existing_predictions) == {
        "next_active_time",
        "optimal_learning_time",
        "subject_difficulty",
        "next_intent",
        "dropout_risk",
    }
    assert snapshot.attractors["study_pace"].baseline == 1.0
    assert snapshot.deviations[0].dim == "study_pace"
    assert snapshot.hints[0].template_id == "study_pace_below"


@pytest.mark.asyncio
async def test_foresight_snapshot_uses_sixty_second_cache(db_session, monkeypatch) -> None:
    user_id = uuid4()
    await _configure_modes(mode="off")
    service = PredictiveService(db_session)
    await cache_service.delete_pattern(f"foresight:snapshot:{user_id}*")

    forecast = type(
        "Forecast",
        (),
        {"to_dict": lambda self: {"next_active_time": "2026-04-22T09:00:00", "confidence": 0.8, "recommended_intervention": None, "risk_level": "low"}},
    )()
    predict_mock = AsyncMock(return_value=forecast)
    monkeypatch.setattr(service, "predict_engagement", predict_mock)
    monkeypatch.setattr(service, "recommend_optimal_time", AsyncMock(return_value={"best_hours": [9]}))
    monkeypatch.setattr(service, "detect_dropout_risk", AsyncMock(return_value={"risk_level": "low"}))
    monkeypatch.setattr(service, "get_next_intent_forecast", AsyncMock(return_value={"predicted_action_type": "resume_priority_task"}))
    monkeypatch.setattr(service, "_build_subject_difficulty_projection", AsyncMock(return_value=None))

    first = await service.build_foresight_snapshot(user_id)
    second = await service.build_foresight_snapshot(user_id)

    assert first.to_dict() == second.to_dict()
    assert predict_mock.await_count == 1
    assert settings.AURORA_FORESIGHT_CACHE_TTL_SECONDS == 60


@pytest.mark.asyncio
async def test_foresight_snapshot_returns_empty_new_fields_when_master_mode_off(db_session, monkeypatch) -> None:
    user_id = uuid4()
    await _configure_modes(mode="off")
    service = PredictiveService(db_session)

    monkeypatch.setattr(service, "predict_engagement", AsyncMock(return_value=type("Forecast", (), {"to_dict": lambda self: {"next_active_time": "2026-04-22T09:00:00", "confidence": 0.8, "recommended_intervention": None, "risk_level": "low"}})()))
    monkeypatch.setattr(service, "recommend_optimal_time", AsyncMock(return_value={"best_hours": [9]}))
    monkeypatch.setattr(service, "detect_dropout_risk", AsyncMock(return_value={"risk_level": "low"}))
    monkeypatch.setattr(service, "get_next_intent_forecast", AsyncMock(return_value={"predicted_action_type": "resume_priority_task"}))
    monkeypatch.setattr(service, "_build_subject_difficulty_projection", AsyncMock(return_value=None))

    snapshot = await service.build_foresight_snapshot(user_id)

    assert snapshot.attractors == {}
    assert snapshot.deviations == ()
    assert snapshot.hints == ()


@pytest.mark.asyncio
async def test_foresight_snapshot_hides_hints_when_jitai_not_live(db_session, monkeypatch) -> None:
    user_id = uuid4()
    await _configure_modes(mode="live", jitai="shadow")
    service = PredictiveService(db_session)

    monkeypatch.setattr(service, "predict_engagement", AsyncMock(return_value=type("Forecast", (), {"to_dict": lambda self: {"next_active_time": "2026-04-22T09:00:00", "confidence": 0.8, "recommended_intervention": None, "risk_level": "low"}})()))
    monkeypatch.setattr(service, "recommend_optimal_time", AsyncMock(return_value={"best_hours": [9]}))
    monkeypatch.setattr(service, "detect_dropout_risk", AsyncMock(return_value={"risk_level": "low"}))
    monkeypatch.setattr(service, "get_next_intent_forecast", AsyncMock(return_value={"predicted_action_type": "resume_priority_task"}))
    monkeypatch.setattr(service, "_build_subject_difficulty_projection", AsyncMock(return_value=None))
    monkeypatch.setattr(PersDynAttractorService, "get_snapshot_attractors", AsyncMock(return_value={"study_pace": _attractor()}))
    monkeypatch.setattr(PersDynAttractorService, "build_current_observation", AsyncMock(return_value={"study_pace": 0.4}))
    monkeypatch.setattr(DeviationDetector, "detect", lambda self, *, attractors, current_observations: (_deviation(),))
    hint_mock = AsyncMock(return_value=(_hint(),))
    monkeypatch.setattr(JITAITrigger, "generate_hints", hint_mock)

    snapshot = await service.build_foresight_snapshot(user_id)

    assert snapshot.deviations
    assert snapshot.hints == ()
    assert hint_mock.await_count == 0


@pytest.mark.asyncio
async def test_foresight_snapshot_allows_nullable_subject_difficulty(db_session, monkeypatch) -> None:
    user_id = uuid4()
    await _configure_modes(mode="off")
    service = PredictiveService(db_session)

    monkeypatch.setattr(service, "predict_engagement", AsyncMock(return_value=type("Forecast", (), {"to_dict": lambda self: {"next_active_time": "2026-04-22T09:00:00", "confidence": 0.8, "recommended_intervention": None, "risk_level": "low"}})()))
    monkeypatch.setattr(service, "recommend_optimal_time", AsyncMock(return_value={"best_hours": [9]}))
    monkeypatch.setattr(service, "detect_dropout_risk", AsyncMock(return_value={"risk_level": "low"}))
    monkeypatch.setattr(service, "get_next_intent_forecast", AsyncMock(return_value={"predicted_action_type": "resume_priority_task"}))
    monkeypatch.setattr(service, "_build_subject_difficulty_projection", AsyncMock(return_value=None))

    snapshot = await service.build_foresight_snapshot(user_id)

    assert snapshot.existing_predictions["subject_difficulty"] is None
