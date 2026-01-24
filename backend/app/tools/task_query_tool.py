"""
P0-3: Task Query Tool - 任务卡片查询与修改工具

Allows LLM to query and modify specific task cards within a plan.
Tools:
- QueryPlanTasksTool: Query tasks with filters (status, type, limit)
- ModifyPlanTaskTool: Modify task properties (title, status, priority, guide_content)
"""
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, and_

from .base import BaseTool, ToolCategory, ToolResult
from .schemas import QueryPlanTasksParams, ModifyPlanTaskParams, TaskStatusFilter
from app.models.task import Task, TaskStatus as ModelTaskStatus, TaskType as ModelTaskType
from app.services.task_service import TaskService
from app.schemas.task import TaskUpdate


class QueryPlanTasksTool(BaseTool):
    """查询计划内的任务列表"""

    name = "query_plan_tasks"
    description = """查询计划内的任务列表，支持按状态和类型筛选。
    当需要了解计划中有哪些任务、或查找特定状态的任务时使用，例如：
    - "这个计划里有哪些待办任务？"
    - "帮我看看已完成的任务"
    - "查找所有学习类型的任务"
    """
    category = ToolCategory.TASK
    parameters_schema = QueryPlanTasksParams
    requires_confirmation = False

    async def execute(
        self,
        params: QueryPlanTasksParams,
        user_id: str,
        db_session: Any,
        tool_call_id: Optional[str] = None,
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)
            plan_uuid = UUID(params.plan_id)

            # Build query
            query = select(Task).where(
                and_(
                    Task.user_id == user_uuid,
                    Task.plan_id == plan_uuid,
                    Task.deleted_at.is_(None),
                )
            )

            # Apply status filter
            if params.status_filter != TaskStatusFilter.ALL:
                status_map = {
                    TaskStatusFilter.PENDING: ModelTaskStatus.PENDING,
                    TaskStatusFilter.IN_PROGRESS: ModelTaskStatus.IN_PROGRESS,
                    TaskStatusFilter.COMPLETED: ModelTaskStatus.COMPLETED,
                    TaskStatusFilter.ABANDONED: ModelTaskStatus.ABANDONED,
                }
                query = query.where(Task.status == status_map[params.status_filter])

            # Apply type filter
            if params.type_filter:
                query = query.where(Task.type == ModelTaskType(params.type_filter.value))

            # Order and limit
            query = query.order_by(Task.priority.desc(), Task.created_at.desc()).limit(
                params.limit
            )

            result = await db_session.execute(query)
            tasks = result.scalars().all()

            if not tasks:
                return ToolResult(
                    success=True,
                    tool_name=self.name,
                    data={"task_count": 0},
                    widget_type="task_list",
                    widget_data={"tasks": [], "message": "该计划下暂无符合条件的任务"},
                )

            # Format tasks for response
            task_list = []
            for task in tasks:
                task_list.append(
                    {
                        "id": str(task.id),
                        "title": task.title,
                        "type": task.type.value,
                        "status": task.status.value,
                        "priority": task.priority,
                        "difficulty": task.difficulty,
                        "estimated_minutes": task.estimated_minutes,
                        "tags": task.tags or [],
                        "created_at": task.created_at.isoformat() if task.created_at else None,
                    }
                )

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"task_count": len(task_list)},
                widget_type="task_list",
                widget_data={
                    "tasks": task_list,
                    "plan_id": params.plan_id,
                    "filter": params.status_filter.value,
                },
            )

        except ValueError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"无效的参数: {e}",
                suggestion="请检查 plan_id 是否为有效的 UUID 格式",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="查询失败，请稍后重试或检查参数",
            )


class ModifyPlanTaskTool(BaseTool):
    """修改计划内某个任务的属性"""

    name = "modify_plan_task"
    description = """修改计划内某个任务的属性，支持修改标题、状态、优先级和执行指南。
    当需要更新任务信息时使用，例如：
    - "把这个任务优先级设为5"
    - "更新任务的执行指南"
    - "把任务标记为完成"
    """
    category = ToolCategory.TASK
    parameters_schema = ModifyPlanTaskParams
    requires_confirmation = False

    async def execute(
        self,
        params: ModifyPlanTaskParams,
        user_id: str,
        db_session: Any,
        tool_call_id: Optional[str] = None,
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)
            task_uuid = UUID(params.task_id)

            # Fetch the task
            task = await TaskService.get_by_id(db_session, task_uuid, user_uuid)
            if not task:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message="任务不存在或无权访问",
                    suggestion="请确认任务 ID 是否正确",
                )

            # Build update payload
            update_fields = {}

            if params.title is not None:
                update_fields["title"] = params.title

            if params.status is not None:
                status_map = {
                    "pending": ModelTaskStatus.PENDING,
                    "in_progress": ModelTaskStatus.IN_PROGRESS,
                    "completed": ModelTaskStatus.COMPLETED,
                    "abandoned": ModelTaskStatus.ABANDONED,
                }
                if params.status.lower() not in status_map:
                    return ToolResult(
                        success=False,
                        tool_name=self.name,
                        error_message=f"无效的状态值: {params.status}",
                        suggestion="状态应为 pending/in_progress/completed/abandoned 之一",
                    )
                update_fields["status"] = status_map[params.status.lower()]

            if params.priority is not None:
                update_fields["priority"] = params.priority

            if params.guide_content is not None:
                update_fields["guide_content"] = params.guide_content

            if not update_fields:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message="未提供任何修改内容",
                    suggestion="请至少指定一个要修改的字段 (title/status/priority/guide_content)",
                )

            # Apply update
            task_update = TaskUpdate(**update_fields)
            updated_task = await TaskService.update(db_session, task, task_update)

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "task_id": str(updated_task.id),
                    "updated_fields": list(update_fields.keys()),
                },
                widget_type="task_card",
                widget_data={
                    "id": str(updated_task.id),
                    "title": updated_task.title,
                    "type": updated_task.type.value,
                    "status": updated_task.status.value,
                    "priority": updated_task.priority,
                    "guide_content": updated_task.guide_content,
                    "updated_at": updated_task.updated_at.isoformat()
                    if updated_task.updated_at
                    else None,
                },
            )

        except ValueError as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"无效的参数: {e}",
                suggestion="请检查 task_id 是否为有效的 UUID 格式",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="修改失败，请稍后重试或检查参数",
            )
