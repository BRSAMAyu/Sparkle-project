from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.aurora.runtime_v1.self_model import SparkleSelfModelService
from app.core.cache import cache_service
from app.models.achievement import UserStreakStats
from app.models.focus import FocusSession, FocusStatus
from app.models.goal import Goal
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.aurora_control_surface_service import AuroraControlSurfaceService
from app.services.goal_today_view import fetch_todays_next_task, todays_task_payload
from app.services.growth_dashboard_service import GrowthDashboardService
from app.services.progress_narrative_service import ProgressNarrativeService

router = APIRouter(prefix="/experience", tags=["experience"])

CorrectionEffectScope = Literal[
    "memory_claim",
    "routing_policy",
    "task_granularity",
    "plan_risk",
    "knowledge_bottleneck",
    "wake_policy",
]


class UnderstandingCorrectionRequest(BaseModel):
    claim: str = Field(..., min_length=1, max_length=600)
    correction: str = Field(..., min_length=1, max_length=1000)
    effect_scope: CorrectionEffectScope


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _clamp_unit(value: Any) -> float:
    try:
        numeric = float(value or 0)
    except (TypeError, ValueError):
        numeric = 0.0
    return round(max(0.0, min(1.0, numeric)), 4)


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _strip(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.75:
        return "high"
    if confidence >= 0.45:
        return "medium"
    return "low"


def _understanding_scope_label(scope: str) -> str:
    labels = {
        "daily_available_time": "学习习惯",
        "task_duration_fit": "学习习惯",
        "task_difficulty_fit": "能力水平",
        "pressure_level_fit": "情绪模式",
        "emotional_state_fit": "情绪模式",
    }
    return labels.get(scope, scope or "策略偏好")


def _understanding_claim_payload(item: dict[str, Any]) -> dict[str, Any]:
    statement = _strip(item.get("statement") or item.get("claim"))
    assumption_id = _strip(item.get("assumption_id") or item.get("claim_id") or statement[:32])
    confidence = _clamp_unit(item.get("confidence"))
    evidence_items = [
        _strip(_as_dict(evidence).get("detail") or evidence)
        for evidence in _as_list(item.get("evidence"))
        if _strip(_as_dict(evidence).get("detail") or evidence)
    ]
    return {
        "claim_id": assumption_id,
        "claim": statement,
        "confidence": confidence,
        "confidence_label": _confidence_label(confidence),
        "evidence_summary": evidence_items[-1] if evidence_items else "基于近期任务执行、纠正记录和上下文命中情况。",
        "scope": _understanding_scope_label(assumption_id or _strip(item.get("scope"))),
        "raw_scope": assumption_id or _strip(item.get("scope")),
        "user_can_correct": True,
    }


def _understanding_recently_corrected(effect: dict[str, Any]) -> list[dict[str, Any]]:
    if not effect.get("visible"):
        return []
    return [
        {
            "claim": _strip(effect.get("claim") or effect.get("semantic_value") or "用户纠正"),
            "correction": _strip(effect.get("correction") or effect.get("action")) or "已按你的反馈重新校准。",
            "effect_on_policy": _as_list(effect.get("affected_state_keys")),
        }
    ]


def _understanding_memory_declarations(control: dict[str, Any], self_model: dict[str, Any]) -> list[dict[str, str]]:
    declarations = [
        {
            "type": "profile_context",
            "content": _strip(reference),
            "persistence": "可被你纠正；用于当前目标、任务粒度和对话风格。",
        }
        for reference in _as_list(control.get("memory_references"))[:4]
        if _strip(reference)
    ]
    task_shape = _strip(_as_dict(self_model.get("harness_effectiveness")).get("task_shape"))
    if task_shape:
        declarations.append(
            {
                "type": "task_shape",
                "content": f"当前任务粒度判断：{task_shape}",
                "persistence": "短期策略读数，会随完成/放弃/纠正继续更新。",
            }
        )
    return declarations


def _understanding_envelope_style(control: dict[str, Any], self_model: dict[str, Any]) -> dict[str, str]:
    task_shape = _strip(_as_dict(self_model.get("harness_effectiveness")).get("task_shape"))
    needs_recalibration = bool(self_model.get("needs_recalibration"))
    if needs_recalibration:
        return {
            "current_tone": "校准优先",
            "current_verbosity": "先确认，再推进",
            "reason_for_style": "最近的纠正或执行信号提示 Sparkle 需要降低自信并确认假设。",
        }
    if task_shape == "struggling":
        return {
            "current_tone": "更稳、更具体",
            "current_verbosity": "拆小步骤",
            "reason_for_style": "任务推进信号显示当前更适合小步确认。",
        }
    return {
        "current_tone": "温和直接",
        "current_verbosity": "中等简洁",
        "reason_for_style": "当前策略命中率和任务节奏读数相对稳定。",
    }


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return cast("str | None", (value.isoformat()))
    return str(value)


# B1-B / S2 例1（SPEC DL §6.4）：unit→人话单位词映射。
# 全量取值域：goal_decomposition_service 产 boolean；demo/seed 产 percent/count/days/time。
# 未知 unit 一律不拼接英文枚举，结构化值经 _criteria_payload 透传给端侧词典兜底。
_CRITERION_UNIT_WORDS: dict[str, str] = {
    "count": "次",
    "percent": "%",
    "days": "天",
}


def _criterion_label(item: Any) -> str:
    """把结构化达标线翻成人类可读的一句话，禁「>= 1boolean」类机话直出（AUDIT S2）。"""
    if isinstance(item, str):
        return item.strip()
    if not isinstance(item, dict):
        return ""
    title = str(item.get("title") or item.get("label") or item.get("metric") or "").strip()
    threshold = item.get("threshold")
    unit = str(item.get("unit") or "").strip()
    if title and threshold is not None:
        if unit == "boolean":
            # 枚举型达标线不走数值化拼接，直接给整句模板。
            return f"完成「{title}」即达标"
        unit_word = _CRITERION_UNIT_WORDS.get(unit)
        if unit_word is None:
            return f"{title} ≥ {threshold}"
        # 「%」紧贴数字，「次/天」留空格。
        separator = "" if unit_word == "%" else " "
        return f"{title} ≥ {threshold}{separator}{unit_word}"
    return title


def _criteria_payload(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    payload: list[dict[str, Any]] = []
    for item in raw:
        label = _criterion_label(item)
        if not label:
            continue
        entry: dict[str, Any] = {
            "label": label,
            "status": item.get("status", "pending") if isinstance(item, dict) else "pending",
            "source": item.get("source", "goal") if isinstance(item, dict) else "goal",
        }
        if isinstance(item, dict):
            # 结构化数据下传（threshold/unit/comparison 原值）：呈现层可据此二次人话化，
            # proto/gRPC 透传原值，分层边界不破坏（SPEC DL §6.4）。
            for key in ("threshold", "unit", "metric"):
                if item.get(key) is not None:
                    entry[key] = item[key]
        payload.append(entry)
    return payload


def _draft_acceptance_criteria(goal: Goal | None, plan: Plan | None) -> list[dict[str, Any]]:
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


async def _active_plan(db: AsyncSession, user_id: UUID) -> Plan | None:
    result = await db.execute(
        select(Plan)
        .where(Plan.user_id == user_id, Plan.is_active.is_(True), Plan.deleted_at.is_(None))
        .order_by(desc(Plan.is_primary), desc(Plan.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _active_goal(db: AsyncSession, user_id: UUID, goal_id: str | None = None) -> Goal | None:
    stmt = select(Goal).where(Goal.user_id == user_id, Goal.deleted_at.is_(None), Goal.status.in_(["active", "draft", "paused"]))
    if goal_id and goal_id not in {"current", "active"}:
        try:
            stmt = stmt.where(Goal.id == UUID(goal_id))
        except ValueError:
            return None
    stmt = stmt.order_by(desc(Goal.is_primary), desc(Goal.updated_at), desc(Goal.created_at)).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _task_counts(db: AsyncSession, user_id: UUID, *, plan_id: UUID | None = None) -> dict[str, int]:
    conditions = [Task.user_id == user_id, Task.deleted_at.is_(None)]
    if plan_id is not None:
        conditions.append(Task.plan_id == plan_id)
    result = await db.execute(
        select(
            func.count(Task.id).label("total"),
            func.count(case((Task.status == TaskStatus.COMPLETED, Task.id))).label("completed"),
            func.count(case((Task.status == TaskStatus.PAUSED, Task.id))).label("paused"),
            func.count(case((Task.status == TaskStatus.STUCK, Task.id))).label("stuck"),
        ).where(*conditions)
    )
    row = result.one()
    return {
        "total": int(row.total or 0),
        "completed": int(row.completed or 0),
        "paused": int(row.paused or 0),
        "stuck": int(row.stuck or 0),
    }


async def _next_task(db: AsyncSession, user_id: UUID, *, plan_id: UUID | None = None) -> dict[str, Any] | None:
    """home 快照/指挥台的「今日下一步」。

    S7 单一事实源：「今日任务」判定与取数统一走 app/services/goal_today_view.py，
    与 goal 详情（experience/goal_router）口径字面一致；本函数不再自带任何
    「下一步」判定（历史实现无 today 过滤且状态集含 PAUSED，曾与 goal 详情
    互斥）。plan_id 为 None 时按用户全局取（保留既有计划回退语义）。
    """
    task = await fetch_todays_next_task(
        db,
        user_id=user_id,
        plan_id=plan_id,
        today=_utcnow().date(),
    )
    return todays_task_payload(task)


def _next_task_payload_verdict(payload: dict[str, Any] | None) -> bool:
    """home 快照口径的「今日有无任务」布尔判定（供 SSOT 回归测试引用）。"""
    return bool(payload and payload.get("id") and payload.get("title"))


async def _goal_graph_summary(user_id: UUID, goal_id: str | None) -> dict[str, Any]:
    if not goal_id or cache_service.redis is None:
        return {"active": False, "nodes": [], "edges": [], "focus_suggestions": []}
    try:
        from app.signals.spine_orchestrator import get_spine_orchestrator

        spine = get_spine_orchestrator(cache_service.redis)
        graph = await spine.get_goal_graph(user_id=str(user_id), goal_id=goal_id)
        if graph is None:
            return {"active": False, "nodes": [], "edges": [], "focus_suggestions": []}
        bottleneck = graph.find_bottleneck()
        suggestions = await spine.get_goal_focus_suggestions(user_id=str(user_id), goal_id=goal_id)
        return {
            "active": True,
            "bottleneck_node_id": bottleneck.node_id if bottleneck else None,
            "bottleneck_label": bottleneck.label if bottleneck else None,
            "coverage": graph.coverage,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "node_type": node.node_type,
                    "label": node.label,
                    "mastery": node.mastery,
                    "why_it_matters": (
                        "当前目标的主要瓶颈"
                        if bottleneck and node.node_id == bottleneck.node_id
                        else "影响目标推进的相关节点"
                    ),
                }
                for node in list(graph.nodes.values())[:12]
            ],
            "edges": [
                {
                    "from_node": edge.from_node_id,
                    "to_node": edge.to_node_id,
                    "edge_type": edge.edge_type,
                }
                for edge in graph.edges[:20]
            ],
            "focus_suggestions": suggestions or [],
        }
    except Exception as exc:
        logger.warning("experience goal graph summary failed user={} goal={}: {}", user_id, goal_id, exc)
        return {"active": False, "nodes": [], "edges": [], "focus_suggestions": []}


# route-tier: authed
@router.get("/understanding-snapshot")
async def get_understanding_snapshot(
    conversation_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """User-visible readout of what Sparkle currently thinks it understands."""
    control = await AuroraControlSurfaceService(db, cache_service.redis).build_snapshot(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )
    self_model = await SparkleSelfModelService(cache_service.redis, db_session=db).get_readout_summary(
        user_id=str(current_user.id),
    )
    facets = list(control.get("facets") or [])
    status_band = control.get("overall_status") or "sensing"
    evidence = list(control.get("status_evidence_chain") or [])[:5]
    memory_refs = list(control.get("memory_references") or [])[:5]
    last_correction = control.get("last_correction_effect") or {}
    claims = [
        _understanding_claim_payload(item)
        for item in _as_list(self_model.get("known_assumptions"))
        if _strip(_as_dict(item).get("statement") or _as_dict(item).get("claim"))
    ]
    high_confidence_count = sum(1 for item in claims if item.get("confidence", 0) >= 0.75)
    uncertain = [
        facet
        for facet in facets
        if facet.get("status") in {"missing", "recalibrating"} or facet.get("meta", {}).get("needs_recalibration")
    ][:3]

    return {
        "active": bool(control.get("aurora_active")),
        "status": status_band,
        "summary": control.get("summary") or "Aurora 正在轻量感知你的目标、状态和上下文。",
        "confidence": _clamp_unit(
            (control.get("progress") or {}).get("ready_count", 0)
            / max(1, (control.get("progress") or {}).get("total", 1))
        ),
        "energy_level": control.get("energy_level"),
        "facets": facets,
        "evidence": evidence,
        "memory_claims": memory_refs,
        "open_questions": [
            {
                "facet": item.get("key"),
                "question": item.get("summary") or "这里可能需要你确认一下。",
                "confidence": _clamp_unit(item.get("confidence", 0.4)),
            }
            for item in uncertain
        ],
        "last_correction_effect": last_correction,
        "next_step_suggestion": control.get("next_step_suggestion"),
        "correctable": True,
        "updated_at": control.get("updated_at") or _utcnow().isoformat(),
        "claims": claims,
        "recently_corrected": _understanding_recently_corrected(last_correction),
        "memory_declarations": _understanding_memory_declarations(control, self_model),
        "envelope_style": _understanding_envelope_style(control, self_model),
        "last_update_time": control.get("updated_at") or _utcnow().isoformat(),
        "total_claims": len(claims),
        "high_confidence_ratio": round(high_confidence_count / len(claims), 4) if claims else 0.0,
    }


# route-tier: authed
@router.post("/understanding-snapshot/corrections")
async def correct_understanding_snapshot(
    request: UnderstandingCorrectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Record a user correction from the UnderstandingSnapshot panel."""
    correction_id = f"understanding_snapshot:{uuid4().hex}"
    reason = f"{request.claim} → {request.correction} [{request.effect_scope}]"
    await SparkleSelfModelService(cache_service.redis, db_session=db).record_user_correction(
        user_id=str(current_user.id),
        signal_id=correction_id,
        reason=reason,
        source="understanding_snapshot",
    )
    effect = {
        "visible": True,
        "semantic_value": request.effect_scope,
        "action": "understanding_snapshot_correction",
        "claim": request.claim,
        "correction": request.correction,
        "affected_state_keys": [request.effect_scope],
        "updated_at": _utcnow().isoformat(),
    }
    if cache_service.redis is not None:
        await cache_service.redis.set(
            f"aurora:last_correction_effect:{current_user.id}",
            json.dumps(effect, ensure_ascii=False),
        )
        await cache_service.redis.expire(f"aurora:last_correction_effect:{current_user.id}", 24 * 3600)
    return {
        "status": "updated",
        "correction_id": correction_id,
        "effect_on_policy": effect["affected_state_keys"],
        "message": "已更新 Sparkle 对你的理解。",
    }


# GOAL-ROUTER：本模块**不得**再注册 GET /goal-detail/{goal_id}。
# goal 域端点（GET goal-detail + PUT criteria-status）唯一所有者是
# experience/goal_router.py——router.py 的 `_include_router_if_new()` 只要发现
# 任一 (path, methods) 重叠就会把整个 closeout router 拒之门外，历史上本模块
# 的同路径 GET 曾把 goal_router 整体遮蔽成死代码（mobile criteria-status PUT
# 因此长期 405）。守卫：tests/unit/test_goal_detail_route_shadowing.py。
# route-tier: authed
@router.get("/growth-dashboard")
async def get_experience_growth_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """A user-facing growth dashboard with quality, narrative, and model-update receipts."""
    base = await GrowthDashboardService(db).build_snapshot(current_user.id, user=current_user)
    narrative = await ProgressNarrativeService(db, redis=cache_service.redis, cache=cache_service).get_weekly_narrative(
        current_user.id
    )
    since = _utcnow() - timedelta(days=7)
    focus_result = await db.execute(
        select(
            func.coalesce(func.sum(FocusSession.duration_minutes), 0),
            func.count(FocusSession.id),
        ).where(
            FocusSession.user_id == current_user.id,
            FocusSession.status == FocusStatus.COMPLETED,
            FocusSession.start_time >= since,
        )
    )
    focus_minutes, focus_sessions = focus_result.one()
    tasks = await _task_counts(db, current_user.id)
    streak_result = await db.execute(select(UserStreakStats).where(UserStreakStats.user_id == current_user.id))
    streak = streak_result.scalar_one_or_none()
    quality_score = _clamp_unit(
        (0.35 * (tasks["completed"] / max(1, tasks["total"])))
        + (0.35 * min(1.0, int(focus_minutes or 0) / 300))
        + (0.20 * min(1.0, (streak.current_streak if streak else 0) / 7))
        + (0.10 if tasks["stuck"] == 0 else 0.0)
    )

    return {
        "growth_status": base.get("growth_status") or {},
        "what_changed_card": base.get("what_changed_card"),
        "next_move_card": base.get("next_move_card"),
        "weekly_narrative": narrative.to_dict() if hasattr(narrative, "to_dict") else narrative,
        "learning_dashboard": {
            "focus_minutes_7d": int(focus_minutes or 0),
            "focus_sessions_7d": int(focus_sessions or 0),
            "tasks_total": tasks["total"],
            "tasks_completed": tasks["completed"],
            "tasks_stuck": tasks["stuck"],
            "tasks_paused": tasks["paused"],
            "completion_rate": _clamp_unit(tasks["completed"] / max(1, tasks["total"])),
        },
        "streak_quality": {
            "score": quality_score,
            "current_streak": int(streak.current_streak if streak else 0),
            "label": (
                "高质量坚持"
                if quality_score >= 0.72
                else ("节奏在恢复" if quality_score >= 0.42 else "需要重新找回节奏")
            ),
            "evidence": [
                f"过去 7 天完成 {tasks['completed']} / {tasks['total']} 个任务",
                f"过去 7 天专注 {int(focus_minutes or 0)} 分钟",
                f"当前连续 {int(streak.current_streak if streak else 0)} 天",
            ],
        },
        "model_update_receipts": [
            item
            for item in [
                base.get("what_changed_card"),
                base.get("active_bottleneck"),
            ]
            if item
        ][:3],
        "updated_at": _utcnow().isoformat(),
    }


# /community-accountability moved to experience/community_router.py
# (fully implemented with DB-backed partnerships, shared goals, squad risks).
# The stub that was here shadowed it via _include_router_if_new() dedup.
