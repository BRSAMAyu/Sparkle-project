from __future__ import annotations

import sys
import types
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.learning.bayesian_learner import BayesianLearner
from app.routing.tool_preference_shadow import ToolPreferenceShadowRecorder


class _FakeGraphRouter:
    def __init__(self) -> None:
        self._nodes = {"orchestrator"}

    class _Graph:
        def __init__(self, nodes: set[str]) -> None:
            self._nodes = nodes

        def nodes(self):
            return self._nodes

        def neighbors(self, _current: str):
            return []

    @property
    def graph(self):
        return self._Graph(self._nodes)


class _FakeHybridRouter:
    def __init__(self, graph_router, semantic_router):
        self.graph_router = graph_router
        self.semantic_router = semantic_router

    async def find_route(self, current: str, query: str, context: dict) -> str | None:
        return None


class _FakeSemanticRouter:
    def __init__(self, embedding_service=None, knowledge_graph=None):
        self.embedding_service = embedding_service
        self.knowledge_graph = knowledge_graph


class _FakeExplorationRouter:
    def __init__(self, learner, user_id=None):
        self.learner = learner
        self.user_id = user_id

    async def select_route(self, source: str, targets: list[str], context: dict = None) -> str | None:
        return targets[0] if targets else None


def _install_router_node_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    semantic_module = types.ModuleType("app.routing.semantic_router")
    semantic_module.SemanticRouter = _FakeSemanticRouter
    semantic_module.HybridRouter = _FakeHybridRouter
    monkeypatch.setitem(sys.modules, "app.routing.semantic_router", semantic_module)

    embedding_module = types.ModuleType("app.services.embedding_service")
    embedding_module.embedding_service = object()
    monkeypatch.setitem(sys.modules, "app.services.embedding_service", embedding_module)

    import app.routing.router_node as router_node_module

    monkeypatch.setattr(router_node_module, "GraphBasedRouter", _FakeGraphRouter)
    monkeypatch.setattr(router_node_module, "HybridExplorationRouter", _FakeExplorationRouter)


@pytest.mark.asyncio
async def test_rule_v_router_node_forwards_redis_to_tool_preference_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_router_node_stubs(monkeypatch)

    import app.routing.router_node as router_node_module

    captured: dict[str, object] = {}

    class _RecordingToolPreferenceRouter:
        def __init__(self, db_session, user_id, redis_client=None):
            captured["db_session"] = db_session
            captured["user_id"] = user_id
            captured["redis_client"] = redis_client
            self.learner = BayesianLearner()

        async def update_learner_from_history(self) -> None:
            return None

        async def rank_tools_by_success(self, candidates, context=None):
            return [(candidate, 0.5) for candidate in candidates]

        async def get_tool_stats_snapshot(self, tool_name: str) -> dict:
            return {"tool_name": tool_name, "success_rate": 50.0, "usage_count": 1, "avg_time_ms": 10}

    monkeypatch.setattr(router_node_module, "ToolPreferenceRouter", _RecordingToolPreferenceRouter)

    user_id = uuid.uuid4()
    redis_client = object()
    state = SimpleNamespace(
        messages=[{"content": "帮我整理计划"}],
        context_data={
            "current_node": "orchestrator",
            "user_id": str(user_id),
            "db_session": object(),
        },
    )

    router = router_node_module.RouterNode(
        routes=["generation", "tool_execution"],
        redis_client=redis_client,
        user_id=str(user_id),
    )

    await router(state)

    assert captured["redis_client"] is redis_client
    assert captured["user_id"] == user_id


@pytest.mark.asyncio
async def test_router_node_keeps_safe_fallback_when_redis_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_router_node_stubs(monkeypatch)

    import app.routing.router_node as router_node_module

    captured: dict[str, object] = {}

    class _RecordingToolPreferenceRouter:
        def __init__(self, db_session, user_id, redis_client=None):
            captured["redis_client"] = redis_client
            self.learner = BayesianLearner()

        async def update_learner_from_history(self) -> None:
            return None

        async def rank_tools_by_success(self, candidates, context=None):
            return [(candidate, 0.5) for candidate in candidates]

        async def get_tool_stats_snapshot(self, tool_name: str) -> dict:
            return {"tool_name": tool_name, "success_rate": 50.0, "usage_count": 1, "avg_time_ms": 10}

    monkeypatch.setattr(router_node_module, "ToolPreferenceRouter", _RecordingToolPreferenceRouter)

    user_id = uuid.uuid4()
    state = SimpleNamespace(
        messages=[{"content": "帮我整理计划"}],
        context_data={
            "current_node": "orchestrator",
            "user_id": str(user_id),
            "db_session": object(),
        },
    )

    router = router_node_module.RouterNode(
        routes=["generation", "tool_execution"],
        redis_client=None,
        user_id=str(user_id),
    )

    await router(state)

    assert captured["redis_client"] is None


class _MemoryRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.values[key] = value
        self.ttls[key] = ttl
        return True


@pytest.mark.asyncio
async def test_router_node_shadow_mode_records_divergence_without_changing_fallback_choice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_router_node_stubs(monkeypatch)

    import app.routing.router_node as router_node_module

    class _ShadowToolPreferenceRouter:
        def __init__(self, db_session, user_id, redis_client=None):
            self.learner = BayesianLearner()

        async def update_learner_from_history(self) -> None:
            return None

        async def rank_tools_by_success(self, candidates, context=None):
            return [("fallback_tool", 0.9), ("learner_tool", 0.7)]

        async def get_tool_stats_snapshot(self, tool_name: str) -> dict:
            return {"tool_name": tool_name, "success_rate": 50.0, "usage_count": 1, "avg_time_ms": 10}

    monkeypatch.setattr(router_node_module, "ToolPreferenceRouter", _ShadowToolPreferenceRouter)
    monkeypatch.setenv("SPARKLE_CL1_SHADOW_MODE", "true")

    user_id = uuid.uuid4()
    redis_client = _MemoryRedis()
    state = SimpleNamespace(
        messages=[{"content": "帮我整理计划"}],
        context_data={
            "current_node": "state_plan",
            "user_id": str(user_id),
            "db_session": object(),
        },
    )

    router = router_node_module.RouterNode(
        routes=["generation", "tool_execution"],
        redis_client=redis_client,
        user_id=str(user_id),
    )
    router._get_candidate_routes = AsyncMock(return_value=["fallback_tool", "learner_tool"])
    router.exploration_router.select_route = AsyncMock(return_value="learner_tool")

    routed = await router(state)

    assert routed.context_data["router_decision"] == "fallback_tool"

    summary = await router.shadow_recorder.get_divergence_summary(user_id=str(user_id))
    assert summary["total_records"] == 1
    assert summary["diverged_records"] == 1
    assert summary["divergence_rate"] == 1.0
    assert summary["latest_record"]["source_state"] == "state_plan"
    assert summary["latest_record"]["fallback_choice"] == "fallback_tool"
    assert summary["latest_record"]["learner_choice"] == "learner_tool"


@pytest.mark.asyncio
async def test_tool_preference_shadow_recorder_returns_recent_records_and_summary() -> None:
    redis = _MemoryRedis()
    recorder = ToolPreferenceShadowRecorder(redis)

    await recorder.record_decision(
        user_id="u1",
        source_state="state_plan",
        fallback_choice="create_plan",
        learner_choice="generate_tasks_for_plan",
        eventual_outcome=None,
    )
    await recorder.record_decision(
        user_id="u1",
        source_state="state_task",
        fallback_choice="create_task",
        learner_choice="create_task",
        eventual_outcome="accepted",
    )

    records = await recorder.get_recent_records(user_id="u1", limit=5)
    summary = await recorder.get_divergence_summary(user_id="u1", limit=5)

    assert len(records) == 2
    assert records[0]["user_id"] == "u1"
    assert summary["total_records"] == 2
    assert summary["diverged_records"] == 1
    assert summary["divergence_rate"] == 0.5
    assert summary["latest_record"]["eventual_outcome"] == "accepted"
