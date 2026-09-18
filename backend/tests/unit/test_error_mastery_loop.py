from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.services.error_replan_bridge import ErrorReplanBridge


@pytest.mark.parametrize(
    ("raw_error_type", "classified"),
    [
        ("concept_confusion", "concept_confusion"),
        ("repeated_mistake", "repeated_mistake"),
        ("baseline_gap", "baseline_gap"),
        ("comprehension_failure", "comprehension_failure"),
        ("time_pressure_miss", "time_pressure_miss"),
        ("knowledge_transfer_fail", "knowledge_transfer_fail"),
        ("prerequisite_missing", "prerequisite_missing"),
        ("careless_error", "careless_error"),
    ],
)
def test_expanded_error_types_are_recognized(raw_error_type, classified):
    bridge = ErrorReplanBridge(db=None)

    assert bridge._classify_trigger_type_from_analysis({"error_type": raw_error_type}) == classified
    assert classified in bridge.TRIGGERING_ERROR_TYPES


@pytest.mark.asyncio
async def test_error_diagnosis_clamps_at_floor_and_defers_mastery_event(db_session):
    """错误→掌握度链路（迁移自已删除的 GalaxyService.update_mastery_from_error）。

    clean-slate 后掌握度写入统一由 ErrorBookMasterySyncService 负责：
    - 单次错题扣分受 [0, 100] 钳制（旧 API 的地板是 10，新契约地板是 0）；
    - 不再直接 publish "mastery_updated_from_error"，而是把 node_mastery_updated
      事件随结果返回（_pending_event），由调用方在 commit 后投递。
    """
    from app.services.error_book_mastery_sync_service import ErrorBookMasterySyncService

    user = User(username="mastery_floor_user", email="mastery-floor@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()

    node = KnowledgeNode(name="热力学过程", description="过程判断")
    db_session.add(node)
    await db_session.flush()

    db_session.add(
        UserNodeStatus(
            user_id=user.id,
            node_id=node.id,
            mastery_score=5,
            bkt_mastery_prob=0.05,
            total_minutes=0,
            total_study_minutes=0,
            study_count=0,
            is_unlocked=True,
        )
    )
    error = ErrorRecord(
        user_id=user.id,
        subject_code="physics",
        chapter="thermodynamics",
        question_text="mastery-floor-error-1",
        mastery_level=0.2,
        latest_analysis={"error_type": "knowledge_gap"},
        linked_knowledge_node_ids=[str(node.id)],
    )
    db_session.add_all([error])
    await db_session.flush()

    results = await ErrorBookMasterySyncService(db_session).apply_error_diagnosis(user.id, error)

    assert len(results) == 1
    assert results[0]["node_id"] == str(node.id)
    assert results[0]["old_mastery"] == 5
    assert results[0]["new_mastery"] == 0  # 5 + knowledge_gap(-10) → 钳制在地板 0
    assert results[0]["delta"] == -5
    assert results[0]["record_type"] == "error_diagnosis"

    # 掌握度事件随结果延迟投递（旧 API 在这里直接 event_bus.publish）
    pending = results[0]["_pending_event"]
    assert pending["topic"] == "node_mastery_updated"
    payload = pending["payload"]
    assert payload["event_type"] == "node_mastery_updated"
    assert payload["node_id"] == str(node.id)
    assert payload["old_mastery"] == 5
    assert payload["new_mastery"] == 0
    assert payload["reason"] == "error_diagnosis:knowledge_gap"

    status = (
        await db_session.execute(
            select(UserNodeStatus).where(UserNodeStatus.user_id == user.id, UserNodeStatus.node_id == node.id)
        )
    ).scalar_one()
    assert status.mastery_score == 0
    assert status.revision == 1


@pytest.mark.asyncio
async def test_error_diagnosis_without_linked_node_returns_empty_and_hint(db_session):
    """无法关联知识节点的错题不得写入任何掌握度（迁移自 update_mastery_from_error 返回 None 分支）。"""
    from app.services.error_book_mastery_sync_service import ErrorBookMasterySyncService

    user = User(username="missing_node_user", email="missing-node@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()

    error = ErrorRecord(
        user_id=user.id,
        subject_code="physics",
        chapter="thermodynamics",
        question_text="missing-node-error-1",
        mastery_level=0.2,
        latest_analysis=None,
        linked_knowledge_node_ids=None,
    )
    db_session.add(error)
    await db_session.flush()

    results = await ErrorBookMasterySyncService(db_session).apply_error_diagnosis(user.id, error)

    assert results == []
    assert error.latest_analysis["linking_hint"]["code"] == "missing_knowledge_links"

    statuses = (
        await db_session.execute(select(UserNodeStatus).where(UserNodeStatus.user_id == user.id))
    ).scalars().all()
    assert statuses == []


async def _seed_replan_context(
    db_session,
    *,
    username: str,
    mastery_score: float,
    analyses: list[dict[str, object]],
) -> tuple[User, Plan, KnowledgeNode, list[ErrorRecord]]:
    user = User(username=username, email=f"{username}@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name=f"{username} 计划",
        type=PlanType.SPRINT,
        description="错题回路测试",
        plan_stage=PlanStage.DAILY,
        target_date=datetime.utcnow().date() + timedelta(days=10),
        daily_available_minutes=90,
        total_estimated_hours=10,
        subject="physics",
        mastery_level=0.3,
        progress=0.2,
        is_active=True,
        priority=PlanPriority.HIGH,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.flush()

    node = KnowledgeNode(name="热力学过程", description="热力学关键节点")
    db_session.add(node)
    await db_session.flush()

    db_session.add(
        UserNodeStatus(
            user_id=user.id,
            node_id=node.id,
            mastery_score=mastery_score,
            bkt_mastery_prob=mastery_score / 100.0,
            total_minutes=0,
            total_study_minutes=0,
            study_count=0,
            is_unlocked=True,
        )
    )

    task = Task(
        user_id=user.id,
        plan_id=plan.id,
        title="热力学过程错题复盘",
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
            question_text=f"{username}-error-{idx}",
            mastery_level=0.2,
            latest_analysis=analysis,
            linked_knowledge_node_ids=[str(node.id)],
            created_at=datetime.utcnow() - timedelta(minutes=idx),
        )
        for idx, analysis in enumerate(analyses)
    ]
    db_session.add_all(errors)
    await db_session.commit()
    return user, plan, node, errors


@pytest.mark.asyncio
async def test_replan_bridge_uses_existing_mastery_without_second_deduction(db_session):
    user, plan, node, errors = await _seed_replan_context(
        db_session,
        username="repeated_mastery_user",
        mastery_score=37,
        analyses=[
            {"error_type": "baseline_gap"},
            {"error_type": "knowledge_transfer_fail"},
            {"error_type": "comprehension_failure"},
        ],
    )

    bridge = ErrorReplanBridge(db_session)
    with (
        patch(
            "app.services.error_replan_bridge.AuroraStage38KillSwitchService.get_feature_mode",
            new=AsyncMock(return_value="live"),
        ),
        patch("app.services.galaxy_service.event_bus.publish", new=AsyncMock()),
        patch(
            "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
            new=AsyncMock(),
        ) as mock_eval,
        patch("app.services.system_update_service.SystemUpdateService.enqueue", new=AsyncMock(return_value=True)),
    ):
        result = await bridge.on_error_created(
            user_id=user.id,
            error_id=errors[-1].id,
            linked_node_ids=[node.id],
        )

    assert result["triggered"] is True
    assert result["recent_error_count"] == 3
    assert result["mastery_update"] is None
    mock_eval.assert_awaited_once_with(
        user_id=user.id,
        plan_id=plan.id,
        trigger="error_created_bridge",
        feedback_category="concept_gap_repeated",
    )

    status = (
        await db_session.execute(
            select(UserNodeStatus).where(UserNodeStatus.user_id == user.id, UserNodeStatus.node_id == node.id)
        )
    ).scalar_one()
    assert status.mastery_score == 37.0


@pytest.mark.asyncio
async def test_two_high_severity_errors_on_same_node_trigger_replan(db_session):
    user, plan, node, errors = await _seed_replan_context(
        db_session,
        username="high_severity_user",
        mastery_score=70,
        analyses=[
            {"error_type": "baseline_gap", "severity": "high"},
            {"error_type": "baseline_gap", "severity": "high"},
        ],
    )

    bridge = ErrorReplanBridge(db_session)
    with (
        patch(
            "app.services.error_replan_bridge.AuroraStage38KillSwitchService.get_feature_mode",
            new=AsyncMock(return_value="live"),
        ),
        patch("app.services.galaxy_service.event_bus.publish", new=AsyncMock()),
        patch(
            "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
            new=AsyncMock(),
        ) as mock_eval,
        patch("app.services.system_update_service.SystemUpdateService.enqueue", new=AsyncMock(return_value=True)),
    ):
        result = await bridge.on_error_created(
            user_id=user.id,
            error_id=errors[-1].id,
            linked_node_ids=[node.id],
        )

    assert result["triggered"] is True
    assert result["threshold_applied"] == 2
    mock_eval.assert_awaited_once_with(
        user_id=user.id,
        plan_id=plan.id,
        trigger="error_created_bridge",
        feedback_category="concept_gap_repeated",
    )


@pytest.mark.asyncio
async def test_careless_error_updates_mastery_but_does_not_replan(db_session):
    user, _plan, node, errors = await _seed_replan_context(
        db_session,
        username="careless_error_user",
        mastery_score=25,
        analyses=[
            {"error_type": "careless_error"},
            {"error_type": "careless_error"},
            {"error_type": "careless_error"},
        ],
    )

    bridge = ErrorReplanBridge(db_session)
    with (
        patch(
            "app.services.error_replan_bridge.AuroraStage38KillSwitchService.get_feature_mode",
            new=AsyncMock(return_value="live"),
        ),
        patch("app.services.galaxy_service.event_bus.publish", new=AsyncMock()),
        patch(
            "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
            new=AsyncMock(),
        ) as mock_eval,
    ):
        result = await bridge.on_error_created(
            user_id=user.id,
            error_id=errors[-1].id,
            linked_node_ids=[node.id],
        )

    assert result["triggered"] is False
    assert result["reason"] == "careless_error_no_replan"
    assert result["mastery_update"] is None
    mock_eval.assert_not_awaited()

    status = (
        await db_session.execute(
            select(UserNodeStatus).where(UserNodeStatus.user_id == user.id, UserNodeStatus.node_id == node.id)
        )
    ).scalar_one()
    assert status.mastery_score == 25.0
