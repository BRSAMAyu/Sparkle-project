from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.north_star_metrics import NorthStarTrendResponse
from app.services.north_star_metrics_service import NorthStarMetricsService

# V3-FIX-331： WeeklySynthesisService 的 mock 周报残轨（POST /reports/generate、
# GET /report、GET /reports/download/{filename} 及 app/templates/weekly_report.html）
# 已删除——其 ai_insight/ai_suggestion 为硬编码模板冒充模型产出。真实周报由
# LearningReportAgent（/learning-reports/generate）与 WeeklyLearningReportService
# （celery beat）两轨覆盖。
router = APIRouter()


# route-tier: internal
@router.get("/north-star/trends", response_model=NorthStarTrendResponse)
async def get_north_star_trends(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return exam pass and 7-day goal completion trends for the current user."""
    return await NorthStarMetricsService(db).get_trends(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        days=days,
    )
