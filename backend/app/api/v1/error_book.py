"""
错题档案 API 路由
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.db.session import AsyncSessionLocal
from app.schemas.error_book import (
    ErrorQueryParams,
    ErrorRecordCreate,
    ErrorRecordListResponse,
    ErrorRecordResponse,
    ErrorRecordUpdate,
    ErrorReviewCardsResponse,
    ErrorTypeEnum,
    RemediablePattern,
    ReviewAction,
    ReviewStatsResponse,
    SubjectEnum,
    TaskTemplate,
)
from app.schemas.semantic_memory import ErrorSemanticSummary
from app.schemas.task import TaskDetail
from app.services.error_book_service import ErrorBookService
from app.services.error_pattern_template_service import ErrorPatternTemplateService

router = APIRouter(prefix="/errors", tags=["Error Book"])
error_book_router = APIRouter(prefix="/error-book", tags=["Error Book"])


async def _analyze_error_task(error_id: UUID, user_id: UUID, db_session_factory) -> None:
    """Run error analysis with a fresh DB session for background execution."""
    async with db_session_factory() as session:
        service = ErrorBookService(session)
        await service.analyze_and_link(error_id, user_id)


async def get_error_service(
    db: AsyncSession = Depends(get_db),
) -> ErrorBookService:
    return ErrorBookService(db)


async def get_error_pattern_template_service(
    db: AsyncSession = Depends(get_db),
) -> ErrorPatternTemplateService:
    return ErrorPatternTemplateService(db)


async def _ocr_and_update_error_task(error_id: UUID, image_url: str) -> None:
    """Fire-and-forget OCR: extract text from image and update the error record."""
    _log = logging.getLogger(__name__)
    try:
        from app.services.ocr_service import ocr_service
        from app.db.session import AsyncSessionLocal

        ocr_text = await ocr_service.ocr_for_math(image_url)
        if not ocr_text or not ocr_text.strip():
            _log.info("OCR returned empty for error %s, skipping update", error_id)
            return

        async with AsyncSessionLocal() as session:
            from sqlalchemy import select, update
            from app.models.error_book import ErrorRecord

            stmt = (
                update(ErrorRecord)
                .where(ErrorRecord.id == error_id)
                .values(question_text=ocr_text.strip())
            )
            await session.execute(stmt)
            await session.commit()
            _log.info("OCR text saved for error %s (%d chars)", error_id, len(ocr_text))
    except Exception:
        _log.warning("OCR fire-and-forget failed for error %s", error_id, exc_info=True)


# route-tier: authed
@router.post("", response_model=ErrorRecordResponse, status_code=201)
async def create_error(
    data: ErrorRecordCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    service: ErrorBookService = Depends(get_error_service),
):
    """
    创建错题
    """
    error = await service.create_error(UUID(user_id), data)

    background_tasks.add_task(_analyze_error_task, error.id, UUID(user_id), AsyncSessionLocal)

    # Fire-and-forget OCR when image present but no question text
    if error.question_image_url and not error.question_text:
        try:
            asyncio.create_task(_ocr_and_update_error_task(error.id, error.question_image_url))
        except Exception:
            logging.getLogger(__name__).warning(
                "Failed to schedule OCR for error %s", error.id, exc_info=True
            )

    return error


# route-tier: authed
@router.get("", response_model=ErrorRecordListResponse)
async def list_errors(
    subject: SubjectEnum | None = Query(None, description="按科目筛选"),
    chapter: str | None = Query(None, description="按章节筛选"),
    node_id: str | None = Query(None, description="按知识节点筛选"),
    error_type: ErrorTypeEnum | None = Query(None, description="按错因类型筛选"),
    mastery_min: float | None = Query(None, ge=0, le=1, description="掌握度下限"),
    mastery_max: float | None = Query(None, ge=0, le=1, description="掌握度上限"),
    need_review: bool | None = Query(None, description="只看需要复习的"),
    keyword: str | None = Query(None, description="题目关键词搜索"),
    cognitive_dimension: str | None = Query(None, description="按认知维度筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    service: ErrorBookService = Depends(get_error_service),
):
    """
    获取错题列表
    """
    params = ErrorQueryParams(
        subject=subject,
        chapter=chapter,
        node_id=node_id,
        error_type=error_type,
        mastery_min=mastery_min,
        mastery_max=mastery_max,
        need_review=need_review,
        keyword=keyword,
        cognitive_dimension=cognitive_dimension,
        page=page,
        page_size=page_size,
    )

    items, total = await service.list_errors(UUID(user_id), params)

    return ErrorRecordListResponse(
        items=items, total=total, page=page, page_size=page_size, has_next=(page * page_size) < total
    )


# route-tier: authed
@router.get("/stats", response_model=ReviewStatsResponse)
async def get_stats(
    user_id: str = Depends(get_current_user_id), service: ErrorBookService = Depends(get_error_service)
):
    """获取错题统计数据"""
    stats = await service.get_review_stats(UUID(user_id))
    return ReviewStatsResponse(**stats)


# route-tier: authed
@router.get("/today-review", response_model=ErrorRecordListResponse)
async def get_today_review_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    service: ErrorBookService = Depends(get_error_service),
):
    """获取今日待复习的错题列表"""
    params = ErrorQueryParams(need_review=True, page=page, page_size=page_size)

    items, total = await service.list_errors(UUID(user_id), params)

    return ErrorRecordListResponse(
        items=items, total=total, page=page, page_size=page_size, has_next=(page * page_size) < total
    )


# route-tier: authed
@router.get("/review-cards", response_model=ErrorReviewCardsResponse)
async def get_review_cards(
    limit: int = Query(8, ge=1, le=20),
    lookback_days: int = Query(90, ge=7, le=365),
    user_id: str = Depends(get_current_user_id),
    service: ErrorBookService = Depends(get_error_service),
):
    """Get clustered, actionable review cards built from recent real mistakes."""
    return await service.get_review_cards(UUID(user_id), limit=limit, lookback_days=lookback_days)


# route-tier: authed
@router.get("/remediable-patterns", response_model=list[RemediablePattern])
@error_book_router.get("/remediable-patterns", response_model=list[RemediablePattern])
async def list_remediable_patterns(
    limit: int = Query(3, ge=1, le=20),
    lookback_days: int = Query(14, ge=1, le=90),
    user_id: str = Depends(get_current_user_id),
    service: ErrorPatternTemplateService = Depends(get_error_pattern_template_service),
):
    """List repeated ErrorBook patterns that can become remediation tasks."""
    return await service.identify_remediable_patterns(UUID(user_id), lookback_days=lookback_days, limit=limit)


# route-tier: authed
@router.post("/patterns/{pattern_id}/generate-template", response_model=TaskTemplate)
@error_book_router.post("/patterns/{pattern_id}/generate-template", response_model=TaskTemplate)
async def generate_remedial_task_template(
    pattern_id: str,
    user_id: str = Depends(get_current_user_id),
    service: ErrorPatternTemplateService = Depends(get_error_pattern_template_service),
):
    """Preview the task template for a remediable error pattern."""
    patterns = await service.identify_remediable_patterns(UUID(user_id), min_confidence=0.0, limit=50)
    pattern = next((item for item in patterns if item.id == pattern_id), None)
    if pattern is None:
        raise HTTPException(status_code=404, detail="没有找到这个可补救错因模式")
    return service.generate_task_template(pattern)


# route-tier: authed
@router.post("/patterns/{pattern_id}/accept-template", response_model=TaskDetail, status_code=201)
@error_book_router.post("/patterns/{pattern_id}/accept-template", response_model=TaskDetail, status_code=201)
async def accept_remedial_task_template(
    pattern_id: str,
    user_id: str = Depends(get_current_user_id),
    service: ErrorPatternTemplateService = Depends(get_error_pattern_template_service),
):
    """Accept a remediable pattern template and create a real task."""
    try:
        return await service.accept_template(UUID(user_id), pattern_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# route-tier: authed
@router.get("/{error_id}", response_model=ErrorRecordResponse)
async def get_error(
    error_id: UUID, user_id: str = Depends(get_current_user_id), service: ErrorBookService = Depends(get_error_service)
):
    """获取错题详情（含 AI 分析和关联知识点）"""
    error = await service.get_error(error_id, UUID(user_id))
    if not error:
        raise HTTPException(status_code=404, detail="没有找到这个错题，可能已经删除了")

    # knowledge_links is populated by the service on the object
    return error


# route-tier: authed
@router.patch("/{error_id}", response_model=ErrorRecordResponse)
async def update_error(
    error_id: UUID,
    data: ErrorRecordUpdate,
    user_id: str = Depends(get_current_user_id),
    service: ErrorBookService = Depends(get_error_service),
):
    """更新错题信息"""
    error = await service.update_error(error_id, UUID(user_id), data)
    if not error:
        raise HTTPException(status_code=404, detail="没有找到这个错题，可能已经删除了")
    return error


# route-tier: authed
@router.delete("/{error_id}", status_code=204)
async def delete_error(
    error_id: UUID, user_id: str = Depends(get_current_user_id), service: ErrorBookService = Depends(get_error_service)
):
    """删除错题（软删除）"""
    success = await service.delete_error(error_id, UUID(user_id))
    if not success:
        raise HTTPException(status_code=404, detail="没有找到这个错题，可能已经删除了")


# route-tier: authed
@router.post("/{error_id}/analyze", response_model=dict)
async def re_analyze_error(
    error_id: UUID,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    service: ErrorBookService = Depends(get_error_service),
):
    """
    重新分析错题
    """
    error = await service.get_error(error_id, UUID(user_id))
    if not error:
        raise HTTPException(status_code=404, detail="没有找到这个错题，可能已经删除了")

    background_tasks.add_task(_analyze_error_task, error_id, UUID(user_id), AsyncSessionLocal)

    return {"message": "分析任务已提交，请稍后刷新查看结果~"}


# route-tier: authed
@router.post("/{error_id}/review", response_model=ErrorRecordResponse)
async def submit_review(
    error_id: UUID,
    data: ReviewAction,
    user_id: str = Depends(get_current_user_id),
    service: ErrorBookService = Depends(get_error_service),
):
    """
    提交复习记录
    """
    try:
        error = await service.submit_review(UUID(user_id), error_id, data)
        return error
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# route-tier: authed
@router.get("/{error_id}/semantic", response_model=ErrorSemanticSummary)
async def get_error_semantic_summary(
    error_id: UUID,
    user_id: str = Depends(get_current_user_id),
    service: ErrorBookService = Depends(get_error_service),
):
    summary = await service.get_semantic_summary(error_id, UUID(user_id))
    if not summary:
        raise HTTPException(status_code=404, detail="没有找到这个错题，可能已经删除了")
    return summary
