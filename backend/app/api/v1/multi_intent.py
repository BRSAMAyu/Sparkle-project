"""
多意图识别 API Endpoints
Multi-Intent Recognition API

提供意图解析和执行接口
"""
from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.intent import (
    IntentParseRequest,
    IntentExecuteRequest,
    IntentExecuteResponse,
    IntentAnalysisPreview,
    MultiIntentResult
)
from app.services.multi_intent_service import MultiIntentService

router = APIRouter()


@router.post("/parse", response_model=Dict[str, Any])
async def parse_intents(
    request: IntentParseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    解析用户输入中的多个意图

    分析用户消息，识别其中包含的所有意图及其关系。

    Returns:
        - is_multi_intent: 是否为多意图
        - intents: 意图列表
        - execution_order: 执行顺序
        - dependencies: 依赖关系
        - estimated_total_time: 预计总时间
    """
    try:
        service = MultiIntentService(db)

        # 如果请求中没有 user_id，使用当前用户
        if not request.user_id:
            request.user_id = current_user.id

        result = await service.parse_intents(request)

        return {
            "success": True,
            "data": result.model_dump()
        }

    except Exception as e:
        logger.error(f"Intent parsing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intent parsing failed: {str(e)}"
        )


@router.post("/preview", response_model=Dict[str, Any])
async def create_intent_preview(
    request: IntentParseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建意图分析预览

    生成用户友好的意图分析预览，用于手动确认模式。

    Returns:
        - original_message: 原始消息
        - detected_intents: 检测到的意图
        - execution_plan: 执行计划描述
        - estimated_time: 预计时间
    """
    try:
        service = MultiIntentService(db)

        if not request.user_id:
            request.user_id = current_user.id

        preview = await service.create_preview(request)

        return {
            "success": True,
            "data": preview.model_dump()
        }

    except Exception as e:
        logger.error(f"Intent preview error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intent preview failed: {str(e)}"
        )


@router.post("/execute", response_model=Dict[str, Any])
async def execute_intents(
    request: IntentExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    执行多个意图

    根据解析结果依次或并行执行多个意图。

    Args:
        - parse_result: 解析后的意图结果
        - confirmed: 用户是否确认执行
        - user_id: 用户ID

    Returns:
        - success: 是否全部成功
        - results: 各意图执行结果
        - errors: 错误信息列表
        - total_time: 总执行时间
    """
    try:
        # 验证用户权限
        if request.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot execute intents for another user"
            )

        service = MultiIntentService(db)
        result = await service.execute_intents(request)

        return {
            "success": result.success,
            "data": result.model_dump()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Intent execution error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intent execution failed: {str(e)}"
        )


@router.post("/analyze-and-execute", response_model=Dict[str, Any])
async def analyze_and_execute(
    message: str,
    context: Optional[Dict[str, Any]] = None,
    auto_execute: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    一键分析并执行意图

    自动解析用户消息，如果是多意图则返回预览，
    如果是单意图或 auto_execute=True 则直接执行。

    Args:
        - message: 用户消息
        - context: 上下文信息
        - auto_execute: 是否自动执行（无需确认）

    Returns:
        - is_multi_intent: 是否为多意图
        - preview: 意图预览（多意图时）
        - execution_result: 执行结果（单意图或自动执行时）
    """
    try:
        service = MultiIntentService(db)

        # 解析意图
        parse_request = IntentParseRequest(
            message=message,
            context=context,
            user_id=current_user.id
        )
        parse_result = await service.parse_intents(parse_request)

        # 单意图或自动执行：直接执行
        if not parse_result.is_multi_intent or auto_execute:
            execute_request = IntentExecuteRequest(
                parse_result=parse_result,
                confirmed=True,
                user_id=current_user.id
            )
            execution_result = await service.execute_intents(execute_request)

            return {
                "success": True,
                "is_multi_intent": parse_result.is_multi_intent,
                "auto_executed": True,
                "execution_result": execution_result.model_dump()
            }

        # 多意图且不自动执行：返回预览
        preview = await service.create_preview(parse_request)

        return {
            "success": True,
            "is_multi_intent": True,
            "auto_executed": False,
            "preview": preview.model_dump(),
            "needs_confirmation": True
        }

    except Exception as e:
        logger.error(f"Analyze and execute error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Operation failed: {str(e)}"
        )


@router.get("/intent-types", response_model=Dict[str, Any])
async def list_intent_types():
    """
    获取支持的意图类型列表

    Returns:
        - intent_types: 意图类型列表及其说明
    """
    from app.schemas.intent import IntentType

    intent_type_descriptions = {
        IntentType.TASK_MANAGEMENT: "任务管理（创建、修改、删除任务）",
        IntentType.KNOWLEDGE_QUERY: "知识查询（概念解释、原理说明）",
        IntentType.TIME_PLANNING: "时间规划（制定计划、安排时间）",
        IntentType.SOCIAL: "社交互动（好友、群组相关）",
        IntentType.LEARNING: "学习内容（学习新知识、练习）",
        IntentType.REFLECTION: "复习反思（回顾总结）",
        IntentType.TOOL_CALL: "工具调用（需要调用特定工具）",
        IntentType.UNKNOWN: "未知意图"
    }

    return {
        "success": True,
        "data": {
            "intent_types": [
                {
                    "value": it.value,
                    "description": intent_type_descriptions.get(it, "")
                }
                for it in IntentType
            ]
        }
    }
