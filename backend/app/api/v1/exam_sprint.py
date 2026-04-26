from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_service
from app.models.user import User
from app.schemas.exam_sprint import (
    DiagnosticGenerateRequest,
    DiagnosticGenerateResponse,
    DiagnosticGradeRequest,
    DiagnosticGradeResponse,
    ExamSprintDashboardResponse,
    ExamSprintIntakeRequest,
    ExamSprintIntakeResponse,
    LearningPortfolioResponse,
    PostExamReviewRequest,
    PostExamReviewResponse,
    SprintCompletionCheckResponse,
    SprintSummaryResponse,
)
from app.services.exam_sprint_dashboard_service import ExamSprintDashboardService
from app.services.exam_sprint_diagnostic_service import ExamSprintDiagnosticService
from app.services.exam_sprint_intake_service import ExamSprintIntakeService
from app.services.exam_sprint_review_service import ExamSprintReviewService

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
@router.get("/dashboard", response_model=ExamSprintDashboardResponse)
async def get_exam_sprint_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExamSprintDashboardService(db)
    return await service.get_dashboard(user_id=current_user.id)


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


# route-tier: authed
@router.post("/post-exam-review", response_model=PostExamReviewResponse)
async def submit_post_exam_review(
    payload: PostExamReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExamSprintReviewService(db=db, redis_client=cache_service.redis)
    try:
        return await service.submit_post_exam_review(user_id=current_user.id, request=payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


# route-tier: authed
@router.get("/sprint-summary", response_model=SprintSummaryResponse)
async def get_exam_sprint_summary(
    plan_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExamSprintReviewService(db=db, redis_client=cache_service.redis)
    try:
        return await service.get_sprint_summary(user_id=current_user.id, plan_id=plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# route-tier: authed
@router.get("/completion", response_model=SprintCompletionCheckResponse)
async def check_exam_sprint_completion(
    plan_id: UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExamSprintReviewService(db=db, redis_client=cache_service.redis)
    try:
        return await service.check_sprint_completion(user_id=current_user.id, plan_id=plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# route-tier: authed
@router.get("/portfolio", response_model=LearningPortfolioResponse)
async def get_learning_portfolio(
    user_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of entries per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user_id is not None and user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看其他用户的学习档案")

    service = ExamSprintReviewService(db=db, redis_client=cache_service.redis)
    return await service.get_portfolio(user_id=user_id or current_user.id, page=page, page_size=page_size)
