"""
知识衰减时光机 API - 必杀技 B

预测未来的知识遗忘状态，模拟复习干预效果
"""

from fastapi import APIRouter, Depends, Query
from typing import Dict, Any, List
from uuid import UUID
from pydantic import BaseModel
from loguru import logger

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.decay_service import DecayService
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/decay", tags=["decay"])


class DecayProjectionResponse(BaseModel):
    """时光机预测响应"""
    days_ahead: int
    total_nodes: int
    projections: Dict[str, Dict[str, Any]]

    # 统计汇总
    summary: Dict[str, int]  # healthy_count, dimming_count, critical_count


class InterventionSimulationRequest(BaseModel):
    """干预模拟请求"""
    node_ids: List[str]  # 要复习的节点ID
    days_ahead: int = 30
    review_boost: float = 30.0  # 复习提升的掌握度


@router.get("/timemachine/future", response_model=DecayProjectionResponse)
async def project_future_decay(
    days_ahead: int = Query(30, ge=1, le=90, description="预测天数（1-90天）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    时光机：查看未来知识遗忘状态

    用途：
    - 前端滑块交互：拖动查看未来 N 天的知识状态
    - Galaxy 可视化：节点随时间逐渐变灰/消失

    返回每个节点的：
    - 当前掌握度 vs 未来掌握度
    - 颜色、透明度（用于渲染）
    - 状态标签（healthy/dimming/critical）
    """
    logger.info(f"用户 {current_user.id} 查询未来 {days_ahead} 天的衰减预测")

    decay_service = DecayService(db)

    # 获取预测
    projections = await decay_service.project_decay_future(
        user_id=current_user.id,
        days_ahead=days_ahead
    )

    # 统计各状态节点数量
    summary = {
        "healthy_count": 0,
        "stable_count": 0,
        "dimming_count": 0,
        "critical_count": 0
    }

    for projection in projections.values():
        status = projection["status"]
        if status == "healthy":
            summary["healthy_count"] += 1
        elif status == "stable":
            summary["stable_count"] += 1
        elif status == "dimming":
            summary["dimming_count"] += 1
        elif status == "critical":
            summary["critical_count"] += 1

    return DecayProjectionResponse(
        days_ahead=days_ahead,
        total_nodes=len(projections),
        projections=projections,
        summary=summary
    )


@router.post("/timemachine/simulate", response_model=DecayProjectionResponse)
async def simulate_review_intervention(
    request: InterventionSimulationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    时光机干预模拟：如果现在复习这些节点，未来会怎样？

    用途：
    - 前端"What If"按钮：点击后重新计算
    - 显示复习的即时效果
    - 帮助用户决策优先复习哪些节点

    流程：
    1. 假设现在复习指定节点（掌握度+30）
    2. 预测未来 N 天的衰减
    3. 返回新的预测状态（被复习的节点标记为绿色）
    """
    logger.info(
        f"用户 {current_user.id} 模拟复习 {len(request.node_ids)} 个节点，"
        f"预测 {request.days_ahead} 天"
    )

    decay_service = DecayService(db)

    # 转换为 UUID
    node_uuids = [UUID(nid) for nid in request.node_ids]

    # 模拟干预
    projections = await decay_service.simulate_intervention(
        user_id=current_user.id,
        node_ids=node_uuids,
        days_ahead=request.days_ahead,
        review_boost=request.review_boost
    )

    # 统计
    summary = {
        "healthy_count": 0,
        "stable_count": 0,
        "dimming_count": 0,
        "critical_count": 0,
        "intervened_count": len(request.node_ids)
    }

    for projection in projections.values():
        status = projection["status"]
        if status == "healthy":
            summary["healthy_count"] += 1
        elif status == "stable":
            summary["stable_count"] += 1
        elif status == "dimming":
            summary["dimming_count"] += 1
        elif status == "critical":
            summary["critical_count"] += 1

    return DecayProjectionResponse(
        days_ahead=request.days_ahead,
        total_nodes=len(projections),
        projections=projections,
        summary=summary
    )


@router.get("/timemachine/comparison")
async def compare_scenarios(
    days_ahead: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    对比场景：不复习 vs 全部复习

    用途：演示时光机的威力
    返回两种场景的对比数据
    """
    decay_service = DecayService(db)

    # 场景1：不复习
    no_review = await decay_service.project_decay_future(
        user_id=current_user.id,
        days_ahead=days_ahead
    )

    # 场景2：全部复习（获取所有节点ID）
    all_node_ids = [UUID(nid) for nid in no_review.keys()]

    with_review = await decay_service.simulate_intervention(
        user_id=current_user.id,
        node_ids=all_node_ids,
        days_ahead=days_ahead,
        review_boost=30.0
    )

    # 计算差异
    def calculate_stats(projections):
        total_mastery = sum(p["future_mastery"] for p in projections.values())
        avg_mastery = total_mastery / len(projections) if projections else 0
        critical_count = sum(1 for p in projections.values() if p["status"] == "critical")
        return {
            "avg_mastery": round(avg_mastery, 2),
            "total_nodes": len(projections),
            "critical_count": critical_count
        }

    return {
        "days_ahead": days_ahead,
        "scenario_no_review": calculate_stats(no_review),
        "scenario_with_review": calculate_stats(with_review),
        "improvement": {
            "mastery_gain": round(
                calculate_stats(with_review)["avg_mastery"] - calculate_stats(no_review)["avg_mastery"],
                2
            ),
            "nodes_saved": calculate_stats(no_review)["critical_count"] - calculate_stats(with_review)["critical_count"]
        }
    }


@router.get("/stats")
async def get_decay_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户当前的衰减统计

    返回：需要复习的节点数、暗淡节点数、坍缩风险节点数
    """
    decay_service = DecayService(db)
    stats = await decay_service.get_decay_stats(user_id=current_user.id)

    return {
        "user_id": str(current_user.id),
        "stats": stats
    }
