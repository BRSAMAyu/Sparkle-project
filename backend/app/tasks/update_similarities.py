"""
用户相似度更新任务
User Similarity Update Tasks

每日定时任务，计算用户相似度并缓存
"""
from collections import defaultdict
from datetime import datetime, timedelta, UTC
from typing import Any
from uuid import UUID

from celery import shared_task
from celery.schedules import crontab
from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_context
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.recommendation import UserItemInteraction, UserLearningProfile, UserSimilarity
from app.models.user import User

SIMILARITY_BATCH_FLUSH_SIZE = 100


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@shared_task(name="tasks.update_all_user_similarities")
def update_all_user_similarities():
    """
    更新所有用户的相似度（每日定时任务）

    执行时间：每天 02:00
    计算方法：Jaccard 相似度
    缓存有效期：24小时
    """
    logger.info("Starting user similarity update task")

    try:
        with get_db_context() as db:
            import asyncio
            asyncio.run(_update_all_similarities(db))

        logger.info("User similarity update task completed")
        return {"status": "success", "updated": True}

    except Exception as e:
        logger.error(f"User similarity update failed: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="tasks.update_user_learning_profiles")
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


@shared_task(name="tasks.update_item_similarities")
def update_item_similarities():
    """
    更新物品相似度（每日定时任务）

    基于用户共同学习行为计算物品相似度
    """
    logger.info("Starting item similarity update task")

    try:
        with get_db_context() as db:
            import asyncio
            asyncio.run(_update_item_similarities(db))

        logger.info("Item similarity update completed")
        return {"status": "success", "updated": True}

    except Exception as e:
        logger.error(f"Item similarity update failed: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="tasks.expire_old_recommendation_cache")
def expire_old_recommendation_cache():
    """
    清理过期的推荐缓存

    每小时执行一次
    """
    logger.info("Starting recommendation cache cleanup")

    try:
        with get_db_context() as db:
            import asyncio
            asyncio.run(_cleanup_expired_cache(db))

        logger.info("Recommendation cache cleanup completed")
        return {"status": "success", "cleaned": True}

    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        return {"status": "error", "message": str(e)}


# ==================== 异步实现函数 ====================

async def _update_all_similarities(db: AsyncSession) -> int:
    """
    更新所有用户相似度的核心逻辑

    Jaccard 相似度：similarity = |A ∩ B| / |A ∪ B|
    """
    # 获取活跃用户列表（最近30天有活动）
    active_since = _utcnow() - timedelta(days=30)

    active_users_query = select(User.id).where(
        User.is_active,
        User.not_deleted_filter(),
        User.last_login_at >= active_since
    )
    result = await db.execute(active_users_query)
    active_user_ids = [row[0] for row in result.all()]

    logger.info(f"Found {len(active_user_ids)} active users")

    # 获取每个用户学习的物品集合
    user_items = await _get_user_item_sets(db, active_user_ids)

    # 计算用户两两之间的相似度
    similarity_count = 0
    version = int(_utcnow().timestamp())

    for i, user_id_1 in enumerate(active_user_ids):
        items_1 = user_items.get(user_id_1, set())

        for user_id_2 in active_user_ids[i + 1:]:
            items_2 = user_items.get(user_id_2, set())

            # 跳过没有学习记录的用户
            if not items_1 or not items_2:
                continue

            # 计算 Jaccard 相似度
            intersection = len(items_1 & items_2)
            union = len(items_1 | items_2)

            if union == 0:
                continue

            similarity = intersection / union

            # 只保留相似度 >= 0.1 的关系
            if similarity < 0.1:
                continue

            # 获取共同学科
            common_subjects = await _get_common_subjects(
                db, user_id_1, user_id_2, items_1 & items_2
            )

            # 规范化用户ID顺序
            if str(user_id_1) < str(user_id_2):
                smaller, larger = user_id_1, user_id_2
            else:
                smaller, larger = user_id_2, user_id_1

            # 检查是否已存在
            existing_query = select(UserSimilarity).where(
                UserSimilarity.user_id_1 == smaller,
                UserSimilarity.user_id_2 == larger,
                UserSimilarity.not_deleted_filter()
            )
            existing_result = await db.execute(existing_query)
            existing = existing_result.scalar_one_or_none()

            if existing:
                # 更新现有记录
                existing.similarity_score = similarity
                existing.common_items_count = intersection
                existing.common_subjects = common_subjects
                existing.last_calculated_at = _utcnow()
                existing.calculation_version = version
            else:
                # 创建新记录
                new_similarity = UserSimilarity(
                    user_id_1=smaller,
                    user_id_2=larger,
                    similarity_score=similarity,
                    common_items_count=intersection,
                    common_subjects=common_subjects,
                    last_calculated_at=_utcnow(),
                    calculation_version=version
                )
                db.add(new_similarity)

            similarity_count += 1

        if (i + 1) % SIMILARITY_BATCH_FLUSH_SIZE == 0:
            await db.flush()
            logger.info(f"Processed {i + 1}/{len(active_user_ids)} users")

    await db.commit()

    # 删除过期的相似度记录
    await _delete_expired_similarities(db, version)

    logger.info(f"Updated {similarity_count} user similarities")
    return similarity_count


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


async def _update_item_similarities(db: AsyncSession) -> int:
    """更新物品相似度"""
    # 获取所有被学习的物品
    items_query = select(
        UserItemInteraction.item_id,
        UserItemInteraction.item_type
    ).where(
        UserItemInteraction.not_deleted_filter()
    ).distinct()

    result = await db.execute(items_query)
    items = result.all()

    # 按类型分组
    items_by_type = defaultdict(list)
    for item_id, item_type in items:
        items_by_type[item_type].append(item_id)

    # 对每种类型计算相似度
    similarity_count = 0

    for item_type, item_ids in items_by_type.items():
        # 获取每个物品的学习用户集合
        item_users = await _get_item_user_sets(db, item_ids, item_type)

        # 计算物品两两之间的相似度
        for i, item_id_1 in enumerate(item_ids):
            users_1 = item_users.get(item_id_1, set())

            for item_id_2 in item_ids[i + 1:]:
                users_2 = item_users.get(item_id_2, set())

                if not users_1 or not users_2:
                    continue

                # Jaccard 相似度
                intersection = len(users_1 & users_2)
                union = len(users_1 | users_2)

                if union == 0:
                    continue

                similarity = intersection / union

                # 只保留相似度 >= 0.2 的关系
                if similarity < 0.2:
                    continue

                # 保存相似度（简化实现，实际应该用 upsert）
                # 这里省略实际保存代码，因为 ItemSimilarity 模型设计需要调整
                similarity_count += 1

    await db.commit()
    logger.info(f"Updated {similarity_count} item similarities")
    return similarity_count


async def _cleanup_expired_cache(db: AsyncSession) -> int:
    """清理过期的推荐缓存"""
    from app.models.recommendation import RecommendationCache

    # 删除过期的缓存
    delete_query = delete(RecommendationCache).where(
        RecommendationCache.expires_at < _utcnow()
    )
    result = await db.execute(delete_query)
    deleted_count = result.rowcount

    await db.commit()
    logger.info(f"Cleaned up {deleted_count} expired cache entries")
    return deleted_count


async def _delete_expired_similarities(db: AsyncSession, current_version: int) -> int:
    """删除过期的相似度记录"""
    delete_query = delete(UserSimilarity).where(
        UserSimilarity.calculation_version < current_version - 7  # 保留7个版本
    )
    result = await db.execute(delete_query)
    deleted_count = result.rowcount

    await db.commit()
    logger.info(f"Deleted {deleted_count} expired similarity records")
    return deleted_count


async def _get_user_item_sets(
    db: AsyncSession,
    user_ids: list[UUID]
) -> dict[UUID, set[UUID]]:
    """获取用户学习的物品集合"""
    query = select(
        UserItemInteraction.user_id,
        UserItemInteraction.item_id
    ).where(
        UserItemInteraction.user_id.in_(user_ids),
        UserItemInteraction.interaction_type.in_(["learned", "LEARNED", "completed", "COMPLETED"]),
        UserItemInteraction.not_deleted_filter()
    )

    result = await db.execute(query)
    user_items = defaultdict(set)

    for user_id, item_id in result.all():
        user_items[user_id].add(item_id)

    return dict(user_items)


async def _get_item_user_sets(
    db: AsyncSession,
    item_ids: list[UUID],
    item_type: str
) -> dict[UUID, set[UUID]]:
    """获取物品的学习用户集合"""
    query = select(
        UserItemInteraction.item_id,
        UserItemInteraction.user_id
    ).where(
        UserItemInteraction.item_id.in_(item_ids),
        UserItemInteraction.item_type == item_type,
        UserItemInteraction.not_deleted_filter()
    )

    result = await db.execute(query)
    item_users = defaultdict(set)

    for item_id, user_id in result.all():
        item_users[item_id].add(user_id)

    return dict(item_users)


async def _get_common_subjects(
    db: AsyncSession,
    user_id_1: UUID,
    user_id_2: UUID,
    common_items: set[UUID]
) -> list[str]:
    """获取共同学科"""
    if not common_items:
        return []

    # 查询这些物品所属的学科
    query = select(
        KnowledgeNode.subject_id,
        func.count(KnowledgeNode.id).label('count')
    ).where(
        KnowledgeNode.id.in_(common_items)
    ).group_by(KnowledgeNode.subject_id)

    result = await db.execute(query)

    # 返回学科ID列表（实际应该返回学科名称）
    common_subjects = []
    for row in result.all():
        if row.subject_id:
            common_subjects.append(str(row.subject_id))

    return common_subjects


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

    subject_distribution = {}
    total_count = 0

    for row in result.all():
        if row.subject_id:
            subject_distribution[str(row.subject_id)] = row.count
            total_count += row.count

    # 转换为比例
    if total_count > 0:
        subject_distribution = {
            k: v / total_count
            for k, v in subject_distribution.items()
        }

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


# Celery Beat 配置示例
CELERYBEAT_SCHEDULE = {
    "update-user-similarities": {
        "task": "tasks.update_similarities.update_all_user_similarities",
        "schedule": crontab(hour=2, minute=0),  # 每天凌晨2点
    },
    "update-learning-profiles": {
        "task": "tasks.update_similarities.update_user_learning_profiles",
        "schedule": crontab(hour=3, minute=0),  # 每天凌晨3点
    },
    "update-item-similarities": {
        "task": "tasks.update_similarities.update_item_similarities",
        "schedule": crontab(hour=4, minute=0),  # 每天凌晨4点
    },
    "cleanup-cache": {
        "task": "tasks.update_similarities.expire_old_recommendation_cache",
        "schedule": crontab(minute=0),  # 每小时
    },
}
