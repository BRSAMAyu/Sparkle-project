#!/usr/bin/env python3
"""Benchmark and acceptance checks for Mirofish chat bridges."""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from typing import Any

import requests
import websockets

from _acceptance_common import BASE_URL, REQUEST_TIMEOUT_SECONDS, ensure, login_with_requests


GATEWAY_HTTP_BASE = os.getenv("GATEWAY_BASE_URL", BASE_URL)
WS_BASE = os.getenv("WS_CHAT_URL", "ws://127.0.0.1:8080/ws/chat")
BENCHMARK_TIMEOUT_SECONDS = float(os.getenv("MIROFISH_BENCHMARK_TIMEOUT_SECONDS", "90"))

SCENARIOS = [
    {
        "name": "chat_to_theater",
        "message": "帮我推演一下学 Python 的路径",
        "expected_flag": "open_theater",
        "preview_key": "prediction_preview",
        "max_total_seconds": 12.0,
        "quality_check": lambda preview: len(list(preview.get("paths") or [])) >= 1,
    },
    {
        "name": "chat_to_simulation",
        "message": "我想模拟一下学习场景",
        "expected_flag": "open_simulation",
        "preview_key": "simulation_preview",
        "max_total_seconds": 12.0,
        "quality_check": lambda preview: len(list(preview.get("round_preview") or [])) >= 1,
    },
    {
        "name": "chat_to_report",
        "message": "给我生成一份最近学习表现的分析报告",
        "expected_flag": "open_report",
        "preview_key": "report_preview",
        "max_total_seconds": 25.0,
        "quality_check": lambda preview: bool(str(preview.get("markdown") or "").strip())
        and (
            len(list(preview.get("mastery") or [])) >= 1
            or len(list(preview.get("sections") or [])) >= 2
        ),
    },
]


def _merge_metadata(events: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for event in events:
        metadata = event.get("metadata")
        if isinstance(metadata, dict):
            merged.update(metadata)
    return merged


def _joined_text(events: list[dict[str, Any]]) -> str:
    full_texts = [
        str(event.get("full_text") or "").strip()
        for event in events
        if event.get("type") == "full_text" and str(event.get("full_text") or "").strip()
    ]
    if full_texts:
        return full_texts[-1]
    return "".join(
        str(event.get("delta") or "")
        for event in events
        if event.get("type") == "delta"
    ).strip()


def _parse_preview(metadata: dict[str, Any], key: str) -> dict[str, Any]:
    raw = metadata.get(key)
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    return {}


async def _collect_chat(ws: websockets.WebSocketClientProtocol) -> tuple[list[dict[str, Any]], dict[str, float]]:
    events: list[dict[str, Any]] = []
    first_event_at: float | None = None
    full_text_at: float | None = None
    started = time.monotonic()

    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=BENCHMARK_TIMEOUT_SECONDS)
        now = time.monotonic()
        if first_event_at is None:
            first_event_at = now
        data = json.loads(raw)
        events.append(data)
        if data.get("type") == "full_text" and full_text_at is None:
            full_text_at = now
        if data.get("type") == "done" or data.get("finish_reason") not in {None, "", "NULL"}:
            break
        if data.get("type") == "error":
            raise RuntimeError(f"chat failed: {data}")

    finished = time.monotonic()
    return events, {
        "first_event_seconds": round((first_event_at or finished) - started, 3),
        "full_text_seconds": round((full_text_at or finished) - started, 3),
        "total_seconds": round(finished - started, 3),
    }


def _issue_ws_ticket(token: str) -> str:
    response = requests.post(
        f"{GATEWAY_HTTP_BASE}/ws/ticket",
        headers={"Authorization": f"Bearer {token}"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    ensure(response.status_code == 200, f"issue ws ticket failed: {response.status_code} {response.text[:400]}")
    payload = response.json()
    ticket = str(payload.get("ticket") or "")
    ensure(bool(ticket), "ws ticket response missing ticket")
    return ticket


async def _run_scenario(token: str, scenario: dict[str, Any]) -> dict[str, Any]:
    ticket = _issue_ws_ticket(token)
    ws_uri = f"{WS_BASE}?ticket={ticket}"
    session_id = str(uuid.uuid4())
    request_id = f"mirofish-{uuid.uuid4().hex[:12]}"

    async with websockets.connect(
        ws_uri,
        ping_interval=None,
        ping_timeout=None,
        max_size=2**22,
    ) as ws:
        await ws.send(
            json.dumps(
                {
                    "type": "message",
                    "message": scenario["message"],
                    "session_id": session_id,
                    "request_id": request_id,
                    "chat_mode": "standard",
                    "extra_context": {"reasoning_mode": "balanced"},
                },
                ensure_ascii=False,
            ),
        )
        events, timings = await _collect_chat(ws)

    metadata = _merge_metadata(events)
    preview = _parse_preview(metadata, scenario["preview_key"])
    full_text = _joined_text(events)
    expected_flag = scenario["expected_flag"]

    ensure(metadata.get(expected_flag) == "true", f"{scenario['name']} missing flag {expected_flag}")
    ensure(bool(full_text), f"{scenario['name']} returned empty full_text")
    ensure(bool(preview), f"{scenario['name']} missing preview payload")
    ensure(
        metadata.get("bridge_execution_mode") == "short_circuit",
        f"{scenario['name']} did not use expected bridge path",
    )
    ensure(
        timings["total_seconds"] <= float(scenario["max_total_seconds"]),
        f"{scenario['name']} too slow: {timings['total_seconds']}s",
    )
    ensure(scenario["quality_check"](preview), f"{scenario['name']} quality gate failed: {preview}")

    deeplink_key = {
        "open_theater": "deep_link",
        "open_simulation": "simulation_deep_link",
        "open_report": "report_deep_link",
    }[expected_flag]

    return {
        "scenario": scenario["name"],
        "message": scenario["message"],
        "speed": timings,
        "cost": {
            "bridge_execution_mode": metadata.get("bridge_execution_mode", "unknown"),
            "bridge_cost_tier": metadata.get("bridge_cost_tier", "unknown"),
            "bridge_quality_mode": metadata.get("bridge_quality_mode", "unknown"),
        },
        "quality": {
            "preview_key": scenario["preview_key"],
            "preview_items": len(
                preview.get("paths")
                or preview.get("round_preview")
                or preview.get("mastery")
                or preview.get("highlights")
                or []
            ),
            "deeplink": metadata.get(deeplink_key),
            "response_excerpt": full_text[:120],
        },
    }


async def main() -> int:
    token = login_with_requests()
    results = []
    for scenario in SCENARIOS:
        results.append(await _run_scenario(token, scenario))

    print(json.dumps({"status": "ALL_OK", "results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
