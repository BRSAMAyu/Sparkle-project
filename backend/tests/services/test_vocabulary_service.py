"""
词汇服务单元测试
Vocabulary Service Unit Tests
"""
import pytest
from datetime import timezone, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.vocabulary_service import VocabularyService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TestCalculateNextReview:
    """测试统一复习算法"""

    def test_forgot_word_returns_one_day(self):
        """忘记单词：1天后复习"""
        result = VocabularyService._calculate_next_review(
            importance=3,
            consecutive_correct=5,
            remembered=False
        )
        expected = _utcnow() + timedelta(days=1)
        # 允许1秒误差
        assert abs((result - expected).total_seconds()) < 1

    def test_importance_5_streak_0_returns_one_day(self):
        """重要度5星，连续0次：1天后复习"""
        result = VocabularyService._calculate_next_review(
            importance=5,
            consecutive_correct=0,
            remembered=True
        )
        expected = _utcnow() + timedelta(days=1)
        assert abs((result - expected).total_seconds()) < 1

    def test_importance_1_streak_0_returns_five_days(self):
        """重要度1星，连续0次：5天后复习"""
        result = VocabularyService._calculate_next_review(
            importance=1,
            consecutive_correct=0,
            remembered=True
        )
        expected = _utcnow() + timedelta(days=5)
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
        expected = _utcnow() + timedelta(days=12)
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
        expected = _utcnow() + timedelta(days=4)
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
        expected = _utcnow() + timedelta(days=180)
        assert abs((result - expected).total_seconds()) < 1

    @pytest.mark.parametrize(
        ("importance", "consecutive_correct", "remembered", "expected_days"),
        [
            (5, 0, True, 1),
            (4, 2, True, 4),
            (3, 3, True, 12),
            (1, 10, True, 180),
            (3, 6, False, 1),
        ],
    )
    def test_backend_schedule_matches_mobile_formula(
        self,
        importance: int,
        consecutive_correct: int,
        remembered: bool,
        expected_days: int,
    ):
        """后端调度应与 Flutter 离线公式保持一致。"""
        result = VocabularyService._calculate_next_review(
            importance=importance,
            consecutive_correct=consecutive_correct,
            remembered=remembered,
        )

        expected = _utcnow() + timedelta(days=expected_days)
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
        db.execute = AsyncMock(
            side_effect=[
                MagicMock(
                    one=MagicMock(
                        return_value=SimpleNamespace(
                            total_words=100,
                            due_for_review=15,
                            accuracy_rate=0.75,
                        )
                    )
                ),
                MagicMock(all=MagicMock(return_value=[(1, 8), (3, 12), (5, 20)])),
            ]
        )

        stats = await VocabularyService.get_statistics(
            db, MagicMock(id=123)
        )

        assert stats["total_words"] == 100
        assert stats["due_for_review"] == 15
        assert stats["accuracy_rate"] == 0.75
        assert stats["by_importance"] == {
            "1": 8,
            "2": 0,
            "3": 12,
            "4": 0,
            "5": 20,
        }
        assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_get_review_list_applies_default_batch_limit():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)

    await VocabularyService.get_review_list(db, MagicMock(id=123))

    stmt = db.execute.await_args.args[0]
    assert stmt._limit_clause.value == VocabularyService.DEFAULT_REVIEW_BATCH_SIZE


def test_build_learning_loop_summary_surfaces_review_graph_and_asset_links():
    word_id = uuid4()
    node_id = uuid4()
    asset_id = uuid4()
    next_review_at = _utcnow() + timedelta(days=1)
    word_book = SimpleNamespace(
        id=word_id,
        word="polymorphism",
        source_translation_id="tx-123",
        next_review_at=next_review_at,
        importance=5,
        review_count=0,
        tags=[
            {
                "type": "learning_loop",
                "knowledge_node_id": str(node_id),
                "knowledge_status": "draft",
                "learning_asset_id": str(asset_id),
                "learning_asset_status": "ACTIVE",
            }
        ],
    )

    summary = VocabularyService.build_learning_loop_summary(word_book)

    assert summary["vocabulary_card"]["word_id"] == str(word_id)
    assert summary["review"]["scheduled"] is True
    assert summary["review"]["next_review_at"] == next_review_at.isoformat()
    assert summary["knowledge_card"] == {
        "created": True,
        "node_id": str(node_id),
        "status": "draft",
    }
    assert summary["learning_asset"]["asset_id"] == str(asset_id)
    assert summary["task_recommendation_hint"]["eligible"] is True


@pytest.mark.asyncio
async def test_attach_learning_links_replaces_prior_loop_tag():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    node_id = uuid4()
    asset_id = uuid4()
    word_book = SimpleNamespace(
        tags=[
            "exam",
            {"type": "learning_loop", "knowledge_node_id": "old"},
        ]
    )

    result = await VocabularyService.attach_learning_links(
        db,
        word_book,
        graph_node_id=node_id,
        graph_status="draft",
        learning_asset_id=asset_id,
        learning_asset_status="ACTIVE",
    )

    assert result.tags[0] == "exam"
    assert len([tag for tag in result.tags if isinstance(tag, dict) and tag.get("type") == "learning_loop"]) == 1
    assert result.tags[1]["knowledge_node_id"] == str(node_id)
    assert result.tags[1]["learning_asset_id"] == str(asset_id)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(word_book)
