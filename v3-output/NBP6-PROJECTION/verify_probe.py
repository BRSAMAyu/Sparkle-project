#!/usr/bin/env python3
"""NBP-6 活栈验证探针：WS 声明 fact → 今日面板投影延迟测量。

用法（栈在跑前提下，gateway :8080 可达）：
    python3 verify_probe.py                          # 默认 127.0.0.1:8080
    python3 verify_probe.py --host 127.0.0.1 --port 8080
    python3 verify_probe.py --assert-under 5         # 投影延迟 >5s 时退出码 1

流程：注册/登录（经 gateway，凭据复用 /tmp/nbp6_probe_creds.json）
  → WS /ws/chat 发一句明示事实（「…期末考试在 7 天后」，带唯一 marker）
  → 回合终止帧到达后立即轮询 GET /api/v1/memory/episodic（账本读面，零缓存直查）
  → 输出：回合耗时、投影延迟（turn_end→可见 / send→可见）、判定。

验收口径（NBP-6）：修复后投影延迟应为亚秒~秒级（写账在轮次收尾即落库，
读面无缓存）；修复前为 30-90s（LLM 抽取阻塞 declared-fact 提升，
NORTHSTAR-LOOP3 实测带内 51.2s）。

依赖：stdlib + websocket-client（WS 拨号）。凭据文件 0600，收工自清。
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import sys
import time
import uuid
from typing import Any
from urllib.parse import urlparse

import websocket

CREDS_PATH = "/tmp/nbp6_probe_creds.json"


def _http_request(
    host: str, port: int, method: str, path: str, body: dict | None = None,
    token: str | None = None, timeout: float = 15.0,
) -> tuple[int, dict, bytes]:
    """最小 HTTP 请求（stdlib）。返回 (status, headers, body)。"""
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


def ensure_account(host: str, port: int) -> tuple[str, str]:
    """注册/登录探针账号，返回 (username, access_token)。凭据复用 /tmp。"""
    if os.path.exists(CREDS_PATH):
        try:
            with open(CREDS_PATH) as f:
                saved = json.load(f)
            status, _, data = _http_request(
                host, port, "POST", "/api/v1/auth/login",
                body={"username": saved["username"], "password": saved["password"]},
            )
            if status == 200:
                tok = json.loads(data)["access_token"]
                print(f"[setup] 复用既有账号 {saved['username']}")
                return saved["username"], tok
        except Exception as exc:  # noqa: BLE001 — 复用失败走全新注册
            print(f"[setup] /tmp 凭据复用失败（{exc}），改用全新账号")

    username = f"nbp6_probe_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = uuid.uuid4().hex + "Aa1!"

    status, _, data = _http_request(
        host, port, "POST", "/api/v1/auth/register",
        body={
            "username": username, "email": email, "password": password,
            "accepted_tos": True, "accepted_privacy": True,
            "tos_version": "v1", "privacy_version": "v1", "agreed_locale": "zh-CN",
        },
    )
    if status not in (200, 201):
        raise SystemExit(f"[setup] 注册失败 HTTP {status}: {data[:300]!r}")
    print(f"[setup] 注册成功 {username}（经 gateway :{port}）")

    status, _, data = _http_request(
        host, port, "POST", "/api/v1/auth/login",
        body={"username": username, "password": password},
    )
    if status != 200:
        raise SystemExit(f"[setup] 登录失败 HTTP {status}: {data[:300]!r}")
    tok = json.loads(data)["access_token"]

    with open(os.open(CREDS_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
        json.dump({"username": username, "password": password}, f)
    print(f"[setup] 凭据已存 {CREDS_PATH}（0600）")
    return username, tok


def run_ws_turn(host: str, port: int, token: str, message: str, *, read_timeout_s: float = 180.0) -> dict:
    """WS 发一句声明 fact，读到终止帧为止。返回计时与帧统计。"""
    session_id = str(uuid.uuid4())
    url = f"ws://{host}:{port}/ws/chat"
    t0 = time.monotonic()
    conn = websocket.create_connection(
        url,
        timeout=read_timeout_s,
        header=[f"Authorization: Bearer {token}"],
    )
    conn.send(json.dumps({"message": message, "session_id": session_id}))
    t_send = time.monotonic()

    frame_types: list[str] = []
    turn_ended = False
    try:
        while not turn_ended:
            raw = conn.recv()
            if not raw:
                break
            frame = json.loads(raw)
            ftype = str(frame.get("type") or frame.get("status_update", {}).get("state") or "?")
            frame_types.append(ftype)
            # 终止形态：full_text+STOP（快交互）或 meta（流式收尾）。
            if ftype == "full_text" and str(frame.get("finish_reason")) == "STOP":
                turn_ended = True
            if ftype == "meta":
                turn_ended = True
            if ftype in ("error", "stream_error"):
                raise SystemExit(f"[ws] 错误帧：{str(frame)[:300]}")
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass
    t_end = time.monotonic()
    if not turn_ended:
        raise SystemExit(f"[ws] 未收到终止帧（帧型序列 {frame_types[-10:]}）")
    return {
        "session_id": session_id,
        "t_send": t_send,
        "t_turn_end": t_end,
        "turn_seconds": round(t_end - t_send, 2),
        "frame_types_tail": frame_types[-10:],
    }


def poll_ledger_for_marker(
    host: str, port: int, token: str, marker: str,
    *, t_turn_end: float, t_send: float, timeout_s: float, poll_interval_s: float,
) -> dict | None:
    """立即轮询 /api/v1/memory/episodic 直到 marker 事实可见或超时。"""
    polls = 0
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        polls += 1
        status, _, data = _http_request(
            host, port, "GET", "/api/v1/memory/episodic?limit=50", token=token,
        )
        if status == 200:
            payload = json.loads(data)
            for item in payload.get("items", []):
                if marker in str(item.get("summary") or ""):
                    t_seen = time.monotonic()
                    return {
                        "polls": polls,
                        "latency_from_turn_end_s": round(t_seen - t_turn_end, 2),
                        "latency_from_send_s": round(t_seen - t_send, 2),
                        "item_id": item.get("id"),
                        "due_at": item.get("due_at"),
                        "source_lane": item.get("source_lane"),
                    }
        else:
            print(f"[poll] 账本读面 HTTP {status}（第 {polls} 次）")
        time.sleep(poll_interval_s)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--timeout-s", type=float, default=180.0, help="投影可见的轮询上限")
    parser.add_argument("--poll-interval-s", type=float, default=0.5)
    parser.add_argument("--assert-under", type=float, default=None,
                        help="投影延迟（自回合终止）超过该秒数时退出码 1（验收判据）")
    args = parser.parse_args()

    gateway = urlparse(f"http://{args.host}:{args.port}")
    _, token = ensure_account(gateway.hostname, gateway.port)

    marker = f"量子引力动力学{uuid.uuid4().hex[:6]}"
    message = f"提醒一下：我有一门 {marker} 期末考试在 7 天后，目标 85 分。"
    print(f"[probe] 声明句：{message}")

    turn = run_ws_turn(gateway.hostname, gateway.port, token, message)
    print(f"[ws] 回合完成：{turn['turn_seconds']}s（帧尾 {turn['frame_types_tail']}）")

    # 回合终止帧到达 → 立即开始轮询（零退避），这就是用户打开今日面板的时刻。
    result = poll_ledger_for_marker(
        gateway.hostname, gateway.port, token, marker,
        t_turn_end=turn["t_turn_end"], t_send=turn["t_send"],
        timeout_s=args.timeout_s, poll_interval_s=args.poll_interval_s,
    )

    summary: dict[str, Any] = {
        "schema": "sparkle.nbp6.projection-latency.v1",
        "marker": marker,
        "turn_seconds": turn["turn_seconds"],
        "projection": result,
        "verdict": None,
    }
    if result is None:
        summary["verdict"] = f"fail: {args.timeout_s}s 内账本未见 marker 事实"
    else:
        latency = result["latency_from_turn_end_s"]
        print(
            f"[result] 投影延迟：turn_end→可见 {latency}s"
            f"（send→可见 {result['latency_from_send_s']}s，轮询 {result['polls']} 次）"
        )
        print(f"[result] 事实项：id={result['item_id']} due_at={result['due_at']}")
        if args.assert_under is not None:
            summary["verdict"] = (
                "pass" if latency < args.assert_under
                else f"fail: 投影延迟 {latency}s ≥ 阈值 {args.assert_under}s"
            )
        else:
            summary["verdict"] = "observed"

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    try:
        os.remove(CREDS_PATH)
        print("[cleanup] 已删除 /tmp 凭据文件")
    except OSError:
        pass
    return 1 if (args.assert_under is not None and summary["verdict"] != "pass") else 0


if __name__ == "__main__":
    sys.exit(main())
