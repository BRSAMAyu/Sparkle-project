"""
Predictive Analytics API - 预测分析接口

Endpoints:
- GET /predictive/engagement - 用户活跃度预测
- GET /predictive/difficulty/{topic_id} - 主题难度预测
- GET /predictive/optimal-time - 最佳学习时间推荐
- GET /predictive/dropout-risk - 流失风险评估
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from loguru import logger

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.services.predictive_service import PredictiveService

router = APIRouter()


@router.get("/engagement")
async def get_engagement_forecast(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户活跃度预测

    Returns:
        - next_active_time: 预测下次活跃时间
        - confidence: 预测置信度 (0-1)
        - dropout_risk: 流失风险 (low/medium/high)
        - typical_weekdays: 典型活跃日
        - typical_hours: 典型活跃时段
    """
    try:
        service = PredictiveService(db)
        forecast = await service.predict_engagement(current_user.id)

        return {
            "status": "success",
            "data": {
                "next_active_time": forecast.next_active_time.isoformat() if forecast.next_active_time else None,
                "confidence": forecast.confidence,
                "dropout_risk": forecast.dropout_risk,
                "typical_weekdays": forecast.typical_weekdays,
                "typical_hours": forecast.typical_hours,
                "prediction_factors": forecast.prediction_factors,
            }
        }

    except Exception as e:
        logger.error(f"Engagement prediction failed for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/difficulty/{topic_id}")
async def get_difficulty_prediction(
    topic_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取主题难度预测

    Args:
        topic_id: 主题ID

    Returns:
        - difficulty_score: 难度分数 (0-1)
        - estimated_time_hours: 预估学习时长（小时）
        - prerequisites_ready: 前置知识是否就绪
        - missing_prerequisites: 缺失的前置知识
        - difficulty_factors: 难度因素分析
    """
    try:
        service = PredictiveService(db)
        prediction = await service.predict_difficulty(current_user.id, topic_id)

        return {
            "status": "success",
            "data": {
                "difficulty_score": prediction.difficulty_score,
                "estimated_time_hours": prediction.estimated_time_hours,
                "prerequisites_ready": prediction.prerequisites_ready,
                "missing_prerequisites": [
                    {
                        "node_id": str(node_id),
                        "current_mastery": mastery
                    }
                    for node_id, mastery in prediction.missing_prerequisites.items()
                ],
                "difficulty_factors": prediction.difficulty_factors,
            }
        }

    except Exception as e:
        logger.error(f"Difficulty prediction failed for topic {topic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimal-time")
async def get_optimal_time_recommendation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取最佳学习时间推荐

    Returns:
        - best_hours: 最佳学习时段（0-23小时）
        - best_weekdays: 最佳学习日（0=周一, 6=周日）
        - performance_by_hour: 按小时的表现统计
        - performance_by_weekday: 按星期的表现统计
    """
    try:
        service = PredictiveService(db)
        recommendation = await service.recommend_optimal_time(current_user.id)

        return {
            "status": "success",
            "data": {
                "best_hours": recommendation["best_hours"],
                "best_weekdays": recommendation["best_weekdays"],
                "performance_by_hour": recommendation["performance_by_hour"],
                "performance_by_weekday": recommendation["performance_by_weekday"],
            }
        }

    except Exception as e:
        logger.error(f"Optimal time recommendation failed for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dropout-risk")
async def get_dropout_risk_assessment(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取流失风险评估

    Returns:
        - risk_score: 风险分数 (0-100)
        - risk_level: 风险等级 (low/medium/high)
        - intervention_suggestions: 干预建议
        - risk_factors: 风险因素分析
    """
    try:
        service = PredictiveService(db)
        assessment = await service.detect_dropout_risk(current_user.id)

        return {
            "status": "success",
            "data": {
                "risk_score": assessment["risk_score"],
                "risk_level": assessment["risk_level"],
                "intervention_suggestions": assessment["intervention_suggestions"],
                "risk_factors": assessment["risk_factors"],
            }
        }

    except Exception as e:
        logger.error(f"Dropout risk assessment failed for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_predictive_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取预测分析仪表板（综合数据）

    Returns:
        - engagement_forecast: 活跃度预测
        - dropout_risk: 流失风险
        - optimal_time: 最佳学习时间
        - upcoming_topics: 即将学习的主题难度预测
    """
    try:
        service = PredictiveService(db)

        # 获取各项预测
        engagement = await service.predict_engagement(current_user.id)
        dropout = await service.detect_dropout_risk(current_user.id)
        optimal = await service.recommend_optimal_time(current_user.id)

        return {
            "status": "success",
            "data": {
                "engagement_forecast": {
                    "next_active_time": engagement.next_active_time.isoformat() if engagement.next_active_time else None,
                    "confidence": engagement.confidence,
                    "dropout_risk": engagement.dropout_risk,
                },
                "dropout_risk": {
                    "risk_score": dropout["risk_score"],
                    "risk_level": dropout["risk_level"],
                    "intervention_suggestions": dropout["intervention_suggestions"][:3],  # Top 3
                },
                "optimal_time": {
                    "best_hours": optimal["best_hours"],
                    "best_weekdays": optimal["best_weekdays"],
                },
                "generated_at": service._get_current_time().isoformat(),
            }
        }

    except Exception as e:
        logger.error(f"Predictive dashboard generation failed for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
