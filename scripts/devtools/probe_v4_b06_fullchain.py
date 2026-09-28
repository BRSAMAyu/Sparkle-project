#!/usr/bin/env python3
"""V4-B06 全链限额探针 — guest JWT → Go 网关(:8080) /ws/chat → gRPC → 引擎 → 真实模型.

V4-B06 卡（真实模型能力、调用预算与全链测量基线）的种子数据探针。
调用预算：默认 3 条最小消息（卡上限 ≤5；不含 guest 登录，其为零模型调用）。

口径（对齐 LATENCY_COST_RUNTIME.md：gRPC 测量与 Flutter→网关整链分开）：
  - t_send            = 客户端 WS send 完成（整链起点，含网关）；
  - t_first_event     = 首个服务端帧（ack/status_update，对应网关
                        sparkle_ai_chat_first_event_duration_seconds）；
  - t_first_visible   = 首个 delta/full_text（对应
                        sparkle_ai_chat_first_token_duration_seconds，「有用首内容」起点）；
  - t_done            = done/finish_reason 帧（整链总时长）。
  - usage 帧（proto Usage: prompt/completion/total_tokens + cost_micro_usd）如实记录。

红线：token/密钥零回显（raw 输出不含 JWT）；失败如实落 FAIL/ERROR，不重试烧预算。
用法（用主检出 backend/.venv 的解释器，本 worktree 无 venv）：
  /Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python \\
      scripts/devtools/probe_v4_b06_fullchain.py --out v4/evidence/V4-B06/probe
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GATEWAY_BASE = os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:8080/api/v1")
WS_URL = os.getenv("WS_CHAT_URL", "ws://127.0.0.1:8080/ws/chat")
CHAT_TIMEOUT_SECONDS = float(os.getenv("V4_B06_PROBE_TIMEOUT_SECONDS", "90"))

# 3 条最小探针消息（≤卡定 5 次预算；第 3 条按 LATENCY_COST_RUNTIME L0 预期走零生成路径）
DEFAULT_TURNS: list[dict[str, str]] = [
    {"name": "t1_generation_min", "message": "用一句话说明什么是番茄钟学习法。", "chat_mode": "standard", "reasoning_mode": "balanced"},
    {"name": "t2_generation_fast", "message": "用一句话解释什么是艾宾浩斯遗忘曲线。", "chat_mode": "standard", "reasoning_mode": "fast"},
    {"name": "t3_greeting_l0", "message": "你好", "chat_mode": "standard", "reasoning_mode": "fast"},
]


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def guest_login() -> tuple[str, str, dict[str, Any]]:
    """经网关获取 guest JWT（零模型调用）。绝不回显 token。"""
    import httpx

    guest_id = f"v4b06_probe_{uuid.uuid4().hex[:8]}"
    started = time.monotonic()
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(f"{GATEWAY_BASE}/auth/guest", params={"guest_id": guest_id})
        elapsed = round(time.monotonic() - started, 3)
        resp.raise_for_status()
        data = resp.json()
    token = str(data.get("access_token") or "")
    user_id = str((data.get("user") or {}).get("id") or "")
    if not token or not user_id:
        raise RuntimeError("guest login response missing access_token/user.id")
    meta = {
        "guest_id_prefix": guest_id[:12],
        "seed_status": data.get("seed_status"),
        "http_elapsed_s": elapsed,
    }
    return token, user_id, meta


async def run_turn(token: str, *, turn: dict[str, str], session_id: str) -> dict[str, Any]:
    import websockets

    req_id = f"v4b06-{uuid.uuid4().hex[:12]}"
    ws_uri = f"{WS_URL}?token={token}"
    events: list[dict[str, Any]] = []
    t_connect: float | None = None
    t_first_event: float | None = None
    t_first_visible: float | None = None
    t_done: float | None = None
    error: str | None = None

    t0 = time.monotonic()
    try:
        async with websockets.connect(ws_uri, ping_interval=None, ping_timeout=None, max_size=2**22) as ws:
            t_connect = round(time.monotonic() - t0, 4)
            await ws.send(
                json.dumps(
                    {
                        "type": "message",
                        "message": turn["message"],
                        "session_id": session_id,
                        "request_id": req_id,
                        "chat_mode": turn["chat_mode"],
                        "extra_context": {"reasoning_mode": turn["reasoning_mode"]},
                    },
                    ensure_ascii=False,
                )
            )
            t_send = time.monotonic()
            while True:
                remaining = CHAT_TIMEOUT_SECONDS - (time.monotonic() - t_send)
                if remaining <= 0:
                    error = f"timeout after {CHAT_TIMEOUT_SECONDS}s"
                    break
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                except (asyncio.TimeoutError, TimeoutError):
                    error = f"recv timeout after {CHAT_TIMEOUT_SECONDS}s"
                    break
                now = time.monotonic()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = {"type": "non_json_frame", "raw_len": len(raw)}
                if t_first_event is None:
                    t_first_event = round(now - t_send, 4)
                etype = str(data.get("type") or "")
                if etype in {"delta", "full_text"} and t_first_visible is None:
                    t_first_visible = round(now - t_send, 4)
                events.append(data)
                if etype == "done" or data.get("finish_reason") not in {None, "", "NULL"} or etype == "error":
                    t_done = round(now - t_send, 4)
                    if etype == "error":
                        error = json.dumps(data, ensure_ascii=False)[:500]
                    break
    except Exception as exc:  # noqa: BLE001 — 探针如实记录一切失败
        error = f"{type(exc).__name__}: {exc}"[:500]

    visible = "".join(
        str(e.get("delta") or "")
        for e in events
        if e.get("type") == "delta"
    )
    full_texts = [str(e.get("full_text") or "") for e in events if e.get("type") == "full_text" and str(e.get("full_text") or "").strip()]
    merged_meta: dict[str, Any] = {}
    for e in events:
        md = e.get("metadata")
        if isinstance(md, dict):
            merged_meta.update(md)
    usage_frames = [e for e in events if e.get("type") == "usage"]
    frame_types = [str(e.get("type") or "?") for e in events]

    return {
        "turn": turn["name"],
        "request_id": req_id,
        "session_id": session_id,
        "chat_mode": turn["chat_mode"],
        "reasoning_mode": turn["reasoning_mode"],
        "t_connect_s": t_connect,
        "t_first_event_s": t_first_event,
        "t_first_visible_s": t_first_visible,
        "t_done_s": t_done,
        "frame_types": frame_types[:60],
        "usage_frames": usage_frames,
        "metadata_subset": {
            k: merged_meta.get(k)
            for k in (
                "model_used",
                "generation_model_key",
                "generation_model_tier",
                "first_touch_model_tier",
                "final_synthesis_model_tier",
                "reasoning_mode",
                "chat_mode",
                "routing_mode",
                "selected_experts",
                "finish_reason",
                "response_fallback_used",
                "trace_id",
                "usage",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "cost_micro_usd",
            )
            if k in merged_meta
        },
        "has_error_frame": any(e.get("type") == "error" for e in events),
        "error": error,
        "text_chars": len(full_texts[-1]) if full_texts else len(visible),
        "text_preview": (full_texts[-1] if full_texts else visible)[:160],
        "event_count": len(events),
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="V4-B06 full-chain probe")
    parser.add_argument("--out", default="v4/evidence/V4-B06/probe", help="evidence output dir")
    parser.add_argument("--turns", type=int, default=3, choices=[1, 2, 3], help="model-bearing turns (budget cap)")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "probe": "v4-b06-fullchain",
        "started_at": _utcnow_iso(),
        "gateway_base": GATEWAY_BASE,
        "ws_url": WS_URL,
        "budget_note": "3 model-bearing turns (card cap <=5); guest login is zero-model",
        "python": os.popen("python3 --version").read().strip(),
        "turns": [],
    }

    print(f"[{_utcnow_iso()}] guest login via {GATEWAY_BASE}/auth/guest ...", flush=True)
    token, user_id, login_meta = await guest_login()
    manifest["guest_login"] = login_meta
    manifest["user_id"] = user_id
    print(f"[{_utcnow_iso()}] login ok seed={login_meta.get('seed_status')} http={login_meta['http_elapsed_s']}s", flush=True)

    session_id = str(uuid.uuid4())
    for turn in DEFAULT_TURNS[: args.turns]:
        print(f"[{_utcnow_iso()}] turn {turn['name']} sending ...", flush=True)
        result = await run_turn(token, turn=turn, session_id=session_id)
        manifest["turns"].append(result)
        print(
            json.dumps(
                {
                    "turn": result["turn"],
                    "first_event_s": result["t_first_event_s"],
                    "first_visible_s": result["t_first_visible_s"],
                    "done_s": result["t_done_s"],
                    "frames": result["frame_types"][:12],
                    "error": result["error"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        await asyncio.sleep(0.5)

    manifest["finished_at"] = _utcnow_iso()
    out_file = out_dir / "probe_raw.json"
    out_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written {out_file}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
