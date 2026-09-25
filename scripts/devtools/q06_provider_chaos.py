#!/usr/bin/env python3
"""Q-06 供应商波动注入（wt406）— 429 / 慢 TTFT / 断流 / 队列压力.

注入点=上游客户端层：引擎经 env 把 DASHSCOPE/DEEPSEEK/ZHIPU 三个 OpenAI 兼容
base_url 指向本 mock（:9099），产品代码零改动；故障由 admin 接口在运行时切换。
被测面：真实 gRPC StreamChat（:50062 chaos 引擎）→ 真实 llm_router/fallback/
health/concurrency 管道 → mock 上游。观测三面：
- 用户可见面：首事件/首内容/截断标记/错误事件/总时长（逐帧时间线原样落盘）；
- 引擎行为面：[LLMFallback] 换道链 / 三相健康状态机跃迁 / 并发池排队（引擎日志切片）;
- 上游请求面：mock 收到的真实尝试链（次数/时序/模型）——false smooth=0，抖动原样呈报。

场景（每场景 n>=8 探针，S5=30 并发）：
  S1 primary-429     仅 qwen* 429（fallback 候选 ok）——换道链与延迟代价
  S3a slow-ttft-35s  仅 qwen* 首 token 延迟 35s（< 60s read timeout，不触发超时）
  S3b slow-ttft-65s  全模型首 token 延迟 65s（> read timeout，触发超时链）
  S4a broken-qwen    仅 qwen* 出 2 delta 后断流——mid-stream 截断语义
  S4b broken-all     全模型断流——截断+fallback 边界（首 chunk 前失败才可换道）
  S5  queue-pressure 全模型 ok 但延迟 5s × 30 并发——并发池排队/公平性/超时
  S2  total-outage   全模型 429 × 12 连发——熔断开路与开路后快速失败（放最后跑）

前置（由驱动方保证）：
  1) chaos 引擎 :50062（.env 覆盖 GRPC_PORT=50062 / REDIS_URL db2 / 三个 base_url→mock）
  2) mock：python3 q06_provider_chaos.py serve &（:9099）
  3) 场景间驱动器自动清 redis db2 的 llm:* 健康键（环境复位，非产品语义改动）

用法:
  python3 q06_provider_chaos.py serve                 # 起 mock（独立进程）
  python3 q06_provider_chaos.py run [--scenarios S1,S3a,...] [--out-dir DIR]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# 注：from __future__ import annotations 使注解成为字符串，FastAPI 经
# get_type_hints 在模块全局解析——Request/Response 类必须在模块顶层可导入，
# 放进 build_mock_app 闭包内会被降级为 query 参数（实测 422）。
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKTREE_BACKEND = REPO_ROOT / "backend"
MOCK_PORT = 9099
GRPC_TARGET = "127.0.0.1:50062"
HTTP_BASE = "http://127.0.0.1:8000/api/v1"
GUEST_ID = "wt406_q06_bench_free"
MOCK_LOG = Path("/tmp/q06_mock_requests.jsonl")
DEFAULT_OUT = REPO_ROOT / "v3-output" / "WT406-Q06-PERF"

PROBE_TEXTS = [
    "什么是间隔重复？",
    "用一句话解释主动回忆",
    "怎么快速背单词？",
    "什么是费曼学习法？",
    "番茄工作法是什么？",
    "帮我出3个关于细胞呼吸的复习题",
    "什么是刻意练习？",
    "艾宾浩斯遗忘曲线对复习安排有什么启发？",
    "什么是交叉学习？",
    "看书犯困怎么办？",
    "什么是输出式学习？",
    "笔记应该手写还是打字？",
]


# ---------------------------------------------------------------------------
# mock 上游服务器（OpenAI 兼容 /chat/completions + /admin/mode）
# ---------------------------------------------------------------------------
def build_mock_app():
    app = FastAPI()
    state = {"mode": "ok", "ttft_delay_s": 0.0, "stream_chunks_before_break": 2, "upstream_latency_s": 0.0}
    app.state.config = state

    def _log(model: str, stream: bool) -> None:
        with open(MOCK_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                "mode": state["mode"], "model": model, "stream": stream,
            }) + "\n")

    def _is_qwen(model: str) -> bool:
        return "qwen" in (model or "").lower()

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "mode": state["mode"]}

    @app.post("/admin/mode")
    async def set_mode(req: Request) -> dict:
        body = await req.json()
        state["mode"] = body.get("mode", "ok")
        state["ttft_delay_s"] = float(body.get("ttft_delay_s", 0.0))
        state["stream_chunks_before_break"] = int(body.get("stream_chunks_before_break", 2))
        state["upstream_latency_s"] = float(body.get("upstream_latency_s", 0.0))
        with open(MOCK_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                                "mode_switch": state["mode"]}) + "\n")
        return state

    @app.post("/compatible-mode/v1/chat/completions")
    async def completions(req: Request):
        body = await req.json()
        model = body.get("model", "")
        stream = bool(body.get("stream"))
        _log(model, stream)
        mode = state["mode"]
        qwen_hit = mode in ("429_dashscope",) and _is_qwen(model)
        all_hit = mode in ("429_all",)
        slow_all = mode in ("slow_ttft_65_all",)
        slow_qwen = mode in ("slow_ttft_35_qwen",) and _is_qwen(model)
        broken_qwen = mode in ("broken_qwen",) and _is_qwen(model)
        broken_all = mode in ("broken_all",)
        latency = state["upstream_latency_s"] if mode == "slow_ok" else 0.0
        ttft_delay = 65.0 if slow_all else (35.0 if slow_qwen else state["ttft_delay_s"])

        if qwen_hit or all_hit:
            await asyncio.sleep(min(latency, 1.0))
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "throttling", "message": "Requests rate limit exceeded, please retry later."}},
                headers={"Retry-After": "1"},
            )

        async def sse() -> StreamingResponse:  # noqa: ANN202
            chunks = ["这是mock回复。", f"模型{model}在模式{mode}下的第二句。", "第三句收尾。"]

            def sdata(content: str | None, finish: str | None = None, usage: dict | None = None) -> str:
                payload: dict = {"id": "chatcmpl-mock", "object": "chat.completion.chunk", "model": model,
                                 "choices": [{"index": 0, "delta": ({} if content is None else {"content": content}),
                                              "finish_reason": finish}]}
                if usage is not None:
                    payload["usage"] = usage
                return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            if ttft_delay > 0:
                await asyncio.sleep(ttft_delay)
            if latency > 0:
                await asyncio.sleep(latency)
            if stream:
                for i, c in enumerate(chunks):
                    yield sdata(c)
                    if (broken_qwen or broken_all) and i + 1 >= state["stream_chunks_before_break"]:
                        # 模拟上游断流：不发 [DONE] 直接截断连接
                        return
                    await asyncio.sleep(0.02)
                yield sdata(None, finish="stop", usage={"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150})
                yield "data: [DONE]\n\n"
            else:
                payload = {"id": "chatcmpl-mock", "object": "chat.completion", "model": model,
                           "choices": [{"index": 0, "message": {"role": "assistant", "content": "".join(chunks)},
                                        "finish_reason": "stop"}],
                           "usage": {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\ndata: [DONE]\n\n"

        return StreamingResponse(sse(), media_type="text/event-stream")

    @app.post("/{path:path}")
    async def catch_all(path: str, req: Request) -> StreamingResponse:
        """zhipu（/api/paas/v4）等非 compatible 路径同口径应答——保证『all providers』
        场景里所有候选都打到 mock，而不是被 404 短路（mock 是测试仪器，非产品面）。"""
        return await completions(req)

    return app


def serve() -> None:
    import uvicorn

    MOCK_LOG.write_text("", encoding="utf-8")
    uvicorn.run(build_mock_app(), host="127.0.0.1", port=MOCK_PORT, log_level="warning")


# ---------------------------------------------------------------------------
# 场景驱动
# ---------------------------------------------------------------------------
def guest_auth() -> tuple[str, str]:
    import httpx

    r = httpx.post(f"{HTTP_BASE}/auth/guest", params={"guest_id": GUEST_ID}, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["access_token"], data["user"]["id"]


def _import_stub():
    sys.path.insert(0, str(WORKTREE_BACKEND))
    sys.path.insert(0, str(WORKTREE_BACKEND / "app" / "gen" / "agent" / "v1"))
    import agent_service_pb2 as pb2
    import agent_service_pb2_grpc as pb2_grpc

    return pb2, pb2_grpc


def mock_set_mode(mode: str, **params: float) -> None:
    import httpx

    r = httpx.post(f"http://127.0.0.1:{MOCK_PORT}/admin/mode",
                   json={"mode": mode, **params}, timeout=10)
    r.raise_for_status()


def mock_requests_since(iso_since: str) -> list[dict]:
    rows = [json.loads(line) for line in MOCK_LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in rows if r.get("ts", "") > iso_since]


def clear_engine_health() -> None:
    """清 chaos 引擎 redis db2 的 llm:* 健康键（场景间环境复位）。"""
    subprocess.run(
        ["docker", "exec", "sparkle_redis", "sh", "-c",
         "redis-cli -a sparkle_dev_redis_2026 -n 2 --scan --pattern 'llm:*' | xargs -r redis-cli -a sparkle_dev_redis_2026 -n 2 DEL >/dev/null 2>&1; exit 0"],
        capture_output=True, timeout=15, check=False,
    )


def one_probe(stub, pb2, token: str, uid: str, text: str, request_id: str, timeout: float = 180.0) -> dict:
    req = pb2.ChatRequest(user_id=uid, message=text, session_id="",
                          request_id=request_id, chat_mode="standard")
    meta = [("authorization", f"Bearer {token}"), ("user-id", uid)]
    t0 = time.perf_counter()
    first_event = first_delta = None
    text_out = ""
    err = None
    frames: list[dict] = []
    truncated_marker = False
    try:
        for fr in stub.StreamChat(req, metadata=meta, timeout=timeout):
            t = time.perf_counter() - t0
            kind = fr.WhichOneof("content")
            md_keys = sorted(fr.metadata.keys()) if fr.metadata else []
            if first_event is None and (md_keys or kind):
                first_event = t
            if kind == "delta":
                if first_delta is None:
                    first_delta = t
                text_out += fr.delta
            elif kind == "full_text":
                text_out = fr.full_text
            elif kind == "error":
                err = {"error_code": str(fr.error.error_code), "message": fr.error.message[:300], "retryable": bool(fr.error.retryable)}
            frames.append({"t": round(t, 3), "kind": kind or "meta_only", "md_keys": md_keys})
    except Exception as exc:  # noqa: BLE001
        err = {"code": type(exc).__name__, "message": str(exc)[:300]}
    total = time.perf_counter() - t0
    if "⚠️ _stream_truncated_" in text_out:
        truncated_marker = True
    return {
        "request_id": request_id,
        "t_first_event_s": round(first_event, 3) if first_event is not None else None,
        "ttft_first_delta_s": round(first_delta, 3) if first_delta is not None else None,
        "total_s": round(total, 3),
        "chars": len(text_out), "truncated_marker": truncated_marker,
        "error": err,
        "frame_count": len(frames),
        "frame_kinds": [f["kind"] for f in frames[:40]],
        "head": text_out[:80].replace("\n", " "),
    }


def grep_engine_log(log_path: Path, since_iso: str, until_iso: str) -> list[str]:
    if not log_path.exists():
        return []
    hits: list[str] = []
    with open(log_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(line) < 19:
                continue
            ts = line[:19]
            if since_iso[11:19] <= ts[11:19] <= until_iso[11:19] and any(
                k in line for k in ("LLMFallback", "marked unhealthy", "probation", "record_failure",
                                    "circuit", "free_tier_downgrade", "rate limit", "Timeout acquiring")
            ):
                hits.append(line.rstrip()[:400])
    return hits[-80:]


SCENARIOS: dict[str, dict] = {
    "S1": {"mode": "429_dashscope", "n": 8, "label": "primary-429（qwen* 429，fallback 候选 ok）"},
    "S3a": {"mode": "slow_ttft_35_qwen", "n": 5, "label": "slow TTFT 35s（qwen*，<60s read timeout）"},
    "S3b": {"mode": "slow_ttft_65_all", "n": 5, "label": "slow TTFT 65s（all，>60s read timeout）"},
    "S4a": {"mode": "broken_qwen", "n": 8, "label": "断流（qwen* 出 2 delta 即断）"},
    "S4b": {"mode": "broken_all", "n": 8, "label": "断流（all）"},
    "S5": {"mode": "slow_ok", "n": 30, "label": "队列压力（all ok×5s 上游延迟，30 并发）"},
    "S2": {"mode": "429_all", "n": 12, "label": "total outage（all 429×12 连发，熔断开路；最后跑）"},
}


async def run_scenarios(out_dir: Path, only: list[str]) -> None:
    pb2, pb2_grpc = _import_stub()
    import grpc

    token, uid = guest_auth()
    print(f"auth ok: {uid}", flush=True)
    engine_log = WORKTREE_BACKEND / "logs"
    log_files = sorted(engine_log.glob("grpc_server_*.log"))
    log_path = log_files[-1] if log_files else None

    results: list[dict] = []
    for sid in only:
        sc = SCENARIOS[sid]
        clear_engine_health()
        mock_set_mode(sc["mode"], stream_chunks_before_break=2)
        time.sleep(1)
        since = datetime.now(timezone.utc).isoformat(timespec="seconds")
        t0 = time.time()
        channel = grpc.insecure_channel(GRPC_TARGET)
        stub = pb2_grpc.AgentServiceStub(channel)
        probes: list[dict] = []
        try:
            if sid == "S5":
                import concurrent.futures

                def _one(i: int) -> dict:
                    local_channel = grpc.insecure_channel(GRPC_TARGET)
                    local_stub = pb2_grpc.AgentServiceStub(local_channel)
                    try:
                        return one_probe(local_stub, pb2, token, uid,
                                         PROBE_TEXTS[i % len(PROBE_TEXTS)],
                                         f"wt406-chaos-{sid}-{i}-{uuid.uuid4().hex[:6]}", timeout=150.0)
                    finally:
                        local_channel.close()

                with concurrent.futures.ThreadPoolExecutor(max_workers=30) as pool:
                    probes = list(pool.map(_one, range(sc["n"])))
            else:
                for i in range(sc["n"]):
                    probes.append(one_probe(stub, pb2, token, uid,
                                            PROBE_TEXTS[i % len(PROBE_TEXTS)],
                                            f"wt406-chaos-{sid}-{i}-{uuid.uuid4().hex[:6]}"))
                    time.sleep(0.6)
        finally:
            channel.close()
        until = datetime.now(timezone.utc).isoformat(timespec="seconds")
        upstream = mock_requests_since(since)
        log_hits = grep_engine_log(log_path, since, until) if log_path else []
        results.append({
            "scenario": sid, "label": sc["label"], "mode": sc["mode"],
            "n": len(probes), "wall_s": round(time.time() - t0, 1),
            "probes": probes,
            "upstream_requests": len([r for r in upstream if "model" in r]),
            "upstream_sample": upstream[:40],
            "engine_log_hits": log_hits,
            "summary": {
                "ok": sum(1 for p in probes if not p["error"]),
                "err": sum(1 for p in probes if p["error"]),
                "truncated": sum(1 for p in probes if p["truncated_marker"]),
                "ttft_max": max((p["ttft_first_delta_s"] or 0) for p in probes),
                "total_max": max(p["total_s"] for p in probes),
                "total_min": min(p["total_s"] for p in probes),
                "err_codes": sorted({(p["error"] or {}).get("error_code", "") for p in probes if p["error"]}),
            },
        })
        print(f"[{sid}] {sc['label']} -> {json.dumps(results[-1]['summary'], ensure_ascii=False)}", flush=True)

    mock_set_mode("ok")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "chaos_results.json"
    # 增量合并（按 scenario id）——防部分跑完后覆写丢历史场景
    merged: list[dict] = []
    if out_path.exists():
        try:
            merged = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            merged = []
    by_id = {r.get("scenario"): r for r in merged}
    for r in results:
        by_id[r["scenario"]] = r
    order = ["S1", "S3a", "S3b", "S4a", "S4b", "S5", "S2"]
    merged = sorted(by_id.values(), key=lambda r: order.index(r["scenario"]) if r.get("scenario") in order else 99)
    out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"results -> {out_path} (scenarios: {[r['scenario'] for r in merged]})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("serve", help="启动 mock 上游（:9099）")
    ap_run = sub.add_parser("run", help="跑场景（需 chaos 引擎 :50062 与 mock 在位）")
    ap_run.add_argument("--scenarios", default="S1,S3a,S3b,S4a,S4b,S5,S2")
    ap_run.add_argument("--out-dir", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    if args.cmd == "serve":
        serve()
    else:
        only = [s.strip() for s in args.scenarios.split(",") if s.strip()]
        asyncio.run(run_scenarios(Path(args.out_dir), only))


if __name__ == "__main__":
    main()
