from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.services.report.learning_report_agent import LearningReportAgent
from app.tools.base import BaseTool, ToolCategory, ToolResult


class GenerateLearningReportParams(BaseModel):
    section_limit: int = Field(default=4, ge=2, le=5, description="学习报告章节数量")
    delivery_mode: str = Field(default="chat_bridge", description="报告生成模式：chat_bridge 或 full")
    source_chat_session_id: str | None = Field(default=None, description="来源聊天会话 ID")


class GenerateLearningReportTool(BaseTool):
    name = "generate_learning_report"
    description = "快速生成学习分析报告预览，并提供进入学习报告页的入口"
    category = ToolCategory.QUERY
    parameters_schema = GenerateLearningReportParams
    requires_confirmation = False

    async def execute(
        self,
        params: GenerateLearningReportParams,
        user_id: str,
        db_session,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            agent = LearningReportAgent(db_session)
            report = await agent.generate_report(
                UUID(user_id),
                section_limit=params.section_limit,
                delivery_mode=params.delivery_mode,
                trigger_source="chat",
            )
            preview = dict(report.get("report_preview") or {})
            preview.setdefault("report_id", str(report.get("report_id") or ""))
            preview.setdefault("markdown", str(report.get("markdown") or ""))
            preview.setdefault("sections", list(report.get("sections") or []))
            preview.setdefault("mastery", list(report.get("mastery") or []))

            return ToolResult(
                success=True,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                data={
                    "report_id": str(report.get("report_id") or ""),
                    "report_preview": preview,
                    "quality_mode": str(report.get("quality_mode") or ""),
                    "deep_link": str(report.get("deep_link") or "/learning-report"),
                    "open_report": True,
                    "source_chat_session_id": params.source_chat_session_id,
                },
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                error_message=f"生成学习报告失败: {exc}",
                error_type="learning_report_generation_failed",
            )
