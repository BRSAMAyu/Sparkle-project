"""M-09 real-model probe — 5 key cases x 5 repeats, hard-capped at 25 calls.

The deterministic suite grades the memory chain (surfaced face + rendered
prompt). This probe verifies the ANSWER layer on top of the same chain: for
each key case, the real surfaced context is rendered into a production-shaped
prompt and a real model answers; the answer is graded lexically against the
case's ``real_model.must_mention`` / ``must_not_mention`` markers. Five
repeats measure stability (per-case pass variance + majority verdict).

Budget discipline (card requirement):
- EXACTLY 5 key cases x 5 repeats = 25 calls maximum; ``_BUDGET`` refuses
  anything beyond.
- The API key is read at RUNTIME from the environment or the main repo's
  ``backend/.env`` (main repo is read-only for this worker). The key is never
  written to any file, log, or result payload — only ``has_key`` booleans and
  the model name are recorded.
- Results (answers, verdicts, latencies, model name) are recorded WITHOUT the
  key and without environment dumps.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from pathlib import Path
from typing import Any

from .harness import EvalEnvironment, run_case
from .memory_eval_schema import Case, load_suite

REAL_MODEL_REPEATS = 5
REAL_MODEL_MAX_CALLS = 25
DEFAULT_MODEL = "qwen3.8-flash"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MAIN_REPO_ENV = Path("/Users/brsama/code/GitHub/Sparkle-project/backend/.env")

_SYSTEM_PROMPT = (
    "你是 Sparkle 星火，一个大学生的 AI 学习伙伴。根据下面提供的用户上下文回答用户的问题。"
    "如果上下文里没有相关信息，就正常回答，不要编造用户没有说过的事。回答用中文。"
)


def _load_api_key() -> str | None:
    """Runtime-only key resolution: env first, then the read-only main-repo
    .env. NEVER returns through logs/results — caller holds it in memory."""
    key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("LLM_API_KEY")
    if key:
        return key.strip()
    if MAIN_REPO_ENV.is_file():
        try:
            for line in MAIN_REPO_ENV.read_text(encoding="utf-8").splitlines():
                match = re.match(r"^\s*(DASHSCOPE_API_KEY|LLM_API_KEY)\s*=\s*(.+?)\s*$", line)
                if match and match.group(2).strip():
                    return match.group(2).strip()
        except OSError:
            return None
    return None


class _CallBudget:
    def __init__(self, limit: int = REAL_MODEL_MAX_CALLS):
        self.limit = limit
        self.used = 0

    def take(self) -> None:
        if self.used >= self.limit:
            raise RuntimeError(f"real-model call budget exhausted ({self.limit}); the M-09 card caps real calls at 25")
        self.used += 1


async def _chat_once(client: Any, model: str, prompt: str, budget: _CallBudget) -> dict[str, Any]:
    budget.take()
    started = time.monotonic()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        answer = (response.choices[0].message.content or "").strip()
        return {
            "ok": True,
            "answer": answer,
            "latency_s": round(time.monotonic() - started, 2),
        }
    except Exception as exc:  # noqa: BLE001 — record failure, never crash the probe
        return {
            "ok": False,
            "answer": "",
            "latency_s": round(time.monotonic() - started, 2),
            "error": f"{type(exc).__name__}",
        }


def _build_probe_prompt(rendered_context: str, query: str) -> str:
    if rendered_context.strip():
        return f"【用户上下文】\n{rendered_context.strip()}\n\n【用户问题】\n{query}"
    return f"【用户问题】\n{query}"


def _grade_answer(answer: str, case: Case) -> dict[str, Any]:
    mentioned = [m for m in case.real_model.must_mention if m in answer]
    forbidden_hits = [m for m in case.real_model.must_not_mention if m in answer]
    return {
        "passed": len(mentioned) == len(case.real_model.must_mention) and not forbidden_hits,
        "must_mention_hits": mentioned,
        "must_not_mention_hits": forbidden_hits,
    }


async def run_real_model_probe(out_path: Path | None = None) -> dict[str, Any]:
    from openai import AsyncOpenAI

    api_key = _load_api_key()
    personas, cases = load_suite()
    key_cases = [c for c in cases if c.real_model.key_case]
    result: dict[str, Any] = {
        "probe_version": "m09-real-model.v1",
        "model": os.environ.get("M09_REAL_MODEL", DEFAULT_MODEL),
        "base_url": os.environ.get("M09_REAL_BASE_URL", DEFAULT_BASE_URL),
        "has_key": bool(api_key),
        "key_cases_expected": 5,
        "repeats": REAL_MODEL_REPEATS,
        "max_calls": REAL_MODEL_MAX_CALLS,
        "calls_used": 0,
        "cases": [],
    }
    if not api_key:
        result["error"] = "no API key available (env DASHSCOPE_API_KEY / main-repo backend/.env)"
        return result
    if len(key_cases) != 5:
        result["error"] = f"expected exactly 5 key cases, found {len(key_cases)}"
        return result

    client = AsyncOpenAI(api_key=api_key, base_url=result["base_url"])
    budget = _CallBudget()
    env = EvalEnvironment()
    try:
        for case in key_cases:
            outcome = await run_case(env, case)
            if outcome.error or outcome.with_memory is None:
                result["cases"].append({"case_id": case.case_id, "error": outcome.error or "missing probe"})
                continue
            prompt = _build_probe_prompt(outcome.with_memory.rendered_prompt, case.probe["query"])
            runs = []
            for repeat in range(REAL_MODEL_REPEATS):
                call = await _chat_once(client, result["model"], prompt, budget)
                graded = _grade_answer(call["answer"], case) if call["ok"] else {"passed": False}
                runs.append({"repeat": repeat + 1, **call, **graded})
            passes = sum(1 for r in runs if r["passed"])
            majority_pass = passes * 2 > len(runs)
            result["cases"].append(
                {
                    "case_id": case.case_id,
                    "dimension": case.dimension,
                    "probe_query": case.probe["query"],
                    "prompt_chars": len(prompt),
                    "runs": runs,
                    "pass_count": passes,
                    "majority_pass": majority_pass,
                    "stability": round(passes / len(runs), 3),
                }
            )
    finally:
        await env.dispose()
        result["calls_used"] = budget.used
    result["majority_all_pass"] = bool(result.get("cases")) and all(
        c.get("majority_pass") for c in result["cases"] if "runs" in c
    )
    if out_path is not None:
        out_path.write_text(__import__("json").dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    import json
    import sys

    report = asyncio.run(run_real_model_probe())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report.get("majority_all_pass") else 1)
