"""F821/B023 未定义名与闭包错绑修复的触发测试（DEBT-BATCH2 验收转维修复）。

覆盖 8 处登记项中被修复的分支，全部为真实调用该分支的最小单测：
1. monitoring /health 错误路径 logger（api/v1/monitoring.py）
2. celery scan_behavior_patterns 内 UUID（core/celery_tasks.py）
3. StreamChat 客户端断连分支 request_id（services/agent_grpc_service.py）
4. get_feedback_statistics 内存侧 cutoff_str（services/feedback_driven_generation.py）
5. SearchNodes mastery 回查 select（services/galaxy_grpc_service.py）
6. GetGalaxyStats 平均掌握度 sa_select（services/galaxy_grpc_service.py）
7. SpineOrchestrator.on_absence_detected 注解 AbsenceSnapshot（signals/spine_orchestrator.py）
8. execute_plan 层内信号量闭包绑定 B023（orchestration/executor.py，行为等价加固）

零真实 LLM 调用、零真实 DB/Redis 连接。
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import get_type_hints

# ---------------------------------------------------------------------------
# 1. monitoring.py /health 错误路径：修复前 NameError: name 'logger' is not defined
# ---------------------------------------------------------------------------


async def test_websocket_health_error_path_uses_module_logger(monkeypatch):
    from app.api.v1 import monitoring as monitoring_module

    class _ExplodingLen:
        def __len__(self) -> int:
            raise RuntimeError("connection map exploded")

    monkeypatch.setattr(monitoring_module.manager, "active_connections", _ExplodingLen())

    result = await monitoring_module.websocket_health()

    assert result["status"] == "unhealthy"
    assert "error" in result


# ---------------------------------------------------------------------------
# 2. celery scan_behavior_patterns：修复前 _run 内 NameError: name 'UUID' is not defined
# ---------------------------------------------------------------------------


def test_scan_behavior_patterns_task_resolves_uuid(monkeypatch):
    from app.core import celery_tasks
    from app.db import session as db_session_mod
    from app.services.analytics import behavior_pattern_service as bps_mod

    user_id = str(uuid.uuid4())
    task_ids = [uuid.uuid4(), uuid.uuid4()]

    class _FakeResult:
        def all(self):
            return [(tid,) for tid in task_ids]

    class _FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def execute(self, stmt):
            return _FakeResult()

    class _FakeService:
        def __init__(self, session):
            pass

        async def analyze_planning_optimism(self, uid, tid):
            return {"user_id": str(uid), "task_id": str(tid)}

    monkeypatch.setattr(db_session_mod, "AsyncSessionLocal", _FakeSession)
    monkeypatch.setattr(bps_mod, "BehaviorPatternService", _FakeService)

    result = celery_tasks.scan_behavior_patterns.apply(args=(user_id,))

    assert result.successful(), f"task failed: {result.result!r}"
    assert result.result["patterns_found"] == 2


# ---------------------------------------------------------------------------
# 3. StreamChat 客户端断连分支：修复前 NameError 落入错误契约（ERROR 响应）
# ---------------------------------------------------------------------------


class _FakeGrpcContext:
    def __init__(self, metadata):
        self._metadata = metadata
        self.code = None
        self.details = None

    def invocation_metadata(self):
        return self._metadata

    def cancelled(self) -> bool:
        return True

    def set_code(self, code):
        self.code = code

    def set_details(self, details):
        self.details = details


class _FakeSession:
    def __init__(self):
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass


class _FakeSessionFactory:
    def __init__(self):
        self.sessions: list[_FakeSession] = []

    def __call__(self):
        session = _FakeSession()
        self.sessions.append(session)
        return session


async def test_streamchat_client_disconnect_branch_no_name_error(monkeypatch):
    from app.gen.agent.v1 import agent_service_pb2
    from app.learning.prompt_bandit import PromptBandit
    from app.services import push_scheduler as push_scheduler_mod
    from app.services.agent_grpc_service import AgentServiceImpl

    async def _fake_select(self, workflow_id, versions):
        return versions[0]

    monkeypatch.setattr(PromptBandit, "select", _fake_select)

    class _FakePushScheduler:
        def __init__(self, db):
            pass

        async def enqueue_session_end_recall(self, user_id, session_context):
            return None

    monkeypatch.setattr(push_scheduler_mod, "PushScheduler", _FakePushScheduler)

    class _FakeOrchestrator:
        redis = None

        async def process_stream(self, request, db_session, context_data):
            yield agent_service_pb2.ChatResponse()

    factory = _FakeSessionFactory()
    svc = object.__new__(AgentServiceImpl)
    svc.orchestrator = _FakeOrchestrator()
    svc.db_session_factory = factory

    request = agent_service_pb2.ChatRequest(request_id="req-f821", session_id="sess-f821")
    ctx = _FakeGrpcContext((("user-id", str(uuid.uuid4())),))

    responses = [resp async for resp in svc.StreamChat(request, ctx)]

    # 断连分支 break 后走 no-text fallback（STOP），而非 NameError 落入 ERROR 契约
    assert len(responses) == 1
    assert responses[0].finish_reason == agent_service_pb2.STOP
    assert responses[0].request_id == "req-f821"
    assert ctx.code is None
    # sessions: [0]=bootstrap, [1]=stream（断连 break 后正常 commit）, [2]=recall
    assert len(factory.sessions) >= 2
    assert factory.sessions[1].committed


# ---------------------------------------------------------------------------
# 4. get_feedback_statistics 内存侧过滤：修复前 NameError: name 'cutoff_str' is not defined
# ---------------------------------------------------------------------------


async def test_get_feedback_statistics_counts_regen_requests_with_cutoff(monkeypatch):
    from app.services.feedback_driven_generation import (
        FeedbackDrivenGenerationService,
        RegenerationRequest,
        RegenerationType,
    )

    def _iso(days_ago: int) -> str:
        return (datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_ago)).isoformat()

    recent = RegenerationRequest(
        request_id="r-recent",
        original_content_id="c1",
        review_id="rev1",
        user_id="u1",
        regeneration_type=RegenerationType.IMPROVE_QUALITY,
        created_at=_iso(1),
    )
    stale = RegenerationRequest(
        request_id="r-stale",
        original_content_id="c2",
        review_id="rev2",
        user_id="u1",
        regeneration_type=RegenerationType.IMPROVE_QUALITY,
        created_at=_iso(40),
    )

    class _FakeScalars:
        def __init__(self, items):
            self._items = items

        def all(self):
            return self._items

    class _FakeResult:
        def __init__(self, items):
            self._items = items

        def scalars(self):
            return _FakeScalars(self._items)

    class _FakeDB:
        async def execute(self, stmt):
            # 单条评分反馈，保证不触发空反馈早退分支
            return _FakeResult([SimpleNamespace(rating=5, was_helpful=True, was_accurate=True)])

    # __init__ 会拉起 LLM 服务（与本方法无关），绕过以保持零 LLM 依赖
    svc = object.__new__(FeedbackDrivenGenerationService)
    svc._db = _FakeDB()
    svc._regeneration_requests = {recent.request_id: recent, stale.request_id: stale}

    stats = await svc.get_feedback_statistics(days=30)

    assert stats["total_feedbacks"] == 1
    assert stats["avg_rating"] == 5.0
    # 30 天窗口只应命中 recent（cutoff_str 字符串比较方向正确）
    assert stats["regeneration_requests"] == 1


# ---------------------------------------------------------------------------
# 5/6. galaxy_grpc_service：修复前 NameError: select / sa_select → 吞成 INTERNAL 空响应
# ---------------------------------------------------------------------------


class _AsyncCM:
    def __init__(self, obj):
        self._obj = obj

    async def __aenter__(self):
        return self._obj

    async def __aexit__(self, *exc):
        return False


def _make_servicer(db):
    from app.services import galaxy_grpc_service as ggs

    factory = lambda: _AsyncCM(db)  # noqa: E731
    servicer = object.__new__(ggs.GalaxyGrpcServiceImpl)
    servicer.db_session_factory = factory
    return servicer


async def test_search_nodes_mastery_lookup_resolves_select(monkeypatch):
    from app.gen.galaxy.v1 import galaxy_service_pb2
    from app.services import galaxy_grpc_service as ggs

    node = SimpleNamespace(id=uuid.uuid4(), name="AlgebraNode", source_type="concept", keywords=["math"])

    class _FakeGalaxyService:
        def __init__(self, db):
            self.db = db

        async def semantic_search(self, *, user_id, query, subject_id, limit):
            return [SimpleNamespace(node=node)]

    class _Rows:
        def all(self):
            return []

    class _DB:
        async def execute(self, stmt):
            return _Rows()

    monkeypatch.setattr(ggs, "GalaxyService", _FakeGalaxyService)

    ctx = _FakeGrpcContext((("user-id", str(uuid.uuid4())),))
    resp = await _make_servicer(_DB()).SearchNodes(galaxy_service_pb2.SearchNodesRequest(query="algebra", limit=5), ctx)

    # 修复前 select 未定义 → except 落 INTERNAL 空响应（total_found=0）
    assert ctx.code is None
    assert resp.total_found == 1
    assert resp.nodes[0].label == "AlgebraNode"


async def test_get_galaxy_stats_avg_mastery_resolves_sa_select(monkeypatch):
    from app.gen.galaxy.v1 import galaxy_service_pb2
    from app.services import galaxy_grpc_service as ggs

    fake_stats = SimpleNamespace(
        total_nodes=10,
        mastered_count=4,
        unlocked_count=6,
        sector_distribution={},
    )

    class _FakeStatsSvc:
        async def calculate_user_stats(self, user_id):
            return fake_stats

    class _FakeGalaxyService:
        def __init__(self, db):
            self.db = db
            self.stats = _FakeStatsSvc()

    class _ScalarResult:
        def scalar(self):
            return 0.5

    class _DB:
        async def execute(self, stmt):
            return _ScalarResult()

    monkeypatch.setattr(ggs, "GalaxyService", _FakeGalaxyService)

    ctx = _FakeGrpcContext((("user-id", str(uuid.uuid4())),))
    resp = await _make_servicer(_DB()).GetGalaxyStats(galaxy_service_pb2.GetGalaxyStatsRequest(), ctx)

    # 修复前 sa_select 未定义 → except 落 INTERNAL 空响应（average_mastery=0）
    assert ctx.code is None
    assert resp.average_mastery == 0.5
    assert resp.total_nodes == 10
    assert resp.in_progress_nodes == 2


# ---------------------------------------------------------------------------
# 7. SpineOrchestrator.on_absence_detected 注解：修复前 get_type_hints 触发 NameError
# ---------------------------------------------------------------------------


def test_on_absence_detected_annotation_resolves():
    from app.signals.absence_detector import AbsenceSnapshot
    from app.signals.spine_orchestrator import SpineOrchestrator

    hints = get_type_hints(SpineOrchestrator.on_absence_detected)

    assert hints["snapshot"] is AbsenceSnapshot


# ---------------------------------------------------------------------------
# 8. execute_plan 层内信号量（B023 默认参绑定加固）：行为等价 + 每层独立并发上限
# ---------------------------------------------------------------------------


async def test_dag_layer_semaphore_bound_per_layer(monkeypatch):
    from app.orchestration import executor as executor_mod
    from app.orchestration.executor import StepResult, ToolExecutor
    from app.orchestration.schemas import ExecutablePlan, ToolCallSpec
    from app.tools.base import ToolResult

    max_conc = executor_mod._DAG_LAYER_MAX_CONCURRENCY
    steps_per_layer = max_conc + 2  # 超过上限，验证并发被钳制

    inflight = 0
    current = {"layer": -1}
    target = {"n": 0}
    gate = {"event": None}
    peak_by_layer: dict[int, int] = {}

    async def fake_execute_step(self, spec, user_id, db_session, progress_callback, runtime_context=None):
        nonlocal inflight
        inflight += 1
        peak_by_layer[current["layer"]] = max(peak_by_layer.get(current["layer"], 0), inflight)
        if gate["event"] is not None and inflight >= target["n"] and not gate["event"].is_set():
            gate["event"].set()
        try:
            await asyncio.wait_for(gate["event"].wait(), timeout=5)
        except TimeoutError:
            pass
        inflight -= 1
        return StepResult(
            step_id=spec.id,
            tool_name=spec.name,
            tool_result=ToolResult(success=True, tool_name=spec.name, data={"ok": True}),
        )

    async def observer(event: dict):
        if event["event"] == "layer_start":
            current["layer"] = event["layer_index"]
            peak_by_layer.setdefault(current["layer"], 0)
            target["n"] = min(steps_per_layer, max_conc)
            gate["event"] = asyncio.Event()

    monkeypatch.setattr(ToolExecutor, "_execute_step", fake_execute_step)

    layer0 = [ToolCallSpec(id=f"s{i}", name="tool_a", params={}) for i in range(steps_per_layer)]
    layer1 = [ToolCallSpec(id=f"s{steps_per_layer + i}", name="tool_b", params={}) for i in range(steps_per_layer)]
    plan = ExecutablePlan(
        plan_id="plan-f821",
        tool_calls=layer0 + layer1,
        execution_order=[[tc.id for tc in layer0], [tc.id for tc in layer1]],
        total_steps=steps_per_layer * 2,
    )

    executor = ToolExecutor()
    result = await executor.execute_plan(
        plan=plan,
        user_id="u1",
        db_session=None,
        execution_observer=observer,
    )

    assert result.aborted is False
    assert len(result.step_results) == steps_per_layer * 2
    # 每层各自拿到本层信号量：并发顶到上限但绝不超过
    assert peak_by_layer[0] == max_conc
    assert peak_by_layer[1] == max_conc
    assert all(peak <= max_conc for peak in peak_by_layer.values())
