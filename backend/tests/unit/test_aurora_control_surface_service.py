from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.aurora.runtime_v1.state import AuroraIntent, AuroraState, InformationalTension
from app.core.profile_context import (
    ActivePattern,
    CognitiveSummary,
    KnowledgeSummary,
    ProfileContext,
    WeakSpot,
)
from app.core.user_insight_state import UserInsightState
from app.services.aurora_control_surface_service import AuroraControlSurfaceService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class _FakeProfileContextService:
    def __init__(self, db, redis=None) -> None:
        del db, redis

    async def get_profile_context(self, user_id):
        del user_id
        return ProfileContext(
            preferences={
                "cold_start_context": {
                    "goal": "冲刺计算机网络期末复习",
                    "exam_scope": "TCP 状态机",
                    "days_left": 12,
                    "motivation": "这次想把最卡的协议部分真正吃透",
                }
            },
            knowledge_summary=KnowledgeSummary(
                weak_spots=[
                    WeakSpot(
                        node_id="tcp-fsm",
                        node_name="TCP 状态机",
                        mastery=0.32,
                    )
                ]
            ),
            cognitive_summary=CognitiveSummary(
                active_patterns=[
                    ActivePattern(
                        pattern_name="先看结构再进入细节",
                        pattern_type="cognitive",
                        confidence=0.84,
                    )
                ]
            ),
            user_insight_state=UserInsightState(
                goals=[{"label": "把 TCP 状态迁移彻底吃透"}],
                current_state={"predicted_overload_risk": "medium"},
                readiness={"predicted_level": "high"},
                active_bottlenecks=[{"label": "TCP 状态机迁移条件总是混淆"}],
                confidence_metadata={"readiness": 0.82, "knowledge": 0.76},
            ),
            user_state_v1={
                "engagement_state": {"freshness_seconds": 35},
                "working_memory_snapshot": {"freshness_seconds": 18},
            },
        )


class _FakeSelfModelService:
    def __init__(self, redis) -> None:
        del redis

    async def get_readout_summary(self, *, user_id, user_context_payload=None):
        del user_id, user_context_payload
        return {
            "strategy_confidence": 0.74,
            "known_assumptions": [
                {
                    "assumption_id": "daily_available_time",
                    "statement": "用户每天能稳定投入当前计划估计的学习时长",
                    "confidence": 0.71,
                    "evidence": [
                        {
                            "source": "task",
                            "detail": "过去三次任务都能在估计时长内完成。",
                            "observed_at": _utcnow().isoformat(),
                        }
                    ],
                }
            ],
            "harness_effectiveness": {
                "context_hit_rate": 0.78,
                "task_completion_rate": 0.81,
            },
            "needs_recalibration": False,
            "recalibration_reasons": [],
            "task_failure_streak": 0,
        }


class _FakeRuntimeStore:
    def __init__(self, redis, enabled=True) -> None:
        del redis, enabled

    async def load_runtime_state(self, *, user_id, surface, conversation_id):
        del user_id, surface
        if conversation_id != "conv-123":
            return None
        return AuroraState(
            user_id="u-1",
            surface="aurora_modeling",
            conversation_id="conv-123",
            runtime_session_id="conv-123",
            user_model_snapshot={
                "surface_state": {"in_detour": False},
                "cold_start_context": {
                    "goal": "冲刺计算机网络期末复习",
                    "exam_scope": "TCP 状态机",
                    "days_left": 12,
                },
            },
            informational_tensions=[
                InformationalTension(
                    tension_id="t-1",
                    domain="goal",
                    description="需要进一步收紧 TCP 状态迁移这个核心目标。",
                    priority=0.9,
                )
            ],
            current_intent=AuroraIntent(intent_type="confirm_understanding"),
            updated_at=_utcnow(),
        )

    async def load_latest_surface_state(self, *, user_id, surface):
        del user_id, surface
        return None


class _FakePersistenceStore:
    def __init__(self, db, enabled=True) -> None:
        del db, enabled

    async def load_cognitive_snapshot(self, user_id):
        del user_id
        return None


class _FakeControlSurfaceService:
    def __init__(self, db, redis=None, enabled=True) -> None:
        del db, redis, enabled

    async def read_control_surface(self, user_id):
        del user_id
        return SimpleNamespace(
            runtime_enabled=True,
            model_dump=lambda mode="json": {"runtime_enabled": True},
        )


@pytest.mark.asyncio
async def test_control_surface_builds_four_real_facets(monkeypatch):
    monkeypatch.setattr(
        "app.services.aurora_control_surface_service.ProfileContextService",
        _FakeProfileContextService,
    )
    monkeypatch.setattr(
        "app.services.aurora_control_surface_service.SparkleSelfModelService",
        _FakeSelfModelService,
    )
    monkeypatch.setattr(
        "app.services.aurora_control_surface_service.AuroraRuntimeStore",
        _FakeRuntimeStore,
    )
    monkeypatch.setattr(
        "app.services.aurora_control_surface_service.AuroraPersistenceStore",
        _FakePersistenceStore,
    )
    monkeypatch.setattr(
        "app.services.aurora_control_surface_service.ControlSurfaceService",
        _FakeControlSurfaceService,
    )

    snapshot = await AuroraControlSurfaceService(db=None, redis=None).build_snapshot(
        user_id=uuid4(),
        conversation_id="conv-123",
    )

    assert snapshot["overall_status"] == "calibration_available"
    assert snapshot["scene_alignment"] == "matched"
    assert snapshot["progress"] == {"ready_count": 4, "active_count": 4, "total": 4}

    facets = {item["key"]: item for item in snapshot["facets"]}
    assert set(facets) == {"user_model", "self_model", "scene_model", "goal_model"}
    assert facets["user_model"]["status"] == "ready"
    assert "TCP 状态机" in facets["user_model"]["summary"]
    assert facets["self_model"]["status"] == "ready"
    assert facets["scene_model"]["status"] == "ready"
    assert facets["scene_model"]["meta"]["conversation_match"] is True
    assert facets["goal_model"]["status"] == "ready"
    assert any(
        "TCP 状态机" in signal or "目标" in signal
        for signal in facets["goal_model"]["signals"]
    )


class _RecalibratingSelfModelService(_FakeSelfModelService):
    async def get_readout_summary(self, *, user_id, user_context_payload=None):
        payload = await super().get_readout_summary(
            user_id=user_id,
            user_context_payload=user_context_payload,
        )
        payload.update(
            {
                "strategy_confidence": 0.38,
                "needs_recalibration": True,
                "recalibration_reasons": ["最近任务完成率持续偏低，Aurora 正在回收原有假设。"],
            }
        )
        return payload


class _FallbackRuntimeStore(_FakeRuntimeStore):
    async def load_runtime_state(self, *, user_id, surface, conversation_id):
        del user_id, surface, conversation_id
        return None

    async def load_latest_surface_state(self, *, user_id, surface):
        del user_id, surface
        return AuroraState(
            user_id="u-1",
            surface="aurora_checkpoint",
            conversation_id="older-conv",
            runtime_session_id="older-conv",
            user_model_snapshot={"surface_state": {"in_detour": True}},
            informational_tensions=[],
            updated_at=_utcnow(),
        )


@pytest.mark.asyncio
async def test_control_surface_marks_recalibration_and_conversation_fallback(monkeypatch):
    monkeypatch.setattr(
        "app.services.aurora_control_surface_service.ProfileContextService",
        _FakeProfileContextService,
    )
    monkeypatch.setattr(
        "app.services.aurora_control_surface_service.SparkleSelfModelService",
        _RecalibratingSelfModelService,
    )
    monkeypatch.setattr(
        "app.services.aurora_control_surface_service.AuroraRuntimeStore",
        _FallbackRuntimeStore,
    )
    monkeypatch.setattr(
        "app.services.aurora_control_surface_service.AuroraPersistenceStore",
        _FakePersistenceStore,
    )
    monkeypatch.setattr(
        "app.services.aurora_control_surface_service.ControlSurfaceService",
        _FakeControlSurfaceService,
    )

    snapshot = await AuroraControlSurfaceService(db=None, redis=None).build_snapshot(
        user_id=uuid4(),
        conversation_id="live-conv",
    )

    facets = {item["key"]: item for item in snapshot["facets"]}
    assert snapshot["overall_status"] == "risk_found"
    assert snapshot["scene_alignment"] == "fallback"
    assert facets["self_model"]["status"] == "recalibrating"
    assert "最近任务完成率持续偏低" in facets["self_model"]["summary"]
    assert facets["scene_model"]["meta"]["conversation_match"] is False
