"""Tests for PlanAdjustmentApplier — bridges adaptive adjustments to task entities."""
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.plan_adjustment_applier import (
    MAX_TASKS_TO_PATCH,
    MIN_DIFFICULTY,
    MAX_DIFFICULTY,
    PlanAdjustmentApplier,
    PlanAdjustmentResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(
    *,
    estimated_minutes: int = 30,
    difficulty: int = 3,
    knowledge_node_id=None,
    order_index: int = 0,
    due_date: date | None = None,
):
    """Lightweight task stand-in for unit tests (avoids SQLAlchemy session issues)."""
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        plan_id=uuid4(),
        title="Test task",
        type="LEARNING",
        estimated_minutes=estimated_minutes,
        difficulty=difficulty,
        energy_cost=1,
        status="PENDING",
        priority=0,
        order_index=order_index,
        due_date=due_date or date.today() + timedelta(days=1),
        tags=[],
        knowledge_node_id=knowledge_node_id,
        guide_content=None,
    )


def _db_result_for_tasks(tasks: list):
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = tasks
    scalars_mock.__iter__.return_value = iter(tasks)
    db_result = MagicMock()
    db_result.scalars.return_value = scalars_mock
    return db_result


def _make_applier(
    tasks: list | None = None,
    facts: dict | None = None,
    constraints: dict | None = None,
):
    """Create PlanAdjustmentApplier with mocked DB, redis, and plan_state_service."""
    db = MagicMock()
    redis = MagicMock()
    applier = PlanAdjustmentApplier(db, redis)

    # --- plan state mock ---
    plan_state = MagicMock()
    plan_state.facts = facts or {}
    plan_state.constraints = constraints or {}

    applier.plan_state_service = MagicMock()
    applier.plan_state_service.get_plan_state = AsyncMock(return_value=plan_state)
    applier.plan_state_service.upsert_plan_state = AsyncMock()

    # --- task query mock ---
    if tasks is not None:
        db.execute = AsyncMock(return_value=_db_result_for_tasks(tasks))

    db.commit = AsyncMock()
    db.add = MagicMock()

    return applier, db


# ===========================================================================
# No-op cases
# ===========================================================================

@pytest.mark.asyncio
async def test_no_plan_state_returns_not_applied():
    applier, _ = _make_applier()
    applier.plan_state_service.get_plan_state = AsyncMock(return_value=None)

    res = await applier.apply_incremental_changes(uuid4(), uuid4())
    assert res.applied is False


@pytest.mark.asyncio
async def test_no_adjustments_no_constraints_returns_not_applied():
    applier, _ = _make_applier(tasks=[_make_task()], facts={}, constraints={})

    res = await applier.apply_incremental_changes(uuid4(), uuid4())
    assert res.applied is False


@pytest.mark.asyncio
async def test_empty_task_list_returns_not_applied():
    applier, _ = _make_applier(
        tasks=[],
        facts={"adaptive_adjustments": {"time_multiplier": 1.3}},
    )

    res = await applier.apply_incremental_changes(uuid4(), uuid4())
    assert res.applied is False


# ===========================================================================
# Patch 1: Time multiplier
# ===========================================================================

@pytest.mark.asyncio
async def test_time_multiplier_scales_estimated_minutes():
    t1 = _make_task(estimated_minutes=30)
    t2 = _make_task(estimated_minutes=60)

    applier, _ = _make_applier(
        tasks=[t1, t2],
        facts={"adaptive_adjustments": {"time_multiplier": 1.3}},
    )

    res = await applier.apply_incremental_changes(uuid4(), uuid4())

    assert res.applied is True
    assert t1.estimated_minutes == 39  # 30 * 1.3
    assert t2.estimated_minutes == 78  # 60 * 1.3
    assert "time_scaled" in res.patch_summary


@pytest.mark.asyncio
async def test_time_multiplier_clamps_to_minimum():
    t = _make_task(estimated_minutes=5)
    applier, _ = _make_applier(
        tasks=[t],
        facts={"adaptive_adjustments": {"time_multiplier": 0.5}},
    )

    await applier.apply_incremental_changes(uuid4(), uuid4())
    assert t.estimated_minutes == 5  # Clamped to MIN_ESTIMATED_MINUTES


@pytest.mark.asyncio
async def test_time_multiplier_1_is_identity():
    """time_multiplier=1.0 enters applied path but makes no changes."""
    t = _make_task(estimated_minutes=30)
    applier, _ = _make_applier(
        tasks=[t],
        facts={"adaptive_adjustments": {"time_multiplier": 1.0}},
    )

    res = await applier.apply_incremental_changes(uuid4(), uuid4())

    # Non-empty adjustments dict passes the guard, but multiplier=1.0 is identity
    # applied=True because adjustments exist, but no tasks actually changed
    assert res.applied is True
    assert len(res.affected_task_ids) == 0
    assert t.estimated_minutes == 30  # Unchanged


# ===========================================================================
# Patch 2: Difficulty shift
# ===========================================================================

@pytest.mark.asyncio
async def test_negative_difficulty_shift_lowers_hard_tasks():
    """Negative shift on difficulty>=3 should decrease by 1."""
    t = _make_task(difficulty=4)
    applier, _ = _make_applier(
        tasks=[t],
        facts={"adaptive_adjustments": {"difficulty_shift": -0.3}},
    )

    res = await applier.apply_incremental_changes(uuid4(), uuid4())
    assert res.applied is True
    assert t.difficulty == 3
    assert "difficulty_adjusted" in res.patch_summary


@pytest.mark.asyncio
async def test_positive_difficulty_shift_raises_easy_tasks():
    """Positive shift on difficulty<=2 should increase by 1."""
    t = _make_task(difficulty=2)
    applier, _ = _make_applier(
        tasks=[t],
        facts={"adaptive_adjustments": {"difficulty_shift": 0.3}},
    )

    res = await applier.apply_incremental_changes(uuid4(), uuid4())
    assert t.difficulty == 3


@pytest.mark.asyncio
async def test_difficulty_clamps_at_1():
    """Difficulty must not go below 1."""
    t = _make_task(difficulty=1)
    applier, _ = _make_applier(
        tasks=[t],
        facts={"adaptive_adjustments": {"difficulty_shift": -0.5}},
    )

    await applier.apply_incremental_changes(uuid4(), uuid4())
    assert t.difficulty == 1


@pytest.mark.asyncio
async def test_difficulty_zero_shift_is_identity():
    """difficulty_shift=0.0 should not change difficulty."""
    t = _make_task(difficulty=3)
    applier, _ = _make_applier(
        tasks=[t],
        facts={"adaptive_adjustments": {"difficulty_shift": 0.0}},
    )

    res = await applier.apply_incremental_changes(uuid4(), uuid4())
    # Non-empty adjustments dict passes guard, but shift=0.0 is identity
    assert res.applied is True
    assert len(res.affected_task_ids) == 0
    assert t.difficulty == 3  # Unchanged


# ===========================================================================
# Patch 3: Prerequisite review insertion
# ===========================================================================

@pytest.mark.asyncio
async def test_prerequisite_review_inserted_for_weak_nodes():
    weak_node = uuid4()
    t = _make_task(knowledge_node_id=weak_node)

    applier, db = _make_applier(
        tasks=[t],
        facts={"adaptive_adjustments": {"time_multiplier": 1.0}},
        constraints={
            "insert_prerequisite_review": True,
            "weak_knowledge_node_ids": [str(weak_node)],
        },
    )

    res = await applier.apply_incremental_changes(uuid4(), uuid4())

    assert res.applied is True
    assert len(res.inserted_task_ids) == 1
    assert "prerequisite_reviews_inserted" in res.patch_summary
    assert db.add.called


@pytest.mark.asyncio
async def test_no_review_for_non_weak_nodes():
    weak_node = uuid4()
    other_node = uuid4()
    t = _make_task(knowledge_node_id=other_node)

    applier, db = _make_applier(
        tasks=[t],
        facts={"adaptive_adjustments": {"time_multiplier": 1.0}},
        constraints={
            "insert_prerequisite_review": True,
            "weak_knowledge_node_ids": [str(weak_node)],
        },
    )

    res = await applier.apply_incremental_changes(uuid4(), uuid4())
    # constraint patches exist → applied=True, but no review inserted
    assert len(res.inserted_task_ids) == 0
    assert db.add.called is False


@pytest.mark.asyncio
async def test_no_review_without_constraint_flag():
    t = _make_task(knowledge_node_id=uuid4())
    applier, db = _make_applier(
        tasks=[t],
        facts={"adaptive_adjustments": {"time_multiplier": 1.0}},
        constraints={},  # No insert_prerequisite_review flag
    )

    res = await applier.apply_incremental_changes(uuid4(), uuid4())
    assert len(res.inserted_task_ids) == 0


# ===========================================================================
# Patch 4: Concurrency / hide distant
# ===========================================================================

@pytest.mark.asyncio
async def test_concurrency_hides_distant_tasks():
    tasks = [_make_task(order_index=i) for i in range(5)]

    applier, _ = _make_applier(
        tasks=tasks,
        facts={"adaptive_adjustments": {"time_multiplier": 1.0}},
        constraints={
            "max_concurrent_tasks": 3,
            "hide_distant_phases": True,
        },
    )

    res = await applier.apply_incremental_changes(uuid4(), uuid4())

    assert res.applied is True
    assert len(res.hidden_task_ids) == 2  # 5 - 3 = 2 hidden


@pytest.mark.asyncio
async def test_no_hiding_without_flag():
    tasks = [_make_task(order_index=i) for i in range(5)]

    applier, _ = _make_applier(
        tasks=tasks,
        facts={"adaptive_adjustments": {"time_multiplier": 1.0}},
        constraints={"max_concurrent_tasks": 3},  # no hide_distant_phases
    )

    res = await applier.apply_incremental_changes(uuid4(), uuid4())
    assert len(res.hidden_task_ids) == 0


# ===========================================================================
# Snapshot & rollback
# ===========================================================================

@pytest.mark.asyncio
async def test_snapshot_recorded_on_patch():
    t = _make_task()
    applier, _ = _make_applier(
        tasks=[t],
        facts={"adaptive_adjustments": {"time_multiplier": 1.5}},
    )

    res = await applier.apply_incremental_changes(uuid4(), uuid4())

    assert res.rollback_snapshot_id is not None
    assert applier.plan_state_service.upsert_plan_state.called


@pytest.mark.asyncio
async def test_rollback_deletes_inserted_reviews():
    inserted_id = uuid4()
    user_id = uuid4()
    plan_id = uuid4()

    applier, db = _make_applier(
        facts={
            "adaptive_meta": {
                "task_patch_snapshots": [
                    {
                        "id": str(uuid4()),
                        "inserted_task_ids": [str(inserted_id)],
                        "hidden_task_ids": [],
                    }
                ]
            }
        }
    )
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    ok = await applier.rollback_last_patch(user_id, plan_id)
    assert ok is True
    assert db.execute.called  # DELETE issued


@pytest.mark.asyncio
async def test_rollback_returns_false_when_no_snapshots():
    applier, _ = _make_applier(facts={"adaptive_meta": {"task_patch_snapshots": []}})

    ok = await applier.rollback_last_patch(uuid4(), uuid4())
    assert ok is False


@pytest.mark.asyncio
async def test_rollback_preserves_existing_adaptive_meta_keys():
    task = _make_task()
    snapshot_id = str(uuid4())
    user_id = uuid4()
    plan_id = uuid4()

    applier, db = _make_applier(
        facts={
            "adaptive_meta": {
                "task_patch_snapshots": [
                    {
                        "id": snapshot_id,
                        "inserted_task_ids": [],
                        "hidden_task_ids": [str(task.id)],
                        "task_state_snapshots": {
                            str(task.id): {
                                "estimated_minutes": task.estimated_minutes,
                                "difficulty": task.difficulty,
                                "order_index": task.order_index,
                                "tags": ["kept"],
                            }
                        },
                    }
                ],
                "last_adjustment_at": "2026-04-02T10:00:00+00:00",
                "active_snapshot_id": "snap-current",
                "rollback_monitor": {"negative_feedback_streak": 1},
            }
        }
    )
    db.execute = AsyncMock(return_value=_db_result_for_tasks([task]))

    ok = await applier.rollback_last_patch(user_id, plan_id)

    assert ok is True
    patch = applier.plan_state_service.upsert_plan_state.await_args.kwargs["patch"]
    meta = patch["facts"]["adaptive_meta"]
    assert meta["task_patch_snapshots"] == []
    assert meta["last_adjustment_at"] == "2026-04-02T10:00:00+00:00"
    assert meta["active_snapshot_id"] == "snap-current"
    assert meta["rollback_monitor"] == {"negative_feedback_streak": 1}


@pytest.mark.asyncio
async def test_rollback_restores_task_fields_and_tags():
    task = _make_task(estimated_minutes=45, difficulty=4, order_index=3)
    original_tags = ["focus"]
    task.tags = list(original_tags)

    # Simulate already-patched state.
    task.estimated_minutes = 60
    task.difficulty = 3
    task.order_index = 4
    task.tags = ["focus", "adaptive_adjusted", "adaptive_hidden"]

    snapshot = {
        "id": str(uuid4()),
        "inserted_task_ids": [],
        "hidden_task_ids": [str(task.id)],
        "task_state_snapshots": {
            str(task.id): {
                "estimated_minutes": 45,
                "difficulty": 4,
                "order_index": 3,
                "tags": original_tags,
            }
        },
    }
    applier, db = _make_applier(
        facts={"adaptive_meta": {"task_patch_snapshots": [snapshot]}},
    )
    db.execute = AsyncMock(return_value=_db_result_for_tasks([task]))

    ok = await applier.rollback_last_patch(uuid4(), uuid4())

    assert ok is True
    assert task.estimated_minutes == 45
    assert task.difficulty == 4
    assert task.order_index == 3
    assert task.tags == original_tags


# ===========================================================================
# User-facing language
# ===========================================================================

@pytest.mark.asyncio
async def test_user_facing_summary_no_forbidden_words():
    t = _make_task()
    applier, _ = _make_applier(
        tasks=[t],
        facts={"adaptive_adjustments": {"time_multiplier": 1.5}},
    )

    res = await applier.apply_incremental_changes(uuid4(), uuid4())

    assert res.user_facing_summary
    forbidden = ["你又", "你没有", "你偏离了", "你失败了", "你落后了", "必须", "立即"]
    for word in forbidden:
        assert word not in res.user_facing_summary, f"Forbidden: {word}"


# ===========================================================================
# Safety limits
# ===========================================================================

@pytest.mark.asyncio
async def test_max_tasks_to_patch_limit():
    tasks = [_make_task() for _ in range(20)]
    applier, _ = _make_applier(
        tasks=tasks,
        facts={"adaptive_adjustments": {"time_multiplier": 1.5}},
    )

    res = await applier.apply_incremental_changes(uuid4(), uuid4())
    assert len(res.affected_task_ids) <= MAX_TASKS_TO_PATCH


@pytest.mark.asyncio
async def test_combined_patches_all_apply():
    """Multiple patch types should all fire in a single run."""
    weak_node = uuid4()
    t1 = _make_task(estimated_minutes=30, difficulty=4, knowledge_node_id=weak_node, order_index=0)
    t2 = _make_task(estimated_minutes=60, difficulty=3, order_index=1)
    t3 = _make_task(estimated_minutes=45, difficulty=2, order_index=2)

    applier, db = _make_applier(
        tasks=[t1, t2, t3],
        facts={"adaptive_adjustments": {"time_multiplier": 1.2, "difficulty_shift": -0.3}},
        constraints={
            "insert_prerequisite_review": True,
            "weak_knowledge_node_ids": [str(weak_node)],
            "max_concurrent_tasks": 2,
            "hide_distant_phases": True,
        },
    )

    res = await applier.apply_incremental_changes(uuid4(), uuid4())

    assert res.applied is True
    # Should have: time scaled, difficulty adjusted, review inserted, some hidden
    assert len(res.inserted_task_ids) >= 1
    assert "time_scaled" in res.patch_summary
    assert "difficulty_adjusted" in res.patch_summary
