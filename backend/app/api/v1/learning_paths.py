"""
Learning Paths API
基于拓扑排序的动态学习路径接口
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.collaboration_workflows import TaskDecompositionWorkflow
from app.agents.enhanced_agents import EnhancedAgentContext
from app.api.deps import get_current_user, get_current_user_id, get_db
from app.core.cache import cache_service
from app.core.exceptions import QuotaExceededError
from app.models.plan import PlanType
from app.models.user import User
from app.schemas.plan import PlanCreate
from app.services.graph_reasoning_service import GraphReasoningService
from app.services.plan_service import PlanService
from app.tools.plan_tools import GenerateTasksForPlanTool
from app.tools.schemas import GenerateTasksForPlanParams

router = APIRouter(prefix="/learning-paths", tags=["Learning Paths"])

async def get_graph_reasoning_service(db: AsyncSession = Depends(get_db)) -> GraphReasoningService:
    return GraphReasoningService(db)

@router.get("/{target_node_id}", response_model=list[dict[str, Any]])
async def get_dynamic_learning_path(
    target_node_id: UUID,
    user_id: str = Depends(get_current_user_id),
    service: GraphReasoningService = Depends(get_graph_reasoning_service)
):
    """
    获取到达目标节点的动态学习路径 (DAG Topological Sort)

    返回按学习顺序排列的节点列表，包含状态（locked/unlocked/mastered）。
    """
    path = await service.generate_learning_path(UUID(user_id), target_node_id)

    if not path:
        # 可能是目标节点不存在，或者没有路径（比如孤立点）
        # 这里返回空列表而不是 404，由前端处理提示 "无需前置" 或 "未找到"
        return []

    return path


@router.post("/{target_node_id}/plan", response_model=dict[str, Any])
async def generate_learning_path_plan(
    target_node_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: GraphReasoningService = Depends(get_graph_reasoning_service)
):
    """
    基于学习路径生成学习计划与任务

    返回 plan_id、plan_summary、tasks 等信息。
    """
    path = await service.generate_learning_path(current_user.id, target_node_id)
    if not path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到学习路径或目标节点不存在",
        )

    target_node = next((node for node in path if node.get("is_target")), None)
    target_name = target_node.get("name") if target_node else "目标节点"
    path_summary = _format_path_summary(path)

    user_query = (
        f"为目标「{target_name}」生成可执行学习计划并拆解任务。\n"
        f"学习路径如下：\n{path_summary}"
    )
    enhanced_context = EnhancedAgentContext(
        user_id=str(current_user.id),
        session_id=f"learning-path-{target_node_id}",
        conversation_history=[],
        user_query=user_query,
        knowledge_context=path_summary,
        db_session=db,
    )

    workflow = TaskDecompositionWorkflow(None)
    collaboration_result = await workflow.execute(user_query, enhanced_context)
    plan_summary = collaboration_result.final_response
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

    task_count = min(8, max(5, len(path)))
    tasks_tool = GenerateTasksForPlanTool()
    tool_result = await tasks_tool.execute(
        GenerateTasksForPlanParams(
            plan_id=str(plan.id),
            topic=target_name,
            difficulty="medium",
            task_count=task_count,
        ),
        user_id=str(current_user.id),
        db_session=db,
    )

    if not tool_result.success:
        return {
            "plan_id": str(plan.id),
            "plan_summary": plan_summary,
            "tasks": [],
            "retry": True,
            "message": tool_result.error_message or "任务生成失败，可稍后重试",
        }

    tasks = tool_result.data.get("tasks", []) if tool_result.data else []
    tasks_payload = [
        {
            **task,
            "status": task.get("status", "pending"),
            "plan_id": str(plan.id),
        }
        for task in tasks
        if isinstance(task, dict)
    ]

    return {
        "plan_id": str(plan.id),
        "plan_summary": plan_summary,
        "tasks": tasks_payload,
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
