"""
Knowledge Galaxy API
知识星图相关接口
"""
from datetime import datetime, time
from typing import Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user_id, get_db
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.subject import Subject
from app.models.task import Task, TaskStatus
from app.schemas.galaxy import GalaxyGraphResponse, GalaxyNodeDTO, SectorEnum

router = APIRouter()


@router.get("/graph", response_model=GalaxyGraphResponse)
async def get_galaxy_graph(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    获取当前用户的完整星图数据
    包含节点基础信息和用户的掌握状态
    """
    # 1. 获取所有学科信息 (用于映射 Sector 和 Color)
    subjects_result = await db.execute(select(Subject))
    subjects = subjects_result.scalars().all()
    subject_map = {
        s.id: {"sector": s.sector_code, "color": s.hex_color} 
        for s in subjects
    }

    # 2. 获取所有知识节点
    nodes_result = await db.execute(select(KnowledgeNode))
    nodes = nodes_result.scalars().all()

    # 3. 获取用户节点状态
    user_status_result = await db.execute(
        select(UserNodeStatus).where(UserNodeStatus.user_id == user_id)
    )
    user_statuses = {
        s.node_id: s for s in user_status_result.scalars().all()
    }

    # 4. 组装节点数据
    node_dtos = []
    for node in nodes:
        subj_info = subject_map.get(node.subject_id, {"sector": "VOID", "color": "#808080"})
        status_info = user_statuses.get(node.id)

        # 默认状态
        is_unlocked = False
        mastery_score = 0

        if status_info:
            is_unlocked = status_info.is_unlocked
            mastery_score = status_info.mastery_score
        
        # 转换 SectorEnum
        try:
            sector_enum = SectorEnum(subj_info["sector"])
        except ValueError:
            sector_enum = SectorEnum.VOID

        node_dtos.append(
            GalaxyNodeDTO(
                id=node.id,
                parent_id=node.parent_id,
                name=node.name,
                importance=node.importance_level,
                sector=sector_enum,
                base_color=subj_info["color"],
                is_unlocked=is_unlocked,
                mastery_score=mastery_score,
            )
        )

    # 5. 计算 user_flame_intensity (基于今日专注时长)
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    
    # 统计今日完成任务的 actual_minutes 总和
    focus_stats_query = select(func.sum(Task.actual_minutes)).where(
        and_(
            Task.user_id == user_id,
            Task.status == TaskStatus.COMPLETED,
            Task.completed_at >= today_start
        )
    )
    focus_stats_result = await db.execute(focus_stats_query)
    total_minutes = focus_stats_result.scalar() or 0
    
    # 强度映射: 假设 120 分钟 (2小时) 达到最大强度 1.0
    intensity = min(float(total_minutes) / 120.0, 1.0)

    return GalaxyGraphResponse(
        nodes=node_dtos,
        user_flame_intensity=intensity
    )


@router.post("/node/{node_id}/spark")
async def spark_node(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    (Debug/MVP) 手动点亮某个节点
    """
    # 检查节点是否存在
    node = await db.get(KnowledgeNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # 获取或创建状态
    result = await db.execute(
        select(UserNodeStatus).where(
            and_(UserNodeStatus.user_id == user_id, UserNodeStatus.node_id == node_id)
        )
    )
    status_obj = result.scalar_one_or_none()

    if not status_obj:
        status_obj = UserNodeStatus(
            user_id=user_id,
            node_id=node_id,
            is_unlocked=True,
            mastery_score=10, # 初始点亮给10分
            total_minutes=0
        )
        db.add(status_obj)
    else:
        status_obj.is_unlocked = True
        status_obj.mastery_score = min(status_obj.mastery_score + 10, 100)
        status_obj.last_interacted_at = datetime.utcnow()
    
    await db.commit()
    return {"status": "sparked", "mastery_score": status_obj.mastery_score}
