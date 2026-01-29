"""
Prism/Cognitive Prism Tools - 认知棱镜工具

Provides tools for behavior analysis and cognitive prism features.
"""
from typing import Any
from uuid import UUID

from loguru import logger
from pydantic import BaseModel

from app.services.cognitive_service import CognitiveService

from .base import BaseTool, ToolCategory, ToolResult


# Empty params schema - this tool doesn't need any parameters
class GetUserBehaviorPatternsParams(BaseModel):
    """获取用户行为模式的参数（无需参数）"""
    pass


class GetUserBehaviorPatternsTool(BaseTool):
    """获取用户行为模式/认知棱镜数据"""

    name = "get_user_behavior_patterns"
    description = """获取用户的行为模式分析结果，包括认知模式、情绪模式和执行模式。
    用于回答用户关于学习习惯、行为分析、认知棱镜、用户画像等请求。
    返回用户已识别的行为定式、模式描述和破解建议。
    """
    category = ToolCategory.QUERY
    parameters_schema = GetUserBehaviorPatternsParams
    requires_confirmation = False

    async def execute(
        self,
        params: Any,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None
    ) -> ToolResult:
        try:
            user_uuid = UUID(user_id)
            service = CognitiveService(db_session)

            # Get user's behavior patterns with minimum confidence threshold
            patterns = await service.get_user_patterns(user_uuid, min_confidence=0.5)

            if not patterns:
                return ToolResult(
                    success=True,
                    tool_name=self.name,
                    data={"patterns": [], "message": "暂无足够的行为数据进行分析，继续学习后会越来越准确"},
                    widget_type="prism_card",
                    widget_data={
                        "patterns": [],
                        "message": "暂无行为模式数据"
                    }
                )

            # Format patterns for response
            pattern_list = []
            for p in patterns:
                pattern_list.append({
                    "id": str(p.id),
                    "pattern_name": p.pattern_name,
                    "pattern_type": p.pattern_type,
                    "description": p.description,
                    "solution_text": p.solution_text,
                    "confidence_score": p.confidence_score,
                    "frequency": p.frequency
                })

            # Group by pattern type for better presentation
            cognitive = [p for p in pattern_list if p.get("pattern_type") == "cognitive"]
            emotional = [p for p in pattern_list if p.get("pattern_type") == "emotional"]
            execution = [p for p in pattern_list if p.get("pattern_type") == "execution"]

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "patterns": pattern_list,
                    "summary": {
                        "cognitive_count": len(cognitive),
                        "emotional_count": len(emotional),
                        "execution_count": len(execution),
                        "total": len(pattern_list)
                    }
                },
                widget_type="prism_card",
                widget_data={
                    "patterns": pattern_list,
                    "cognitive": cognitive,
                    "emotional": emotional,
                    "execution": execution
                }
            )

        except Exception as e:
            logger.error(f"GetUserBehaviorPatternsTool failed: {e}")
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=str(e),
                suggestion="请稍后再试或联系客服"
            )
