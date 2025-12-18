from typing import Any, Optional
from uuid import UUID
from datetime import datetime

from .base import BaseTool, ToolCategory, ToolResult
from .schemas import CreateTaskParams, UpdateTaskStatusParams, BatchCreateTasksParams
from app.services.task_service import TaskService
from app.schemas.task import TaskCreate, TaskUpdate, TaskCompleteRequest, TaskStatus
from app.models.task import TaskType as ModelTaskType

class CreateTaskTool(BaseTool):
    """创建单个学习任务"""
    name = "create_task"
    description = """创建一个新的学习任务卡片。
    当用户表达想要做某件学习相关的事情时使用，例如：
    - "帮我创建一个复习高数的任务"
    - "我想学习 Python，帮我规划一下"
    - "把刚才讨论的内容整理成任务"
    """
    category = ToolCategory.TASK
    parameters_schema = CreateTaskParams
    requires_confirmation = False
    
    async def execute(
        self, 
        params: CreateTaskParams, 
        user_id: str,
        db_session: Any
    ) -> ToolResult:
        try:
            # Convert string user_id to UUID
            user_uuid = UUID(user_id)
            
            # Map params to TaskCreate schema
            # Note: subject_id is not directly supported in Task model yet, ignoring for now
            task_create = TaskCreate(
                title=params.title,
                type=ModelTaskType(params.task_type.value),
                estimated_minutes=params.estimated_minutes or 30, # Default to 30 if None
                guide_content=params.description,
                priority=params.priority,
                due_date=params.due_date.date() if params.due_date else None,
                tags=[] # tags not provided in params, defaulting to empty
            )
            
            task = await TaskService.create(
                db=db_session,
                obj_in=task_create,
                user_id=user_uuid
            )
            
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"task_id": str(task.id)},
                widget_type="task_card",  # 前端渲染类型
                widget_data={
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.guide_content,
                    "type": task.type.value,
                    "status": task.status.value,
                    "estimated_minutes": task.estimated_minutes,
                    "priority": task.priority,
                    "created_at": task.created_at.isoformat()
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="请检查参数是否正确，或稍后重试"
            )

class UpdateTaskStatusTool(BaseTool):
    """更新任务状态"""
    name = "update_task_status"
    description = """更新任务的状态。
    当用户表达完成、放弃或开始某个任务时使用，例如：
    - "我完成了这个任务"
    - "把这个任务标记为进行中"
    - "放弃这个任务"
    """
    category = ToolCategory.TASK
    parameters_schema = UpdateTaskStatusParams
    requires_confirmation = False
    
    async def execute(
        self, 
        params: UpdateTaskStatusParams, 
        user_id: str,
        db_session: Any
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)
            task_uuid = UUID(params.task_id)
            
            task = await TaskService.get_by_id(db_session, task_uuid, user_uuid)
            if not task:
                raise ValueError("Task not found")
                
            new_status = params.status
            
            if new_status == "in_progress":
                task = await TaskService.start(db_session, task)
            elif new_status == "completed":
                actual_minutes = params.actual_minutes or task.estimated_minutes
                task = await TaskService.complete(db_session, task, actual_minutes=actual_minutes)
            elif new_status == "abandoned":
                task = await TaskService.abandon(db_session, task, reason="User requested via chat")
            elif new_status == "pending":
                # Reset to pending? TaskService doesn't have reset, so manual update
                task_update = TaskUpdate(status=TaskStatus.PENDING)
                task = await TaskService.update(db_session, task, task_update)
            
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"task_id": str(task.id), "new_status": task.status.value},
                widget_type="task_card",
                widget_data={
                    "id": str(task.id),
                    "title": task.title,
                    "status": task.status.value,
                    "actual_minutes": task.actual_minutes
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="请确认任务 ID 是否正确"
            )

class BatchCreateTasksTool(BaseTool):
    """批量创建任务"""
    name = "batch_create_tasks"
    description = """批量创建多个学习任务。
    当需要一次性创建多个相关任务时使用，例如：
    - "帮我制定本周的学习计划，包含 5 个任务"
    - "把这个知识点拆解成几个小任务"
    """
    category = ToolCategory.TASK
    parameters_schema = BatchCreateTasksParams
    requires_confirmation = True  # 批量操作需要确认
    
    async def execute(
        self, 
        params: BatchCreateTasksParams, 
        user_id: str,
        db_session: Any
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)
            created_tasks = []
            
            # Reuse logic from CreateTaskTool implicitly or just call service loop
            for task_params in params.tasks:
                task_create = TaskCreate(
                    title=task_params.title,
                    type=ModelTaskType(task_params.task_type.value),
                    estimated_minutes=task_params.estimated_minutes or 30,
                    guide_content=task_params.description,
                    priority=task_params.priority,
                    due_date=task_params.due_date.date() if task_params.due_date else None,
                    tags=[]
                )
                
                task = await TaskService.create(
                    db=db_session,
                    obj_in=task_create,
                    user_id=user_uuid
                )
                
                created_tasks.append({
                    "id": str(task.id),
                    "title": task.title,
                    "type": task.type.value,
                    "status": task.status.value
                })
            
            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"task_count": len(created_tasks)},
                widget_type="task_list",  # 任务列表组件
                widget_data={"tasks": created_tasks}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="批量创建失败，请检查参数或减少任务数量后重试"
            )
