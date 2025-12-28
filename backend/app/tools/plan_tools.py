from typing import Any
from uuid import UUID

from .base import BaseTool, ToolCategory, ToolResult
from .schemas import CreatePlanParams
from app.services.plan_service import PlanService
from app.schemas.plan import PlanCreate
from app.models.plan import PlanType as ModelPlanType


class CreatePlanTool(BaseTool):
    """创建学习计划"""
    name = "create_plan"
    description = """创建冲刺计划或成长计划，并返回计划卡片。"""
    category = ToolCategory.PLAN
    parameters_schema = CreatePlanParams
    requires_confirmation = False

    async def execute(
        self,
        params: CreatePlanParams,
        user_id: str,
        db_session: Any
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)
            plan_type = ModelPlanType(params.plan_type.value)

            plan_create = PlanCreate(
                name=params.title,
                type=plan_type,
                description=params.description,
                subject=params.subject_id,
                target_date=params.target_date.date() if params.target_date else None,
                daily_available_minutes=60,
            )

            plan = await PlanService.create(
                db=db_session,
                obj_in=plan_create,
                user_id=user_uuid
            )

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={"plan_id": str(plan.id)},
                widget_type="plan_card",
                widget_data={
                    "id": str(plan.id),
                    "title": plan.name,
                    "type": plan.type.value,
                    "description": plan.description,
                    "target_date": plan.target_date.isoformat() if plan.target_date else None,
                    "target_mastery": params.target_mastery,
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="请检查计划参数或稍后再试"
            )
