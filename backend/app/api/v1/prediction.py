"""
意图预测 API Endpoints
Intent Prediction API

提供实时意图预测接口，用于前端打字时显示预测建议
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.shadow_prediction_service import shadow_prediction_service

router = APIRouter()


class IntentPredictRequest(BaseModel):
    """意图预测请求"""
    partial_text: str = Field(..., description="部分输入的文本", min_length=1)
    active_plan_id: str | None = Field(default=None, description="当前活跃的计划ID")


class IntentPredictResponse(BaseModel):
    """意图预测响应"""
    intent_type: str = Field(description="预测的意图类型")
    confidence: float = Field(description="置信度 0-1")
    suggested_actions: list[str] = Field(description="建议的操作列表", default_factory=list)
    suggested_tools: list[str] = Field(description="可能使用的工具", default_factory=list)
    execution_mode: str = Field(description="预测的执行模式: direct/langgraph")
    mode_confidence: float = Field(description="执行模式置信度")


@router.post("/intent/predict", response_model=dict[str, Any])
async def predict_intent(
    request: IntentPredictRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    实时意图预测

    用于前端打字时调用，返回预测的意图类型和建议操作。

    Returns:
        - intent_type: 预测的意图类型 (task_management/knowledge_query/time_planning等)
        - confidence: 置信度 0-1
        - suggested_actions: 建议的操作列表
        - suggested_tools: 可能使用的工具列表
        - execution_mode: 预测的执行模式 (direct/langgraph)
        - mode_confidence: 执行模式置信度
    """
    try:
        # Call lightweight prediction (no Redis recording)
        prediction = await shadow_prediction_service.predict_intent_only(
            user_message=request.partial_text,
            active_plan_id=request.active_plan_id,
            user_id=str(current_user.id),
        )

        return {
            "success": True,
            "data": prediction
        }

    except Exception as e:
        logger.error(f"Intent prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intent prediction failed: {str(e)}"
        )


@router.get("/intent/types", response_model=dict[str, Any])
async def list_intent_types():
    """
    获取支持的意图类型列表

    Returns:
        - intent_types: 意图类型列表及其说明
    """
    intent_type_descriptions = {
        "task_management": "任务管理（创建、修改、删除任务）",
        "knowledge_query": "知识查询（概念解释、原理说明）",
        "time_planning": "时间规划（制定计划、安排时间）",
        "social": "社交互动（好友、群组相关）",
        "learning": "学习内容（学习新知识、练习）",
        "reflection": "复习反思（回顾总结）",
        "tool_call": "工具调用（需要调用特定工具）",
        "unknown": "未知意图"
    }

    return {
        "success": True,
        "data": {
            "intent_types": [
                {
                    "value": key,
                    "description": intent_type_descriptions.get(key, "")
                }
                for key in intent_type_descriptions
            ]
        }
    }
