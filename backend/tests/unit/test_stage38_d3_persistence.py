from __future__ import annotations

import sys
from types import SimpleNamespace
import types
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

import app.core.celery_app as celery_module
from app.core.cache import cache_service
from app.core.metrics import (
    ERROR_REPLAN_BRIDGE_BLOCKED_BY_GATE_TOTAL,
    ERROR_REPLAN_BRIDGE_EVALUATED_TOTAL,
)

_gen_pkg = types.ModuleType("app.gen")
_sparkle_pkg = types.ModuleType("app.gen.sparkle")
_inference_pkg = types.ModuleType("app.gen.sparkle.inference")
_v1_pkg = types.ModuleType("app.gen.sparkle.inference.v1")
_signals_pkg = types.ModuleType("app.gen.sparkle.signals")
_signals_v1_pkg = types.ModuleType("app.gen.sparkle.signals.v1")
_adaptive_replanner_pkg = types.ModuleType("app.orchestration.adaptive_replanner")
_gen_pkg.__path__ = []
_sparkle_pkg.__path__ = []
_inference_pkg.__path__ = []
_signals_pkg.__path__ = []
_v1_pkg.inference_pb2 = types.SimpleNamespace(
    InferenceRequest=object,
    Budgets=object,
    Message=object,
    PREDICT_NEXT_ACTIONS=0,
    P0=0,
)
_signals_v1_pkg.signals_pb2 = types.SimpleNamespace()
_adaptive_replanner_pkg.AdaptiveReplanner = object
sys.modules.setdefault("app.gen", _gen_pkg)
sys.modules.setdefault("app.gen.sparkle", _sparkle_pkg)
sys.modules.setdefault("app.gen.sparkle.inference", _inference_pkg)
sys.modules.setdefault("app.gen.sparkle.inference.v1", _v1_pkg)
sys.modules.setdefault("app.gen.sparkle.signals", _signals_pkg)
sys.modules.setdefault("app.gen.sparkle.signals.v1", _signals_v1_pkg)
sys.modules.setdefault("app.orchestration.adaptive_replanner", _adaptive_replanner_pkg)

from app.services.error_replan_bridge import ErrorReplanBridge
from app.services.push_service import PushService
from app.services.report.learning_report_agent import LearningReportAgent
from app.services.simulation.simulation_engine import SimulationEngine, SimulationSession
from app.services.simulation.simulation_state import LearningSimulationState


def _raise_broker_down(*args, **kwargs):
    raise RuntimeError("broker down")


@pytest.mark.asyncio
async def test_error_replan_bridge_records_stage38_gate_metrics(monkeypatch):
    user_id = uuid4()
    error_id = uuid4()
    bridge = ErrorReplanBridge(db=SimpleNamespace())

    monkeypatch.setattr(
        "app.services.error_replan_bridge.AuroraStage38KillSwitchService.get_feature_mode",
        AsyncMock(return_value="shadow"),
    )

    before_eval = ERROR_REPLAN_BRIDGE_EVALUATED_TOTAL.labels(mode="shadow")._value.get()
    before_blocked = ERROR_REPLAN_BRIDGE_BLOCKED_BY_GATE_TOTAL.labels(
        gate="no_linked_nodes",
        mode="shadow",
    )._value.get()

    result = await bridge.on_error_created(user_id=user_id, error_id=error_id, linked_node_ids=[])

    assert result["reason"] == "no_linked_nodes"
    assert ERROR_REPLAN_BRIDGE_EVALUATED_TOTAL.labels(mode="shadow")._value.get() == before_eval + 1
    assert (
        ERROR_REPLAN_BRIDGE_BLOCKED_BY_GATE_TOTAL.labels(gate="no_linked_nodes", mode="shadow")._value.get()
        == before_blocked + 1
    )


@pytest.mark.asyncio
async def test_push_service_shadow_mode_computes_without_sending(db_session, test_user, monkeypatch):
    service = PushService(db_session)
    policy = SimpleNamespace(
        silent_during_focus=False,
        timezone="Asia/Shanghai",
        active_hours=[],
        min_interval_minutes=0,
        daily_cap=5,
    )
    prefs = SimpleNamespace(explicit={})
    engine = SimpleNamespace(
        get_push_policy_profile=AsyncMock(return_value=policy),
        pref_service=SimpleNamespace(get_preferences=AsyncMock(return_value=prefs)),
    )

    class TriggerStrategy:
        trigger_type = "memory"

        async def should_trigger(self, user, current_policy):
            return True

        async def get_context_data(self, user):
            return {"topic": "复盘"}

    class NoTriggerStrategy:
        trigger_type = "noop"

        async def should_trigger(self, user, current_policy):
            return False

        async def get_context_data(self, user):
            return {}

    monkeypatch.setattr("app.services.push_service.get_personalization_engine", lambda db, redis: engine)
    monkeypatch.setattr("app.services.push_service.SprintStrategy", lambda db: TriggerStrategy())
    monkeypatch.setattr("app.services.push_service.MemoryStrategy", lambda db: NoTriggerStrategy())
    monkeypatch.setattr("app.services.push_service.EmptyCapsuleStrategy", lambda db: NoTriggerStrategy())
    monkeypatch.setattr("app.services.push_service.CuriosityStrategy", lambda db: NoTriggerStrategy())
    monkeypatch.setattr("app.services.push_service.InactivityStrategy", lambda db: NoTriggerStrategy())
    monkeypatch.setattr(service, "_check_frequency_cap", AsyncMock(return_value=False))
    monkeypatch.setattr(service, "_is_active_time", lambda current_policy: True)
    monkeypatch.setattr(service, "_generate_push_content", AsyncMock(return_value={"title": "Hi", "body": "Body"}))
    send_push = AsyncMock()
    monkeypatch.setattr(service, "_send_push", send_push)

    result = await service.process_user_push(test_user, delivery_mode="shadow")

    assert result == {"triggered": True, "sent": False, "shadowed": True, "trigger_type": "memory"}
    send_push.assert_not_awaited()


@pytest.mark.asyncio
async def test_simulation_checkpoint_loads_from_db_when_cache_misses(db_session, test_user, monkeypatch):
    engine = SimulationEngine(db_session)
    session = SimulationSession(
        id="sim-stage38-1",
        scenario_key="study_group",
        state=LearningSimulationState.WAITING_FOR_USER,
        topic="线代讨论",
        participants=[],
        rounds=[],
        insight_summary="需要继续讨论矩阵秩",
    )

    monkeypatch.setattr(cache_service, "set", AsyncMock(return_value=None))
    monkeypatch.setattr(cache_service, "get", AsyncMock(return_value=None))
    monkeypatch.setattr(celery_module, "schedule_long_task", _raise_broker_down)

    await engine._persist_checkpoint(user_id=test_user.id, session=session, participants=[])
    engine._local_checkpoints.clear()

    payload = await engine._load_checkpoint(session_id=session.id, user_id=test_user.id)

    assert payload["id"] == session.id
    assert payload["topic"] == "线代讨论"
    assert payload["user_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_learning_report_loads_from_db_when_cache_misses(db_session, test_user, monkeypatch):
    agent = LearningReportAgent(db_session)
    payload = {
        "report_id": "report-stage38-1",
        "sections": ["概览", "行动"],
        "markdown": "# 测试报告",
        "delivery_mode": "full",
        "quality_mode": "full_analysis",
        "trigger_source": "api",
    }

    monkeypatch.setattr(cache_service, "set", AsyncMock(return_value=None))
    monkeypatch.setattr(cache_service, "get", AsyncMock(return_value=None))
    monkeypatch.setattr(celery_module, "schedule_long_task", _raise_broker_down)

    await agent._cache_report(user_id=test_user.id, cache_version="v-stage38", payload=payload)
    loaded = await agent._load_cached_report(user_id=test_user.id, cache_version="v-stage38")

    assert loaded == payload
