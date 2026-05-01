"""
Learning Paths API
基于拓扑排序的动态学习路径接口
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.collaboration_workflows import TaskDecompositionWorkflow
from app.agents.enhanced_agents import EnhancedAgentContext
from app.api.deps import get_current_user, get_current_user_id, get_db
from app.core.cache import cache_service
from app.core.exceptions import QuotaExceededError
from app.models.galaxy import UserNodeStatus
from app.models.plan import PlanType
from app.models.task import SubTaskStatus, TaskType
from app.models.user import User
from app.schemas.plan import PlanCreate
from app.schemas.task import TaskCreate
from app.services.graph_reasoning_service import GraphReasoningService
from app.services.plan_service import PlanService
from app.services.task_service import TaskService
from app.tools.entity_cards import (
    build_learning_path_entity_card,
    build_plan_entity_card,
    build_task_list_entity_card,
)
from app.tools.plan_tools import GenerateTasksForPlanTool
from app.tools.schemas import GenerateTasksForPlanParams

router = APIRouter(prefix="/learning-paths", tags=["Learning Paths"])


# ============ Response Models ============

class LearningPathErrorResponse(BaseModel):
    """统一的学习路径错误响应"""
    error_code: str  # "CYCLIC_DEPENDENCY" | "TARGET_NOT_FOUND" | "NO_PATH" | "GRAPH_ERROR"
    message: str
    details: dict[str, Any] | None = None


class LearningPathNodeResponse(BaseModel):
    """学习路径节点响应"""
    id: str
    name: str
    status: str  # mastered, unlocked, locked
    is_target: bool
    is_optional: bool = False
    relation_type: str | None = None
    source_type: str | None = None


class LearningPathTaskResponse(BaseModel):
    """轻量学习路径任务响应"""
    id: str
    title: str
    type: str
    estimated_minutes: int
    status: str
    knowledge_node_id: str | None = None
    guide_content: str | None = None


# ============ Helpers ============

def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)

def _is_error_response(path: list[dict[str, Any]]) -> bool:
    """检查路径响应是否为错误响应"""
    return len(path) == 1 and "error" in path[0]


def _extract_error(path: list[dict[str, Any]]) -> tuple[str, str, dict | None]:
    """从路径响应中提取错误信息，返回 (error_code, message, details)"""
    error_data = path[0]
    error_code = error_data.get("error_code", "UNKNOWN_ERROR")
    message = error_data.get("message", "未知错误")
    details = error_data.get("details")
    return error_code, message, details


def _build_fallback_plan_summary(target_name: str, path: list[dict[str, Any]]) -> str:
    steps: list[str] = []
    active_path = path or []
    target_step_index = len(active_path)

    for index, node in enumerate(active_path, start=1):
        name = str(node.get("name", "未知节点"))
        status = str(node.get("status", "locked"))
        is_target = bool(node.get("is_target"))
        if is_target:
            target_step_index = index
        if status == "mastered":
            steps.append(f"{index}. 快速复盘 {name}，确认前置知识仍然稳固。")
        elif is_target:
            steps.append(f"{index}. 聚焦攻克目标节点 {name}，完成理解、练习和应用闭环。")
        else:
            steps.append(f"{index}. 先补齐 {name} 的核心概念、关键方法和典型练习。")

    if not steps:
        steps.append("1. 直接进入目标主题学习，先建立基础认知框架。")

    return "\n".join(
        [
            f"学习目标：{target_name}",
            "",
            "建议节奏：",
            *steps,
            "",
            f"完成标志：能够独立解释 {target_name}，并把第 {target_step_index} 步涉及的关键知识串联起来。",
        ]
    )


def _build_task_path_guide(target_name: str, path: list[dict[str, Any]]) -> str:
    ordered_nodes = [node for node in path if not node.get("is_optional")]
    optional_nodes = [node for node in path if node.get("is_optional")]

    lines = [f"目标：围绕「{target_name}」建立一条可以立刻执行的学习路径。", "", "建议执行顺序："]
    active_index = 1
    for node in ordered_nodes:
        status = str(node.get("status", "locked"))
        name = str(node.get("name", "未知节点"))
        if status == "mastered":
            lines.append(f"{active_index}. 快速复盘 {name}，确认关键概念没有遗忘。")
        elif node.get("is_target"):
            lines.append(f"{active_index}. 集中攻克 {name}，先理解核心，再完成一轮练习与输出。")
        else:
            lines.append(f"{active_index}. 先补齐 {name} 的基础概念和典型用法。")
        active_index += 1

    if optional_nodes:
        lines.extend(["", "可选加深："])
        for node in optional_nodes[:3]:
            relation = node.get("relation_type") or "related"
            lines.append(f"- {node.get('name', '未知节点')}（{relation}）")

    lines.extend(
        [
            "",
            "完成标志：",
            f"- 能用自己的话解释 {target_name}",
            "- 至少完成一轮例题、练习或小型输出",
        ]
    )
    return "\n".join(lines)


def _build_task_step_guide(
    *,
    task_index: int,
    total_steps: int,
    node_name: str,
    node_description: str,
    is_target: bool,
    summary: str,
) -> str:
    heading = f"第 {task_index}/{total_steps} 步：{node_name}"
    focus = "目标节点，优先完成理解 + 练习 + 输出。" if is_target else "前置节点，优先补齐概念和基本方法。"
    detail = node_description or "围绕该节点完成概念理解、例题练习和简短输出。"
    return "\n".join(
        [
            heading,
            "",
            f"本步重点：{focus}",
            f"节点说明：{detail}",
            "",
            "整条路径摘要：",
            summary,
        ]
    )


async def _upsert_learning_path_snapshot(
    *,
    db: AsyncSession,
    user_id: UUID,
    target_node_id: UUID,
    summary: str,
    tasks_payload: list[dict[str, Any]],
    selected_related_node_ids: list[UUID],
    mode: str,
) -> None:
    result = await db.execute(
        select(UserNodeStatus).where(
            UserNodeStatus.user_id == user_id,
            UserNodeStatus.node_id == target_node_id,
        )
    )
    user_status = result.scalar_one_or_none()
    if user_status is None:
        user_status = UserNodeStatus(
            user_id=user_id,
            node_id=target_node_id,
            is_unlocked=True,
            mastery_score=0,
            total_minutes=0,
            total_study_minutes=0,
            study_count=0,
            learning_path_snapshot=None,
        )
        db.add(user_status)

    user_status.learning_path_snapshot = {
        "mode": mode,
        "summary": summary,
        "task_count": len(tasks_payload),
        "tasks": tasks_payload,
        "selected_related_node_ids": [str(node_id) for node_id in selected_related_node_ids],
        "generated_at": _utcnow().isoformat(),
    }
    await db.commit()


async def _generate_plan_summary(
    *,
    user_query: str,
    enhanced_context: EnhancedAgentContext,
    target_name: str,
    path: list[dict[str, Any]],
) -> tuple[str, bool]:
    try:
        workflow = TaskDecompositionWorkflow(None)
        collaboration_result = await asyncio.wait_for(
            workflow.execute(user_query, enhanced_context),
            timeout=45,
        )
        plan_summary = (collaboration_result.final_response or "").strip()
        if plan_summary:
            return plan_summary, False
    except Exception as exc:
        logger.warning(f"Learning path plan workflow failed for {target_name}: {exc}")

    return _build_fallback_plan_summary(target_name, path), True


# ============ Endpoints ============


async def get_graph_reasoning_service(db: AsyncSession = Depends(get_db)) -> GraphReasoningService:
    return GraphReasoningService(db)


@router.get(
    "/{target_node_id}",
    response_model=Union[list[LearningPathNodeResponse], LearningPathErrorResponse],
)
async def get_dynamic_learning_path(
    target_node_id: UUID,
    include_related: bool = Query(False, description="是否返回可选拓展节点建议"),
    selected_related_node_ids: list[UUID] = Query(default_factory=list, description="用户主动纳入路径的相关节点"),
    user_id: str = Depends(get_current_user_id),
    service: GraphReasoningService = Depends(get_graph_reasoning_service),
):
    """
    获取到达目标节点的动态学习路径 (DAG Topological Sort)

    返回按学习顺序排列的节点列表，包含状态（locked/unlocked/mastered）。

    Error Codes:
    - CYCLIC_DEPENDENCY: 知识图谱存在循环依赖
    - TARGET_NOT_FOUND: 目标节点不存在
    - GRAPH_ERROR: 图结构查询失败
    """
    path = await service.generate_learning_path(
        UUID(user_id),
        target_node_id,
        include_related_suggestions=include_related,
        selected_related_node_ids=selected_related_node_ids,
    )

    # 检查是否为空路径
    if not path:
        return []

    # 检查是否为错误响应
    if _is_error_response(path):
        error_code, message, details = _extract_error(path)
        status_code = status.HTTP_400_BAD_REQUEST
        if error_code == "TARGET_NOT_FOUND":
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(
            status_code=status_code,
            detail=LearningPathErrorResponse(
                error_code=error_code,
                message=message,
                details=details,
            ).model_dump(),
        )

    return path


@router.post("/{target_node_id}/plan", response_model=dict[str, Any])
async def generate_learning_path_plan(
    target_node_id: UUID,
    include_related: bool = Query(False, description="是否在响应里返回推荐拓展节点"),
    selected_related_node_ids: list[UUID] = Query(default_factory=list, description="用户选择纳入计划的相关节点"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: GraphReasoningService = Depends(get_graph_reasoning_service),
):
    """
    基于学习路径生成学习计划与任务

    返回 plan_id、plan_summary、tasks 等信息。
    """
    path = await service.generate_learning_path(
        current_user.id,  # type: ignore[arg-type]
        target_node_id,
        include_related_suggestions=include_related,
        selected_related_node_ids=selected_related_node_ids,
    )

    # 检查是否为空路径
    if not path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=LearningPathErrorResponse(
                error_code="NO_PATH",
                message="未找到学习路径或目标节点不存在",
            ).model_dump(),
        )

    # 检查是否为错误响应
    if _is_error_response(path):
        error_code, message, details = _extract_error(path)
        http_status = status.HTTP_400_BAD_REQUEST
        if error_code == "TARGET_NOT_FOUND":
            http_status = status.HTTP_404_NOT_FOUND
        raise HTTPException(
            status_code=http_status,
            detail=LearningPathErrorResponse(
                error_code=error_code,
                message=message,
                details=details,
            ).model_dump(),
        )

    target_node = next((node for node in path if node.get("is_target")), None)
    target_name = str(target_node.get("name", "目标节点")) if target_node else "目标节点"
    path_summary = _format_path_summary(path)

    user_query = f"为目标「{target_name}」生成可执行学习计划并拆解任务。\n学习路径如下：\n{path_summary}"
    enhanced_context = EnhancedAgentContext(
        user_id=str(current_user.id),
        session_id=f"learning-path-{target_node_id}",
        conversation_history=[],
        user_query=user_query,
        knowledge_context=path_summary,
        db_session=db,
    )

    plan_summary, summary_fallback_used = await _generate_plan_summary(
        user_query=user_query,
        enhanced_context=enhanced_context,
        target_name=target_name,
        path=path,
    )
    plan_description = _truncate_text(plan_summary, 1200)

    plan_create = PlanCreate(
        name=f"学习路径：{target_name}",
        type=PlanType.GROWTH,
        description=plan_description,
        subject=target_name,
        daily_available_minutes=60,
    )

    try:
        plan = await PlanService.create(
            db=db,
            obj_in=plan_create,
            user_id=current_user.id,
            redis_client=cache_service.redis,
        )
    except QuotaExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": exc.message,
                "current_count": exc.current_count,
                "max_quota": exc.max_quota,
                "error_code": "QUOTA_EXCEEDED",
            },
        ) from exc

    plan.source = "learning_path"
    plan.source_metadata = {
        "target_node_id": str(target_node_id),
        "path_node_ids": [node["id"] for node in path],
        "selected_related_node_ids": [str(node_id) for node_id in selected_related_node_ids],
        "total_nodes": len(path),
    }
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    plan_id = str(plan.id)

    task_count = min(8, max(5, len(path)))
    tasks_tool = GenerateTasksForPlanTool()
    tool_result = await tasks_tool.execute(
        GenerateTasksForPlanParams(
            plan_id=plan_id,
            topic=target_name,
            difficulty="medium",
            task_count=task_count,
        ),
        user_id=str(current_user.id),
        db_session=db,
    )

    if not tool_result.success:
        return {
            "plan_id": plan_id,
            "plan_summary": plan_summary,
            "tasks": [],
            "retry": True,
            "message": tool_result.error_message or "任务生成失败，可稍后重试",
            "entity_card": build_learning_path_entity_card(
                plan={
                    "id": plan_id,
                    "name": plan.name,
                    "description": plan.description,
                    "type": plan.type.value if plan.type else None,
                    "subject": plan.subject,
                    "source": plan.source,
                    "is_active": True,
                    "task_count": 0,
                },
                tasks=[],
                target_name=target_name,
                tool_name="generate_learning_path_plan",
                source_channel="learning_path",
            ),
        }

    tasks = tool_result.data.get("tasks", []) if tool_result.data else []
    tasks_payload = [
        {
            **task,
            "status": task.get("status", "pending"),
            "plan_id": plan_id,
        }
        for task in tasks
        if isinstance(task, dict)
    ]
    plan_payload = {
        "id": plan_id,
        "name": plan.name,
        "description": plan.description,
        "type": plan.type.value if plan.type else None,
        "subject": plan.subject,
        "source": plan.source,
        "is_active": True,
        "task_count": len(tasks_payload),
    }

    return {
        "plan_id": plan_id,
        "plan_summary": plan_summary,
        "tasks": tasks_payload,
        "retry": summary_fallback_used,
        "message": "已使用稳定兜底方案生成学习计划" if summary_fallback_used else None,
        "entity_card": build_learning_path_entity_card(
            plan=plan_payload,
            tasks=tasks_payload,
            target_name=target_name,
            tool_name="generate_learning_path_plan",
            source_channel="learning_path",
        ),
        "plan_entity_card": build_plan_entity_card(
            plan_payload,
            tool_name="generate_learning_path_plan",
            source_channel="learning_path",
        ),
        "task_list_entity_card": build_task_list_entity_card(
            tasks_payload,
            tool_name="generate_learning_path_plan",
            plan_id=plan_id,
            plan_title=plan.name,
            source_channel="learning_path",
        ),
    }


@router.post("/{target_node_id}/task-path", response_model=dict[str, Any])
async def generate_learning_task_path(
    target_node_id: UUID,
    include_related: bool = Query(True, description="是否在任务路径中纳入推荐拓展节点"),
    selected_related_node_ids: list[UUID] = Query(default_factory=list, description="用户选择纳入任务路径的拓展节点"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: GraphReasoningService = Depends(get_graph_reasoning_service),
):
    """
    生成不占用计划额度的轻量学习路径。

    会直接创建一组任务卡，并把最近一次学习路径摘要写回知识节点详情。
    """
    path = await service.generate_learning_path(
        current_user.id,  # type: ignore[arg-type]
        target_node_id,
        include_related_suggestions=include_related,
        selected_related_node_ids=selected_related_node_ids,
    )

    if not path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=LearningPathErrorResponse(
                error_code="NO_PATH",
                message="未找到学习路径或目标节点不存在",
            ).model_dump(),
        )
    if _is_error_response(path):
        error_code, message, details = _extract_error(path)
        http_status = status.HTTP_400_BAD_REQUEST
        if error_code == "TARGET_NOT_FOUND":
            http_status = status.HTTP_404_NOT_FOUND
        raise HTTPException(
            status_code=http_status,
            detail=LearningPathErrorResponse(
                error_code=error_code,
                message=message,
                details=details,
            ).model_dump(),
        )

    target_node = next((node for node in path if node.get("is_target")), None)
    target_name = str(target_node.get("name", "目标节点")) if target_node else "目标节点"
    active_nodes = [node for node in path if node.get("status") != "mastered"]
    if not active_nodes:
        active_nodes = [node for node in path if not node.get("is_optional")]
    if not active_nodes:
        active_nodes = path

    limited_nodes = active_nodes[:5]
    guide_summary = _build_task_path_guide(target_name, limited_nodes)

    tasks_payload: list[dict[str, Any]] = []
    for index, node in enumerate(limited_nodes, start=1):
        node_id = UUID(str(node["id"]))
        node_name = str(node.get("name", "未知节点"))
        node_description = service.get_node_description(node_id)
        is_target = bool(node.get("is_target"))
        title_prefix = "攻克" if is_target else "学习"
        task = await TaskService.create(
            db=db,
            obj_in=TaskCreate(
                title=f"{title_prefix}：{node_name}",
                type=TaskType.LEARNING,
                estimated_minutes=35 if is_target else 25,
                difficulty=3 if is_target else 2,
                knowledge_node_id=node_id,
                guide_content=_build_task_step_guide(
                    task_index=index,
                    total_steps=len(limited_nodes),
                    node_name=node_name,
                    node_description=node_description,
                    is_target=is_target,
                    summary=guide_summary,
                ),
            ),
            user_id=current_user.id,
        )
        tasks_payload.append(
            {
                "id": str(task.id),
                "title": task.title,
                "type": task.type.value if task.type else "LEARNING",
                "estimated_minutes": int(task.estimated_minutes or 25),
                "status": task.status.value if task.status else "PENDING",
                "knowledge_node_id": str(task.knowledge_node_id) if task.knowledge_node_id else None,
                "guide_content": task.guide_content,
            }
        )

    await _upsert_learning_path_snapshot(
        db=db,
        user_id=current_user.id,
        target_node_id=target_node_id,
        summary=guide_summary,
        tasks_payload=tasks_payload,
        selected_related_node_ids=selected_related_node_ids,
        mode="task_path",
    )

    return {
        "mode": "task_path",
        "target_node_id": str(target_node_id),
        "target_name": target_name,
        "plan_summary": guide_summary,
        "tasks": tasks_payload,
        "message": f"已为「{target_name}」生成 {len(tasks_payload)} 张可立即执行的任务卡",
        "retry": False,
        "task_list_entity_card": build_task_list_entity_card(
            tasks_payload,
            tool_name="generate_learning_task_path",
            source_channel="learning_path",
        ),
    }


@router.post("/{target_node_id}/full-plan")
async def generate_full_path_plan(
    target_node_id: UUID,
    include_related: bool = Query(False, description="是否在返回路径时附带推荐拓展节点"),
    selected_related_node_ids: list[UUID] = Query(default_factory=list, description="用户选择纳入完整计划的相关节点"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: GraphReasoningService = Depends(get_graph_reasoning_service),
):
    """
    Generate a full learning plan where every step makes the Galaxy alive.
    Filters out mastered nodes and sequentially creates subtasks.
    """
    # 1. 获取路径，过滤 mastered
    path = await service.generate_learning_path(
        current_user.id,
        target_node_id,
        include_related_suggestions=include_related,
        selected_related_node_ids=selected_related_node_ids,
    )
    if not path:
        raise HTTPException(status_code=404, detail="未找到学习路径")
    if _is_error_response(path):
        error_code, message, details = _extract_error(path)
        http_status = status.HTTP_400_BAD_REQUEST
        if error_code == "TARGET_NOT_FOUND":
            http_status = status.HTTP_404_NOT_FOUND
        raise HTTPException(
            status_code=http_status,
            detail=LearningPathErrorResponse(
                error_code=error_code,
                message=message,
                details=details,
            ).model_dump(),
        )

    active_nodes = [n for n in path if n.get("status") != "mastered"]
    if not active_nodes:
        raise HTTPException(status_code=400, detail="所有节点已掌握，无需生成计划")

    target_node = next((n for n in path if n.get("is_target")), active_nodes[-1])
    target_name = target_node.get("name", "目标节点")

    # 2. Full-plan 要优先保证稳定落地，避免被 LLM 速率限制拖垮用户点击链路。
    # 这里直接使用确定性的兜底摘要，确保“生成计划 -> 创建父任务/子任务 -> 跳转计划页”稳定可用。
    plan_summary = _build_fallback_plan_summary(str(target_name), active_nodes)
    summary_fallback_used = True

    # 3. 创建 Plan
    plan_description = _truncate_text(plan_summary, 1200)
    try:
        plan = await PlanService.create(
            db=db,
            obj_in=PlanCreate(
                name=f"学习路径：{target_name}",
                type=PlanType.GROWTH,
                description=plan_description,
                subject=target_name,
                daily_available_minutes=60,
            ),
            user_id=current_user.id,  # type: ignore
            redis_client=cache_service.redis,
        )
    except QuotaExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": exc.message,
                "current_count": exc.current_count,
                "max_quota": exc.max_quota,
                "error_code": "QUOTA_EXCEEDED",
            },
        ) from exc

    # Phase 4: 设置学习路径来源信息
    plan.source = "learning_path"
    plan.source_metadata = {
        "target_node_id": str(target_node_id),
        "path_node_ids": [n["id"] for n in active_nodes],
        "selected_related_node_ids": [str(node_id) for node_id in selected_related_node_ids],
        "total_nodes": len(active_nodes),
    }
    db.add(plan)

    # 4. 创建父任务
    from app.models.task import SubTask, TaskType

    # 第一次遍历：计算总预估时间
    total_estimated = 0
    for node in active_nodes:
        node_id = UUID(node["id"]) if isinstance(node["id"], str) else node["id"]
        edge_count = service.get_node_edge_count(node_id)
        if edge_count <= 2:
            base_minutes = 15
        elif edge_count <= 5:
            base_minutes = 25
        else:
            base_minutes = 40

        is_target = node.get("is_target", False)
        if is_target:
            total_estimated += base_minutes * 2 + 30  # 理解 + 练习 + 综合
        else:
            total_estimated += base_minutes

    parent_task = await TaskService.create(
        db=db,
        obj_in=TaskCreate(
            title=f"学习路径：{target_name}",
            type=TaskType.LEARNING,
            plan_id=plan.id,  # type: ignore
            estimated_minutes=total_estimated,
            difficulty=2,
            knowledge_node_id=target_node_id,
        ),
        user_id=current_user.id,  # type: ignore
    )

    # 5. 按拓扑顺序创建 SubTask 链（第二次遍历）
    order = 1
    for node in active_nodes:
        is_target = node.get("is_target", False)
        node_id = UUID(node["id"]) if isinstance(node["id"], str) else node["id"]

        edge_count = service.get_node_edge_count(node_id)
        if edge_count <= 2:
            base_minutes = 15
        elif edge_count <= 5:
            base_minutes = 25
        else:
            base_minutes = 40

        node_description = service.get_node_description(node_id)
        node_name = node.get("name", "Unknown")

        if is_target:
            # 目标节点拆 3 条
            subtask_configs = [
                ("理解核心概念", base_minutes),
                ("练习巩固", base_minutes),
                ("综合应用", 30),
            ]
            for label, est_min in subtask_configs:
                guide = (
                    f"核心概念：{node_description}\n建议资源：{node_name} 相关知识点\n练习方向：实际应用和综合练习"
                    if node_description
                    else f"学习 {node_name} 的核心内容并进行练习"
                )
                subtask = SubTask(
                    parent_task_id=parent_task.id,
                    title=f"{label}：{node_name}",
                    order=order,
                    knowledge_node_id=node_id,
                    status=SubTaskStatus.PENDING,
                    estimated_minutes=est_min,
                    guide_content=guide,
                )
                db.add(subtask)
                order += 1
        else:
            # 前置节点 1 条
            guide = (
                f"核心概念：{node_description}\n建议资源：{node_name} 相关知识点\n练习方向：基础理解和应用"
                if node_description
                else f"学习 {node_name} 的基础内容"
            )
            subtask = SubTask(
                parent_task_id=parent_task.id,
                title=f"学习：{node_name}",
                order=order,
                knowledge_node_id=node_id,
                status=SubTaskStatus.PENDING,
                estimated_minutes=base_minutes,
                guide_content=guide,
            )
            db.add(subtask)
            order += 1

    await db.commit()

    full_plan_payload = {
        "id": str(plan.id),
        "name": plan.name,
        "description": plan.description,
        "type": plan.type.value if plan.type else None,
        "subject": plan.subject,
        "source": plan.source,
        "is_active": True,
        "task_count": order - 1,
    }
    parent_task_payload = {
        "id": str(parent_task.id),
        "title": parent_task.title,
        "type": parent_task.type.value if parent_task.type else None,
        "estimated_minutes": parent_task.estimated_minutes,
        "difficulty": parent_task.difficulty,
        "plan_id": str(plan.id),
        "status": parent_task.status.value if parent_task.status else "pending",
    }

    return {
        "plan_id": str(plan.id),
        "plan_summary": plan_summary,
        "parent_task_id": str(parent_task.id),
        "subtask_count": order - 1,
        "fallback_used": summary_fallback_used,
        "entity_card": build_learning_path_entity_card(
            plan=full_plan_payload,
            tasks=[parent_task_payload],
            target_name=str(target_name),
            tool_name="generate_full_path_plan",
            source_channel="learning_path",
        ),
        "plan_entity_card": build_plan_entity_card(
            full_plan_payload,
            tool_name="generate_full_path_plan",
            source_channel="learning_path",
        ),
        "task_list_entity_card": build_task_list_entity_card(
            [parent_task_payload],
            tool_name="generate_full_path_plan",
            plan_id=str(plan.id),
            plan_title=plan.name,
            source_channel="learning_path",
        ),
    }


def _format_path_summary(path: list[dict[str, Any]]) -> str:
    lines = []
    for node in path:
        name = node.get("name", "Unknown")
        status = node.get("status", "locked")
        tag = "目标" if node.get("is_target") else status
        lines.append(f"- {name} ({tag})")
    return "\n".join(lines)


def _truncate_text(text: str, limit: int) -> str:
    clean = (text or "").strip()
    if len(clean) <= limit:
        return clean
    return f"{clean[:limit].rstrip()}…"
