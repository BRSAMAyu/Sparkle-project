from __future__ import annotations

from uuid import uuid4

import pytest

from app.orchestration.planning_workflow import PlanningSession, PlanningWorkflowManager


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)


@pytest.mark.parametrize(
    ("message", "context"),
    [
        ("7天后考计算机网络，从来没学过，帮我规划一下", {}),
        ("我想在3天内复习完高数，给我做个计划", {}),
        ("两周后数据库期末，帮我安排备考", {}),
        ("想在5天内把操作系统冲到不挂科", {}),
        ("帮我做一个7天英语四级冲刺计划", {}),
    ],
)
def test_detect_planning_intent_positive_cases(message: str, context: dict[str, str]) -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    assert manager.detect_planning_intent(message, context) is True


@pytest.mark.parametrize(
    ("message", "context"),
    [
        ("帮我创建一个任务，明天学两小时计网", {}),
        ("今天做什么", {}),
        ("帮我更新这个计划，把Day2改轻一点", {}),
        ("明天提醒我复习计网", {}),
        ("这个任务完成了吗", {}),
    ],
)
def test_detect_planning_intent_negative_cases(message: str, context: dict[str, str]) -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    assert manager.detect_planning_intent(message, context) is False


@pytest.mark.parametrize(
    ("days", "expected_ranges", "expected_phase_count"),
    [
        (3, [(1, 2), (3, 3)], 2),
        (5, [(1, 2), (3, 4), (5, 5)], 3),
        (7, [(1, 3), (4, 5), (6, 7)], 3),
    ],
)
def test_build_strategy_uses_dynamic_day_ranges(
    days: int,
    expected_ranges: list[tuple[int, int]],
    expected_phase_count: int,
) -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    session = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-session-strategy",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw=f"{days}天后考计算机网络",
        collected={
            "time_constraint_days": days,
            "daily_available_hours": 3,
            "subject": "计算机网络",
            "knowledge_baseline": "完全没学过",
        },
    )

    strategy = manager._build_strategy(session)

    phases = strategy["phases"]
    assert len(phases) == expected_phase_count
    assert [(phase["start_day"], phase["end_day"]) for phase in phases] == expected_ranges
    assert all(phase["start_day"] <= phase["end_day"] for phase in phases)
    assert phases[-1]["end_day"] == days


def test_daily_task_specs_expands_each_phase_to_one_task_per_day() -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    specs = manager._daily_task_specs(
        {
            "start_day": 3,
            "end_day": 5,
            "label": "核心攻克",
            "focus": "每天攻克一个核心知识点",
        },
        phase_index=2,
    )

    assert [spec["day"] for spec in specs] == [3, 4, 5]
    assert all("核心攻克" in spec["focus"] for spec in specs)


@pytest.mark.asyncio
async def test_irrelevant_message_during_clarifying_bypasses_without_advancing_state() -> None:
    redis = FakeRedis()
    manager = PlanningWorkflowManager(redis_client=redis)
    session = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-session-1",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="7天后考计算机网络，帮我规划",
        collected={},
        turns_in_state=2,
    )
    await manager.save_session(session)
    turn_user_id = uuid4()

    result = await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=turn_user_id,
        chat_session_id="chat-session-1",
        message="等等，先帮我查一下这个任务完成没有",
        context={},
    )

    persisted = await manager.get_active_session("chat-session-1")
    runtime_state = await manager.runtime_adapter.load_state(
        user_id=str(turn_user_id),
        conversation_id="chat-session-1",
    )
    scaffold = manager.runtime_adapter.build_detour_scaffold(runtime_state) if runtime_state is not None else {}
    assert result == {"bypass_planning": True}
    assert persisted is not None
    assert persisted.state == "CLARIFYING"
    assert persisted.turns_in_state == 2
    assert runtime_state is not None
    assert scaffold["current_intent"]["intent_type"] == "answer_detour"
    assert scaffold["top_latent_thread"] is not None


@pytest.mark.asyncio
async def test_relevant_message_during_clarifying_advances_turn_counter() -> None:
    redis = FakeRedis()
    manager = PlanningWorkflowManager(redis_client=redis)
    session = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-session-2",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="7天后考计算机网络，帮我规划",
        collected={},
        turns_in_state=0,
    )
    await manager.save_session(session)
    turn_user_id = uuid4()

    result = await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=turn_user_id,
        chat_session_id="chat-session-2",
        message="考传输层、网络层和应用层，我是零基础",
        context={},
    )

    persisted = await manager.get_active_session("chat-session-2")
    runtime_state = await manager.runtime_adapter.load_state(
        user_id=str(turn_user_id),
        conversation_id="chat-session-2",
    )
    scaffold = manager.runtime_adapter.build_detour_scaffold(runtime_state) if runtime_state is not None else {}
    assert result is not None
    assert result.get("bypass_planning") is None
    assert persisted is not None
    assert persisted.turns_in_state == 1
    assert persisted.collected["knowledge_baseline"] == "完全没学过"
    assert "daily_available_hours" not in persisted.collected
    assert runtime_state is not None
    assert scaffold["top_tension"]["domain"] == "time_available"
    assert all(item["domain"] != "knowledge_baseline" for item in scaffold["open_tensions"])
