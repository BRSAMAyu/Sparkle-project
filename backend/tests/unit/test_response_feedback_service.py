import random
import uuid
from datetime import timedelta
import json

import pytest
from sqlalchemy import select

from app.learning.prompt_bandit import PromptBandit
from app.models.response_feedback import ResponseFeedback
from app.services.response_feedback_service import ResponseFeedbackService


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value


@pytest.mark.asyncio
async def test_feedback_insert_success(db_session):
    service = ResponseFeedbackService(db_session)
    user_id = str(uuid.uuid4())
    response_id = str(uuid.uuid4())

    result = await service.submit_feedback(
        user_id=user_id,
        response_id=response_id,
        trace_id="trace-1",
        feedback_type=ResponseFeedback.FEEDBACK_UP,
        reasons=["inaccurate"],
        free_text="ok",
        workflow_id="standard_chat",
        prompt_version="v1",
    )

    assert result.success is True
    assert result.already_recorded is False

    rows = (await db_session.execute(select(ResponseFeedback))).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_feedback_idempotent_insert(db_session):
    service = ResponseFeedbackService(db_session)
    user_id = str(uuid.uuid4())
    response_id = str(uuid.uuid4())

    await service.submit_feedback(
        user_id=user_id,
        response_id=response_id,
        trace_id="trace-2",
        feedback_type=ResponseFeedback.FEEDBACK_DOWN,
        reasons=["verbose"],
        workflow_id="standard_chat",
        prompt_version="v2",
    )
    result = await service.submit_feedback(
        user_id=user_id,
        response_id=response_id,
        trace_id="trace-2",
        feedback_type=ResponseFeedback.FEEDBACK_DOWN,
        reasons=["verbose"],
        workflow_id="standard_chat",
        prompt_version="v2",
    )

    assert result.success is True
    assert result.already_recorded is True

    rows = (await db_session.execute(select(ResponseFeedback))).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_feedback_summary(db_session):
    service = ResponseFeedbackService(db_session)
    user_id = str(uuid.uuid4())

    await service.submit_feedback(
        user_id=user_id,
        response_id=str(uuid.uuid4()),
        trace_id="trace-3",
        feedback_type=ResponseFeedback.FEEDBACK_UP,
        reasons=["formatting"],
        workflow_id="standard_chat",
        prompt_version="v1",
    )
    await service.submit_feedback(
        user_id=user_id,
        response_id=str(uuid.uuid4()),
        trace_id="trace-4",
        feedback_type=ResponseFeedback.FEEDBACK_DOWN,
        reasons=["inaccurate", "verbose"],
        workflow_id="standard_chat",
        prompt_version="v1",
    )
    await service.submit_feedback(
        user_id=user_id,
        response_id=str(uuid.uuid4()),
        trace_id="trace-5",
        feedback_type=ResponseFeedback.FEEDBACK_DOWN,
        reasons=["too_simple"],
        workflow_id="workflow_x",
        prompt_version="v2",
    )

    summary = await service.get_summary(timedelta(hours=24))

    assert summary["feedback_count"] == 3
    assert summary["up_count"] == 1
    assert summary["down_count"] == 2
    assert summary["down_rate"] == pytest.approx(2 / 3)
    assert summary["top_reasons"]["inaccurate"] == 1
    assert summary["by_prompt_version"]["v1"]["down"] == 1
    assert summary["by_workflow_id"]["standard_chat"]["up"] == 1


@pytest.mark.asyncio
async def test_prompt_bandit_update_shifts_selection():
    redis = FakeRedis()
    bandit = PromptBandit(redis_client=redis, rng=random.Random(7))

    for _ in range(20):
        await bandit.update("standard_chat", "v1", 1)
    for _ in range(20):
        await bandit.update("standard_chat", "v2", 0)

    counts = {"v1": 0, "v2": 0}
    for _ in range(500):
        choice = await bandit.select("standard_chat", ["v1", "v2"])
        counts[choice] += 1

    assert counts["v1"] > counts["v2"]


@pytest.mark.asyncio
async def test_feedback_dedupe_does_not_double_update_bandit(db_session):
    redis = FakeRedis()
    service = ResponseFeedbackService(db_session, redis_client=redis)
    user_id = str(uuid.uuid4())
    response_id = str(uuid.uuid4())

    await service.submit_feedback(
        user_id=user_id,
        response_id=response_id,
        trace_id="trace-6",
        feedback_type=ResponseFeedback.FEEDBACK_UP,
        workflow_id="standard_chat",
        prompt_version="v1",
    )
    await service.submit_feedback(
        user_id=user_id,
        response_id=response_id,
        trace_id="trace-6",
        feedback_type=ResponseFeedback.FEEDBACK_UP,
        workflow_id="standard_chat",
        prompt_version="v1",
    )

    raw = await redis.get("bandit:prompt:standard_chat")
    assert raw is not None
    state = json.loads(raw)
    arm_state = state["arms"]["v1"]
    assert arm_state["alpha"] == 2.0
    assert arm_state["beta"] == 1.0
