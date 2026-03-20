from __future__ import annotations
"""
PlanState Tools - LLM tools for accessing plan state and tasks

Provides tools for the LLM to:
1. Get plan state (facts, milestones, task_index)
2. Get task summaries within a plan
3. Get detailed task information

Usage:
    These tools are registered in the ToolRegistry and can be invoked by the LLM
    through function calling.
"""
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.services.plan_state_service import PlanStateService
from app.services.task_state_sync import TaskStateSyncService
from app.tools.base import BaseTool, ToolCategory, ToolResult
from app.tools.entity_cards import build_task_list_entity_card, wrap_widget_payload
from app.tools.plan_resolution import PlanResolutionError, resolve_user_plan_reference

# ============================================
# Parameter Schemas
# ============================================

class GetPlanStateParams(BaseModel):
    """Parameters for get_plan_state tool"""
    plan_id: str = Field(
        ...,
        description="计划ID、计划名称，或当前想查询的计划引用"
    )


class GetTaskSummaryParams(BaseModel):
    """Parameters for get_task_summary tool"""
    plan_id: str = Field(
        ...,
        description="计划ID、计划名称，或当前想查询的计划引用"
    )
    limit: int = Field(
        default=10,
        description="返回的任务数量上限",
        ge=1,
        le=50
    )


class GetTaskDetailParams(BaseModel):
    """Parameters for get_task_detail tool"""
    task_id: str = Field(
        ...,
        description="任务ID (UUID格式)"
    )


# ============================================
# Tool Implementations
# ============================================

class GetPlanStateTool(BaseTool):
    """
    获取计划状态工具

    Returns plan-level state including:
    - facts: Learned facts during plan execution
    - milestones: Achievement records
    - task_index: Task completion statistics
    - constraints: Runtime constraints
    """
    name = "get_plan_state"
    description = "获取当前计划的状态信息，包括进度、里程碑、任务统计等"
    category = ToolCategory.PLAN
    parameters_schema = GetPlanStateParams
    requires_confirmation = False

    async def execute(
        self,
        params: GetPlanStateParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)
            resolved = await resolve_user_plan_reference(
                db_session,
                user_id=user_uuid,
                plan_ref=params.plan_id,
            )
        except PlanResolutionError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion=e.suggestion,
                data={
                    "available_plans": e.available_plan_names,
                } if e.available_plan_names else None,
            )
        except ValueError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"无效的用户ID格式: {e}",
            )

        try:
            service = PlanStateService(db_session)
            state = await service.get_plan_state(user_uuid, resolved.plan_id)

            if state is None:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message=f"未找到计划状态: plan={resolved.plan_name}",
                    suggestion="请确认该计划仍然有效，或切换到其他计划后重试",
                )

            # Build lightweight response (format matches frontend PlanContextData)
            data = {
                "plan_id": str(state.plan_id),
                "plan_name": resolved.plan_name,
                "resolved_via": resolved.resolution,
                "status": state.status,
                "version": state.version,
                "facts": state.facts or {},
                "milestones": [
                    {
                        "id": m.get("id"),
                        "title": m.get("title"),
                        "achieved_at": m.get("achieved_at"),
                    }
                    for m in (state.milestones or [])[-5:]  # Last 5 milestones
                ],
                "task_index": state.task_index or {},
                "task_summary": {  # Frontend expects "task_summary" alias
                    "total": (state.task_index or {}).get("total", 0),
                    "completed": (state.task_index or {}).get("completed", 0),
                },
                "task_summaries": (state.task_summaries or [])[:10],
                "recent_feedback": (state.feedback_log or [])[-5:],  # Last 5 feedback entries
                "constraints": state.constraints or {},
            }

            return ToolResult(
                success=True,
                tool_name=self.name,
                data=data,
                widget_type="plan_context_summary",  # Match frontend widget type
                widget_data=data,
            )

        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"获取计划状态失败: {e}",
            )


class GetTaskSummaryTool(BaseTool):
    """
    获取计划内任务摘要工具

    Returns lightweight summaries of tasks within a plan.
    """
    name = "get_task_summary"
    description = "获取计划内的任务摘要列表，包括标题、状态、类型、预估时间等"
    category = ToolCategory.TASK
    parameters_schema = GetTaskSummaryParams
    requires_confirmation = False

    async def execute(
        self,
        params: GetTaskSummaryParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)
            resolved = await resolve_user_plan_reference(
                db_session,
                user_id=user_uuid,
                plan_ref=params.plan_id,
            )
        except PlanResolutionError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion=e.suggestion,
                data={
                    "available_plans": e.available_plan_names,
                } if e.available_plan_names else None,
            )
        except ValueError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"无效的用户ID格式: {e}",
            )

        try:
            sync_service = TaskStateSyncService(db_session)
            summaries = await sync_service.get_task_summaries(
                user_id=user_uuid,
                plan_id=resolved.plan_id,
                limit=params.limit,
            )

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "plan_id": str(resolved.plan_id),
                    "plan_name": resolved.plan_name,
                    "resolved_via": resolved.resolution,
                    "task_count": len(summaries),
                    "tasks": summaries,
                },
                widget_type="task_list",
                widget_data=wrap_widget_payload(
                    widget_type="task_list",
                    widget_data={
                        "tasks": summaries,
                        "plan_id": str(resolved.plan_id),
                        "plan_name": resolved.plan_name,
                    },
                    entity_card=build_task_list_entity_card(
                        summaries,
                        tool_name=self.name,
                        plan_id=str(resolved.plan_id),
                        plan_title=resolved.plan_name,
                    ),
                ),
            )

        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"获取任务摘要失败: {e}",
            )


class GetTaskDetailTool(BaseTool):
    """
    获取任务详情工具

    Returns full details of a specific task.
    """
    name = "get_task_detail"
    description = "获取单个任务的完整详情，包括描述、笔记、时间记录等"
    category = ToolCategory.TASK
    parameters_schema = GetTaskDetailParams
    requires_confirmation = False

    async def execute(
        self,
        params: GetTaskDetailParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            task_id = UUID(params.task_id)
            user_uuid = UUID(user_id)
        except ValueError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"无效的ID格式: {e}",
            )

        try:
            sync_service = TaskStateSyncService(db_session)
            detail = await sync_service.get_task_detail(
                user_id=user_uuid,
                task_id=task_id,
            )

            if detail is None:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message=f"未找到任务: task_id={params.task_id}",
                )

            return ToolResult(
                success=True,
                tool_name=self.name,
                data=detail,
                widget_type="task_detail",
                widget_data=detail,
            )

        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"获取任务详情失败: {e}",
            )
