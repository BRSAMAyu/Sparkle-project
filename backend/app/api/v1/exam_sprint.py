from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_service
from app.models.user import User
from app.schemas.exam_sprint import (
    DiagnosticGenerateRequest,
    DiagnosticGenerateResponse,
    DiagnosticGradeRequest,
    DiagnosticGradeResponse,
    ExamSprintIntakeRequest,
    ExamSprintIntakeResponse,
)
from app.services.exam_sprint_diagnostic_service import ExamSprintDiagnosticService
from app.services.exam_sprint_intake_service import ExamSprintIntakeService

router = APIRouter()

# route-tier: authed
@router.post("/intake", response_model=ExamSprintIntakeResponse)
async def intake_exam_sprint(
    payload: ExamSprintIntakeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Collect the structured exam sprint setup and seed the first sprint plan."""
    service = ExamSprintIntakeService(db=db, redis_client=cache_service.redis)
    try:
        return await service.intake(user_id=current_user.id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

# route-tier: authed
@router.post("/diagnose/generate", response_model=DiagnosticGenerateResponse)
async def generate_exam_sprint_diagnostic(
    payload: DiagnosticGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExamSprintDiagnosticService(db)
    try:
        return await service.generate(user_id=current_user.id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

# route-tier: authed
@router.post("/diagnose/grade", response_model=DiagnosticGradeResponse)
async def grade_exam_sprint_diagnostic(
    payload: DiagnosticGradeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExamSprintDiagnosticService(db)
    try:
        return await service.grade(user_id=current_user.id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
