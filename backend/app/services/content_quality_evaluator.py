"""
Content Quality Evaluator
内容质量评估器

Automatically evaluates response quality to determine if it should be added to the seed library.
"""
from datetime import UTC, datetime, timedelta
import inspect
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.response_feedback import ResponseFeedback
from app.models.seed_content import SeedItem, SeedLibrary


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ContentQualityEvaluator:
    """Evaluates content quality for automatic seed library inclusion"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    async def _extract_scalars(result: Any) -> list[Any]:
        scalars_obj = result.scalars()
        if inspect.isawaitable(scalars_obj):
            scalars_obj = await scalars_obj
        rows = scalars_obj.all()
        if inspect.isawaitable(rows):
            rows = await rows
        return list(rows)

    @staticmethod
    def _is_positive(feedback: ResponseFeedback) -> bool:
        explicit = getattr(feedback, "is_positive", None)
        if explicit is not None:
            return bool(explicit)
        feedback_type = getattr(feedback, "feedback_type", None)
        return feedback_type == ResponseFeedback.FEEDBACK_UP

    @staticmethod
    def _action(feedback: ResponseFeedback) -> str | None:
        action = getattr(feedback, "action", None)
        if action is not None:
            return action
        return getattr(feedback, "action_taken", None)

    @staticmethod
    def _rating(feedback: ResponseFeedback) -> int | None:
        rating = getattr(feedback, "rating", None)
        if rating is not None:
            return rating
        if getattr(feedback, "feedback_type", None) == ResponseFeedback.FEEDBACK_UP:
            return 5
        if getattr(feedback, "feedback_type", None) == ResponseFeedback.FEEDBACK_DOWN:
            return 1
        return None

    async def evaluate_response_quality(
        self,
        response_id: str,
    ) -> dict[str, Any]:
        """
        评估回答质量

        Args:
            response_id: 回复ID

        Returns:
            Dict with quality metrics and recommendation
        """
        # 1. Get feedback for this response
        result = await self.db.execute(
            select(ResponseFeedback).where(
                ResponseFeedback.response_id == response_id
            )
        )
        feedback_records = await self._extract_scalars(result)

        if not feedback_records:
            return {
                'response_id': response_id,
                'quality_score': 0.0,
                'should_seed': False,
                'reason': 'No feedback found',
            }

        # 2. Calculate quality score
        quality_score = await self._calculate_quality_score(feedback_records)

        # 3. Check seeding criteria
        should_seed, reason = await self._check_seeding_criteria(
            quality_score,
            feedback_records,
        )

        return {
            'response_id': response_id,
            'quality_score': quality_score,
            'should_seed': should_seed,
            'reason': reason,
            'feedback_count': len(feedback_records),
            'positive_count': sum(1 for f in feedback_records if self._is_positive(f)),
            'negative_count': sum(1 for f in feedback_records if not self._is_positive(f)),
            'metrics': {
                'avg_rating': (
                    sum(ratings) / len(ratings)
                    if (ratings := [r for r in (self._rating(f) for f in feedback_records) if r is not None])
                    else None
                ),
                'save_count': sum(1 for f in feedback_records if self._action(f) == 'save'),
                'share_count': sum(1 for f in feedback_records if self._action(f) == 'share'),
                'revisit_count': sum(1 for f in feedback_records if self._action(f) == 'revisit'),
            },
        }

    async def _calculate_quality_score(
        self,
        feedback_records: list[ResponseFeedback],
    ) -> float:
        """
        计算综合质量评分 (0-10)

        Args:
            feedback_records: 反馈记录列表

        Returns:
            float: 质量评分
        """
        if not feedback_records:
            return 0.0

        # 1. Positive feedback ratio (40% weight)
        positive_count = sum(1 for f in feedback_records if self._is_positive(f))
        positive_ratio = positive_count / len(feedback_records)
        score_positive = positive_ratio * 4.0

        # 2. Average rating (30% weight)
        ratings = [r for r in (self._rating(f) for f in feedback_records) if r is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        score_rating = (avg_rating / 5.0) * 3.0

        # 3. Action engagement (30% weight)
        # High-value actions: save > share > revisit
        action_scores = {'save': 3.0, 'share': 2.0, 'revisit': 1.0}
        total_action_score = 0.0
        for feedback in feedback_records:
            action = self._action(feedback)
            if action:
                total_action_score += action_scores.get(action, 0)

        # Normalize action score (assuming max 10 actions)
        score_action = min(total_action_score, 10.0) * 0.3

        # Combined score
        quality_score = score_positive + score_rating + score_action

        return min(10.0, max(0.0, quality_score))

    async def _check_seeding_criteria(
        self,
        quality_score: float,
        feedback_records: list[ResponseFeedback],
    ) -> tuple[bool, str]:
        """
        检查是否符合入库标准

        Args:
            quality_score: 质量评分
            feedback_records: 反馈记录

        Returns:
            tuple[bool, str]: (是否入库, 原因)
        """
        # Minimum feedback threshold
        if len(feedback_records) < 3:
            return False, f"Insufficient feedback ({len(feedback_records)} < 3)"

        # Minimum quality score
        if quality_score < 7.0:
            return False, f"Quality score too low ({quality_score:.1f} < 7.0)"

        # Positive feedback ratio
        positive_count = sum(1 for f in feedback_records if self._is_positive(f))
        positive_ratio = positive_count / len(feedback_records)

        if positive_ratio < 0.7:
            return False, f"Positive feedback ratio too low ({positive_ratio:.1%} < 70%)"

        # Check for recent activity
        recent_cutoff = _utcnow() - timedelta(days=30)
        recent_feedback = [f for f in feedback_records if f.created_at and f.created_at >= recent_cutoff]

        if len(recent_feedback) < 2:
            return False, f"Insufficient recent activity ({len(recent_feedback)} < 2 in last 30 days)"

        return True, "Meets all quality criteria"

    async def find_candidate_responses(
        self,
        min_quality_score: float = 7.0,
        min_feedback_count: int = 3,
        days_back: int = 30,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        查找候选入库的回复

        Args:
            min_quality_score: 最低质量评分
            min_feedback_count: 最少反馈数量
            days_back: 回溯天数
            limit: 返回数量限制

        Returns:
            list[Dict]: 候选回复列表
        """
        cutoff_date = _utcnow() - timedelta(days=days_back)

        # Find responses with sufficient feedback
        # Group by response_id and count

        feedback_count_subq = (
            select(
                ResponseFeedback.response_id.label('response_id'),
                func.count(ResponseFeedback.id).label('feedback_count'),
                func.sum(
                    case(
                        (ResponseFeedback.feedback_type == ResponseFeedback.FEEDBACK_UP, 1),
                        else_=0,
                    )
                ).label('positive_count'),
            )
            .where(ResponseFeedback.created_at >= cutoff_date)
            .group_by(ResponseFeedback.response_id)
            .having(func.count(ResponseFeedback.id) >= min_feedback_count)
            .subquery()
        )

        # Join with feedback to get full records
        result = await self.db.execute(
            select(
                feedback_count_subq.c.response_id,
                feedback_count_subq.c.feedback_count,
                feedback_count_subq.c.positive_count,
            )
            .order_by(feedback_count_subq.c.positive_count.desc())
            .limit(limit)
        )

        candidates = []
        rows = result.all()
        if inspect.isawaitable(rows):
            rows = await rows
        for row in rows:
            response_id, count, positive_count = row
            positive_ratio = positive_count / count if count > 0 else 0
            quality_score = min(10.0, (positive_ratio * 8.0) + min(count, 10) * 0.2)

            if quality_score >= min_quality_score:
                candidates.append({
                    'response_id': str(response_id),
                    'quality_score': quality_score,
                    'feedback_count': count,
                    'positive_count': positive_count,
                    'positive_ratio': positive_ratio,
                    'created_at': None,
                })

        return candidates

    async def auto_seed_to_library(
        self,
        response_id: str,
        target_library_id: str | None = None,
    ) -> str | None:
        """
        自动将高质量回复添加到种子库

        Args:
            response_id: 回复ID
            target_library_id: 目标种子库ID（None则创建新的测试库）

        Returns:
            Optional[str]: 种子项ID，如果失败返回None
        """
        # 1. Evaluate quality
        evaluation = await self.evaluate_response_quality(response_id)

        if not evaluation['should_seed']:
            logger.info(
                f"Response {response_id} not suitable for seeding: {evaluation['reason']}"
            )
            return None

        # 2. Get or create target library
        if target_library_id is None:
            # Find or create test library
            target_library_id = await self._get_or_create_test_library()

        # 3. Create seed item
        try:
            target_library_uuid = UUID(str(target_library_id))
            item = SeedItem(
                library_id=target_library_uuid,
                item_type='example',
                title=f"Auto-seeded response {response_id[:8]}",
                content=f"Response with quality score: {evaluation['quality_score']:.1f}",
                content_data={
                    'source_response_id': response_id,
                    'quality_metrics': evaluation.get('metrics', {}),
                    'auto_seeded': True,
                    'auto_seed_date': _utcnow().isoformat(),
                },
                tags=['auto-seeded', 'high-quality'],
            )
            self.db.add(item)
            await self.db.commit()
            await self.db.refresh(item)

            logger.info(
                f"Successfully auto-seeded response {response_id} to library {target_library_id}, "
                f"item_id: {item.id}"
            )

            return str(item.id)

        except Exception as e:
            logger.error(f"Failed to auto-seed response {response_id}: {e}")
            return None

    async def _get_or_create_test_library(self) -> str:
        """获取或创建测试种子库"""
        result = await self.db.execute(
            select(SeedLibrary).where(
                SeedLibrary.name == "Auto-Seeded Content",
                SeedLibrary.category == "custom",
                SeedLibrary.visibility == "private",
                SeedLibrary.deleted_at.is_(None),
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return str(existing.id)

        library = SeedLibrary(
            name="Auto-Seeded Content",
            description="High-quality responses auto-seeded from user feedback",
            category="custom",
            visibility="private",
            tags=["auto-seeded", "test"],
            language="zh",
        )
        self.db.add(library)
        await self.db.commit()
        await self.db.refresh(library)

        return str(library.id)
