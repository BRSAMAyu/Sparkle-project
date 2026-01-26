from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.config import settings
from app.models.cognitive import BehaviorPattern
from app.models.user import User
from app.services.analytics.behavior_pattern_decay_service import BehaviorPatternDecayService


@pytest.mark.asyncio
async def test_behavior_pattern_decay_applies(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_BEHAVIOR_DECAY", True, raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    pattern = BehaviorPattern(
        user_id=user_id,
        pattern_name="Test Pattern",
        pattern_type="execution",
        description="desc",
        solution_text="solution",
        evidence_ids=["evt_1"],
        confidence_score=0.6,
        frequency=1,
        last_observed_at=datetime.utcnow() - timedelta(days=40),
    )
    db_session.add(pattern)
    await db_session.commit()

    service = BehaviorPatternDecayService(db_session)
    updated = await service.apply_decay(
        user_id=user_id,
        window_days=30,
        decay_factor=0.5,
        min_confidence=0.35,
    )

    await db_session.refresh(pattern)
    assert updated["updated"] == 1
    assert updated["archived"] == 1
    assert pattern.confidence_score == pytest.approx(0.3)
    assert pattern.is_archived is True
    assert pattern.last_decay_at is not None


@pytest.mark.asyncio
async def test_behavior_pattern_decay_respects_recent_decay(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_BEHAVIOR_DECAY", True, raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    pattern = BehaviorPattern(
        user_id=user_id,
        pattern_name="Recent Decay",
        pattern_type="execution",
        description="desc",
        solution_text="solution",
        evidence_ids=["evt_1"],
        confidence_score=0.6,
        frequency=1,
        last_observed_at=datetime.utcnow() - timedelta(days=40),
        last_decay_at=datetime.utcnow() - timedelta(hours=1),
    )
    db_session.add(pattern)
    await db_session.commit()

    service = BehaviorPatternDecayService(db_session)
    updated = await service.apply_decay(
        user_id=user_id,
        window_days=30,
        decay_factor=0.5,
        min_confidence=0.35,
    )

    await db_session.refresh(pattern)
    assert updated["updated"] == 0
    assert updated["archived"] == 0
    assert pattern.confidence_score == pytest.approx(0.6)
