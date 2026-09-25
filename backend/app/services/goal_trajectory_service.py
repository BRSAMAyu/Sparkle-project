"""J-08 · Goal Trajectory —— 「想法 → 成果」全链只读投影（零新真源、零新表）.

定位（J 链收官卡）：把成果完成后的价值累积做成**可呈现的轨迹**——
``action → artifact/outcome → goal milestone → reflection → experience
candidate → Galaxy`` 每一环都从**既有真源**读侧行投影，本模块零写入、
零 LLM、零 schema 变更：

1. **不重建真源（卡面 forbidden #1）**：
   - outcome 事实 → D-02 ``OutcomeLedgerService``（五源读模型，查询时点
     重算）+ X-08 ``derive_outcome_id``（**同一身份函数**，不引入第二套
     身份推导——契约锁见 ``tests/services/test_j08_goal_trajectory.py``）；
   - artifact → J-06 ``HybridJourneyArtifact`` 产物行；
   - milestone → Goal ``metadata_payload["creation_wizard"]["milestones"]``
     + 计划下 ``goal_first_step``/``goal_milestone`` 标签任务行（达成判定
     = 真实任务行终态，不另立里程碑状态存储）；
   - reflection → ``TaskFeedback.reflection_payload``（用户真实提交的结构
     化反思，只投影不推断——零性格断言，红线见负测）；
   - experience candidate → ``EpisodicMemory``（``source_type="reflection"``
     的真实记忆行，M-03 预筛候选契约字段投影）；
   - Galaxy → G-02 吸收后 ``UserNodeStatus.learning_path_snapshot``
     的 provenance 行，经 ``provenance.read_graph_event_sources`` 读取
     ——**与星图面（``NodeWithStatus.graph_event_sources``）同一投影
     函数**，同一 outcome 在两面呈现数据同源是结构性保证。
2. **价值叙事 = 证据与成果，非时长统计（卡面 work 3）**：``value_summary``
   只含成果/证据/反思/候选/点亮计数；分钟与 streak 不进轨迹主叙事。
3. **诚实失败**：无活跃目标 → ``NoActiveGoalError``（路由面 422）；
   目标不存在/非本人 → ``GoalNotFoundError``（路由面 404）。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.outcome_ledger import OutcomePolarity, OutcomeSource, derive_outcome_id, outcome_key
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.goal import Goal
from app.models.hybrid_journey import HybridJourneyArtifact
from app.models.memory import EpisodicMemory
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.models.task_feedback import TaskFeedback
from app.models.task_resources import TaskKnowledgeLink
from app.services.galaxy.provenance import read_graph_event_sources
from app.services.outcome_ledger_service import OutcomeLedgerService

GOAL_TRAJECTORY_SCHEMA_VERSION = "goal_trajectory.v1"

#: goals.py 创建流写入的里程碑任务标签（达成判定的任务锚）。
MILESTONE_TASK_TAGS = frozenset({"goal_first_step", "goal_milestone"})

#: D-02 账本轮询上限（轨迹面核验窗口；计划任务数远小于该值）。
_LEDGER_SCAN_LIMIT = 200

#: 单目标轨迹各环展示上限（轨迹是叙事面，不是全量导出）。
_TRAJECTORY_RING_CAP = 20


class NoActiveGoalError(Exception):
    """用户没有可归属轨迹的活跃目标（路由面 → 422 no_active_goal）。"""


class GoalNotFoundError(Exception):
    """目标不存在或不属于该用户（路由面 → 404 goal_not_found）。"""


async def build_goal_trajectory(
    db: AsyncSession,
    *,
    user_id: UUID | str,
    goal_id: UUID | str | None = None,
) -> dict[str, Any]:
    """组装「想法 → 成果」轨迹（全环真实数据，只读）。"""
    user_uuid = UUID(str(user_id))
    goal = await _resolve_goal(db, user_id=user_uuid, goal_id=goal_id)
    plan = await _load_plan(db, goal)
    tasks = await _load_plan_tasks(db, user_id=user_uuid, plan_id=plan.id) if plan else []
    task_ids = [task.id for task in tasks]

    metadata_raw = goal.metadata_payload
    metadata: dict[str, Any] = metadata_raw if isinstance(metadata_raw, dict) else {}
    wizard_raw = metadata.get("creation_wizard")
    wizard: dict[str, Any] = wizard_raw if isinstance(wizard_raw, dict) else {}
    milestones_raw = wizard.get("milestones")
    wizard_milestones: list[Any] = milestones_raw if isinstance(milestones_raw, list) else []

    ledger_index = await _ledger_task_index(db, user_id=user_uuid)
    outcomes_by_task = _outcome_face(tasks=tasks, ledger_index=ledger_index)
    milestones_face = _milestones_face(
        wizard_milestones=wizard_milestones,
        tasks=tasks,
        outcomes_by_task=outcomes_by_task,
    )
    artifacts_face = await _artifacts_face(db, user_id=user_uuid, task_ids=task_ids)
    reflections_face = await _reflections_face(db, task_ids=task_ids)
    candidates_face = await _experience_candidates_face(db, user_id=user_uuid, task_ids=task_ids)
    galaxy_face = await _galaxy_face(db, user_id=user_uuid, tasks=tasks)
    outcomes = list(outcomes_by_task.values())

    return {
        "version": GOAL_TRAJECTORY_SCHEMA_VERSION,
        "idea": _idea_face(goal=goal, wizard=wizard),
        "milestones": milestones_face,
        "outcomes": outcomes[:_TRAJECTORY_RING_CAP],
        "artifacts": artifacts_face,
        "reflections": reflections_face,
        "experience_candidates": candidates_face,
        "galaxy": galaxy_face,
        "value_summary": {
            "milestones_reached": sum(1 for item in milestones_face if item.get("reached")),
            "milestones_total": len(milestones_face),
            "outcomes_formed": sum(1 for item in outcomes if item.get("ledger_verified")),
            # 失败留痕（NEGATIVE outcome 保留不丢弃——X-08 纪律的轨迹面呈现）
            "outcomes_record_kept": sum(
                1 for item in outcomes if item.get("polarity") == OutcomePolarity.NEGATIVE.value
            ),
            "artifacts": len(artifacts_face),
            "reflections": len(reflections_face),
            "experience_candidates": len(candidates_face),
            "galaxy_nodes_lit": sum(1 for item in galaxy_face if item.get("is_unlocked")),
        },
    }


# ---------------------------------------------------------------------------
# 目标解析（J-04/J-06 同判据：显式 id → 本人校验；缺省 → 最近活跃目标）
# ---------------------------------------------------------------------------


async def _resolve_goal(db: AsyncSession, *, user_id: UUID, goal_id: UUID | str | None) -> Goal:
    if goal_id is not None:
        try:
            parsed = UUID(str(goal_id))
        except (ValueError, AttributeError) as exc:
            raise GoalNotFoundError from exc
        result = await db.execute(
            select(Goal).where(
                Goal.id == parsed,
                Goal.user_id == user_id,
                Goal.deleted_at.is_(None),
            )
        )
        goal = result.scalar_one_or_none()
        if goal is None:
            raise GoalNotFoundError
        return goal

    result = await db.execute(
        select(Goal)
        .where(Goal.user_id == user_id, Goal.status == "active", Goal.deleted_at.is_(None))
        .order_by(Goal.created_at.desc())
        .limit(1)
    )
    goal = result.scalars().first()
    if goal is None:
        raise NoActiveGoalError
    return goal


async def _load_plan(db: AsyncSession, goal: Goal) -> Plan | None:
    if goal.plan_id is None:
        return None
    result = await db.execute(
        select(Plan).where(
            Plan.id == goal.plan_id,
            Plan.user_id == goal.user_id,
            Plan.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def _load_plan_tasks(db: AsyncSession, *, user_id: UUID, plan_id: UUID) -> list[Task]:
    result = await db.execute(
        select(Task)
        .where(
            Task.user_id == user_id,
            Task.plan_id == plan_id,
            Task.deleted_at.is_(None),
        )
        .order_by(Task.created_at.asc(), Task.id.asc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# 各环投影（全部只读；数据源见模块 docstring）
# ---------------------------------------------------------------------------


def _idea_face(goal: Goal, *, wizard: dict[str, Any]) -> dict[str, Any]:
    motivation = str(wizard.get("motivation") or "").strip()
    return {
        "goal_id": str(goal.id),
        "title": goal.title,
        "goal_type": goal.goal_type,
        "status": goal.status,
        "target_date": goal.target_date.isoformat() if goal.target_date else None,
        # 想法面：用户建目标时的真实动机（无则回退描述，不编造）
        "motivation": motivation or (goal.description or ""),
        "created_at": goal.created_at.isoformat() if goal.created_at else None,
    }


def _milestone_tag_of(task: Task) -> str | None:
    tags = {str(tag or "").strip() for tag in (task.tags or [])}
    for tag in ("goal_first_step", "goal_milestone"):
        if tag in tags:
            return tag
    return None


def _milestones_face(
    *,
    wizard_milestones: list[Any],
    tasks: list[Task],
    outcomes_by_task: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """里程碑环：元数据草案 × 计划里程碑任务行（达成 = 真实任务行终态）。"""
    milestone_tasks = [task for task in tasks if _milestone_tag_of(task) is not None]
    faces: list[dict[str, Any]] = []

    def _task_face(task: Task | None) -> dict[str, Any] | None:
        if task is None:
            return None
        outcome = outcomes_by_task.get(str(task.id))
        return {
            "task_id": str(task.id),
            "task_status": str(getattr(task.status, "value", task.status)),
            "reached": task.status == TaskStatus.COMPLETED,
            "outcome_id": outcome["outcome_id"] if outcome else None,
        }

    for index, item in enumerate(wizard_milestones[:_TRAJECTORY_RING_CAP]):
        if not isinstance(item, dict):
            continue
        task = milestone_tasks[index] if index < len(milestone_tasks) else None
        task_face = _task_face(task)
        faces.append(
            {
                "milestone_id": str(item.get("id") or f"m{index + 1}"),
                "title": str(item.get("title") or (task.title if task else "")).strip(),
                "task": task_face,
                "reached": bool(task_face and task_face["reached"]),
                "task_id": task_face["task_id"] if task_face else None,
                "outcome_id": task_face["outcome_id"] if task_face else None,
            }
        )

    # 元数据缺里程碑草案时，任务行本身就是里程碑事实（goals.py 同构创建）
    for task in milestone_tasks[len(wizard_milestones) :][: _TRAJECTORY_RING_CAP - len(faces)]:
        task_face = _task_face(task)
        faces.append(
            {
                "milestone_id": None,
                "title": str(task.title or "").strip(),
                "task": task_face,
                "reached": bool(task_face and task_face["reached"]),
                "task_id": task_face["task_id"] if task_face else None,
                "outcome_id": task_face["outcome_id"] if task_face else None,
            }
        )
    return faces


def _outcome_face(
    *,
    tasks: list[Task],
    ledger_index: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """outcome 环：终态任务 → D-02 身份（同一 derive_outcome_id）+ 账本核验。

    ``ledger_verified`` = 账本真实查询命中（GJ03/GJ05「形成 outcome」的
    诚实口径：只有账本读模型确认的条目才算已形成）；ABANDONED → NEGATIVE
    留痕不点亮（失败保留）。
    """
    faces: dict[str, dict[str, Any]] = {}
    for task in tasks:
        status_value = str(getattr(task.status, "value", task.status))
        if status_value not in (TaskStatus.COMPLETED.value, TaskStatus.ABANDONED.value):
            continue
        outcome_id = derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=task.id)
        entry = ledger_index.get(str(task.id))
        polarity = OutcomePolarity.NEGATIVE if status_value == TaskStatus.ABANDONED.value else OutcomePolarity.POSITIVE
        faces[str(task.id)] = {
            "outcome_id": outcome_id,
            "outcome_key": outcome_key(OutcomeSource.TASK_COMPLETION, task.id),
            "task_id": str(task.id),
            "task_title": str(task.title or "").strip(),
            "polarity": polarity.value,
            # 真相面属账本（查询时点重算）；轨迹面只透传账本结论，不自行分级
            "ledger_truth": entry.truth_class.value if entry is not None else None,
            "ledger_verified": entry is not None,
            "evidence_count": len(entry.evidence) if entry is not None else 0,
            "occurred_at": (
                (task.completed_at or task.created_at).isoformat() if (task.completed_at or task.created_at) else None
            ),
        }
    return faces


async def _ledger_task_index(db: AsyncSession, *, user_id: UUID) -> dict[str, Any]:
    """D-02 账本 task_completion 流索引（source_id → entry；单一真源核验面）。"""
    page = await OutcomeLedgerService(db).query(
        user_id=user_id,
        source=OutcomeSource.TASK_COMPLETION,
        limit=_LEDGER_SCAN_LIMIT,
    )
    return {entry.source_id: entry for entry in page.items}


async def _artifacts_face(db: AsyncSession, *, user_id: UUID, task_ids: list[UUID]) -> list[dict[str, Any]]:
    """artifact 环：J-06 Hybrid 旅程产物行（per run per stage 恰一行）。"""
    if not task_ids:
        return []
    result = await db.execute(
        select(HybridJourneyArtifact)
        .where(
            HybridJourneyArtifact.user_id == user_id,
            HybridJourneyArtifact.task_id.in_(task_ids),
            HybridJourneyArtifact.not_deleted_filter(),
        )
        .order_by(HybridJourneyArtifact.created_at.asc())
        .limit(_TRAJECTORY_RING_CAP)
    )
    return [
        {
            "id": str(artifact.id),
            "run_id": str(artifact.run_id),
            "task_id": str(artifact.task_id) if artifact.task_id else None,
            "stage": artifact.stage,
            "artifact_kind": artifact.artifact_kind,
            "citation_count": len(artifact.citations or []),
            "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
        }
        for artifact in result.scalars().all()
    ]


async def _reflections_face(db: AsyncSession, *, task_ids: list[UUID]) -> list[dict[str, Any]]:
    """reflection 环：用户真实提交的结构化反思（只投影，零推断零性格断言）。"""
    if not task_ids:
        return []
    result = await db.execute(
        select(TaskFeedback)
        .where(
            TaskFeedback.task_id.in_(task_ids),
            TaskFeedback.deleted_at.is_(None),
            TaskFeedback.reflection_payload.isnot(None),
        )
        .order_by(TaskFeedback.created_at.asc())
        .limit(_TRAJECTORY_RING_CAP)
    )
    faces: list[dict[str, Any]] = []
    for feedback in result.scalars().all():
        payload = feedback.reflection_payload if isinstance(feedback.reflection_payload, dict) else {}
        faces.append(
            {
                "feedback_id": str(feedback.id),
                "task_id": str(feedback.task_id),
                "category": str(feedback.category or "").strip() or None,
                # 以下三项是用户自报内容原样回声（submit_reflection_answer 落库值）
                "stuck_point": str(payload.get("stuck_point") or "").strip() or None,
                "effective_method": str(payload.get("effective_method") or "").strip() or None,
                "adjustment_intention": str(payload.get("adjustment_intention") or "").strip() or None,
                "memory_id": str(payload.get("memory_id")) if payload.get("memory_id") else None,
                "submitted_at": str(payload.get("submitted_at") or "").strip() or None,
            }
        )
    return faces


async def _experience_candidates_face(db: AsyncSession, *, user_id: UUID, task_ids: list[UUID]) -> list[dict[str, Any]]:
    """experience candidate 环：反思沉淀的真实 episodic memory 行。

    字段 = M-03 预筛候选契约（``id``/``user_id``/``summary``/``occurred_at``/
    ``source_type``/``source_lane``/``epistemic_class``）——与反思面的
    ``memory_id`` 互为同一条链（reflection → candidate）的可核对身份。
    """
    if not task_ids:
        return []
    feedback_ids = (
        (
            await db.execute(
                select(TaskFeedback.id).where(
                    TaskFeedback.user_id == user_id,
                    TaskFeedback.task_id.in_(task_ids),
                    TaskFeedback.deleted_at.is_(None),
                    TaskFeedback.reflection_payload.isnot(None),
                )
            )
        )
        .scalars()
        .all()
    )
    if not feedback_ids:
        return []
    result = await db.execute(
        select(EpisodicMemory)
        .where(
            EpisodicMemory.user_id == user_id,
            EpisodicMemory.source_type == "reflection",
            EpisodicMemory.source_id.in_([str(fid) for fid in feedback_ids]),
            EpisodicMemory.deleted_at.is_(None),
        )
        .order_by(EpisodicMemory.occurred_at.asc())
        .limit(_TRAJECTORY_RING_CAP)
    )
    return [
        {
            "id": str(memory.id),
            "user_id": str(memory.user_id),
            "summary": str(memory.summary or ""),
            "occurred_at": memory.occurred_at.isoformat() if memory.occurred_at else None,
            "source_type": memory.source_type,
            "source_lane": memory.source_lane,
            "epistemic_class": memory.epistemic_class,
        }
        for memory in result.scalars().all()
    ]


async def _galaxy_face(db: AsyncSession, *, user_id: UUID, tasks: list[Task]) -> list[dict[str, Any]]:
    """Galaxy 环：任务关联节点 + G-02 吸收 provenance（与星图同一投影函数）。

    节点解析与 G-02 吸收器确定性链同构（task.knowledge_node_id →
    TaskKnowledgeLink 前置链接），**不做**关键词模糊匹配。
    """
    node_ids: list[UUID] = []
    for task in tasks:
        if task.knowledge_node_id is not None:
            node_ids.append(UUID(str(task.knowledge_node_id)))
    if tasks:
        task_id_list = [task.id for task in tasks]
        links = await db.execute(
            select(TaskKnowledgeLink.knowledge_node_id)
            .where(
                TaskKnowledgeLink.task_id.in_(task_id_list),
                TaskKnowledgeLink.relation_type == "prerequisite",
            )
            .distinct()
        )
        node_ids.extend(UUID(str(row[0])) for row in links.all())

    seen: set[UUID] = set()
    unique_nodes: list[UUID] = []
    for node_id in node_ids:
        if node_id not in seen:
            seen.add(node_id)
            unique_nodes.append(node_id)
    if not unique_nodes:
        return []

    faces: list[dict[str, Any]] = []
    for node_id in unique_nodes[:_TRAJECTORY_RING_CAP]:
        node = await db.get(KnowledgeNode, node_id)
        if node is None:
            continue
        status = await db.get(UserNodeStatus, (user_id, node_id))
        if status is None:
            continue
        # 同源单点：与星图 NodeWithStatus._graph_event_sources 同一读函数
        sources = read_graph_event_sources(status)
        faces.append(
            {
                "node_id": str(node_id),
                "node_name": str(node.name or "").strip(),
                "mastery": round(float(status.mastery_score or 0.0), 1),
                "is_unlocked": bool(status.is_unlocked),
                "graph_event_sources": sources,
                "outcome_ids": [
                    str(source.get("reference_id"))
                    for source in sources
                    if source.get("source_type") == "outcome_ledger" and source.get("reference_id")
                ],
            }
        )
    return faces


__all__ = [
    "GOAL_TRAJECTORY_SCHEMA_VERSION",
    "GoalNotFoundError",
    "MILESTONE_TASK_TAGS",
    "NoActiveGoalError",
    "build_goal_trajectory",
]
