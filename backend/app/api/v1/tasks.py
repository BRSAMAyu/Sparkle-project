"""
Tasks API Endpoints
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Path, Header, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from loguru import logger

from app.db.session import get_db
from app.api.deps import get_current_user
from app.core.cache import cache_service
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskType
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskDetail, TaskCompleteRequest,
    TaskStart, TaskAbandon, TaskSummary, TaskSuggestionRequest, TaskSuggestionResponse,
    TaskRecommendationResponse
)
from app.schemas.task_feedback import TaskFeedbackCreate, TaskFeedbackResponse, TaskFeedbackStats
from app.services.task_guide_service import task_guide_service
from app.services.task_service import TaskService
from app.services.feedback_service import feedback_service
from app.services.intelligent_task_service import IntelligentTaskService

from app.core.exceptions import NotFoundError, AuthorizationError

router = APIRouter()

@router.get("", response_model=Dict[str, Any])
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    type: Optional[TaskType] = Query(None, description="Filter by type"),
    plan_id: Optional[UUID] = Query(None, description="Filter by plan ID"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    due_date_start: Optional[date] = Query(None, description="Filter by due date start (inclusive)"),
    due_date_end: Optional[date] = Query(None, description="Filter by due date end (inclusive)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List tasks with filtering and pagination
    """
    query = select(Task).where(Task.user_id == current_user.id)
    
    # Filters
    if status:
        query = query.where(Task.status == status)
    if type:
        query = query.where(Task.type == type)
    if plan_id:
        query = query.where(Task.plan_id == plan_id)
    if tags:
        pass # Tag filtering implementation pending DB specific JSON operators
    if due_date_start:
        query = query.where(Task.due_date >= due_date_start)
    if due_date_end:
        query = query.where(Task.due_date <= due_date_end)

    # Order by created_at desc
    query = query.order_by(desc(Task.created_at))
    
    # Pagination
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar_one()
    
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return {
        "data": [TaskDetail.model_validate(t) for t in tasks],
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    }

@router.post("", response_model=Dict[str, Any])
async def create_task(
    task_in: TaskCreate,
    generate_guide: bool = Query(False, description="Whether to auto-generate guide"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new task
    """
    task = await TaskService.create(db, task_in, current_user.id)

    if generate_guide and not task.guide_content:
        # Call guide generation service
        guide = await task_guide_service.generate_guide(task, current_user, db)
        task.guide_content = guide
        db.add(task)
        await db.commit()
        await db.refresh(task)

    # Get Nudge suggestions based on user behavior patterns
    nudges = []
    try:
        nudge_service = IntelligentTaskService(db)
        nudges = await nudge_service.get_task_nudges(
            db, current_user.id,
            {"estimated_minutes": task_in.estimated_minutes, **task_in.model_dump()}
        )
    except Exception as e:
        logger.warning(f"Failed to get task nudges: {e}")

    return {
        "data": TaskDetail.model_validate(task),
        "nudges": nudges
    }

@router.post("/suggestions", response_model=TaskSuggestionResponse)
async def get_task_suggestions(
    request: TaskSuggestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取任务创建建议 (LLM 驱动)
    """
    service = IntelligentTaskService(db)
    return await service.get_suggestions(current_user.id, request.input_text)

@router.get("/recommendations/micro", response_model=List[TaskRecommendationResponse])
async def get_micro_task_recommendations(
    context: Optional[str] = Query(None, description="上下文: commute, lunch, evening"),
    limit: int = Query(3, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取碎片时间微任务推荐
    """
    from app.services.personalization import get_personalization_engine
    from app.services.task_recommendation_service import TaskRecommendationService

    engine = get_personalization_engine(db, cache_service.redis)
    service = TaskRecommendationService(db, engine)

    recommendations = await service.get_recommendations(
        user_id=current_user.id,
        limit=limit * 2,
        context=context,
    )

    micro_tasks = [r for r in recommendations if r.estimated_minutes <= 15]
    return [TaskRecommendationResponse(**r.__dict__) for r in micro_tasks[:limit]]

@router.get("/{task_id}", response_model=Dict[str, Any])
async def get_task(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get task details
    """
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError(message="Task not found")
        
    return {"data": TaskDetail.model_validate(task)}

@router.put("/{task_id}", response_model=Dict[str, Any])
async def update_task(
    task_in: TaskUpdate,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update task
    """
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError(message="Task not found")
        
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
        
    await db.commit()
    await db.refresh(task)
    
    return {"data": TaskDetail.model_validate(task)}

@router.delete("/{task_id}")
async def delete_task(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete task
    """
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError(message="Task not found")
        
    await db.delete(task)
    await db.commit()
    
    return {"success": True}

@router.post("/{task_id}/start", response_model=Dict[str, Any])
async def start_task(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start task
    """
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError(message="Task not found")
        
    task.status = TaskStatus.IN_PROGRESS
    task.started_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(task)
    
    return {"data": TaskDetail.model_validate(task)}

@router.post("/{task_id}/abandon", response_model=Dict[str, Any])
async def abandon_task(
    request: TaskAbandon,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Abandon task
    """
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError(message="Task not found")
        
    task.status = TaskStatus.ABANDONED
    task.user_note = request.reason # Store reason in user_note or separate field if available
    
    await db.commit()
    await db.refresh(task)
    
    return {"data": TaskDetail.model_validate(task)}

@router.post("/{task_id}/complete", response_model=Dict[str, Any])
async def complete_task(
    request: TaskCompleteRequest,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key")
):
    """
    完成任务 (v2.1 增强)
    """
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(message="Task not found")

    if task.status == TaskStatus.COMPLETED:
        return {
            "success": True,
            "data": {
                "task": TaskDetail.model_validate(task),
            },
            "message": "Task already completed",
            "retry_token": x_idempotency_key or "generated-token",
        }

    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.utcnow()
    task.actual_minutes = request.actual_minutes
    task.user_note = request.note
    # request.completion_quality is used for stats, ignored in model for now if not in schema

    await db.commit()
    await db.refresh(task)

    plan_update_result = None
    if task.plan_id:
        from app.services.plan_service import PlanService
        plan_update_result = await PlanService.update_progress(db, task.plan_id, task.user_id)

    spark_result = None
    if task.knowledge_node_id:
        from app.services.galaxy_service import GalaxyService

        galaxy_service = GalaxyService(db)
        study_minutes = request.actual_minutes or task.estimated_minutes or 15

        try:
            spark_result = await galaxy_service.spark_node(
                user_id=current_user.id,
                node_id=task.knowledge_node_id,
                study_minutes=study_minutes,
                task_id=task.id,
                trigger_expansion=True,
            )
            logger.info(
                "Task {} completion triggered galaxy spark: node={}, new_mastery={}",
                task_id,
                task.knowledge_node_id,
                spark_result.spark_event.new_mastery if spark_result and spark_result.spark_event else "N/A",
            )
        except Exception as e:
            logger.error(f"Failed to spark node after task completion: {e}")

    feedback = {}
    try:
        feedback = await feedback_service.generate_feedback(task, current_user, db)
    except Exception as e:
        logger.warning(f"Failed to generate feedback: {e}")

    galaxy_update = None
    if spark_result:
        next_review_at = None
        updated_status = spark_result.updated_status
        if updated_status and getattr(updated_status, "next_review_at", None):
            next_review_at = updated_status.next_review_at.isoformat()
        galaxy_update = {
            "node_id": str(task.knowledge_node_id),
            "new_mastery": spark_result.spark_event.new_mastery if spark_result.spark_event else None,
            "next_review_at": next_review_at,
        }

    # Generate Next Steps
    next_actions = []
    try:
        from app.services.next_step_service import next_step_service
        next_actions = await next_step_service.suggest_next_actions(
            completed_task=task,
            user=current_user,
            db=db
        )
    except Exception as e:
        logger.warning(f"Failed to generate next actions: {e}")

    # ========== Achievement Integration ==========
    unlocked_achievements = []
    try:
        from app.services.achievement_engine import AchievementEngine, AchievementEvent

        achievement_engine = AchievementEngine(db)
        unlocked = await achievement_engine.process_event(
            user_id=str(current_user.id),
            event_type=AchievementEvent.TASK_COMPLETED,
            task_id=str(task.id),
            actual_minutes=request.actual_minutes or task.estimated_minutes or 15,
            estimated_minutes=task.estimated_minutes,
            difficulty=task.difficulty if hasattr(task, 'difficulty') else None,
        )

        if unlocked:
            unlocked_achievements = unlocked
            next_actions.append({
                "type": "achievement_unlocked",
                "achievements": unlocked
            })
            logger.info(f"User {current_user.id} unlocked {len(unlocked)} achievements on task completion")
    except Exception as e:
        logger.warning(f"Achievement processing failed: {e}")
    # ============================================

    # 返回数据
    return {
        "success": True,
        "data": {
            "task": TaskDetail.model_validate(task),
            # Mock update data for MVP
            "flame_update": {
                "level_before": 3,
                "level_after": 3,
                "brightness_change": 5 + feedback.get("flame_bonus", 0)
            },
            "stats_update": {
                "today_completed": 5,
                "streak_days": 7
            },
            "feedback": feedback.get("content"),
            "plan_update": plan_update_result,
            "galaxy_update": galaxy_update or feedback.get("galaxy_update"),
            "unlocked_achievements": unlocked_achievements,
        },
        "next_actions": [action.model_dump() for action in next_actions],
        # 🆕 v2.1: 重试令牌 (在这里简单返回 key 或 生成一个新的 token)
        "retry_token": x_idempotency_key or "generated-token"
    }

@router.post("/confirm-batch/{tool_result_id}", response_model=Dict[str, Any])
async def confirm_generated_tasks(
    tool_result_id: str = Path(..., description="Tool result ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    确认 AI 生成的一批任务 (P0.1 修复)
    """
    from app.services.task_service import TaskService
    tasks = await TaskService.confirm_tasks_by_tool_result(
        db, tool_result_id, current_user.id
    )
    return {
        "success": True,
        "count": len(tasks),
        "data": [TaskDetail.model_validate(t) for t in tasks]
    }

# ========== Task Feedback Endpoints ==========

@router.post("/{task_id}/feedback", response_model=Dict[str, Any])
async def submit_task_feedback(
    feedback_in: TaskFeedbackCreate,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    提交任务反馈

    - 验证任务所有权
    - 验证任务状态（必须是COMPLETED）
    - 支持重复提交（更新现有反馈）
    - 自动推断并更新用户偏好
    """
    from app.services.task_feedback_service import TaskFeedbackService

    service = TaskFeedbackService(db, cache_service.redis)

    try:
        feedback = await service.submit_feedback(
            user_id=current_user.id,
            task_id=task_id,
            completion_quality=feedback_in.completion_quality,
            feedback_text=feedback_in.feedback_text,
            category=feedback_in.category,
        )
        return {
            "success": True,
            "data": TaskFeedbackResponse.model_validate(feedback)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}/feedback", response_model=Dict[str, Any])
async def get_task_feedback(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取任务的反馈历史

    返回该任务的所有反馈记录（按创建时间倒序）
    """
    from app.services.task_feedback_service import TaskFeedbackService

    # 验证任务所有权
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError(message="Task not found")

    service = TaskFeedbackService(db)
    feedbacks = await service.get_task_feedbacks(task_id)

    return {
        "success": True,
        "data": [TaskFeedbackResponse.model_validate(f) for f in feedbacks],
        "total": len(feedbacks)
    }


@router.get("/feedback/stats", response_model=Dict[str, Any])
async def get_user_feedback_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的任务反馈统计

    Returns:
        - total_feedbacks: 总反馈数
        - avg_completion_quality: 平均完成质量评分
        - category_distribution: 反馈分类分布
        - recent_feedbacks: 最近的反馈记录
    """
    from app.services.task_feedback_service import TaskFeedbackService

    service = TaskFeedbackService(db)
    stats = await service.get_user_task_feedback_stats(current_user.id)

    return {
        "success": True,
        "data": {
            "total_feedbacks": stats["total_feedbacks"],
            "avg_completion_quality": stats["avg_completion_quality"],
            "category_distribution": stats["category_distribution"],
            "recent_feedbacks": [
                TaskFeedbackResponse.model_validate(f) for f in stats["recent_feedbacks"]
            ],
        }
    }

