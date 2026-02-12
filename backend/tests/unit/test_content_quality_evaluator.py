"""
Unit tests for Content Quality Evaluator
内容质量评估器单元测试
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


from app.services.content_quality_evaluator import ContentQualityEvaluator
from app.models.response_feedback import ResponseFeedback
from app.models.seed_content import SeedItem


@pytest.fixture
def db_session():
    """Mock database session"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def evaluator(db_session):
    """Create quality evaluator instance"""
    return ContentQualityEvaluator(db_session)


@pytest.mark.asyncio
async def test_evaluate_response_quality_high_quality(evaluator: ContentQualityEvaluator):
    """Test evaluating high quality response"""
    response_id = "test-response-1"

    with patch.object(evaluator.db, 'execute') as mock_execute:
        # Create mock feedback records
        feedback1 = Mock(spec=ResponseFeedback)
        feedback1.is_positive = True
        feedback1.rating = 5
        feedback1.action = "save"
        feedback1.created_at = _utcnow()

        feedback2 = Mock(spec=ResponseFeedback)
        feedback2.is_positive = True
        feedback2.rating = 4
        feedback2.action = "save"
        feedback2.created_at = _utcnow()

        feedback3 = Mock(spec=ResponseFeedback)
        feedback3.is_positive = True
        feedback3.rating = 5
        feedback3.action = "share"
        feedback3.created_at = _utcnow()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            feedback1, feedback2, feedback3
        ]
        mock_execute.return_value = mock_result

        result = await evaluator.evaluate_response_quality(response_id)

        assert result["response_id"] == response_id
        assert result["quality_score"] >= 7.0
        assert result["should_seed"] is True
        assert result["feedback_count"] == 3


@pytest.mark.asyncio
async def test_evaluate_response_quality_low_quality(evaluator: ContentQualityEvaluator):
    """Test evaluating low quality response"""
    response_id = "test-response-2"

    with patch.object(evaluator.db, 'execute') as mock_execute:
        # Create mock negative feedback
        feedback1 = Mock(spec=ResponseFeedback)
        feedback1.is_positive = False
        feedback1.rating = 2
        feedback1.action = None
        feedback1.created_at = _utcnow()

        feedback2 = Mock(spec=ResponseFeedback)
        feedback2.is_positive = False
        feedback2.rating = 1
        feedback2.action = None
        feedback2.created_at = _utcnow()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            feedback1, feedback2
        ]
        mock_execute.return_value = mock_result

        result = await evaluator.evaluate_response_quality(response_id)

        assert result["quality_score"] < 7.0
        assert result["should_seed"] is False


@pytest.mark.asyncio
async def test_evaluate_response_quality_no_feedback(evaluator: ContentQualityEvaluator):
    """Test evaluating response with no feedback"""
    response_id = "test-response-3"

    with patch.object(evaluator.db, 'execute') as mock_execute:
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_execute.return_value = mock_result

        result = await evaluator.evaluate_response_quality(response_id)

        assert result["quality_score"] == 0.0
        assert result["should_seed"] is False
        assert "No feedback found" in result["reason"]


@pytest.mark.asyncio
async def test_find_candidate_responses(evaluator: ContentQualityEvaluator):
    """Test finding candidate responses for seeding"""
    with patch.object(evaluator.db, 'execute') as mock_execute:
        mock_agg_result = Mock()
        mock_agg_result.all.return_value = [("response-1", 5, 4)]
        mock_execute.return_value = mock_agg_result

        candidates = await evaluator.find_candidate_responses(
            min_quality_score=7.0,
            min_feedback_count=3,
            days_back=30,
            limit=50
        )

        assert len(candidates) > 0
        assert candidates[0]["response_id"] == "response-1"
        assert candidates[0]["quality_score"] >= 7.0


@pytest.mark.asyncio
async def test_auto_seed_to_library(evaluator: ContentQualityEvaluator):
    """Test auto-seeding high quality response"""
    response_id = "test-response-auto"

    with patch.object(evaluator, 'evaluate_response_quality') as mock_eval:
        mock_eval.return_value = {
            "response_id": response_id,
            "quality_score": 8.5,
            "should_seed": True,
            "reason": "Meets all quality criteria"
        }

        with patch.object(evaluator, '_get_or_create_test_library') as mock_lib:
            mock_lib.return_value = str(uuid4())

            async def _refresh(item):
                item.id = "item-1"

            evaluator.db.refresh.side_effect = _refresh

            result = await evaluator.auto_seed_to_library(response_id)

            assert result == "item-1"
            evaluator.db.add.assert_called_once()


@pytest.mark.asyncio
async def test_auto_seed_to_library_low_quality(evaluator: ContentQualityEvaluator):
    """Test that low quality responses are not seeded"""
    response_id = "test-response-low"

    with patch.object(evaluator, 'evaluate_response_quality') as mock_eval:
        mock_eval.return_value = {
            "response_id": response_id,
            "quality_score": 5.0,
            "should_seed": False,
            "reason": "Quality score too low"
        }

        result = await evaluator.auto_seed_to_library(response_id)

        assert result is None
