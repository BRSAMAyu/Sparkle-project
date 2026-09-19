"""B-05b: probe all zhipu lane candidates through the engine's own LLM client stack.

One real API call per registry key (glm_5_1_top, glm_4_7_no_thinking, glm_4_7_thinking,
glm_4_5_air_batch, glm_4_6_batch, glm_4_7_flash_no_thinking, glm_4_7_flash_thinking,
glm_5_max, glm_4_5_air_free) using llm_router.select_specific_model +
llm_router.get_openai_client_kwargs + services.llm.providers.OpenAICompatibleProvider —
i.e. the exact request shape the engine sends (including extra_body clear_thinking).

Usage (from repo root, python3.11 with backend deps):
    cd backend && /opt/homebrew/bin/python3.11 ../scripts/devtools/probe_zhipu_lanes_b05b.py

Requires backend/.env with a valid ZHIPU_API_KEY. Read-only probe, no state mutated
(circuit breaker / health tracking are in-process only).
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

ZHIPU_KEYS = [
    "glm_5_1_top",
    "glm_4_7_no_thinking",
    "glm_4_7_thinking",
    "glm_4_5_air_batch",
    "glm_4_6_batch",
    "glm_4_7_flash_no_thinking",
    "glm_4_7_flash_thinking",
    "glm_5_max",
    "glm_4_5_air_free",
]

PROMPT = [{"role": "user", "content": "只回复两个字：在线"}]


async def probe_key(router, provider_cls, model_key: str) -> dict:
    try:
        selection = router.select_specific_model(model_key)
    except Exception as e:  # noqa: BLE001 — probe must survive selection errors
        return {"model_key": model_key, "stage": "select", "ok": False, "error": f"{type(e).__name__}: {e}"}

    client_kwargs = router.get_openai_client_kwargs(selection)
    request_kwargs = {
        k: v for k, v in client_kwargs.items()
        if k not in {"api_key", "base_url", "model", "temperature"}
    }
    provider = provider_cls(
        api_key=client_kwargs["api_key"],
        base_url=client_kwargs["base_url"],
        timeout_seconds=90.0,
    )
    t0 = time.perf_counter()
    try:
        answer = await provider.chat(
            PROMPT,
            model=client_kwargs["model"],
            temperature=client_kwargs["temperature"],
            **request_kwargs,
        )
        elapsed = round(time.perf_counter() - t0, 3)
        return {
            "model_key": model_key,
            "model_name": client_kwargs["model"],
            "base_url": client_kwargs["base_url"],
            "extra_body": request_kwargs.get("extra_body"),
            "ok": True,
            "elapsed_s": elapsed,
            "answer_head": (answer or "")[:80],
        }
    except Exception as e:  # noqa: BLE001
        elapsed = round(time.perf_counter() - t0, 3)
        status = getattr(e, "status_code", None)
        return {
            "model_key": model_key,
            "model_name": client_kwargs["model"],
            "base_url": client_kwargs["base_url"],
            "extra_body": request_kwargs.get("extra_body"),
            "ok": False,
            "elapsed_s": elapsed,
            "error_type": type(e).__name__,
            "status_code": status,
            "error_head": str(e)[:300],
        }


async def main() -> int:
    from app.core.llm_router import llm_router
    from app.services.llm.providers import OpenAICompatibleProvider

    results = []
    for key in ZHIPU_KEYS:
        r = await probe_key(llm_router, OpenAICompatibleProvider, key)
        results.append(r)
        flag = "OK " if r.get("ok") else "FAIL"
        print(f"[{flag}] {key} ({r.get('model_name')} @ {r.get('base_url')}) "
              f"elapsed={r.get('elapsed_s')}s "
              f"{'answer=' + str(r.get('answer_head'))[:40]!r}"
              if r.get("ok") else f"[{flag}] {key} status={r.get('status_code')} err={r.get('error_head', '')[:160]}",
              flush=True)
        await asyncio.sleep(0.5)

    out = Path("/tmp/b05b-probe/results_engine_lanes.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "results": results},
                              ensure_ascii=False, indent=2))
    n_ok = sum(1 for r in results if r.get("ok"))
    print(f"\n{n_ok}/{len(results)} lanes healthy; saved -> {out}")
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
