from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from math import sqrt
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.community import Group, GroupMember
from app.models.recommendation import UserItemInteraction
from app.models.user import User
from app.schemas.community import (
    FriendRecommendationFeedbackRequest,
    GroupListItem,
    GroupRecommendationFeedbackRequest,
    GroupTypeEnum,
    RecommendationFeedbackInsight,
    RecommendationFeedbackPrompt,
    RecommendationFeedbackStageEnum,
    RecommendationItemTypeEnum,
    UserBrief,
)
from app.services.personalization.preference_service import PreferenceService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class RecommendationFeedbackService:
    """推荐反馈闭环：结构化问卷、自然语言解析、个体调优、全局洞察。"""

    TUNING_PREF_KEY = "recommendation_feedback_tuning"
    USER_MULTIPLIER_MIN = 0.65
    USER_MULTIPLIER_MAX = 1.45
    GLOBAL_MULTIPLIER_MIN = 0.90
    GLOBAL_MULTIPLIER_MAX = 1.10
    PROMPT_LOOKBACK_DAYS = 30
    INSIGHT_WINDOW_DAYS = 45

    FRIEND_FEATURES = {
        "subject_overlap",
        "preference_alignment",
        "group_affinity",
        "mastery_alignment",
        "cognitive_alignment",
        "stability",
        "relationship_readiness",
        "support_strength",
        "subject_bridge",
        "mastery_gap_help",
        "preference_balance",
        "diversity",
    }
    GROUP_FEATURES = {
        "tag_score",
        "friend_affinity",
        "activity",
        "quality",
        "freshness",
    }
    FRIEND_STAGE_ACTIONS = {
        "friend_match_view": {
            RecommendationFeedbackStageEnum.IMMEDIATE: timedelta(minutes=45),
        },
        "friend_match_friend_request": {
            RecommendationFeedbackStageEnum.FOLLOW_UP: timedelta(days=2),
            RecommendationFeedbackStageEnum.OUTCOME: timedelta(days=7),
        },
        "friend_match_accountability_invite": {
            RecommendationFeedbackStageEnum.FOLLOW_UP: timedelta(days=2),
            RecommendationFeedbackStageEnum.OUTCOME: timedelta(days=7),
        },
    }
    GROUP_STAGE_ACTIONS = {
        "reco_view": {
            RecommendationFeedbackStageEnum.IMMEDIATE: timedelta(minutes=45),
        },
        "reco_join": {
            RecommendationFeedbackStageEnum.FOLLOW_UP: timedelta(days=2),
            RecommendationFeedbackStageEnum.OUTCOME: timedelta(days=7),
        },
    }
    SIGNAL_POLARITY = {
        "want_more_similarity": "negative",
        "too_dissimilar": "negative",
        "want_more_complementarity": "negative",
        "too_similar": "negative",
        "prefer_existing_friend": "negative",
        "too_passive": "negative",
        "too_intense": "negative",
        "good_similarity": "positive",
        "good_complementarity": "positive",
        "trustworthy": "positive",
        "want_more_tag_match": "negative",
        "too_hot": "negative",
        "too_quiet": "negative",
        "want_more_niche": "negative",
        "want_more_popular": "negative",
        "atmosphere_negative": "negative",
        "atmosphere_positive": "positive",
        "good_interest_match": "positive",
    }

    @classmethod
    async def record_friend_feedback(
        cls,
        db: AsyncSession,
        current_user_id: UUID,
        payload: FriendRecommendationFeedbackRequest,
    ) -> None:
        from app.services.friend_match_service import FriendMatchService

        interaction = await FriendMatchService.record_feedback(db, current_user_id, payload)
        if interaction is None:
            return

        meta = await cls._decorate_interaction_meta(
            item_type=RecommendationItemTypeEnum.FRIEND,
            payload=payload,
            existing_meta=interaction.meta or {},
        )
        interaction.meta = meta
        await db.flush()

        if meta.get("has_structured_feedback"):
            await cls._apply_user_tuning(
                db,
                current_user_id,
                RecommendationItemTypeEnum.FRIEND,
                meta.get("tuning_deltas") or {},
            )
            await FriendMatchService._clear_cache(db, current_user_id)

    @classmethod
    async def record_group_feedback(
        cls,
        db: AsyncSession,
        current_user_id: UUID,
        payload: GroupRecommendationFeedbackRequest,
    ) -> None:
        from app.services.group_recommendation_service import GroupRecommendationService

        interaction = await GroupRecommendationService.record_feedback(db, current_user_id, payload)
        if interaction is None:
            return

        meta = await cls._decorate_interaction_meta(
            item_type=RecommendationItemTypeEnum.GROUP,
            payload=payload,
            existing_meta=interaction.meta or {},
        )
        interaction.meta = meta
        await db.flush()

        if meta.get("has_structured_feedback"):
            await cls._apply_user_tuning(
                db,
                current_user_id,
                RecommendationItemTypeEnum.GROUP,
                meta.get("tuning_deltas") or {},
            )
            await GroupRecommendationService._clear_cache(db, current_user_id)

    @classmethod
    async def get_pending_prompts(
        cls,
        db: AsyncSession,
        current_user_id: UUID,
        *,
        item_type: RecommendationItemTypeEnum | None = None,
        limit: int = 20,
    ) -> list[RecommendationFeedbackPrompt]:
        interactions = await cls._load_recent_interactions(
            db,
            current_user_id,
            days=cls.PROMPT_LOOKBACK_DAYS,
        )
        if not interactions:
            return []

        now = _utcnow()
        completed_prompt_ids = {
            str((interaction.meta or {}).get("prompt_id"))
            for interaction in interactions
            if (interaction.meta or {}).get("has_structured_feedback")
            and (interaction.meta or {}).get("prompt_id")
        }
        completed_stage_keys = {
            (
                cls._interaction_item_type(interaction).value,
                str(interaction.item_id),
                str((interaction.meta or {}).get("stage")),
            )
            for interaction in interactions
            if cls._interaction_item_type(interaction) is not None
            and (interaction.meta or {}).get("has_structured_feedback")
            and (interaction.meta or {}).get("stage")
        }

        prompt_specs: list[tuple[UserItemInteraction, RecommendationItemTypeEnum, RecommendationFeedbackStageEnum, datetime]] = []
        for interaction in interactions:
            derived_type = cls._interaction_item_type(interaction)
            if derived_type is None:
                continue
            if item_type and derived_type != item_type:
                continue

            stage_map = cls.FRIEND_STAGE_ACTIONS if derived_type == RecommendationItemTypeEnum.FRIEND else cls.GROUP_STAGE_ACTIONS
            for stage, delay in stage_map.get(interaction.interaction_type, {}).items():
                due_at = interaction.created_at + delay
                if due_at > now:
                    continue
                prompt_id = cls._build_prompt_id(derived_type, interaction.item_id, stage, interaction.id)
                if prompt_id in completed_prompt_ids:
                    continue
                if (derived_type.value, str(interaction.item_id), stage.value) in completed_stage_keys:
                    continue
                prompt_specs.append((interaction, derived_type, stage, due_at))

        prompt_specs.sort(key=lambda item: item[3], reverse=True)
        prompt_specs = prompt_specs[:limit]
        if not prompt_specs:
            return []

        friend_ids = {
            interaction.item_id
            for interaction, derived_type, _, _ in prompt_specs
            if derived_type == RecommendationItemTypeEnum.FRIEND
        }
        group_ids = {
            interaction.item_id
            for interaction, derived_type, _, _ in prompt_specs
            if derived_type == RecommendationItemTypeEnum.GROUP
        }
        user_map = await cls._load_user_briefs(db, friend_ids)
        group_map = await cls._load_group_snapshots(db, group_ids)

        prompts: list[RecommendationFeedbackPrompt] = []
        for interaction, derived_type, stage, due_at in prompt_specs:
            meta = interaction.meta or {}
            prompts.append(
                RecommendationFeedbackPrompt(
                    prompt_id=cls._build_prompt_id(derived_type, interaction.item_id, stage, interaction.id),
                    item_type=derived_type,
                    item_id=interaction.item_id,
                    stage=stage,
                    trigger_action=interaction.interaction_type,
                    title=cls._build_prompt_title(derived_type, stage),
                    subtitle=cls._build_prompt_subtitle(derived_type, stage, meta),
                    due_at=due_at,
                    strategy=meta.get("strategy"),
                    target=meta.get("target"),
                    user=user_map.get(interaction.item_id),
                    group=group_map.get(interaction.item_id),
                    reason_tags=list(meta.get("reason_types") or [])[:4],
                )
            )
        return prompts

    @classmethod
    async def get_feedback_insights(
        cls,
        db: AsyncSession,
        current_user_id: UUID,
        *,
        item_type: RecommendationItemTypeEnum | None = None,
        days: int = 30,
    ) -> list[RecommendationFeedbackInsight]:
        item_types = [item_type] if item_type else [
            RecommendationItemTypeEnum.FRIEND,
            RecommendationItemTypeEnum.GROUP,
        ]
        insights: list[RecommendationFeedbackInsight] = []
        for current_type in item_types:
            interactions = [
                interaction
                for interaction in await cls._load_recent_interactions(db, current_user_id, days=days)
                if cls._interaction_item_type(interaction) == current_type
                and (interaction.meta or {}).get("has_structured_feedback")
            ]
            average_scores = cls._average_questionnaire_scores(interactions)
            top_positive, top_negative = cls._rank_signals(interactions)
            user_tuning = await cls.get_user_tuning(db, current_user_id, current_type)
            global_adjustments = await cls.get_global_adjustments(db, current_type, days=days)
            insights.append(
                RecommendationFeedbackInsight(
                    item_type=current_type,
                    recent_feedback_count=len(interactions),
                    average_scores=average_scores,
                    top_positive_signals=top_positive,
                    top_negative_signals=top_negative,
                    user_tuning=user_tuning,
                    global_adjustments=global_adjustments,
                )
            )
        return insights

    @classmethod
    async def get_user_tuning(
        cls,
        db: AsyncSession,
        user_id: UUID,
        item_type: RecommendationItemTypeEnum,
    ) -> dict[str, Any]:
        preference_service = PreferenceService(db, cache_service.redis)
        prefs = await preference_service.get_preferences(user_id)
        tuning_root = dict((prefs.explicit or {}).get(cls.TUNING_PREF_KEY) or {})
        return dict(tuning_root.get(item_type.value) or {})

    @classmethod
    async def get_global_adjustments(
        cls,
        db: AsyncSession,
        item_type: RecommendationItemTypeEnum,
        *,
        days: int = 30,
    ) -> dict[str, float]:
        cutoff = _utcnow() - timedelta(days=days)
        result = await db.execute(
            select(UserItemInteraction).where(
                UserItemInteraction.created_at >= cutoff,
                UserItemInteraction.not_deleted_filter(),
            )
        )
        relevant = [
            interaction
            for interaction in result.scalars().all()
            if cls._interaction_item_type(interaction) == item_type
            and (interaction.meta or {}).get("has_structured_feedback")
        ]
        if not relevant:
            return {}

        totals: dict[str, float] = defaultdict(float)
        counts: dict[str, int] = defaultdict(int)
        for interaction in relevant:
            delta_block = dict((interaction.meta or {}).get("tuning_deltas") or {})
            feature_block = dict(delta_block.get("feature_weights") or {})
            for key, value in feature_block.items():
                totals[key] += float(value)
                counts[key] += 1

        adjustments: dict[str, float] = {}
        for key, total in totals.items():
            mean_delta = total / max(counts.get(key, 1), 1)
            adjustments[key] = round(
                cls._clamp(1.0 + mean_delta * 0.45, cls.GLOBAL_MULTIPLIER_MIN, cls.GLOBAL_MULTIPLIER_MAX),
                4,
            )
        return adjustments

    @classmethod
    async def _decorate_interaction_meta(
        cls,
        *,
        item_type: RecommendationItemTypeEnum,
        payload: FriendRecommendationFeedbackRequest | GroupRecommendationFeedbackRequest,
        existing_meta: dict[str, Any],
    ) -> dict[str, Any]:
        questionnaire = cls._extract_questionnaire(payload)
        parsed_signals = cls._parse_feedback_signals(
            item_type=item_type,
            free_text=payload.free_text,
            issues=payload.selected_issues,
            strengths=payload.selected_strengths,
        )
        tuning_deltas = cls._build_tuning_deltas(
            item_type=item_type,
            payload=payload,
            parsed_signals=parsed_signals,
        )
        has_structured_feedback = bool(
            questionnaire
            or payload.selected_issues
            or payload.selected_strengths
            or payload.free_text
            or payload.prompt_id
        )
        meta = dict(existing_meta or {})
        meta.update(
            {
                "questionnaire": questionnaire,
                "prompt_id": payload.prompt_id,
                "stage": payload.stage.value,
                "questionnaire_version": payload.questionnaire_version,
                "selected_issues": list(payload.selected_issues or []),
                "selected_strengths": list(payload.selected_strengths or []),
                "free_text": payload.free_text,
                "parsed_signals": parsed_signals,
                "tuning_deltas": tuning_deltas,
                "has_structured_feedback": has_structured_feedback,
            }
        )
        return meta

    @classmethod
    def _extract_questionnaire(
        cls,
        payload: FriendRecommendationFeedbackRequest | GroupRecommendationFeedbackRequest,
    ) -> dict[str, int]:
        questionnaire: dict[str, int] = {}
        for key in (
            "overall_score",
            "relevance_score",
            "explanation_score",
            "actionability_score",
            "similarity_score",
            "complementary_score",
            "comfort_score",
            "interest_match_score",
            "activity_score",
            "atmosphere_score",
        ):
            value = getattr(payload, key, None)
            if value is not None:
                questionnaire[key] = int(value)
        return questionnaire

    @classmethod
    def _parse_feedback_signals(
        cls,
        *,
        item_type: RecommendationItemTypeEnum,
        free_text: str | None,
        issues: list[str],
        strengths: list[str],
    ) -> list[str]:
        text = " ".join([free_text or "", *issues, *strengths]).lower()
        signals: set[str] = set()

        if item_type == RecommendationItemTypeEnum.FRIEND:
            if any(token in text for token in ("不够相似", "不太相似", "差异太大", "不像我", "similarity low", "too different")):
                signals.add("too_dissimilar")
            if any(token in text for token in ("更像我", "更契合", "更相似", "similar", "契合度")):
                signals.add("want_more_similarity")
            if any(token in text for token in ("太像了", "同质化", "互补", "能监督我", "补位", "complement")):
                signals.add("want_more_complementarity")
            if any(token in text for token in ("太被动", "不够主动", "催不动", "passive")):
                signals.add("too_passive")
            if any(token in text for token in ("压迫", "太强势", "太 intense", "太卷")):
                signals.add("too_intense")
            if any(token in text for token in ("熟人", "已经认识", "好友", "existing friend")):
                signals.add("prefer_existing_friend")
            if any(token in text for token in ("很相似", "挺像", "同频", "same pace")):
                signals.add("good_similarity")
            if any(token in text for token in ("很互补", "互相带动", "监督效果好", "complementary")):
                signals.add("good_complementarity")
            if any(token in text for token in ("舒服", "信任", "靠谱", "trust")):
                signals.add("trustworthy")
        else:
            if any(token in text for token in ("标签不准", "兴趣不匹配", "不感兴趣", "不对口", "tag mismatch")):
                signals.add("want_more_tag_match")
            if any(token in text for token in ("太火", "太吵", "太多人", "太卷", "too active", "too crowded")):
                signals.add("too_hot")
            if any(token in text for token in ("太安静", "没人说话", "冷清", "too quiet")):
                signals.add("too_quiet")
            if any(token in text for token in ("小众", "niche", "探索")):
                signals.add("want_more_niche")
            if any(token in text for token in ("热门", "人多", "活跃一些", "popular")):
                signals.add("want_more_popular")
            if any(token in text for token in ("氛围好", "友善", "积极", "welcome")):
                signals.add("atmosphere_positive")
            if any(token in text for token in ("氛围差", "攻击性", "不友好", "negative atmosphere")):
                signals.add("atmosphere_negative")
            if any(token in text for token in ("兴趣很对口", "正好想找", "match my interest")):
                signals.add("good_interest_match")

        return sorted(signals)

    @classmethod
    def _build_tuning_deltas(
        cls,
        *,
        item_type: RecommendationItemTypeEnum,
        payload: FriendRecommendationFeedbackRequest | GroupRecommendationFeedbackRequest,
        parsed_signals: list[str],
    ) -> dict[str, Any]:
        feature_weights: dict[str, float] = defaultdict(float)
        strategy_bias: dict[str, float] = defaultdict(float)

        def bump_feature(*keys: str, delta: float) -> None:
            for key in keys:
                feature_weights[key] += delta

        def bump_strategy(*keys: str, delta: float) -> None:
            for key in keys:
                strategy_bias[key] += delta

        if item_type == RecommendationItemTypeEnum.FRIEND:
            if getattr(payload, "relevance_score", None) and payload.relevance_score <= 2:
                bump_feature("subject_overlap", "preference_alignment", delta=0.08)
            if getattr(payload, "similarity_score", None) and payload.similarity_score <= 2:
                bump_feature("subject_overlap", "preference_alignment", "cognitive_alignment", delta=0.08)
                bump_strategy("compatibility", delta=0.06)
            if getattr(payload, "complementary_score", None) and payload.complementary_score <= 2:
                bump_feature("support_strength", "mastery_gap_help", "diversity", delta=0.08)
                bump_strategy("complementary", delta=0.06)
            if getattr(payload, "comfort_score", None) and payload.comfort_score <= 2:
                bump_feature("relationship_readiness", "stability", delta=0.06)
            if getattr(payload, "overall_score", None) and payload.overall_score >= 4 and payload.strategy.value == "compatibility":
                bump_strategy("compatibility", delta=0.03)
            if getattr(payload, "overall_score", None) and payload.overall_score >= 4 and payload.strategy.value == "complementary":
                bump_strategy("complementary", delta=0.03)

            for signal in parsed_signals:
                if signal in {"want_more_similarity", "too_dissimilar"}:
                    bump_feature("subject_overlap", "preference_alignment", "mastery_alignment", delta=0.10)
                    bump_strategy("compatibility", delta=0.07)
                elif signal in {"want_more_complementarity", "too_similar"}:
                    bump_feature("support_strength", "diversity", "mastery_gap_help", delta=0.10)
                    bump_strategy("complementary", delta=0.07)
                elif signal == "prefer_existing_friend":
                    bump_feature("relationship_readiness", delta=0.08)
                elif signal == "too_passive":
                    bump_feature("stability", delta=0.08)
                elif signal == "too_intense":
                    bump_feature("stability", delta=-0.05)
                elif signal == "good_similarity":
                    bump_feature("subject_overlap", "preference_alignment", delta=0.04)
                elif signal == "good_complementarity":
                    bump_feature("support_strength", "diversity", delta=0.04)
                elif signal == "trustworthy":
                    bump_feature("relationship_readiness", "stability", delta=0.04)
        else:
            if getattr(payload, "interest_match_score", None) and payload.interest_match_score <= 2:
                bump_feature("tag_score", delta=0.10)
            if getattr(payload, "activity_score", None) and payload.activity_score <= 2:
                bump_feature("activity", delta=0.05)
            if getattr(payload, "atmosphere_score", None) and payload.atmosphere_score <= 2:
                bump_feature("quality", delta=0.04)
            if getattr(payload, "overall_score", None) and payload.overall_score >= 4:
                bump_feature("quality", delta=0.02)

            for signal in parsed_signals:
                if signal == "want_more_tag_match":
                    bump_feature("tag_score", delta=0.12)
                elif signal == "too_hot":
                    bump_feature("activity", delta=-0.08)
                    bump_feature("freshness", delta=0.04)
                elif signal == "too_quiet":
                    bump_feature("activity", delta=0.10)
                elif signal == "want_more_niche":
                    bump_feature("freshness", delta=0.08)
                    bump_feature("quality", delta=-0.03)
                elif signal == "want_more_popular":
                    bump_feature("quality", "activity", delta=0.07)
                elif signal == "atmosphere_positive":
                    bump_feature("quality", "friend_affinity", delta=0.04)
                elif signal == "atmosphere_negative":
                    bump_feature("quality", delta=-0.06)
                elif signal == "good_interest_match":
                    bump_feature("tag_score", delta=0.04)

        result: dict[str, Any] = {}
        if feature_weights:
            result["feature_weights"] = {key: round(value, 4) for key, value in feature_weights.items() if abs(value) > 0}
        if strategy_bias:
            result["strategy_bias"] = {key: round(value, 4) for key, value in strategy_bias.items() if abs(value) > 0}
        return result

    @classmethod
    async def _apply_user_tuning(
        cls,
        db: AsyncSession,
        user_id: UUID,
        item_type: RecommendationItemTypeEnum,
        deltas: dict[str, Any],
    ) -> None:
        if not deltas:
            return

        preference_service = PreferenceService(db, cache_service.redis)
        prefs = await preference_service.get_preferences(user_id)
        explicit = dict(prefs.explicit or {})
        tuning_root = dict(explicit.get(cls.TUNING_PREF_KEY) or {})
        current = dict(tuning_root.get(item_type.value) or {})
        feedback_count = int(current.get("feedback_count") or 0)
        alpha = max(0.12, 0.35 / sqrt(feedback_count + 1))

        feature_weights = cls._merge_weight_block(
            current.get("feature_weights"),
            deltas.get("feature_weights"),
            alpha=alpha,
            minimum=cls.USER_MULTIPLIER_MIN,
            maximum=cls.USER_MULTIPLIER_MAX,
        )
        merged: dict[str, Any] = {
            "feature_weights": feature_weights,
            "feedback_count": feedback_count + 1,
            "last_feedback_at": _utcnow().isoformat(),
        }

        if item_type == RecommendationItemTypeEnum.FRIEND:
            merged["strategy_bias"] = cls._merge_weight_block(
                current.get("strategy_bias"),
                deltas.get("strategy_bias"),
                alpha=alpha,
                minimum=cls.USER_MULTIPLIER_MIN,
                maximum=cls.USER_MULTIPLIER_MAX,
            )

        tuning_root[item_type.value] = merged
        explicit[cls.TUNING_PREF_KEY] = tuning_root
        await preference_service.update_explicit(user_id, {cls.TUNING_PREF_KEY: tuning_root})

    @classmethod
    def _merge_weight_block(
        cls,
        existing: dict[str, Any] | None,
        deltas: dict[str, Any] | None,
        *,
        alpha: float,
        minimum: float,
        maximum: float,
    ) -> dict[str, float]:
        base = {str(key): float(value) for key, value in dict(existing or {}).items()}
        for key, delta in dict(deltas or {}).items():
            current = float(base.get(key, 1.0))
            base[key] = round(cls._clamp(current + float(delta) * alpha, minimum, maximum), 4)
        return base

    @classmethod
    async def _load_recent_interactions(
        cls,
        db: AsyncSession,
        user_id: UUID,
        *,
        days: int,
    ) -> list[UserItemInteraction]:
        cutoff = _utcnow() - timedelta(days=days)
        result = await db.execute(
            select(UserItemInteraction)
            .where(
                UserItemInteraction.user_id == user_id,
                UserItemInteraction.created_at >= cutoff,
                UserItemInteraction.not_deleted_filter(),
            )
            .order_by(UserItemInteraction.created_at.desc())
        )
        return list(result.scalars().all())

    @classmethod
    def _interaction_item_type(cls, interaction: UserItemInteraction) -> RecommendationItemTypeEnum | None:
        if interaction.item_type == "friend_candidate":
            return RecommendationItemTypeEnum.FRIEND
        if interaction.item_type == "group":
            return RecommendationItemTypeEnum.GROUP
        return None

    @classmethod
    async def _load_user_briefs(
        cls,
        db: AsyncSession,
        user_ids: set[UUID],
    ) -> dict[UUID, UserBrief]:
        if not user_ids:
            return {}
        result = await db.execute(select(User).where(User.id.in_(list(user_ids))))
        briefs: dict[UUID, UserBrief] = {}
        for user in result.scalars().all():
            briefs[user.id] = UserBrief(
                id=user.id,
                username=user.username,
                nickname=user.nickname,
                avatar_url=user.avatar_url,
                flame_level=user.flame_level,
                flame_brightness=user.flame_brightness,
                status=user.status.value,
            )
        return briefs

    @classmethod
    async def _load_group_snapshots(
        cls,
        db: AsyncSession,
        group_ids: set[UUID],
    ) -> dict[UUID, GroupListItem]:
        if not group_ids:
            return {}

        group_result = await db.execute(select(Group).where(Group.id.in_(list(group_ids))))
        groups = list(group_result.scalars().all())
        count_result = await db.execute(
            select(GroupMember.group_id, func.count(GroupMember.id))
            .where(
                GroupMember.group_id.in_(list(group_ids)),
                GroupMember.not_deleted_filter(),
            )
            .group_by(GroupMember.group_id)
        )
        member_counts = {group_id: int(count) for group_id, count in count_result.all()}
        now = _utcnow()
        snapshots: dict[UUID, GroupListItem] = {}
        for group in groups:
            days_remaining = None
            if group.deadline:
                days_remaining = max(0, (group.deadline - now).days)
            snapshots[group.id] = GroupListItem(
                id=group.id,
                name=group.name,
                description=group.description,
                type=GroupTypeEnum(group.type.value),
                member_count=member_counts.get(group.id, 0),
                total_flame_power=group.total_flame_power,
                today_checkin_count=group.today_checkin_count,
                deadline=group.deadline,
                days_remaining=days_remaining,
                focus_tags=group.focus_tags or [],
                sprint_goal=group.sprint_goal,
                is_public=group.is_public,
                join_requires_approval=group.join_requires_approval,
                my_role=None,
            )
        return snapshots

    @classmethod
    def _build_prompt_id(
        cls,
        item_type: RecommendationItemTypeEnum,
        item_id: UUID,
        stage: RecommendationFeedbackStageEnum,
        source_interaction_id: UUID,
    ) -> str:
        return f"{item_type.value}:{item_id}:{stage.value}:{source_interaction_id}"

    @classmethod
    def _build_prompt_title(
        cls,
        item_type: RecommendationItemTypeEnum,
        stage: RecommendationFeedbackStageEnum,
    ) -> str:
        if item_type == RecommendationItemTypeEnum.FRIEND:
            if stage == RecommendationFeedbackStageEnum.IMMEDIATE:
                return "这位推荐伙伴符合你的期待吗？"
            if stage == RecommendationFeedbackStageEnum.FOLLOW_UP:
                return "这次好友/伙伴推荐落地得顺利吗？"
            return "这位推荐伙伴后来真的帮到你了吗？"
        if stage == RecommendationFeedbackStageEnum.IMMEDIATE:
            return "这个社群推荐对你有吸引力吗？"
        if stage == RecommendationFeedbackStageEnum.FOLLOW_UP:
            return "加入后，这个社群和推荐描述一致吗？"
        return "这次社群推荐长期来看值不值得？"

    @classmethod
    def _build_prompt_subtitle(
        cls,
        item_type: RecommendationItemTypeEnum,
        stage: RecommendationFeedbackStageEnum,
        meta: dict[str, Any],
    ) -> str:
        if item_type == RecommendationItemTypeEnum.FRIEND:
            if stage == RecommendationFeedbackStageEnum.IMMEDIATE:
                return "告诉我们契合度、互补性和舒适度是否真的对得上。"
            if stage == RecommendationFeedbackStageEnum.FOLLOW_UP:
                return "这会直接调节你后续的责任伙伴/好友推荐权重。"
            return "长期反馈会沉淀成你的个性化匹配偏好。"
        strategy = meta.get("strategy")
        if stage == RecommendationFeedbackStageEnum.IMMEDIATE:
            return "从兴趣、活跃度和氛围几个维度给它打分。"
        if strategy:
            return f"我们会结合你对 {strategy} 推荐的反馈做后续调优。"
        return "你的加入体验会反作用到后续社群推荐。"

    @classmethod
    def _average_questionnaire_scores(
        cls,
        interactions: list[UserItemInteraction],
    ) -> dict[str, float]:
        totals: dict[str, float] = defaultdict(float)
        counts: dict[str, int] = defaultdict(int)
        for interaction in interactions:
            questionnaire = dict((interaction.meta or {}).get("questionnaire") or {})
            for key, value in questionnaire.items():
                totals[key] += float(value)
                counts[key] += 1
        return {
            key: round(totals[key] / max(counts[key], 1), 3)
            for key in sorted(totals.keys())
        }

    @classmethod
    def _rank_signals(
        cls,
        interactions: list[UserItemInteraction],
    ) -> tuple[list[str], list[str]]:
        positive_counter: Counter[str] = Counter()
        negative_counter: Counter[str] = Counter()
        for interaction in interactions:
            meta = interaction.meta or {}
            for signal in meta.get("parsed_signals") or []:
                polarity = cls.SIGNAL_POLARITY.get(signal, "negative")
                if polarity == "positive":
                    positive_counter[signal] += 1
                else:
                    negative_counter[signal] += 1
            for signal in meta.get("selected_strengths") or []:
                positive_counter[str(signal)] += 1
            for signal in meta.get("selected_issues") or []:
                negative_counter[str(signal)] += 1
        return (
            [key for key, _ in positive_counter.most_common(5)],
            [key for key, _ in negative_counter.most_common(5)],
        )

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
