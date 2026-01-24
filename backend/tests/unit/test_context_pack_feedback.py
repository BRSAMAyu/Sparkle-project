from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.context_pack import ContextPackRun, ContextPackFeedback, ContextBudgetProfile
from app.models.user import User
from app.services.response_feedback_service import ResponseFeedbackService


@pytest.mark.asyncio
async def test_feedback_ingestion_links_pack_run(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_BUDGET_TUNING", True, raising=False)
    monkeypatch.setattr(settings, "CONTEXT_PACK_FEEDBACK_WINDOW_MINUTES", 10, raising=False)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    pack_run = ContextPackRun(
        user_id=user_id,
        intent="chat",
        budgets={"preferences": 100, "goals": 120, "episodic": 140},
        token_usage={"preferences": 80, "goals": 90, "episodic": 100},
        memory_counts={"preferences": 2, "goals": 1, "episodic": 3},
        evidence_score_avg=0.6,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(pack_run)
    await db_session.commit()

    service = ResponseFeedbackService(db_session, redis_client=None)
    result = await service.submit_feedback(
        user_id=str(user_id),
        response_id=str(uuid4()),
        trace_id="trace_1",
        feedback_type=2,
        reasons=["verbose"],
        free_text=None,
        workflow_id=None,
        prompt_version=None,
        meta={},
    )
    assert result.success is True

    feedback_rows = (await db_session.execute(select(ContextPackFeedback))).scalars().all()
    assert feedback_rows
    assert feedback_rows[0].pack_run_id == pack_run.id

    profiles = (await db_session.execute(select(ContextBudgetProfile))).scalars().all()
    assert profiles
