from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.card_protocol import (
    DeliveryChannel,
    DeliveryStrategy,
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
    InterventionRecord,
    InterventionTriggerType,
)
from app.models.plan import Plan, PlanStage, PlanType
from app.orchestration.experience_actuator import ExperienceActuator


class _FakeRedis:
    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self._ttl: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self._kv.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._kv[key] = value
        self._ttl[key] = ttl


@pytest.fixture
async def test_plan(db_session, test_user) -> Plan:
    plan = Plan(
        user_id=test_user.id,
        name="Phase 4 测试计划",
        type=PlanType.SPRINT,
        description="验证 experience actuator",
        plan_stage=PlanStage.SPRINT,
        target_date=date(2026, 4, 25),
        daily_available_minutes=60,
        progress=0.1,
        is_active=True,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


@pytest.mark.asyncio
async def test_experience_actuator_auto_applies_session_strategy_adjustments(db_session, test_user, test_plan):
    redis = _FakeRedis()
    actuator = ExperienceActuator(db_session, redis=redis)
    user_context_payload = {
        "current_query": "Please slow down and ground in my notes.",
        "user_strategy_state": {
            "difficulty_level": 3,
            "session_mode": "guided",
            "explanation_style": "conceptual",
            "retrieval_emphasis": "balanced",
            "push_vs_support": 0.5,
            "intervention_intensity": "medium",
        },
        "residual_decision_context": {
            "confidence": 0.84,
            "primary_residual": "R_e",
            "loop_type": "truth_seeking",
            "experience_mode": "explain",
            "intervention_family": "understanding_repair",
            "what_matters_now": "用用户材料把真正的概念误解校准清楚。",
            "system_adjustments": [
                {
                    "field": "retrieval_emphasis",
                    "recommended_value": "user_materials",
                    "target_layer": "session",
                    "reversible": True,
                    "confidence_gate": 0.84,
                },
                {
                    "field": "explanation_style",
                    "recommended_value": "step_by_step",
                    "target_layer": "session",
                    "reversible": True,
                    "confidence_gate": 0.84,
                },
            ],
        },
        "situation_brief": {"decision_context": {}},
    }

    runtime_summary = await actuator.apply(
        user_id=str(test_user.id),
        session_id="phase4-session-adjust",
        plan_id=test_plan.id,
        request_id="req-adjust-1",
        user_message="Use my uploaded notes and go slower.",
        file_ids=[],
        user_context_payload=user_context_payload,
    )

    assert len(runtime_summary["auto_strategy_adjustments"]) == 2
    assert runtime_summary["visible_adaptation"]["what_changed"]
    assert "如果这次调整不合适" in runtime_summary["visible_adaptation"]["reversibility_note"]
    assert "我先按你的材料把真正卡住的点校准清楚" in user_context_payload["proactive_opening_message"]
    assert user_context_payload["user_strategy_state"]["retrieval_emphasis"] == "user_materials"
    assert user_context_payload["user_strategy_state"]["explanation_style"] == "step_by_step"
    assert user_context_payload["residual_decision_context"]["auto_applied_adjustments"][0]["field"] == "retrieval_emphasis"


@pytest.mark.asyncio
async def test_experience_actuator_auto_binds_intervention_feedback(db_session, test_user):
    redis = _FakeRedis()
    actuator = ExperienceActuator(db_session, redis=redis)
    record = InterventionRecord(
        user_id=test_user.id,
        trigger_type=InterventionTriggerType.STALL_PATTERN,
        delivery_strategy=DeliveryStrategy.MICRO_RESTART,
        delivery_channel=DeliveryChannel.CHAT,
        acceptance_status=InterventionAcceptanceStatus.DELIVERED,
        outcome_status=InterventionOutcomeStatus.PENDING,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    user_context_payload = {
        "user_strategy_state": {
            "difficulty_level": 3,
            "session_mode": "guided",
            "explanation_style": "conceptual",
            "retrieval_emphasis": "balanced",
            "push_vs_support": 0.5,
            "intervention_intensity": "medium",
        },
        "active_interventions": [
            {
                "intervention_id": str(record.id),
                "source": "runtime_context",
            }
        ],
        "residual_decision_context": {
            "confidence": 0.78,
            "system_adjustments": [],
            "grounding_priority": ["general_knowledge"],
        },
    }

    runtime_summary = await actuator.apply(
        user_id=str(test_user.id),
        session_id="phase4-feedback-bind",
        plan_id=None,
        request_id="req-feedback-1",
        user_message="这样轻一点我就能开始了。",
        file_ids=[],
        user_context_payload=user_context_payload,
    )
    await db_session.refresh(record)

    assert runtime_summary["auto_feedback_binding"]["bound"] is True
    assert runtime_summary["auto_feedback_binding"]["detected_sentiment"] == "helped"
    assert user_context_payload["last_feedback_binding"]["intervention_id"] == str(record.id)
    assert record.acceptance_status == InterventionAcceptanceStatus.ACTED


@pytest.mark.asyncio
async def test_experience_actuator_auto_retrieves_user_material_grounding(monkeypatch, db_session, test_user):
    actuator = ExperienceActuator(db_session, redis=_FakeRedis())

    fake_file = SimpleNamespace(
        id=uuid4(),
        file_name="thermo-notes.pdf",
        mime_type="application/pdf",
    )
    fake_result = SimpleNamespace(
        file_name="thermo-notes.pdf",
        score=0.91,
        chunk=SimpleNamespace(
            id=uuid4(),
            file_id=fake_file.id,
            section_title="Entropy",
            page_numbers=[12],
            content="熵增方向的判断要先看系统边界，再看不可逆过程的主导项。",
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

    user_context_payload = {
        "current_query": "帮我解释熵增方向判断",
        "user_strategy_state": {
            "difficulty_level": 3,
            "session_mode": "guided",
            "explanation_style": "conceptual",
            "retrieval_emphasis": "user_materials",
            "push_vs_support": 0.5,
            "intervention_intensity": "medium",
        },
        "residual_decision_context": {
            "confidence": 0.82,
            "system_adjustments": [],
            "grounding_priority": ["user_materials", "general_knowledge"],
            "what_matters_now": "先用用户材料校准熵增方向判断。",
        },
    }

    runtime_summary = await actuator.apply(
        user_id=str(test_user.id),
        session_id="phase4-grounding",
        plan_id=None,
        request_id="req-ground-1",
        user_message="用我上传的热力学笔记解释熵增方向判断。",
        file_ids=[str(fake_file.id)],
        user_context_payload=user_context_payload,
    )

    grounding = runtime_summary["user_material_grounding"]
    assert grounding["status"] == "grounded"
    assert grounding["results"][0]["file_name"] == "thermo-notes.pdf"
    assert "熵增方向" in grounding["results"][0]["snippet"]
    assert runtime_summary["visible_adaptation"]["evidence_summary"].startswith("这轮证据先来自你的资料")


@pytest.mark.asyncio
async def test_experience_actuator_keeps_core_adjustments_when_grounding_sidecar_fails(
    monkeypatch,
    db_session,
    test_user,
    test_plan,
):
    actuator = ExperienceActuator(db_session, redis=_FakeRedis())

    async def _fake_resolve_scoped_files(db_session, *, user_id, requested_file_ids):
        del db_session, user_id, requested_file_ids
        raise RuntimeError("vector index unavailable")

    monkeypatch.setattr(
        "app.orchestration.experience_actuator._resolve_scoped_files",
        _fake_resolve_scoped_files,
    )

    user_context_payload = {
        "current_query": "用我的资料解释这个概念。",
        "user_strategy_state": {
            "difficulty_level": 3,
            "session_mode": "guided",
            "explanation_style": "conceptual",
            "retrieval_emphasis": "balanced",
            "push_vs_support": 0.5,
            "intervention_intensity": "medium",
        },
        "residual_decision_context": {
            "confidence": 0.84,
            "primary_residual": "R_e",
            "loop_type": "truth_seeking",
            "experience_mode": "explain",
            "intervention_family": "understanding_repair",
            "what_matters_now": "先把真实误解校准清楚。",
            "grounding_priority": ["user_materials"],
            "feedback_hook": {
                "ask": "这样解释后，真正卡住的点是不是更清楚了？",
            },
            "system_adjustments": [
                {
                    "field": "retrieval_emphasis",
                    "recommended_value": "user_materials",
                    "target_layer": "session",
                    "reversible": True,
                    "confidence_gate": 0.84,
                }
            ],
        },
    }

    runtime_summary = await actuator.apply(
        user_id=str(test_user.id),
        session_id="phase4-sidecar-safe",
        plan_id=test_plan.id,
        request_id="req-sidecar-safe-1",
        user_message="用我的资料解释这个概念。",
        file_ids=["file-1"],
        user_context_payload=user_context_payload,
    )

    assert runtime_summary["auto_strategy_adjustments"][0]["field"] == "retrieval_emphasis"
    assert runtime_summary["user_material_grounding"]["status"] == "file_resolution_failed"
    assert runtime_summary["visible_adaptation"]["what_changed"] == ["优先按你的资料来校准"]
    assert user_context_payload["user_strategy_state"]["retrieval_emphasis"] == "user_materials"


@pytest.mark.asyncio
async def test_experience_actuator_clears_stale_feedback_binding_when_auto_bind_finds_none(
    monkeypatch,
    db_session,
    test_user,
):
    actuator = ExperienceActuator(db_session, redis=_FakeRedis())

    async def _fake_bind_feedback(self, **kwargs):
        del self, kwargs
        return {
            "bound": False,
            "duplicate_suppressed": False,
            "reason": "no_active_intervention",
            "active_interventions": [],
        }

    monkeypatch.setattr(
        "app.orchestration.experience_actuator.InterventionFeedbackBindingService.bind_feedback",
        _fake_bind_feedback,
    )

    user_context_payload = {
        "active_interventions": [{"intervention_id": str(uuid4()), "source": "runtime_context"}],
        "last_feedback_binding": {
            "intervention_id": "stale-binding",
            "sentiment": "helped",
        },
        "user_strategy_state": {
            "difficulty_level": 3,
            "session_mode": "guided",
            "explanation_style": "conceptual",
            "retrieval_emphasis": "balanced",
            "push_vs_support": 0.5,
            "intervention_intensity": "medium",
        },
        "residual_decision_context": {
            "confidence": 0.7,
            "system_adjustments": [],
            "grounding_priority": ["general_knowledge"],
        },
    }

    runtime_summary = await actuator.apply(
        user_id=str(test_user.id),
        session_id="phase4-clear-stale",
        plan_id=None,
        request_id="req-stale-clear",
        user_message="还是不行。",
        file_ids=[],
        user_context_payload=user_context_payload,
    )

    assert runtime_summary["auto_feedback_binding"]["bound"] is False
    assert "last_feedback_binding" not in user_context_payload
