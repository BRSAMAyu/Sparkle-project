from typing import Any
from uuid import UUID

from .base import BaseTool, ToolCategory, ToolResult
from .schemas import SuggestFocusSessionParams
from app.models.task import Task


class SuggestFocusSessionTool(BaseTool):
    """专注会话建议"""
    name = "suggest_focus_session"
    description = """生成一个可立即开始的专注冲刺卡片，可绑定到某个任务。"""
    category = ToolCategory.FOCUS
    parameters_schema = SuggestFocusSessionParams
    requires_confirmation = False

        async def execute(

            self, 

            params: SuggestFocusSessionParams, 

            user_id: str,

            db_session: Any,

            tool_call_id: Optional[str] = None

        ) -> ToolResult:

    
        try:
            task_data = None
            title = params.task_title or "专注冲刺"

            if params.task_id:
                task = await db_session.get(Task, UUID(params.task_id))
                if not task or str(task.user_id) != user_id:
                    return ToolResult(
                        success=False,
                        tool_name=self.name,
                        error_message="未找到对应任务",
                        suggestion="请确认任务是否存在或创建新的专注任务"
                    )

                title = task.title
                task_data = {
                    "id": str(task.id),
                    "title": task.title,
                    "type": task.type.value,
                    "status": task.status.value,
                    "estimated_minutes": task.estimated_minutes,
                    "priority": task.priority,
                    "difficulty": task.difficulty,
                    "energy_cost": task.energy_cost,
                    "tags": task.tags or [],
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                }

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"duration_minutes": params.duration_minutes},
                widget_type="focus_card",
                widget_data={
                    "title": title,
                    "duration_minutes": params.duration_minutes,
                    "reason": "建议立即开始一段专注冲刺",
                    "task": task_data,
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="请稍后再试或直接进入专注模式"
            )
