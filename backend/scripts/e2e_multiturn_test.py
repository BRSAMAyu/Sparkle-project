#!/usr/bin/env python3
"""Sparkle End-to-End Multi-Turn Chat Test — v2 (new WS per turn, matching SGW pattern).

Tests: Auth → WebSocket → Go Gateway → Python gRPC → LLM → Response
"""

import asyncio
import json
import os
import time
import uuid
import sys

import requests
import websockets

BASE = "http://localhost:8000"
WS_URL = "ws://localhost:8080/ws/chat"
GATEWAY_BASE = "http://localhost:8080"

USERNAME = os.getenv("LOCAL_SMOKE_USERNAME", "e2etest")
EMAIL = os.getenv("LOCAL_SMOKE_EMAIL", "e2e@sparkle.dev")
PASSWORD = os.getenv("LOCAL_SMOKE_PASSWORD", "Test123456!")


def log_section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")

def log_step(step):
    print(f"\n── {step}")

def log_result(label, value, ok=None):
    marker = "✅" if ok else ("❌" if ok is False else "  ")
    print(f"  {marker} {label}: {value}")


async def step_health():
    log_section("Step 1: Health Checks")
    try:
        r = requests.get(f"{GATEWAY_BASE}/ready", timeout=5)
        d = r.json()
        ok = d.get("status") == "ready"
        for comp in ["database", "grpc_agent", "redis"]:
            cs = d.get("components", {}).get(comp, {}).get("status")
            log_result(f"  {comp}", cs, cs == "healthy")
        log_result("Gateway ready", d.get("status"), ok)
    except Exception as e:
        log_result("Gateway", str(e), False)
        return False
    try:
        r = requests.get(f"{BASE}/health", timeout=5)
        api_ok = r.json().get("status") == "healthy"
        log_result("Python API", r.json().get("status"), api_ok)
        return api_ok
    except Exception as e:
        log_result("Python API", str(e), False)
        return False


def step_auth():
    log_section("Step 2: Auth")
    for action, path in [("Login", "/api/v1/auth/login"), ("Register", "/api/v1/auth/register")]:
        try:
            payload = {"username": USERNAME, "password": PASSWORD}
            if "register" in path:
                payload.update({"email": EMAIL, "nickname": "E2E", "accepted_tos": True, "accepted_privacy": True})
            r = requests.post(f"{BASE}{path}", json=payload, timeout=10)
            d = r.json()
            if r.status_code in (200, 201) and "access_token" in d:
                log_result(action, "success", True)
                return d["access_token"], d.get("user", {}).get("id", "unknown")
        except Exception as e:
            log_result(action, str(e), False)
    return None, None


async def step_chat(token, session_id):
    log_section("Step 3: Multi-Turn Chat (new WS per turn)")

    turns = [
        ("考试咨询", "我7天后考计算机网络，零基础，怎么办？"),
        ("追问协议", "OSI七层模型是什么？能给我一个简单的记忆方法吗？"),
        ("表达困惑", "我不太理解传输层和网络层的区别，能换个方式解释吗？"),
        ("具体行动", "能给我一个7天的学习计划吗？每天2小时"),
    ]

    results = []
    for i, (name, message) in enumerate(turns):
        log_step(f"Turn {i+1}: {name}")
        t0 = time.time()
        chunks = []
        meta_keys = set()
        ttft = None
        error = None

        try:
            async with websockets.connect(
                f"{WS_URL}?token={token}",
                ping_interval=None, ping_timeout=None, close_timeout=10,
            ) as ws:
                await ws.send(json.dumps({
                    "message": message, "session_id": session_id, "chat_mode": "standard",
                }))

                while True:
                    raw = await asyncio.wait_for(ws.recv(), timeout=120.0)
                    data = json.loads(raw)
                    if ttft is None:
                        ttft = (time.time() - t0) * 1000

                    mt = data.get("type", "")

                    if mt == "delta":
                        d = data.get("delta", "") or data.get("content", "")
                        if isinstance(d, str):
                            chunks.append(d)

                    elif mt == "full_text":
                        d = data.get("full_text", "") or data.get("content", "")
                        if isinstance(d, str):
                            chunks.append(d)
                        break

                    elif mt in ("done", "stream_end", "complete"):
                        break

                    elif mt == "error":
                        error = data.get("message") or data.get("error") or "unknown"
                        break

                    if "metadata" in data:
                        meta_keys.update(data["metadata"].keys())

        except asyncio.TimeoutError:
            error = f"timeout after 120s ({len(chunks)} chunks)"
        except websockets.exceptions.ConnectionClosedError as e:
            error = f"connection closed: {str(e)[:80]}"
        except Exception as e:
            error = str(e)[:120]

        elapsed = (time.time() - t0) * 1000
        text = "".join(chunks)
        ok = len(text) > 20 and error is None

        log_result("TTFT", f"{ttft:.0f}ms" if ttft else "N/A")
        log_result("Total", f"{elapsed:.0f}ms")
        log_result("Chunks", len(chunks))
        log_result("Response", f"{len(text)} chars", ok)
        if text:
            log_result("Preview", text[:200].replace("\n", "\\n"))
        if meta_keys:
            log_result("Metadata", sorted(meta_keys))
        if error:
            log_result("Error", error, False)

        results.append({"name": name, "ok": ok, "ttft": ttft, "total_ms": elapsed,
                         "chunks": len(chunks), "len": len(text), "meta": sorted(meta_keys)})

    return results


async def main():
    print("\n" + "="*60)
    print("  SPARKLE E2E MULTI-TURN CHAT TEST v2")
    print("  WS → Go Gateway → Python gRPC → LLM (qwen-plus)")
    print("="*60)

    if not await step_health():
        print("\n❌ Health checks failed"); return 1

    token, uid = step_auth()
    if not token:
        print("\n❌ Auth failed"); return 1

    session_id = str(uuid.uuid4())
    results = await step_chat(token, session_id)

    log_section("Summary")
    passed = sum(1 for r in results if r["ok"])
    ttfts = [r["ttft"] for r in results if r["ttft"]]
    avg_ttft = sum(ttfts) / len(ttfts) if ttfts else 0
    log_result("Turns OK", f"{passed}/{len(results)}", passed == len(results))
    log_result("Avg TTFT", f"{avg_ttft:.0f}ms")
    for r in results:
        s = "✅" if r["ok"] else "❌"
        print(f"  {s} {r['name']}: {r['ttft']:.0f}ms/{r['total_ms']:.0f}ms, {r['len']} chars")

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
