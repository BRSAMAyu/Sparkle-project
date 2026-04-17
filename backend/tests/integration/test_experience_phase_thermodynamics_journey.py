from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.card_protocol import (
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
    InterventionRecord,
    InterventionTriggerType,
)
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.user import User
from app.orchestration.experience_actuator import ExperienceActuator
from app.orchestration.situation_brief import SituationBriefBuilder
from app.services.experience_phase_evaluator import ExperiencePhaseEvaluator


class _FakeRedis:
    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self._ttl: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self._kv.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._kv[key] = value
        self._ttl[key] = ttl


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _base_plan_context(plan: Plan) -> dict[str, str]:
    return {
        "plan_title": plan.name,
        "goal": "掌握热力学第二章",
        "plan_stage": "冲刺阶段",
    }


def _baseline_user_context() -> dict[str, object]:
    return {
        "active_goals": [{"title": "14 天内稳住热力学第二章"}],
        "learning_gaps_summary": "熵增方向判断和可逆/不可逆过程仍然容易混淆。",
        "context_focus": {"focus_mode": "knowledge_focus", "route_intent": "knowledge"},
        "profile_context": {
            "knowledge_summary": {
                "weak_spots": [{"node_name": "熵增方向判断", "mastery": 39}],
            },
            "cognitive_summary": {
                "active_patterns": [{"pattern_name": "启动困难", "pattern_type": "execution", "confidence": 0.81}]
            },
        },
        "user_strategy_state": {
            "difficulty_level": 4,
            "session_mode": "guided",
            "explanation_style": "conceptual",
            "retrieval_emphasis": "balanced",
            "push_vs_support": 0.52,
            "intervention_intensity": "medium",
        },
    }


@pytest.mark.asyncio
async def test_phase5_thermodynamics_component_journey_scores_judgment_layers(monkeypatch, db_session):
    user = User(
        username="phase5_thermo_user",
        email="phase5_thermo_user@example.com",
        hashed_password="hashed",
        nickname="Ava",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="热力学 14 天冲刺",
        type=PlanType.SPRINT,
        description="用真实材料查漏补缺",
        plan_stage=PlanStage.DAILY,
        target_date=(__import__("datetime").datetime.utcnow().date() + timedelta(days=14)),
        daily_available_minutes=90,
        total_estimated_hours=18,
        subject="热力学",
        mastery_level=0.41,
        progress=0.28,
        is_active=True,
        priority=PlanPriority.HIGH,
        is_primary=True,
    )
    db_session.add(plan)

    intervention = InterventionRecord(
        user_id=user.id,
        trigger_type=InterventionTriggerType.STALL_PATTERN,
        delivery_strategy=DeliveryStrategy.MICRO_RESTART,
        delivery_channel=DeliveryChannel.CHAT,
        acceptance_status=InterventionAcceptanceStatus.DELIVERED,
        outcome_status=InterventionOutcomeStatus.PENDING,
    )
    db_session.add(intervention)
    await db_session.commit()
    await db_session.refresh(plan)
    await db_session.refresh(intervention)

    fake_file = SimpleNamespace(
        id=uuid4(),
        file_name="thermo-notes.pdf",
        mime_type="application/pdf",
    )
    fake_result = SimpleNamespace(
        file_name="thermo-notes.pdf",
        score=0.93,
        chunk=SimpleNamespace(
            id=uuid4(),
            file_id=fake_file.id,
            section_title="Entropy",
            page_numbers=[12],
            content="判断熵增方向时，先确定系统边界，再看不可逆过程是否主导。",
        ),
    )

    async def _fake_resolve_scoped_files(db_session, *, user_id, requested_file_ids):
        del db_session, user_id, requested_file_ids
        return [fake_file]

    async def _fake_document_vector_search(self, *, user_id, query, file_ids, vector_query, limit, threshold):
        del self, user_id, query, file_ids, vector_query, limit, threshold
        return [fake_result]

    monkeypatch.setattr(
        "app.orchestration.experience_actuator._resolve_scoped_files",
        _fake_resolve_scoped_files,
    )
    monkeypatch.setattr(
        "app.orchestration.experience_actuator.KnowledgeRetrievalService.document_vector_search",
        _fake_document_vector_search,
    )

    redis = _FakeRedis()
    actuator = ExperienceActuator(db_session, redis=redis)
    builder = SituationBriefBuilder()

    turn_context = _baseline_user_context()

    turn_context["current_query"] = "用我上传的热力学笔记解释熵增方向判断。"
    brief1 = builder.build(
        user_context_payload=turn_context,
        plan_context=_base_plan_context(plan),
        focused_memory={},
        context_briefing_note="用户想先用自己的资料修复热力学概念误解。",
        visible_update_context={},
        dual_core_snapshot={"decision": {"mode": "balanced"}},
        session_feedback_signal={},
        progress_snapshot={},
        adaptation_records=[],
    ).to_dict()
    turn_context["situation_brief"] = brief1
    turn_context["residual_decision_context"] = brief1["decision_context"]
    runtime1 = await actuator.apply(
        user_id=str(user.id),
        session_id="phase5-thermo-session",
        plan_id=plan.id,
        request_id="thermo-turn-1",
        user_message=str(turn_context["current_query"]),
        file_ids=[str(fake_file.id)],
        user_context_payload=turn_context,
    )

    assert turn_context["user_material_grounding"]["status"] == "grounded"

    turn1 = {
        "expected_residual": "R_e",
        "expected_loop_type": "truth_seeking",
        "expected_mode": "explain",
        "expected_grounding": "user_materials",
        "decision_context": deepcopy(turn_context["residual_decision_context"]),
        "auto_strategy_adjustments": runtime1.get("auto_strategy_adjustments", []),
        "user_material_grounding": runtime1.get("user_material_grounding", {}),
        "user_signal": "clearer",
        "freedom_preservation": 0.86,
    }

    turn_context = {
        "active_goals": [{"title": "14 天内稳住热力学第二章"}],
        "current_query": "This is too much and I still cannot start.",
        "context_focus": {"focus_mode": "general_focus", "route_intent": "chat"},
        "profile_context": {
            "cognitive_summary": {
                "active_patterns": [{"pattern_name": "启动困难", "pattern_type": "execution", "confidence": 0.83}]
            }
        },
        "user_strategy_state": _baseline_user_context()["user_strategy_state"],
    }
    brief2 = builder.build(
        user_context_payload=turn_context,
        plan_context=_base_plan_context(plan),
        focused_memory={},
        context_briefing_note="User is overloaded and struggling to start.",
        visible_update_context={},
        dual_core_snapshot={"decision": {"mode": "execution_first"}},
        session_feedback_signal={},
        progress_snapshot={"attention_areas": ["Load is too high this week."]},
        adaptation_records=[],
    ).to_dict()
    turn_context["situation_brief"] = brief2
    turn_context["residual_decision_context"] = brief2["decision_context"]
    runtime2 = await actuator.apply(
        user_id=str(user.id),
        session_id="phase5-thermo-session",
        plan_id=plan.id,
        request_id="thermo-turn-2",
        user_message=str(turn_context["current_query"]),
        file_ids=[str(fake_file.id)],
        user_context_payload=turn_context,
    )

    turn2 = {
        "expected_residual": "R_c",
        "expected_loop_type": "truth_seeking",
        "expected_mode": "stabilize",
        "decision_context": deepcopy(turn_context["residual_decision_context"]),
        "auto_strategy_adjustments": runtime2.get("auto_strategy_adjustments", []),
        "user_signal": "accepted",
        "freedom_preservation": 0.88,
    }

    turn_context = {
        "active_goals": [{"title": "14 天内稳住热力学第二章"}],
        "current_query": "这样轻一点我就能开始了，下一步怎么做最稳？",
        "context_focus": {"focus_mode": "general_focus", "route_intent": "chat"},
        "profile_context": {
            "cognitive_summary": {
                "active_patterns": [{"pattern_name": "启动困难", "pattern_type": "execution", "confidence": 0.81}]
            }
        },
        "active_interventions": [{"intervention_id": str(intervention.id), "source": "runtime_context"}],
        "user_strategy_state": _baseline_user_context()["user_strategy_state"],
    }
    brief3 = builder.build(
        user_context_payload=turn_context,
        plan_context=_base_plan_context(plan),
        focused_memory={},
        context_briefing_note="用户开始恢复行动，Sparkle 需要保留连续性并轻推下一步。",
        visible_update_context={},
        dual_core_snapshot={"decision": {"mode": "execution_first"}},
        session_feedback_signal={},
        progress_snapshot={"highlights": ["用户已经能重新启动。"]},
        adaptation_records=[],
    ).to_dict()
    turn_context["situation_brief"] = brief3
    turn_context["residual_decision_context"] = brief3["decision_context"]
    runtime3 = await actuator.apply(
        user_id=str(user.id),
        session_id="phase5-thermo-session",
        plan_id=plan.id,
        request_id="thermo-turn-3",
        user_message=str(turn_context["current_query"]),
        file_ids=[str(fake_file.id)],
        user_context_payload=turn_context,
    )
    await db_session.refresh(intervention)

    assert runtime3["auto_feedback_binding"]["bound"] is True
    assert intervention.acceptance_status == InterventionAcceptanceStatus.ACTED

    turn3 = {
        "expected_residual": "R_c",
        "expected_loop_type": "truth_seeking",
        "expected_mode": "mobilize",
        "decision_context": deepcopy(turn_context["residual_decision_context"]),
        "active_interventions": deepcopy(turn_context.get("active_interventions", [])),
        "auto_feedback_binding": runtime3.get("auto_feedback_binding", {}),
        "user_signal": "started",
        "freedom_preservation": 0.9,
    }

    observed_modes = [
        turn1["decision_context"].get("experience_mode"),
        turn2["decision_context"].get("experience_mode"),
        turn3["decision_context"].get("experience_mode"),
    ]
    report = ExperiencePhaseEvaluator().evaluate(
        scenario_id="thermo_phase5_live_journey",
        turns=[turn1, turn2, turn3],
        outcomes={
            "misconception_reduction": (
                1.0
                if runtime1.get("user_material_grounding", {}).get("status") == "grounded"
                and runtime1.get("user_material_grounding", {}).get("results")
                else 0.0
            ),
            "task_execution": 1.0 if runtime3.get("auto_feedback_binding", {}).get("bound") else 0.0,
            "consistency": 1.0 if observed_modes == ["explain", "stabilize", "mobilize"] else 0.0,
            "real_world_performance": (
                0.75
                if intervention.acceptance_status == InterventionAcceptanceStatus.ACTED
                and runtime1.get("user_material_grounding", {}).get("status") == "grounded"
                else 0.25
            ),
        },
    )

    assert report.supporting_metrics["turn_count"] == 3
    assert report.intelligence_scorecard["correct_residual_diagnosis"].score == 1.0
    assert report.intelligence_scorecard["correct_loop_selection"].score == 1.0
    assert report.intelligence_scorecard["grounded_evidence_use"].score == 1.0
    assert report.experience_scorecard["real_change"].score >= 0.75
    assert report.experience_scorecard["continuity_and_trust"].score >= 0.6
