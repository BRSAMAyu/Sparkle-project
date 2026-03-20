#!/usr/bin/env python3
"""Real multi-turn AI chat acceptance covering standard chat, mode switching, history and omnibar."""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from typing import Any

import httpx
import websockets

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
GATEWAY_BASE = os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:8080/api/v1")
WS_URL = os.getenv("WS_CHAT_URL", "ws://127.0.0.1:8080/ws/chat")
USERNAME = os.getenv("LOCAL_SMOKE_USERNAME", "chat_test")
PASSWORD = os.getenv("LOCAL_SMOKE_PASSWORD", "Chat123456")
CHAT_TIMEOUT_SECONDS = float(os.getenv("AI_CHAT_ACCEPTANCE_TIMEOUT_SECONDS", "180"))
STANDARD_TURN_MAX_SECONDS = float(os.getenv("AI_CHAT_STANDARD_TURN_MAX_SECONDS", "25"))
DEEP_ANALYSIS_MAX_SECONDS = float(os.getenv("AI_CHAT_DEEP_ANALYSIS_MAX_SECONDS", "45"))
STUDY_PLAN_MAX_SECONDS = float(os.getenv("AI_CHAT_STUDY_PLAN_MAX_SECONDS", "60"))
ERROR_DIAGNOSIS_MAX_SECONDS = float(os.getenv("AI_CHAT_ERROR_DIAGNOSIS_MAX_SECONDS", "60"))


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _has_standard_context_leak(text: str) -> bool:
    lowered = (text or "").lower()
    leak_markers = (
        "根据你的计划",
        "你之前提到",
        "今日专注",
        "番茄钟次数",
        "当前有 2 个计划",
        "当前有2个计划",
    )
    return any(marker.lower() in lowered for marker in leak_markers)


async def _collect_chat(
    ws: websockets.WebSocketClientProtocol,
    *,
    timeout: float = CHAT_TIMEOUT_SECONDS,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    while True:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        except websockets.exceptions.ConnectionClosedOK:
            if any(event.get("type") in {"full_text", "delta"} for event in events):
                return events
            raise
        data = json.loads(raw)
        events.append(data)
        if data.get("type") == "done":
            return events
        if data.get("finish_reason") not in {None, "", "NULL"}:
            return events
        if data.get("type") == "error":
            raise RuntimeError(f"chat failed: {data}")


def _joined_text(events: list[dict[str, Any]]) -> str:
    return "".join(
        (event.get("delta") or "") + (event.get("full_text") or "")
        for event in events
        if event.get("type") in {"delta", "full_text"}
    ).strip()


def _merge_metadata(events: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for event in events:
        metadata = event.get("metadata")
        if isinstance(metadata, dict):
            merged.update(metadata)
    return merged


def _has_tool_or_widget_signal(events: list[dict[str, Any]]) -> bool:
    for event in events:
        if event.get("type") in {"tool_result", "widget", "action_card"}:
            return True
        metadata = event.get("metadata")
        if isinstance(metadata, dict):
            if metadata.get("tool_result") or metadata.get("widgets") or metadata.get("tool_calls"):
                return True
    return False


async def _send_ws_message(
    token: str,
    *,
    session_id: str,
    message: str,
    chat_mode: str = "standard",
    request_id: str | None = None,
) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    req_id = request_id or f"req-{uuid.uuid4().hex[:12]}"
    ws_uri = f"{WS_URL}?token={token}"
    started_at = time.monotonic()
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
                    "message": message,
                    "session_id": session_id,
                    "request_id": req_id,
                    "chat_mode": chat_mode,
                },
                ensure_ascii=False,
            ),
        )
        events = await _collect_chat(ws)
    metadata = _merge_metadata(events)
    metadata["elapsed_seconds"] = round(time.monotonic() - started_at, 3)
    return events, _joined_text(events), metadata


async def main() -> int:
    async with httpx.AsyncClient(timeout=45.0) as client:
        login = await client.post(
            f"{API_BASE}/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        session_id = str(uuid.uuid4())

        turn1_events, turn1_text, turn1_meta = await _send_ws_message(
            token,
            session_id=session_id,
            message="请用三条简洁要点告诉我番茄钟学习法是什么。",
            chat_mode="standard",
        )
        _assert(turn1_text != "", "standard turn 1 returned empty text")
        _assert(any(e.get("type") == "done" or e.get("finish_reason") for e in turn1_events), "standard turn 1 did not terminate cleanly")
        _assert(turn1_meta["elapsed_seconds"] <= STANDARD_TURN_MAX_SECONDS, f"standard turn 1 too slow: {turn1_meta['elapsed_seconds']}s")
        _assert(not _has_standard_context_leak(turn1_text), "standard turn 1 leaked unrelated personal plan/focus context")

        turn2_events, turn2_text, turn2_meta = await _send_ws_message(
            token,
            session_id=session_id,
            message="基于刚才的解释，再给我一个今天就能执行的 25 分钟开始动作。",
            chat_mode="standard",
        )
        _assert(turn2_text != "", "standard turn 2 returned empty text")
        _assert(turn2_text != turn1_text, "standard turn 2 duplicated previous answer")
        _assert(
            turn2_meta["elapsed_seconds"] <= STANDARD_TURN_MAX_SECONDS,
            f"standard turn 2 too slow: {turn2_meta['elapsed_seconds']}s",
        )
        _assert(not _has_standard_context_leak(turn2_text), "standard turn 2 leaked unrelated personal plan/focus context")

        deep_events, deep_text, deep_meta = await _send_ws_message(
            token,
            session_id=session_id,
            message="请用类比和反例解释栈和队列的区别，并告诉我最容易混淆的点。",
            chat_mode="deep_analysis",
        )
        _assert(deep_text != "", "deep_analysis returned empty text")
        _assert(deep_meta["elapsed_seconds"] <= DEEP_ANALYSIS_MAX_SECONDS, f"deep_analysis too slow: {deep_meta['elapsed_seconds']}s")

        plan_session = str(uuid.uuid4())
        plan_events, plan_text, plan_meta = await _send_ws_message(
            token,
            session_id=plan_session,
            message="我还有 7 天准备 Python 测验，请结合我现在的计划和任务，给我一个可执行的学习任务拆解。",
            chat_mode="study_plan",
        )
        _assert(plan_text != "", "study_plan returned empty text")
        _assert(plan_meta["elapsed_seconds"] <= STUDY_PLAN_MAX_SECONDS, f"study_plan too slow: {plan_meta['elapsed_seconds']}s")

        diagnosis_events, diagnosis_text, diagnosis_meta = await _send_ws_message(
            token,
            session_id=str(uuid.uuid4()),
            message="为什么我总是把 TCP 三次握手和四次挥手的顺序记反？请帮我诊断常见误区。",
            chat_mode="error_diagnosis",
        )
        _assert(diagnosis_text != "", "error_diagnosis returned empty text")
        _assert(
            diagnosis_meta["elapsed_seconds"] <= ERROR_DIAGNOSIS_MAX_SECONDS,
            f"error_diagnosis too slow: {diagnosis_meta['elapsed_seconds']}s",
        )

        sessions_resp = await client.get(f"{GATEWAY_BASE}/chat/sessions", headers=headers)
        sessions_resp.raise_for_status()
        sessions = sessions_resp.json()
        _assert(any(str(item.get("id") or item.get("session_id")) == session_id for item in sessions), "recent sessions missing standard session")

        history_resp = await client.get(
            f"{GATEWAY_BASE}/chat/history/{session_id}",
            headers=headers,
            params={"limit": 20, "offset": 0},
        )
        history_resp.raise_for_status()
        history = history_resp.json()
        _assert(len(history) >= 4, "conversation history too short after multi-turn chat")
        _assert(any(msg.get("role") == "assistant" and msg.get("content") for msg in history), "conversation history missing assistant replies")

        omnibar_resp = await client.post(
            f"{API_BASE}/omnibar/dispatch",
            headers=headers,
            json={"text": "提醒我今晚复习线性代数 30 分钟"},
        )
        omnibar_resp.raise_for_status()
        omnibar_data = omnibar_resp.json()
        _assert(omnibar_data.get("action_type") == "TASK", f"omnibar should create a task for reminder input, got {omnibar_data.get('action_type')}")
        _assert("data" in omnibar_data, "omnibar missing data payload")

    print(
        json.dumps(
            {
                "status": "ALL_OK",
                "session_id": session_id,
                "standard_turn_1_preview": turn1_text[:120],
                "standard_turn_1_seconds": turn1_meta["elapsed_seconds"],
                "standard_turn_2_preview": turn2_text[:120],
                "standard_turn_2_seconds": turn2_meta["elapsed_seconds"],
                "deep_analysis_preview": deep_text[:120],
                "deep_analysis_seconds": deep_meta["elapsed_seconds"],
                "study_plan_preview": plan_text[:120],
                "study_plan_seconds": plan_meta["elapsed_seconds"],
                "error_diagnosis_preview": diagnosis_text[:120],
                "error_diagnosis_seconds": diagnosis_meta["elapsed_seconds"],
                "history_count": len(history),
                "recent_sessions_count": len(sessions),
                "study_plan_has_tool_signal": _has_tool_or_widget_signal(plan_events),
                "study_plan_selected_experts": plan_meta.get("selected_experts"),
                "deep_analysis_selected_experts": deep_meta.get("selected_experts"),
                "error_diagnosis_selected_experts": diagnosis_meta.get("selected_experts"),
                "standard_selected_experts": turn1_meta.get("selected_experts"),
                "omnibar_action_type": omnibar_data.get("action_type"),
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
