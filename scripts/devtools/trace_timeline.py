#!/usr/bin/env python3
"""O-02 查询脚本：按 trace_id 还原一次请求的全链时间线。

从引擎日志（loguru 纯文本或 serialize=True 的 JSON 记录）中聚合：
- ``TRACE_SPINE {...}`` 单行 JSON span（阶段/时长/actual model/token/cost/
  causal_trace_id 关联）——由 ``app/core/trace_spine.py`` 发射；
- ``[LATENCY] session=... request=... trace=...`` 分段耗时行；
- ``StreamChat started/completed``（gRPC 入口/出口锚点）；
- ``C-08 context funnel``（context 关联面：items/tokens/refs/bloat）。

用法::

    python3 scripts/devtools/trace_timeline.py <logfile> [more.log ...] \
        [--trace-id <id>] [--json] [--redis-url redis://localhost:6379/0]

- 不传 ``--trace-id`` 时自动选日志中出现 span 最多的 trace_id。
- ``--redis-url`` 可选：用 causal_trace_id 拉 ``spine:trace:<id>`` 的
  outcome/receipt 关联（缺 Redis 时跳过，时间线仍然完整）。

只读工具；正文零输出——span 本身不含正文，本脚本也不做任何内容解码。
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict
from typing import Any

TRACE_SPINE_MARKER = "TRACE_SPINE"

# 预编译匹配器：(名称, 正则)。全部针对单行，捕获 trace 锚点与关键标量。
_LATENCY_RE = re.compile(
    r"\[LATENCY\]\s+session=(?P<session>\S+)\s+request=(?P<request>\S+)"
    r"(?:\s+trace=(?P<trace>[^\s,]+))?\s+total=(?P<total>\d+)ms"
)
_STREAMCHAT_STARTED_RE = re.compile(
    r"StreamChat started\s+-\s+user_id=(?P<user>[^\s,]+),\s+session=(?P<session>\S+),\s+trace=(?P<trace>[^\s,]+)"
)
_STREAMCHAT_DONE_RE = re.compile(r"StreamChat completed for trace=(?P<trace>[^\s,]+)")
_FUNNEL_RE = re.compile(
    r"C-08 context funnel(?:\s+(?P<request>\S+))?(?:\s+trace=(?P<trace>[^\s,]+))?"
    r"(?P<surfaces>(?:\s+\w+=\d+i/\d+t)*)"
)
_ORCHESTRATION_ERROR_RE = re.compile(r"Orchestration Error")

# 时间戳前缀（loguru 默认格式 | 序列化格式两种都容忍）
_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)")


def _now_epoch(text_line: str) -> float:
    """尽力从行首提取时间戳；失败返回 0.0（保序降级）。"""
    import datetime as _dt

    match = _TS_RE.match(text_line)
    if not match:
        return 0.0
    raw = match.group(1).replace(" ", "T")
    try:
        return _dt.datetime.fromisoformat(raw).timestamp()
    except ValueError:
        return 0.0


def parse_spine_span(line: str) -> dict[str, Any] | None:
    """从一行日志解析 TRACE_SPINE span JSON；非 span 行返回 None。

    兼容三种载体：
    - 引擎现行格式：``... TRACE_SPINE {...}``（前缀锚点）；
    - 仅有 JSON 的行：``... {"marker": "TRACE_SPINE", ...}``；
    - loguru 序列化 JSON：``{"text": "... TRACE_SPINE {...}", ...}``。

    策略：先取首个 ``{`` 到末个 ``}`` 的整段尝试解析（消息恰为单 JSON
    对象）；marker 字段必须等于 ``TRACE_SPINE`` 才认定成立。
    """
    candidate = line
    if line.lstrip().startswith("{"):
        try:
            outer = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            outer = None
        if isinstance(outer, dict) and isinstance(outer.get("text"), str):
            candidate = outer["text"]
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(candidate[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("marker") != TRACE_SPINE_MARKER:
        return None
    return payload


def parse_line(line: str) -> list[dict[str, Any]]:
    """一行日志 → 0..n 条记录（span / latency / 锚点 / funnel）。"""
    records: list[dict[str, Any]] = []
    span = parse_spine_span(line)
    if span is not None:
        records.append(
            {
                "kind": "span",
                "ts": float(span.get("ts") or 0.0),
                "trace_id": str(span.get("trace_id") or ""),
                "stage": str(span.get("stage") or "unknown"),
                "status": str(span.get("status") or "ok"),
                "duration_ms": span.get("duration_ms"),
                "tags": dict(span.get("tags") or {}),
            }
        )
        return records

    match = _LATENCY_RE.search(line)
    if match:
        trace = match.group("trace") or ""
        if trace:
            records.append(
                {
                    "kind": "latency",
                    "ts": _now_epoch(line),
                    "trace_id": trace,
                    "session": match.group("session"),
                    "request": match.group("request"),
                    "total_ms": float(match.group("total")),
                }
            )
            return records

    match = _STREAMCHAT_STARTED_RE.search(line)
    if match:
        records.append(
            {
                "kind": "entry",
                "ts": _now_epoch(line),
                "trace_id": match.group("trace"),
                "session": match.group("session"),
                "user_hint": match.group("user")[:8],
            }
        )
        return records

    match = _STREAMCHAT_DONE_RE.search(line)
    if match:
        records.append(
            {
                "kind": "exit",
                "ts": _now_epoch(line),
                "trace_id": match.group("trace"),
            }
        )
        return records

    match = _FUNNEL_RE.search(line)
    if match and (match.group("trace") or match.group("request")):
        records.append(
            {
                "kind": "funnel",
                "ts": _now_epoch(line),
                "trace_id": match.group("trace") or "",
                "request_id": match.group("request") or "",
                "surfaces": match.group("surfaces").strip(),
            }
        )
        return records

    if _ORCHESTRATION_ERROR_RE.search(line):
        records.append({"kind": "error_marker", "ts": _now_epoch(line), "trace_id": ""})
    return records


def collect_records(sources: list[str]) -> list[dict[str, Any]]:
    """展开文件/目录/glob 并逐行解析（按文件内顺序，记录时间戳排序由消费方做）。"""
    records: list[dict[str, Any]] = []
    paths: list[str] = []
    for source in sources:
        if os.path.isdir(source):
            for root, _dirs, files in os.walk(source):
                paths.extend(os.path.join(root, name) for name in sorted(files))
        elif any(ch in source for ch in "*?["):
            paths.extend(sorted(glob.glob(source)))
        else:
            paths.append(source)
    for path in paths:
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    records.extend(parse_line(line))
        except OSError as exc:
            print(f"warn: cannot read {path}: {exc}", file=sys.stderr)
    return records


def link_request_ids(records: list[dict[str, Any]]) -> None:
    """request_id ↔ trace_id 关联（LATENCY 无 trace 前缀时借 entry/锚点回填）。"""
    request_to_trace: dict[str, str] = {}
    for record in records:
        if record.get("request") and record.get("trace_id"):
            request_to_trace[str(record["request"])] = record["trace_id"]
        tags = record.get("tags") or {}
        if isinstance(tags, dict) and tags.get("request_id") and record.get("trace_id"):
            request_to_trace.setdefault(str(tags["request_id"]), record["trace_id"])
    for record in records:
        if not record.get("trace_id") and record.get("request") in request_to_trace:
            record["trace_id"] = request_to_trace[str(record["request"])]
        tags = record.get("tags") or {}
        if isinstance(tags, dict) and not record.get("trace_id") and tags.get("request_id"):
            record["trace_id"] = request_to_trace.get(str(tags["request_id"]), "")


def build_timeline(records: list[dict[str, Any]], trace_id: str) -> dict[str, Any]:
    """按 trace_id 聚合：有序时间线 + 汇总（model/cost/latency/context 关联）。"""
    mine = [record for record in records if record.get("trace_id") == trace_id]
    mine.sort(key=lambda r: (float(r.get("ts") or 0.0)))

    stages: list[dict[str, Any]] = []
    models: list[str] = []
    total_cost = 0.0
    total_tokens = 0
    llm_latency = 0.0
    funnel: list[dict[str, Any]] = []
    causal_trace_ids: list[str] = []
    entry = exit_ = None
    latency_total = None

    for record in mine:
        kind = record.get("kind")
        if kind == "span":
            stages.append(record)
            tags = record.get("tags") or {}
            if record.get("stage") == "llm_call":
                model = str(tags.get("model") or "")
                if model and model not in models:
                    models.append(model)
                total_cost += float(tags.get("cost_usd") or 0.0)
                total_tokens += int(tags.get("total_tokens") or 0)
                llm_latency += float(record.get("duration_ms") or 0.0)
            causal = str(tags.get("causal_trace_id") or "")
            if causal and causal not in causal_trace_ids:
                causal_trace_ids.append(causal)
        elif kind == "entry":
            entry = record
        elif kind == "exit":
            exit_ = record
        elif kind == "latency":
            latency_total = record.get("total_ms")
        elif kind == "funnel":
            funnel.append(record)

    summary = {
        "trace_id": trace_id,
        "stage_count": len(stages),
        "has_entry": entry is not None,
        "has_exit": exit_ is not None,
        "actual_models": models,
        "llm_total_cost_usd": round(total_cost, 6),
        "llm_total_tokens": total_tokens,
        "llm_total_latency_ms": round(llm_latency, 2),
        "chain_latency_total_ms": latency_total,
        "funnel_records": len(funnel),
        "causal_trace_ids": causal_trace_ids,
    }
    return {"summary": summary, "stages": stages, "funnel": funnel, "entry": entry, "exit": exit_}


def pick_default_trace(records: list[dict[str, Any]]) -> str:
    """选 span 最多的 trace_id（最近时间优先打破平局）。"""
    counter: dict[str, tuple[int, float]] = {}
    for record in records:
        trace = record.get("trace_id")
        if not trace:
            continue
        count, latest = counter.get(trace, (0, 0.0))
        counter[trace] = (count + 1, max(latest, float(record.get("ts") or 0.0)))
    if not counter:
        return ""
    return max(counter.items(), key=lambda kv: (kv[1][0], kv[1][1]))[0]


def fetch_outcome_link(causal_trace_id: str, redis_url: str) -> dict[str, Any] | None:
    """可选：从 Redis 拉 causal trace（receipt/outcome 关联面）。失败静默。"""
    if not causal_trace_id or not redis_url:
        return None
    try:
        import redis  # type: ignore import-not-at-top

        client = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=2.0)
        raw = client.get(f"spine:trace:{causal_trace_id}")
        if not raw:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def format_timeline(timeline: dict[str, Any]) -> str:
    """人读时间线：时间 | 阶段 | 状态 | 时长 | 关键 tag。"""
    import datetime as _dt

    def _fmt_ts(value: Any) -> str:
        try:
            return _dt.datetime.fromtimestamp(float(value)).strftime("%H:%M:%S")
        except (TypeError, ValueError, OSError, OverflowError):
            return f"{float(value):.3f}" if isinstance(value, (int, float)) else str(value)

    summary = timeline["summary"]
    lines: list[str] = []
    lines.append(f"trace_id = {summary['trace_id']}")
    lines.append(
        f"stages={summary['stage_count']}"
        f" entry={'Y' if summary['has_entry'] else 'N'} exit={'Y' if summary['has_exit'] else 'N'}"
    )
    lines.append(
        f"models={','.join(summary['actual_models']) or '-'}"
        f" cost=${summary['llm_total_cost_usd']:.6f}"
        f" tokens={summary['llm_total_tokens']}"
        f" llm_latency={summary['llm_total_latency_ms']:.0f}ms"
        f" chain_total={summary['chain_latency_total_ms'] or '-'}ms"
    )
    if summary["causal_trace_ids"]:
        lines.append(f"causal_trace_ids={','.join(summary['causal_trace_ids'])}")
    lines.append("-" * 72)
    for stage in timeline["stages"]:
        tags = stage.get("tags") or {}
        keep = {
            key: tags[key]
            for key in ("model", "cost_usd", "total_tokens", "prompt_tokens", "completion_tokens",
                        "causal_trace_id", "energy_level", "execution_mode", "routing_layer",
                        "intent", "confidence", "chat_mode", "workflow_id", "plan_id",
                        "timed_out", "error_type", "stage_count", "elapsed_ms")
            if key in tags
        }
        duration = stage.get("duration_ms")
        lines.append(
            f"  {_fmt_ts(stage.get('ts', 0))}  {stage.get('stage', '?'):<20}"
            f" {stage.get('status', '?'):<10}"
            f" {('-' if duration is None else f'{float(duration):.0f}ms'):>8}"
            + (f"  {json.dumps(keep, ensure_ascii=False)}" if keep else "")
        )
    for funnel in timeline["funnel"]:
        lines.append(f"  {_fmt_ts(funnel.get('ts', 0))}  context_funnel         {'-':<10} {'-':>8}  {funnel.get('surfaces') or ''}")
    lines.append("-" * 72)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按 trace_id 还原全链时间线（O-02）")
    parser.add_argument("sources", nargs="+", help="日志文件/目录/glob")
    parser.add_argument("--trace-id", default="", help="目标 trace_id（缺省自动选 span 最多者）")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--redis-url", default=os.getenv("REDIS_URL", ""), help="可选：拉 causal trace receipt/outcome")
    args = parser.parse_args(argv)

    records = collect_records(args.sources)
    if not records:
        print("no trace records found in given sources", file=sys.stderr)
        return 1
    link_request_ids(records)

    trace_id = args.trace_id or pick_default_trace(records)
    if not trace_id:
        print("no trace_id candidates found", file=sys.stderr)
        return 1

    timeline = build_timeline(records, trace_id)
    if timeline["summary"]["causal_trace_ids"]:
        outcome = fetch_outcome_link(timeline["summary"]["causal_trace_ids"][0], args.redis_url)
        if outcome is not None:
            timeline["causal_trace"] = {
                key: outcome.get(key)
                for key in ("trace_id", "policy_decision_id", "receipt_ids", "outcome_to_measure", "aurora_energy_level")
                if key in outcome
            }

    if args.json:
        print(json.dumps(timeline, ensure_ascii=False, indent=2, default=str))
    else:
        print(format_timeline(timeline))
        if "causal_trace" in timeline:
            print(f"causal_trace(linked) = {json.dumps(timeline['causal_trace'], ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
