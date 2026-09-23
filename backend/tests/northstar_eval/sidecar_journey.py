"""SIDECAR-JOURNEY · 旅程层：Aurora 规划旁路 + fast-track 多轮续聊的真实路径（API 级，引擎直调）。

照 ``tests/northstar_eval/real_drive.py`` 风格（phase 驱动 + 结构化证据 + 诚实降级），
但走**引擎直调**（gRPC ``ChatRequest`` → ``ChatOrchestrator.process_stream``），
不依赖网关 / PostgreSQL / 真实 Redis / .env——全部外部协作者桩化（进程内）。

旅程（同一 user_id + session_id 连续三轮，wt190 修复后首次可达的真实用户路径）::

    T1 target_open  「7天后考计算机网络，没学过，每天2小时」→ fast-track 冲刺开场（Day0 建 target）
    T2 digression   「等等，先帮我查一下这个任务完成没有」→ 规划离题：sidecar 挂载 + 通用链作答
    T3 return       「回到规划，把节奏调轻一点」→ fast-track 续聊：策略修订，不重新开场

任务卡三条断言点::

    A1 第二轮开场不重复 onboarding（T2 回答非开场白且无 fast-track 元数据；T3 续聊非重开）
    A2 sidecar 出现过一次（全旅程挂载计数 == 1，且恰在 T2）
    A3 回归提问正常回答（T3 策略修订内容帧 + 同一 planning_session_id + AWAITING_CONFIRM）

诚实红线（mock 边界，不得对上报宣称超出）::

    - 通用链回答文本由图桩（LLM 替身）确定性给出——只验证**路径与契约**，不验证回答质量；
    - Aurora 决策内容（decision_loop.decide → soft_return_topic）为桩——sidecar 的**挂载路径、
      键命中、清单登记、提示注入面**是真实的，决策智能不是；
    - 瓶颈分析强制走确定性 fallback（同 wt190 既有用例惯例）；
    - 回答质量 / 真实规划文案 / 真 LLM 冒烟：留给主会话按 REPORT.md 申报命令跑。

用法（backend/ 下，无需任何在跑服务）::

    SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" \\
        python3.11 -m tests.northstar_eval.sidecar_journey [--out-dir DIR]

证据默认落 /tmp/sidecar_journey/<run_id>/evidence.json（收工自清，不入库）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from app.aurora.runtime_v1.decision_loop import AuroraDecision
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.orchestrator import ChatOrchestrator
from app.orchestration.planning_workflow import PLANNING_SESSION_PREFIX, PlanningWorkflowManager
from app.orchestration.schemas import RouteDecision
from app.orchestration.statechart_engine import WorkflowState

JOURNEY_SCHEMA = "sparkle.sidecar-journey.run.v1"
VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"

TARGET_OPEN_MESSAGE = "7天后考计算机网络，没学过，每天2小时"
DIGRESSION_MESSAGE = "等等，先帮我查一下这个任务完成没有"
RETURN_ADJUST_MESSAGE = "回到规划，把节奏调轻一点"

#: LLM 替身（图桩）的确定性回答——显式声明为桩文本，不代表真实回答质量。
STUB_CHAT_REPLY = "（桩回答）这个任务目前还没完成；先答你这里，稍后我们接着把规划推进下去。"
STRATEGY_REVISION_REPLY = "我按你的反馈把策略收紧了一版，你确认后我就开始生成任务卡。"

MOCK_BOUNDARIES = (
    "通用链回答=图桩确定性文本（LLM 替身），仅验路径与契约，不验回答质量",
    "Aurora decision_loop.decide=桩（soft_return_topic）；sidecar 挂载路径/键命中/manifest 登记为真实路径",
    "bottleneck_analyzer.analyze=强制 RuntimeError → 确定性 fallback（wt190 既有惯例）",
    "网关/PostgreSQL/真实 Redis 不参与：进程内内存桩；鉴权、限流、WS 帧映射不在本旅程覆盖内",
)


class JourneyCheckFailure(AssertionError):
    """旅程断言失败（携带步骤与观测，进 evidence）。"""


class _MemoryRedis:
    """内存 Redis 桩（与 tests/orchestration/test_orchestrator_process_stream_integration
    的 _MemoryRedis 同域同法）：覆盖 process_stream 内部真实触达的操作面。"""

    def __init__(self):
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.values[key] = value
        self.ttls[key] = ttl
        return True

    async def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    async def delete(self, *keys: str):
        removed = 0
        for key in keys:
            if key in self.values:
                removed += 1
                self.values.pop(key, None)
                self.ttls.pop(key, None)
        return removed

    async def keys(self, pattern: str):
        prefix = pattern[:-1] if pattern.endswith("*") else pattern
        return [key for key in self.values if key.startswith(prefix)]

    async def ttl(self, key: str):
        return self.ttls.get(key, -1)

    async def expire(self, key: str, ttl: int):
        if key in self.values:
            self.ttls[key] = ttl
            return True
        return False

    async def ping(self):
        return True


class _Patches:
    """模块属性级补丁（脚本/pytest 两用，退出即还原）。"""

    def __init__(self) -> None:
        self._saved: list[tuple[Any, str, Any]] = []

    def setattr(self, obj: Any, name: str, value: Any) -> None:
        self._saved.append((obj, name, getattr(obj, name, None)))
        setattr(obj, name, value)

    def restore(self) -> None:
        for obj, name, old in reversed(self._saved):
            setattr(obj, name, old)
        self._saved.clear()

    def __enter__(self) -> "_Patches":
        return self

    def __exit__(self, *exc_info) -> None:
        self.restore()


class _RunLedgerStub:
    def __init__(self, *args, **kwargs):
        pass

    async def record_event(self, *args, **kwargs) -> None:
        return None

    def to_metadata_payload(self) -> dict[str, object]:
        return {}


class _ChatSignalCollectorStub:
    def __init__(self, redis_client):
        self.redis_client = redis_client

    async def collect_signals(self, *args, **kwargs) -> None:
        return None


def _build_journey_orchestrator() -> tuple[ChatOrchestrator, _MemoryRedis, dict[str, Any]]:
    """构造引擎直调用编排器：真实 fast-track / sidecar / planning / state 路径 +
    桩化 LLM 图与外围观测。返回 (orchestrator, redis, harness)。"""
    import app.orchestration.orchestrator as orchestrator_module
    import app.orchestration.circuit_breaker as circuit_breaker_module
    from app.aurora.runtime_v1.decision_loop import AuroraDecision as _AuroraDecision

    redis = _MemoryRedis()
    harness: dict[str, Any] = {
        "user_context_by_turn": [],  # 每轮 _build_full_context 产出的 payload（sidecar 挂载面）
        "graph_user_contexts": [],  # 图桩内可见的 state.context_data["user_context"]
        "graph_answers": [],
    }

    class _GraphStub:
        async def invoke(self, state):
            return state

    async def _breaker_initialize(self) -> None:
        return None

    patches = harness.setdefault("_patches", _Patches())
    patches.setattr(orchestrator_module, "create_standard_chat_graph", lambda: _GraphStub())
    patches.setattr(orchestrator_module, "RunLedgerRecorder", _RunLedgerStub)
    patches.setattr(orchestrator_module, "ChatSignalCollector", _ChatSignalCollectorStub)
    patches.setattr(circuit_breaker_module.CircuitBreaker, "initialize", _breaker_initialize)

    orchestrator = orchestrator_module.ChatOrchestrator(db_session=None, redis_client=redis)

    async def passthrough_route(route_decision: RouteDecision, **kwargs) -> RouteDecision:
        return route_decision

    async def emit_noop(*args, **kwargs) -> None:
        return None

    def _capture_user_context(**kwargs):
        # `_build_full_context` 契约：6 元组，[3] 是 user_context_payload。
        # 这里**新建并留存同一对象**——sidecar 随后原地挂载进它，挂载才可观测。
        del kwargs
        payload: dict[str, Any] = {}
        harness["user_context_by_turn"].append(payload)
        return ({}, None, False, payload, {"messages": []}, None)

    async def execute_graph(*, state, queue, result_holder, **kwargs):
        async def _drain():
            while not queue.empty():
                item = await queue.get()
                yield item
                queue.task_done()

        async for item in _drain():
            yield item
        user_context = dict(state.context_data.get("user_context") or {})
        harness["graph_user_contexts"].append(user_context)
        harness["graph_answers"].append(STUB_CHAT_REPLY)
        yield agent_service_pb2.ChatResponse(delta=STUB_CHAT_REPLY)
        result_holder["final_state"] = WorkflowState()

    async def build_final_response(*, session_id, **kwargs):
        return (
            agent_service_pb2.ChatResponse(
                session_id=session_id,
                full_text=STUB_CHAT_REPLY,
                finish_reason=agent_service_pb2.STOP,
            ),
            {"message": STUB_CHAT_REPLY},
        )

    orchestrator._validate_request = AsyncMock(return_value=None)
    orchestrator._check_idempotency_response = AsyncMock(return_value=None)
    orchestrator._acquire_session_lock = AsyncMock(return_value=True)
    orchestrator.state_manager.start_lock_renewal = AsyncMock(return_value=(None, None))
    orchestrator._resolve_active_tools = MagicMock(return_value=[])
    orchestrator._maybe_short_circuit_bridge_tool = AsyncMock(return_value=None)
    orchestrator._build_full_context = AsyncMock(side_effect=_capture_user_context)
    orchestrator._detect_session_feedback = AsyncMock(return_value=(None, None, None))
    orchestrator._apply_cohort_to_session_feedback_signal = MagicMock(side_effect=lambda signal, cohort: signal)
    orchestrator._maybe_enqueue_perceptible_insight = AsyncMock(return_value=None)
    orchestrator._maybe_enqueue_understanding_depth = AsyncMock(return_value=None)
    orchestrator._drain_system_updates = AsyncMock(
        return_value=(
            [],
            [],
            [],
            [],
            None,
            None,
            {
                "proactive_opening_message": "",
                "pending_observation": "",
                "post_adaptation_question": "",
            },
        )
    )
    orchestrator._check_sufficiency = AsyncMock(return_value=(False, "chat"))
    orchestrator._check_goal_quality = AsyncMock(return_value=False)
    orchestrator._load_context_versions = AsyncMock(return_value={})
    orchestrator._prepare_runtime_context = AsyncMock(return_value=(None, emit_noop))
    orchestrator._notify_pending_milestone_proposals = AsyncMock(return_value=None)
    orchestrator._apply_context_focus_overlay = AsyncMock(side_effect=lambda **kwargs: kwargs["user_context_payload"])
    orchestrator._apply_dual_core_routing = AsyncMock(side_effect=passthrough_route)
    orchestrator._emit_roundtable_preview = AsyncMock(return_value=None)
    orchestrator._emit_orchestration_trace = AsyncMock(return_value=None)
    orchestrator._cache_response = AsyncMock(return_value=True)
    orchestrator._cleanup = AsyncMock(return_value=None)
    orchestrator._track_task = MagicMock()
    orchestrator._persist_assistant_message = AsyncMock(return_value=None)
    orchestrator._record_decision = AsyncMock(return_value=None)
    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="direct", reason="simple_chat", risk_level="low"), None)
    )
    orchestrator._plan_and_validate = AsyncMock(
        side_effect=lambda **kwargs: (kwargs["route_decision"], None, None, False)
    )
    orchestrator._execute_graph = execute_graph
    orchestrator._build_final_response = AsyncMock(side_effect=build_final_response)
    orchestrator.grounding_validator.validate_plan = AsyncMock(
        return_value=type("V", (), {"is_valid": True, "warnings": [], "failure_reason": ""})()
    )
    for log_method in (
        "log_route_decision",
        "log_circuit_state_change",
        "log_collaboration_start",
        "log_collaboration_end",
        "log_langgraph_plan",
        "log_validation_failed",
        "log_phase_a_decision",
    ):
        setattr(orchestrator.observability, log_method, AsyncMock(return_value=None))
    orchestrator.shadow_predictor.predict_and_record = AsyncMock(return_value=None)

    # Aurora 决策内容桩：sidecar 挂载路径本身是真实路径（见 MOCK_BOUNDARIES）。
    async def fake_decide(readout):
        return _AuroraDecision(
            action="soft_return_topic",
            chat_directive={
                "intent": "recover_planning_naturally",
                "brief": "Answer the current task first, then recover planning naturally.",
            },
        )

    orchestrator.aurora_runtime_v1.decision_loop.decide = fake_decide

    # 瓶颈分析强制确定性 fallback（与 wt190 既有用例同款；脚本模式手动补丁）。
    from app.orchestration import bottleneck_analyzer as bottleneck_module

    patches.setattr(
        bottleneck_module.bottleneck_analyzer,
        "analyze",
        AsyncMock(side_effect=RuntimeError("journey: force deterministic fallback")),
    )
    # 决策桩为实例属性，随实例丢弃，无需还原；模块级补丁由调用方 finally 还原。
    return orchestrator, redis, harness


def _content_frames(responses: list) -> list:
    return [response for response in responses if response.full_text]


def _sidecar_in(payload: Any) -> bool:
    return isinstance(payload, dict) and isinstance(payload.get("aurora_planning_sidecar"), dict)


def _planning_keys(redis: _MemoryRedis, user_id: str, session_id: str) -> dict[str, bool]:
    scoped = f"{PLANNING_SESSION_PREFIX.format(user_id=f'{user_id}:')}{session_id}"
    unscoped = f"{PLANNING_SESSION_PREFIX.format(user_id='')}{session_id}"
    return {"user_scoped_hit": scoped in redis.values, "unscoped_exists": unscoped in redis.values}


async def _run_turn(orchestrator: ChatOrchestrator, *, user_id: str, session_id: str, message: str) -> list:
    request = agent_service_pb2.ChatRequest(
        request_id=f"req-{uuid.uuid4()}",
        session_id=session_id,
        user_id=user_id,
        message=message,
    )
    return [response async for response in orchestrator.process_stream(request)]


def _check(condition: bool, step: str, detail: str, observations: dict[str, Any]) -> None:
    if not condition:
        raise JourneyCheckFailure(f"[{step}] {detail} | observations={json.dumps(observations, ensure_ascii=False, default=str)}")


async def run_journey(out_dir: str | Path | None = None) -> dict[str, Any]:
    """跑三轮最小旅程并就地断言；返回汇总证据（可 JSON 落盘）。"""
    run_id = f"sidecar-journey-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"
    orchestrator, redis, harness = _build_journey_orchestrator()
    patches: _Patches = harness["_patches"]
    manager: PlanningWorkflowManager = orchestrator.planning_workflow_manager
    user_id = str(uuid.uuid4())
    session_id = f"journey-{uuid.uuid4()}"
    steps: list[dict[str, Any]] = []

    try:
        return await _run_journey_steps(run_id, orchestrator, redis, harness, manager, user_id, session_id, steps, out_dir)
    finally:
        patches.restore()


async def _run_journey_steps(
    run_id: str,
    orchestrator: ChatOrchestrator,
    redis: _MemoryRedis,
    harness: dict[str, Any],
    manager: PlanningWorkflowManager,
    user_id: str,
    session_id: str,
    steps: list[dict[str, Any]],
    out_dir: str | Path | None,
) -> dict[str, Any]:

    try:
        # ---- T1 target_open：Day0 建 target（fast-track 冲刺开场） ----
        t1 = await _run_turn(orchestrator, user_id=user_id, session_id=session_id, message=TARGET_OPEN_MESSAGE)
        t1_content = _content_frames(t1)
        t1_keys = _planning_keys(redis, user_id, session_id)
        session1 = await manager.get_active_session(session_id, user_id)
        t1_obs = {
            "frames": len(t1),
            "content_frames": len(t1_content),
            "fast_track_metadata": (t1_content[-1].metadata.get("planning_fast_track") if t1_content else None),
            "planning_state": session1.state if session1 else None,
            "sprint_pack_id": (session1.collected.get("sprint_pack_id") if session1 else None),
            "keys": t1_keys,
            "sidecar_mounts": sum(1 for ctx in harness["user_context_by_turn"] if _sidecar_in(ctx)),
        }
        _check(bool(t1_content), "T1", "fast-track 必须产出内容帧", t1_obs)
        _check(t1_obs["fast_track_metadata"] == "exam_sprint", "T1", "T1 应由 fast-track 处理", t1_obs)
        _check(session1 is not None and session1.state == "PLANNING", "T1", "规划会话应直达 PLANNING", t1_obs)
        _check(t1_obs["sprint_pack_id"] == "computer_networks@v1", "T1", "Sprint Pack 预填应命中", t1_obs)
        _check(t1_keys["user_scoped_hit"] and not t1_keys["unscoped_exists"], "T1", "会话键必须 user 域命中", t1_obs)
        _check(t1_obs["sidecar_mounts"] == 0, "T1", "T1 不应挂 sidecar", t1_obs)
        steps.append({"step_id": "T1", "name": "target_open", "message": TARGET_OPEN_MESSAGE, "verdict": VERDICT_PASS, "observations": t1_obs})
        opening_text = t1_content[-1].full_text

        # ---- T2 digression：规划离题 → sidecar 恰挂载一次 + 通用链作答 ----
        t2 = await _run_turn(orchestrator, user_id=user_id, session_id=session_id, message=DIGRESSION_MESSAGE)
        t2_content = _content_frames(t2)
        graph_ctx = harness["graph_user_contexts"][-1] if harness["graph_user_contexts"] else {}
        t2_sidecar_mounts = sum(1 for ctx in harness["user_context_by_turn"] if _sidecar_in(ctx))
        t2_obs = {
            "content_frames": len(t2_content),
            "answer": t2_content[-1].full_text if t2_content else None,
            "answer_is_stub": bool(t2_content) and t2_content[-1].full_text == STUB_CHAT_REPLY,
            "answer_repeats_opening": bool(t2_content) and t2_content[-1].full_text == opening_text,
            "fast_track_metadata": (t2_content[-1].metadata.get("planning_fast_track") if t2_content else None),
            "graph_sidecar_visible": _sidecar_in(graph_ctx),
            "sidecar_action": ((graph_ctx.get("aurora_planning_sidecar") or {}).get("decision", {}).get("action") if _sidecar_in(graph_ctx) else None),
            "sidecar_mounts_total": t2_sidecar_mounts,
        }
        session2 = await manager.get_active_session(session_id, user_id)
        t2_obs["planning_session_id_unchanged"] = bool(session2) and session2.planning_session_id == session1.planning_session_id
        _check(bool(t2_content), "T2", "离题轮必须有回答", t2_obs)
        _check(not t2_obs["answer_repeats_opening"], "T2", "A1：第二轮不得重复开场白", t2_obs)
        _check(t2_obs["fast_track_metadata"] is None, "T2", "A1：离题轮不得再次走 fast-track 开场", t2_obs)
        _check(t2_obs["graph_sidecar_visible"] and t2_obs["sidecar_action"] == "soft_return_topic", "T2", "A2：sidecar 应在本轮挂载且决策为 soft_return_topic", t2_obs)
        _check(t2_sidecar_mounts == 1, "T2", "A2：sidecar 全旅程恰挂载一次", t2_obs)
        _check(t2_obs["planning_session_id_unchanged"], "T2", "离题不得换会话", t2_obs)
        steps.append({"step_id": "T2", "name": "digression", "message": DIGRESSION_MESSAGE, "verdict": VERDICT_PASS, "observations": t2_obs})

        # ---- T3 return：回归提问 → fast-track 续聊（策略修订），不重新开场 ----
        t3 = await _run_turn(orchestrator, user_id=user_id, session_id=session_id, message=RETURN_ADJUST_MESSAGE)
        t3_content = _content_frames(t3)
        t3_obs = {
            "content_frames": len(t3_content),
            "answer": t3_content[-1].full_text if t3_content else None,
            "fast_track_metadata": (t3_content[-1].metadata.get("planning_fast_track") if t3_content else None),
            "sidecar_mounts_total": sum(1 for ctx in harness["user_context_by_turn"] if _sidecar_in(ctx)),
        }
        session3 = await manager.get_active_session(session_id, user_id)
        t3_obs.update(
            {
                "planning_session_id_unchanged": bool(session3) and session3.planning_session_id == session1.planning_session_id,
                "planning_state": session3.state if session3 else None,
                "keys": _planning_keys(redis, user_id, session_id),
            }
        )
        _check(bool(t3_content), "T3", "回归轮必须有回答", t3_obs)
        _check(t3_obs["answer"] == STRATEGY_REVISION_REPLY, "T3", "A3：回归提问应得到策略修订回复（续聊命中同一会话）", t3_obs)
        _check(t3_obs["answer"] != opening_text, "T3", "A1：回归续聊不得重新开场", t3_obs)
        _check(t3_obs["fast_track_metadata"] == "exam_sprint", "T3", "T3 应由 fast-track 续聊分支处理", t3_obs)
        _check(t3_obs["planning_session_id_unchanged"], "T3", "续聊必须命中同一 planning_session_id", t3_obs)
        _check(t3_obs["planning_state"] == "AWAITING_CONFIRM", "T3", "策略修订后会话应进入 AWAITING_CONFIRM", t3_obs)
        _check(t3_obs["sidecar_mounts_total"] == 1, "T3", "A2：回归轮不应再挂 sidecar（总计仍为 1）", t3_obs)
        _check(t3_obs["keys"]["user_scoped_hit"] and not t3_obs["keys"]["unscoped_exists"], "T3", "全旅程只有 user 域会话键", t3_obs)
        steps.append({"step_id": "T3", "name": "return", "message": RETURN_ADJUST_MESSAGE, "verdict": VERDICT_PASS, "observations": t3_obs})
    except JourneyCheckFailure as failure:
        steps.append(
            {
                "step_id": "FAILURE",
                "name": "journey_check",
                "verdict": VERDICT_FAIL,
                "observations": {"error": str(failure)},
            }
        )
        summary = {
            "schema": JOURNEY_SCHEMA,
            "run_id": run_id,
            "verdict": VERDICT_FAIL,
            "user_id_sha": uuid.uuid5(uuid.NAMESPACE_URL, user_id).hex[:12],
            "session_id": session_id,
            "steps": steps,
            "mock_boundaries": list(MOCK_BOUNDARIES),
            "finished_at": datetime.now(UTC).isoformat(),
        }
        _write_evidence(summary, out_dir)
        return summary

    summary = {
        "schema": JOURNEY_SCHEMA,
        "run_id": run_id,
        "verdict": VERDICT_PASS,
        "user_id_sha": uuid.uuid5(uuid.NAMESPACE_URL, user_id).hex[:12],
        "session_id": session_id,
        "assertion_points": {
            "A1_no_reopening_on_second_turn": True,
            "A2_sidecar_mounted_exactly_once": True,
            "A3_return_question_answered_and_session_continued": True,
        },
        "steps": steps,
        "mock_boundaries": list(MOCK_BOUNDARIES),
        "finished_at": datetime.now(UTC).isoformat(),
    }
    _write_evidence(summary, out_dir)
    return summary


def _write_evidence(summary: dict[str, Any], out_dir: str | Path | None) -> None:
    target = Path(out_dir) if out_dir else Path("/tmp/sidecar_journey") / summary["run_id"]
    try:
        target.mkdir(parents=True, exist_ok=True)
        (target / "evidence.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        summary["evidence_path"] = str(target / "evidence.json")
    except OSError as exc:  # 证据落盘失败不改变旅程结论，仅标注
        summary["evidence_path"] = None
        print(f"[sidecar_journey] evidence write failed: {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SIDECAR-JOURNEY 三轮最小旅程（引擎直调，全桩化）")
    parser.add_argument("--out-dir", default=None, help="证据目录（默认 /tmp/sidecar_journey/<run_id>）")
    args = parser.parse_args(argv)
    summary = asyncio.run(run_journey(out_dir=args.out_dir))
    print(json.dumps({key: summary[key] for key in ("schema", "run_id", "verdict", "assertion_points", "evidence_path") if key in summary}, ensure_ascii=False, indent=2))
    return 0 if summary["verdict"] == VERDICT_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
