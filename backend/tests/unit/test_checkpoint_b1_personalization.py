from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.aurora.runtime_v1 import AURORA_CHECKPOINT_SURFACE, AuroraRuntimeTurnPlan
from app.aurora.runtime_v1.models import AuroraStateSnapshot
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.services.checkpoint_nudge_service import CheckpointDebriefService, CheckpointNudgeService


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def setex(self, key: str, ttl: int, value: object) -> None:
        self.values[key] = value

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)


class _NoMessageRuntime:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def plan_turn(self, **kwargs):
        self.calls.append(kwargs)
        return AuroraRuntimeTurnPlan(
            surface=kwargs["surface"],
            messages=[],
            surface_complete=False,
            modeling_complete=False,
        )


def _task(plan_id, user_id, index: int, *, completed: bool = False) -> Task:
    return Task(
        user_id=user_id,
        plan_id=plan_id,
        title=f"Day {index} · TCP 拥塞控制",
        type=TaskType.LEARNING,
        tags=["TCP 拥塞控制"],
        estimated_minutes=40,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.COMPLETED if completed else TaskStatus.PENDING,
        order_index=index,
        phase_index=index,
    )


@pytest.mark.asyncio
async def test_checkpoint_nudge_text_snapshot_uses_prior_state_and_unclosed_question(db_session, test_user) -> None:
    session = ChatSession(id=uuid4(), user_id=test_user.id, is_active=True, last_message_at=datetime.utcnow())
    plan_id = uuid4()
    plan = Plan(
        id=plan_id,
        user_id=test_user.id,
        name="7天计网冲刺",
        type=PlanType.SPRINT,
        subject="计算机网络",
        is_active=True,
    )
    db_session.add_all(
        [
            session,
            plan,
            ChatMessage(
                user_id=test_user.id,
                session_id=session.id,
                role=MessageRole.ASSISTANT,
                content="你提到想试一下 worked example，后来试了吗？",
            ),
            AuroraStateSnapshot(
                user_id=test_user.id,
                surface=AURORA_CHECKPOINT_SURFACE,
                conversation_id=f"cp:{plan_id}:2",
                runtime_session_id=str(session.id),
                snapshot_at=datetime(2026, 4, 24, 10, 0, tzinfo=UTC).replace(tzinfo=None),
                user_model_snapshot={
                    "checkpoint_description": "Day 2 晚：做20题自测",
                    "blocker_summary": "TCP 拥塞控制 worked example 还没试",
                    "next_task_title": "Day 4 · TCP 拥塞控制补强",
                },
                informational_tensions=[
                    {
                        "domain": "knowledge_gap",
                        "description": "TCP 拥塞控制 worked example 还没试",
                        "priority": 0.82,
                        "status": "open",
                    }
                ],
                latent_threads=[],
                activity_profile={},
                runtime_metadata={},
            ),
            *[_task(plan_id, test_user.id, index, completed=index <= 2) for index in range(1, 8)],
        ]
    )
    await db_session.commit()

    runtime = _NoMessageRuntime()
    message = await CheckpointNudgeService(db_session, _FakeRedis(), runtime_service=runtime).send_nudge(
        user_id=test_user.id,
        plan_id=plan_id,
        checkpoint={"day": 4, "description": "Day 4 晚：检查传输层"},
    )

    assert "接着上次的线索来" in message.content
    assert "TCP 拥塞控制 worked example 还没试" in message.content
    assert "完成了 2/7 个任务" in message.content
    payload = message.actions[0]["data"]
    assert payload["previous_runtime_state_summary"]
    assert len(payload["debrief_context"]["question_plan"]) == 3
    assert payload["debrief_context"]["question_plan"][0]["reason"]
    checkpoint_state = runtime.calls[0]["request_extra_context"]["checkpoint_state"]
    assert checkpoint_state["unclosed_questions"]
    assert checkpoint_state["personalized_questions"][0]["focus"] == "continuity"


def test_checkpoint_question_plan_varies_between_on_track_and_behind() -> None:
    service = CheckpointNudgeService(db=None, redis=None)  # type: ignore[arg-type]

    on_track = service._checkpoint_question_plan(
        checkpoint_state={
            "status": "on_track",
            "completion_rate": 0.75,
            "expected_completion_rate": 0.55,
        },
        open_threads=[],
        unclosed_questions=[],
    )
    behind = service._checkpoint_question_plan(
        checkpoint_state={
            "status": "behind",
            "completion_rate": 0.2,
            "expected_completion_rate": 0.6,
            "specific_lagging_domain": "TCP 拥塞控制",
        },
        open_threads=["worked example 还没试"],
        unclosed_questions=[],
    )

    assert len(on_track) == 1
    assert len(behind) == 3
    assert all(question.reason for question in [*on_track, *behind])
    assert {question.focus for question in behind} == {"continuity", "bottleneck", "next_step"}


@pytest.mark.asyncio
async def test_checkpoint_debrief_consumes_planned_question_without_legacy_prompt(db_session, test_user) -> None:
    plan_id = uuid4()
    session_id = uuid4()
    db_session.add(
        Plan(
            id=plan_id,
            user_id=test_user.id,
            name="7天计网冲刺",
            type=PlanType.SPRINT,
            is_active=True,
        )
    )
    await db_session.commit()

    service = CheckpointDebriefService(db_session, _FakeRedis())
    start = await service.process_turn(
        user_id=test_user.id,
        chat_session_id=session_id,
        user_message="开始复盘",
        context={
            "debrief_context": {
                "nudge_id": f"cp:{plan_id}:4",
                "plan_id": str(plan_id),
                "checkpoint_day": 4,
                "checkpoint_description": "Day 4 晚：检查传输层",
                "question_plan": [
                    {
                        "question_id": "keep-or-adjust",
                        "focus": "next_step",
                        "question": "接下来一天你想保持原节奏，还是把某一块稍微调轻一点？",
                        "reason": "进度可控时只需要确认微调，不需要把复盘扩成新的负担。",
                    }
                ],
            }
        },
    )
    final = await service.process_turn(
        user_id=test_user.id,
        chat_session_id=session_id,
        user_message="保持原节奏，TCP 这块已经顺了",
        context={},
    )

    assert "接下来一天你想保持原节奏" in start["message"]
    assert "我问这个是因为" in start["message"]
    assert start["message"] != "这个检查点的情况怎么样？"
    assert final["finished"] is True
    assert final["goal_met"] is True
