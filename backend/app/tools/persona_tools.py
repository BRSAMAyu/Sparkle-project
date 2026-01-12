from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

from app.tools.base import BaseTool, ToolCategory, ToolResult
from app.services.persona_service import PersonaService


class PersonaRequest(BaseModel):
    purpose: str = Field(..., description="learning_recommendation, chat_style, safety_guard")


class PersonaTool(BaseTool):
    name = "get_persona_snapshot"
    description = "获取经过脱敏处理的用户画像快照，用于个性化反馈"
    category = ToolCategory.QUERY
    parameters_schema = PersonaRequest

    async def execute(self, params: PersonaRequest, user_id: str, db_session, tool_call_id: Optional[str] = None) -> ToolResult:
        service = PersonaService(db_session)
        snapshot = await service.get_snapshot(UUID(user_id), params.purpose)
        return ToolResult(
            success=True,
            tool_name=self.name,
            data=snapshot,
            widget_type=None,
            widget_data=None
        )
