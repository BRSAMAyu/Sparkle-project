from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, inspect, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.core.profile_context import ProfileContext
from app.db.session import AsyncSessionLocal
from app.models.accountability import (
    AccountabilityPartnership,
    AccountabilitySlotType,
    AccountabilityStatus,
)
from app.models.community import Friendship, FriendshipStatus, GroupMember, UserBlock
from app.models.recommendation import RecommendationCache, UserItemInteraction
from app.models.user import SearchVisibility, User
from app.schemas.community import (
    FriendMatchStrategyEnum,
    FriendRecommendation,
    FriendRecommendationFeedbackRequest,
    FriendRecommendationTargetEnum,
    RecommendationItemTypeEnum,
    UserBrief,
)
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_context_service import ProfileContextService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_tag(value: str | None) -> str:
    return str(value or "").strip().lower()


def _normalize_set(values: list[str] | set[str] | None) -> set[str]:
    if not values:
        return set()
    return {_normalize_tag(value) for value in values if _normalize_tag(value)}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _closeness(left: float | int | None, right: float | int | None, max_gap: float) -> float:
    if left is None or right is None or max_gap <= 0:
        return 0.5
    return max(0.0, 1.0 - abs(float(left) - float(right)) / max_gap)


def _risk_bucket(risk_signal: str) -> str | None:
    if risk_signal in {"risk.execution_delay", "risk.focus_fatigue"}:
        return "execution"
    if risk_signal == "risk.knowledge_gap":
        return "mastery"
    if risk_signal == "risk.planning_overrun":
        return "planning"
    if risk_signal == "risk.overcorrection":
        return "balance"
    return None


@dataclass
class _CandidateProfile:
    user: User
    context: ProfileContext
    relationship_status: str
    is_existing_friend: bool
    can_invite_accountability: bool
    group_overlap_count: int
    has_core_accountability_partner: bool
    active_subjects: set[str]
    risk_buckets: set[str]
    pattern_names: set[str]
    overall_mastery: float
    engagement_score: float
    depth_preference: float
    curiosity_preference: float
    focus_duration_preference: float
    learning_style: str
    feedback_style: str
    dominant_pattern_type: str | None


class FriendMatchService:
    """好友/责任伙伴匹配推荐服务。"""

    CACHE_TTL_SECONDS = 60 * 20
    MAX_CANDIDATES = 60

    @classmethod
    async def get_recommendations(
        cls,
        db: AsyncSession,
        current_user: User,
        *,
        limit: int = 10,
        strategy: FriendMatchStrategyEnum = FriendMatchStrategyEnum.COMPATIBILITY,
        target: FriendRecommendationTargetEnum = FriendRecommendationTargetEnum.ACCOUNTABILITY,
    ) -> list[FriendRecommendation]:
        recommendation_type = f"friend_match_v2:{strategy.value}:{target.value}"
        cached = await cls._get_cached_recommendations(
            db,
            current_user.id,
            recommendation_type,
        )
        if cached:
            return cached[:limit]

        items = await cls._generate_recommendations(
            db,
            current_user,
            limit=limit,
            strategy=strategy,
            target=target,
        )
        await cls._cache_recommendations(
            db,
            current_user.id,
            recommendation_type,
            items,
        )
        return items[:limit]

    @classmethod
    async def record_feedback(
        cls,
        db: AsyncSession,
        current_user_id: UUID,
        payload: FriendRecommendationFeedbackRequest,
    ) -> UserItemInteraction | None:
        if not await cls._table_exists(db, UserItemInteraction.__tablename__):
            return None

        interaction = UserItemInteraction(
            user_id=current_user_id,
            item_id=payload.target_user_id,
            item_type="friend_candidate",
            interaction_type=f"friend_match_{payload.action}",
            interaction_weight=1.0,
            meta={
                "strategy": payload.strategy.value,
                "target": payload.target.value,
                "source": payload.source,
                "score": payload.score,
            },
        )
        db.add(interaction)
        await db.flush()

        if payload.action in {"dismiss", "friend_request", "accountability_invite"}:
            await cls._clear_cache(db, current_user_id)
        return interaction

    @classmethod
    async def _generate_recommendations(
        cls,
        db: AsyncSession,
        current_user: User,
        *,
        limit: int,
        strategy: FriendMatchStrategyEnum,
        target: FriendRecommendationTargetEnum,
    ) -> list[FriendRecommendation]:
        relationship_map = await cls._load_relationship_map(db, current_user.id)
        blocked_user_ids = await cls._load_blocked_user_ids(db, current_user.id)
        current_has_core_partner, partner_state_map = await cls._load_accountability_state(
            db,
            current_user.id,
        )
        group_overlap_map = await cls._load_group_overlap_counts(db, current_user.id)

        accepted_friend_ids = {
            user_id
            for user_id, status in relationship_map.items()
            if status == FriendshipStatus.ACCEPTED.value
        }
        pending_user_ids = {
            user_id
            for user_id, status in relationship_map.items()
            if status == FriendshipStatus.PENDING.value
        }

        public_candidates = await cls._load_public_candidates(
            db,
            current_user.id,
            accepted_friend_ids=accepted_friend_ids,
            pending_user_ids=pending_user_ids,
            blocked_user_ids=blocked_user_ids,
        )
        accepted_friends = await cls._load_existing_friends(
            db,
            accepted_friend_ids=accepted_friend_ids,
            blocked_user_ids=blocked_user_ids,
        )

        candidates_by_id: dict[str, User] = {
            str(user.id): user
            for user in [*accepted_friends, *public_candidates]
            if str(user.id) != str(current_user.id)
        }

        async with AsyncSessionLocal() as profile_db:
            profile_service = ProfileContextService(profile_db)
            current_context = await profile_service.get_profile_context(current_user.id)
            current_profile = cls._build_candidate_profile(
                current_user,
                current_context,
                relationship_status="self",
                is_existing_friend=False,
                can_invite_accountability=False,
                group_overlap_count=0,
                has_core_accountability_partner=current_has_core_partner,
            )
            contexts: list[ProfileContext] = []
            for user in candidates_by_id.values():
                contexts.append(await profile_service.get_profile_context(user.id))

        tuning = await cls._load_feedback_tuning(db, current_user.id)

        recommendations: list[FriendRecommendation] = []
        for user, context in zip(candidates_by_id.values(), contexts, strict=False):
            relationship_status = relationship_map.get(str(user.id), "none")
            is_existing_friend = relationship_status == FriendshipStatus.ACCEPTED.value
            can_invite = (
                target == FriendRecommendationTargetEnum.ACCOUNTABILITY
                and is_existing_friend
                and not current_has_core_partner
                and not partner_state_map.get(str(user.id), False)
            )
            candidate_profile = cls._build_candidate_profile(
                user,
                context,
                relationship_status=relationship_status,
                is_existing_friend=is_existing_friend,
                can_invite_accountability=can_invite,
                group_overlap_count=group_overlap_map.get(str(user.id), 0),
                has_core_accountability_partner=partner_state_map.get(str(user.id), False),
            )

            if target == FriendRecommendationTargetEnum.ACCOUNTABILITY:
                if relationship_status == FriendshipStatus.PENDING.value:
                    continue
                if candidate_profile.has_core_accountability_partner and not is_existing_friend:
                    continue
            elif relationship_status != "none":
                continue

            if strategy == FriendMatchStrategyEnum.COMPLEMENTARY:
                score_breakdown = cls._score_complementary(current_profile, candidate_profile)
            else:
                score_breakdown = cls._score_compatibility(current_profile, candidate_profile)

            score_breakdown = cls._apply_feedback_tuning(
                score_breakdown,
                tuning=tuning,
                strategy=strategy,
            )
            total_score = cls._weighted_total(score_breakdown)
            total_score *= cls._strategy_bias_multiplier(tuning, strategy)
            if is_existing_friend and target == FriendRecommendationTargetEnum.ACCOUNTABILITY:
                total_score = min(1.0, total_score + 0.06)

            reasons = cls._build_reasons(
                current_profile,
                candidate_profile,
                strategy=strategy,
            )
            summary = "；".join(reasons[:2]) if reasons else "适合作为下一位学习搭子"
            action = "send_friend_request"
            if candidate_profile.can_invite_accountability:
                action = "invite_accountability"
            elif candidate_profile.relationship_status == FriendshipStatus.PENDING.value:
                action = "pending"

            recommendations.append(
                FriendRecommendation(
                    user=UserBrief(
                        id=user.id,
                        username=user.username,
                        nickname=user.nickname,
                        avatar_url=user.avatar_url,
                        flame_level=user.flame_level,
                        flame_brightness=user.flame_brightness,
                        status=user.status.value,
                    ),
                    match_score=min(max(total_score, 0.0), 1.0),
                    match_reasons=reasons,
                    strategy=strategy.value,
                    target=target.value,
                    summary=summary,
                    relationship_status=candidate_profile.relationship_status,
                    is_existing_friend=candidate_profile.is_existing_friend,
                    can_invite_accountability=candidate_profile.can_invite_accountability,
                    recommended_action=action,
                    score_breakdown={
                        key: round(value, 3)
                        for key, value in score_breakdown.items()
                    },
                )
            )

        recommendations.sort(
            key=lambda item: (
                -item.match_score,
                item.recommended_action != "invite_accountability",
                item.user.nickname or item.user.username,
            )
        )
        return recommendations[:limit]

    @classmethod
    def _build_candidate_profile(
        cls,
        user: User,
        context: ProfileContext,
        *,
        relationship_status: str,
        is_existing_friend: bool,
        can_invite_accountability: bool,
        group_overlap_count: int,
        has_core_accountability_partner: bool,
    ) -> _CandidateProfile:
        preferences = context.preferences or {}
        active_subjects = _normalize_set(
            context.knowledge_summary.active_learning_subjects,
        )
        risk_buckets = {
            bucket
            for bucket in (
                _risk_bucket(signal)
                for signal in context.cognitive_summary.risk_signals
            )
            if bucket
        }
        pattern_names = _normalize_set(
            [pattern.pattern_name for pattern in context.cognitive_summary.active_patterns],
        )
        last_login_delta_days = 14.0
        if user.last_login_at:
            last_login_delta_days = max(
                0.0,
                (_utcnow() - user.last_login_at).total_seconds() / 86400.0,
            )
        recency_score = max(0.0, 1.0 - last_login_delta_days / 14.0)
        flame_score = min(1.0, max(0.0, float(user.flame_level or 0) / 20.0))
        group_score = min(1.0, group_overlap_count / 3.0)
        engagement_score = min(1.0, 0.5 * recency_score + 0.3 * flame_score + 0.2 * group_score)

        return _CandidateProfile(
            user=user,
            context=context,
            relationship_status=relationship_status,
            is_existing_friend=is_existing_friend,
            can_invite_accountability=can_invite_accountability,
            group_overlap_count=group_overlap_count,
            has_core_accountability_partner=has_core_accountability_partner,
            active_subjects=active_subjects,
            risk_buckets=risk_buckets,
            pattern_names=pattern_names,
            overall_mastery=float(context.knowledge_summary.overall_mastery or 0.0),
            engagement_score=engagement_score,
            depth_preference=float(preferences.get("depth_preference", user.depth_preference or 0.5)),
            curiosity_preference=float(preferences.get("curiosity_preference", user.curiosity_preference or 0.5)),
            focus_duration_preference=float(preferences.get("focus_duration_preference", 25)),
            learning_style=str(preferences.get("learning_style", "balanced")),
            feedback_style=str(preferences.get("feedback_style", "balanced")),
            dominant_pattern_type=context.cognitive_summary.dominant_pattern_type,
        )

    @classmethod
    def _score_compatibility(
        cls,
        current: _CandidateProfile,
        candidate: _CandidateProfile,
    ) -> dict[str, float]:
        subject_overlap = _jaccard(current.active_subjects, candidate.active_subjects)
        preference_alignment = sum(
            [
                _closeness(current.depth_preference, candidate.depth_preference, 1.0),
                _closeness(current.curiosity_preference, candidate.curiosity_preference, 1.0),
                _closeness(
                    current.focus_duration_preference,
                    candidate.focus_duration_preference,
                    60.0,
                ),
                1.0 if current.learning_style == candidate.learning_style else 0.45,
            ]
        ) / 4.0
        mastery_alignment = _closeness(current.overall_mastery, candidate.overall_mastery, 1.0)
        cognitive_alignment = max(
            _jaccard(current.risk_buckets, candidate.risk_buckets),
            1.0 if current.dominant_pattern_type and current.dominant_pattern_type == candidate.dominant_pattern_type else 0.35,
        )
        relationship_readiness = 1.0 if candidate.is_existing_friend else 0.55
        group_affinity = min(1.0, candidate.group_overlap_count / 3.0)

        return {
            "subject_overlap": subject_overlap * 0.28,
            "preference_alignment": preference_alignment * 0.24,
            "group_affinity": group_affinity * 0.14,
            "mastery_alignment": mastery_alignment * 0.12,
            "cognitive_alignment": cognitive_alignment * 0.10,
            "stability": candidate.engagement_score * 0.07,
            "relationship_readiness": relationship_readiness * 0.05,
        }

    @classmethod
    def _score_complementary(
        cls,
        current: _CandidateProfile,
        candidate: _CandidateProfile,
    ) -> dict[str, float]:
        needs = cls._infer_support_needs(current)
        strengths = cls._infer_strengths(candidate)
        support_strength = cls._support_fit_score(needs, strengths)
        subject_bridge = _jaccard(current.active_subjects, candidate.active_subjects)
        mastery_gap_help = min(
            1.0,
            max(0.0, candidate.overall_mastery - current.overall_mastery + 0.35),
        )
        preference_balance = sum(
            [
                min(1.0, candidate.depth_preference + (0.2 if current.depth_preference < 0.45 else 0.0)),
                min(1.0, candidate.engagement_score + (0.15 if "execution" in needs else 0.0)),
                min(
                    1.0,
                    _closeness(candidate.focus_duration_preference, 35.0, 35.0),
                ),
            ]
        ) / 3.0
        diversity = 1.0 if current.dominant_pattern_type != candidate.dominant_pattern_type else 0.45
        relationship_readiness = 1.0 if candidate.is_existing_friend else 0.5

        return {
            "support_strength": support_strength * 0.30,
            "subject_bridge": subject_bridge * 0.20,
            "mastery_gap_help": mastery_gap_help * 0.16,
            "preference_balance": preference_balance * 0.14,
            "stability": candidate.engagement_score * 0.12,
            "relationship_readiness": relationship_readiness * 0.04,
            "diversity": diversity * 0.04,
        }

    @classmethod
    def _infer_support_needs(cls, profile: _CandidateProfile) -> set[str]:
        needs = set(profile.risk_buckets)
        if profile.focus_duration_preference < 20:
            needs.add("execution")
        if profile.overall_mastery < 0.42:
            needs.add("mastery")
        if profile.depth_preference < 0.42:
            needs.add("planning")
        if not needs:
            needs.add("execution")
        return needs

    @classmethod
    def _infer_strengths(cls, profile: _CandidateProfile) -> dict[str, float]:
        return {
            "execution": min(
                1.0,
                0.55 * profile.engagement_score
                + 0.25 * _closeness(profile.focus_duration_preference, 35.0, 35.0)
                + 0.20 * (0.0 if "execution" in profile.risk_buckets else 1.0),
            ),
            "mastery": min(
                1.0,
                0.65 * profile.overall_mastery
                + 0.20 * profile.engagement_score
                + 0.15 * (0.0 if "mastery" in profile.risk_buckets else 1.0),
            ),
            "planning": min(
                1.0,
                0.55 * profile.depth_preference
                + 0.25 * _closeness(profile.focus_duration_preference, 35.0, 35.0)
                + 0.20 * (0.0 if "planning" in profile.risk_buckets else 1.0),
            ),
            "balance": min(
                1.0,
                0.45 * profile.curiosity_preference
                + 0.25 * (1.0 if profile.feedback_style == "balanced" else 0.55)
                + 0.30 * profile.engagement_score,
            ),
        }

    @classmethod
    def _support_fit_score(cls, needs: set[str], strengths: dict[str, float]) -> float:
        if not needs:
            return max(strengths.values()) if strengths else 0.5
        scores = [strengths.get(need, 0.45) for need in needs]
        return sum(scores) / len(scores)

    @classmethod
    def _weighted_total(cls, score_breakdown: dict[str, float]) -> float:
        return sum(score_breakdown.values())

    @classmethod
    def _apply_feedback_tuning(
        cls,
        score_breakdown: dict[str, float],
        *,
        tuning: dict[str, dict[str, float]],
        _strategy: FriendMatchStrategyEnum,
    ) -> dict[str, float]:
        feature_weights = tuning.get("feature_weights") or {}
        adjusted: dict[str, float] = {}
        for key, value in score_breakdown.items():
            multiplier = float(feature_weights.get(key, 1.0))
            adjusted[key] = value * multiplier
        total = sum(adjusted.values())
        if total > 1.0 and total > 0:
            scale = 1.0 / total
            adjusted = {key: value * scale for key, value in adjusted.items()}
        return adjusted

    @classmethod
    def _strategy_bias_multiplier(
        cls,
        tuning: dict[str, dict[str, float]],
        strategy: FriendMatchStrategyEnum,
    ) -> float:
        strategy_bias = tuning.get("strategy_bias") or {}
        return float(strategy_bias.get(strategy.value, 1.0))

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
        user_tuning = dict(tuning_root.get("friend") or {})
        global_adjustments = await RecommendationFeedbackService.get_global_adjustments(
            db,
            RecommendationItemTypeEnum.FRIEND,
        )
        merged_features = dict(user_tuning.get("feature_weights") or {})
        for key, value in (global_adjustments or {}).items():
            merged_features[key] = float(merged_features.get(key, 1.0)) * float(value)
        merged_strategy = dict(user_tuning.get("strategy_bias") or {})
        return {
            "feature_weights": merged_features,
            "strategy_bias": merged_strategy,
        }

    @classmethod
    def _build_reasons(
        cls,
        current: _CandidateProfile,
        candidate: _CandidateProfile,
        *,
        strategy: FriendMatchStrategyEnum,
    ) -> list[str]:
        reasons: list[str] = []
        subject_overlap = _jaccard(current.active_subjects, candidate.active_subjects)
        if candidate.is_existing_friend:
            reasons.append("你们已经是好友，建立责任伙伴关系会更顺手")

        if strategy == FriendMatchStrategyEnum.COMPLEMENTARY:
            needs = cls._infer_support_needs(current)
            strengths = cls._infer_strengths(candidate)
            if "execution" in needs and strengths.get("execution", 0.0) >= 0.62:
                reasons.append("TA 的执行节奏更稳定，适合做监督型伙伴")
            if "mastery" in needs and strengths.get("mastery", 0.0) >= 0.6:
                reasons.append("TA 在你当前关注主题上的掌握更稳，适合互相带动")
            if "planning" in needs and strengths.get("planning", 0.0) >= 0.6:
                reasons.append("TA 的规划和专注偏好更成熟，适合在关键节点监督和提醒你")
            if subject_overlap >= 0.35:
                reasons.append("你们主攻主题有交集，互补关系更容易落地")
        else:
            if subject_overlap >= 0.4:
                reasons.append("你们关注的学习主题高度重合")
            preference_alignment = (
                _closeness(current.depth_preference, candidate.depth_preference, 1.0)
                + _closeness(current.curiosity_preference, candidate.curiosity_preference, 1.0)
                + _closeness(current.focus_duration_preference, candidate.focus_duration_preference, 60.0)
            ) / 3.0
            if preference_alignment >= 0.7:
                reasons.append("学习节奏和专注偏好比较接近")
            if candidate.group_overlap_count > 0:
                reasons.append(f"你们在 {candidate.group_overlap_count} 个相同社群里有共同经历")
            if (
                current.dominant_pattern_type
                and current.dominant_pattern_type == candidate.dominant_pattern_type
            ):
                reasons.append("你们处理学习任务的方式比较契合")

        if not reasons:
            reasons.append("学习方向和活跃状态都比较合适")
        return reasons[:3]

    @classmethod
    async def _load_relationship_map(
        cls,
        db: AsyncSession,
        user_id: UUID,
    ) -> dict[str, str]:
        result = await db.execute(
            select(Friendship).where(
                or_(
                    Friendship.user_id == user_id,
                    Friendship.friend_id == user_id,
                )
            )
        )
        relationship_map: dict[str, str] = {}
        for friendship in result.scalars().all():
            other_id = friendship.friend_id if str(friendship.user_id) == str(user_id) else friendship.user_id
            relationship_map[str(other_id)] = (
                friendship.status.value if hasattr(friendship.status, "value") else str(friendship.status)
            )
        return relationship_map

    @classmethod
    async def _load_blocked_user_ids(
        cls,
        db: AsyncSession,
        user_id: UUID,
    ) -> set[str]:
        result = await db.execute(
            select(UserBlock).where(
                or_(
                    UserBlock.blocker_id == user_id,
                    UserBlock.blocked_id == user_id,
                ),
                UserBlock.not_deleted_filter(),
            )
        )
        blocked: set[str] = set()
        for row in result.scalars().all():
            if str(row.blocker_id) == str(user_id):
                blocked.add(str(row.blocked_id))
            else:
                blocked.add(str(row.blocker_id))
        return blocked

    @classmethod
    async def _load_group_overlap_counts(
        cls,
        db: AsyncSession,
        user_id: UUID,
    ) -> dict[str, int]:
        my_group_rows = await db.execute(
            select(GroupMember.group_id).where(
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter(),
            )
        )
        group_ids = [row[0] for row in my_group_rows.fetchall()]
        if not group_ids:
            return {}

        result = await db.execute(
            select(
                GroupMember.user_id,
                func.count(GroupMember.group_id),
            ).where(
                GroupMember.group_id.in_(group_ids),
                GroupMember.user_id != user_id,
                GroupMember.not_deleted_filter(),
            ).group_by(GroupMember.user_id)
        )
        return {str(user): int(count or 0) for user, count in result.all()}

    @classmethod
    async def _load_accountability_state(
        cls,
        db: AsyncSession,
        user_id: UUID,
    ) -> tuple[bool, dict[str, bool]]:
        result = await db.execute(
            select(AccountabilityPartnership).where(
                AccountabilityPartnership.slot_type == AccountabilitySlotType.CORE,
                AccountabilityPartnership.status.in_(
                    [AccountabilityStatus.PENDING, AccountabilityStatus.ACTIVE]
                ),
                AccountabilityPartnership.not_deleted_filter(),
            )
        )
        partner_state_map: dict[str, bool] = {}
        current_has_core_partner = False
        for partnership in result.scalars().all():
            participants = {
                str(partnership.initiator_id),
                str(partnership.partner_id),
            }
            if str(user_id) in participants:
                current_has_core_partner = True
            for participant_id in participants:
                if participant_id != str(user_id):
                    partner_state_map[participant_id] = True
        return current_has_core_partner, partner_state_map

    @classmethod
    async def _load_existing_friends(
        cls,
        db: AsyncSession,
        *,
        accepted_friend_ids: set[str],
        blocked_user_ids: set[str],
    ) -> list[User]:
        if not accepted_friend_ids:
            return []
        result = await db.execute(
            select(User).where(
                User.id.in_([UUID(user_id) for user_id in accepted_friend_ids if user_id not in blocked_user_ids]),
                User.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    @classmethod
    async def _load_public_candidates(
        cls,
        db: AsyncSession,
        current_user_id: UUID,
        *,
        accepted_friend_ids: set[str],  # noqa: ARG003
        pending_user_ids: set[str],
        blocked_user_ids: set[str],
    ) -> list[User]:
        excluded_ids = {
            str(current_user_id),
            *blocked_user_ids,
            *pending_user_ids,
        }
        result = await db.execute(
            select(User).where(
                User.is_active.is_(True),
                User.searchable_by == SearchVisibility.EVERYONE,
            ).order_by(
                User.last_login_at.desc().nullslast(),
                User.flame_level.desc(),
            ).limit(cls.MAX_CANDIDATES)
        )
        users = []
        for user in result.scalars().all():
            if str(user.id) in excluded_ids:
                continue
            users.append(user)
        return users

    @classmethod
    async def _table_exists(cls, db: AsyncSession, table_name: str) -> bool:
        connection = await db.connection()
        return await connection.run_sync(lambda sync_conn: inspect(sync_conn).has_table(table_name))

    @classmethod
    async def _get_cached_recommendations(
        cls,
        db: AsyncSession,
        user_id: UUID,
        recommendation_type: str,
    ) -> list[FriendRecommendation] | None:
        if not await cls._table_exists(db, RecommendationCache.__tablename__):
            return None
        result = await db.execute(
            select(RecommendationCache).where(
                RecommendationCache.user_id == user_id,
                RecommendationCache.recommendation_type == recommendation_type,
                RecommendationCache.expires_at > _utcnow(),
                RecommendationCache.not_deleted_filter(),
            ).order_by(RecommendationCache.generated_at.desc()).limit(1)
        )
        cache = result.scalar_one_or_none()
        if not cache:
            return None
        items = [
            FriendRecommendation.model_validate(item)
            for item in (cache.cached_recommendations or [])
        ]
        cache.hit_count += 1
        return items

    @classmethod
    async def _cache_recommendations(
        cls,
        db: AsyncSession,
        user_id: UUID,
        recommendation_type: str,
        items: list[FriendRecommendation],
    ) -> None:
        if not await cls._table_exists(db, RecommendationCache.__tablename__):
            return
        cache = RecommendationCache(
            user_id=user_id,
            recommendation_type=recommendation_type,
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
                RecommendationCache.recommendation_type.like("friend_match_v2:%"),
                RecommendationCache.not_deleted_filter(),
            )
        )
        for cache in result.scalars().all():
            await cache.delete(db, soft=True)
