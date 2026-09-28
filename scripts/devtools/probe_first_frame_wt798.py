#!/usr/bin/env python3
"""E-08 首帧重采探针（wt798）— keyless intake-ack 首帧测量（wt755 集成后活栈）.

口径与 wt372 bench（scripts/devtools/bench_ai_stack_l0_l3.py）对齐：
  - 引擎直连：gRPC 127.0.0.1:50051 StreamChat + HTTP 127.0.0.1:8000 guest JWT；
    网关 :8080 纯透传不进口径（同 wt372 §口径注记）。
  - t0 = 客户端发起 StreamChat 前；t_ack = 收到首个帧（应为 intake ack：ux_progress
    stage=intake、metadata.early_ack=true、status_update）。
  - 失败不重试，逐样本如实落 raw.jsonl。

keyless 臂设计（引擎有真实 key、非 demo_mode，不可走 happy path）：
  消息长度 > MAX_MESSAGE_LENGTH(2000)（validator.py 确定性拒绝）→ 新代码次序为
  [请求身份锚定 → run_started → intake ack → drain] → 校验失败 → INVALID_ARGUMENT
  终帧。ack 路径与正常请求完全同构（同一 emit 点），LLM 零消耗、零成本。
  服务端次序佐证：/tmp/grpc_day7b.log 中 "Validation failed" 行时间戳应晚于该样本
  客户端 t_ack（同机时钟）。

用法:
  backend/.venv/bin/python scripts/devtools/probe_first_frame_wt798.py run \
      [--samples 24] [--guest-id wt798_e08_guest] [--chars 2400] [--out-dir DIR]
  backend/.venv/bin/python scripts/devtools/probe_first_frame_wt798.py summarize \
      --out-dir DIR

参考钉测：backend/tests/unit/test_stage_events_e03.py::
test_intake_ack_beats_slow_prologue_guards（wt755，0b063c7c 集成主干）。
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_BACKEND = Path("/Users/brsama/code/GitHub/Sparkle-project/backend")
GRPC_TARGET = "127.0.0.1:50051"
HTTP_BASE = "http://127.0.0.1:8000/api/v1"
ENGINE_LOG = Path("/tmp/grpc_day7b.log")
DEFAULT_OUT_DIR = REPO_ROOT / "v3-output" / "WT798-E08SAMPLE" / "evidence"
INTER_SAMPLE_SLEEP_S = 0.5
BENIGN_SENTENCE = "帮我制定一个高效的期末复习计划，包括每日任务拆分与复盘节奏，"


def _import_stubs():
    sys.path.insert(0, str(ENGINE_BACKEND))
    gen_dir = ENGINE_BACKEND / "app" / "gen" / "agent" / "v1"
    sys.path.insert(0, str(gen_dir))
    import agent_service_pb2 as pb2  # noqa: PLC0415
    import agent_service_pb2_grpc as pb2_grpc  # noqa: PLC0415
    return pb2, pb2_grpc


def guest_auth(guest_id: str) -> tuple[str, str]:
    import httpx  # noqa: PLC0415

    r = httpx.post(f"{HTTP_BASE}/auth/guest", params={"guest_id": guest_id}, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["access_token"], data["user"]["id"]


def _pct(values: list[float], p: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, round((p / 100) * (len(ordered) - 1))))
    return ordered[k]


def _parse_ack_frame(fr) -> dict:  # noqa: ANN001
    md = {k: v for k, v in fr.metadata.items()} if fr.metadata else {}
    ux = {}
    try:
        ux = json.loads(md.get("ux_progress") or "{}")
    except json.JSONDecodeError:
        ux = {}
    return {"kind": fr.WhichOneof("content"), "stage": ux.get("stage", ""), "metadata": md}


def run(samples: int, guest_id: str, chars: int, out_dir: Path) -> None:
    import grpc  # noqa: PLC0415

    pb2, pb2_grpc = _import_stubs()
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "raw.jsonl"

    log_offset = ENGINE_LOG.stat().st_size if ENGINE_LOG.exists() else 0
    token, user_id = guest_auth(guest_id)
    print(f"guest user_id={user_id} guest_id={guest_id}")

    channel = grpc.insecure_channel(GRPC_TARGET)
    grpc.channel_ready_future(channel).result(timeout=10)
    stub = pb2_grpc.AgentServiceStub(channel)
    meta = [("authorization", f"Bearer {token}"), ("user-id", user_id)]

    message = (BENIGN_SENTENCE * (chars // len(BENIGN_SENTENCE) + 1))[:chars]
    assert len(message) > 2000, "探针消息必须超过 MAX_MESSAGE_LENGTH(2000)"

    records: list[dict] = []
    for i in range(1, samples + 1):
        request_id = f"wt798-e08-ack-{i:02d}-{uuid.uuid4().hex[:6]}"
        session_id = f"wt798e08-{uuid.uuid4().hex[:12]}"
        req = pb2.ChatRequest(
            user_id=user_id,
            message=message,
            session_id=session_id,
            request_id=request_id,
        )
        frames_seen: list[dict] = []
        t_ack = None
        t_tail = None
        error_msg = ""
        finish_reason_name = ""
        t0 = time.perf_counter()
        try:
            for fr in stub.StreamChat(req, metadata=meta, timeout=60):
                t = time.perf_counter() - t0
                info = _parse_ack_frame(fr)
                frames_seen.append({"t": round(t, 4), **info,
                                    "finish_reason": pb2.FinishReason.Name(fr.finish_reason)})
                if t_ack is None:
                    t_ack = t
                if fr.finish_reason != pb2.NULL:
                    finish_reason_name = pb2.FinishReason.Name(fr.finish_reason)
                    t_tail = t
                    if fr.WhichOneof("content") == "error":
                        error_msg = fr.error.message
                    break
        except grpc.RpcError as exc:
            t_tail = time.perf_counter() - t0
            error_msg = f"grpc:{exc.code().name}:{exc.details()}"
        total = time.perf_counter() - t0
        first = frames_seen[0] if frames_seen else {}
        rec = {
            "sample": i,
            "request_id": request_id,
            "session_id": session_id,
            "t_ack_s": round(t_ack, 4) if t_ack is not None else None,
            "t_tail_s": round(t_tail, 4) if t_tail is not None else None,
            "total_s": round(total, 4),
            "first_frame_kind": first.get("kind"),
            "first_frame_stage": first.get("stage"),
            "first_frame_is_early_ack": bool(first.get("metadata", {}).get("early_ack") == "true"),
            "finish_reason": finish_reason_name,
            "error_message": error_msg,
            "n_frames": len(frames_seen),
            "frames": frames_seen,
            "message_chars": len(message),
        }
        records.append(rec)
        print(f"[{i:02d}/{samples}] t_ack={rec['t_ack_s']}s stage={rec['first_frame_stage']} "
              f"early_ack={rec['first_frame_is_early_ack']} finish={finish_reason_name} "
              f"err={error_msg[:60]}")
        with raw_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        time.sleep(INTER_SAMPLE_SLEEP_S)

    # 服务端次序佐证：捕获本窗口内引擎日志的 Validation failed 时间戳
    server_validation_times: list[str] = []
    try:
        with ENGINE_LOG.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(log_offset)
            for line in f:
                if "Validation failed" in line:
                    server_validation_times.append(line[:23])
    except OSError:
        pass
    (out_dir / "server_validation_log_lines.json").write_text(
        json.dumps({"captured_after_offset": log_offset, "lines": server_validation_times},
                   ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    summarize(out_dir)


def summarize(out_dir: Path) -> None:
    raw_path = out_dir / "raw.jsonl"
    records = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    acks = [r["t_ack_s"] for r in records if r.get("t_ack_s") is not None]
    tails = [r["t_tail_s"] for r in records if r.get("t_tail_s") is not None]
    ack_is_first = sum(1 for r in records if r["n_frames"] > 0)
    early_acks = sum(1 for r in records if r.get("first_frame_is_early_ack"))
    intake_stage = sum(1 for r in records if r.get("first_frame_stage") == "intake")
    ok_finish = sum(1 for r in records if r.get("finish_reason") == "ERROR")
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n": len(records),
        "t_ack_p50_s": round(_pct(acks, 50), 4) if acks else None,
        "t_ack_p95_s": round(_pct(acks, 95), 4) if acks else None,
        "t_ack_min_s": round(min(acks), 4) if acks else None,
        "t_ack_max_s": round(max(acks), 4) if acks else None,
        "t_ack_mean_s": round(statistics.fmean(acks), 4) if acks else None,
        "t_tail_p50_s": round(_pct(tails, 50), 4) if tails else None,
        "t_tail_p95_s": round(_pct(tails, 95), 4) if tails else None,
        "first_frame_received": ack_is_first,
        "first_frame_is_early_ack_true": early_acks,
        "first_frame_stage_intake": intake_stage,
        "finish_reason_ERROR": ok_finish,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("--samples", type=int, default=24)
    p_run.add_argument("--guest-id", default="wt798_e08_guest")
    p_run.add_argument("--chars", type=int, default=2400)
    p_run.add_argument("--out-dir", type=Path, default=None)
    p_sum = sub.add_parser("summarize")
    p_sum.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.cmd == "run":
        out_dir = args.out_dir or (DEFAULT_OUT_DIR / datetime.now().strftime("ack_%Y%m%d_%H%M%S"))
        run(args.samples, args.guest_id, args.chars, out_dir)
    else:
        summarize(args.out_dir)


if __name__ == "__main__":
    main()
