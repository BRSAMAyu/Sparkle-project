from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.services.report.learning_report_agent import LearningReportAgent

router = APIRouter(prefix="/learning-reports", tags=["learning-reports"])


class LearningReportRequest(BaseModel):
    section_limit: int = Field(default=5, ge=2, le=5)
    trigger_source: str = Field(default="api", min_length=1)


@router.post("/generate")
async def generate_learning_report(
    request: LearningReportRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    agent = LearningReportAgent(db)
    return await agent.generate_report(
        UUID(user_id),
        section_limit=request.section_limit,
        trigger_source=request.trigger_source,
    )
