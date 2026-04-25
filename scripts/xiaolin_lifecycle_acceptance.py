#!/usr/bin/env python3
"""High-fidelity lifecycle acceptance for Sparkle Exam Sprint + Aurora Runtime.

This script simulates a realistic user arc instead of a one-turn smoke test:

1. A new user registers and completes Aurora modeling with detours.
2. Modeling output is bridged into planning without a new explicit intent.
3. A 7-day exam sprint plan is generated from cold-start + Galaxy mastery data.
4. The first task is executed, feedback creates a knowledge gap and remedial task.
5. A checkpoint miss inserts a review remedial task.
6. Achievement state flows back into Aurora dashboard readouts.
7. A second 14-day sprint request proves the policy generalizes beyond 7 days.

The script uses SQLite in-memory DB and scripted LLM decisions/messages, but it
exercises the actual service boundaries that matter for product regressions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
BACKEND_VENV_PYTHON = BACKEND_ROOT / ".venv" / "bin" / "python"
ARTIFACT_PATH = ROOT / "artifacts" / "lifecycle" / "xiaolin_lifecycle_acceptance.json"

if BACKEND_VENV_PYTHON.exists() and Path(sys.executable).resolve() != BACKEND_VENV_PYTHON.resolve():
    os.execv(str(BACKEND_VENV_PYTHON), [str(BACKEND_VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

logging.basicConfig(level=logging.ERROR)

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  # Register all SQLAlchemy mappers for realistic relationship coverage.
from app.aurora.runtime_v1 import AURORA_SURFACE_MODELING, AuroraRuntimeV1Service
from app.aurora.runtime_v1.control_surface import ActivityProfile, AuroraHardBounds, ControlSurfaceReading
from app.aurora.runtime_v1.dashboard import DashboardReadout, DashboardReadoutBuilder
from app.aurora.runtime_v1.decision_loop import AuroraDecision
from app.models.base import Base
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.models.user import PushPreference, User
from app.models.user_preferences import UserPreferencesCenter
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.orchestration.exam_sprint_policy import ExamSprintPolicyEngine, ExamSprintPolicyInput
from app.orchestration.planning_workflow import PlanningWorkflowManager
from app.services.personalization.preference_service import PreferenceService
from app.services.task_feedback_service import TaskFeedbackService

logger.remove()
logger.add(sys.stderr, level="ERROR")

# ---------------------------------------------------------------------------
# Stub out real LLM calls so planning workflow uses rule-based fallbacks.
# Both bottleneck_analyzer.analyze() and llm_service.reason_json() already
# have try/except → fallback paths; we just make them fail immediately.
# ---------------------------------------------------------------------------
import app.services.llm_service as _llm_mod
import app.orchestration.bottleneck_analyzer as _bn_mod


class _StubLLMService:
    """Redirects every LLM call to an immediate exception so callers hit their fallback."""

    def __getattr__(self, name: str) -> Any:
        async def _fail(*_: Any, **__: Any) -> None:
            raise RuntimeError("stub: no real LLM in lifecycle acceptance")

        return _fail


_original_llm_service = _llm_mod.llm_service

_original_bn_analyze = _bn_mod.bottleneck_analyzer.analyze
_original_bn_rule_fallback = _bn_mod.bottleneck_analyzer._rule_fallback


async def _stub_bn_analyze(*args: Any, **kwargs: Any) -> Any:
    """Skip the LLM round-trip; jump straight to rule-based fallback."""
    return _original_bn_rule_fallback(*args, **kwargs)


_llm_mod.llm_service = _StubLLMService()  # type: ignore[assignment]
_bn_mod.bottleneck_analyzer.analyze = _stub_bn_analyze  # type: ignore[assignment]

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}
        self.expirations: dict[str, int] = {}

    async def get(self, key: str) -> Any:
        return self.values.get(key)

    async def set(self, key: str, value: Any, ex: int | None = None) -> None:
        self.values[key] = value
        if ex is not None:
            self.expirations[key] = ex

    async def setex(self, key: str, ttl: int, value: Any) -> None:
        self.values[key] = value
        self.expirations[key] = ttl

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)
        self.expirations.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self.values

    async def expire(self, key: str, ttl: int) -> bool:
        if key not in self.values:
            return False
        self.expirations[key] = ttl
        return True


@dataclass
class Trace:
    events: list[dict[str, Any]] = field(default_factory=list)

    def add(self, name: str, **payload: Any) -> None:
        self.events.append({"event": name, **_jsonable(payload)})


class ScriptedDecisionLoop:
    """Scripted cognition for deterministic lifecycle acceptance."""

    def __init__(self, trace: Trace) -> None:
        self.trace = trace
        self.turn = 0
        self.readouts: list[DashboardReadout] = []

    async def decide(self, readout: DashboardReadout) -> AuroraDecision:
        self.turn += 1
        self.readouts.append(readout)
        self.trace.add(
            "aurora_decision_readout",
            turn=self.turn,
            surface=readout.surface,
            covered_domains=readout.covered_domains,
            missing_domains=readout.missing_domains,
            recently_asked_domains=readout.recently_asked_domains,
            galaxy_baseline=readout.request_extra_context.get("galaxy_baseline"),
        )

        if self.turn == 1:
            return _decision("emit_message", target_domain="scope", summary="Need exam scope before planning.")
        if self.turn == 2:
            return _decision("emit_message", target_domain="baseline", summary="Detour was heard; keep modeling warm.")
        if self.turn == 3:
            return _decision("emit_message", target_domain="time", summary="Scope and baseline are clear; time is missing.")
        return _decision(
            "emit_message",
            modeling_complete=True,
            surface_complete=True,
            state_updates={
                "informational_tensions": [
                    {"domain": "goal", "status": "resolved"},
                    {"domain": "scope", "status": "resolved"},
                    {"domain": "baseline", "status": "resolved"},
                    {"domain": "time", "status": "resolved"},
                    {"domain": "motivation", "status": "resolved"},
                ],
            },
            target_domain=None,
            summary="Modeling has enough planning-critical context.",
        )


class ScriptedChatAdapter:
    def __init__(self, trace: Trace) -> None:
        self.trace = trace
        self.messages_by_turn = [
            [
                "我先不急着排表，先把考试边界摸清楚。",
                "这次计网主要考哪些范围？如果只有课件或老师划重点，也直接说。",
            ],
            [
                "这个插曲我收到了，不会把你刚才的目标丢掉。",
                "回到备考本身：你现在最虚的是概念、题型，还是整门课都还没建立框架？",
            ],
            ["范围和基础我已经有数了。接下来只差一个硬约束：这 7 天每天能拿出几小时？"],
            [
                "够了，我已经能给你做一个生存优先的 7 天计网冲刺方案。",
                "我会优先保传输层、网络层和典型题，不把计划做成泛泛阅读清单。",
            ],
        ]
        self.turn = 0

    async def render(self, decision: AuroraDecision, readout: DashboardReadout) -> list[str]:
        if decision.action in {"wait", "drop_thread"}:
            return []
        messages = self.messages_by_turn[min(self.turn, len(self.messages_by_turn) - 1)]
        self.turn += 1
        self.trace.add("aurora_messages", turn=self.turn, messages=messages)
        return messages


def _decision(
    action: str,
    *,
    target_domain: str | None,
    modeling_complete: bool = False,
    surface_complete: bool = False,
    state_updates: dict[str, Any] | None = None,
    summary: str,
) -> AuroraDecision:
    return AuroraDecision(
        action=action,
        surface_complete=surface_complete,
        modeling_complete=modeling_complete,
        state_updates=state_updates or {},
        chat_directive={"intent": action, "target_domain": target_domain},
        metadata={"reasoning_summary": summary},
    )


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def create_session() -> tuple[AsyncSession, Any]:
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return session_factory(), engine


async def seed_user_and_galaxy(db: AsyncSession, trace: Trace) -> User:
    user = User(
        username=f"xiaolin_{uuid4().hex[:8]}",
        email=f"xiaolin_{uuid4().hex[:8]}@example.com",
        hashed_password="local-acceptance",
        full_name="小林",
        nickname="小林",
        email_verified=True,
        last_login_at=_utcnow(),
        agreed_to_tos_at=_utcnow(),
        agreed_to_privacy_at=_utcnow(),
    )
    db.add(user)
    await db.flush()
    db.add(
        PushPreference(
            user_id=user.id,
            timezone="Asia/Shanghai",
            active_slots=[{"start": "08:00", "end": "22:30"}],
            enable_curiosity=True,
            persona_type="coach",
            daily_cap=5,
        )
    )
    db.add(
        UserPreferencesCenter(
            user_id=user.id,
            explicit={
                "aurora_preferences": {
                    "dnd_windows": [{"start": "23:30", "end": "07:30"}],
                    "disabled_actions": [],
                    "privacy_boundaries": ["clinical_diagnosis", "inferred_social_identity"],
                    "timezone_name": "Asia/Shanghai",
                }
            },
            inferred={},
            traits_prior={},
            trait_observation_state={},
        )
    )

    nodes = [
        ("TCP 三次握手", 8.0, 5),
        ("拥塞控制", 12.0, 5),
        ("IP 地址与子网划分", 28.0, 4),
        ("DNS 与 HTTP", 46.0, 3),
        ("OSI/TCP-IP 分层", 18.0, 5),
    ]
    for name, mastery, importance in nodes:
        node = KnowledgeNode(name=name, description=f"计算机网络考点：{name}", importance_level=importance)
        db.add(node)
        await db.flush()
        db.add(
            UserNodeStatus(
                user_id=user.id,
                node_id=node.id,
                mastery_score=mastery,
                bkt_mastery_prob=mastery / 100.0,
                is_unlocked=True,
                study_count=1,
            )
        )

    await db.commit()
    await db.refresh(user)
    trace.add("user_registered", user_id=str(user.id), login="email", galaxy_nodes=len(nodes))
    return user


async def run_modeling_arc(
    *,
    db: AsyncSession,
    redis: FakeRedis,
    user: User,
    trace: Trace,
) -> dict[str, Any]:
    service = AuroraRuntimeV1Service(
        redis_client=redis,
        decision_loop=ScriptedDecisionLoop(trace),
        chat_adapter=ScriptedChatAdapter(trace),
    )
    conversation_id = "conv-xiaolin-modeling"
    messages = [
        "我 7 天后考计算机网络，想别挂科，最好能冲到 75。",
        "等一下，我还要准备别的课，所以别排得太满。",
        "范围大概是网络层、传输层、应用层，TCP/IP 那块我完全没学过。",
        "每天最多 4 小时，周三晚上没空。我主要是必须过，不然奖学金会受影响。",
    ]
    conversation_context: dict[str, Any] = {"messages": []}
    last_plan = None

    for idx, message in enumerate(messages, start=1):
        plan = await service.plan_turn(
            active_db=db,
            user_id=str(user.id),
            surface=AURORA_SURFACE_MODELING,
            conversation_id=conversation_id,
            request_id=f"modeling-{idx}",
            user_message=message,
            request_extra_context={
                "informational_tensions": [
                    {"domain": "goal", "status": "open"},
                    {"domain": "scope", "status": "open"},
                    {"domain": "baseline", "status": "open"},
                    {"domain": "time", "status": "open"},
                ]
            },
            conversation_context=conversation_context,
            user_context_payload={},
        )
        conversation_context["messages"].append({"role": "user", "content": message})
        for assistant_message in plan.messages:
            conversation_context["messages"].append({"role": "assistant", "content": assistant_message})
        last_plan = plan

    assert last_plan is not None
    assert last_plan.modeling_complete is True
    assert last_plan.surface_complete is True
    assert last_plan.activity_profile.get("conversation_style") == "warm"
    asked_domains = [
        message["content"]
        for message in conversation_context["messages"]
        if message["role"] == "assistant" and any(mark in message["content"] for mark in ("？", "?"))
    ]
    assert len(asked_domains) >= 3
    assert not _has_semantic_overlap([message["content"] for message in conversation_context["messages"] if message["role"] == "assistant"])

    galaxy_baseline = await service._fetch_galaxy_baseline(active_db=db, user_id=str(user.id))
    assert galaxy_baseline
    assert galaxy_baseline["avg_mastery"] < 30
    assert any("TCP" in str(item) for item in galaxy_baseline["weak_nodes"])

    cold_start_context = {
        "primary_goal_description": "7 天后计算机网络考试，目标先过线并尽量到 75 分",
        "subject": "计算机网络",
        "exam_scope": "网络层、传输层、应用层，重点 TCP/IP、子网划分、DNS/HTTP",
        "knowledge_baseline": "完全没学过",
        "daily_available_hours": 4,
        "time_constraint_days": 7,
        "blocked_days": ["周三晚上没空"],
        "available_materials": ["老师课件", "历年题", "教材重点章"],
        "motivation": "必须过线，否则奖学金会受影响",
    }
    modeling_output = {
        "activity_profile": last_plan.activity_profile,
        "user_model_snapshot": {"preferences": {"cold_start_context": cold_start_context}},
        "cold_start_context": cold_start_context,
        "galaxy_baseline": galaxy_baseline,
    }
    trace.add(
        "modeling_complete",
        messages=len(conversation_context["messages"]),
        avg_mastery=galaxy_baseline["avg_mastery"],
        weak_nodes=list(galaxy_baseline["weak_nodes"]),
    )
    return modeling_output


async def run_planning_arc(
    *,
    db: AsyncSession,
    redis: FakeRedis,
    user: User,
    modeling_output: dict[str, Any],
    trace: Trace,
) -> tuple[Plan, list[Task], dict[str, Any]]:
    user_id = user.id
    manager = PlanningWorkflowManager(redis_client=redis)
    chat_session_id = "conv-xiaolin-planning"
    context = {"from_modeling_complete": True, "modeling_output": modeling_output}
    first = await manager.process_planning_turn(
        db=db,
        user_id=user_id,
        chat_session_id=chat_session_id,
        message="开始规划",
        context=context,
    )
    assert first is not None
    assert any(widget["type"] == "planning_bottleneck_card" for widget in first.get("widgets", []))
    strategy_widgets = [widget for widget in first.get("widgets", []) if widget["type"] == "planning_strategy_card"]
    assert strategy_widgets
    strategy = strategy_widgets[0]["data"]["strategy"]
    assert strategy["sprint_policy"]["sprint_mode"] == "seven_day_survival"
    assert "defer_or_skip" in json.dumps(strategy, ensure_ascii=False)

    generated = await manager.process_planning_turn(
        db=db,
        user_id=user_id,
        chat_session_id=chat_session_id,
        message="确认这个方案",
        context=context,
    )
    assert generated is not None
    assert generated.get("metadata", {}).get("surface_complete") is True

    plan = (await db.execute(select(Plan).where(Plan.user_id == user_id).order_by(Plan.created_at.desc()))).scalars().first()
    assert plan is not None
    tasks = list(
        (
            await db.execute(
                select(Task).where(Task.user_id == user_id, Task.plan_id == plan.id).order_by(Task.order_index.asc())
            )
        )
        .scalars()
        .all()
    )
    assert len(tasks) == 7
    assert tasks[0].title.startswith("Day 1"), f"Expected first visible task to be Day 1, got {tasks[0].title}"
    assert tasks[-1].title.startswith("Day 7"), f"Expected final visible task to be Day 7, got {tasks[-1].title}"
    assert all(task.guide_json and task.guide_json.get("retrieval_first") is True for task in tasks)
    assert all(task.guide_json.get("output_action") for task in tasks)
    assert all(task.success_criteria for task in tasks)
    assert all(task.guide_json.get("micro_contract") for task in tasks)
    assert any("奖学金" in str(task.ai_prompt or "") or "必须过线" in str(task.ai_prompt or "") for task in tasks)
    assert any("retrieval" in json.dumps(task.guide_json, ensure_ascii=False).lower() or "闭卷" in json.dumps(task.guide_json, ensure_ascii=False) for task in tasks)
    assert any(task.difficulty >= 4 for task in tasks), "Galaxy weak baseline should raise difficulty signal"

    trace.add(
        "planning_generated",
        plan_id=str(plan.id),
        plan_name=plan.name,
        task_count=len(tasks),
        first_task=tasks[0].title,
        sprint_mode=strategy["sprint_policy"]["sprint_mode"],
    )
    return plan, tasks, strategy


async def run_execution_and_adaptation_arc(
    *,
    db: AsyncSession,
    redis: FakeRedis,
    user_id: UUID,
    plan: Plan,
    tasks: list[Task],
    trace: Trace,
) -> None:
    plan_id = plan.id
    import app.services.task_feedback_service as feedback_module

    class FakeReflectionService:
        async def maybe_enqueue_reflection_prompt(self, **_: Any) -> None:
            return None

    class FakeRoutingProfileService:
        async def record_session_outcome(self, **_: Any) -> dict[str, Any]:
            return {}

    async def fake_publish(*_: Any, **__: Any) -> None:
        return None

    feedback_module.TaskReflectionService = lambda db, redis: FakeReflectionService()  # type: ignore[assignment]
    feedback_module.RoutingProfileService = lambda db, redis: FakeRoutingProfileService()  # type: ignore[assignment]
    feedback_module.event_bus.publish = fake_publish  # type: ignore[method-assign]

    first = tasks[0]
    first.status = TaskStatus.COMPLETED
    first.completed_at = _utcnow()
    first.actual_minutes = int(first.estimated_minutes or 60) + 20
    await db.commit()

    feedback, _ = await TaskFeedbackService(db, redis=redis).submit_feedback(
        user_id=user_id,
        task_id=first.id,
        completion_quality=2,
        feedback_text="TCP 三次握手还是搞不懂，题目一换就没思路",
        category="unclear",
    )
    assert feedback.category == "unclear"

    prefs = await PreferenceService(db).get_preferences(user_id)
    gaps = prefs.explicit.get("knowledge_gaps")
    assert isinstance(gaps, list) and gaps
    assert "TCP" in gaps[-1]["description"]

    refreshed_tasks = list(
        (
            await db.execute(
                select(Task).where(Task.user_id == user_id, Task.plan_id == plan_id).order_by(Task.order_index.asc())
            )
        )
        .scalars()
        .all()
    )
    remedials = [task for task in refreshed_tasks if task.title.startswith("[补强]")]
    assert remedials
    assert remedials[0].estimated_minutes <= 30
    assert remedials[0].guide_json["sprint_fail_safe"] is True
    assert remedials[0].guide_json["density_adjustment"] in {"reduced", "minimum_viable"}
    assert refreshed_tasks.index(remedials[0]) == refreshed_tasks.index(first) + 1

    checkpoint_task = await AdaptiveReplanner(db, redis).adjust_for_checkpoint(
        user_id=user_id,
        plan_id=plan_id,
        debrief_result={
            "goal_met": False,
            "checkpoint_day": 3,
            "checkpoint_description": "检查网络层与传输层核心题型是否能闭卷输出",
            "first_answer": "落后了，网络层没做完",
            "second_answer": "主要是没时间，也有一点理解问题",
        },
    )
    assert checkpoint_task is not None
    assert checkpoint_task.title.startswith("[复盘补强]")
    assert checkpoint_task.estimated_minutes <= 45
    assert checkpoint_task.guide_json["sprint_fail_safe"] is True
    assert checkpoint_task.guide_json["density_adjustment"] in {"reduced", "minimum_viable"}

    trace.add(
        "execution_adapted",
        feedback_id=str(feedback.id),
        knowledge_gap=gaps[-1]["description"],
        remedial_title=remedials[0].title,
        checkpoint_remedial=checkpoint_task.title,
    )


def run_achievement_readout_check(user_id: UUID, trace: Trace) -> None:
    readout = DashboardReadoutBuilder().build(
        surface="aurora_checkpoint",
        user_id=str(user_id),
        conversation_id="conv-achievement",
        request_id="achievement-readout",
        user_message="今天复盘完了",
        request_extra_context={},
        conversation_context={"messages": []},
        user_context_payload={
            "cognitive_context": {
                "achievement_summary": {
                    "total_achievement_score": 35,
                    "recent_unlocks": [{"name": "第一次闭卷输出", "rarity": "common"}],
                    "in_progress_achievements": [{"name": "连续 3 天完成检索任务"}],
                }
            }
        },
        control_surface_reading=ControlSurfaceReading(
            adjustable=ActivityProfile(conversation_style="warm"),
            hard_bounds=AuroraHardBounds(
                dnd_windows=[{"start": "23:30", "end": "07:30"}],
                timezone_name="Asia/Shanghai",
            ),
            runtime_enabled=True,
        ),
        activity_profile={"conversation_style": "warm", "task_density_hint": 0.45},
        candidate_affordances=[],
    )
    assert readout.achievement_signals["momentum"] > 0
    assert readout.achievement_signals["recent_unlocks"]
    trace.add("achievement_reinforcement_visible", achievement_signals=readout.achievement_signals)


def run_fourteen_day_generalization(trace: Trace) -> None:
    policy = ExamSprintPolicyEngine.build(
        ExamSprintPolicyInput(
            total_days=14,
            subject="数据库系统",
            exam_scope="关系代数、SQL、事务、索引",
            knowledge_baseline="上过课但没复习",
            time_available="每天 3 小时",
            cold_start_context={"daily_available_hours": 3},
        )
    )
    assert policy.sprint_mode == "fourteen_day_build_and_retrieve"
    assert policy.retrieval_policy.get("spaced_retrieval") == "multi_day_successive_relearning"
    assert policy.triage_level == "balanced"
    trace.add(
        "fourteen_day_generalization",
        sprint_mode=policy.sprint_mode,
        triage_level=policy.triage_level,
        retrieval_policy=policy.retrieval_policy,
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _has_semantic_overlap(messages: list[str]) -> bool:
    seen: set[str] = set()
    for message in messages:
        normalized = "".join(ch for ch in message.lower() if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")
        if not normalized:
            continue
        if normalized in seen:
            return True
        if any(normalized in old or old in normalized for old in seen):
            return True
        seen.add(normalized)
    return False


async def main() -> None:
    trace = Trace()
    redis = FakeRedis()
    db, engine = await create_session()
    try:
        user = await seed_user_and_galaxy(db, trace)
        user_id = user.id
        modeling_output = await run_modeling_arc(db=db, redis=redis, user=user, trace=trace)
        plan, tasks, _strategy = await run_planning_arc(
            db=db,
            redis=redis,
            user=user,
            modeling_output=modeling_output,
            trace=trace,
        )
        await run_execution_and_adaptation_arc(db=db, redis=redis, user_id=user_id, plan=plan, tasks=tasks, trace=trace)
        run_achievement_readout_check(user_id, trace)
        run_fourteen_day_generalization(trace)

        report = {
            "status": "PASS",
            "scenario": "xiaolin_full_lifecycle_exam_sprint",
            "generated_at": _utcnow().isoformat(),
            "coverage": [
                "register_login_surrogate",
                "aurora_multiturn_modeling_with_detour",
                "modeling_complete_to_planning_bridge",
                "galaxy_mastery_prefill",
                "seven_day_exam_sprint_plan_generation",
                "retrieval_first_task_cards",
                "task_feedback_to_knowledge_gap",
                "remedial_task_insertion",
                "checkpoint_recovery_task",
                "achievement_signals_to_dashboard",
                "fourteen_day_policy_generalization",
            ],
            "trace": trace.events,
        }
        ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "PASS", "artifact": str(ARTIFACT_PATH), "events": len(trace.events)}, ensure_ascii=False))
    finally:
        await db.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
