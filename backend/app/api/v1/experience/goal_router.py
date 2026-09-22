from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.v1 import experience_readouts as _readouts
from app.aurora.runtime_v1.models import GoalWorldGraphSnapshot
from app.models.accountability import AccountabilityCheckin, AccountabilityPartnership, AccountabilityStatus
from app.models.file_storage import StoredFile
from app.models.goal import Goal
from app.models.plan import Plan
from app.models.strategy_belief import StrategyBeliefSnapshot
from app.models.task import Task
from app.models.task_document import TaskDocument
from app.models.user import User
from app.services.goal_today_view import fetch_todays_next_task, todays_task_payload

# GOAL-ROUTER（v3-output/GOAL-ROUTER/REPORT.md）：
# 本 router 是 /experience/goal-detail/{goal_id}（GET+PUT criteria-status）的
# 唯一所有者。历史上 router.py 的 `_include_router_if_new()` 曾因 readouts
# 抢注同路径 GET 而把本 router 整体遮蔽成死代码（mobile 的 criteria-status
# PUT 因此长期 405）——readouts 侧已删除该 GET，本 router 现为生效路径。
# GET 返回**超集形状**：goal 详情屏契约字段（GoalDetailPayload 原有字段）+
# home 仪表盘卡兼容字段（active/plan/progress/next_task/goal_graph/
# why_this_matters/updated_at，即原 readouts 快照面），两个 mobile 解析器
# （goal_detail_provider.dart / experience_models.dart）都直接可读。
# `_readouts` 复用说明：home 卡兼容字段的口径（active goal 解析、任务计数、
# spine 目标图摘要）必须与 readouts 逐字一致，故直接引用其实现而非复制，
# 防止出现第三套口径漂移。守卫：tests/unit/test_goal_detail_route_shadowing.py。

router = APIRouter(prefix="/experience", tags=["experience"])


class CriteriaStatusPayload(BaseModel):
    status: str = "confirmed"


class GoalSummaryPayload(BaseModel):
    id: str
    title: str
    goal_type: str
    status: str
    target_date: str | None = None
    mastery: float = 0.0
    progress: float = 0.0
    priority: str = "normal"


class CriteriaThresholdPayload(BaseModel):
    id: str
    label: str
    metric: str | None = None
    threshold: str | None = None
    unit: str | None = None
    current_value: str | None = None
    met: bool = False


class MinimumAcceptanceCriteriaPayload(BaseModel):
    description: str
    status: str = "pending_confirmation"
    thresholds: list[CriteriaThresholdPayload] = Field(default_factory=list)


class PlanHealthPayload(BaseModel):
    overall: float = 0.0
    phase_health: float = 0.0
    task_completion_rate: float = 0.0


class CurrentPhasePayload(BaseModel):
    name: str
    progress: float = 0.0


class TodaysMinimalNextStepPayload(BaseModel):
    task_id: str | None = None
    title: str | None = None
    type: str | None = None
    estimated_minutes: int | None = None


class KnowledgeBottleneckPayload(BaseModel):
    node_id: str
    label: str
    mastery: float = 0.0
    goal_impact: str


class AccountabilityStatusPayload(BaseModel):
    partner_count: int = 0
    active_commitments: int = 0
    last_checkin: str | None = None


class RelatedSourcePayload(BaseModel):
    id: str
    title: str
    type: str
    relevance: float = 0.0


class StrategyBeliefPayload(BaseModel):
    strategy_id: str
    title: str
    confidence: float
    counter_evidence: list[dict[str, Any]] = Field(default_factory=list)


class GoalDetailPayload(BaseModel):
    # goal 详情屏契约（goal_detail_provider.dart GoalDetailData.fromJson）。
    goal: GoalSummaryPayload | None = None
    minimum_acceptance_criteria: MinimumAcceptanceCriteriaPayload
    plan_health: PlanHealthPayload
    current_phase: CurrentPhasePayload
    todays_minimal_next_step: TodaysMinimalNextStepPayload
    knowledge_bottlenecks: list[KnowledgeBottleneckPayload] = Field(default_factory=list)
    accountability_status: AccountabilityStatusPayload
    related_sources: list[RelatedSourcePayload] = Field(default_factory=list)
    strategy_belief: StrategyBeliefPayload | None = None
    # home 仪表盘卡兼容字段（experience_models.dart GoalDetailSnapshot.fromJson，
    # 原 readouts 快照形状；goal 可为 None、plan 为计划回退结果）。
    active: bool = False
    plan: dict[str, Any] | None = None
    progress: dict[str, Any] = Field(default_factory=dict)
    next_task: dict[str, Any] | None = None
    goal_graph: dict[str, Any] = Field(default_factory=dict)
    why_this_matters: str | None = None
    updated_at: str | None = None


# route-tier: authed
@router.get("/goal-detail/{goal_id}", response_model=GoalDetailPayload)
async def get_goal_detail(
    goal_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalDetailPayload:
    """goal 详情（唯一生效路径；超集形状见模块头注释）。

    ``goal_id`` 两种用法：
    - 具体 UUID（goal 详情屏）：精确加载本人目标，查无 → 404；
    - ``current``/``active`` 别名（home 仪表盘卡）：解析主目标，查无时回退
      活跃计划并给出 ``active=false`` 的空态快照（保持原 readouts 行为）。
    """
    goal = await _resolve_goal(db, goal_id=goal_id, user_id=current_user.id)
    plan: Plan | None = None
    if goal is not None and goal.plan_id is not None:
        plan = await _load_plan(db, goal)
    if plan is None:
        plan = await _readouts._active_plan(db, current_user.id)

    task_counts = await _readouts._task_counts(db, current_user.id, plan_id=plan.id if plan else None)
    next_task = await _todays_next_task(db, user_id=current_user.id, plan_id=plan.id if plan else None)
    graph_payload = await _load_graph_payload(db, user_id=current_user.id, goal_id=goal.id if goal else None)
    spine_graph = await _readouts._goal_graph_summary(
        current_user.id,
        str(goal.id) if goal else (str(plan.id) if plan else goal_id),
    )
    accountability = await _accountability_status(db, current_user.id)
    sources = await _related_sources(db, user_id=current_user.id, plan_id=plan.id if plan else None)
    strategy_belief = await _strategy_belief_payload(db, user_id=current_user.id, goal=goal) if goal else None

    return GoalDetailPayload(
        goal=_goal_summary(goal),
        minimum_acceptance_criteria=_criteria_or_draft(goal=goal, plan=plan),
        plan_health=_plan_health_payload(goal=goal, plan=plan, task_counts=task_counts),
        current_phase=_current_phase_payload(plan=plan, goal=goal),
        todays_minimal_next_step=_next_step_payload(next_task),
        knowledge_bottlenecks=_bottleneck_payloads(graph_payload),
        accountability_status=accountability,
        related_sources=sources,
        strategy_belief=strategy_belief,
        active=bool(goal or plan),
        plan=_plan_summary(plan),
        progress=_progress_payload(goal=goal, plan=plan, task_counts=task_counts),
        next_task=todays_task_payload(next_task),
        goal_graph=spine_graph,
        why_this_matters=spine_graph.get("bottleneck_label")
        or "这个目标会影响 Sparkle 今天的计划、资料选择和任务排序。",
        updated_at=_readouts._utcnow().isoformat(),
    )


async def _resolve_goal(db: AsyncSession, *, goal_id: str, user_id: UUID) -> Goal | None:
    """具体 UUID → 精确目标（404 语义）；'current'/'active'/其余 → 主目标别名。"""
    try:
        parsed = UUID(goal_id)
    except ValueError:
        return await _readouts._active_goal(db, user_id, goal_id)
    goal = await _load_goal(db, goal_id=parsed, user_id=user_id)
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


# route-tier: authed
@router.put("/goal-detail/{goal_id}/criteria-status")
async def update_criteria_status(
    payload: CriteriaStatusPayload,
    goal_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    goal = await _load_goal(db, goal_id=goal_id, user_id=current_user.id)
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    status_value = payload.status.strip()
    if status_value not in ("confirmed", "pending_confirmation"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="status must be 'confirmed' or 'pending_confirmation'",
        )

    criteria = goal.minimum_acceptance_criteria
    if isinstance(criteria, dict):
        criteria = dict(criteria)
    elif isinstance(criteria, list):
        criteria = {"thresholds": criteria}
    else:
        criteria = {}
    criteria["status"] = status_value
    goal.minimum_acceptance_criteria = criteria
    await db.commit()

    return {"status": "ok", "criteria_status": status_value}


async def _load_goal(db: AsyncSession, *, goal_id: UUID, user_id: UUID) -> Goal | None:
    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id,
            Goal.user_id == user_id,
            Goal.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


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


def _goal_summary(goal: Goal | None) -> GoalSummaryPayload | None:
    if goal is None:
        return None
    return GoalSummaryPayload(
        id=str(goal.id),
        title=goal.title,
        goal_type=goal.goal_type,
        status=goal.status,
        target_date=goal.target_date.isoformat() if goal.target_date else None,
        mastery=_safe_ratio(goal.mastery),
        progress=_safe_ratio(goal.progress),
        priority=goal.priority or "normal",
    )


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _plan_summary(plan: Plan | None) -> dict[str, Any] | None:
    """home 卡兼容的计划投影（与原 readouts 快照逐字同形）。"""
    if plan is None:
        return None
    return {
        "id": str(plan.id),
        "name": plan.name,
        "type": _enum_value(plan.type),
        "subject": plan.subject,
        "target_date": _iso_date(plan.target_date),
        "progress": _clamp_unit(plan.progress),
        "mastery_level": _clamp_unit(plan.mastery_level),
        "plan_stage": _enum_value(plan.plan_stage),
        "priority": _enum_value(plan.priority),
    }


def _progress_payload(*, goal: Goal | None, plan: Plan | None, task_counts: dict[str, int]) -> dict[str, Any]:
    overall = _clamp_unit((goal.progress if goal else None) or (plan.progress if plan else None) or 0)
    return {
        "overall": overall,
        "tasks_total": task_counts["total"],
        "tasks_completed": task_counts["completed"],
        "paused": task_counts["paused"],
        "stuck": task_counts["stuck"],
    }


def _clamp_unit(value: Any) -> float:
    return _readouts._clamp_unit(value)


def _iso_date(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _criteria_or_draft(*, goal: Goal | None, plan: Plan | None) -> MinimumAcceptanceCriteriaPayload:
    """达标线载荷：目标自带优先；无则回退草案（home 卡达标线行不因此退化为空）。"""
    payload = _criteria_payload(goal.minimum_acceptance_criteria if goal else None)
    if payload.thresholds:
        return payload
    drafts = _draft_acceptance_criteria(goal, plan)
    return MinimumAcceptanceCriteriaPayload(
        description="",
        status="draft",
        thresholds=[
            CriteriaThresholdPayload(
                id=f"draft-{index + 1}",
                label=str(item.get("label") or ""),
            )
            for index, item in enumerate(drafts)
            if item.get("label")
        ],
    )


def _draft_acceptance_criteria(goal: Goal | None, plan: Plan | None) -> list[dict[str, Any]]:
    """无达标线目标时的草案达标线（自原 readouts goal-detail 快照迁移，GOAL-ROUTER）。"""
    title = str((goal.title if goal else None) or (plan.name if plan else "") or "").strip()
    goal_type = str((goal.goal_type if goal else None) or (plan.type.value if plan and plan.type else "general"))
    subject = str((plan.subject if plan else "") or "").strip()
    if goal_type == "exam" or subject:
        return [
            {"label": "核心科目达到目标分数线", "status": "draft", "source": "sparkle_draft"},
            {"label": "最近一次模拟/真题达到最低通过标准", "status": "draft", "source": "sparkle_draft"},
            {"label": "高频错题知识点完成复盘", "status": "draft", "source": "sparkle_draft"},
        ]
    if title:
        return [
            {"label": f"{title} 有可交付成果", "status": "draft", "source": "sparkle_draft"},
            {"label": "关键风险已被复盘并处理", "status": "draft", "source": "sparkle_draft"},
            {"label": "下一阶段计划已经确认", "status": "draft", "source": "sparkle_draft"},
        ]
    return [
        {"label": "目标定义清楚", "status": "draft", "source": "sparkle_draft"},
        {"label": "有可执行的下一步", "status": "draft", "source": "sparkle_draft"},
    ]


async def _strategy_belief_payload(
    db: AsyncSession,
    *,
    user_id: UUID,
    goal: Goal,
) -> StrategyBeliefPayload | None:
    metadata = goal.metadata_payload if isinstance(goal.metadata_payload, dict) else {}
    current_strategy = metadata.get("current_strategy_id") or metadata.get("strategy_key")
    query = select(StrategyBeliefSnapshot).where(
        StrategyBeliefSnapshot.user_id == str(user_id),
        StrategyBeliefSnapshot.deleted_at.is_(None),
    )
    if current_strategy:
        query = query.where(StrategyBeliefSnapshot.strategy_key == str(current_strategy))
    result = await db.execute(query.order_by(StrategyBeliefSnapshot.updated_at.desc()))
    beliefs = list(result.scalars().all())
    candidates = [
        belief
        for belief in beliefs
        if belief.belief_score < 0.4 and _counter_evidence_payload(belief.counter_evidence)
    ]
    if not candidates:
        return None

    belief = sorted(candidates, key=lambda item: item.belief_score)[0]
    return StrategyBeliefPayload(
        strategy_id=belief.strategy_key,
        title=belief.strategy_key.replace("_", " ").title(),
        confidence=round(belief.belief_score, 3),
        counter_evidence=_counter_evidence_payload(belief.counter_evidence),
    )


def _counter_evidence_payload(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    payload: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            reason = str(item.get("reason") or item.get("detail") or item.get("evidence_id") or "").strip()
            if reason:
                payload.append(
                    {
                        "reason": reason,
                        "weight": float(item.get("weight") or 1.0),
                        "source": str(item.get("source") or "counter_evidence"),
                    }
                )
        elif str(item).strip():
            payload.append({"reason": str(item).strip(), "weight": 1.0, "source": "counter_evidence"})
    return payload


async def _todays_next_task(db: AsyncSession, *, user_id: UUID, plan_id: UUID | None) -> Task | None:
    """goal 详情「今日最小下一步」取数。

    S7 单一事实源：「今日任务」判定与取数统一走 app/services/goal_today_view.py，
    与 home 快照（experience_readouts goal-detail next_task）口径字面一致；
    本函数不再自带查询定义（历史实现无 today 过滤且排除 PAUSED，曾与 home
    快照对同一目标状态给出相反结论）。
    """
    return await fetch_todays_next_task(
        db,
        user_id=user_id,
        plan_id=plan_id,
        today=datetime.now(UTC).date(),
    )


def _todays_step_exists(task: Task | None) -> bool:
    """goal 详情口径的「今日有无任务」布尔判定（供 SSOT 回归测试引用）。"""
    return task is not None


async def _load_graph_payload(db: AsyncSession, *, user_id: UUID, goal_id: UUID | None) -> dict[str, Any]:
    if goal_id is None:
        return {}
    result = await db.execute(
        select(GoalWorldGraphSnapshot)
        .where(
            GoalWorldGraphSnapshot.user_id == str(user_id),
            GoalWorldGraphSnapshot.goal_id == str(goal_id),
            GoalWorldGraphSnapshot.deleted_at.is_(None),
        )
        .order_by(GoalWorldGraphSnapshot.last_saved_at.desc())
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    return snapshot.payload if snapshot and isinstance(snapshot.payload, dict) else {}


async def _accountability_status(db: AsyncSession, user_id: UUID) -> AccountabilityStatusPayload:
    active_filter = and_(
        AccountabilityPartnership.status == AccountabilityStatus.ACTIVE,
        or_(
            AccountabilityPartnership.initiator_id == user_id,
            AccountabilityPartnership.partner_id == user_id,
        ),
        AccountabilityPartnership.deleted_at.is_(None),
    )
    count_result = await db.execute(select(func.count(AccountabilityPartnership.id)).where(active_filter))
    partner_count = int(count_result.scalar_one() or 0)

    checkin_result = await db.execute(
        select(AccountabilityCheckin.created_at)
        .join(AccountabilityPartnership, AccountabilityPartnership.id == AccountabilityCheckin.partnership_id)
        .where(
            active_filter,
            AccountabilityCheckin.user_id == user_id,
            AccountabilityCheckin.deleted_at.is_(None),
        )
        .order_by(AccountabilityCheckin.created_at.desc())
        .limit(1)
    )
    last_checkin = checkin_result.scalar_one_or_none()
    return AccountabilityStatusPayload(
        partner_count=partner_count,
        active_commitments=partner_count,
        last_checkin=_iso(last_checkin),
    )


async def _related_sources(db: AsyncSession, *, user_id: UUID, plan_id: UUID | None) -> list[RelatedSourcePayload]:
    if plan_id is None:
        return []
    result = await db.execute(
        select(StoredFile)
        .join(TaskDocument, TaskDocument.file_id == StoredFile.id)
        .join(Task, Task.id == TaskDocument.task_id)
        .where(
            StoredFile.user_id == user_id,
            StoredFile.deleted_at.is_(None),
            Task.user_id == user_id,
            Task.plan_id == plan_id,
            Task.deleted_at.is_(None),
        )
        .order_by(TaskDocument.created_at.desc())
        .limit(5)
    )
    files = result.scalars().all()
    return [
        RelatedSourcePayload(
            id=str(file.id),
            title=file.file_name,
            type=file.mime_type,
            relevance=_safe_ratio(0.86 - (index * 0.08)),
        )
        for index, file in enumerate(files)
    ]


def _criteria_payload(raw: Any) -> MinimumAcceptanceCriteriaPayload:
    if isinstance(raw, dict):
        description = str(raw.get("description") or raw.get("summary") or "")
        status_text = str(raw.get("status") or "pending_confirmation")
        raw_items = raw.get("thresholds") or raw.get("criteria") or raw.get("items") or []
    elif isinstance(raw, list):
        description = ""
        status_text = "pending_confirmation"
        raw_items = raw
    else:
        return MinimumAcceptanceCriteriaPayload(
            description="",
            status="pending_confirmation",
            thresholds=[],
        )

    thresholds: list[CriteriaThresholdPayload] = []
    for index, item in enumerate(raw_items):
        item_map = item if isinstance(item, dict) else {"label": str(item)}
        label = str(
            item_map.get("label")
            or item_map.get("description")
            or item_map.get("metric")
            or item_map.get("name")
            or f"Criterion {index + 1}"
        )
        thresholds.append(
            CriteriaThresholdPayload(
                id=str(item_map.get("id") or item_map.get("key") or f"criterion-{index + 1}"),
                label=label,
                metric=_optional_text(item_map.get("metric")),
                threshold=_optional_text(item_map.get("threshold") or item_map.get("target")),
                unit=_optional_text(item_map.get("unit")),
                current_value=_optional_text(item_map.get("current_value") or item_map.get("current")),
                met=bool(item_map.get("met") or item_map.get("is_met") or item_map.get("completed")),
            )
        )
    return MinimumAcceptanceCriteriaPayload(
        description=description,
        status=status_text,
        thresholds=thresholds,
    )


def _plan_health_payload(*, goal: Goal | None, plan: Plan | None, task_counts: dict[str, int]) -> PlanHealthPayload:
    progress = _safe_ratio((plan.progress if plan else None) or (goal.progress if goal else None))
    mastery = _safe_ratio((plan.mastery_level if plan else None) or (goal.mastery if goal else None))
    total = task_counts["total"]
    task_completion_rate = task_counts["completed"] / total if total else progress
    overall = (progress * 0.45) + (mastery * 0.35) + (task_completion_rate * 0.2)
    return PlanHealthPayload(
        overall=round(_safe_ratio(overall), 3),
        phase_health=round(_safe_ratio(progress), 3),
        task_completion_rate=round(_safe_ratio(task_completion_rate), 3),
    )


def _current_phase_payload(*, plan: Plan | None, goal: Goal | None) -> CurrentPhasePayload:
    if plan is None:
        return CurrentPhasePayload(
            name=(goal.status if goal else None) or "active",
            progress=_safe_ratio(goal.progress if goal else 0),
        )
    stage = plan.plan_stage.value if hasattr(plan.plan_stage, "value") else str(plan.plan_stage)
    return CurrentPhasePayload(name=stage, progress=_safe_ratio(plan.progress))


def _next_step_payload(task: Task | None) -> TodaysMinimalNextStepPayload:
    if task is None:
        return TodaysMinimalNextStepPayload()
    task_type = task.type.value if hasattr(task.type, "value") else str(task.type)
    return TodaysMinimalNextStepPayload(
        task_id=str(task.id),
        title=task.title,
        type=task_type,
        estimated_minutes=task.estimated_minutes,
    )


def _bottleneck_payloads(graph_payload: dict[str, Any]) -> list[KnowledgeBottleneckPayload]:
    nodes_raw = graph_payload.get("nodes")
    nodes = nodes_raw if isinstance(nodes_raw, list) else []
    bottleneck_id = graph_payload.get("bottleneck_node_id")

    ranked = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        mastery = _safe_ratio(node.get("mastery"))
        focus_priority = _safe_ratio(node.get("focus_priority"))
        is_bottleneck = node.get("node_id") == bottleneck_id or bool(node.get("is_bottleneck"))
        impact_score = (1 - mastery) + focus_priority + (0.75 if is_bottleneck else 0)
        ranked.append((impact_score, node))

    ranked.sort(key=lambda item: item[0], reverse=True)
    payloads: list[KnowledgeBottleneckPayload] = []
    for impact_score, node in ranked[:6]:
        label = str(node.get("label") or node.get("node_id") or "Untitled node")
        node_id = str(node.get("node_id") or "")
        if not node_id:
            continue
        payloads.append(
            KnowledgeBottleneckPayload(
                node_id=node_id,
                label=label,
                mastery=_safe_ratio(node.get("mastery")),
                goal_impact=_impact_label(impact_score, node),
            )
        )
    return payloads


def _impact_label(score: float, node: dict[str, Any]) -> str:
    blocks_count = node.get("blocks_count") or node.get("blocked_count")
    if blocks_count:
        return f"blocks {blocks_count} downstream steps"
    if node.get("node_id") == node.get("bottleneck_node_id") or node.get("is_bottleneck"):
        return "current bottleneck"
    if score >= 1.2:
        return "high goal impact"
    if score >= 0.75:
        return "medium goal impact"
    return "supporting goal progress"


def _safe_ratio(value: Any) -> float:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    if number > 1:
        number = number / 100
    return max(0.0, min(1.0, number))


def _optional_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
