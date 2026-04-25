from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.galaxy import KnowledgeNode
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter
from app.orchestration.planning_workflow import PlanningSession, PlanningWorkflowManager
from app.services.galaxy_service import GalaxyService
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
        node_id for spec in all_specs[:3] for node_id in spec["subject_strategy"]["node_ids"]  # type: ignore[index]
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

    assert day_one_spec["task_kind"] == "diagnostic_triage"
    assert day_one_spec["title_focus"] == "诊断分诊"
    assert day_one_guide["why_now"]
    assert "掌握度" in day_one_guide["why_now"]
    assert "权重" in day_one_guide["why_now"]
    assert day_one_guide["related_archetypes"]
    assert day_one_guide["common_mistakes_to_watch"]


@pytest.mark.asyncio
async def test_previous_exam_weak_nodes_injected_into_aurora_state(db_session, test_user) -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    user_id = test_user.id
    prefs = UserPreferencesCenter(
        user_id=user_id,
        explicit={
            "exam_sprint_growth_archive": {
                "entries": [
                    {
                        "review_id": "review-tcp",
                        "subject": "计算机网络",
                        "reviewed_at": "2026-04-24T10:00:00",
                        "persistent_weak_nodes": [
                            {"node_id": "cn.tcp_state", "node_name": "TCP 状态机"},
                            {"node_id": "cn.tcp_three_way", "node_name": "TCP 三次握手"},
                        ],
                    }
                ]
            }
        },
    )
    db_session.add(prefs)
    await db_session.commit()

    session = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-previous-weak",
        user_id=str(user_id),
        state="CLARIFYING",
        goal_raw="7天后考计算机网络",
        collected={"subject": "计算机网络"},
    )
    previous = await manager._load_previous_exam_weak_nodes_for_session(
        db=db_session,
        user_id=user_id,
        session=session,
        profile_context={},
        message="7天后考计算机网络，帮我冲刺",
    )
    session.collected["previous_exam_weak_nodes"] = previous
    state = await manager.runtime_adapter.get_or_create_state(
        user_id=str(user_id),
        conversation_id=session.chat_session_id,
        db=db_session,
        planning_session_id=session.planning_session_id,
        goal_raw=session.goal_raw,
        profile_context={},
        collected=session.collected,
    )

    node_ids = [item["node_id"] for item in state.cold_start_context["previous_exam_weak_nodes"]]
    assert "cn.tcp_state" in node_ids
    assert "cn.tcp_three_way" in node_ids


def test_previous_exam_weak_nodes_boost_pack_task_minutes_and_difficulty() -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    phase = {
        "start_day": 1,
        "end_day": 7,
        "label": "检索攻克",
        "focus": "每天围绕高频基础分做闭卷输出 + 典型题验证",
        "daily_hours": 2,
        "sprint_policy": {"sprint_mode": "seven_day_survival"},
    }
    base_session = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-base-pack",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="7天后考计算机网络",
        collected={
            "time_constraint_days": 7,
            "daily_available_hours": 2,
            "subject": "计算机网络",
            "avg_mastery_score": 45,
            "recommended_path": "minimum_pass",
        },
    )
    history_session = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-history-pack",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="7天后考计算机网络",
        collected={
            **base_session.collected,
            "previous_exam_weak_nodes": [{"node_id": "cn.tcp_three_way", "node_name": "TCP 三次握手"}],
        },
    )

    base_specs = manager._daily_task_specs(phase, phase_index=1, session=base_session)
    history_specs = manager._daily_task_specs(phase, phase_index=1, session=history_session)
    boosted = next(
        spec
        for spec in history_specs
        if "cn.tcp_three_way" in spec.get("subject_strategy", {}).get("node_ids", [])
    )
    baseline = next(spec for spec in base_specs if spec["day"] == boosted["day"])
    base_difficulty = manager._mastery_to_difficulty(history_session.collected["avg_mastery_score"], 1)

    assert boosted["previous_exam_weak"] is True
    assert boosted["estimated_minutes"] > baseline["estimated_minutes"]
    assert min(5, base_difficulty + 1) > base_difficulty


def test_first_day_recommendation_mentions_previous_exam_weak_nodes() -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    session = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-history-recommendation",
        user_id=str(uuid4()),
        state="PLANNING",
        goal_raw="7天后考计算机网络",
        collected={
            "subject": "计算机网络",
            "previous_exam_weak_nodes": [{"node_id": "cn.tcp_state", "node_name": "TCP 状态机"}],
        },
    )

    recommendation = manager._decorate_first_day_recommendation(
        session=session,
        recommendation="今天先做好这 2 件事，计算机网络 的第一步就稳下来了。",
    )

    assert "根据你上次的考后复盘" in recommendation
    assert "TCP" in recommendation
    assert "优先级提高" in recommendation


def test_cross_sprint_mastery_adds_light_review_for_mastered_nodes() -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    previous_sprint_summary = {
        "strongest_nodes": ["cn.osi_model", "cn.tcp_handshake"],
        "mastery_snapshot": {"cn.osi_model": 0.85},
    }
    session = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-session-cross-sprint",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="7天后考计算机网络，帮我规划",
        collected={
            "time_constraint_days": 7,
            "daily_available_hours": 2,
            "subject": "计算机网络",
            "exam_scope": "计算机网络期末",
            "knowledge_baseline": "上次冲刺过一轮",
            "avg_mastery_score": 45,
            "recommended_path": "minimum_pass",
            "sprint_pack_id": "computer_networks@v1",
            "previous_sprint_summary": previous_sprint_summary,
            "cold_start_context": {
                "sprint_pack_id": "computer_networks@v1",
                "previous_sprint_summary": previous_sprint_summary,
            },
        },
    )

    strategy = manager._build_strategy(session)
    specs: list[dict[str, object]] = []
    for index, phase in enumerate(strategy["phases"], start=1):
        specs.extend(manager._daily_task_specs(phase, phase_index=index, session=session))

    osi_specs = [
        spec
        for spec in specs
        if "cn.osi_model" in _as_node_ids(spec.get("subject_strategy"))
    ]
    assert osi_specs
    assert min(int(spec["estimated_minutes"]) for spec in osi_specs) <= 20
    assert osi_specs[0]["subject_strategy"]["review_mode"] == "skip_or_light_review"  # type: ignore[index]
    assert "上次已掌握" in " ".join(strategy["strategy_notes"])

    day_one_phase = strategy["phases"][0]
    guide = manager._build_task_guide_json(
        session=session,
        phase=day_one_phase,
        phase_index=1,
        default_daily_hours=2,
        day_number=osi_specs[0]["day"],
        day_focus=osi_specs[0]["focus"],
        day_spec=osi_specs[0],
    )
    prompt = manager._build_task_ai_prompt(
        session=session,
        phase={**day_one_phase, "focus": osi_specs[0]["focus"]},
        guide_json=guide,
    )
    assert "上次已掌握" in prompt


def test_cross_sprint_weak_nodes_are_promoted_ahead_of_default_priority() -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    base_collected = {
        "time_constraint_days": 7,
        "daily_available_hours": 2,
        "subject": "计算机网络",
        "exam_scope": "计算机网络期末",
        "knowledge_baseline": "上次冲刺过一轮",
        "avg_mastery_score": 45,
        "recommended_path": "minimum_pass",
    }
    previous_sprint_summary = {
        "strongest_nodes": ["cn.osi_model"],
        "persistent_weak_nodes": ["cn.http"],
        "mastery_snapshot": {"cn.osi_model": 0.85, "cn.http": 0.2},
    }
    session = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-session-cross-sprint-weak",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="7天后考计算机网络，帮我规划",
        collected={
            **base_collected,
            "sprint_pack_id": "computer_networks@v1",
            "previous_sprint_summary": previous_sprint_summary,
            "cold_start_context": {
                "sprint_pack_id": "computer_networks@v1",
                "previous_sprint_summary": previous_sprint_summary,
            },
        },
    )

    strategy = manager._build_strategy(session)
    first_phase_specs = manager._daily_task_specs(strategy["phases"][0], phase_index=1, session=session)
    first_core_spec = next(
        spec
        for spec in first_phase_specs
        if _as_dict_for_test(spec.get("subject_strategy")).get("review_mode") != "skip_or_light_review"
    )

    assert "cn.http" in _as_node_ids(first_core_spec.get("subject_strategy"))
    assert first_core_spec["subject_strategy"]["previous_mastery_summary"]["priority_boost_nodes"] == ["cn.http"]  # type: ignore[index]


def test_cross_sprint_absent_history_keeps_sprint_pack_output_unchanged() -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    collected = {
        "time_constraint_days": 7,
        "daily_available_hours": 2,
        "subject": "计算机网络",
        "exam_scope": "计算机网络期末",
        "knowledge_baseline": "上过课但没复习",
        "avg_mastery_score": 38,
        "recommended_path": "minimum_pass",
    }
    baseline = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-session-no-history-baseline",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="7天后考计算机网络，帮我规划",
        collected=dict(collected),
    )
    with_empty_history = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-session-no-history-empty",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="7天后考计算机网络，帮我规划",
        collected={**collected, "sprint_pack_id": "computer_networks@v1"},
    )

    baseline_strategy = manager._build_strategy(baseline)
    empty_strategy = manager._build_strategy(with_empty_history)
    baseline_specs = manager._daily_task_specs(baseline_strategy["phases"][0], phase_index=1, session=baseline)
    empty_specs = manager._daily_task_specs(empty_strategy["phases"][0], phase_index=1, session=with_empty_history)

    assert [
        _as_node_ids(spec.get("subject_strategy")) for spec in empty_specs
    ] == [
        _as_node_ids(spec.get("subject_strategy")) for spec in baseline_specs
    ]


@pytest.mark.asyncio
async def test_enrich_cross_sprint_mastery_from_galaxy_rollup(db_session, test_user) -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    session = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-session-galaxy-rollup",
        user_id=str(test_user.id),
        state="CLARIFYING",
        goal_raw="7天后考计算机网络，帮我规划",
        collected={
            "subject": "计算机网络",
            "sprint_pack_id": "computer_networks@v1",
            "cold_start_context": {
                "sprint_pack_id": "computer_networks@v1",
                "mastery_snapshot": {"cn.osi_model": 0.2},
            },
        },
    )

    await GalaxyService(db_session).update_node_mastery(
        user_id=test_user.id,
        node_id="cn.tcp_flow_control",
        new_mastery=0.5,
        reason="test_cross_sprint_rollup",
    )

    await manager._enrich_cross_sprint_mastery_from_galaxy(
        db=db_session,
        user_id=test_user.id,
        session=session,
        aurora_state=None,
    )

    summary = session.collected.get("galaxy_sprint_mastery_summary")
    assert summary is not None
    assert summary["mastery_snapshot"]["cn.tcp_flow_control"] == pytest.approx(0.5)


def _as_dict_for_test(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _as_node_ids(subject_strategy: object) -> list[str]:
    strategy = _as_dict_for_test(subject_strategy)
    return [str(node_id) for node_id in list(strategy.get("node_ids") or [])]


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
        goal_raw="7天后考古典文学，帮我规划",
        collected={
            "time_constraint_days": 7,
            "daily_available_hours": 2,
            "subject": "古典文学",
            "knowledge_baseline": "上过课但没复习",
        },
    )

    baseline_specs = manager._daily_task_specs(phase, phase_index=1)
    fallback_specs = manager._daily_task_specs(phase, phase_index=1, session=session)

    assert fallback_specs == baseline_specs


def test_generate_next_day_plan_keeps_full_task_when_not_behind() -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    session = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-session-full-next-day",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="7天后考高数，帮我规划",
        collected={
            "time_constraint_days": 7,
            "daily_available_hours": 2,
            "subject": "高等数学",
        },
    )
    strategy = manager._build_strategy(session)
    phase = strategy["phases"][0]
    day_spec = manager._daily_task_specs(phase, phase_index=1, session=session)[0]

    generated = manager._generate_next_day_plan(
        day_spec=day_spec,
        sprint_policy=strategy["sprint_policy"],
        completion_rate=0.8,
    )

    assert generated == [day_spec]
    assert generated[0]["task_kind"] != "compressed_recovery"


def test_generate_next_day_plan_compresses_when_behind_and_near_deadline() -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    session = PlanningSession(
        planning_session_id=str(uuid4()),
        chat_session_id="chat-session-compressed-next-day",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="7天后考计算机网络，帮我规划",
        collected={
            "time_constraint_days": 7,
            "daily_available_hours": 2,
            "subject": "计算机网络",
            "exam_scope": "计算机网络期末",
            "knowledge_baseline": "上过课但没复习",
            "recommended_path": "minimum_pass",
        },
    )
    strategy = manager._build_strategy(session)
    sprint_policy = dict(strategy["sprint_policy"])
    sprint_policy["days_left"] = 5
    day_spec = {
        "day": 5,
        "focus": "继续推进传输层高频节点",
        "title_focus": "TCP 拥塞控制",
        "task_kind": "retrieval_drill",
        "estimated_minutes": 70,
        "minimum_output": "闭卷复述、3题小测或一道典型题独立完成",
    }

    generated = manager._generate_next_day_plan(
        day_spec=day_spec,
        sprint_policy=sprint_policy,
        completion_rate=0.3,
    )

    assert len(generated) == 1
    assert generated[0]["task_kind"] == "compressed_recovery"
    assert generated[0]["estimated_minutes"] <= 35
    assert generated[0]["daily_spec"]["compressed"] is True


@pytest.mark.asyncio
async def test_insert_repair_task_prepends_next_day_and_deduplicates(db_session) -> None:
    user = User(
        username="repair_task_user",
        email="repair_task_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="计网冲刺",
        type=PlanType.SPRINT,
        description="7 天计划",
        plan_stage=PlanStage.DAILY,
        target_date=datetime.utcnow().date() + timedelta(days=7),
        daily_available_minutes=90,
        total_estimated_hours=10,
        subject="计算机网络",
        mastery_level=0.3,
        progress=0.1,
        is_active=True,
        priority=PlanPriority.HIGH,
    )
    db_session.add(plan)
    await db_session.flush()

    error_node = KnowledgeNode(name="TCP 滑动窗口机制", description="TCP flow control")
    other_node = KnowledgeNode(name="TCP 确认号", description="ACK")
    db_session.add_all([error_node, other_node])
    await db_session.flush()

    regular_day_two = Task(
        user_id=user.id,
        plan_id=plan.id,
        title="Day 2 · 计网 - TCP 确认号",
        type=TaskType.LEARNING,
        tags=["day:2"],
        estimated_minutes=45,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=1,
        order_index=2000,
        knowledge_node_id=other_node.id,
    )
    db_session.add(regular_day_two)
    await db_session.flush()
    db_session.add(
        TaskKnowledgeLink(
            task_id=regular_day_two.id,
            knowledge_node_id=other_node.id,
            relation_type="focus",
            is_primary=True,
        )
    )
    await db_session.commit()

    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    first = await manager._insert_repair_task(
        db=db_session,
        plan_id=plan.id,
        next_day=2,
        error_node_id=error_node.id,
        error_cause_category="concept_confusion",
    )
    second = await manager._insert_repair_task(
        db=db_session,
        plan_id=plan.id,
        next_day=2,
        error_node_id=error_node.id,
        error_cause_category="concept_confusion",
    )

    assert first is not None
    assert second is not None
    assert second.id == first.id

    task_rows = await db_session.execute(
        select(Task).where(Task.plan_id == plan.id).order_by(Task.order_index.asc(), Task.created_at.asc())
    )
    tasks = list(task_rows.scalars().all())
    repair_tasks = [task for task in tasks if (task.guide_json or {}).get("task_kind") == "targeted_repair"]

    assert len(repair_tasks) == 1
    assert tasks[0].id == first.id
    assert repair_tasks[0].title == "修复昨日错题：TCP 滑动窗口机制"
    assert repair_tasks[0].estimated_minutes == 15
    assert repair_tasks[0].order_index == 2000
    assert repair_tasks[0].guide_json["daily_spec"]["task_kind"] == "targeted_repair"
    assert repair_tasks[0].guide_json["output_action"] == "闭卷复述错因 + 1 道同类题独立完成"


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


@pytest.mark.asyncio
async def test_exam_sprint_fast_track_single_message_enters_planning_with_pack_prefill(monkeypatch) -> None:
    from app.orchestration import bottleneck_analyzer as bottleneck_module

    monkeypatch.setattr(
        bottleneck_module.bottleneck_analyzer,
        "analyze",
        AsyncMock(side_effect=RuntimeError("force deterministic fallback")),
    )

    redis = FakeRedis()
    manager = PlanningWorkflowManager(redis_client=redis)
    user_id = uuid4()
    conversation_id = "chat-session-fast-track"

    result = await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=user_id,
        chat_session_id=conversation_id,
        message="7天后考计算机网络，没学过，每天2小时",
        context={},
    )

    persisted = await manager.get_active_session(conversation_id)

    assert result is not None
    assert persisted is not None
    assert persisted.state == "PLANNING"
    assert persisted.collected["subject"] == "计算机网络"
    assert "Sprint Pack 默认范围" in persisted.collected["exam_scope"]
    assert persisted.collected["knowledge_baseline"] == "完全没学过"
    assert persisted.collected["time_available"] == "每天约 2 小时"
    assert persisted.collected["sprint_pack_id"] == "computer_networks@v1"
    assert persisted.confirmed_strategy is not None

    day_one_spec = manager._daily_task_specs(
        persisted.confirmed_strategy["phases"][0],
        phase_index=1,
        session=persisted,
    )[0]
    assert day_one_spec["day"] == 1
    assert day_one_spec["task_kind"] == "diagnostic_triage"
