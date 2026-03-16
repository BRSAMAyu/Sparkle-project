import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.core.event_types import CAPSULE_REGENERATE_REQUESTED
from app.models.curiosity_capsule import CuriosityCapsule
from app.models.error_book import ErrorRecord
from app.models.task import Task, TaskStatus, TaskType
from app.services.capsule_feedback_service import CapsuleFeedbackService
from app.services.capsule_generation_service import CapsuleGenerationService
from app.services.cognitive.auto_fragment_collector import AutoFragmentCollector
from app.services.cognitive_service import CognitiveService
from app.services.personalization.preference_service import PreferenceService


@pytest.mark.asyncio
async def test_auto_collector_task_completion(db, test_user):
    task = Task(
        user_id=test_user.id,
        title="Write summary",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=30,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.COMPLETED,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    collector = AutoFragmentCollector(db)
    collector.cognitive_service.analyze_behavior = AsyncMock(return_value={})

    with patch("app.services.cognitive_service.embedding_service.get_embedding", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.0] * 1024
        await collector.collect_from_task_completion(
            user_id=test_user.id,
            task_id=task.id,
            estimated_minutes=30,
            actual_minutes=50,
            completion_rate=0.9,
            difficulty=3,
        )

    cognitive_service = CognitiveService(db)
    fragments = await cognitive_service.get_fragments(test_user.id)

    assert len(fragments) == 1
    assert "planning.underestimate" in (fragments[0].error_tags or [])


@pytest.mark.asyncio
async def test_pattern_affects_capsule_generation(db, test_user):
    cognitive_service = CognitiveService(db)

    with patch("app.services.cognitive_service.embedding_service.get_embedding", new_callable=AsyncMock) as mock_embed, \
         patch("app.services.cognitive_service.event_bus.publish", new_callable=AsyncMock):
        mock_embed.return_value = [0.0] * 1024
        fragment = await cognitive_service.create_fragment(
            user_id=test_user.id,
            content="I keep underestimating task durations.",
            source_type="behavior_auto",
            error_tags=["planning.underestimate"],
            severity=2,
        )

        await cognitive_service._upsert_pattern(
            user_id=test_user.id,
            analysis={
                "pattern_name": "Planning Optimism",
                "pattern_type": "execution",
                "confidence_score": 0.8,
                "solution_text": "Break tasks into smaller chunks",
            },
            fragment_id=fragment.id,
        )

    capsule_service = CapsuleGenerationService()
    context = await capsule_service._gather_user_context(test_user.id, db)

    assert "behavior_patterns" in context
    assert any(p["name"] == "Planning Optimism" for p in context["behavior_patterns"])


@pytest.mark.asyncio
async def test_auto_collector_focus_session_interrupts(db, test_user):
    collector = AutoFragmentCollector(db)
    collector.cognitive_service.analyze_behavior = AsyncMock(return_value={})

    with patch("app.services.cognitive_service.embedding_service.get_embedding", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.0] * 1024
        await collector.collect_from_focus_session(
            user_id=test_user.id,
            session_id=None,
            duration_minutes=30,
            interruptions=3,
        )

    cognitive_service = CognitiveService(db)
    fragments = await cognitive_service.get_fragments(test_user.id)

    assert len(fragments) == 1
    assert "execution.focus_breakdown" in (fragments[0].error_tags or [])


@pytest.mark.asyncio
async def test_auto_collector_error_pattern(db, test_user):
    node_id = uuid4()
    error1 = ErrorRecord(
        user_id=test_user.id,
        subject_code="math",
        linked_knowledge_node_ids=[node_id],
    )
    error2 = ErrorRecord(
        user_id=test_user.id,
        subject_code="math",
        linked_knowledge_node_ids=[node_id],
    )
    db.add_all([error1, error2])
    await db.commit()

    collector = AutoFragmentCollector(db)
    collector.cognitive_service.analyze_behavior = AsyncMock(return_value={})

    with patch.object(collector, "_count_errors_for_node", new_callable=AsyncMock) as mock_count, \
         patch("app.services.cognitive_service.embedding_service.get_embedding", new_callable=AsyncMock) as mock_embed:
        mock_count.return_value = 2
        mock_embed.return_value = [0.0] * 1024
        await collector.collect_from_error_pattern(
            user_id=test_user.id,
            error_id=error1.id,
            linked_node_ids=[str(node_id)],
        )

    cognitive_service = CognitiveService(db)
    fragments = await cognitive_service.get_fragments(test_user.id)

    assert len(fragments) == 1
    assert "knowledge.blind_spot" in (fragments[0].error_tags or [])


@pytest.mark.asyncio
async def test_feedback_updates_inferred_preferences(db, test_user):
    service = CapsuleFeedbackService()
    await service._update_inferred_preferences(
        test_user.id,
        depth_delta=0.2,
        curiosity_delta=-0.1,
        db=db,
    )

    prefs = await PreferenceService(db).get_preferences(test_user.id)
    inferred = prefs.inferred or {}
    assert inferred.get("depth_preference") == pytest.approx(0.52, rel=1e-3)
    assert inferred.get("curiosity_preference") == pytest.approx(0.49, rel=1e-3)


@pytest.mark.asyncio
async def test_feedback_triggers_regenerate_event(db, test_user):
    capsule = CuriosityCapsule(
        user_id=test_user.id,
        title="Test Capsule",
        content="Test Content",
    )
    db.add(capsule)
    await db.commit()
    await db.refresh(capsule)

    service = CapsuleFeedbackService()
    with patch("app.services.capsule_feedback_service.event_bus.publish", new_callable=AsyncMock) as mock_publish, \
         patch("app.models.capsule_feedback.CapsuleFeedback.calculate_preference_deltas", return_value=(0.2, 0.0)):
        await service.submit_feedback(
            user_id=test_user.id,
            capsule_id=capsule.id,
            db=db,
            rating=5,
            comment="Great",
        )

    assert any(call.args[0] == CAPSULE_REGENERATE_REQUESTED for call in mock_publish.call_args_list)
