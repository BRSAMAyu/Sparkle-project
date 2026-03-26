from __future__ import annotations

from urllib.parse import urlencode
from uuid import UUID

from pydantic import BaseModel, Field

from app.services.simulation.simulation_engine import SimulationEngine
from app.tools.base import BaseTool, ToolCategory, ToolResult


class QuickSimulationParams(BaseModel):
    scenario_key: str = Field(default="study_group", description="学习模拟场景 key")
    seed_topic: str | None = Field(default=None, description="模拟主题")
    source_chat_session_id: str | None = Field(default=None, description="来源聊天会话 ID")


class QuickSimulationTool(BaseTool):
    name = "run_quick_simulation"
    description = "快速运行一个学习模拟预览，适合学习小组、知识辩论和角色扮演"
    category = ToolCategory.QUERY
    parameters_schema = QuickSimulationParams
    requires_confirmation = False

    async def execute(
        self,
        params: QuickSimulationParams,
        user_id: str,
        db_session,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        topic = (params.seed_topic or "当前学习主题").strip()
        scenario_key = (params.scenario_key or "study_group").strip() or "study_group"
        try:
            engine = SimulationEngine(db_session)
            session = await engine.run(
                topic=topic,
                scenario_key=scenario_key,
                user_id=UUID(user_id),
            )
            query = {
                "topic": topic,
                "scenario_key": scenario_key,
            }
            if params.source_chat_session_id:
                query["source_chat_session_id"] = params.source_chat_session_id

            return ToolResult(
                success=True,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                data={
                    "session_id": session.id,
                    "scenario_key": session.scenario_key,
                    "topic": session.topic,
                    "participants": list(session.participants or []),
                    "round_preview": list(session.rounds or [])[:3],
                    "insight_summary": session.insight_summary,
                    "open_simulation": True,
                    "deep_link": f"/simulation?{urlencode(query)}",
                    "source_chat_session_id": params.source_chat_session_id,
                },
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                error_message=f"启动学习模拟失败: {exc}",
                error_type="simulation_launch_failed",
            )
