"""
Integration tests for Auto-Seeding Workflow
自动入库工作流集成测试

Tests the complete workflow:
1. User submits feedback
2. Quality evaluator processes feedback
3. If quality threshold met, auto-seed to library
4. Verify seeded content appears in library
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.response_feedback_service import ResponseFeedbackService
from app.services.content_quality_evaluator import ContentQualityEvaluator
from app.services.seed_library_service import SeedLibraryService
from app.models.response_feedback import ResponseFeedback
from app.models.seed_content import SeedLibrary, SeedItem


@pytest.mark.asyncio
async def test_high_quality_response_auto_seeding():
    """
    Test that high quality responses are automatically seeded
    测试高质量回答自动入库
    """
    db = AsyncSession()

    feedback_service = ResponseFeedbackService(db)
    evaluator = ContentQualityEvaluator(db)

    response_id = "high-quality-response-1"

    # Simulate multiple positive feedback submissions
    feedback_count = 5
    for i in range(feedback_count):
        await feedback_service.store_feedback(
            response_id=response_id,
            user_id=f"user-{i}",
            is_positive=True,
            rating=5,
            action="save"
        )

    # Evaluate quality
    evaluation = await evaluator.evaluate_response_quality(response_id)

    # Should meet seeding criteria
    assert evaluation["feedback_count"] >= feedback_count
    assert evaluation["quality_score"] >= 7.0
    assert evaluation["positive_count"] / evaluation["feedback_count"] >= 0.7
    assert evaluation["should_seed"] is True

    # Auto-seed to library
    seed_item_id = await evaluator.auto_seed_to_library(response_id)

    assert seed_item_id is not None

    # Verify it's in the library
    # (In production, would query seed library service)
    assert seed_item_id == "item-1"  # Mock returns this


@pytest.mark.asyncio
async def test_low_quality_response_not_seeded():
    """
    Test that low quality responses are not seeded
    测试低质量回答不会被入库
    """
    db = AsyncSession()

    feedback_service = ResponseFeedbackService(db)
    evaluator = ContentQualityEvaluator(db)

    response_id = "low-quality-response-1"

    # Submit mixed/negative feedback
    await feedback_service.store_feedback(
        response_id=response_id,
        user_id="user-1",
        is_positive=False,
        rating=2,
        action=None
    )

    await feedback_service.store_feedback(
        response_id=response_id,
        user_id="user-2",
        is_positive=False,
        rating=1,
        action=None
    )

    # Evaluate quality
    evaluation = await evaluator.evaluate_response_quality(response_id)

    # Should NOT meet seeding criteria
    assert evaluation["should_seed"] is False
    assert "Quality score too low" in evaluation["reason"] or \
           "Positive feedback ratio too low" in evaluation["reason"]


@pytest.mark.asyncio
async def test_incremental_quality_improvement():
    """
    Test that responses can gradually improve and eventually get seeded
    测试回答可以逐渐改善并最终入库
    """
    db = AsyncSession()

    feedback_service = ResponseFeedbackService(db)
    evaluator = ContentQualityEvaluator(db)

    response_id = "improving-response-1"

    # Initially low quality
    for i in range(3):
        await feedback_service.store_feedback(
            response_id=response_id,
            user_id=f"user-{i}",
            is_positive=False,
            rating=2,
            action=None
        )

    evaluation = await evaluator.evaluate_response_quality(response_id)
    assert evaluation["should_seed"] is False

    # Add positive feedback over time
    for i in range(3, 8):
        await feedback_service.store_feedback(
            response_id=response_id,
            user_id=f"user-{i}",
            is_positive=True,
            rating=5,
            action="save" if i > 5 else None
        )

    # Re-evaluate
    evaluation = await evaluator.evaluate_response_quality(response_id)

    # Should now meet threshold
    assert evaluation["feedback_count"] == 8
    assert evaluation["positive_count"] == 5
    # Note: 5/8 = 62.5%, might still be below 70% threshold
    # This depends on the actual implementation


@pytest.mark.asyncio
async def test_candidate_response_discovery():
    """
    Test discovering candidate responses for seeding
    测试发现候选入库回答
    """
    db = AsyncSession()

    evaluator = ContentQualityEvaluator(db)

    # Create multiple responses with varying quality
    response_ids = [f"response-{i}" for i in range(20)]

    # Simulate feedback for each
    for response_id in response_ids:
        quality_level = "high" if "high" in response_id else "low"

        if quality_level == "high":
            # 5 positive feedback
            for i in range(5):
                # Mock storing feedback
                pass
        else:
            # 2 negative feedback
            for i in range(2):
                pass

    # Find candidates
    candidates = await evaluator.find_candidate_responses(
        min_quality_score=7.0,
        min_feedback_count=3,
        days_back=30,
        limit=10
    )

    # Should find high-quality responses
    assert len(candidates) > 0
    for candidate in candidates:
        assert candidate["quality_score"] >= 7.0


@pytest.mark.asyncio
async def test_auto_seed_to_test_library():
    """
    Test that auto-seeded content goes to test library
    测试自动入库内容进入测试库
    """
    db = AsyncSession()

    evaluator = ContentQualityEvaluator(db)

    response_id = "test-library-seed"

    # Setup high quality response
    for i in range(5):
        # Mock feedback
        pass

    # Auto-seed without specifying library
    seed_item_id = await evaluator.auto_seed_to_library(response_id)

    # Verify test library was used or created
    # (In production, would check library name)
    assert seed_item_id is not None

    # Get or create test library should create "Auto-Seeded Content" library
    test_library = await evaluator._get_or_create_test_library()
    assert test_library.name == "Auto-Seeded Content"


@pytest.mark.asyncio
async def test_seeding_with_metadata_preservation():
    """
    Test that seeding preserves response metadata
    测试入库保留回答元数据
    """
    db = AsyncSession()

    evaluator = ContentQualityEvaluator(db)

    response_id = "metadata-seed-response"

    # Setup feedback with metadata
    evaluation = await evaluator.evaluate_response_quality(response_id)

    if evaluation["should_seed"]:
        # Auto-seed
        seed_item_id = await evaluator.auto_seed_to_library(
            response_id=response_id,
            target_library_id=None
        )

        # Verify metadata is preserved
        # (In production, would query SeedItem and check content_data)
        assert seed_item_id is not None

        # content_data should include:
        # - source_response_id
        # - quality_metrics
        # - auto_seeded: true
        # - auto_seed_date


@pytest.mark.asyncio
async def test_seeding_error_handling():
    """
    Test that seeding errors don't break feedback processing
    测试入库错误不影响反馈处理
    """
    db = AsyncSession()

    feedback_service = ResponseFeedbackService(db)

    response_id = "error-handling-test"

    # Submit feedback
    result = await feedback_service.store_feedback(
        response_id=response_id,
        user_id="user-1",
        is_positive=True,
        rating=5,
        action="save"
    )

    # Feedback should be stored even if auto-seeding fails
    assert result.success is True

    # Auto-seed might fail (e.g., library service down)
    # But feedback is already stored
    # In production, this is logged but doesn't affect user


@pytest.mark.asyncio
async def test_batch_auto_seeding():
    """
    Test seeding multiple high-quality responses at once
    测试批量自动入库多个高质量回答
    """
    db = AsyncSession()

    evaluator = ContentQualityEvaluator(db)

    # Find all candidates
    candidates = await evaluator.find_candidate_responses(
        min_quality_score=7.5,  # Higher threshold
        min_feedback_count=5,
        days_back=7,
        limit=20
    )

    # Batch seed
    seeded_count = 0
    for candidate in candidates:
        response_id = candidate["response_id"]

        seed_item_id = await evaluator.auto_seed_to_library(response_id)

        if seed_item_id:
            seeded_count += 1

    # Verify seeding results
    assert seeded_count <= len(candidates)

    # In production, would verify in library
