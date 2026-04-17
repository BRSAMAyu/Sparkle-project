from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.card_protocol import InterventionRecord, InterventionTriggerType
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.services.error_replan_bridge import ErrorReplanBridge


@pytest.mark.asyncio
async def test_error_replan_bridge_triggers_plan_health_for_repeated_concept_errors(db_session):
    user = User(
        username="bridge_user",
        email="bridge_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="热力学冲刺",
        type=PlanType.SPRINT,
        description="两周后考试",
        plan_stage=PlanStage.DAILY,
        target_date=datetime.utcnow().date() + timedelta(days=10),
        daily_available_minutes=90,
        total_estimated_hours=18,
        subject="热力学",
        mastery_level=0.3,
        progress=0.2,
        is_active=True,
        priority=PlanPriority.HIGH,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.flush()

    node = KnowledgeNode(name="可逆过程 vs 不可逆过程", description="热力学关键概念")
    db_session.add(node)
    await db_session.flush()

    db_session.add(
        UserNodeStatus(
            user_id=user.id,
            node_id=node.id,
            mastery_score=38,
            bkt_mastery_prob=0.38,
            total_minutes=0,
            total_study_minutes=0,
            study_count=0,
            is_unlocked=True,
        )
    )

    task = Task(
        user_id=user.id,
        plan_id=plan.id,
        title="整理可逆过程错题",
        type=TaskType.ERROR_FIX,
        tags=["thermodynamics"],
        estimated_minutes=30,
        difficulty=4,
        energy_cost=3,
        status=TaskStatus.PENDING,
        priority=4,
        due_date=datetime.utcnow().date() + timedelta(days=2),
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

    errors = [
        ErrorRecord(
            user_id=user.id,
            subject_code="physics",
            chapter="thermodynamics",
            question_text=f"error-{idx}",
            mastery_level=0.2,
            latest_analysis={"error_type": "concept_confusion"},
            linked_knowledge_node_ids=[str(node.id)],
            created_at=datetime.utcnow() - timedelta(days=idx),
        )
        for idx in range(3)
    ]
    db_session.add_all(errors)
    await db_session.commit()

    bridge = ErrorReplanBridge(db_session)
    with (
        patch(
            "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
            new=AsyncMock(),
        ) as mock_eval,
        patch(
            "app.services.system_update_service.SystemUpdateService.enqueue",
            new=AsyncMock(return_value=True),
        ) as mock_enqueue,
    ):
        result = await bridge.on_error_created(
            user_id=user.id,
            error_id=errors[-1].id,
            linked_node_ids=[node.id],
        )

    assert result["triggered"] is True
    assert result["reason"] == "error_pressure_bridge"
    assert result["recent_error_count"] == 3
    mock_eval.assert_awaited_once_with(
        user_id=user.id,
        plan_id=plan.id,
        trigger="error_created_bridge",
        feedback_category="concept_gap_repeated",
    )
    record = (
        await db_session.execute(
            select(InterventionRecord).where(InterventionRecord.user_id == user.id)
        )
    ).scalar_one()
    assert record.trigger_type == InterventionTriggerType.CONCEPT_GAP
    assert record.diagnosis_payload["node_name"] == node.name
    enqueue_args = mock_enqueue.await_args.args
    payload = enqueue_args[-1]
    assert payload["metadata"]["intervention_id"] == str(record.id)


@pytest.mark.asyncio
async def test_error_replan_bridge_skips_non_triggering_error_types(db_session):
    user = User(
        username="bridge_skip_user",
        email="bridge_skip_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    node = KnowledgeNode(name="熵增判断", description="概念")
    db_session.add(node)
    await db_session.flush()

    error = ErrorRecord(
        user_id=user.id,
        subject_code="physics",
        chapter="thermodynamics",
        question_text="careless",
        mastery_level=0.5,
        latest_analysis={"error_type": "calculation_error"},
        linked_knowledge_node_ids=[str(node.id)],
    )
    db_session.add(error)
    await db_session.commit()

    bridge = ErrorReplanBridge(db_session)
    with patch(
        "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
        new=AsyncMock(),
    ) as mock_eval:
        result = await bridge.on_error_created(
            user_id=user.id,
            error_id=error.id,
            linked_node_ids=[node.id],
        )

    assert result["triggered"] is False
    assert result["reason"] == "unsupported_error_type:calculation_error"
    mock_eval.assert_not_awaited()
