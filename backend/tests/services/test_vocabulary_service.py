"""
词汇服务单元测试
Vocabulary Service Unit Tests
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.vocabulary_service import VocabularyService


class TestCalculateNextReview:
    """测试统一复习算法"""

    def test_forgot_word_returns_one_day(self):
        """忘记单词：1天后复习"""
        result = VocabularyService._calculate_next_review(
            importance=3,
            consecutive_correct=5,
            remembered=False
        )
        expected = datetime.utcnow() + timedelta(days=1)
        # 允许1秒误差
        assert abs((result - expected).total_seconds()) < 1

    def test_importance_5_streak_0_returns_one_day(self):
        """重要度5星，连续0次：1天后复习"""
        result = VocabularyService._calculate_next_review(
            importance=5,
            consecutive_correct=0,
            remembered=True
        )
        expected = datetime.utcnow() + timedelta(days=1)
        assert abs((result - expected).total_seconds()) < 1

    def test_importance_1_streak_0_returns_five_days(self):
        """重要度1星，连续0次：5天后复习"""
        result = VocabularyService._calculate_next_review(
            importance=1,
            consecutive_correct=0,
            remembered=True
        )
        expected = datetime.utcnow() + timedelta(days=5)
        assert abs((result - expected).total_seconds()) < 1

    def test_importance_3_streak_3_returns_twelve_days(self):
        """重要度3星，连续3次：约12天后复习 (3 × 2²)"""
        result = VocabularyService._calculate_next_review(
            importance=3,
            consecutive_correct=3,
            remembered=True
        )
        # base_interval = 6 - 3 = 3
        # multiplier = 2^(3-1) = 4
        # days = 3 * 4 = 12
        expected = datetime.utcnow() + timedelta(days=12)
        assert abs((result - expected).total_seconds()) < 1

    def test_importance_4_streak_2_returns_four_days(self):
        """重要度4星，连续2次：4天后复习 (2 × 2¹)"""
        result = VocabularyService._calculate_next_review(
            importance=4,
            consecutive_correct=2,
            remembered=True
        )
        # base_interval = 6 - 4 = 2
        # multiplier = 2^(2-1) = 2
        # days = 2 * 2 = 4
        expected = datetime.utcnow() + timedelta(days=4)
        assert abs((result - expected).total_seconds()) < 1

    def test_max_interval_capped_at_180_days(self):
        """最大间隔上限为180天"""
        result = VocabularyService._calculate_next_review(
            importance=1,
            consecutive_correct=10,  # 会产生很大的间隔
            remembered=True
        )
        # base_interval = 5, multiplier = 2^9 = 512
        # 5 * 512 = 2560，但应该被限制为 180
        expected = datetime.utcnow() + timedelta(days=180)
        assert abs((result - expected).total_seconds()) < 1


@pytest.mark.asyncio
class TestRecordReview:
    """测试记录复习结果"""

    async def test_record_review_increments_counters(self):
        """记录正确复习应增加计数器"""
        db = AsyncMock()
        word_book = MagicMock()
        word_book.review_count = 5
        word_book.correct_review_count = 3
        word_book.consecutive_correct = 2
        word_book.importance = 3

        db.get = AsyncMock(return_value=word_book)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        result = await VocabularyService.record_review(
            db, MagicMock(id=123), remembered=True
        )

        assert result.review_count == 6
        assert result.correct_review_count == 4
        assert result.consecutive_correct == 3

    async def test_record_review_resets_consecutive_on_forgot(self):
        """忘记时应重置连续计数"""
        db = AsyncMock()
        word_book = MagicMock()
        word_book.review_count = 5
        word_book.correct_review_count = 3
        word_book.consecutive_correct = 5
        word_book.importance = 3

        db.get = AsyncMock(return_value=word_book)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        result = await VocabularyService.record_review(
            db, MagicMock(id=123), remembered=False
        )

        assert result.consecutive_correct == 0
        assert result.correct_review_count == 3  # 不增加

    async def test_record_review_returns_none_for_not_found(self):
        """单词不存在时返回 None"""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        result = await VocabularyService.record_review(
            db, MagicMock(id=123), remembered=True
        )

        assert result is None


@pytest.mark.asyncio
class TestUpdateImportance:
    """测试更新重要度"""

    async def test_update_importance_success(self):
        """成功更新重要度"""
        db = AsyncMock()
        word_book = MagicMock()
        word_book.consecutive_correct = 2

        db.get = AsyncMock(return_value=word_book)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        result = await VocabularyService.update_importance(
            db, MagicMock(id=123), importance=5
        )

        assert result.importance == 5
        assert db.commit.called

    async def test_update_importance_invalid_range(self):
        """无效的重要度范围应抛出异常"""
        db = AsyncMock()

        with pytest.raises(ValueError, match="Importance must be between"):
            await VocabularyService.update_importance(
                db, MagicMock(id=123), importance=6
            )

    async def test_update_importance_not_found(self):
        """单词不存在时返回 None"""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        result = await VocabularyService.update_importance(
            db, MagicMock(id=123), importance=3
        )

        assert result is None


@pytest.mark.asyncio
class TestGetStatistics:
    """测试获取统计信息"""

    async def test_get_statistics_returns_summary(self):
        """返回统计摘要"""
        db = AsyncMock()
        db.dialect = MagicMock()

        # Mock count queries - scalar() is a method that returns a value
        async def mock_execute(stmt):
            result = AsyncMock()
            if 'total' in str(stmt).lower():
                result.scalar = MagicMock(return_value=100)
            elif 'due' in str(stmt).lower():
                result.scalar = MagicMock(return_value=15)
            else:
                result.scalar = MagicMock(return_value=5)
            return result

        db.execute = mock_execute

        stats = await VocabularyService.get_statistics(
            db, MagicMock(id=123)
        )

        assert 'total_words' in stats
        assert 'due_for_review' in stats
        assert 'accuracy_rate' in stats
        assert 'by_importance' in stats
