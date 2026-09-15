from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.galaxy import StudyRecord
from app.models.task import Task, TaskStatus, TaskType
from app.services.predictive_service import PredictiveService


@pytest.mark.asyncio
async def test_predict_engagement_keeps_existing_shape(db_session) -> None:
    user_id = uuid4()
    node_id = uuid4()
    now = datetime(2026, 4, 21, 9, 0, 0)
    db_session.add(
        StudyRecord(
            user_id=user_id,
            node_id=node_id,
            study_minutes=60,
            mastery_delta=0.1,
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2),
        )
    )
    db_session.add(
        StudyRecord(
            user_id=user_id,
            node_id=node_id,
            study_minutes=45,
            mastery_delta=0.08,
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
        )
    )
    await db_session.commit()

    forecast = await PredictiveService(db_session).predict_engagement(user_id)

    payload = forecast.to_dict()
    assert "next_active_time" in payload
    assert "confidence" in payload
    assert "risk_level" in payload


@pytest.mark.asyncio
async def test_recommend_optimal_time_keeps_existing_shape(db_session) -> None:
    result = await PredictiveService(db_session).recommend_optimal_time(uuid4())

    assert "best_hours" in result
    assert "best_weekdays" in result
    assert "confidence" in result


@pytest.mark.asyncio
async def test_detect_dropout_risk_keeps_existing_shape(db_session) -> None:
    result = await PredictiveService(db_session).detect_dropout_risk(uuid4())

    assert set(result) >= {"risk_score", "risk_level", "recommendation", "metrics"}


@pytest.mark.asyncio
async def test_get_next_intent_forecast_keeps_existing_shape(db_session, monkeypatch) -> None:
    service = PredictiveService(db_session)
    monkeypatch.setattr(
        service,
        "_maybe_attach_within_category_preference",
        AsyncMock(side_effect=lambda user_id, forecast: forecast),
    )

    result = await service.get_next_intent_forecast(uuid4())

    assert set(result) >= {
        "schema_version",
        "prediction_id",
        "predicted_action_type",
        "suggested_prompt",
    }
