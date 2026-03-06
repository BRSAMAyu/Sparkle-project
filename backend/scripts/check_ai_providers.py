#!/usr/bin/env python3
"""Probe every configured AI provider with a real request and fail on any blocking issue."""
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from typing import Awaitable, Callable

import httpx
import websockets
from openai import AsyncOpenAI

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.services.stt.providers.xunfei_provider import XunFeiProvider


@dataclass
class ProbeResult:
    name: str
    ok: bool
    detail: str
    category: str


async def _probe_openai_compatible(
    *, name: str, base_url: str, api_key: str, model: str, prompt: str
) -> ProbeResult:
    if not api_key:
        return ProbeResult(name, False, "missing api key", "config")
    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30.0)
        resp = await client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        content = (resp.choices[0].message.content or "").strip()
        if not content:
            return ProbeResult(name, False, "empty response", "provider")
        return ProbeResult(name, True, content[:120], "ok")
    except Exception as exc:  # noqa: BLE001
        return ProbeResult(name, False, f"{type(exc).__name__}: {exc}", "provider")


async def _probe_mimo() -> ProbeResult:
    if not settings.XIAOMI_MIMO_API_KEY:
        return ProbeResult("mimo", False, "missing api key", "config")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.XIAOMI_MIMO_BASE_URL.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.XIAOMI_MIMO_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.XIAOMI_CHAT_MODEL,
                    "messages": [{"role": "user", "content": "请只回复：MIMO正常"}],
                    "temperature": 0,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if not content:
            return ProbeResult("mimo", False, json.dumps(data, ensure_ascii=False)[:200], "provider")
        return ProbeResult("mimo", True, content[:120], "ok")
    except Exception as exc:  # noqa: BLE001
        return ProbeResult("mimo", False, f"{type(exc).__name__}: {exc}", "provider")


async def _probe_xunfei() -> ProbeResult:
    if not (settings.XUNFEI_APP_ID and settings.XUNFEI_API_KEY and settings.XUNFEI_API_SECRET):
        return ProbeResult("xunfei", False, "missing app/key/secret", "config")
    provider = XunFeiProvider()
    try:
        ws_url = provider._generate_auth_url()
        async with websockets.connect(ws_url, open_timeout=10, close_timeout=3):
            await asyncio.sleep(0.2)
        return ProbeResult("xunfei", True, "websocket auth handshake succeeded", "ok")
    except Exception as exc:  # noqa: BLE001
        return ProbeResult("xunfei", False, f"{type(exc).__name__}: {exc}", "provider")


async def main() -> int:
    probes: list[Callable[[], Awaitable[ProbeResult]]] = [
        lambda: _probe_openai_compatible(
            name="dashscope_qwen",
            base_url=settings.DASHSCOPE_BASE_URL_COMPATIBLE,
            api_key=settings.DASHSCOPE_API_KEY,
            model=settings.DASHSCOPE_CHAT_MODEL,
            prompt="请只回复：QWEN正常",
        ),
        lambda: _probe_openai_compatible(
            name="deepseek",
            base_url=settings.DEEPSEEK_BASE_URL,
            api_key=settings.DEEPSEEK_API_KEY,
            model=settings.DEEPSEEK_CHAT_MODEL,
            prompt="请只回复：DeepSeek正常",
        ),
        lambda: _probe_openai_compatible(
            name="glm",
            base_url=settings.ZHIPU_BASE_URL,
            api_key=settings.ZHIPU_API_KEY,
            model=settings.ZHIPU_CHAT_MODEL,
            prompt="请只回复：GLM正常",
        ),
        lambda: _probe_openai_compatible(
            name="siliconflow_translate",
            base_url=settings.HUNYUAN_BASE_URL,
            api_key=settings.HUNYUAN_API_KEY or settings.SILICONFLOW_API_KEY,
            model=settings.HUNYUAN_TRANSLATE_MODEL,
            prompt="Translate 'Hello, world!' to Simplified Chinese. Return translation only.",
        ),
        _probe_mimo,
        _probe_xunfei,
    ]

    results = await asyncio.gather(*(probe() for probe in probes))
    failed = [item for item in results if not item.ok]

    for item in results:
        status = "OK" if item.ok else "FAIL"
        print(f"[{status}] {item.name}: {item.detail}")

    if failed:
        print("\nBlocking AI provider failures detected:")
        for item in failed:
            print(f"- {item.name} ({item.category}): {item.detail}")
        return 1

    print("\nAll configured AI providers passed live probes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
