"""
错题档案 API 路由
"""

from __future__ import annotations

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
    ErrorTypeEnum,
    ReviewAction,
    ReviewStatsResponse,
    SubjectEnum,
)
from app.schemas.semantic_memory import ErrorSemanticSummary
from app.services.error_book_service import ErrorBookService

router = APIRouter(prefix="/errors", tags=["Error Book"])


async def _analyze_error_task(error_id: UUID, user_id: UUID, db_session_factory) -> None:
    """Run error analysis with a fresh DB session for background execution."""
    async with db_session_factory() as session:
        service = ErrorBookService(session)
        await service.analyze_and_link(error_id, user_id)


async def get_error_service(
    db: AsyncSession = Depends(get_db),
) -> ErrorBookService:
    return ErrorBookService(db)


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

    return error


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


@router.get("/stats", response_model=ReviewStatsResponse)
async def get_stats(
    user_id: str = Depends(get_current_user_id), service: ErrorBookService = Depends(get_error_service)
):
    """获取错题统计数据"""
    stats = await service.get_review_stats(UUID(user_id))
    return ReviewStatsResponse(**stats)


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


@router.delete("/{error_id}", status_code=204)
async def delete_error(
    error_id: UUID, user_id: str = Depends(get_current_user_id), service: ErrorBookService = Depends(get_error_service)
):
    """删除错题（软删除）"""
    success = await service.delete_error(error_id, UUID(user_id))
    if not success:
        raise HTTPException(status_code=404, detail="没有找到这个错题，可能已经删除了")


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
        raise HTTPException(status_code=404, detail=str(e))


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
