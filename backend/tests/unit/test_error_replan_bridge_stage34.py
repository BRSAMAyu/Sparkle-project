from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.core.metrics import ERROR_REPLAN_BRIDGE_ERROR_TOTAL
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.services.error_replan_bridge import ErrorReplanBridge


async def _seed_bridge_fixture(db_session, *, created_at: datetime) -> tuple[User, Plan, KnowledgeNode, ErrorRecord]:
    user = User(
        username=f"bridge_{created_at.timestamp()}",
        email=f"bridge_{created_at.timestamp()}@example.com",
        hashed_password="hashed",
        created_at=created_at,
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="Stage34 bridge plan",
        type=PlanType.SPRINT,
        description="bridge",
        plan_stage=PlanStage.DAILY,
        target_date=datetime.utcnow().date() + timedelta(days=7),
        daily_available_minutes=60,
        total_estimated_hours=6,
        subject="physics",
        mastery_level=0.2,
        progress=0.0,
        is_active=True,
        priority=PlanPriority.HIGH,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.flush()

    node = KnowledgeNode(name="Entropy", description="node")
    db_session.add(node)
    await db_session.flush()

    db_session.add(
        UserNodeStatus(
            user_id=user.id,
            node_id=node.id,
            mastery_score=35,
            bkt_mastery_prob=0.35,
            total_minutes=0,
            total_study_minutes=0,
            study_count=0,
            is_unlocked=True,
        )
    )
    task = Task(
        user_id=user.id,
        plan_id=plan.id,
        title="Bridge task",
        type=TaskType.ERROR_FIX,
        tags=["physics"],
        estimated_minutes=20,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=3,
        due_date=datetime.utcnow().date() + timedelta(days=1),
        knowledge_node_id=node.id,
    )
    db_session.add(task)
    await db_session.flush()
    db_session.add(
        TaskKnowledgeLink(
            task_id=task.id,
            knowledge_node_id=node.id,
            relation_type="prerequisite",
            is_primary=True,
        )
    )

    error = ErrorRecord(
        user_id=user.id,
        subject_code="physics",
        chapter="thermodynamics",
        question_text="latest",
        mastery_level=0.2,
        latest_analysis={"error_type": "concept_confusion"},
        linked_knowledge_node_ids=[str(node.id)],
        created_at=datetime.utcnow(),
    )
    db_session.add(error)
    await db_session.commit()
    return user, plan, node, error


@pytest.mark.asyncio
async def test_error_replan_bridge_live_mode_triggers_for_new_user_after_single_error(db_session) -> None:
    user, plan, node, error = await _seed_bridge_fixture(
        db_session,
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    bridge = ErrorReplanBridge(db_session)

    with patch(
        "app.services.error_replan_bridge.AuroraStage34KillSwitchService.get_feature_mode",
        new=AsyncMock(return_value="live"),
    ), patch(
        "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
        new=AsyncMock(),
    ) as mock_eval, patch(
        "app.services.system_update_service.SystemUpdateService.enqueue",
        new=AsyncMock(return_value=True),
    ):
        result = await bridge.on_error_created(
            user_id=user.id,
            error_id=error.id,
            linked_node_ids=[node.id],
        )

    assert result["triggered"] is True
    assert result["threshold_applied"] == 1
    assert result["is_new_user"] is True
    assert result["mode"] == "live"
    mock_eval.assert_awaited_once_with(
        user_id=user.id,
        plan_id=plan.id,
        trigger="error_created_bridge",
        feedback_category="concept_gap_repeated",
    )


@pytest.mark.asyncio
async def test_error_replan_bridge_live_mode_keeps_mature_user_threshold(db_session) -> None:
    user, _plan, node, error = await _seed_bridge_fixture(
        db_session,
        created_at=datetime.utcnow() - timedelta(days=30),
    )
    bridge = ErrorReplanBridge(db_session)

    with patch(
        "app.services.error_replan_bridge.AuroraStage34KillSwitchService.get_feature_mode",
        new=AsyncMock(return_value="live"),
    ), patch(
        "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
        new=AsyncMock(),
    ) as mock_eval:
        result = await bridge.on_error_created(
            user_id=user.id,
            error_id=error.id,
            linked_node_ids=[node.id],
        )

    assert result["triggered"] is False
    assert result["threshold_applied"] == 3
    assert result["is_new_user"] is False
    assert result["mode"] == "live"
    mock_eval.assert_not_awaited()


@pytest.mark.asyncio
async def test_error_replan_bridge_counts_plan_health_error_category(db_session) -> None:
    user, _plan, node, error = await _seed_bridge_fixture(
        db_session,
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    bridge = ErrorReplanBridge(db_session)
    before = ERROR_REPLAN_BRIDGE_ERROR_TOTAL.labels(category="PlanHealthError", mode="live")._value.get()

    with patch(
        "app.services.error_replan_bridge.AuroraStage34KillSwitchService.get_feature_mode",
        new=AsyncMock(return_value="live"),
    ), patch(
        "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ), patch(
        "app.services.system_update_service.SystemUpdateService.enqueue",
        new=AsyncMock(return_value=True),
    ) as mock_enqueue:
        result = await bridge.on_error_created(
            user_id=user.id,
            error_id=error.id,
            linked_node_ids=[node.id],
        )

    after = ERROR_REPLAN_BRIDGE_ERROR_TOTAL.labels(category="PlanHealthError", mode="live")._value.get()
    assert result["triggered"] is False
    assert result["reason"] == "plan_health_error"
    assert after == before + 1
    assert mock_enqueue.await_count >= 1

