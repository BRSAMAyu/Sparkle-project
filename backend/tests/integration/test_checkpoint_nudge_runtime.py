from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.aurora.runtime_v1 import AuroraRuntimeV1Service
from app.aurora.runtime_v1.decision_loop import AuroraDecision
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.services.checkpoint_nudge_service import CheckpointNudgeService


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def setex(self, key: str, ttl: int, value: object) -> None:
        self.values[key] = value

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)


class _CheckpointDecisionLoop:
    def __init__(self) -> None:
        self.readouts = []

    async def decide(self, readout):
        self.readouts.append(readout)
        return AuroraDecision(
            action="emit_message",
            harness_updates={
                "agenda_priority": "传输层",
                "strategy": {
                    "concept_first": True,
                    "problem_first": False,
                    "worked_example_first": True,
                    "retrieval_practice": True,
                    "interleaving": False,
                    "spaced_review": True,
                    "error_analysis_required": True,
                    "drop_low_roi_topics": False,
                    "new_topic_allowed": True,
                },
            },
            state_updates={
                "informational_tensions": [
                    {
                        "domain": "传输层",
                        "description": "checkpoint 完成率只有 50%，传输层任务落后",
                        "priority": 0.82,
                        "status": "open",
                    }
                ]
            },
            chat_directive={
                "intent": "checkpoint_repair",
                "target_domain": "传输层",
                "standard_layer_contract": {
                    "response_type": "diagnostic",
                    "must_include": ["completion_check", "one_concrete_next_step"],
                    "must_not_include": ["long_motivational_speech"],
                    "max_response_length": "brief",
                },
            },
        )


class _CheckpointChatAdapter:
    async def render(self, decision, readout):
        percent = readout.checkpoint_state["completion_percent"]
        domain = readout.checkpoint_state["specific_lagging_domain"]
        return [f"你现在完成率 {percent}%，真正拖住进度的是{domain}。先把这块拆成一个 20 分钟补强。"]


@pytest.mark.asyncio
async def test_checkpoint_nudge_uses_aurora_decision_loop_with_progress_context(db_session, test_user) -> None:
    redis = _FakeRedis()
    plan_id = uuid4()
    start = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
    plan = Plan(
        id=plan_id,
        user_id=test_user.id,
        name="4天计网冲刺",
        type=PlanType.SPRINT,
        subject="计算机网络",
        is_active=True,
        target_date=(start + timedelta(days=3)).date(),
        created_at=start,
    )
    tasks = [
        Task(
            user_id=test_user.id,
            plan_id=plan_id,
            title="Day 1 · OSI 模型",
            type=TaskType.LEARNING,
            tags=["OSI 模型"],
            estimated_minutes=30,
            difficulty=2,
            energy_cost=1,
            status=TaskStatus.COMPLETED,
            phase_index=1,
            order_index=1,
        ),
        Task(
            user_id=test_user.id,
            plan_id=plan_id,
            title="Day 2 · 子网划分",
            type=TaskType.TRAINING,
            tags=["子网划分"],
            estimated_minutes=40,
            difficulty=3,
            energy_cost=2,
            status=TaskStatus.COMPLETED,
            phase_index=2,
            order_index=2,
        ),
        Task(
            user_id=test_user.id,
            plan_id=plan_id,
            title="Day 2 · 传输层自测",
            type=TaskType.TRAINING,
            tags=["传输层"],
            estimated_minutes=45,
            difficulty=4,
            energy_cost=3,
            status=TaskStatus.PENDING,
            phase_index=2,
            order_index=3,
        ),
        Task(
            user_id=test_user.id,
            plan_id=plan_id,
            title="Day 3 · 拥塞控制",
            type=TaskType.LEARNING,
            tags=["拥塞控制"],
            estimated_minutes=50,
            difficulty=4,
            energy_cost=3,
            status=TaskStatus.PENDING,
            phase_index=3,
            order_index=4,
        ),
    ]
    db_session.add_all([plan, *tasks])
    await db_session.commit()

    decision_loop = _CheckpointDecisionLoop()
    runtime = AuroraRuntimeV1Service(
        redis_client=redis,
        decision_loop=decision_loop,
        chat_adapter=_CheckpointChatAdapter(),
    )

    message = await CheckpointNudgeService(
        db_session,
        redis,
        runtime_service=runtime,
    ).send_nudge(
        user_id=test_user.id,
        plan_id=plan_id,
        checkpoint={"day": 2, "description": "中段检查：确认自测和薄弱域"},
    )

    assert "完成率 50%" in message.content
    assert "传输层" in message.content
    assert "我们来快速复盘一下" not in message.content
    assert len(decision_loop.readouts) == 1
    readout = decision_loop.readouts[0]
    assert readout.checkpoint_state["completion_rate"] == 0.5
    assert readout.checkpoint_state["specific_lagging_domain"] == "传输层"
    assert readout.cold_start_context["subject"] == "计算机网络"
    assert "cold_start_context" in readout.to_llm_payload(action="emit_message")
