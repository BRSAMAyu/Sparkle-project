import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from sqlalchemy import select

from app.aurora.runtime_v1.write_pipeline import AURORA_CLAIM_KEY_TEMPLATE
from app.models.card_protocol import DeliveryChannel, DeliveryStrategy, InterventionRecord, InterventionTriggerType
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.notification import Notification
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter
from app.services.error_replan_bridge import ErrorReplanBridge
from app.services.notification_center_service import NotificationCenterService


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str) -> None:
        self.store[key] = value


@pytest.mark.asyncio
async def test_error_replan_bridge_triggers_plan_health_for_repeated_concept_errors(db_session):
    user = User(
        username="bridge_user",
        email="bridge_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        UserPreferencesCenter(
            user_id=user.id,
            explicit={
                "learning_goal_type": "exam",
                "knowledge_level": "intermediate",
                "learning_style": "balanced",
            },
        )
    )

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

    redis = _FakeRedis()
    bridge = ErrorReplanBridge(db_session, redis=redis)
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
    assert len(result["repair_task_ids"]) == 1
    mock_eval.assert_awaited_once_with(
        user_id=user.id,
        plan_id=plan.id,
        trigger="error_created_bridge",
        feedback_category="concept_gap_repeated",
    )
    record = (
        await db_session.execute(select(InterventionRecord).where(InterventionRecord.user_id == user.id))
    ).scalar_one()
    assert record.trigger_type == InterventionTriggerType.CONCEPT_GAP
    assert record.diagnosis_payload["node_name"] == node.name
    assert record.diagnosis_payload["error_type"] == "concept_confusion"
    assert record.diagnosis_payload["cohort_profile"]["goal_type"] == "exam"
    enqueue_args = mock_enqueue.await_args.args
    payload = enqueue_args[-1]
    assert payload["metadata"]["intervention_id"] == str(record.id)
    claim_key = AURORA_CLAIM_KEY_TEMPLATE.format(user_id=str(user.id), domain="weak_node")
    stored_claims = json.loads(redis.store[claim_key])
    assert str(node.id) in stored_claims["values"]
    assert stored_claims["claims"][0]["evidence_type"] == "error_replan_signal"
    assert stored_claims["claims"][0]["planning_session_id"] == str(plan.id)

    task_rows = await db_session.execute(
        select(Task).where(Task.user_id == user.id, Task.plan_id == plan.id).order_by(Task.order_index.asc())
    )
    repair_tasks = [
        task for task in task_rows.scalars().all() if (task.guide_json or {}).get("task_kind") == "targeted_repair"
    ]
    assert len(repair_tasks) == 1
    assert repair_tasks[0].estimated_minutes == 15
    assert repair_tasks[0].guide_json["daily_spec"]["task_kind"] == "targeted_repair"
    assert repair_tasks[0].guide_json["output_action"] == "闭卷复述错因 + 1 道同类题独立完成"


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
        latest_analysis={"error_type": "essay_off_topic"},
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
    assert result["reason"] == "unsupported_error_type:essay_off_topic"
    mock_eval.assert_not_awaited()


@pytest.mark.asyncio
async def test_error_replan_bridge_supports_expanded_rule_trigger_types(db_session):
    user = User(
        username="bridge_rule_user",
        email="bridge_rule_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="程序化练习",
        type=PlanType.SPRINT,
        description="方法巩固",
        plan_stage=PlanStage.DAILY,
        target_date=datetime.utcnow().date() + timedelta(days=10),
        daily_available_minutes=90,
        total_estimated_hours=12,
        subject="math",
        mastery_level=0.3,
        progress=0.2,
        is_active=True,
        priority=PlanPriority.HIGH,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.flush()

    node = KnowledgeNode(name="列方程步骤", description="程序性步骤")
    db_session.add(node)
    await db_session.flush()

    db_session.add(
        UserNodeStatus(
            user_id=user.id,
            node_id=node.id,
            mastery_score=40,
            bkt_mastery_prob=0.4,
            total_minutes=0,
            total_study_minutes=0,
            study_count=0,
            is_unlocked=True,
        )
    )
    task = Task(
        user_id=user.id,
        plan_id=plan.id,
        title="步骤化复盘",
        type=TaskType.ERROR_FIX,
        tags=["math"],
        estimated_minutes=30,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=4,
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

    errors = [
        ErrorRecord(
            user_id=user.id,
            subject_code="math",
            chapter="algebra",
            question_text=f"error-{idx}",
            mastery_level=0.2,
            latest_analysis={"error_type": "method_wrong"},
            linked_knowledge_node_ids=[str(node.id)],
            created_at=datetime.utcnow() - timedelta(days=idx),
        )
        for idx in range(3)
    ]
    db_session.add_all(errors)
    await db_session.commit()

    bridge = ErrorReplanBridge(db_session)
    with patch(
        "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
        new=AsyncMock(),
    ) as mock_eval:
        result = await bridge.on_error_created(
            user_id=user.id,
            error_id=errors[-1].id,
            linked_node_ids=[node.id],
        )

    assert result["triggered"] is True
    mock_eval.assert_awaited_once()


@pytest.mark.asyncio
async def test_error_replan_bridge_respects_plan_type_cooldown(db_session):
    user = User(
        username="bridge_cooldown_user",
        email="bridge_cooldown@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="冷静期计划",
        type=PlanType.SPRINT,
        description="冷静期测试",
        plan_stage=PlanStage.DAILY,
        target_date=datetime.utcnow().date() + timedelta(days=10),
        daily_available_minutes=90,
        total_estimated_hours=8,
        subject="physics",
        mastery_level=0.3,
        progress=0.2,
        is_active=True,
        priority=PlanPriority.HIGH,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.flush()

    node = KnowledgeNode(name="熵增判断", description="概念")
    db_session.add(node)
    await db_session.flush()
    db_session.add(
        UserNodeStatus(
            user_id=user.id,
            node_id=node.id,
            mastery_score=40,
            bkt_mastery_prob=0.4,
            total_minutes=0,
            total_study_minutes=0,
            study_count=0,
            is_unlocked=True,
        )
    )
    task = Task(
        user_id=user.id,
        plan_id=plan.id,
        title="冷静期任务",
        type=TaskType.ERROR_FIX,
        tags=["physics"],
        estimated_minutes=30,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=4,
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
    errors = [
        ErrorRecord(
            user_id=user.id,
            subject_code="physics",
            chapter="thermo",
            question_text=f"cooldown-{idx}",
            mastery_level=0.2,
            latest_analysis={"error_type": "concept_confusion"},
            linked_knowledge_node_ids=[str(node.id)],
            created_at=datetime.utcnow() - timedelta(hours=idx),
        )
        for idx in range(3)
    ]
    db_session.add_all(errors)
    await db_session.flush()
    db_session.add(
        InterventionRecord(
            user_id=user.id,
            trigger_type=InterventionTriggerType.CONCEPT_GAP,
            trigger_source_ref="error_replan_bridge",
            diagnosis_payload={"plan_ids": [str(plan.id)], "error_type": "concept_confusion"},
            delivery_strategy=DeliveryStrategy.SUPPORTIVE,
            delivery_channel=DeliveryChannel.CHAT,
        )
    )
    await db_session.commit()

    bridge = ErrorReplanBridge(db_session)
    with patch(
        "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
        new=AsyncMock(),
    ) as mock_eval:
        result = await bridge.on_error_created(
            user_id=user.id,
            error_id=errors[-1].id,
            linked_node_ids=[node.id],
        )

    assert result["triggered"] is False
    assert result["reason"] == "trigger_cooldown_active"
    mock_eval.assert_not_awaited()


@pytest.mark.asyncio
async def test_error_replan_bridge_proposes_specialized_repair_for_repeated_tcp_state_errors(db_session):
    user = User(
        username="bridge_tcp_specialized",
        email="bridge_tcp_specialized@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="计网冲刺",
        type=PlanType.SPRINT,
        description="TCP 重点补强",
        plan_stage=PlanStage.DAILY,
        target_date=datetime.utcnow().date() + timedelta(days=7),
        daily_available_minutes=90,
        total_estimated_hours=12,
        subject="计算机网络",
        mastery_level=0.4,
        progress=0.2,
        is_active=True,
        priority=PlanPriority.HIGH,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.flush()

    node = KnowledgeNode(name="TCP 三次握手", description="连接建立状态变化")
    db_session.add(node)
    await db_session.flush()

    db_session.add(
        UserNodeStatus(
            user_id=user.id,
            node_id=node.id,
            mastery_score=72,
            bkt_mastery_prob=0.72,
            total_minutes=0,
            total_study_minutes=0,
            study_count=0,
            is_unlocked=True,
        )
    )

    task = Task(
        user_id=user.id,
        plan_id=plan.id,
        title="TCP 连接建立专项",
        type=TaskType.LEARNING,
        tags=["network"],
        estimated_minutes=45,
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

    errors = [
        ErrorRecord(
            user_id=user.id,
            subject_code="computer",
            chapter="transport",
            question_text=text,
            mastery_level=0.2,
            latest_analysis={
                "error_type": "concept_confusion",
                "root_cause": "TCP 三次握手状态变化总是混淆",
                "study_suggestions": "重画三次握手状态图",
            },
            linked_knowledge_node_ids=[str(node.id)],
            created_at=datetime.utcnow() - timedelta(minutes=index),
        )
        for index, text in enumerate(
            [
                "TCP 三次握手里 SYN-SENT 到 ESTABLISHED 的状态变化总记错",
                "又做错了一道 TCP 三次握手状态转换题，SYN/ACK 顺序还是混淆",
                "TCP 三次握手状态变化题第三次做错，seq/ack 和状态名总对不上",
            ]
        )
    ]
    db_session.add_all(errors)
    await db_session.commit()

    bridge = ErrorReplanBridge(db_session)
    with patch(
        "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
        new=AsyncMock(),
    ) as mock_eval:
        result = await bridge.on_error_created(
            user_id=user.id,
            error_id=errors[-1].id,
            linked_node_ids=[node.id],
        )

    assert result["triggered"] is True
    assert result["reason"] == "specialized_error_repair"
    assert result["repair_cluster_id"] == "mistake.three_way_state"
    assert result["repair_cluster_source"] == "sprint_pack"
    assert result["same_cluster_streak"] == 3
    mock_eval.assert_not_awaited()

    record = (
        await db_session.execute(
            select(InterventionRecord)
            .where(InterventionRecord.user_id == user.id)
            .order_by(InterventionRecord.created_at.desc())
        )
    ).scalar_one()
    assert record.diagnosis_payload["specialized_repair"] is True
    assert record.diagnosis_payload["cluster_id"] == "mistake.three_way_state"
    assert record.diagnosis_payload["related_nodes"] == ["cn.tcp_three_way"]
    assert record.diagnosis_payload["repair_task"]["repair_cluster_label"] == "三次握手状态/标志位错误"

    notification = (
        await db_session.execute(
            select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc())
        )
    ).scalar_one()
    assert notification.type == "intervention"
    assert notification.data["record_id"] == str(record.id)
    assert notification.data["schedule_options"][0]["action_payload"]["schedule"] == "today"


@pytest.mark.asyncio
async def test_error_replan_bridge_falls_back_to_generic_keyword_cluster_without_sprint_pack(db_session):
    user = User(
        username="bridge_generic_specialized",
        email="bridge_generic_specialized@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="物理冲刺",
        type=PlanType.SPRINT,
        description="单位换算专项",
        plan_stage=PlanStage.DAILY,
        target_date=datetime.utcnow().date() + timedelta(days=7),
        daily_available_minutes=60,
        total_estimated_hours=8,
        subject="physics",
        mastery_level=0.3,
        progress=0.2,
        is_active=True,
        priority=PlanPriority.HIGH,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.flush()

    node = KnowledgeNode(name="速度单位换算", description="m/s 与 km/h")
    db_session.add(node)
    await db_session.flush()

    db_session.add(
        UserNodeStatus(
            user_id=user.id,
            node_id=node.id,
            mastery_score=68,
            bkt_mastery_prob=0.68,
            total_minutes=0,
            total_study_minutes=0,
            study_count=0,
            is_unlocked=True,
        )
    )

    task = Task(
        user_id=user.id,
        plan_id=plan.id,
        title="速度与加速度题",
        type=TaskType.TRAINING,
        tags=["physics"],
        estimated_minutes=30,
        difficulty=2,
        energy_cost=1,
        status=TaskStatus.PENDING,
        priority=2,
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

    errors = [
        ErrorRecord(
            user_id=user.id,
            subject_code="physics",
            chapter="kinematics",
            question_text=text,
            mastery_level=0.2,
            latest_analysis={
                "error_type": "concept_confusion",
                "root_cause": "单位换算还是会混",
                "study_suggestions": "把单位换算链条写清楚",
            },
            linked_knowledge_node_ids=[str(node.id)],
            created_at=datetime.utcnow() - timedelta(minutes=index),
        )
        for index, text in enumerate(
            [
                "速度单位换算又错了，m/s 和 km/h 总换反",
                "第二道题还是错在单位换算，米每秒和千米每小时没统一",
                "第三次在单位换算上出错，公式没问题但单位换算错了",
            ]
        )
    ]
    db_session.add_all(errors)
    await db_session.commit()

    bridge = ErrorReplanBridge(db_session)
    with patch(
        "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
        new=AsyncMock(),
    ) as mock_eval:
        result = await bridge.on_error_created(
            user_id=user.id,
            error_id=errors[-1].id,
            linked_node_ids=[node.id],
        )

    assert result["triggered"] is True
    assert result["reason"] == "specialized_error_repair"
    assert result["repair_cluster_id"] == "generic.unit_conversion"
    assert result["repair_cluster_source"] == "generic_keyword"
    mock_eval.assert_not_awaited()

    record = (
        await db_session.execute(
            select(InterventionRecord)
            .where(InterventionRecord.user_id == user.id)
            .order_by(InterventionRecord.created_at.desc())
        )
    ).scalar_one()
    assert record.diagnosis_payload["cluster_source"] == "generic_keyword"
    assert record.diagnosis_payload["repair_task"]["related_nodes"] == [str(node.id)]


@pytest.mark.asyncio
async def test_accepting_specialized_repair_intervention_materializes_task_card(db_session):
    user = User(
        username="bridge_accept_specialized",
        email="bridge_accept_specialized@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="计网专项计划",
        type=PlanType.SPRINT,
        description="专项修复接受测试",
        plan_stage=PlanStage.DAILY,
        target_date=datetime.utcnow().date() + timedelta(days=7),
        daily_available_minutes=90,
        total_estimated_hours=10,
        subject="计算机网络",
        mastery_level=0.4,
        progress=0.2,
        is_active=True,
        priority=PlanPriority.HIGH,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.flush()

    node = KnowledgeNode(name="TCP 三次握手", description="连接建立")
    db_session.add(node)
    await db_session.flush()

    db_session.add(
        UserNodeStatus(
            user_id=user.id,
            node_id=node.id,
            mastery_score=75,
            bkt_mastery_prob=0.75,
            total_minutes=0,
            total_study_minutes=0,
            study_count=0,
            is_unlocked=True,
        )
    )

    original_task = Task(
        user_id=user.id,
        plan_id=plan.id,
        title="原有学习任务",
        type=TaskType.LEARNING,
        tags=["network"],
        estimated_minutes=40,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=2,
        due_date=datetime.utcnow().date() + timedelta(days=2),
        knowledge_node_id=node.id,
        source_planning_session_id="plan-session-1",
        phase_index=2,
    )
    db_session.add(original_task)
    await db_session.flush()
    db_session.add(
        TaskKnowledgeLink(
            task_id=original_task.id,
            knowledge_node_id=node.id,
            relation_type="prerequisite",
            is_primary=True,
        )
    )

    errors = [
        ErrorRecord(
            user_id=user.id,
            subject_code="computer",
            chapter="transport",
            question_text=text,
            mastery_level=0.2,
            latest_analysis={
                "error_type": "concept_confusion",
                "root_cause": "三次握手状态变化总错",
                "study_suggestions": "重画状态图",
            },
            linked_knowledge_node_ids=[str(node.id)],
            created_at=datetime.utcnow() - timedelta(minutes=index),
        )
        for index, text in enumerate(
            [
                "第一道 TCP 三次握手状态变化题做错",
                "第二道 TCP 三次握手状态转换题还是错",
                "第三次在 TCP 三次握手状态变化上出错",
            ]
        )
    ]
    db_session.add_all(errors)
    await db_session.commit()

    bridge = ErrorReplanBridge(db_session)
    with patch(
        "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
        new=AsyncMock(),
    ):
        result = await bridge.on_error_created(
            user_id=user.id,
            error_id=errors[-1].id,
            linked_node_ids=[node.id],
        )

    record_id = result["intervention_id"]
    notification_id = result["notification_id"]
    assert record_id is not None
    assert notification_id is not None

    transitioned = await NotificationCenterService(db_session).transition_intervention_notification(
        user_id=user.id,
        notification_id=UUID(str(notification_id)),
        action="accepted",
        action_payload={"schedule": "tomorrow"},
    )
    assert transitioned is True

    rows = await db_session.execute(
        select(Task).where(Task.user_id == user.id, Task.plan_id == plan.id).order_by(Task.created_at.asc())
    )
    tasks = list(rows.scalars().all())
    specialized = [task for task in tasks if task.title.startswith("[专项修复]")]
    assert len(specialized) == 1
    assert specialized[0].type == TaskType.ERROR_FIX
    assert specialized[0].due_date == datetime.utcnow().date() + timedelta(days=1)
    assert specialized[0].priority > original_task.priority
    assert specialized[0].guide_json["repair_cluster_id"] == "mistake.three_way_state"
    assert specialized[0].guide_json["related_nodes"] == ["cn.tcp_three_way"]
    assert original_task.due_date == datetime.utcnow().date() + timedelta(days=2)

    record = await db_session.get(InterventionRecord, UUID(str(record_id)))
    assert record is not None
    assert record.action_payload["repair_task_id"] == str(specialized[0].id)
    assert record.action_payload["repair_schedule"] == "tomorrow"
