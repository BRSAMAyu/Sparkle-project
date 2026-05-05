"""
Group Recommendation Service

Multi-stage recall -> rule-based scoring -> diversity re-ranking.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import desc, func, inspect, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.community import Friendship, FriendshipStatus, Group, GroupMember, GroupMessage, GroupType
from app.models.plan import Plan
from app.models.recommendation import RecommendationCache, UserItemInteraction
from app.models.task import Task
from app.schemas.community import (
    GroupListItem,
    GroupRecommendationFeedbackRequest,
    GroupRecommendationItem,
    GroupRecommendationReason,
    GroupTypeEnum,
    RecommendationItemTypeEnum,
)
from app.services.personalization.preference_service import PreferenceService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_tag(tag: str) -> str:
    return tag.strip().lower()


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _normalize_scores(values: dict[UUID, float]) -> dict[UUID, float]:
    if not values:
        return {}
    max_value = max(values.values())
    if max_value <= 0:
        return dict.fromkeys(values, 0.0)
    return {key: value / max_value for key, value in values.items()}


@dataclass
class _Candidate:
    group: Group
    member_count: int
    friend_count: int
    msg_count_7d: int
    tag_score: float
    activity_score: float
    quality_score: float
    freshness_score: float
    total_score: float
    tag_set: set[str]
    matched_tags: list[str]
    days_remaining: int | None


class GroupRecommendationService:
    """群组推荐多阶段服务"""

    RECOMMENDATION_TYPE = "group_v1"
    CACHE_TTL_SECONDS = 60 * 60 * 12
    DISMISS_TTL_DAYS = 30
    MAX_RECOMMENDATIONS = 60

    @classmethod
    async def get_recommendations(
        cls,
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20,
        cursor: int = 0,
    ) -> list[GroupRecommendationItem]:
        cached = await cls._get_cached_recommendations(db, user_id)
        if cached:
            cached.hit_count += 1
            items = [
                GroupRecommendationItem.model_validate(item)
                for item in (cached.cached_recommendations or [])
            ]
        else:
            target_size = max(limit + cursor, cls.MAX_RECOMMENDATIONS)
            items = await cls._generate_recommendations(
                db,
                user_id,
                target_size,
            )
            await cls._cache_recommendations(db, user_id, items)

        if cursor:
            return items[cursor:cursor + limit]
        return items[:limit]

    @classmethod
    async def record_feedback(
        cls,
        db: AsyncSession,
        user_id: UUID,
        feedback: GroupRecommendationFeedbackRequest,
    ) -> UserItemInteraction | None:
        if not await cls._table_exists(db, UserItemInteraction.__tablename__):
            return None

        interaction = UserItemInteraction(
            user_id=user_id,
            item_id=feedback.group_id,
            item_type="group",
            interaction_type=f"reco_{feedback.action}",
            interaction_weight=1.0,
            meta={
                "source": feedback.source,
                "reason_types": feedback.reason_types or [],
                "recommendation_type": cls.RECOMMENDATION_TYPE,
            },
        )
        db.add(interaction)
        await db.flush()

        if feedback.action in {"dismiss", "join"}:
            await cls._clear_cache(db, user_id)
        return interaction

    @classmethod
    async def _get_cached_recommendations(
        cls,
        db: AsyncSession,
        user_id: UUID,
    ) -> RecommendationCache | None:
        if not await cls._table_exists(db, RecommendationCache.__tablename__):
            return None

        query = select(RecommendationCache).where(
            RecommendationCache.user_id == user_id,
            RecommendationCache.recommendation_type == cls.RECOMMENDATION_TYPE,
            RecommendationCache.expires_at > _utcnow(),
            RecommendationCache.not_deleted_filter(),
        ).order_by(desc(RecommendationCache.generated_at)).limit(1)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def _cache_recommendations(
        cls,
        db: AsyncSession,
        user_id: UUID,
        items: list[GroupRecommendationItem],
    ) -> None:
        if not await cls._table_exists(db, RecommendationCache.__tablename__):
            return

        cache = RecommendationCache(
            user_id=user_id,
            recommendation_type=cls.RECOMMENDATION_TYPE,
            cached_recommendations=[item.model_dump(mode="json") for item in items],
            generated_at=_utcnow(),
            expires_at=_utcnow() + timedelta(seconds=cls.CACHE_TTL_SECONDS),
        )
        db.add(cache)
        await db.flush()

    @classmethod
    async def _clear_cache(cls, db: AsyncSession, user_id: UUID) -> None:
        if not await cls._table_exists(db, RecommendationCache.__tablename__):
            return

        result = await db.execute(
            select(RecommendationCache).where(
                RecommendationCache.user_id == user_id,
                RecommendationCache.recommendation_type == cls.RECOMMENDATION_TYPE,
                RecommendationCache.not_deleted_filter(),
            ),
        )
        caches = list(result.scalars().all())
        for cache in caches:
            await cache.delete(db, soft=True)

    @classmethod
    async def _generate_recommendations(
        cls,
        db: AsyncSession,
        user_id: UUID,
        limit: int,
    ) -> list[GroupRecommendationItem]:
        now = _utcnow()

        user_group_ids = await cls._get_user_group_ids(db, user_id)
        dismissed_group_ids = await cls._get_recent_dismissed_group_ids(
            db, user_id, now,
        )
        friend_ids = await cls._get_friend_ids(db, user_id)

        eligible_groups = await cls._get_eligible_groups(
            db,
            now,
            user_group_ids,
            dismissed_group_ids,
        )
        if not eligible_groups:
            return []

        group_ids = [group.id for group in eligible_groups]
        member_counts = await cls._get_member_counts(db, group_ids)
        friend_counts = await cls._get_friend_counts(db, group_ids, friend_ids)
        msg_counts = await cls._get_message_counts(db, group_ids, now)
        user_tags = await cls._collect_user_tags(db, user_id)
        tuning = await cls._load_feedback_tuning(db, user_id)

        activity_raw = {
            group.id: msg_counts.get(group.id, 0) + group.today_checkin_count * 2
            for group in eligible_groups
        }
        quality_raw = {
            group.id: math.log1p(member_counts.get(group.id, 0))
            + math.log1p(group.total_flame_power + 1)
            for group in eligible_groups
        }
        friend_raw = {
            group.id: math.log1p(friend_counts.get(group.id, 0))
            for group in eligible_groups
        }

        activity_scores = _normalize_scores(activity_raw)
        quality_scores = _normalize_scores(quality_raw)
        friend_scores = _normalize_scores(friend_raw)

        tag_weight = 0.35 * float((tuning.get("feature_weights") or {}).get("tag_score", 1.0))
        friend_weight = 0.25 * float((tuning.get("feature_weights") or {}).get("friend_affinity", 1.0))
        activity_weight = 0.20 * float((tuning.get("feature_weights") or {}).get("activity", 1.0))
        quality_weight = 0.10 * float((tuning.get("feature_weights") or {}).get("quality", 1.0))
        freshness_weight = 0.10 * float((tuning.get("feature_weights") or {}).get("freshness", 1.0))

        weight_sum = tag_weight + friend_weight + activity_weight + quality_weight + freshness_weight
        if weight_sum > 0:
            tag_weight /= weight_sum
            friend_weight /= weight_sum
            activity_weight /= weight_sum
            quality_weight /= weight_sum
            freshness_weight /= weight_sum

        if not user_tags:
            activity_weight += tag_weight * 0.5
            quality_weight += tag_weight * 0.5
            tag_weight = 0.0
            weight_sum = friend_weight + activity_weight + quality_weight + freshness_weight
            if weight_sum > 0:
                friend_weight /= weight_sum
                activity_weight /= weight_sum
                quality_weight /= weight_sum
                freshness_weight /= weight_sum

        candidates = []
        for group in eligible_groups:
            group_tags = group.focus_tags or []
            normalized_group_tags = {
                _normalize_tag(tag) for tag in group_tags if _normalize_tag(tag)
            }
            tag_score = _jaccard(user_tags, normalized_group_tags)
            matched_tags = [
                tag for tag in group_tags if _normalize_tag(tag) in user_tags
            ]

            freshness_score = cls._freshness_score(now, group.created_at)
            total_score = (
                tag_score * tag_weight
                + friend_scores.get(group.id, 0.0) * friend_weight
                + activity_scores.get(group.id, 0.0) * activity_weight
                + quality_scores.get(group.id, 0.0) * quality_weight
                + freshness_score * freshness_weight
            )

            days_remaining = None
            if group.deadline:
                delta = group.deadline - now
                days_remaining = max(0, delta.days)

            candidates.append(
                _Candidate(
                    group=group,
                    member_count=member_counts.get(group.id, 0),
                    friend_count=friend_counts.get(group.id, 0),
                    msg_count_7d=msg_counts.get(group.id, 0),
                    tag_score=tag_score,
                    activity_score=activity_scores.get(group.id, 0.0),
                    quality_score=quality_scores.get(group.id, 0.0),
                    freshness_score=freshness_score,
                    total_score=total_score,
                    tag_set=normalized_group_tags,
                    matched_tags=matched_tags[:3],
                    days_remaining=days_remaining,
                ),
            )

        candidates = cls._apply_recall_filters(
            candidates,
            activity_scores,
            quality_scores,
            friend_counts,
        )
        candidates.sort(key=lambda item: item.total_score, reverse=True)

        ranked = cls._mmr_rerank(candidates, limit)
        ranked = cls._inject_exploration(ranked, candidates, limit, user_id, now)

        return [cls._to_recommendation(item, now) for item in ranked[:limit]]

    @staticmethod
    async def _get_user_group_ids(db: AsyncSession, user_id: UUID) -> set[UUID]:
        result = await db.execute(
            select(GroupMember.group_id).where(
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter(),
            ),
        )
        return {row[0] for row in result.all()}

    @classmethod
    async def _get_recent_dismissed_group_ids(
        cls,
        db: AsyncSession,
        user_id: UUID,
        now: datetime,
    ) -> set[UUID]:
        if not await cls._table_exists(db, UserItemInteraction.__tablename__):
            return set()

        result = await db.execute(
            select(UserItemInteraction.item_id).where(
                UserItemInteraction.user_id == user_id,
                UserItemInteraction.item_type == "group",
                UserItemInteraction.interaction_type == "reco_dismiss",
                UserItemInteraction.created_at
                >= now - timedelta(days=cls.DISMISS_TTL_DAYS),
                UserItemInteraction.not_deleted_filter(),
            ),
        )
        return {row[0] for row in result.all()}

    @staticmethod
    async def _table_exists(db: AsyncSession, table_name: str) -> bool:
        connection = await db.connection()
        return await connection.run_sync(
            lambda sync_conn: inspect(sync_conn).has_table(table_name),
        )

    @staticmethod
    async def _get_friend_ids(db: AsyncSession, user_id: UUID) -> set[UUID]:
        result = await db.execute(
            select(Friendship).where(
                Friendship.status == FriendshipStatus.ACCEPTED,
                Friendship.not_deleted_filter(),
                or_(Friendship.user_id == user_id, Friendship.friend_id == user_id),
            ),
        )
        friend_ids = set()
        for friendship in result.scalars().all():
            friend_ids.add(
                friendship.friend_id
                if friendship.user_id == user_id
                else friendship.user_id
            )
        return friend_ids

    @staticmethod
    async def _get_eligible_groups(
        db: AsyncSession,
        now: datetime,
        user_group_ids: set[UUID],
        dismissed_group_ids: set[UUID],
    ) -> list[Group]:
        result = await db.execute(
            select(Group).where(
                Group.is_public.is_(True),
                Group.not_deleted_filter(),
            ),
        )
        groups = list(result.scalars().all())
        eligible = []
        for group in groups:
            if group.id in user_group_ids:
                continue
            if group.id in dismissed_group_ids:
                continue
            if group.type == GroupType.SPRINT and group.deadline and group.deadline <= now:
                continue
            eligible.append(group)
        return eligible

    @staticmethod
    async def _get_member_counts(
        db: AsyncSession,
        group_ids: list[UUID],
    ) -> dict[UUID, int]:
        if not group_ids:
            return {}
        result = await db.execute(
            select(GroupMember.group_id, func.count(GroupMember.id))
            .where(
                GroupMember.group_id.in_(group_ids),
                GroupMember.not_deleted_filter(),
            )
            .group_by(GroupMember.group_id),
        )
        return {row[0]: int(row[1]) for row in result.all()}

    @staticmethod
    async def _get_friend_counts(
        db: AsyncSession,
        group_ids: list[UUID],
        friend_ids: set[UUID],
    ) -> dict[UUID, int]:
        if not group_ids or not friend_ids:
            return {}
        result = await db.execute(
            select(GroupMember.group_id, func.count(GroupMember.id))
            .where(
                GroupMember.group_id.in_(group_ids),
                GroupMember.user_id.in_(friend_ids),
                GroupMember.not_deleted_filter(),
            )
            .group_by(GroupMember.group_id),
        )
        return {row[0]: int(row[1]) for row in result.all()}

    @staticmethod
    async def _get_message_counts(
        db: AsyncSession,
        group_ids: list[UUID],
        now: datetime,
    ) -> dict[UUID, int]:
        if not group_ids:
            return {}
        since = now - timedelta(days=7)
        result = await db.execute(
            select(GroupMessage.group_id, func.count(GroupMessage.id))
            .where(
                GroupMessage.group_id.in_(group_ids),
                GroupMessage.created_at >= since,
                GroupMessage.not_deleted_filter(),
            )
            .group_by(GroupMessage.group_id),
        )
        return {row[0]: int(row[1]) for row in result.all()}

    @staticmethod
    async def _collect_user_tags(db: AsyncSession, user_id: UUID) -> set[str]:
        tags: set[str] = set()

        task_rows = await db.execute(
            select(Task.tags).where(
                Task.user_id == user_id,
                Task.not_deleted_filter(),
            ),
        )
        for row in task_rows.scalars().all():
            if not row:
                continue
            for tag in row:
                normalized = _normalize_tag(str(tag))
                if normalized:
                    tags.add(normalized)

        plan_rows = await db.execute(
            select(Plan.subject).where(
                Plan.user_id == user_id,
                Plan.subject.is_not(None),
                Plan.not_deleted_filter(),
            ),
        )
        for subject in plan_rows.scalars().all():
            normalized = _normalize_tag(str(subject))
            if normalized:
                tags.add(normalized)

        group_tag_rows = await db.execute(
            select(Group.focus_tags).join(
                GroupMember,
                GroupMember.group_id == Group.id,
            ).where(
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter(),
                Group.not_deleted_filter(),
            ),
        )
        for row in group_tag_rows.scalars().all():
            if not row:
                continue
            for tag in row:
                normalized = _normalize_tag(str(tag))
                if normalized:
                    tags.add(normalized)

        if len(tags) > 50:
            return set(list(tags)[:50])
        return tags

    @staticmethod
    def _freshness_score(now: datetime, created_at: datetime | None) -> float:
        if not created_at:
            return 0.0
        days_since = max(0, (now - created_at).days)
        return max(0.0, 1.0 - min(days_since, 60) / 60)

    @staticmethod
    def _apply_recall_filters(
        candidates: list[_Candidate],
        activity_scores: dict[UUID, float],
        quality_scores: dict[UUID, float],
        friend_counts: dict[UUID, int],
    ) -> list[_Candidate]:
        if not candidates:
            return []

        friend_ids = {item.group.id for item in candidates if friend_counts.get(item.group.id, 0) > 0}
        tag_ids = {item.group.id for item in candidates if item.tag_score > 0}
        activity_ids = {
            group_id
            for group_id, _ in sorted(
                activity_scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:50]
        }
        quality_ids = {
            group_id
            for group_id, _ in sorted(
                quality_scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:50]
        }

        recall_ids = friend_ids | tag_ids | activity_ids | quality_ids
        if not recall_ids:
            return candidates
        return [item for item in candidates if item.group.id in recall_ids]

    @staticmethod
    def _mmr_rerank(
        candidates: list[_Candidate],
        limit: int,
        lambda_weight: float = 0.8,
    ) -> list[_Candidate]:
        if not candidates:
            return []
        selected = [candidates[0]]
        remaining = candidates[1:]
        while remaining and len(selected) < limit:
            best = None
            best_score = float("-inf")
            for candidate in remaining:
                max_sim = 0.0
                for picked in selected:
                    sim = _jaccard(candidate.tag_set, picked.tag_set)
                    if sim > max_sim:
                        max_sim = sim
                score = lambda_weight * candidate.total_score - (1 - lambda_weight) * max_sim
                if score > best_score:
                    best = candidate
                    best_score = score
            if best is None:
                break
            selected.append(best)
            remaining.remove(best)
        return selected

    @classmethod
    def _inject_exploration(
        cls,
        ranked: list[_Candidate],
        candidates: list[_Candidate],
        limit: int,
        user_id: UUID,
        now: datetime,
    ) -> list[_Candidate]:
        if not ranked or len(ranked) < 5:
            return ranked

        exploration_count = max(1, math.ceil(limit * 0.1))
        if len(ranked) <= exploration_count:
            return ranked

        remaining = [item for item in candidates if item not in ranked]
        if not remaining:
            return ranked

        explore_pool = sorted(
            remaining,
            key=lambda item: item.activity_score + item.freshness_score,
            reverse=True,
        )[:max(exploration_count * 3, 10)]
        if not explore_pool:
            return ranked

        seed_bucket = int(now.timestamp() // cls.CACHE_TTL_SECONDS)
        rng = random.Random(f"{user_id}-{seed_bucket}")
        picks = (
            rng.sample(explore_pool, exploration_count)
            if len(explore_pool) >= exploration_count
            else explore_pool
        )

        return ranked[:-exploration_count] + picks

    @classmethod
    def _to_recommendation(cls, candidate: _Candidate, now: datetime) -> GroupRecommendationItem:
        group = candidate.group
        days_remaining = candidate.days_remaining
        group_item = GroupListItem(
            id=group.id,
            name=group.name,
            type=GroupTypeEnum(group.type.value),
            member_count=candidate.member_count,
            total_flame_power=group.total_flame_power,
            deadline=group.deadline,
            days_remaining=days_remaining,
            focus_tags=group.focus_tags or [],
            sprint_goal=group.sprint_goal,
            my_role=None,
        )

        reasons = cls._build_reasons(candidate, now)

        return GroupRecommendationItem(
            group=group_item,
            score=min(max(candidate.total_score, 0.0), 1.0),
            reasons=reasons,
            requires_approval=group.join_requires_approval,
        )

    @classmethod
    async def _load_feedback_tuning(
        cls,
        db: AsyncSession,
        user_id: UUID,
    ) -> dict[str, dict[str, float]]:
        from app.services.recommendation_feedback_service import RecommendationFeedbackService

        preference_service = PreferenceService(db, cache_service.redis)
        prefs = await preference_service.get_preferences(user_id)
        tuning_root = dict((prefs.explicit or {}).get(RecommendationFeedbackService.TUNING_PREF_KEY) or {})
        user_tuning = dict(tuning_root.get("group") or {})
        global_adjustments = await RecommendationFeedbackService.get_global_adjustments(
            db,
            RecommendationItemTypeEnum.GROUP,
        )
        merged_features = dict(user_tuning.get("feature_weights") or {})
        for key, value in (global_adjustments or {}).items():
            merged_features[key] = float(merged_features.get(key, 1.0)) * float(value)
        return {"feature_weights": merged_features}

    @classmethod
    def _build_reasons(
        cls,
        candidate: _Candidate,
        now: datetime,
    ) -> list[GroupRecommendationReason]:
        reasons: list[GroupRecommendationReason] = []

        if candidate.friend_count > 0:
            reasons.append(
                GroupRecommendationReason(
                    type="friend_overlap",
                    data={"friend_count": candidate.friend_count},
                ),
            )

        if candidate.matched_tags:
            reasons.append(
                GroupRecommendationReason(
                    type="tag_overlap",
                    data={"tags": candidate.matched_tags},
                ),
            )

        if candidate.msg_count_7d >= 10 or candidate.activity_score >= 0.6:
            reasons.append(
                GroupRecommendationReason(
                    type="trending",
                    data={"msg_7d": candidate.msg_count_7d},
                ),
            )

        if candidate.group.created_at:
            days_since = max(0, (now - candidate.group.created_at).days)
            if days_since <= 30:
                data = None
                if candidate.group.type == GroupType.SPRINT and candidate.days_remaining is not None:
                    data = {"days_remaining": candidate.days_remaining}
                else:
                    data = {"days_since": days_since}
                reasons.append(GroupRecommendationReason(type="fresh", data=data))

        if candidate.group.join_requires_approval:
            approval_reason = GroupRecommendationReason(type="approval_required", data=None)
            if all(reason.type != "approval_required" for reason in reasons):
                if len(reasons) >= 2:
                    reasons[-1] = approval_reason
                else:
                    reasons.append(approval_reason)

        return reasons[:2]
