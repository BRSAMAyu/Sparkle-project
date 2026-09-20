"""E-04 real-model probe — 三面 key case × 2 repeats，预算硬顶。

预算纪律（卡面红线）：每面 ≤20 次、三面合计 ≤60 次；``_CallBudget`` 硬限
拒绝超额。key 来自 env（DASHSCOPE_API_KEY/LLM_API_KEY）或主仓
``backend/.env``（主仓只读）；key 永不写入任何文件/日志/结果——产物只含
``has_key`` 布尔与模型名（M-09 同款纪律）。

调用形态镜像生产：semantic-tier 通道经 chat_json（无 response_format，
JSON 稳定性由 prompt+生产解析器承担；temperature 0.3，extractor 0.0），
qwen3.8-flash（B-05 实测可用形态：enable_thinking=false，低延迟分类通道）。
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from pathlib import Path
from typing import Any

from .ai_face_schema import (
    REAL_MODEL_MAX_CALLS_PER_FACE,
    REAL_MODEL_MAX_CALLS_TOTAL,
    REAL_MODEL_REPEATS,
    Case,
    load_suite,
)
from .faces import ADAPTERS, FACE_TEMPERATURES, RuleView, live_prompts
from .grading import CaseVerdict, aggregate, grade_raw_completion
from .prompt_registry import sha256_text

DEFAULT_MODEL = "qwen3.8-flash"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MAIN_REPO_ENV = Path("/Users/brsama/code/GitHub/Sparkle-project/backend/.env")


def _load_api_key() -> str | None:
    """Runtime-only key resolution（M-09 同款）：env 优先，其次只读主仓 .env。"""
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
    def __init__(self) -> None:
        self.per_face: dict[str, int] = {}
        self.total = 0
        self.ledger: list[dict[str, Any]] = []

    def take(self, face: str, case_id: str, repeat: int) -> None:
        used_face = self.per_face.get(face, 0)
        if used_face >= REAL_MODEL_MAX_CALLS_PER_FACE:
            raise RuntimeError(f"per-face budget exhausted ({face}: {used_face}/{REAL_MODEL_MAX_CALLS_PER_FACE})")
        if self.total >= REAL_MODEL_MAX_CALLS_TOTAL:
            raise RuntimeError(f"total call budget exhausted ({self.total}/{REAL_MODEL_MAX_CALLS_TOTAL})")
        self.per_face[face] = used_face + 1
        self.total += 1

    def record(self, face: str, case_id: str, repeat: int, *, ok: bool, latency_s: float) -> None:
        self.ledger.append(
            {"face": face, "case_id": case_id, "repeat": repeat, "ok": ok, "latency_s": latency_s}
        )


async def _chat_once(
    client: Any,
    *,
    model: str,
    system_prompt: str,
    user_content: str | None,
    temperature: float,
    budget: _CallBudget,
    face: str,
    case_id: str,
    repeat: int,
) -> dict[str, Any]:
    budget.take(face, case_id, repeat)
    started = time.monotonic()
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if user_content is not None:
        messages.append({"role": "user", "content": user_content})
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            extra_body={"enable_thinking": False},
        )
        answer = (response.choices[0].message.content or "").strip()
        latency = round(time.monotonic() - started, 2)
        budget.record(face, case_id, repeat, ok=True, latency_s=latency)
        return {"ok": True, "raw": answer, "latency_s": latency}
    except Exception as exc:  # noqa: BLE001 — 记录失败，探针不崩（预算已扣）
        latency = round(time.monotonic() - started, 2)
        budget.record(face, case_id, repeat, ok=False, latency_s=latency)
        return {"ok": False, "raw": "", "latency_s": latency, "error": f"{type(exc).__name__}"}


def _build_case_prompt(case: Case, view: RuleView) -> tuple[str, str | None]:
    adapter = ADAPTERS[case.sub_suite]
    built = adapter.build_prompt(case.payload, view)
    if case.sub_suite == "memory.extract":
        system, user = built
        return system, user
    return built, None


async def run_probe(round_label: str, out_path: Path | None = None) -> dict[str, Any]:
    from openai import AsyncOpenAI

    api_key = _load_api_key()
    cases = load_suite()
    key_cases = [c for c in cases if c.key_case]
    prompts = live_prompts()
    result: dict[str, Any] = {
        "probe_version": "e04-real-model.v1",
        "round": round_label,
        "model": os.environ.get("E04_REAL_MODEL", DEFAULT_MODEL),
        "base_url": os.environ.get("E04_REAL_BASE_URL", DEFAULT_BASE_URL),
        "has_key": bool(api_key),
        "repeats": REAL_MODEL_REPEATS,
        "caps": {"per_face": REAL_MODEL_MAX_CALLS_PER_FACE, "total": REAL_MODEL_MAX_CALLS_TOTAL},
        "prompt_shas": {sub: sha256_text(text) for sub, text in prompts.items()},
        "budget": {"per_face": {}, "total": 0, "ledger": []},
        "cases": [],
    }
    if not api_key:
        result["error"] = "no API key available (env DASHSCOPE_API_KEY / main-repo backend/.env)"
        if out_path is not None:
            out_path.write_text(__import__("json").dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    client = AsyncOpenAI(api_key=api_key, base_url=result["base_url"])
    budget = _CallBudget()
    verdicts: list[CaseVerdict] = []

    for case in key_cases:
        adapter = ADAPTERS[case.sub_suite]
        view: RuleView = adapter.rule_view(case.payload)
        ok, reason = view.matches_expectation(case.runtime_expectation)
        if not ok:
            result["cases"].append({"case_id": case.case_id, "error": f"rule drift: {reason}", "passed": False})
            verdicts.append(
                CaseVerdict(
                    case_id=case.case_id,
                    face=case.face,
                    sub_suite=case.sub_suite,
                    dimension=case.dimension,
                    key_case=True,
                    is_safety=case.is_safety,
                    calls=[],
                )
            )
            continue
        system_prompt, user_content = _build_case_prompt(case, view)
        verdict = CaseVerdict(
            case_id=case.case_id,
            face=case.face,
            sub_suite=case.sub_suite,
            dimension=case.dimension,
            key_case=True,
            is_safety=case.is_safety,
        )
        repeats_rows = []
        for repeat in range(REAL_MODEL_REPEATS):
            call = await _chat_once(
                client,
                model=result["model"],
                system_prompt=system_prompt,
                user_content=user_content,
                temperature=FACE_TEMPERATURES[case.sub_suite],
                budget=budget,
                face=case.face,
                case_id=case.case_id,
                repeat=repeat + 1,
            )
            if call["ok"]:
                call_verdict = grade_raw_completion(case, call["raw"], feasible=view.feasible)
            else:
                from .grading import CallVerdict as _CV

                call_verdict = _CV(ok=False)
                call_verdict.fail("contract.api_error", error=call.get("error"))
            verdict.calls.append(call_verdict)
            repeats_rows.append(
                {
                    "repeat": repeat + 1,
                    "ok": call_verdict.ok,
                    "failure_kinds": call_verdict.failure_kinds,
                    "choice": call_verdict.detail.get("choice"),
                    "raw_head": call["raw"][:160],
                    "latency_s": call["latency_s"],
                }
            )
        verdicts.append(verdict)
        result["cases"].append(
            {
                "case_id": case.case_id,
                "face": case.face,
                "sub_suite": case.sub_suite,
                "dimension": case.dimension,
                "key_case": True,
                "is_safety": case.is_safety,
                "prompt_chars": len(system_prompt) + len(user_content or ""),
                "repeats": repeats_rows,
                "passed": verdict.passed,
                "pass_fraction": verdict.pass_fraction,
            }
        )

    result["budget"] = {
        "per_face": budget.per_face,
        "total": budget.total,
        "ledger": budget.ledger,
    }
    result["aggregate"] = aggregate(verdicts)
    if out_path is not None:
        out_path.write_text(__import__("json").dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    import json
    import sys

    round_label = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    out = Path(__file__).parent / f"real_model_{round_label}.json"
    report = asyncio.run(run_probe(round_label, out_path=out))
    print(json.dumps({"round": round_label, "calls": report["budget"]["total"], "out": str(out)}, ensure_ascii=False))
    sys.exit(0 if not report.get("error") else 1)
