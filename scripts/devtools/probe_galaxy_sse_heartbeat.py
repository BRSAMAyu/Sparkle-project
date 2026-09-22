#!/usr/bin/env python3
"""SSE-HB-VERIFY：galaxy SSE 心跳实机观察探针（一次性，wt112）。

对共享 dev 栈经 **gateway**(:8080) 注册/登录 northstar_sse_* 测试账号，
订阅 GET /api/v1/galaxy/events（Bearer 鉴权），保持**单条只读 SSE 连接**
idle 观察 N 秒（默认 360s ≥5 分钟），记录：

  1. 连接是否保持（断连次数与时间线）；
  2. `: heartbeat` 注释帧到达间隔（修复预期 ~20s）；
  3. 事件帧/其它帧计数（应≈0，纯空闲观察）。

纯观察：不发 chat、零 LLM、不写任何业务数据；断连后自动重连并计数
（复现修复前客户端静默重连行为以便对照断连频率）。

用法（栈在跑前提下，worktree 根执行）：
    python3.11 scripts/devtools/probe_galaxy_sse_heartbeat.py            # 360s
    python3.11 scripts/devtools/probe_galaxy_sse_heartbeat.py --duration 600

凭据仅写 /tmp/sse_hb_probe_creds.json（0600，收工自清，复跑即重建）；
证据 JSON 写 --evidence-out（默认 v3-output/SSE-HB-VERIFY/evidence/probe.json，
不含密码）。报告：v3-output/SSE-HB-VERIFY/REPORT.md。
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import socket
import statistics
import sys
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

GATEWAY_DEFAULT = "http://localhost:8080"
CREDS_PATH = "/tmp/sse_hb_probe_creds.json"
ACCOUNT_PREFIX = "northstar_sse_hb"
READ_TIMEOUT_S = 90  # 远大于 20s 心跳间隔；超过即视为异常静默（本身是发现）
RECONNECT_BACKOFF_S = 1.0


def _http_request(
    host: str, port: int, method: str, path: str, body: dict | None = None,
    token: str | None = None, timeout: float = 15.0,
) -> tuple[int, dict, bytes]:
    """最小 HTTP 请求（stdlib，无依赖）。返回 (status, headers, body)。"""
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    payload = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json", "Connection": "close"}
    if payload:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    conn.request(method, path, body=payload, headers=headers)
    resp = conn.getresponse()
    data = resp.read()
    hdrs = {k.lower(): v for k, v in resp.getheaders()}
    status = resp.status
    conn.close()
    return status, hdrs, data


def ensure_account(gateway: urlparse) -> tuple[str, str]:
    """注册/登录 northstar_sse_* 账号，返回 (username, access_token)。经 gateway API。"""
    # 复用 /tmp 凭据（若仍可登录）——幂等复跑
    if os.path.exists(CREDS_PATH):
        try:
            with open(CREDS_PATH) as f:
                saved = json.load(f)
            status, _, data = _http_request(
                gateway.hostname, gateway.port, "POST", "/api/v1/auth/login",
                body={"username": saved["username"], "password": saved["password"]},
            )
            if status == 200:
                tok = json.loads(data)["access_token"]
                print(f"[setup] 复用既有账号 {saved['username']}（/tmp 凭据仍有效）")
                return saved["username"], tok
        except Exception as exc:  # noqa: BLE001 — 探针容忍任何复用失败，走全新注册
            print(f"[setup] /tmp 凭据复用失败（{exc}），改用全新账号")

    username = f"{ACCOUNT_PREFIX}_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = uuid.uuid4().hex + "Aa1!"

    status, _, data = _http_request(
        gateway.hostname, gateway.port, "POST", "/api/v1/auth/register",
        body={
            "username": username, "email": email, "password": password,
            "accepted_tos": True, "accepted_privacy": True,
            "tos_version": "v1", "privacy_version": "v1", "agreed_locale": "zh-CN",
        },
    )
    if status not in (200, 201):
        raise SystemExit(f"[setup] 注册失败 HTTP {status}: {data[:300]!r}")
    print(f"[setup] 注册成功 {username}（经 gateway :{gateway.port}）")

    status, _, data = _http_request(
        gateway.hostname, gateway.port, "POST", "/api/v1/auth/login",
        body={"username": username, "password": password},
    )
    if status != 200:
        raise SystemExit(f"[setup] 登录失败 HTTP {status}: {data[:300]!r}")
    tok = json.loads(data)["access_token"]

    with open(os.open(CREDS_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
        json.dump({"username": username, "password": password}, f)
    print(f"[setup] 凭据已存 {CREDS_PATH}（0600，收工自清）")
    return username, tok


def run_probe(subscribe_url: urlparse, token: str, duration_s: float) -> dict:
    """保持单条 SSE 连接 idle 读 duration_s 秒；断连自动重连并计数。"""
    host, port = subscribe_url.hostname, subscribe_url.port
    started = time.monotonic()
    wall_started = datetime.now(timezone.utc).isoformat()

    heartbeats: list[float] = []          # 每帧 monotonic 时刻
    hb_intervals: list[float] = []        # 相邻心跳间隔
    event_frames = 0
    other_lines = 0
    total_bytes = 0
    disconnects: list[dict] = []
    connect_events: list[dict] = []
    silence_gaps: list[dict] = []         # 超过 READ_TIMEOUT 无任何字节的时段
    content_types: list[str] = []
    resp_headers_seen: list[dict] = []
    reconnect_no = 0
    last_frame_at: float | None = None

    while (time.monotonic() - started) < duration_s:
        t_connect = time.monotonic()
        connect_events.append({
            "connection_no": reconnect_no + 1,
            "at_elapsed_s": round(t_connect - started, 2),
        })
        conn = http.client.HTTPConnection(host, port, timeout=READ_TIMEOUT_S)
        try:
            conn.request("GET", "/api/v1/galaxy/events", headers={
                "Accept": "text/event-stream",
                "Authorization": f"Bearer {token}",
            })
            resp = conn.getresponse()
            ct = resp.getheader("Content-Type", "")
            content_types.append(ct)
            if len(resp_headers_seen) < 3:  # 只留前几条连接的头作证据
                resp_headers_seen.append({k: v for k, v in resp.getheaders()})
            if resp.status != 200:
                body = resp.read()[:300]
                disconnects.append({
                    "at_elapsed_s": round(time.monotonic() - started, 2),
                    "connection_no": reconnect_no + 1,
                    "reason": f"HTTP {resp.status}: {body!r}",
                })
                raise OSError(f"non-200 {resp.status}")
            print(f"[probe] 连接#{reconnect_no + 1} 建立 HTTP 200 content-type={ct!r} "
                  f"t={t_connect - started:.1f}s")
            last_frame_at = time.monotonic()

            while (time.monotonic() - started) < duration_s:
                line = resp.readline()  # 阻塞读一行；超时抛 socket.timeout
                if not line:
                    raise EOFError("server closed stream (readline empty)")
                now = time.monotonic()
                total_bytes += len(line)
                gap = now - last_frame_at if last_frame_at else 0.0
                last_frame_at = now
                text = line.decode("utf-8", "replace").rstrip("\r\n")
                if text.startswith(":"):
                    # SSE 注释帧 —— 期望 ": heartbeat"
                    if heartbeats:
                        hb_intervals.append(round(now - heartbeats[-1], 2))
                    heartbeats.append(now)
                    if gap > READ_TIMEOUT_S:
                        silence_gaps.append({
                            "before_heartbeat_no": len(heartbeats),
                            "gap_s": round(gap, 2),
                        })
                    print(f"[hb ] #{len(heartbeats):02d} t={now - started:7.1f}s "
                          f"gap={gap:5.1f}s  {text!r}")
                elif text.startswith(("event:", "data:", "id:")):
                    event_frames += 1
                    print(f"[evt] t={now - started:7.1f}s gap={gap:5.1f}s  {text[:120]!r}")
                elif text:
                    other_lines += 1
                    print(f"[???] t={now - started:7.1f}s  {text[:120]!r}")
                # 空行（帧分隔）不计数
        except (socket.timeout, TimeoutError):
            elapsed = time.monotonic() - started
            silence_gaps.append({
                "connection_no": reconnect_no + 1,
                "at_elapsed_s": round(elapsed, 2),
                "gap_s": READ_TIMEOUT_S,
                "note": "read timeout — 连接期无任何字节到达（心跳缺失?）",
            })
            disconnects.append({
                "at_elapsed_s": round(elapsed, 2),
                "connection_no": reconnect_no + 1,
                "reason": f"read timeout {READ_TIMEOUT_S}s（无字节）",
            })
            print(f"[!!!] 连接#{reconnect_no + 1} 读超时 t={elapsed:.1f}s")
        except (EOFError, OSError, http.client.HTTPException) as exc:
            elapsed = time.monotonic() - started
            disconnects.append({
                "at_elapsed_s": round(elapsed, 2),
                "connection_no": reconnect_no + 1,
                "reason": f"{type(exc).__name__}: {exc}",
            })
            print(f"[!!!] 连接#{reconnect_no + 1} 断连 t={elapsed:.1f}s ({exc})")
        finally:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
        reconnect_no += 1
        if (time.monotonic() - started) < duration_s:
            time.sleep(RECONNECT_BACKOFF_S)

    held_full = len(disconnects) == 0
    return {
        "schema": "sparkle.sse-hb.probe.v1",
        "subscribe_target": f"{subscribe_url.scheme}://{subscribe_url.hostname}:{subscribe_url.port}",
        "endpoint": "/api/v1/galaxy/events (Bearer)",
        "started_at_utc": wall_started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_s": round(time.monotonic() - started, 2),
        "connect_count": len(connect_events),
        "disconnect_count": len(disconnects),
        "connection_held_full_duration": held_full,
        "heartbeat_count": len(heartbeats),
        "heartbeat_intervals_s": hb_intervals,
        "heartbeat_gap_stats": (
            {
                "n": len(hb_intervals),
                "min": min(hb_intervals), "max": max(hb_intervals),
                "mean": round(statistics.fmean(hb_intervals), 2),
                "median": statistics.median(hb_intervals),
            } if hb_intervals else None
        ),
        "event_field_lines": event_frames,
        "other_lines": other_lines,
        "total_bytes": total_bytes,
        "silence_gaps": silence_gaps,
        "disconnect_events": disconnects,
        "connect_events": connect_events,
        "content_types_seen": sorted(set(content_types)),
        "response_headers_first_connections": resp_headers_seen,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gateway-url", default=GATEWAY_DEFAULT,
                    help="注册/登录用的 gateway 地址（默认 http://localhost:8080）")
    ap.add_argument("--subscribe-url", default=None,
                    help="SSE 订阅目标（默认与 --gateway-url 相同；对照实验可指向引擎 ：8000）")
    ap.add_argument("--duration", type=float, default=360.0,
                    help="观察时长秒（默认 360 ≥5 分钟）")
    ap.add_argument("--evidence-out", default="v3-output/SSE-HB-VERIFY/evidence/probe.json")
    args = ap.parse_args()

    gateway = urlparse(args.gateway_url)
    subscribe = urlparse(args.subscribe_url or args.gateway_url)
    print(f"[setup] 注册/登录 {args.gateway_url}；SSE 订阅 {args.subscribe_url or args.gateway_url}；"
          f"观察 {args.duration}s（单连接只读 idle）")
    username, token = ensure_account(gateway)

    t0 = time.monotonic()
    result = run_probe(subscribe, token, args.duration)
    result["account"] = username  # 只记用户名，不记密码
    result["register_gateway"] = f"{gateway.scheme}://{gateway.hostname}:{gateway.port}"

    os.makedirs(os.path.dirname(args.evidence_out) or ".", exist_ok=True)
    with open(args.evidence_out, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n[done] 证据 → {args.evidence_out}")

    hb = result["heartbeat_gap_stats"]
    print(json.dumps({
        "account": username,
        "observed_s": result["duration_s"],
        "disconnect_count": result["disconnect_count"],
        "connect_count": result["connect_count"],
        "heartbeat_count": result["heartbeat_count"],
        "heartbeat_interval_mean_s": hb and hb["mean"],
        "heartbeat_interval_minmax_s": hb and [hb["min"], hb["max"]],
        "event_field_lines": result["event_field_lines"],
        "connection_held_full_duration": result["connection_held_full_duration"],
        "wall_s": round(time.monotonic() - t0, 1),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
