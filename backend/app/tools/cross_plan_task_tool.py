from typing import Type, List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool
from app.models.task import Task, TaskStatus
from app.models.plan import Plan

class QueryAllTasksParams(BaseModel):
    status_filter: Optional[str] = Field(None, description="Filter by status (pending, in_progress, completed)")
    plan_id_filter: Optional[str] = Field(None, description="Filter by specific plan ID")
    limit: int = Field(50, description="Max tasks to return")

class QueryAllTasksTool(BaseTool):
    name = "query_all_tasks"
    description = "Query tasks across all plans. Use this when user asks about 'other plans' or wants a global view."
    args_schema: Type[BaseModel] = QueryAllTasksParams

    async def execute(
        self,
        db: AsyncSession,
        user_id: UUID,
        status_filter: Optional[str] = None,
        plan_id_filter: Optional[str] = None,
        limit: int = 50,
        **kwargs
    ) -> List[Any]:
        query = select(Task, Plan.title.label("plan_title"))\
            .join(Plan, Task.plan_id == Plan.id)\
            .where(Task.user_id == user_id)

        if status_filter:
            try:
                status_enum = TaskStatus(status_filter)
                query = query.where(Task.status == status_enum)
            except ValueError:
                pass  # Ignore invalid status

        if plan_id_filter:
            try:
                plan_uuid = UUID(plan_id_filter)
                query = query.where(Task.plan_id == plan_uuid)
            except ValueError:
                pass

        query = query.order_by(Task.due_date.asc().nulls_last(), Task.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        rows = result.all()
        
        tasks_data = []
        for task, plan_title in rows:
            tasks_data.append({
                "id": str(task.id),
                "title": task.title,
                "plan_title": plan_title,
                "status": task.status.value,
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date else None
            })
            
        return tasks_data
