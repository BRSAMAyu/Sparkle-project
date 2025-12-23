from typing import List, Any
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import DailyMetricResponse, UserAnalyticsSummary

router = APIRouter()

@router.get("/daily", response_model=List[DailyMetricResponse])
async def get_daily_metrics(
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get daily metrics for the current user within a date range.
    """
    service = AnalyticsService(db)
    
    # Check if we need to calculate today's metrics on the fly
    today = date.today()
    if end_date >= today:
        await service.calculate_daily_metrics(current_user.id, today)
        
    # Query metrics
    # Note: We should probably move this query to the service as well, but for now it's simple enough
    from sqlalchemy import select, and_
    from app.models.analytics import UserDailyMetric
    
    query = select(UserDailyMetric).where(
        and_(
            UserDailyMetric.user_id == current_user.id,
            UserDailyMetric.date >= start_date,
            UserDailyMetric.date <= end_date
        )
    ).order_by(UserDailyMetric.date)
    
    result = await db.execute(query)
    metrics = result.scalars().all()
    return metrics

@router.get("/summary", response_model=UserAnalyticsSummary)
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get a text summary of user analytics (useful for debugging LLM context).
    """
    service = AnalyticsService(db)
    # Ensure today's stats are up to date
    await service.calculate_daily_metrics(current_user.id, date.today())
    
    summary = await service.get_user_profile_summary(current_user.id)
    return UserAnalyticsSummary(summary=summary)
