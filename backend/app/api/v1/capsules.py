"""
Curiosity Capsules API

增强版API - 支持胶囊生成、反馈、收藏、分享等功能
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.core.celery_app import get_celery_queue_status
from app.db.session import get_db
from app.models.user import User
from app.services.capsule_favorite_service import capsule_favorite_service
from app.services.capsule_feedback_service import capsule_feedback_service
from app.services.capsule_generation_service import capsule_generation_service
from app.services.capsule_share_service import capsule_share_service
from app.services.curiosity_capsule_service import curiosity_capsule_service
from app.services.glm_batch_service import glm_batch_service

router = APIRouter()


def get_celery_status() -> dict:
    """Backward-compatible Celery health probe for capsule batch generation."""
    return get_celery_queue_status(settings.GLM_BATCH_QUEUE)


# =============================================================================
# Schema 定义
# =============================================================================

class CuriosityCapsuleSchema(BaseModel):
    """胶囊基础 Schema"""
    id: UUID
    title: str
    content: str
    is_read: bool
    created_at: datetime
    related_subject: str | None = None
    # 增强字段
    depth_level: str | None = None
    generation_method: str | None = None
    quality_score: float | None = None
    feedback_count: int = 0
    share_count: int = 0
    personalization_context: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class CapsuleDetailSchema(CuriosityCapsuleSchema):
    """胶囊详情 Schema"""
    source_context: dict | None = None
    is_favorite: bool = False  # 当前用户是否收藏


class CapsuleFeedbackCreate(BaseModel):
    """提交反馈请求"""
    rating: int | None = Field(None, ge=1, le=5, description="评分 1-5")
    helpful: bool | None = Field(None, description="是否有用")
    category: str | None = Field(None, description="反馈分类")
    comment: str | None = Field(None, max_length=500, description="评论")


class CapsuleFeedbackSchema(BaseModel):
    """反馈响应"""
    id: UUID
    capsule_id: UUID
    rating: int | None
    helpful: bool | None
    category: str | None
    comment: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CapsuleFavoriteSchema(BaseModel):
    """收藏响应"""
    id: UUID
    capsule_id: UUID
    note: str | None
    created_at: datetime
    capsule: CuriosityCapsuleSchema | None = None

    model_config = ConfigDict(from_attributes=True)


class CapsuleGenerationRequest(BaseModel):
    """批量生成请求"""
    depth_preference: float = Field(0.5, ge=0.0, le=1.0, description="深度偏好 0.0-1.0")
    curiosity_preference: float = Field(0.5, ge=0.0, le=1.0, description="好奇心偏好 0.0-1.0")
    requested_count: int | None = Field(None, ge=1, le=10, description="请求数量")


class CapsuleGenerationJobSchema(BaseModel):
    """生成任务响应"""
    id: UUID
    status: str
    generation_type: str
    depth_preference: float
    curiosity_preference: float
    requested_count: int
    actual_count: int | None
    capsule_ids: list[UUID] | None
    progress: float
    error_message: str | None
    duration_ms: int | None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class CapsuleShareRequest(BaseModel):
    """分享请求"""
    group_id: UUID | None = None
    friend_id: UUID | None = None
    message: str | None = Field(None, max_length=200, description="附加消息")


class CapsuleStatsSchema(BaseModel):
    """统计信息响应"""
    total_received: int
    total_read: int
    total_favorited: int
    total_feedback_given: int
    average_rating_given: float | None


# =============================================================================
# 原有端点（向后兼容）
# =============================================================================

@router.get("/today", response_model=list[CapsuleDetailSchema])
async def get_today_capsules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取今日未读胶囊
    如果没有胶囊，自动触发生成
    """
    capsules = await curiosity_capsule_service.get_today_capsules(current_user.id, db)

    if not capsules:
        # 尝试自动生成
        new_capsule = await curiosity_capsule_service.generate_daily_capsule(current_user.id, db)
        if new_capsule:
            capsules = [new_capsule]

    # 增强响应数据
    result = []
    for capsule in capsules:
        is_fav = await capsule_favorite_service.is_favorited(current_user.id, capsule.id, db)
        result.append(CapsuleDetailSchema(
            **capsule.__dict__,
            is_favorite=is_fav,
        ))

    return result


@router.post("/{id}/read")
async def mark_capsule_read(
    id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    标记胶囊为已读
    """
    marked = await curiosity_capsule_service.mark_as_read(current_user.id, id, db)
    if not marked:
        raise HTTPException(status_code=404, detail="Capsule not found")
    return {"success": True}


@router.post("/generate", response_model=CapsuleDetailSchema)
async def generate_capsule(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    手动触发胶囊生成（用于测试/演示）
    """
    capsule = await curiosity_capsule_service.generate_daily_capsule(current_user.id, db)
    if not capsule:
        raise HTTPException(status_code=400, detail="生成知识胶囊失败，请稍后再试")

    is_fav = await capsule_favorite_service.is_favorited(current_user.id, capsule.id, db)
    return CapsuleDetailSchema(
        **capsule.__dict__,
        is_favorite=is_fav,
    )


# =============================================================================
# 新增端点
# =============================================================================

@router.get("/favorites", response_model=list[CapsuleFavoriteSchema])
async def get_favorites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    获取收藏的胶囊列表
    """
    favorites = await curiosity_capsule_service.get_favorites(
        current_user.id, db, limit=limit, offset=offset
    )
    return favorites


@router.post("/{id}/favorite")
async def toggle_favorite(
    id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    note: str | None = Query(None, description="收藏备注"),
):
    """
    收藏/取消收藏胶囊
    """
    result = await curiosity_capsule_service.toggle_favorite(
        current_user.id, id, db, note=note
    )
    return {
        "is_favorited": result["is_favorited"],
        "favorite_id": str(result["favorite"].id) if result["favorite"] else None,
    }


@router.post("/{id}/feedback", response_model=CapsuleFeedbackSchema)
async def submit_feedback(
    id: UUID = Path(...),
    feedback_data: CapsuleFeedbackCreate = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    提交胶囊反馈
    """
    try:
        feedback = await curiosity_capsule_service.submit_feedback(
            user_id=current_user.id,
            capsule_id=id,
            db=db,
            rating=feedback_data.rating,
            helpful=feedback_data.helpful,
            category=feedback_data.category,
            comment=feedback_data.comment,
        )
        return feedback
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{id}/share")
async def share_capsule(
    id: UUID = Path(...),
    share_data: CapsuleShareRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    分享胶囊到群组或好友
    """
    try:
        if share_data.group_id:
            result = await curiosity_capsule_service.share_to_group(
                user_id=current_user.id,
                capsule_id=id,
                group_id=share_data.group_id,
                db=db,
                message=share_data.message,
            )
            return {"success": True, "message_id": str(result.id), "type": "group"}

        elif share_data.friend_id:
            result = await capsule_share_service.share_to_friend(
                user_id=current_user.id,
                capsule_id=id,
                friend_id=share_data.friend_id,
                db=db,
                message=share_data.message,
            )
            return {"success": True, "message_id": str(result.id), "type": "friend"}

        else:
            raise HTTPException(status_code=400, detail="请选择要分享给好友还是学习小组")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/generation/jobs", response_model=list[CapsuleGenerationJobSchema])
async def get_generation_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=50),
):
    """
    获取胶囊生成任务列表
    """
    jobs = await curiosity_capsule_service.get_generation_jobs(
        current_user.id, db, limit=limit
    )
    return jobs


@router.post("/generate/batch")
async def request_batch_generation(
    request: CapsuleGenerationRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    请求批量生成胶囊（异步）

    返回任务ID，可以通过 /generation/jobs 查询状态
    """
    interactive_manual_request = (request.requested_count or 1) <= 1
    celery_status = (
        {
            "status": "unhealthy",
            "queue": settings.GLM_BATCH_QUEUE,
            "queue_worker_count": 0,
            "queue_active_tasks": 0,
            "queue_reserved_tasks": 0,
            "reason": "interactive_manual_request",
        }
        if interactive_manual_request
        else get_celery_status()
    )
    dispatch = glm_batch_service.decide_capsule_dispatch(
        depth_preference=request.depth_preference,
        curiosity_preference=request.curiosity_preference,
        requested_count=request.requested_count or 1,
        generation_type="manual",
        celery_status=celery_status,
    )
    expired_jobs = await capsule_generation_service.expire_stale_jobs(
        user_id=current_user.id,
        db=db,
        older_than_seconds=300,
    )
    should_fallback_sync = interactive_manual_request or (not dispatch.should_enqueue) or expired_jobs > 0

    if should_fallback_sync:
        logger.warning(
            f"Capsule batch generation falling back to sync mode: decision={dispatch} celery_status={celery_status} expired_jobs={expired_jobs} interactive_manual_request={interactive_manual_request}"
        )
        job = await curiosity_capsule_service.generate_batch(
            user_id=current_user.id,
            db=db,
            depth_preference=request.depth_preference,
            curiosity_preference=request.curiosity_preference,
            generation_type="manual",
            requested_count=request.requested_count,
            model_key=dispatch.spillover_model_key,
            execution_mode=dispatch.execution_mode,
        )
        return {
            "success": True,
            "task_id": str(job.id),
            "job_id": str(job.id),
            "status": job.status,
            "actual_count": job.actual_count,
            "message": "胶囊已生成（同步降级）",
        }

    pending_job = None
    try:
        if settings.GLM_BATCH_ENABLED and settings.GLM_BATCH_CAPSULES_ENABLED and dispatch.should_enqueue:
            pending_job = await capsule_generation_service.create_generation_job(
                user_id=current_user.id,
                db=db,
                depth_preference=request.depth_preference,
                curiosity_preference=request.curiosity_preference,
                generation_type="manual",
                requested_count=request.requested_count or 1,
                model_used=dispatch.batch_model_key,
            )
            task = glm_batch_service.enqueue_capsule_generation(
                user_id=current_user.id,
                depth_preference=request.depth_preference,
                curiosity_preference=request.curiosity_preference,
                generation_type="manual",
                requested_count=request.requested_count or 1,
                job_id=pending_job.id,
            )
        else:
            from app.core.celery_app import celery_app

            pending_job = await capsule_generation_service.create_generation_job(
                user_id=current_user.id,
                db=db,
                depth_preference=request.depth_preference,
                curiosity_preference=request.curiosity_preference,
                generation_type="manual",
                requested_count=request.requested_count or 1,
                model_used=None,
            )
            task = celery_app.send_task(
                "generate_capsules_batch",
                args=(
                    str(current_user.id),
                    request.depth_preference,
                    request.curiosity_preference,
                    "manual",
                    request.requested_count,
                    None,
                    "online",
                    str(pending_job.id),
                ),
            )
    except Exception as exc:
        logger.warning(f"Celery batch generation failed, retrying synchronously: {exc}")
        job = await curiosity_capsule_service.generate_batch(
            user_id=current_user.id,
            db=db,
            depth_preference=request.depth_preference,
            curiosity_preference=request.curiosity_preference,
            generation_type="manual",
            requested_count=request.requested_count,
            model_key=dispatch.spillover_model_key or dispatch.batch_model_key,
            execution_mode="sync_fallback",
        )
        return {
            "success": True,
            "task_id": str(job.id),
            "job_id": str(job.id),
            "status": job.status,
            "actual_count": job.actual_count,
            "message": "胶囊已生成（同步降级）",
        }

    return {
        "success": True,
        "task_id": task.id,
        "job_id": str(pending_job.id) if pending_job else None,
        "message": "胶囊生成任务已提交，请稍后查询结果",
    }


@router.get("/stats", response_model=CapsuleStatsSchema)
async def get_capsule_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取胶囊统计信息
    """
    from sqlalchemy import func, select

    from app.models.capsule_favorite import CapsuleFavorite
    from app.models.curiosity_capsule import CuriosityCapsule

    # 总接收数
    total_result = await db.execute(
        select(func.count(CuriosityCapsule.id)).where(
            CuriosityCapsule.user_id == current_user.id
        )
    )
    total_received = total_result.scalar() or 0

    # 已读数
    read_result = await db.execute(
        select(func.count(CuriosityCapsule.id)).where(
            CuriosityCapsule.user_id == current_user.id,
            CuriosityCapsule.is_read
        )
    )
    total_read = read_result.scalar() or 0

    # 收藏数
    fav_result = await db.execute(
        select(func.count(CapsuleFavorite.id)).where(
            CapsuleFavorite.user_id == current_user.id
        )
    )
    total_favorited = fav_result.scalar() or 0

    # 反馈统计
    feedback_stats = await capsule_feedback_service.get_user_feedback_stats(
        current_user.id, db
    )

    return CapsuleStatsSchema(
        total_received=total_received,
        total_read=total_read,
        total_favorited=total_favorited,
        total_feedback_given=feedback_stats["total_feedbacks"],
        average_rating_given=feedback_stats["avg_rating"],
    )


@router.get("/{id}", response_model=CapsuleDetailSchema)
async def get_capsule_detail(
    id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取胶囊详情
    """
    from app.models.curiosity_capsule import CuriosityCapsule

    capsule = await db.get(CuriosityCapsule, id)
    if not capsule or capsule.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="没有找到这个知识胶囊")

    is_fav = await capsule_favorite_service.is_favorited(current_user.id, capsule.id, db)

    return CapsuleDetailSchema(
        **capsule.__dict__,
        is_favorite=is_fav,
    )


# =============================================================================
# 根路径端点（兼容性）- 使用 /list 避免与 /{id} 路由冲突
# =============================================================================

@router.get("/list/all", response_model=list[CuriosityCapsuleSchema])
async def list_capsules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    获取用户的胶囊列表
    """
    capsules = await curiosity_capsule_service.get_user_capsules(
        user_id=current_user.id,
        db=db,
        limit=limit,
        offset=offset
    )
    return capsules
