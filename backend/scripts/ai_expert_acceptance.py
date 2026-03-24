#!/usr/bin/env python3
"""Acceptance for expert catalog, custom experts, expert teams, and live chat."""
from __future__ import annotations

import asyncio
import json
import os
import uuid

import httpx
import websockets

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
WS_URL = os.getenv("WS_CHAT_URL", "ws://127.0.0.1:8080/ws/chat")
USERNAME = os.getenv("LOCAL_SMOKE_USERNAME", "chat_test")
PASSWORD = os.getenv("LOCAL_SMOKE_PASSWORD", "Chat123456")
CHAT_TIMEOUT_SECONDS = float(os.getenv("AI_EXPERT_ACCEPTANCE_TIMEOUT_SECONDS", "180"))


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


async def _collect_chat(ws, *, timeout: float = CHAT_TIMEOUT_SECONDS) -> list[dict]:
    events: list[dict] = []
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


def _merge_metadata(events: list[dict]) -> dict:
    merged: dict = {}
    for event in events:
        metadata = event.get("metadata")
        if isinstance(metadata, dict):
            merged.update(metadata)
    return merged


def _joined_text(events: list[dict]) -> str:
    return "".join(
        (event.get("delta") or "") + (event.get("full_text") or "")
        for event in events
        if event.get("type") in {"delta", "full_text"}
    ).strip()


async def main() -> int:
    async with httpx.AsyncClient(timeout=30.0) as client:
        login = await client.post(
            f"{API_BASE}/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        catalog_resp = await client.get(f"{API_BASE}/multi-agent/catalog", headers=headers)
        catalog_resp.raise_for_status()
        catalog = catalog_resp.json()
        _assert(len(catalog.get("experts", [])) >= 8, "official expert catalog too small")
        _assert(len(catalog.get("model_options", [])) >= 8, "model options missing")
        _assert(any(item.get("model_policy") for item in catalog.get("experts", [])), "expert model policies missing")

        custom_expert_resp = await client.post(
            f"{API_BASE}/multi-agent/custom-experts",
            headers=headers,
            json={
                "name": f"自定义批判专家-{uuid.uuid4().hex[:6]}",
                "description": "强调反例、风险和边界条件",
                "system_prompt": "你是一位批判性分析专家。回答时先下判断，再补两个边界条件，最后给风险提醒。避免空话。",
                "base_expert_id": "deep_analyst",
                "preferred_model_key": "mimo_pro",
                "reasoning_mode": "deep",
            },
        )
        custom_expert_resp.raise_for_status()
        custom_expert = custom_expert_resp.json()
        custom_id = custom_expert["id"]

        custom_team_resp = await client.post(
            f"{API_BASE}/multi-agent/custom-teams",
            headers=headers,
            json={
                "name": f"验收团队-{uuid.uuid4().hex[:6]}",
                "description": "深度分析 + 时间导师 + 自定义批判专家",
                "collaboration_mode": "parallel",
                "expert_ids": ["deep_analyst", "time_tutor", custom_id],
                "answer_expert_ids": [custom_id, "deep_analyst"],
            },
        )
        custom_team_resp.raise_for_status()
        custom_team = custom_team_resp.json()

    ws_uri = f"{WS_URL}?token={token}"

    async with websockets.connect(ws_uri, ping_interval=None, ping_timeout=None, max_size=2**22) as ws:
        await ws.send(json.dumps({
            "type": "message",
            "message": "请分析我复习离散数学时只记结论不看证明会有什么风险。",
            "session_id": f"explicit-expert-{uuid.uuid4().hex[:8]}",
            "chat_mode": f"expert::{custom_id}",
        }, ensure_ascii=False))
        explicit_events = await _collect_chat(ws)

    team_mode = "team::" + json.dumps(
        {
            "agents": ["deep_analyst", "time_tutor", custom_id],
            "final_agents": [custom_id, "deep_analyst"],
            "mode": "parallel",
            "label": custom_team["name"],
            "team_id": custom_team["id"],
        },
        ensure_ascii=False,
    )
    async with websockets.connect(ws_uri, ping_interval=None, ping_timeout=None, max_size=2**22) as ws:
        await ws.send(json.dumps({
            "type": "message",
            "message": "我还有10天考试，离散数学总是重结论轻证明，请给我兼顾理解和冲刺的方案。",
            "session_id": f"expert-team-{uuid.uuid4().hex[:8]}",
            "chat_mode": team_mode,
        }, ensure_ascii=False))
        team_events = await _collect_chat(ws)

    explicit_meta = _merge_metadata(explicit_events)
    team_meta = _merge_metadata(team_events)
    explicit_text = _joined_text(explicit_events)
    team_text = _joined_text(team_events)

    _assert(explicit_text != "", "explicit custom expert returned empty text")
    _assert(team_text != "", "custom team returned empty text")
    _assert(custom_id in str(explicit_meta.get("selected_experts") or ""), "explicit chat missing selected_experts")
    _assert(custom_id in str(team_meta.get("selected_experts") or ""), "team chat missing selected_experts")
    _assert("deep_analyst" in str(team_meta.get("answer_experts") or ""), "team chat missing answer_experts")
    _assert(custom_id in str(team_meta.get("answer_experts") or ""), "team chat missing custom answer expert")

    print(json.dumps({
        "status": "ALL_OK",
        "official_experts": len(catalog.get("experts", [])),
        "model_options": len(catalog.get("model_options", [])),
        "custom_expert_id": custom_id,
        "custom_team_id": custom_team["id"],
        "explicit_selected_experts": explicit_meta.get("selected_experts"),
        "team_selected_experts": team_meta.get("selected_experts"),
        "team_answer_experts": team_meta.get("answer_experts"),
        "explicit_text_preview": explicit_text[:160],
        "team_text_preview": team_text[:160],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
