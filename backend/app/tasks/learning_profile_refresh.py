"""
用户学习画像日刷新任务
User Learning Profile Daily Refresh Task

V3-FIX-340 接线裁决（wt646）：本任务自 update_similarities.py 拆出并真实接入
celery（include + beat + 路由）。激活依据=UserLearningProfile 有活消费链：
SeedExtractor._onboarding_seeds（chat 上下文构建/仿真种子）逐日读
subject_distribution，而该表此前结构性零写入（写入方四任务全部不可达），
消费面永远走 "degraded onboarding context" 降级分支。

同源裁决下，update_all_user_similarities / update_item_similarities 两个相似度
任务已删除（读面 /recommendations API 零产品消费者，O(n²) 日算无兑付；
后者实现本身不落库）——若产品要推荐位，先建消费面再随测重引写入方。
"""
from typing import Any, cast
from uuid import UUID

from celery import shared_task
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time_utils import utcnow as _utcnow
from app.db.session import get_db_context
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.recommendation import UserItemInteraction, UserLearningProfile
from app.models.user import User

SIMILARITY_BATCH_FLUSH_SIZE = 100


@shared_task(
    name="tasks.update_user_learning_profiles",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    acks_late=True,
)
def update_user_learning_profiles():
    """
    更新用户学习画像（每日定时任务）

    聚合用户学习偏好和行为模式
    """
    logger.info("Starting user learning profile update task")

    try:
        with get_db_context() as db:
            import asyncio
            asyncio.run(_update_learning_profiles(db))

        logger.info("User learning profile update completed")
        return {"status": "success", "updated": True}

    except Exception as e:
        logger.error(f"User learning profile update failed: {e}")
        return {"status": "error", "message": str(e)}


async def _update_learning_profiles(db: AsyncSession) -> int:
    """更新用户学习画像"""
    # 获取所有用户
    users_query = select(User.id).where(
        User.is_active,
        User.not_deleted_filter()
    )
    result = await db.execute(users_query)
    user_ids = [row[0] for row in result.all()]

    updated_count = 0

    for user_id in user_ids:
        # 获取用户学习统计
        stats = await _get_user_learning_stats(db, user_id)

        # 获取或创建学习画像
        profile_query = select(UserLearningProfile).where(
            UserLearningProfile.user_id == user_id,
            UserLearningProfile.not_deleted_filter()
        )
        profile_result = await db.execute(profile_query)
        profile = profile_result.scalar_one_or_none()

        if profile:
            # 更新现有画像
            profile.subject_distribution = stats.get("subject_distribution", {})
            profile.total_study_minutes = stats.get("total_study_minutes", 0)
            profile.total_items_completed = stats.get("total_items_completed", 0)
            profile.average_session_duration = stats.get("average_session_duration")
            profile.learning_vector = stats.get("learning_vector")
            profile.last_updated_at = _utcnow()
            profile.update_version += 1
        else:
            # 创建新画像
            profile = UserLearningProfile(
                user_id=user_id,
                subject_distribution=stats.get("subject_distribution", {}),
                total_study_minutes=stats.get("total_study_minutes", 0),
                total_items_completed=stats.get("total_items_completed", 0),
                average_session_duration=stats.get("average_session_duration"),
                learning_vector=stats.get("learning_vector"),
                last_updated_at=_utcnow()
            )
            db.add(profile)

        updated_count += 1

        if updated_count % SIMILARITY_BATCH_FLUSH_SIZE == 0:
            await db.flush()

    await db.commit()
    logger.info(f"Updated {updated_count} user learning profiles")
    return updated_count


async def _get_user_learning_stats(
    db: AsyncSession,
    user_id: UUID
) -> dict[str, Any]:
    """获取用户学习统计"""
    # 统计各学科的学习数量
    subject_query = select(
        KnowledgeNode.subject_id,
        func.count(UserNodeStatus.id).label('count')
    ).join(
        UserNodeStatus, UserNodeStatus.node_id == KnowledgeNode.id
    ).where(
        UserNodeStatus.user_id == user_id,
        UserNodeStatus.mastery_score >= 50
    ).group_by(KnowledgeNode.subject_id)

    result = await db.execute(subject_query)

    subject_counts: dict[str, int] = {}
    total_count = 0

    for row in result.all():
        if row.subject_id:
            # label('count') 被 mypy 推断为 Callable；运行时是行内 int 计数
            count = cast("int", row.count)
            subject_counts[str(row.subject_id)] = count
            total_count += count

    # 转换为比例
    subject_distribution: dict[str, float] = (
        {k: v / total_count for k, v in subject_counts.items()} if total_count > 0 else {}
    )

    # 统计总学习时间（简化）
    study_time_query = select(func.count(UserItemInteraction.id)).where(
        UserItemInteraction.user_id == user_id,
        UserItemInteraction.interaction_type == "learned"
    )
    study_result = await db.execute(study_time_query)
    total_study_minutes = study_result.scalar() or 0

    return {
        "subject_distribution": subject_distribution,
        "total_study_minutes": total_study_minutes,
        "total_items_completed": total_count,
        "average_session_duration": 30.0,  # 默认值
        "learning_vector": list(subject_distribution.values())
    }
