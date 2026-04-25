from __future__ import annotations

from uuid import uuid4

import pytest

from app.orchestration.planning_workflow import PlanningSession, PlanningWorkflowManager
from app.sprint_packs.sprint_pack_loader import load_pack


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


def test_daily_task_specs_use_sprint_pack_for_computer_networks() -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    session = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-session-pack",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="7天后考计算机网络，帮我规划",
        collected={
            "time_constraint_days": 7,
            "daily_available_hours": 2,
            "subject": "计算机网络",
            "exam_scope": "计算机网络期末",
            "knowledge_baseline": "上过课但没复习",
            "avg_mastery_score": 38,
            "recommended_path": "minimum_pass",
            "weak_nodes": [
                {"node_id": "cn.tcp_congestion_control", "mastery_score": 38},
                {"node_id": "cn.subnetting", "mastery_score": 32},
            ],
        },
    )

    strategy = manager._build_strategy(session)
    all_specs: list[dict[str, object]] = []
    for index, phase in enumerate(strategy["phases"], start=1):
        all_specs.extend(manager._daily_task_specs(phase, phase_index=index, session=session))

    assert len(all_specs) == 7
    assert all(_spec.get("subject_strategy") for _spec in all_specs[:3])
    pack = load_pack("计算机网络")
    assert pack is not None
    nodes_by_id = {node["node_id"]: node for node in pack["knowledge_nodes"]}
    first_three_node_ids = [
        node_id
        for spec in all_specs[:3]
        for node_id in spec["subject_strategy"]["node_ids"]  # type: ignore[index]
    ]
    assert first_three_node_ids
    assert all(float(nodes_by_id[node_id]["exam_weight"]) > 0.7 for node_id in first_three_node_ids)

    day_one_spec = manager._daily_task_specs(strategy["phases"][0], phase_index=1, session=session)[0]
    day_one_guide = manager._build_task_guide_json(
        session=session,
        phase=strategy["phases"][0],
        phase_index=1,
        default_daily_hours=2,
        day_number=day_one_spec["day"],
        day_focus=day_one_spec["focus"],
        day_spec=day_one_spec,
    )

    assert day_one_spec["title_focus"] != "诊断分诊"
    assert day_one_guide["why_now"]
    assert "掌握度" in day_one_guide["why_now"]
    assert "权重" in day_one_guide["why_now"]
    assert day_one_guide["related_archetypes"]
    assert day_one_guide["common_mistakes_to_watch"]


def test_last_24h_mode_overrides_strategy_and_generates_cram_tasks() -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    session = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-session-last-24h",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="明天考计算机网络，帮我规划最后一天",
        collected={
            "time_constraint_days": 1,
            "daily_available_hours": 3,
            "subject": "计算机网络",
            "exam_scope": "计算机网络期末",
            "knowledge_baseline": "上过课但错题很多",
            "avg_mastery_score": 48,
            "recommended_path": "minimum_pass",
        },
    )

    strategy = manager._build_strategy(session)
    policy = strategy["sprint_policy"]
    specs = manager._daily_task_specs(
        strategy["phases"][0],
        phase_index=1,
        session=session,
        error_clusters=[
            {
                "label": "TCP 状态变化混淆",
                "count": 3,
                "focus_summary": "三次握手、四次挥手",
                "chapters": ["传输层"],
                "examples": ["TIME_WAIT 作用遗漏"],
                "lowest_mastery": 40,
            }
        ],
    )

    assert policy["last_24h_mode"] is True
    assert policy["drop_low_roi_topics"] is True
    assert policy["new_topic_allowed"] is False
    assert policy["error_analysis_required"] is True
    assert "new_chapter_introduction" in policy["standard_layer_contract"]["must_not_include"]
    assert len(strategy["phases"]) == 1
    assert [spec["task_kind"] for spec in specs] == [
        "retrieval_triage",
        "retrieval_repair",
        "mock_review",
    ]
    assert all(spec["day"] == 1 for spec in specs)
    assert all(spec["subject_strategy"]["last_24h_mode"] is True for spec in specs)
    assert specs[0]["subject_strategy"]["focus_nodes"]
    assert specs[1]["subject_strategy"]["error_clusters"][0]["label"] == "TCP 状态变化混淆"
    assert "new_chapter_introduction" in specs[0]["subject_strategy"]["must_not_include"]


def test_daily_task_specs_fallback_when_sprint_pack_missing() -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    phase = {
        "start_day": 1,
        "end_day": 2,
        "label": "基础梳理",
        "focus": "先把概念和典型题的主线梳理清楚",
        "daily_hours": 2,
        "sprint_mode": "seven_day_survival",
        "retrieval_policy": {"minimum_output": "闭卷复述或小测"},
    }
    session = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-session-no-pack",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="7天后考高数，帮我规划",
        collected={
            "time_constraint_days": 7,
            "daily_available_hours": 2,
            "subject": "高等数学",
            "knowledge_baseline": "上过课但没复习",
        },
    )

    baseline_specs = manager._daily_task_specs(phase, phase_index=1)
    fallback_specs = manager._daily_task_specs(phase, phase_index=1, session=session)

    assert fallback_specs == baseline_specs


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
