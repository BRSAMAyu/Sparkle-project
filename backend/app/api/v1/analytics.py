import os
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.analytics.weekly_synthesis_service import WeeklySynthesisService
from app.services.llm_service import llm_service

router = APIRouter()


async def _build_weekly_report_payload(
    *,
    current_user: User,
    db: AsyncSession,
    background_tasks: BackgroundTasks | None = None,
) -> dict[str, Any]:
    service = WeeklySynthesisService(db, llm_service)
    report_data = await service.generate_report(str(current_user.id))

    filename = f"weekly_report_{current_user.id}_{report_data['week_of']}.pdf"
    output_path = os.path.join("/tmp", filename)

    if background_tasks is not None:
        background_tasks.add_task(service.generate_pdf, report_data, output_path)

    return {
        "message": "Report generation started",
        "data": report_data,
        "download_url": f"/api/v1/analytics/reports/download/{filename}",
    }

@router.post("/reports/generate", response_model=dict[str, Any])
async def generate_weekly_report(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger on-demand generation of the weekly learning report.
    Returns the JSON data immediately and schedules PDF generation.
    """
    try:
        return await _build_weekly_report_payload(
            current_user=current_user,
            db=db,
            background_tasks=background_tasks,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Report generation failed") from e


@router.get("/report", response_model=dict[str, Any])
async def get_weekly_report_alias(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compatibility alias for legacy acceptance and dashboard integrations."""
    try:
        return await _build_weekly_report_payload(
            current_user=current_user,
            db=db,
            background_tasks=background_tasks,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Report generation failed") from e

@router.get("/reports/download/{filename}")
async def download_report(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Download a generated PDF report.
    """
    # Security check: filename should contain user_id to prevent accessing others' reports
    if str(current_user.id) not in filename:
        raise HTTPException(status_code=403, detail="Access denied")

    file_path = os.path.join("/tmp", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(file_path, media_type="application/pdf", filename=filename)
