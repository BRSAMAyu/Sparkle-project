from __future__ import annotations

from urllib.parse import urlencode
from uuid import UUID

from pydantic import BaseModel, Field

from app.services.theater.prediction_theater_service import PredictionTheaterService
from app.tools.base import BaseTool, ToolCategory, ToolResult


class LaunchPredictionParams(BaseModel):
    topic: str = Field(..., min_length=1, description="学习目标、路径推演主题或 what-if 问题")
    target_node_id: str | None = Field(default=None, description="可选的知识节点 UUID")
    source_chat_session_id: str | None = Field(default=None, description="来源聊天会话 ID")


class LaunchPredictionTool(BaseTool):
    name = "launch_prediction"
    description = "为学习规划、路径推演或跳过知识点后的影响生成知识推演剧场预览"
    category = ToolCategory.QUERY
    parameters_schema = LaunchPredictionParams
    requires_confirmation = False

    async def execute(
        self,
        params: LaunchPredictionParams,
        user_id: str,
        db_session,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            target_node_uuid = None
            if params.target_node_id:
                target_node_uuid = UUID(params.target_node_id)

            service = PredictionTheaterService(db_session)
            prediction = await service.generate_prediction(
                user_id=UUID(user_id),
                topic=params.topic,
                target_node_id=target_node_uuid,
            )
            paths = []
            for item in list(prediction.get("paths") or [])[:3]:
                if not isinstance(item, dict):
                    continue
                paths.append(
                    {
                        "id": str(item.get("id") or ""),
                        "title": str(item.get("title") or ""),
                        "estimated_mastery": float(item.get("estimated_mastery") or 0.0),
                        "estimated_completion_rate": float(item.get("estimated_completion_rate") or 0.0),
                    }
                )

            query = {
                "topic": params.topic,
                "target_node_id": str(prediction.get("target_node_id") or params.target_node_id or ""),
            }
            if params.source_chat_session_id:
                query["source_chat_session_id"] = params.source_chat_session_id

            return ToolResult(
                success=True,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                data={
                    "prediction_id": str(prediction.get("prediction_id") or ""),
                    "topic": params.topic,
                    "target_node_id": str(prediction.get("target_node_id") or params.target_node_id or ""),
                    "paths": paths,
                    "open_theater": True,
                    "deep_link": f"/theater?{urlencode({k: v for k, v in query.items() if v})}",
                    "source_chat_session_id": params.source_chat_session_id,
                },
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                error_message=f"启动知识推演失败: {exc}",
                error_type="prediction_launch_failed",
            )
