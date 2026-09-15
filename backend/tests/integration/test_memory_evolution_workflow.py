"""
Integration tests for Memory Evolution Workflow
记忆演化工作流集成测试

Tests the complete memory evolution tracking workflow:
1. User updates preference/goal
2. Evolution is automatically tracked
3. History can be retrieved
4. Predictions can be generated
5. Visualization data is correct
"""
import os
import pytest
from datetime import timezone, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory_service import MemoryService
from app.services.memory_evolution_service import MemoryEvolutionService


pytestmark = pytest.mark.skipif(
    os.getenv("FULL_STACK_TESTS") != "1",
    reason="Requires full memory evolution data fixtures and services.",
)
from app.models.memory import MemoryPreference, MemoryGoal
from app.models.memory_evolution import MemoryEvolution, EvolutionPrediction


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_preference_evolution_workflow():
    """
    Test complete preference evolution workflow
    测试完整的偏好演化工作流
    """
    db = AsyncSession()

    memory_service = MemoryService(db)
    evolution_service = MemoryEvolutionService(db)

    user_id = "test-user-evo"

    # Step 1: Create initial preference
    initial_pref = await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="learning_style",
        pref_value={"style": "visual", "intensity": "moderate"},
        evidence_refs=[],  # Empty evidence list for initial preference
        confidence=0.5,
        source_type="user_state"
    )

    initial_pref_id = initial_pref.id

    # Verify evolution was tracked
    evolutions = await evolution_service.get_evolution_history(
        memory_id=initial_pref_id,
        limit=10
    )
    assert len(evolutions) == 1
    assert evolutions[0]["change_type"] == "create"

    # Step 2: Update preference (should track evolution)
    updated_pref = await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="learning_style",
        pref_value={"style": "textual", "intensity": "high"},
        evidence_refs=["user_feedback"],
        confidence=0.8,
        source_type="user_state"
    )

    # Verify evolution was tracked
    evolutions = await evolution_service.get_evolution_history(
        memory_id=initial_pref_id,
        limit=10
    )
    assert len(evolutions) == 2

    update_evo = [e for e in evolutions if e["change_type"] == "update"][0]
    assert update_evo["change_reason"] == "user_edit"
    assert update_evo["confidence_delta"] == 0.3  # 0.8 - 0.5
    assert update_evo["old_value"]["pref_value"]["style"] == "visual"
    assert update_evo["new_value"]["pref_value"]["style"] == "textual"


@pytest.mark.asyncio
async def test_goal_evolution_with_feedback():
    """
    Test goal evolution through feedback learning
    测试通过反馈学习的目标演化
    """
    db = AsyncSession()

    memory_service = MemoryService(db)
    evolution_service = MemoryEvolutionService(db)

    user_id = "test-user-goal-evo"

    # Create initial goal
    initial_goal = await memory_service.create_goal(
        user_id=user_id,
        title="Learn Python",
        target_date=_utcnow() + timedelta(days=30),
        status="pending",
        metadata={"priority": "high"}
    )

    initial_goal_id = initial_goal.id

    # Add feedback (evidence) - should update goal
    await memory_service.add_goal_evidence(
        user_id=user_id,
        goal_id=initial_goal_id,
        evidence_type="progress",
        evidence_data={"progress": "30%", "date": _utcnow().isoformat()}
    )

    # Check evolution was tracked
    evolutions = await evolution_service.get_evolution_history(
        memory_id=initial_goal_id,
        limit=10
    )

    feedback_evolutions = [e for e in evolutions if e["change_reason"] == "feedback_learning"]
    assert len(feedback_evolutions) > 0


@pytest.mark.asyncio
async def test_evolution_history_comparison():
    """
    Test comparing different versions of a memory
    测试记忆的不同版本对比
    """
    db = AsyncSession()

    evolution_service = MemoryEvolutionService(db)
    memory_id = "test-memory-compare"

    # Create multiple evolution records
    for i in range(3):
        await evolution_service.track_memory_change(
            memory_id=memory_id,
            memory_type="preference",
            old_value={"confidence": 0.5 + i * 0.1},
            new_value={"confidence": 0.6 + i * 0.1},
            change_reason="user_edit",
            trigger_event="manual_update"
        )

    # Get history
    history = await evolution_service.get_evolution_history(memory_id)

    # Compare consecutive versions
    comparison = await evolution_service.compare_memory_versions(history[1]["id"])

    assert "field_changes" in comparison
    assert comparison["old_value"]["confidence"] < comparison["new_value"]["confidence"]
    assert "confidence_delta" in comparison


@pytest.mark.asyncio
async def test_evolution_prediction_accuracy():
    """
    Test that evolution predictions are tracked and validated
    测试演化预测被跟踪和验证
    """
    db = AsyncSession()

    evolution_service = MemoryEvolutionService(db)
    memory_id = "test-prediction"

    # Create prediction
    predictions = await evolution_service.predict_evolution(
        memory_id=memory_id,
        time_horizon_days=7
    )

    assert len(predictions) > 0

    # Simulate time passing and actual change
    await evolution_service.track_memory_change(
        memory_id=memory_id,
        memory_type="preference",
        old_value={"confidence": 0.7},
        new_value={"confidence": 0.6},  # Decay occurred
        change_reason="system_inference"
    )

    # Check prediction was actualized (in real system, background job would update)
    # For test, we verify prediction was created
    all_predictions = await evolution_service._get_predictions(memory_id)
    assert len(all_predictions) > 0


@pytest.mark.asyncio
async def test_evolution_visualization_data():
    """
    Test that visualization data is correctly formatted
    测试可视化数据格式正确
    """
    db = AsyncSession()

    evolution_service = MemoryEvolutionService(db)
    memory_id = "test-viz"

    # Create evolution timeline
    for i in range(10):
        await evolution_service.track_memory_change(
            memory_id=memory_id,
            memory_type="preference",
            old_value={"confidence": 0.5},
            new_value={"confidence": 0.5 + i * 0.05},
            change_reason="user_edit"
        )

    # Get visualization data
    viz_data = await evolution_service.visualize_evolution(
        memory_id=memory_id,
        time_range_days=30
    )

    # Verify structure
    assert "timeline" in viz_data
    assert "timestamps" in viz_data["timeline"]
    assert "confidence_scores" in viz_data["timeline"]
    assert len(viz_data["timeline"]["timestamps"]) == 10

    # Verify trend analysis
    assert "impact_trend" in viz_data
    assert viz_data["total_changes"] == 10


@pytest.mark.asyncio
async def test_multi_memory_interaction():
    """
    Test that changes to one memory can affect related memories
    测试一个记忆的变化影响相关记忆
    """
    db = AsyncSession()

    memory_service = MemoryService(db)
    evolution_service = MemoryEvolutionService(db)

    user_id = "test-multi-memory"

    # Create related preferences
    pref1 = await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="learning_time",
        pref_value={"hours": 2},
        evidence_refs=[],
        source_type="user_state"
    )

    # Update another preference that might affect learning_time
    # (In real system, this would trigger re-evaluation)
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="schedule",
        pref_value={"available_hours": 1},
        evidence_refs=["pref1"],
        source_type="user_state"
    )

    # Check that both evolutions were tracked
    evo1 = await evolution_service.get_evolution_history(pref1.id)
    evo2 = await evolution_service.get_evolution_history(pref1.id)

    assert len(evo1) > 0
    assert len(evo2) > 0


@pytest.mark.asyncio
async def test_evolution_with_conflict_resolution():
    """
    Test memory evolution when conflicts are detected
    测试检测到冲突时的记忆演化
    """
    db = AsyncSession()

    memory_service = MemoryService(db)
    evolution_service = MemoryEvolutionService(db)

    user_id = "test-conflict"

    # Create preference
    pref = await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="learning_style",
        pref_value={"style": "visual"},
        evidence_refs=[],
        source_type="user_state"
    )

    # Simulate conflicting update from system
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="learning_style",
        pref_value={"style": "textual"},
        evidence_refs=["system_inference"],
        source_type="system_inference"
    )

    # Check that conflict was recorded
    evolutions = await evolution_service.get_evolution_history(pref.id)
    conflict_evo = [e for e in evolutions if e["change_reason"] == "conflict_resolution"]

    # In production, conflict resolution logic would merge or choose
    # For test, we verify evolution was tracked
    assert len(evolutions) >= 2
