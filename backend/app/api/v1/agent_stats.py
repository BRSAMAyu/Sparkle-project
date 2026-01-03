"""
Agent Statistics API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from loguru import logger

from app.services.agent_stats_service import AgentStatsService
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/agent-stats", tags=["agent-stats"])


@router.get("/user/overview")
async def get_user_stats_overview(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户的Agent使用统计概览

    返回：
    - 总体统计（总执行次数、平均耗时、会话数）
    - 各Agent类型统计
    - 最近活动记录
    """
    try:
        stats_service = AgentStatsService(db)
        stats = await stats_service.get_user_stats(current_user.id, days=days)
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get user stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.get("/user/top-agents")
async def get_top_agents(
    limit: int = Query(5, ge=1, le=10, description="返回数量"),
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户最常使用的Agent

    返回：
    - Agent类型
    - 使用次数
    - 平均耗时
    """
    try:
        stats_service = AgentStatsService(db)
        top_agents = await stats_service.get_most_used_agents(
            current_user.id,
            limit=limit,
            days=days
        )
        return {
            "success": True,
            "data": {
                "period_days": days,
                "top_agents": top_agents
            }
        }
    except Exception as e:
        logger.error(f"Failed to get top agents: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve top agents")


@router.get("/performance")
async def get_performance_metrics(
    agent_type: Optional[str] = Query(None, description="Agent类型（可选）"),
    days: int = Query(7, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取Agent性能指标

    包括：
    - 平均耗时
    - 中位数耗时
    - P95耗时
    - 成功率/失败率
    """
    try:
        stats_service = AgentStatsService(db)
        metrics = await stats_service.get_performance_metrics(
            user_id=current_user.id,
            agent_type=agent_type,
            days=days
        )
        return {
            "success": True,
            "data": metrics
        }
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")


@router.get("/agent-types")
async def get_available_agent_types():
    """
    获取所有可用的Agent类型

    返回所有Agent的元数据，包括：
    - 类型ID
    - 显示名称
    - 描述
    - 图标建议
    """
    agent_types = [
        {
            "id": "orchestrator",
            "name": "Orchestrator",
            "description": "主脑指挥官 - 理解意图、拆解任务、汇总结果",
            "icon": "psychology",
            "color": "#9C27B0"
        },
        {
            "id": "knowledge",
            "name": "KnowledgeAgent",
            "description": "知识检索专家 - GraphRAG检索、文档查询",
            "icon": "auto_awesome",
            "color": "#2196F3"
        },
        {
            "id": "math",
            "name": "MathAgent",
            "description": "数学专家 - 数值计算、公式推导",
            "icon": "calculate",
            "color": "#FFC107"
        },
        {
            "id": "code",
            "name": "CodeAgent",
            "description": "代码工程师 - 代码生成、调试、执行",
            "icon": "terminal",
            "color": "#4CAF50"
        },
        {
            "id": "data_analysis",
            "name": "DataAnalyst",
            "description": "数据分析专家 - 数据处理、统计、可视化",
            "icon": "analytics",
            "color": "#8B5CF6"
        },
        {
            "id": "translation",
            "name": "Translator",
            "description": "翻译专家 - 语言翻译、本地化",
            "icon": "translate",
            "color": "#06B6D4"
        },
        {
            "id": "image",
            "name": "ImageAgent",
            "description": "图像处理专家 - 图像生成、编辑、分析",
            "icon": "image",
            "color": "#EC4899"
        },
        {
            "id": "audio",
            "name": "AudioAgent",
            "description": "音频工程师 - 音频处理、语音识别、音乐",
            "icon": "audiotrack",
            "color": "#F59E0B"
        },
        {
            "id": "writing",
            "name": "WritingAgent",
            "description": "写作专家 - 内容创作、总结、编辑",
            "icon": "edit",
            "color": "#F59E0B"
        },
        {
            "id": "reasoning",
            "name": "ReasoningAgent",
            "description": "逻辑推理专家 - 复杂推理、问题解决",
            "icon": "lightbulb",
            "color": "#EAB308"
        }
    ]

    return {
        "success": True,
        "data": {
            "agent_types": agent_types,
            "total_count": len(agent_types)
        }
    }


@router.post("/refresh-summary")
async def refresh_stats_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    刷新统计汇总物化视图

    注意：此操作可能耗时较长，建议通过定时任务调用
    """
    # 仅管理员可以手动刷新
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        stats_service = AgentStatsService(db)
        await stats_service.refresh_materialized_view()
        return {
            "success": True,
            "message": "Stats summary refreshed successfully"
        }
    except Exception as e:
        logger.error(f"Failed to refresh stats summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh stats summary")
