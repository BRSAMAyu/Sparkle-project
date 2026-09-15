from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.schemas.foresight import AttractorState, Deviation
from app.services.predictive_service import PredictiveService


def _attractor(dim: str = "mood_valence") -> AttractorState:
    return AttractorState(
        dim=dim,
        baseline=0.5,
        variability=0.1,
        recovery_rate=0.1,
        confidence=0.8,
        updated_at=datetime(2026, 4, 21, 9, 0, 0),
    )


def _deviation(dim: str = "mood_valence") -> Deviation:
    return Deviation(
        dim=dim,
        current_value=0.1,
        baseline=0.6,
        z_score=-3.5,
        direction="below",
        projected_3d=0.3,
        confidence=0.8,
    )


def test_sqam_predictive_dp1_realtime_messages_redact_pii() -> None:
    service = PredictiveService(db=None)  # type: ignore[arg-type]

    messages = service._build_realtime_llm_messages(
        partial_text="我手机号是13812345678，邮箱是foo@example.com",
        base={
            "signals": {},
            "predicted_action_type": "continue_chat",
            "suggested_prompt": "",
        },
    )

    assert "[REDACTED_PHONE]" in messages[1]["content"]
    assert "[REDACTED_EMAIL]" in messages[1]["content"]


def test_sqam_predictive_st1_caps_merged_confidence() -> None:
    service = PredictiveService(db=None)  # type: ignore[arg-type]

    merged = service._merge_prediction_payload(
        {
            "title": "base",
            "summary": "base",
            "confidence": 0.5,
            "predicted_action_type": "continue_chat",
            "predicted_window": "now",
            "reasons": ["base"],
            "suggested_prompt": "",
        },
        {"title": "x", "confidence": 1.7},
    )

    assert merged is not None
    assert merged["confidence"] == 0.95


@pytest.mark.asyncio
async def test_sqam_predictive_id1_analytics_exposes_ctr_field(db_session) -> None:
    analytics = await PredictiveService(db_session).get_prediction_analytics(uuid4())

    assert "ctr" in analytics["overall"]
    assert "ctr" in analytics["funnel"]


@pytest.mark.asyncio
async def test_sqam_predictive_sm1_high_risk_suppresses_mood_only_jitai(
    db_session, monkeypatch
) -> None:
    service = PredictiveService(db_session)
    monkeypatch.setattr(
        service,
        "predict_engagement",
        AsyncMock(return_value=type("F", (), {"to_dict": lambda self: {}})()),
    )
    monkeypatch.setattr(service, "recommend_optimal_time", AsyncMock(return_value={}))
    monkeypatch.setattr(
        service, "detect_dropout_risk", AsyncMock(return_value={"risk_level": "high"})
    )
    monkeypatch.setattr(service, "get_next_intent_forecast", AsyncMock(return_value={}))
    monkeypatch.setattr(
        service, "_build_subject_difficulty_projection", AsyncMock(return_value={})
    )
    monkeypatch.setattr(
        "app.services.predictive_service.AuroraStage27ForesightKillSwitchService.get_mode",
        AsyncMock(return_value="live"),
    )
    monkeypatch.setattr(
        "app.services.predictive_service.AuroraStage27ForesightKillSwitchService.is_feature_enabled",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.services.predictive_service.AuroraStage27ForesightKillSwitchService.is_feature_live",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.services.predictive_service.PersDynAttractorService.get_snapshot_attractors",
        AsyncMock(return_value={"mood_valence": _attractor()}),
    )
    monkeypatch.setattr(
        "app.services.predictive_service.PersDynAttractorService.build_current_observation",
        AsyncMock(return_value={"mood_valence": 0.1}),
    )
    monkeypatch.setattr(
        "app.services.predictive_service.DeviationDetector.detect",
        lambda self, *, attractors, current_observations: (_deviation(),),
    )
    jitai_mock = AsyncMock(return_value=())
    monkeypatch.setattr(
        "app.services.predictive_service.JITAITrigger.generate_hints", jitai_mock
    )

    snapshot = await service.build_foresight_snapshot(uuid4())

    assert snapshot.hints == ()
    jitai_mock.assert_not_awaited()
