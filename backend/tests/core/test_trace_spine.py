"""O-02 trace spine 单测：合成链路 + PII/Memory 正文零泄漏 + 关键接线面。

覆盖：
1. ``sanitize_tags`` 红线：正文/结构体只能以 长度+短哈希 指纹出现；
2. 合成链路（entry→context→aurora→llm→run→outcome，mock 各层）：全链同一个
   trace_id、阶段有序、actual model/cost 可关联；
3. C-08 funnel 记录挂 trace_id 且正文零泄漏；
4. 接线面存在性（变异检测锚点）：网关 trace_id 贯穿 / llm_call span /
   funnel trace 传入；
5. LatencyProbe [LATENCY] 行携带 trace=。

真实 LLM 0 次；无网络、无服务。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from loguru import logger

from app.core.trace_spine import (
    TRACE_SPINE_MARKER,
    SpineRecorder,
    bind_spine,
    current_trace_id,
    emit_span,
    fingerprint,
    sanitize_tags,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# loguru 捕获夹具
# ---------------------------------------------------------------------------


class _LogCapture:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self._sink_id = None

    def start(self) -> None:
        self._sink_id = logger.add(self._write, level="INFO")

    def stop(self) -> None:
        if self._sink_id is not None:
            logger.remove(self._sink_id)
            self._sink_id = None

    def _write(self, message) -> None:  # noqa: ANN001 - loguru sink 协议
        self.lines.append(str(message))

    def spine_payloads(self) -> list[dict]:
        payloads = []
        for line in self.lines:
            start = line.find("{")
            end = line.rfind("}")
            if start < 0 or end <= start:
                continue
            try:
                payload = json.loads(line[start : end + 1])
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(payload, dict) and payload.get("marker") == TRACE_SPINE_MARKER:
                payloads.append(payload)
        return payloads


@pytest.fixture()
def capture():
    cap = _LogCapture()
    cap.start()
    try:
        yield cap
    finally:
        cap.stop()


# ---------------------------------------------------------------------------
# 1. sanitize_tags / 红线
# ---------------------------------------------------------------------------


def test_sanitize_tags_redacts_content_bodies():
    long_message = (
        "我上周日在西湖边背完了整套高数公式，感觉线性代数还是不行，"
        "打算这周把错题本重做一遍再找助教答疑，另外英语单词也欠了两周的量没背"
    )
    short_label = "deepseek_chat"
    tags = sanitize_tags(
        {
            "model": short_label,
            "cost_usd": 0.0012,
            "ok": True,
            "note": long_message,
            "payload": {"inner": long_message},
            "items": [1, 2, 3],
            "none_value": None,
        }
    )
    assert tags["model"] == short_label
    assert tags["cost_usd"] == 0.0012
    assert tags["ok"] is True
    assert "none_value" not in tags
    # 长文本（>48 字符）：一律指纹化，正文不可还原
    note = str(tags["note"])
    assert note.startswith("<len=") and ",hash=" in note and note.endswith(">")
    assert long_message not in note
    assert "错题本" not in note
    # 结构体：同样只允许 指纹
    for key in ("payload", "items"):
        value = str(tags[key])
        assert value.startswith("<len=") and ",hash=" in value and value.endswith(">")
        assert long_message not in value


def test_fingerprint_matches_c08_content_fingerprint():
    from app.orchestration.context_funnel import content_fingerprint

    text = "golden journey receipt body"
    assert fingerprint(text) == content_fingerprint(text)


def test_emit_span_is_single_line_json(capture):
    emit_span("llm_call", trace_id="abc123", duration_ms=12.5, tags={"model": "glm", "cost_usd": 0.5})
    payloads = capture.spine_payloads()
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["trace_id"] == "abc123"
    assert payload["stage"] == "llm_call"
    assert payload["duration_ms"] == 12.5
    assert payload["tags"]["model"] == "glm"


def test_emit_span_never_raises_on_bad_input(capture):
    emit_span("x", trace_id=object(), tags={"bad": object()})  # type: ignore[arg-type]
    assert isinstance(capture.spine_payloads(), list)


# ---------------------------------------------------------------------------
# 2. 合成链路（mock 各层）：trace_id 从入口到 outcome 不丢
# ---------------------------------------------------------------------------


def test_synthetic_chain_trace_id_end_to_end(capture):
    """UI→Gateway→Context→Aurora→LLM→Run→Outcome 合成链。

    gateway 传入 trace_id → SpineRecorder 绑定 → 各层 step →
    graph 独立 task 场景（无 recorder）走 emit_span + 显式 trace_id 兜底。
    """
    gateway_trace_id = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
    recorder = SpineRecorder(
        trace_id=gateway_trace_id, request_id="req_x", session_id="sess_x", user_id="user-abcdef42"
    )
    with bind_spine(recorder):
        assert current_trace_id() == gateway_trace_id
        recorder.step("orchestrator_entry", chat_mode="standard", workflow_id="standard_chat")
        recorder.step("context_build")
        recorder.step("aurora_turn", causal_trace_id="ct_001", energy_level="L1")
        recorder.step("route_decision", intent="qa", execution_mode="fast")
        # graph worker task：contextvar 不可达 → 数据面（user_context.trace_id）兜底
        recorder_unbound = current_trace_id()
        assert recorder_unbound == gateway_trace_id  # 同 task 内绑定仍在
        emit_span(
            "llm_call",
            trace_id=gateway_trace_id,
            duration_ms=810.0,
            tags={"model": "deepseek_chat", "total_tokens": 930, "cost_usd": 0.0002},
        )
        emit_span(
            "run_execute",
            trace_id=gateway_trace_id,
            duration_ms=40.0,
            tags={"run_id": "run_9", "trace_id": gateway_trace_id},
        )
        recorder.step("outcome_link", causal_trace_id="ct_001")
        recorder.finish()

    payloads = capture.spine_payloads()
    assert len(payloads) == 8
    # 全链同一个 trace_id
    assert all(p["trace_id"] == gateway_trace_id for p in payloads)
    # 阶段有序且关键阶段齐全
    stages = [p["stage"] for p in payloads]
    assert stages == [
        "orchestrator_entry",
        "context_build",
        "aurora_turn",
        "route_decision",
        "llm_call",
        "run_execute",
        "outcome_link",
        "finish",
    ]
    # actual model / cost / receipt 关联可查
    llm_span = next(p for p in payloads if p["stage"] == "llm_call")
    assert llm_span["tags"]["model"] == "deepseek_chat"
    assert llm_span["tags"]["cost_usd"] == 0.0002
    aurora = next(p for p in payloads if p["stage"] == "aurora_turn")
    assert aurora["tags"]["causal_trace_id"] == "ct_001"
    # PII：user_id 只剩 8 位前缀
    assert all(p["tags"]["user_hint"] == "user-abc" for p in payloads if "user_hint" in p.get("tags", {}))


def test_spine_step_duration_monotonic(capture):
    import time

    recorder = SpineRecorder(trace_id="t" * 32)
    recorder.step("a")
    time.sleep(0.01)
    recorder.step("b")
    payloads = capture.spine_payloads()
    assert payloads[1]["duration_ms"] >= payloads[0]["duration_ms"]


def test_spine_error_status_propagates(capture):
    recorder = SpineRecorder(trace_id="e" * 32)
    recorder.finish(status="error", error_type="ValueError")
    recorder.step("after_fail")
    payloads = capture.spine_payloads()
    assert payloads[0]["status"] == "error"
    assert payloads[1]["status"] == "after_error"


# ---------------------------------------------------------------------------
# 3. funnel 挂 trace_id + 正文零泄漏
# ---------------------------------------------------------------------------


def test_funnel_record_carries_trace_id_and_no_content_leak():
    from app.orchestration.context_funnel import (
        build_context_funnel_record,
        find_content_leak,
        funnel_log_line,
    )

    memory_body = "用户提到他对排列组合的错题本已经三周没复习了，焦虑情绪明显"
    record = build_context_funnel_record(
        request_id="req_f1",
        trace_id="f" * 32,
        memory_refs=[{"kind": "episodic", "ref": "mem:42", "tokens": 12, "content_len": len(memory_body)}],
    )
    assert record["trace_id"] == "f" * 32
    log_line = funnel_log_line(record)
    assert "trace=" + "f" * 32 in log_line
    assert find_content_leak(record, [memory_body]) == []


# ---------------------------------------------------------------------------
# 4. 接线面（变异检测锚点）：关键 wire 必须存在
# ---------------------------------------------------------------------------


def _read(relative: str) -> str:
    return (_BACKEND_ROOT / relative).read_text(encoding="utf-8")


def test_wiring_gateway_trace_id_preferred_in_process_stream():
    src = _read("app/orchestration/orchestrator.py")
    assert 'context_data or {}).get("trace_id"' in src, "process_stream 必须优先采用网关 trace_id"
    assert 'span.set_attribute("sparkle.trace_id", trace_id)' in src
    assert "state.context_data[\"trace_id\"] = trace_id" in src, "trace_id 必须随 state 数据面传播"
    assert 'user_context_payload["trace_id"] = trace_id' in src, "trace_id 必须随 user_context 传入 LLM 层"


def test_wiring_grpc_service_passes_trace_id():
    src = _read("app/services/agent_grpc_service.py")
    assert '"trace_id": trace_id' in src, "gRPC service 必须把网关 trace_id 传给 process_stream"


def test_wiring_llm_service_emits_llm_call_span():
    src = _read("app/services/llm_service.py")
    assert '"llm_call"' in src
    assert "record_llm_cost" in src
    assert "cost_usd" in src
    assert "sparkle.trace_id" in src
    # 发射必须真实接线：主路径走 recorder，兜底走显式 emit_span。
    assert "_spine = current_recorder()" in src, "llm_call span 主发射路径缺失"
    assert "emit_span(" in src, "llm_call span 兜底发射路径缺失"


def test_wiring_workflow_passes_trace_id_to_funnel():
    src = _read("app/agents/standard_workflow.py")
    assert "trace_id=str(state.context_data.get(\"trace_id\") or\")" in src.replace("\"\n            or\"", "\" or\"") or (
        'state.context_data.get("trace_id")' in src
    ), "standard_workflow 必须把 state 的 trace_id 传给 funnel 记录"


def test_wiring_finish_span_emitted_in_finally():
    """验收员补锚点（R2 变异 M3 盲区）：process_stream 正常/异常路径都必须
    发射 finish 收尾 span（否则每条 trace 时间线无终点、stage_count 缺失）。"""
    src = _read("app/orchestration/orchestrator.py")
    assert "spine.finish(" in src, "process_stream finally 必须发射 spine.finish 收尾 span"
    for stage in ("orchestrator_entry", "graph_execute", "final_compose", "aurora_turn", "route_decision", "plan_validate"):
        assert f'"{stage}"' in src, f"{stage} span 落点缺失"


# ---------------------------------------------------------------------------
# 5. LatencyProbe trace 关联
# ---------------------------------------------------------------------------


def test_latency_probe_line_contains_trace(capture):
    from app.orchestration.latency_probe import LatencyProbe

    probe = LatencyProbe(session_id="s1", request_id="r1", trace_id="b" * 32)
    probe.mark("hop_a")
    probe.finish()
    latency_lines = [line for line in capture.lines if "[LATENCY]" in line]
    assert latency_lines, "LatencyProbe 必须输出 [LATENCY] 行"
    assert f"trace={'b' * 32}" in latency_lines[0]


# ---------------------------------------------------------------------------
# 6. run 侧 trace_id 落列（既有契约不回归）
# ---------------------------------------------------------------------------


def test_agent_run_model_still_has_trace_id_column():
    from app.models.agent_run import AgentRun

    assert hasattr(AgentRun, "trace_id"), "AgentRun.trace_id 列是 run↔trace 关联面，不得移除"
