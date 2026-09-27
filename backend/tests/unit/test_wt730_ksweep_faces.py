"""wt730 kill_switch 邻批扫雷（V3-FIX-443 批次）红→绿测试。

三面：
1. runtime_v1 ``aurora_runtime`` 开关接线（本批修复）：Stage38 服务补注册
   ``aurora_runtime`` binding——修前 ``get_feature_mode("aurora_runtime")`` 恒
   ValueError（被宽 except 吞掉后缺省 "shadow"），off 分支不可达（假开/死面，
   FIX-341/345 同族）。既有 test_plan_turn_kill_switch_off_returns_minimal_plan
   docstring 明文记载「binding 接线属后续开关接入工作」——本批接线。
2. err_replan off 假关断（本批修复）：bridge ``on_error_created`` 在 mode=off
   时早退零副作用（修复任务/干预记录/弱节点 claim/replan 全不发生）——修前
   off 与 shadow 同样跑全链（FIX-415 幽灵信号/假关断同族）。
3. stage34 ``error_bridge`` 死绑定（登记不修，见台账 V3-FIX-443）：仅遥测
   读者零行为读者，真实 bridge 由 stage38 err_replan 治理——FIX-341/345
   假开关同族，撤面动遥测负载形留待专卡。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.config import settings
from app.core.cache import cache_service
from app.models.card_protocol import InterventionRecord
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter
from app.services.aurora_stage38_kill_switch_service import AuroraStage38KillSwitchService
from app.services.error_replan_bridge import ErrorReplanBridge

FROZEN_UTC_NOW = datetime(2026, 9, 25, 20, 0)  # naive UTC（同 test_error_replan_bridge 冻结钟）


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str) -> None:
        self.store[key] = value


# ---------------------------------------------------------------------------
# 面 1：aurora_runtime binding 接线（修前 ValueError→恒 shadow）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stage38_aurora_runtime_mode_resolves_tri_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """tri-state 设置在场即唯一判据：off 可达（修前 ValueError）。"""
    monkeypatch.setattr(cache_service, "redis", None)
    monkeypatch.setattr(settings, "AURORA_STAGE38_AURORA_RUNTIME_MODE", "off")
    mode = await AuroraStage38KillSwitchService().get_feature_mode("aurora_runtime")
    assert mode == "off"


@pytest.mark.asyncio
async def test_stage38_aurora_runtime_mode_live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    monkeypatch.setattr(settings, "AURORA_STAGE38_AURORA_RUNTIME_MODE", "live")
    mode = await AuroraStage38KillSwitchService().get_feature_mode("aurora_runtime")
    assert mode == "live"


@pytest.mark.asyncio
async def test_stage38_aurora_runtime_legacy_bool_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """tri-state 缺席（None）时 legacy bool ENABLE_AURORA_RUNTIME_V1 兜底。"""
    monkeypatch.setattr(cache_service, "redis", None)
    monkeypatch.setattr(settings, "AURORA_STAGE38_AURORA_RUNTIME_MODE", None)
    monkeypatch.setattr(settings, "ENABLE_AURORA_RUNTIME_V1", False)
    mode = await AuroraStage38KillSwitchService().get_feature_mode("aurora_runtime")
    assert mode == "off"

    monkeypatch.setattr(settings, "ENABLE_AURORA_RUNTIME_V1", True)
    mode = await AuroraStage38KillSwitchService().get_feature_mode("aurora_runtime")
    assert mode == "live"


@pytest.mark.asyncio
async def test_runtime_plan_turn_off_gate_via_settings_no_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """真开关链路（零桩）：settings off → 最小 TurnPlan，决策管线不执行。

    修前 get_feature_mode("aurora_runtime") 恒 ValueError → 缺省 "shadow"，
    本测在 off 设置下仍执行完整管线（红）。
    """
    from tests.unit.test_aurora_runtime_v1 import _FakeRedis as _RuntimeFakeRedis
    from tests.unit.test_aurora_runtime_v1 import _RecordingDecisionLoop, _StaticChatAdapter

    monkeypatch.setattr(cache_service, "redis", None)
    monkeypatch.setattr(settings, "AURORA_STAGE38_AURORA_RUNTIME_MODE", "off")
    decision_loop = _RecordingDecisionLoop()
    service = AuroraRuntimeV1Service(
        redis_client=_RuntimeFakeRedis(),
        decision_loop=decision_loop,
        chat_adapter=_StaticChatAdapter(),
    )

    plan = await service.plan_turn(
        active_db=None,
        user_id="user-wt730-off",
        surface="aurora_modeling",
        conversation_id="conv-wt730",
        request_id="req-wt730",
        user_message="继续",
        request_extra_context=None,
        conversation_context=None,
        user_context_payload=None,
    )

    assert decision_loop.readouts == []
    assert plan.messages == []
    assert plan.surface_complete is False
    assert plan.modeling_complete is False


@pytest.mark.asyncio
async def test_stage38_summary_includes_aurora_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    monkeypatch.setattr(settings, "AURORA_STAGE38_ERR_REPLAN_MODE", "shadow")
    monkeypatch.setattr(settings, "AURORA_STAGE38_PUSH_SCHEDULER_MODE", "shadow")
    monkeypatch.setattr(settings, "AURORA_STAGE38_AURORA_RUNTIME_MODE", "live")

    summary = await AuroraStage38KillSwitchService().summary()
    assert summary == {
        "err_replan_mode": "shadow",
        "push_scheduler_mode": "shadow",
        "aurora_runtime_mode": "live",
    }


# ---------------------------------------------------------------------------
# 面 2：err_replan off 假关断（修前 off 仍跑全链副作用）
# ---------------------------------------------------------------------------


async def _seed_bridge_user(db_session):
    user = User(
        username="wt730_bridge_user",
        email="wt730_bridge_user@example.com",
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
        target_date=FROZEN_UTC_NOW.date() + timedelta(days=10),
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
        due_date=FROZEN_UTC_NOW.date() + timedelta(days=2),
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
            question_text=f"wt730-error-{idx}",
            mastery_level=0.2,
            latest_analysis={"error_type": "concept_confusion"},
            linked_knowledge_node_ids=[str(node.id)],
            created_at=FROZEN_UTC_NOW - timedelta(days=idx),
        )
        for idx in range(3)
    ]
    db_session.add_all(errors)
    await db_session.commit()
    return user, plan, node, errors


@pytest.mark.asyncio
async def test_err_replan_off_stops_bridge_without_side_effects(db_session, monkeypatch) -> None:
    """mode=off：早退 blocked，零副作用（修前全链照跑=假关断）。"""
    monkeypatch.setattr(
        "app.services.error_replan_bridge._utcnow",
        lambda: FROZEN_UTC_NOW,
        raising=False,
    )
    monkeypatch.setattr(cache_service, "redis", None)
    monkeypatch.setattr(settings, "AURORA_STAGE38_ERR_REPLAN_MODE", "off")

    user, plan, node, errors = await _seed_bridge_user(db_session)

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
        ),
    ):
        result = await bridge.on_error_created(
            user_id=user.id,
            error_id=errors[-1].id,
            linked_node_ids=[node.id],
        )

    assert result["triggered"] is False
    assert result["mode"] == "off"
    assert result["reason"] == "kill_switch_off"

    # 副作用面全零：无 replan 评估
    mock_eval.assert_not_awaited()
    # 无修复任务落库
    task_rows = await db_session.execute(select(Task).where(Task.user_id == user.id, Task.plan_id == plan.id))
    repair_tasks = [t for t in task_rows.scalars().all() if (t.guide_json or {}).get("task_kind") == "targeted_repair"]
    assert repair_tasks == []
    # 无干预记录落库
    records = await db_session.execute(select(InterventionRecord).where(InterventionRecord.user_id == user.id))
    assert records.scalars().all() == []
    # 无弱节点 claim 写 Redis
    assert redis.store == {}
