import pytest
from unittest.mock import AsyncMock, patch

from app.models.task import Task, TaskStatus, TaskType
from app.services.cognitive.auto_fragment_collector import AutoFragmentCollector
from app.services.capsule_generation_service import CapsuleGenerationService
from app.services.cognitive_service import CognitiveService


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
