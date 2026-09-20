"""O-02 查询脚本正确性：样例日志 → 正确时间线/汇总；变异敏感。

脚本以 importlib 从 scripts/devtools 加载（仓库既有模式，
见 test_rebuild_embedding_index_n3.py）；纯文件解析、无网络无服务。
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "devtools" / "trace_timeline.py"

_TRACE = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
_TRACE_OTHER = "ffffffffffffffffffffffffffffffff"
_TRACE_SPINE_MARKER = "TRACE_SPINE"


def _load_script():
    spec = importlib.util.spec_from_file_location("trace_timeline_script", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _spine_json(**payload) -> str:
    base = {"marker": _TRACE_SPINE_MARKER, "ts": 1758400000.0, "status": "ok", "trace_id": _TRACE}
    base.update(payload)
    return json.dumps(base, ensure_ascii=False)


def _spine_message(**payload) -> str:
    """引擎现行发射格式：``TRACE_SPINE {json}``（前缀锚点 + marker 校验位）。"""
    return f"{_TRACE_SPINE_MARKER} {_spine_json(**payload)}"


TRACE_SPINE_JSON_ENTRY = _spine_json(stage="orchestrator_entry", duration_ms=5.0, tags={"chat_mode": "standard"})
TRACE_SPINE_JSON_CONTEXT = _spine_json(stage="context_build", duration_ms=850.0, tags={"elapsed_ms": 855.0})
TRACE_SPINE_JSON_AURORA = _spine_json(stage="aurora_turn", duration_ms=400.0, tags={"causal_trace_id": "ct_777", "energy_level": "L1"})
TRACE_SPINE_JSON_LLM = _spine_json(
    stage="llm_call",
    duration_ms=1200.0,
    tags={"model": "deepseek_chat", "prompt_tokens": 600, "completion_tokens": 330, "total_tokens": 930, "cost_usd": 0.000186},
)
TRACE_SPINE_JSON_FINISH = _spine_json(stage="finish", duration_ms=4000.0, tags={"stage_count": 4})
TRACE_SPINE_JSON_OTHER = _spine_json(stage="llm_call", trace_id=_TRACE_OTHER, duration_ms=1.0, tags={"model": "other"})

TRACE_SPINE_MESSAGE_ENTRY = _spine_message(stage="orchestrator_entry", duration_ms=5.0, tags={"chat_mode": "standard"})
TRACE_SPINE_MESSAGE_CONTEXT = _spine_message(stage="context_build", duration_ms=850.0, tags={"elapsed_ms": 855.0})
TRACE_SPINE_MESSAGE_AURORA = _spine_message(stage="aurora_turn", duration_ms=400.0, tags={"causal_trace_id": "ct_777", "energy_level": "L1"})
TRACE_SPINE_MESSAGE_LLM = _spine_message(
    stage="llm_call",
    duration_ms=1200.0,
    tags={"model": "deepseek_chat", "prompt_tokens": 600, "completion_tokens": 330, "total_tokens": 930, "cost_usd": 0.000186},
)
TRACE_SPINE_MESSAGE_FINISH = _spine_message(stage="finish", duration_ms=4000.0, tags={"stage_count": 4})

_SAMPLE_LOG = "\n".join(
    [
        # 另一条 trace（噪声，验证过滤）
        f"2026-09-21 10:00:00.000 | INFO | app.core.trace_spine: {TRACE_SPINE_JSON_OTHER}",
        # gRPC 入口锚点
        f"2026-09-21 10:00:01.000 | INFO | app.services.agent_grpc_service: StreamChat started - "
        f"user_id=01234567-89ab-cdef-0123-456789abcdef, session=sess_1, trace={_TRACE}, "
        f"chat_mode=standard, workflow=standard_chat, prompt_version=v1",
        # spine spans（引擎现行前缀格式）
        f"2026-09-21 10:00:01.100 | INFO | app.core.trace_spine: {TRACE_SPINE_MESSAGE_ENTRY}",
        f"2026-09-21 10:00:02.000 | INFO | app.core.trace_spine: {TRACE_SPINE_MESSAGE_CONTEXT}",
        f"2026-09-21 10:00:02.500 | INFO | app.core.trace_spine: {TRACE_SPINE_MESSAGE_AURORA}",
        f"2026-09-21 10:00:03.000 | INFO | app.core.trace_spine: {TRACE_SPINE_MESSAGE_LLM}",
        # funnel 行（带 trace=）
        f"2026-09-21 10:00:03.100 | INFO | app.agents.standard_workflow: C-08 context funnel req_f1 "
        f"trace={_TRACE} episodic=3/2/1i/120t refs=4 alignment=aligned bloat=- inert=0 cited=2 faithful=True consistent=True",
        # [LATENCY] 行
        f"2026-09-21 10:00:04.000 | INFO | app.orchestration.latency_probe: [LATENCY] session=sess_1 "
        f"request=req_f1 trace={_TRACE} total=3000ms first_stream_content=2100ms hops: build_full_context=900ms",
# loguru serialize=True JSON 载体（生产格式，内含前缀格式消息）
json.dumps(
    {
        "text": (
            f"2026-09-21 10:00:04.500 | INFO | app.core.trace_spine: {TRACE_SPINE_MESSAGE_FINISH}"
        ),
        "record": {"level": {"name": "INFO"}},
    },
    ensure_ascii=False,
),
        # 无前缀的裸 JSON 行（旧格式容忍）
        f"2026-09-21 10:00:04.700 | INFO | app.core.trace_spine: {TRACE_SPINE_JSON_OTHER}",
        # 出口锚点
        f"2026-09-21 10:00:05.000 | INFO | app.services.agent_grpc_service: StreamChat completed for trace={_TRACE}",
    ]
)


def test_parse_line_extracts_all_record_kinds(tmp_path):
    module = _load_script()
    log_file = tmp_path / "engine.log"
    log_file.write_text(_SAMPLE_LOG, encoding="utf-8")

    records = module.collect_records([str(log_file)])
    kinds = {record["kind"] for record in records}
    assert {"span", "entry", "exit", "latency", "funnel"} <= kinds
    # 序列化 JSON 载体里的 finish span 也要被解出
    finish = [r for r in records if r["kind"] == "span" and r["stage"] == "finish"]
    assert finish and finish[0]["trace_id"] == _TRACE


def test_build_timeline_summary_correct(tmp_path):
    module = _load_script()
    log_file = tmp_path / "engine.log"
    log_file.write_text(_SAMPLE_LOG, encoding="utf-8")
    records = module.collect_records([str(log_file)])
    module.link_request_ids(records)

    timeline = module.build_timeline(records, _TRACE)
    summary = timeline["summary"]

    # 阶段有序完整（entry → context → aurora → llm → finish）
    stages = [s["stage"] for s in timeline["stages"]]
    assert stages == ["orchestrator_entry", "context_build", "aurora_turn", "llm_call", "finish"]
    # actual model / cost / token 关联
    assert summary["actual_models"] == ["deepseek_chat"]
    assert math.isclose(summary["llm_total_cost_usd"], 0.000186, abs_tol=1e-9)
    assert summary["llm_total_tokens"] == 930
    assert summary["llm_total_latency_ms"] == 1200.0
    # chain latency 关联（[LATENCY] 行）
    assert summary["chain_latency_total_ms"] == 3000.0
    # receipt/causal 关联
    assert summary["causal_trace_ids"] == ["ct_777"]
    # funnel 记录被聚合
    assert summary["funnel_records"] == 1
    # entry/exit 锚点
    assert summary["has_entry"] and summary["has_exit"]
    # 噪声 trace 未混入
    assert all(s["trace_id"] == _TRACE for s in timeline["stages"])


def test_pick_default_trace_prefers_densest(tmp_path):
    module = _load_script()
    log_file = tmp_path / "engine.log"
    log_file.write_text(_SAMPLE_LOG, encoding="utf-8")
    records = module.collect_records([str(log_file)])
    assert module.pick_default_trace(records) == _TRACE


def test_format_timeline_human_readable(tmp_path):
    module = _load_script()
    log_file = tmp_path / "engine.log"
    log_file.write_text(_SAMPLE_LOG, encoding="utf-8")
    records = module.collect_records([str(log_file)])
    timeline = module.build_timeline(records, _TRACE)
    rendered = module.format_timeline(timeline)
    assert f"trace_id = {_TRACE}" in rendered
    assert "deepseek_chat" in rendered
    assert "causal_trace_ids=ct_777" in rendered
    assert "llm_call" in rendered


def test_parse_line_ignores_plain_content_lines():
    module = _load_script()
    records = module.parse_line("2026-09-21 10:00:00 | INFO | app: 用户消息正文原样出现在日志里")
    assert records == []
