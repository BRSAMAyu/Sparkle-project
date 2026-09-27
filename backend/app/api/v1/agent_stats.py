"""
Agent Statistics API Endpoints

V3-FIX-330（如实化）：`agent_execution_stats` 的唯一写入口
`AgentStatsService.record_agent_execution` 在生产链路零调用（全仓无写入方），
读侧聚合永远只能产出「被冒充为测量值的结构性零」。在写侧接线之前，
所有数据端点一律如实返回 unavailable 语义（degraded=True +
data_status="unavailable" + unavailable_reason="write_side_unwired"），
不再把空表零当作统计值返回；移动端仓库层据 degraded 抛
StatisticsSourceUnavailableException（D-04），不会把零上屏。
写侧接线落地时必须同步翻转本标记并恢复真实聚合查询。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.agent_stats_service import AgentStatsService

router = APIRouter(prefix="/agent-stats", tags=["agent-stats"])

# V3-FIX-330：写侧未接线的结构事实标记。接线任务须同步移除本标记并恢复读侧真实聚合。
UNAVAILABLE_REASON_WRITE_SIDE_UNWIRED = "write_side_unwired"


def _unavailable_markers() -> dict[str, Any]:
    """返回如实不可用标记：零占位字段在 degraded=True 下不代表任何测量值。"""
    return {
        "degraded": True,
        "data_status": "unavailable",
        "unavailable_reason": UNAVAILABLE_REASON_WRITE_SIDE_UNWIRED,
    }


@router.get("/user/overview")
async def get_user_stats_overview(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(get_current_user),
):
    """
    获取用户的Agent使用统计概览（写侧接线前如实返回 unavailable）

    返回字段结构保持稳定，但 degraded=True 表明全部数值是不可用占位，
    不是测量值：写侧 record_agent_execution 未接线（V3-FIX-330）。
    """
    del current_user  # 仅作鉴权门
    return {
        "success": True,
        "data": {
            "period_days": days,
            "overall": {
                "total_executions": 0,
                "avg_duration_ms": 0,
                "total_sessions": 0,
            },
            "by_agent": [],
            "recent_executions": [],
            **_unavailable_markers(),
        },
    }


@router.get("/overview")
async def get_user_stats_overview_alias(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(get_current_user),
):
    """Compatibility alias for legacy acceptance paths."""
    return await get_user_stats_overview(days=days, current_user=current_user)


@router.get("/user/top-agents")
async def get_top_agents(
    limit: int = Query(5, ge=1, le=10, description="返回数量"),
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(get_current_user),
):
    """
    获取用户最常使用的Agent（写侧接线前如实返回 unavailable）

    degraded=True：top_agents 为不可用占位，不是测量值（V3-FIX-330）。
    """
    del current_user, limit  # limit 语义在写侧接线后随真实聚合恢复
    return {
        "success": True,
        "data": {
            "period_days": days,
            "top_agents": [],
            **_unavailable_markers(),
        },
    }


@router.get("/performance")
async def get_performance_metrics(
    agent_type: str | None = Query(None, description="Agent类型（可选）"),
    days: int = Query(7, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(get_current_user),
):
    """
    获取Agent性能指标（写侧接线前如实返回 unavailable）

    degraded=True：耗时/成功率等全部数值是不可用占位，不是测量值（V3-FIX-330）。
    """
    del current_user
    return {
        "success": True,
        "data": {
            "period_days": days,
            "agent_type": agent_type,
            "total_executions": 0,
            "avg_duration_ms": 0,
            "max_duration_ms": 0,
            "success_rate": 0,
            "failure_rate": 0,
            **_unavailable_markers(),
        },
    }


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
    if not current_user.is_superuser:
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
        raise HTTPException(status_code=500, detail="Failed to refresh stats summary") from e
