from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.runtime_v1.chat_adapter import ChatLayerAdapter
from app.aurora.runtime_v1.decision_loop import AuroraDecisionLoop
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.aurora.runtime_v1.write_pipeline import get_claim
from app.core.celery_tasks import _run_spaced_repetition_reminders_for_user
from app.models.achievement import Achievement, AchievementRarity, AchievementType, UserAchievement, UserStreakStats
from app.models.card_protocol import InterventionRecord
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.notification import Notification
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_feedback import TaskFeedback
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.orchestration.exam_sprint_policy import ExamSprintPolicyEngine, ExamSprintPolicyInput
from app.orchestration.planning_workflow import PlanningWorkflowManager
from app.schemas.exam_sprint import (
    ExamSprintBaselineInput,
    ExamSprintIntakeRequest,
    ExamSprintScopeContext,
    HelpfulFeature,
    PostExamReviewRequest,
    ReviewPlanSelection,
    ReviewTopicSelection,
)
from app.schemas.task import TaskCreate
from app.services.achievement_event_consumer import AchievementEventConsumer
from app.services.error_replan_bridge import ErrorReplanBridge
from app.services.exam_sprint_review_service import ExamSprintReviewService
from app.services.galaxy_service import GalaxyService
from app.services.memory_service import MemoryService
from app.services.notification_service import NotificationService
from app.services.progress_narrative_service import ProgressNarrativeService, WeeklyGrowthNarrative
from app.services.task_service import TaskService

try:
    from fakeredis.aioredis import FakeRedis as _FakeRedisImpl
except Exception:  # pragma: no cover - local fallback when fakeredis is unavailable
    _FakeRedisImpl = None


pytestmark = pytest.mark.asyncio


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class _FallbackFakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, *, ex: int | None = None, nx: bool = False):
        del ex
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    async def setex(self, key: str, _ttl: int, value: str) -> bool:
        self.store[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self.store:
                removed += 1
                self.store.pop(key, None)
        return removed

    async def expire(self, key: str, _ttl: int) -> bool:
        return key in self.store

    async def ping(self) -> bool:
        return True

    async def flushdb(self) -> None:
        self.store.clear()

    async def aclose(self) -> None:
        return None


class _FakeJsonLLM:
    def __init__(self, payload):
        self.payload = payload

    async def chat_json(self, messages, **kwargs):
        del messages, kwargs
        return self.payload


class _IntentEchoChatAdapter:
    async def render(self, decision, readout) -> list[str]:
        del readout
        return [str((decision.chat_directive or {}).get("intent") or decision.action)]


class _SessionCM:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False


@dataclass(frozen=True)
class JourneyModels:
    intake: ExamSprintIntakeRequest
    review_request: PostExamReviewRequest


async def _create_user(db_session: AsyncSession, prefix: str) -> User:
    suffix = uuid4().hex[:8]
    user = User(
        username=f"{prefix}_{suffix}",
        email=f"{prefix}_{suffix}@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def fakeredis_client():
    client = _FakeRedisImpl(decode_responses=True) if _FakeRedisImpl is not None else _FallbackFakeRedis()
    yield client
    if hasattr(client, "flushdb"):
        await client.flushdb()
    if hasattr(client, "aclose"):
        await client.aclose()


@pytest.fixture
def journey_models() -> JourneyModels:
    intake = ExamSprintIntakeRequest(
        subject="计算机网络",
        exam_date=date(2026, 5, 2),
        target_mode="pass",
        scope_context=ExamSprintScopeContext(text="主要考传输层、网络层、应用层"),
        baseline=ExamSprintBaselineInput(current_level=0, weak_chapters=["传输层", "网络层"]),
        daily_study_minutes=120,
        conversation_id="north-star-journey",
    )
    review_request = PostExamReviewRequest(
        self_rating=8,
        sparkle_helped=True,
        helpful_features=[HelpfulFeature.ERROR_REVIEW, HelpfulFeature.STRATEGY_ADJUSTMENT],
        underprepared_topics=[ReviewTopicSelection(node_name="TCP 拥塞控制")],
        prepared_but_not_tested_topics=[ReviewPlanSelection(label="Day 7 · 综合回看")],
    )
    return JourneyModels(intake=intake, review_request=review_request)


def _build_modeling_output(intake: ExamSprintIntakeRequest) -> dict[str, object]:
    goal_raw = f"零基础用户要在 {(intake.exam_date - date(2026, 4, 25)).days} 天后通过{intake.subject}考试"
    cold_start_context = {
        "goal_raw": goal_raw,
        "goal_type": "exam",
        "subject": intake.subject,
        "exam_scope": intake.scope_context.text,
        "knowledge_baseline": "完全没学过",
        "time_available": "每天约 2 小时",
        "daily_available_hours": intake.daily_study_minutes // 60,
        "time_constraint_days": 7,
        "motivation": "7 天后通过考试",
    }
    return {
        "activity_profile": {"conversation_style": "warm", "task_density_hint": 0.4},
        "user_model_snapshot": {
            "subject": intake.subject,
            "goal_raw": goal_raw,
            "knowledge_baseline": "完全没学过",
            "daily_available_hours": intake.daily_study_minutes // 60,
            "time_constraint_days": 7,
            "preferences": {"cold_start_context": cold_start_context},
        },
        "cold_start_context": cold_start_context,
        "galaxy_baseline": {"weak_nodes": [], "mastery_snapshot": {}},
    }


async def _create_bridged_plan(
    *,
    db_session: AsyncSession,
    user_id: UUID,
    redis_client,
    monkeypatch,
    intake: ExamSprintIntakeRequest,
    conversation_id: str,
) -> tuple[dict, dict, Plan, list[Task]]:
    from app.orchestration import bottleneck_analyzer as bottleneck_module

    monkeypatch.setattr(
        bottleneck_module.bottleneck_analyzer,
        "analyze",
        AsyncMock(side_effect=RuntimeError("force deterministic fallback")),
    )
    monkeypatch.setattr("app.services.task_service._sync_task_card_projection", AsyncMock(return_value=None))
    monkeypatch.setattr("app.services.plan_service._sync_plan_card_projection", AsyncMock(return_value=None))
    monkeypatch.setattr(
        "app.services.plan_quota_service.PlanQuotaService.check_and_raise", AsyncMock(return_value=None)
    )

    manager = PlanningWorkflowManager(redis_client=redis_client)
    modeling_output = _build_modeling_output(intake)

    first = await manager.process_planning_turn(
        db=db_session,
        user_id=user_id,
        chat_session_id=conversation_id,
        message=f"7天后考{intake.subject}，从没学过，每天2小时，直接开始规划。",
        context={"from_modeling_complete": True, "modeling_output": modeling_output},
    )
    confirm = first

    plan = (
        (await db_session.execute(select(Plan).where(Plan.user_id == user_id).order_by(Plan.created_at.desc())))
        .scalars()
        .first()
    )
    tasks = list(
        (
            await db_session.execute(
                select(Task).where(Task.plan_id == plan.id).order_by(Task.order_index.asc(), Task.created_at.asc())
            )
        ).scalars()
    )
    return first, confirm, plan, tasks


async def _seed_mid_mastery_node(
    db_session: AsyncSession,
    *,
    user_id: UUID,
    mastery: float,
    days_ago: int,
    now: datetime,
    node_name: str = "TCP 流量控制",
) -> KnowledgeNode:
    node = KnowledgeNode(name=node_name, description="networking basics")
    db_session.add(node)
    await db_session.flush()
    db_session.add(
        UserNodeStatus(
            user_id=user_id,
            node_id=node.id,
            mastery_score=mastery,
            bkt_mastery_prob=mastery,
            is_unlocked=True,
            last_interacted_at=now - timedelta(days=days_ago),
            updated_at=now - timedelta(days=days_ago),
        )
    )
    await db_session.commit()
    return node


class TestNorthStarJourney:
    async def test_cold_start_aurora_modeling_completes(self, fakeredis_client):
        service = AuroraRuntimeV1Service(
            redis_client=fakeredis_client,
            decision_loop=AuroraDecisionLoop(
                llm_factory=lambda: _FakeJsonLLM(
                    {
                        "action": "emit_message",
                        "surface_complete": False,
                        "modeling_complete": False,
                        "chat_directive": {"intent": "continue_modeling", "target_domain": "time"},
                    }
                )
            ),
            chat_adapter=ChatLayerAdapter(
                llm_factory=lambda: _FakeJsonLLM({"messages": ["信息够用了。接下来我可以直接按这个状态给你做规划。"]})
            ),
        )

        plan = await service.plan_turn(
            active_db=None,
            user_id="north-star-user",
            surface="aurora_modeling",
            conversation_id="north-star-modeling",
            request_id="req-modeling-complete",
            user_message="每天3小时，主要考传输层和网络层。",
            request_extra_context={
                "task_state": {
                    "goal_raw": "7天后通过计网考试",
                    "subject": "计算机网络",
                    "knowledge_baseline": "从没系统学过",
                    "daily_available_hours": 3,
                },
                "informational_tensions": [
                    {"domain": "goal", "status": "resolved"},
                    {"domain": "exam_scope", "status": "resolved"},
                    {"domain": "knowledge_baseline", "status": "resolved"},
                    {"domain": "time_available", "status": "resolved"},
                ],
            },
            conversation_context={},
            user_context_payload={},
        )

        claim = await get_claim("modeling_complete", redis=fakeredis_client, user_id="north-star-user")
        assert plan.modeling_complete is True
        assert plan.surface_complete is True
        assert claim is not None
        assert claim.value is True

    async def test_modeling_to_plan_auto_bridge(
        self,
        db_session: AsyncSession,
        fakeredis_client,
        journey_models: JourneyModels,
        monkeypatch,
    ):
        user = await _create_user(db_session, "journey_bridge")
        first, confirm, plan, tasks = await _create_bridged_plan(
            db_session=db_session,
            user_id=user.id,
            redis_client=fakeredis_client,
            monkeypatch=monkeypatch,
            intake=journey_models.intake,
            conversation_id="north-star-bridge",
        )

        assert any(widget["type"] == "plan_card" for widget in first["widgets"])
        assert confirm["message"].startswith("方案已经确认")
        assert plan.subject == "计算机网络"
        assert plan.type == PlanType.SPRINT
        assert tasks

    async def test_sprint_pack_injected_into_plan(
        self,
        db_session: AsyncSession,
        fakeredis_client,
        journey_models: JourneyModels,
        monkeypatch,
    ):
        user = await _create_user(db_session, "journey_pack")
        _, _, _plan, tasks = await _create_bridged_plan(
            db_session=db_session,
            user_id=user.id,
            redis_client=fakeredis_client,
            monkeypatch=monkeypatch,
            intake=journey_models.intake,
            conversation_id="north-star-sprint-pack",
        )

        first_task = tasks[0]
        guide_json = dict(first_task.guide_json or {})
        sprint_pack_nodes = list(guide_json.get("sprint_pack_nodes") or [])

        assert sprint_pack_nodes
        assert all(str(item["node_id"]).startswith("cn.") for item in sprint_pack_nodes)
        assert list(guide_json.get("knowledge_node_ids") or [])

    async def test_task_completion_updates_galaxy_mastery(self, db_session: AsyncSession, monkeypatch):
        user = await _create_user(db_session, "journey_mastery")
        monkeypatch.setattr("app.services.task_service._sync_task_card_projection", AsyncMock(return_value=None))
        monkeypatch.setattr("app.services.task_service.event_bus_reliable.publish", AsyncMock(return_value=None))
        monkeypatch.setattr("app.services.task_service.publish_srl_event", AsyncMock(return_value=None))

        task = await TaskService.create(
            db=db_session,
            obj_in=TaskCreate(
                title="Day 1 · TCP 流量控制",
                type=TaskType.LEARNING,
                tags=["exam_sprint"],
                estimated_minutes=30,
                difficulty=2,
                energy_cost=2,
                guide_json={
                    "sprint_mode": "seven_day_survival",
                    "sprint_pack_nodes": [{"node_id": "cn.tcp_flow_control", "label": "TCP 流量控制"}],
                    "knowledge_node_ids": ["cn.tcp_flow_control"],
                },
            ),
            user_id=user.id,
        )

        await TaskService.start(db_session, task)
        await TaskService.complete(db_session, task, actual_minutes=25)
        mastery = await GalaxyService(db_session).get_sprint_mastery_summary(user.id, ["cn.tcp_flow_control"])

        assert mastery["cn.tcp_flow_control"] == pytest.approx(0.25)

    async def test_stuck_trigger_aurora_diagnosis(self):
        service = AuroraRuntimeV1Service(
            decision_loop=AuroraDecisionLoop(
                llm_factory=lambda: _FakeJsonLLM(
                    {
                        "action": "emit_message",
                        "chat_directive": {"intent": "continue_current_task"},
                    }
                )
            ),
            chat_adapter=_IntentEchoChatAdapter(),
        )

        plan = await service.plan_turn(
            active_db=None,
            user_id="north-star-user",
            surface="aurora_planning",
            conversation_id="north-star-stuck",
            request_id="req-stuck",
            user_message="我还是卡在 TCP 状态机。",
            request_extra_context={"task_state": {"stage": "stuck", "stuck_topic": "TCP状态机"}},
            conversation_context={},
            user_context_payload={},
        )

        assert plan.messages == ["diagnose_stuck_point"]

    async def test_error_creates_repair_task(self, db_session: AsyncSession, fakeredis_client, monkeypatch):
        user = await _create_user(db_session, "journey_error")

        db_session.add(
            UserPreferencesCenter(
                user_id=user.id,
                explicit={"learning_goal_type": "exam", "knowledge_level": "intermediate"},
            )
        )
        plan = Plan(
            user_id=user.id,
            name="计网冲刺",
            type=PlanType.SPRINT,
            description="7 天计划",
            plan_stage=PlanStage.DAILY,
            target_date=date(2026, 5, 2),
            daily_available_minutes=120,
            total_estimated_hours=14,
            subject="计算机网络",
            mastery_level=0.2,
            progress=0.1,
            is_active=True,
            priority=PlanPriority.HIGH,
            is_primary=True,
            source_metadata={"day_highlights": {"day": 1, "recommendation": "先保底"}},
        )
        db_session.add(plan)
        await db_session.flush()

        node = KnowledgeNode(name="TCP 状态机", description="关键易错点")
        db_session.add(node)
        await db_session.flush()

        db_session.add(
            UserNodeStatus(
                user_id=user.id,
                node_id=node.id,
                mastery_score=38,
                bkt_mastery_prob=0.38,
                is_unlocked=True,
            )
        )
        base_task = Task(
            user_id=user.id,
            plan_id=plan.id,
            title="Day 2 · TCP 确认号",
            type=TaskType.LEARNING,
            tags=["day:2"],
            estimated_minutes=45,
            difficulty=3,
            energy_cost=2,
            status=TaskStatus.PENDING,
            priority=1,
            order_index=2000,
        )
        db_session.add(base_task)
        await db_session.flush()
        db_session.add(
            TaskKnowledgeLink(
                task_id=base_task.id,
                knowledge_node_id=node.id,
                relation_type="focus",
                is_primary=True,
            )
        )

        errors = [
            ErrorRecord(
                user_id=user.id,
                subject_code="network",
                chapter="transport",
                question_text=f"error-{idx}",
                mastery_level=0.2,
                latest_analysis={"error_type": "concept_confusion"},
                linked_knowledge_node_ids=[str(node.id)],
                created_at=_utcnow() - timedelta(days=idx),
            )
            for idx in range(3)
        ]
        db_session.add_all(errors)
        await db_session.commit()

        bridge = ErrorReplanBridge(db_session, redis=fakeredis_client)
        with (
            patch(
                "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
                new=AsyncMock(return_value=[]),
            ),
            patch("app.services.system_update_service.SystemUpdateService.enqueue", new=AsyncMock(return_value=True)),
        ):
            result = await bridge.on_error_created(
                user_id=user.id,
                error_id=errors[-1].id,
                linked_node_ids=[node.id],
            )

        repair_tasks = list(
            (
                await db_session.execute(
                    select(Task).where(Task.plan_id == plan.id).order_by(Task.order_index.asc(), Task.created_at.asc())
                )
            ).scalars()
        )
        targeted = [task for task in repair_tasks if dict(task.guide_json or {}).get("task_kind") == "targeted_repair"]

        assert result["triggered"] is True
        assert len(targeted) == 1
        assert targeted[0].title == "修复昨日错题：TCP 状态机"
        assert targeted[0].guide_json["daily_spec"]["task_kind"] == "targeted_repair"

    async def test_adaptive_compression_low_completion(self, db_session: AsyncSession, test_user: User):
        plan = Plan(
            user_id=test_user.id,
            name="7天计网冲刺",
            type=PlanType.SPRINT,
            description="冲刺计划",
            plan_stage=PlanStage.SPRINT,
            subject="计算机网络",
            target_date=date(2026, 5, 2),
            is_active=True,
            source_metadata={},
        )
        db_session.add(plan)
        await db_session.flush()
        db_session.add_all(
            [
                Task(
                    user_id=test_user.id,
                    plan_id=plan.id,
                    title="Day 5 · TCP 拥塞控制",
                    type=TaskType.LEARNING,
                    status=TaskStatus.PENDING,
                    estimated_minutes=60,
                    difficulty=3,
                    energy_cost=3,
                    order_index=5000,
                    guide_json={"task_kind": "retrieval_drill"},
                ),
                Task(
                    user_id=test_user.id,
                    plan_id=plan.id,
                    title="Day 5 · TCP 流量控制",
                    type=TaskType.LEARNING,
                    status=TaskStatus.PENDING,
                    estimated_minutes=45,
                    difficulty=3,
                    energy_cost=2,
                    order_index=5001,
                    guide_json={"task_kind": "retrieval_drill"},
                ),
            ]
        )
        await db_session.commit()

        replanner = AdaptiveReplanner(db_session, redis=None)
        sprint_policy = ExamSprintPolicyEngine.build(
            ExamSprintPolicyInput(total_days=7, subject="计算机网络", daily_available_hours=2)
        ).to_dict()
        sprint_policy["days_left"] = 5

        await replanner.compress_sprint_day(
            plan_id=plan.id,
            day_number=5,
            completion_rate=0.3,
            sprint_policy=sprint_policy,
            source_daily_spec={"title_focus": "TCP 拥塞控制", "task_kind": "retrieval_drill"},
        )

        await db_session.refresh(plan)
        kept_tasks = list(
            (
                await db_session.execute(
                    select(Task)
                    .where(Task.plan_id == plan.id, Task.deleted_at.is_(None))
                    .order_by(Task.order_index.asc(), Task.created_at.asc())
                )
            ).scalars()
        )

        assert plan.source_metadata["adaptive_compressions"]["5"]["compressed"] is True
        assert kept_tasks[0].title.startswith("Day 5 · 压缩保底")
        assert kept_tasks[0].guide_json["compressed"] is True
        assert kept_tasks[0].estimated_minutes <= 35

    async def test_sprint_complete_creates_growth_archive(
        self,
        db_session: AsyncSession,
        journey_models: JourneyModels,
        monkeypatch,
    ):
        monkeypatch.setattr("app.core.websocket.get_ws_manager", lambda: AsyncMock())
        user = await _create_user(db_session, "journey_review")
        user_id = user.id
        exam_date = date(2026, 4, 23)
        started_at = datetime.combine(exam_date - timedelta(days=6), time(hour=9))

        node = KnowledgeNode(
            id=uuid4(),
            name="TCP 拥塞控制",
            description="TCP 拥塞控制",
            importance_level=3,
            source_type="seed",
            dominant_sector_code="VOID",
            sector_classification_status="pending",
        )
        achievement = await db_session.get(Achievement, "sprint_first")
        if achievement is None:
            achievement = Achievement(
                id="sprint_first",
                name="初出茅庐",
                description="完成第一个冲刺计划",
                type=AchievementType.SPRINT,
                rarity=AchievementRarity.COMMON,
                trigger_code="SPRINTS_TOTAL",
                trigger_config={"count": 1},
                reward_config=[],
                category="sprint",
            )
        plan = Plan(
            user_id=user_id,
            name="7天计网冲刺",
            type=PlanType.SPRINT,
            plan_stage=PlanStage.SPRINT,
            subject="计算机网络",
            target_date=exam_date,
            progress=0.85,
            is_active=True,
            source_metadata={"post_exam_review": {}},
            created_at=started_at,
            updated_at=started_at,
        )
        tasks = [
            Task(
                user_id=user_id,
                plan=plan,
                title="Day 1 · 高频保底",
                type=TaskType.LEARNING,
                tags=[],
                estimated_minutes=45,
                actual_minutes=50,
                difficulty=2,
                energy_cost=2,
                status=TaskStatus.COMPLETED,
                completed_at=started_at + timedelta(days=1),
            ),
            Task(
                user_id=user_id,
                plan=plan,
                title="Day 2 · TCP 补强",
                type=TaskType.LEARNING,
                tags=[],
                estimated_minutes=40,
                actual_minutes=42,
                difficulty=3,
                energy_cost=3,
                status=TaskStatus.COMPLETED,
                completed_at=started_at + timedelta(days=3),
            ),
            Task(
                user_id=user_id,
                plan=plan,
                title="Day 7 · 综合回看",
                type=TaskType.LEARNING,
                tags=[],
                estimated_minutes=35,
                difficulty=2,
                energy_cost=2,
                status=TaskStatus.PENDING,
            ),
        ]
        prefs = UserPreferencesCenter(
            user_id=user_id,
            explicit={
                "cold_start_context": {
                    "estimated_score_now": 38,
                    "diagnostic_estimated_score": 38.0,
                    "diagnostic_node_mastery_snapshot": [
                        {"node_id": str(node.id), "node_name": node.name, "mastery": 38.0},
                    ],
                }
            },
        )
        db_session.add_all(
            [
                node,
                achievement,
                plan,
                prefs,
                *tasks,
                UserNodeStatus(user_id=user_id, node_id=node.id, mastery_score=72.0),
                StudyRecord(
                    user_id=user_id,
                    node_id=node.id,
                    task_id=tasks[0].id,
                    study_minutes=50,
                    mastery_delta=8.0,
                    initial_mastery=38.0,
                    created_at=started_at + timedelta(days=1),
                ),
                ErrorRecord(
                    user_id=user_id,
                    subject_code="network",
                    chapter="TCP",
                    question_text="q1",
                    mastery_level=0.8,
                    review_count=2,
                    created_at=started_at + timedelta(days=2),
                ),
            ]
        )
        await db_session.commit()
        # Keep a reference to the plan's id before service calls
        plan_id = plan.id

        review_request = journey_models.review_request.model_copy(update={"plan_id": plan.id})
        response = await ExamSprintReviewService(db_session).submit_post_exam_review(
            user_id=user_id,
            request=review_request,
        )

        stored_prefs = (
            await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id))
        ).scalar_one()

        assert response.archived_in_growth_profile is True
        assert stored_prefs.explicit["exam_sprint_growth_archive"]["entries"][-1]["review_id"] == response.review_id
        assert response.summary.task_stats.completed == 2

    async def test_spaced_repetition_scheduled(self, db_session: AsyncSession, monkeypatch):
        user = await _create_user(db_session, "journey_spaced")
        monkeypatch.setattr(NotificationService, "_push_notification_via_websocket", AsyncMock(return_value=None))
        now = datetime(2026, 4, 25, 9, 0, 0)
        node = await _seed_mid_mastery_node(
            db_session,
            user_id=user.id,
            mastery=0.55,
            days_ago=7,
            now=now,
        )

        result = await _run_spaced_repetition_reminders_for_user(
            db_session,
            str(user.id),
            now=now.isoformat(),
        )

        notifications = list(
            (
                await db_session.execute(
                    select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.asc())
                )
            ).scalars()
        )

        assert result["sent"] == 1
        assert result["sent_node_ids"] == [str(node.id)]
        assert notifications[0].data["node_id"] == str(node.id)

    async def test_episodic_memory_persists_cross_session(self, db_session: AsyncSession, test_user: User):
        session_a = MemoryService(db_session)
        session_b = MemoryService(db_session)

        created = await session_a.create_episodic_memory(
            user_id=test_user.id,
            summary="会话 A：用户说自己是零基础，先保底过线。",
            source_type="chat",
            source_id="session-a",
            occurred_at=_utcnow(),
            importance_score=0.8,
            tags=["north_star", "session_a"],
            evidence_refs=[{"type": "chat_turn", "id": "session-a:1"}],
            confidence=0.9,
            subject_type="self",
        )
        recent = await session_b.get_recent_episodic(test_user.id, limit=5)

        assert created is not None
        assert any(memory.source_id == "session-a" for memory in recent)
        assert any("零基础" in memory.summary for memory in recent)

    async def test_weekly_narrative_generated_on_sunday(self, db_session: AsyncSession):
        user_id = uuid4()
        sunday = datetime(2026, 4, 26, 18, 0, 0)
        week_start = sunday - timedelta(days=sunday.weekday())
        week_end = week_start + timedelta(days=7)

        user = User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
        node = KnowledgeNode(id=uuid4(), name="TCP 三次握手", importance_level=3)
        task = Task(
            id=uuid4(),
            user_id=user_id,
            title="TCP 费曼复述",
            type=TaskType.LEARNING,
            status=TaskStatus.COMPLETED,
            estimated_minutes=35,
            actual_minutes=42,
            difficulty=3,
            energy_cost=2,
            tags=["传输层"],
            completed_at=sunday - timedelta(days=1),
            created_at=sunday - timedelta(days=1),
        )
        study = StudyRecord(
            id=uuid4(),
            user_id=user_id,
            node_id=node.id,
            task_id=task.id,
            study_minutes=42,
            mastery_delta=18.5,
            initial_mastery=40,
            record_type="task_complete",
            created_at=sunday - timedelta(days=1),
        )
        error = ErrorRecord(
            id=uuid4(),
            user_id=user_id,
            subject_code="network",
            chapter="TCP",
            question_text="TIME_WAIT 作用",
            latest_analysis={"root_cause": "概念混淆"},
            mastery_level=0.85,
            created_at=sunday - timedelta(days=1),
            last_reviewed_at=sunday - timedelta(days=1),
            review_count=2,
            is_deleted=False,
        )
        feedback = TaskFeedback(
            id=uuid4(),
            user_id=user_id,
            task_id=task.id,
            completion_quality=4,
            category="too_difficult",
            feedback_text="讲给自己听之后顺了",
            reflection_payload={"selected_option": "换一种解释方式", "submitted_at": sunday.isoformat()},
            created_at=sunday - timedelta(days=1),
        )
        db_session.add_all([user, node, task, study, error, feedback])
        await db_session.commit()

        narrative = await ProgressNarrativeService(db_session, redis=None).get_weekly_narrative(
            user_id,
            week_start,
            week_end,
            force=True,
            now=sunday,
        )

        assert sunday.weekday() == 6
        assert isinstance(narrative, WeeklyGrowthNarrative)
        assert narrative.is_placeholder is False
        assert "TCP" in narrative.body
        assert narrative.data_points["tasks_completed"] == 1

    async def test_milestone_achievement_unlock_notification(self, db_session: AsyncSession, monkeypatch):
        user = await _create_user(db_session, "journey_milestone")
        monkeypatch.setattr(NotificationService, "_push_notification_via_websocket", AsyncMock(return_value=None))

        for index in range(5):
            node = KnowledgeNode(name=f"node-{index}")
            db_session.add(node)
            await db_session.flush()
            db_session.add(UserNodeStatus(user_id=user.id, node_id=node.id, is_unlocked=True, mastery_score=42.0))

        db_session.add(
            UserStreakStats(
                user_id=user.id,
                total_checkin_days=30,
                current_streak=9,
                max_streak=12,
            )
        )
        await db_session.commit()

        notification = await AchievementEventConsumer(event_bus=AsyncMock())._maybe_create_milestone_notification(
            db=db_session,
            user_id=user.id,
            event={"achievement_id": "30_day_learner", "achievement_name": "30 天学习者"},
        )

        stored = (await db_session.execute(select(Notification).where(Notification.id == notification.id))).scalar_one()
        unlocked = (
            (
                await db_session.execute(
                    select(UserAchievement).where(
                        UserAchievement.user_id == user.id,
                        UserAchievement.achievement_id == "30_day_learner",
                    )
                )
            )
            .scalars()
            .all()
        )

        assert notification is not None
        assert notification.type == "milestone_notification"
        assert notification.data["study_days"] == 30
        assert stored.title == "你已经坚持学习 30 天了"
        assert unlocked == []
