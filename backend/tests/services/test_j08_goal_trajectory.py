"""J-08 · Goal Completion → Reflection → Trajectory —— 想法到成果全链（真实 DB）.

卡面 acceptance 逐条红测：
- **轨迹链每环真实数据流断言（零断点）**：action 完成（TaskService.complete
  真实管线）→ artifact/outcome（X-08 capture 广播 + D-02 账本可查询 + J-06
  产物行）→ goal milestone（轨迹面从真实任务行推导 reached + outcome 身份）→
  reflection（TaskReflectionService.submit_reflection_answer 真实落库）→
  experience candidate（EpisodicMemory 真实行，M-03 候选契约字段）→ Galaxy
  （G-02 真实吸收器点亮 + provenance 落行）——每环断言真实 DB 行，不 mock 业务。
- **两面同源（GJ03/GJ05 形成 outcome）**：Goal 轨迹面与星图面
  （``NodeWithStatus.graph_event_sources``）经同一投影函数读同一 provenance
  行，同一 outcome id 在两面呈现；账本（D-02）身份、吸收溯源、两面投影
  四方一致（同一 outcome 在两面呈现数据同源断言）。
- **反思零性格断言负测**：确定性反思面（模板问句/选项/字段、连接回应、记忆
  摘要、零事件上下文）扫描人格断言模式必须零命中；反思内容基于真实事件数据
  （真实卡点回声；零事件时显式 ``no recent decisions found``，不凭空编造）。
- **契约锁（已合规面，如实标注）**：outcome 身份单一推导——X-08
  ``derive_outcome_id`` = D-02 账本 id = G-02 溯源 reference_id；本卡不新建
  第二套身份/真源，锁防未来漂移。

传输层说明：Redis 事件总线为外部设施，测试以记录桩替换（仅传输层；被测行为
= 完成管线 / 吸收器 / 账本 / 反思服务 / 轨迹投影，全部真实 DB）。
CognitiveService 片段面按既有 ``test_task_reflection_service`` 先例隔离
（episodic memory 写入本身真实执行并断言）。
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.outcome_ledger import OutcomeSource, derive_outcome_id, outcome_key
from app.core.run_state_machine import RunStatus
from app.models.agent_run import AgentRun
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.goal import Goal
from app.models.hybrid_journey import HybridJourneyArtifact
from app.models.memory import EpisodicMemory
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_feedback import TaskFeedback
from app.schemas.galaxy import NodeWithStatus
from app.services.galaxy.outcome_absorption_service import (
    OUTCOME_EVIDENCE_AUDIT_REASON,
    OUTCOME_PROVENANCE_SOURCE_TYPE,
    GalaxyOutcomeAbsorber,
)
from app.services.outcome_capture_service import (
    OUTCOME_RECORDED_EVENT,
    build_task_outcome_capture,
)
from app.services.outcome_ledger_service import OutcomeLedgerService
from app.services.task_reflection_service import TaskReflectionService
from app.services.task_service import TaskService
from tests.golden.north_star_wvpl_fixture import _fid as fixture_id
from tests.golden.north_star_wvpl_fixture import (
    file_evidence as _file_evidence,
)
from tests.golden.north_star_wvpl_fixture import (
    make_user as _make_user,
)

pytestmark = pytest.mark.asyncio


def _naive_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# 传输层记录桩（与 test_x08_outcome_ledger_gj 同款；仅替换传输，行为全真）
# ---------------------------------------------------------------------------


class _RecordingBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, event_type, payload, stream="sparkle_events"):
        self.published.append((event_type, dict(payload)))
        return "msg-id"


@pytest.fixture()
def recording_bus(monkeypatch):
    from app.core.event_bus import event_bus
    from app.services import outcome_capture_service

    bus = _RecordingBus()
    monkeypatch.setattr(outcome_capture_service, "event_bus_reliable", bus)

    async def _record_publish(event_type, payload, stream="sparkle_events"):
        bus.published.append((event_type, dict(payload)))
        return "msg-id"

    monkeypatch.setattr(event_bus, "publish", _record_publish)
    return bus


async def _ensure_mastery_audit_log(db_session) -> None:
    await db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS mastery_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                old_mastery INTEGER NOT NULL,
                new_mastery INTEGER NOT NULL,
                reason TEXT,
                request_id TEXT,
                revision INTEGER DEFAULT 1,
                created_at DATETIME NOT NULL
            )
        """))
    await db_session.commit()


# ---------------------------------------------------------------------------
# Fixtures：带里程碑元数据的目标 + 计划 + 里程碑任务（goals.py 创建流同构）
# ---------------------------------------------------------------------------

_MILESTONES = [
    {
        "id": "m1",
        "title": "画出能量流向图",
        "description": "把热力学第一定律画成能量流向图",
        "estimated_days": 7,
        "acceptance_criteria": ["图上标注每个能量项"],
    },
    {
        "id": "m2",
        "title": "完成一组代表题",
        "description": "选 5 道代表题做完并批改",
        "estimated_days": 7,
        "acceptance_criteria": ["5 道题全部批改"],
    },
]

_MOTIVATION = "能在考试里用能量守恒解题"


async def _milestone_goal_plan(db_session, user, *, gid: int, pid: int) -> tuple[Goal, Plan]:
    goal = Goal(
        id=fixture_id(gid),
        user_id=user.id,
        title="吃透热力学",
        goal_type="skill",
        status="active",
        metadata_payload={
            "creation_wizard": {
                "motivation": _MOTIVATION,
                "time_horizon": "medium",
                "milestones": _MILESTONES,
                "created_at": _naive_now().isoformat(),
            }
        },
    )
    db_session.add(goal)
    await db_session.flush()
    plan = Plan(
        id=fixture_id(pid),
        user_id=user.id,
        name="吃透热力学",
        type=PlanType.GROWTH,
        goal_id=goal.id,
    )
    db_session.add(plan)
    await db_session.commit()
    goal.plan_id = plan.id
    db_session.add(goal)
    await db_session.commit()
    await db_session.refresh(plan)
    return goal, plan


async def _milestone_task(
    db_session,
    user,
    plan: Plan,
    *,
    title: str,
    tags: list[str],
    node: KnowledgeNode | None = None,
    status: TaskStatus = TaskStatus.IN_PROGRESS,
    tid: int | None = None,
) -> Task:
    from app.core.action_plan import ACTION_PLAN_SCHEMA_VERSION

    task = Task(
        id=fixture_id(tid) if tid is not None else None,
        user_id=user.id,
        title=title,
        type=TaskType.LEARNING,
        estimated_minutes=25,
        plan_id=plan.id,
        tags=tags,
        status=status,
        knowledge_node_id=node.id if node is not None else None,
        action_schema_version=ACTION_PLAN_SCHEMA_VERSION,
        desired_outcome="完成并留下证据",
        smallest_useful_step={"description": "产出", "useful_because": ["produces_artifact"]},
        execution_mode="human",
        cognitive_ownership="user_core",
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


def _last_outcome_payload(bus: _RecordingBus) -> dict:
    payloads = [p for e, p in bus.published if e == OUTCOME_RECORDED_EVENT]
    assert payloads, "完成管线必须广播 outcome.recorded"
    return payloads[-1]


def _find_task_entry(entries, task_id):
    for entry in entries:
        if entry.source.value == "task_completion" and entry.source_id == str(task_id):
            return entry
    return None


async def _patch_cognitive_fragment(monkeypatch) -> None:
    async def fake_create_fragment(self, **kwargs):
        return SimpleNamespace(id=uuid4())

    async def fake_analyze_behavior(self, user_id, fragment_id):
        return {"ok": True}

    monkeypatch.setattr(
        "app.services.task_reflection_service.CognitiveService.create_fragment",
        fake_create_fragment,
    )
    monkeypatch.setattr(
        "app.services.task_reflection_service.CognitiveService.analyze_behavior",
        fake_analyze_behavior,
    )


# ---------------------------------------------------------------------------
# 全链：action → outcome → milestone → reflection → experience candidate → Galaxy
# ---------------------------------------------------------------------------


async def test_j08_trajectory_full_chain_no_break(db_session, recording_bus, monkeypatch):
    """轨迹链每环真实数据流断言：完成到 Galaxy 更新全链不断点 + 两面同源."""
    await _ensure_mastery_audit_log(db_session)
    user = await _make_user(db_session, uid=8201)
    goal, plan = await _milestone_goal_plan(db_session, user, gid=8201, pid=8201)
    node = KnowledgeNode(name="热力学第一定律", importance_level=3, is_seed=True)
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)

    task1 = await _milestone_task(
        db_session,
        user,
        plan,
        title=_MILESTONES[0]["title"],
        tags=["goal_first_step"],
        node=node,
        tid=8202,
    )
    task2 = await _milestone_task(
        db_session,
        user,
        plan,
        title=_MILESTONES[1]["title"],
        tags=["goal_milestone"],
        tid=8203,
        status=TaskStatus.PENDING,
    )
    await _file_evidence(db_session, user, task1, fid=8202)

    # ---- 环1 action → artifact/outcome：真实完成管线（GJ03 面）----
    completed = await TaskService.complete(db_session, task1, 25)
    assert completed.status == TaskStatus.COMPLETED
    outcome_id = derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=task1.id)
    payload = _last_outcome_payload(recording_bus)
    assert payload["outcome_id"] == outcome_id
    assert payload["polarity"] == "positive"
    assert payload["correlation_plan_id"] == str(plan.id)

    # D-02 账本可查询：outcome 真实形成（truth=actual、document:// 证据已核）
    ledger = OutcomeLedgerService(db_session)
    page = await ledger.query(user_id=user.id, source=OutcomeSource.TASK_COMPLETION)
    ledger_entry = _find_task_entry(page.items, task1.id)
    assert ledger_entry is not None, "GJ03 outcome 必须在账本可查询"
    assert ledger_entry.outcome_id == outcome_id
    assert ledger_entry.truth_class.value == "actual"
    assert ledger_entry.polarity.value == "positive"

    # ---- 环2 outcome → Galaxy：真实 G-02 吸收器点亮（GJ05 面）----
    absorber = GalaxyOutcomeAbsorber(db_session)
    absorption = await absorber.absorb_outcome(payload)
    assert absorption.action == "lit"
    assert absorption.mastery_by_node[str(node.id)] > 0
    evidence_rows = (
        await db_session.execute(
            text("SELECT reason, request_id FROM mastery_audit_log WHERE node_id = :node_id"),
            {"node_id": str(node.id)},
        )
    ).fetchall()
    assert any(
        OUTCOME_EVIDENCE_AUDIT_REASON in str(row.reason) for row in evidence_rows
    ), "吸收必须留下 append-only 证据行（点亮硬门）"

    # ---- 环3 goal milestone：里程碑任务完成即达成（轨迹面推导，真实任务行）----
    # ---- 环4+5 reflection → experience candidate：真实反思提交 + 真实记忆行 ----
    await _patch_cognitive_fragment(monkeypatch)
    feedback = TaskFeedback(user_id=user.id, task_id=task1.id, category="too_difficult")
    db_session.add(feedback)
    await db_session.commit()
    await db_session.refresh(feedback)

    reflection_service = TaskReflectionService(db_session, redis=None)
    stuck_point = "公式会背，但不知道什么时候套用能量守恒"
    reflection_payload = await reflection_service.submit_reflection_answer(
        user_id=user.id,
        feedback_id=feedback.id,
        selected_option="概念没理解",
        free_text=None,
        stuck_point=stuck_point,
        effective_method="先画能量流向图",
        adjustment_intention="下次先做一道代表题",
    )
    assert reflection_payload["status"] == "completed"
    await db_session.refresh(feedback)
    memory_id = feedback.reflection_payload["memory_id"]
    assert memory_id, "反思必须落 experience candidate（episodic memory）"
    memory = await db_session.get(EpisodicMemory, memory_id)
    assert memory is not None
    assert memory.source_type == "reflection"
    assert memory.source_id == str(feedback.id)
    assert "能量流向图" in memory.summary  # 真实事件数据回声，非凭空编造

    # ---- 环6 J-06 artifact 面：真实交付回执行（真实模型行 fixture）----
    run = AgentRun(
        user_id=user.id,
        task_id=task1.id,
        objective="J-08 轨迹产物 run",
        allowed_tools=[],
        permissions={},
        budget={},
        completion_condition={},
        status=RunStatus.SUCCEEDED,
        heartbeat_at=_naive_now(),
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    artifact = HybridJourneyArtifact(
        user_id=user.id,
        run_id=run.id,
        task_id=task1.id,
        stage="outcome",
        artifact_kind="delivery_receipt",
        citations=[],
        source_refs=[{"scheme": "task", "ref": str(task1.id)}],
        payload={"task_id": str(task1.id), "task_status": "COMPLETED"},
        schema_version="hybrid_journey.v1",
    )
    db_session.add(artifact)
    await db_session.commit()

    # ---- 轨迹面：全链投影（Goal 页面数据源）----
    from app.services.goal_trajectory_service import build_goal_trajectory

    trajectory = await build_goal_trajectory(db_session, user_id=user.id, goal_id=goal.id)

    # 环0 想法：真实目标行 + 真实动机元数据
    idea = trajectory["idea"]
    assert idea["goal_id"] == str(goal.id)
    assert idea["title"] == "吃透热力学"
    assert idea["motivation"] == _MOTIVATION

    # 环3 milestone：真实任务行推导 reached + outcome 身份
    milestones = {m["title"]: m for m in trajectory["milestones"]}
    assert milestones[_MILESTONES[0]["title"]]["reached"] is True
    assert milestones[_MILESTONES[0]["title"]]["task_id"] == str(task1.id)
    assert milestones[_MILESTONES[0]["title"]]["outcome_id"] == outcome_id
    assert milestones[_MILESTONES[1]["title"]]["reached"] is False

    # 环1 outcome 面：账本核验（ledger_verified 走真实 D-02 查询）
    outcomes = trajectory["outcomes"]
    traj_outcome = next(o for o in outcomes if o["task_id"] == str(task1.id))
    assert traj_outcome["outcome_id"] == outcome_id == ledger_entry.outcome_id
    assert traj_outcome["ledger_verified"] is True
    assert traj_outcome["polarity"] == "positive"
    assert traj_outcome["ledger_truth"] == "actual"
    assert traj_outcome["evidence_count"] >= 1

    # 环6 artifact 面：真实 J-06 产物行进轨迹
    traj_artifact = next((a for a in trajectory["artifacts"] if a["task_id"] == str(task1.id)), None)
    assert traj_artifact is not None, "J-06 产物必须进入轨迹（artifact 环）"
    assert traj_artifact["artifact_kind"] == "delivery_receipt"
    assert traj_artifact["stage"] == "outcome"

    # 环4 reflection 面：真实用户反思数据（零性格推断，只投影用户自报）
    reflections = trajectory["reflections"]
    assert len(reflections) == 1
    assert reflections[0]["stuck_point"] == stuck_point
    assert reflections[0]["effective_method"] == "先画能量流向图"
    assert reflections[0]["memory_id"] == memory_id

    # 环5 experience candidate 面：真实 episodic memory 行（M-03 候选契约字段）
    candidates = trajectory["experience_candidates"]
    assert len(candidates) == 1
    assert candidates[0]["id"] == memory_id
    assert candidates[0]["source_type"] == "reflection"
    assert "能量流向图" in candidates[0]["summary"]

    # ---- 两面同源：Goal 轨迹面 == 星图面（同一 provenance 行、同一投影函数）----
    status_row = await db_session.get(UserNodeStatus, (user.id, node.id))
    assert status_row is not None
    star_map_sources = NodeWithStatus._graph_event_sources(status_row)  # 星图面投影
    galaxy_face = trajectory["galaxy"]
    traj_galaxy = next(g for g in galaxy_face if g["node_id"] == str(node.id))
    assert (
        traj_galaxy["graph_event_sources"] == star_map_sources
    ), "两面必须读同一 provenance 行（同一投影函数、同一数据）"
    star_outcome_ids = {
        str(s["reference_id"]) for s in star_map_sources if s.get("source_type") == OUTCOME_PROVENANCE_SOURCE_TYPE
    }
    assert outcome_id in star_outcome_ids, "同一 outcome 必须在星图面呈现"
    assert traj_galaxy["outcome_ids"] == [outcome_id]
    # 四方一致：X-08 身份 = D-02 账本 = G-02 溯源 = 轨迹面
    assert outcome_id == ledger_entry.outcome_id
    assert outcome_id in star_outcome_ids

    # ---- 价值叙事：证据与成果计数，分钟/streak 不作主叙事（work 3）----
    value = trajectory["value_summary"]
    assert value["outcomes_formed"] == 1
    assert value["milestones_reached"] == 1
    assert value["reflections"] == 1
    assert value["experience_candidates"] == 1
    assert value["artifacts"] == 1
    assert value["galaxy_nodes_lit"] == 1
    blob = json.dumps(trajectory, ensure_ascii=False)
    assert "streak" not in blob.lower()
    assert "total_minutes" not in blob.lower()
    assert "actual_minutes" not in blob.lower()

    # 未完成任务不产生 outcome（失败不点亮成果叙事）
    assert all(o["task_id"] != str(task2.id) for o in outcomes)


# ---------------------------------------------------------------------------
# 诚实失败面：无目标 / 越权目标
# ---------------------------------------------------------------------------


async def test_j08_trajectory_requires_goal(db_session):
    from app.services.goal_trajectory_service import NoActiveGoalError, build_goal_trajectory

    user = await _make_user(db_session, uid=8211)
    with pytest.raises(NoActiveGoalError):
        await build_goal_trajectory(db_session, user_id=user.id)


async def test_j08_trajectory_rejects_foreign_goal(db_session):
    from app.services.goal_trajectory_service import GoalNotFoundError, build_goal_trajectory

    owner = await _make_user(db_session, uid=8212)
    outsider = await _make_user(db_session, uid=8213)
    goal = Goal(user_id=owner.id, title="别人的目标", goal_type="skill", status="active")
    db_session.add(goal)
    await db_session.commit()

    with pytest.raises(GoalNotFoundError):
        await build_goal_trajectory(db_session, user_id=outsider.id, goal_id=goal.id)


# ---------------------------------------------------------------------------
# 反思零性格断言负测（反思基于真实事件数据）
# ---------------------------------------------------------------------------

_PERSONALITY_ASSERTION_PATTERNS = [
    re.compile(pattern)
    for pattern in [
        r"你是[个一]",
        r"你(天生|本质|向来|总是|从来|一向|就是)",
        r"性格",
        r"人格",
        r"内向|外向",
        r"拖延症",
        r"不自律",
        r"你很懒|你太懒",
        r"你属于.{0,6}(型|类)",
        r"你是一?个?.{0,4}(的人|型的人)",
        r"you are (a|an|the kind of)",
        r"your personality",
    ]
]


def _assert_no_personality_assertion(text_value: str, *, face: str) -> None:
    for pattern in _PERSONALITY_ASSERTION_PATTERNS:
        match = pattern.search(text_value)
        assert match is None, f"反思面 {face} 出现性格断言: {match!r} in {text_value!r}"


async def test_reflection_surfaces_never_assert_personality(db_session, monkeypatch):
    """零性格断言负测：全部确定性反思面无人格断言；内容基于真实事件数据."""
    await _patch_cognitive_fragment(monkeypatch)
    user = await _make_user(db_session, uid=8221)

    # 1) 模板问句/选项/字段（反思提示面的全部静态文案）
    service = TaskReflectionService(db_session, redis=None)
    for category, template in TaskReflectionService.PROMPT_TEMPLATES.items():
        _assert_no_personality_assertion(str(template["question"]), face=f"template:{category}")
        for option in template["options"]:
            _assert_no_personality_assertion(str(option), face=f"template-option:{category}")
        prompt = await service._build_prompt(
            category=category,
            task_id=uuid4(),
            plan_id=None,
            feedback_id=None,
            user_id=user.id,
            task_title="任何任务",
        )
        for field in prompt["fields"]:
            _assert_no_personality_assertion(str(field["label"]), face=f"field-label:{category}")
            _assert_no_personality_assertion(str(field["hint"]), face=f"field-hint:{category}")
        _assert_no_personality_assertion(str(prompt["question"]), face=f"prompt-question:{category}")

    # 2) 连接回应（确定性生成面）：全形状矩阵扫描
    task = Task(
        user_id=user.id,
        title="热力学公式练习",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=20,
        difficulty=3,
    )
    db_session.add(task)
    await db_session.commit()
    structured_grid = [
        {},
        {"stuck_point": "状态方程不会用", "effective_method": None, "adjustment_intention": None},
        {"stuck_point": None, "effective_method": "画图", "adjustment_intention": None},
        {"stuck_point": None, "effective_method": None, "adjustment_intention": "先做代表题"},
        {"stuck_point": "卡在边界条件", "effective_method": "画图", "adjustment_intention": "先做代表题"},
    ]
    previous_variants = [[], [{"id": "m1", "summary": "之前卡在单位换算", "occurred_at": None}]]
    node_variants = [[], [{"id": "n1", "name": "热力学第一定律", "source": "task_primary", "confidence": 0.9}]]
    for structured in structured_grid:
        for previous in previous_variants:
            for linked in node_variants:
                response = service._build_connection_response(
                    task=task,
                    structured=structured,
                    linked_nodes=linked,
                    recent_reflections=previous,
                )
                _assert_no_personality_assertion(response, face="connection_response")
                summary = service._build_reflection_memory_summary(
                    task=task, structured=structured, linked_nodes=linked
                )
                _assert_no_personality_assertion(summary, face="memory_summary")

    # 3) 真实提交的反思回应只回声真实事件数据（含真实卡点，不新增人格判断）
    feedback = TaskFeedback(user_id=user.id, task_id=task.id, category="too_difficult")
    db_session.add(feedback)
    await db_session.commit()
    await db_session.refresh(feedback)
    stuck_point = "不知道什么时候套用状态方程"
    payload = await service.submit_reflection_answer(
        user_id=user.id,
        feedback_id=feedback.id,
        selected_option=None,
        free_text=None,
        stuck_point=stuck_point,
        effective_method=None,
        adjustment_intention=None,
    )
    _assert_no_personality_assertion(str(payload["ai_response"]), face="submitted_ai_response")
    _assert_no_personality_assertion(str(payload["prompt"]["question"]), face="submitted_prompt")
    assert stuck_point in str(payload["ai_response"]), "反思回应必须基于真实事件数据（回声真实卡点）"

    # 4) 零事件上下文：不凭空编造事件（显式 no recent decisions + confidence 0.0）
    context = await service._build_reflection_context(
        user_id=user.id,
        trigger="milestone_reached",
        trigger_payload={},
    )
    assert context["route_history_context_entry_count"] == 1
    assert "no recent decisions found" in context["route_history_context"]
    assert "confidence=0.0;" in context["route_history_context"]


async def test_reflection_triggered_context_requires_real_events(db_session):
    """反思上下文只来自真实 route history 行；无行时零编造（有行时回声真实行）."""
    from app.models.aurora_stage20 import RoutingDecisionLog

    user = await _make_user(db_session, uid=8222)
    service = TaskReflectionService(db_session, redis=None)

    empty = await service._build_reflection_context(user_id=user.id, trigger="plan_completed", trigger_payload={})
    assert "no recent decisions found" in empty["route_history_context"]

    now = _naive_now()
    entry = RoutingDecisionLog(
        user_id=user.id,
        decision_type="task_route",
        decision_payload={"mode": "human"},
        source_state_v2_key="state:human",
        input_aggregator_snapshot_id="snap-j08",
        decided_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(entry)
    await db_session.commit()

    filled = await service._build_reflection_context(user_id=user.id, trigger="plan_completed", trigger_payload={})
    assert f"decision={entry.decision_type}" in filled["route_history_context"], "反思上下文必须回声真实事件行"


# ---------------------------------------------------------------------------
# 契约锁（已合规面，如实标注）：outcome 身份单一推导，本卡零新身份
# ---------------------------------------------------------------------------


async def test_contract_lock_outcome_identity_single_derivation(db_session, recording_bus):
    """X-08 身份 = D-02 账本 id = G-02 溯源 reference_id（已有合规面，防漂移锁）."""
    await _ensure_mastery_audit_log(db_session)
    user = await _make_user(db_session, uid=8231)
    node = KnowledgeNode(name="契约锁节点", importance_level=3, is_seed=True)
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)

    task = Task(
        id=fixture_id(8232),
        user_id=user.id,
        title="契约锁任务",
        type=TaskType.LEARNING,
        estimated_minutes=25,
        status=TaskStatus.IN_PROGRESS,
        knowledge_node_id=node.id,
        tags=["goal_milestone"],
    )
    db_session.add(task)
    await db_session.commit()
    await _file_evidence(db_session, user, task, fid=8232)

    capture_identity = derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=task.id)
    assert capture_identity == derive_outcome_id(
        source=OutcomeSource.TASK_COMPLETION, source_id=task.id
    ), "身份推导必须确定性（同输入同 id）"

    await TaskService.complete(db_session, task, 20)
    capture = build_task_outcome_capture(task)
    derived = capture.outcome_id
    assert derived == capture_identity, "完成前后身份必须同一推导函数产出"
    assert capture.outcome_key == outcome_key(OutcomeSource.TASK_COMPLETION, task.id)
    payload = _last_outcome_payload(recording_bus)
    assert payload["outcome_id"] == derived

    ledger_entry = _find_task_entry(
        (await OutcomeLedgerService(db_session).query(user_id=user.id, source=OutcomeSource.TASK_COMPLETION)).items,
        task.id,
    )
    assert ledger_entry is not None and ledger_entry.outcome_id == derived

    absorption = await GalaxyOutcomeAbsorber(db_session).absorb_outcome(payload)
    assert absorption.action == "lit"
    status_row = await db_session.get(UserNodeStatus, (user.id, node.id))
    provenance = NodeWithStatus._graph_event_sources(status_row)
    assert any(
        str(s.get("reference_id")) == derived and s.get("source_type") == OUTCOME_PROVENANCE_SOURCE_TYPE
        for s in provenance
    ), "G-02 溯源 reference_id 必须与账本身份同源"


# ---------------------------------------------------------------------------
# 轨迹面投影契约：与星图同一 provenance 读函数（同源的结构性保证）
# ---------------------------------------------------------------------------


async def test_contract_lock_trajectory_reads_same_provenance_projection(db_session):
    """轨迹面与星图面共用 read_graph_event_sources（同一函数 = 同一数据）."""
    from app.services.galaxy.provenance import append_graph_event_source, read_graph_event_sources

    user = await _make_user(db_session, uid=8241)
    status_row = UserNodeStatus(user_id=user.id, node_id=fixture_id(8242), mastery_score=42.0, is_unlocked=True)
    append_graph_event_source(
        status_row,
        event_type=OUTCOME_RECORDED_EVENT,
        source_type=OUTCOME_PROVENANCE_SOURCE_TYPE,
        reference_id="outc_contractlock",
        label="positive",
        payload={"outcome_id": "outc_contractlock"},
    )
    db_session.add(status_row)
    await db_session.commit()
    await db_session.refresh(status_row)

    via_helper = read_graph_event_sources(status_row)
    via_star_map = NodeWithStatus._graph_event_sources(status_row)
    assert via_helper == via_star_map, "两面必须共用同一投影函数（结构性同源）"
    assert via_helper[0]["reference_id"] == "outc_contractlock"
