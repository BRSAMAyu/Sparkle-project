"""Q-01 · V3 scenario library 统一 Runner CLI（deterministic / model / simulator 三路由）。

用法（backend/ 下）::

    SECRET_KEY=test python3 -m tests.v3_scenario_eval.runner                        # stdout 机读 JSON
    SECRET_KEY=test python3 -m tests.v3_scenario_eval.runner --out /tmp/v3run.json  # 附带 evidence/ 落盘
    SECRET_KEY=test python3 -m tests.v3_scenario_eval.runner --seed 42 --provider-config /tmp/p.json

acceptance 钉面：260 case 可枚举；unsupported 不算 PASS（诚实降级）；
结果 JSON schema 稳定（版本字段 + 固定键集）；真实 LLM 0 次。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .grading import (
    REASON_REAL_MODEL_ZERO_CALL,
    VERDICT_UNSUPPORTED,
    AttemptResult,
    ItemResult,
    attempt_verdict,
    case_verdict,
    grade_attempt,
    summarize,
)
from .harnesses import RealModelAdapter, execute, parse_provider_config
from .scenario_schema import HARNESS_MODEL, Scenario, load_scenarios, scenarios_path

RESULTS_SCHEMA_VERSION = "sparkle.v3.scenario-results.v1"

#: verdict 语义声明（冻结文案；写入每轮 meta，防误读）。
VERDICT_SEMANTICS = (
    "contract-simulation: verdicts judge a deterministic reference implementation of the V3 "
    "behavioral contract, not the production system; per-case provenance is recorded in "
    "evidence.provenance; unsupported items degrade honestly and never count as PASS"
)

SUPPORTED_PROVIDERS = frozenset({"mock", "zhipu", "hunyuan", "siliconflow"})


def _git_sha() -> str:
    override = os.environ.get("V3_EVAL_GIT_SHA")
    if override:
        return override
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def derive_attempt_seed(run_seed: int, case_id: str, attempt: int) -> int:
    """per-attempt seed（sha256 稳定派生；跨进程/跨平台一致，不用盐化 hash）。"""
    digest = hashlib.sha256(f"{run_seed}:{case_id}:{attempt}".encode()).digest()
    return int.from_bytes(digest[:4], "big")


def run_case(scenario: Scenario, run_seed: int, provider_config: Any) -> dict[str, Any]:
    """单 case 全 repeat 执行 → 稳定 case-level 结果对象。"""
    attempts: list[AttemptResult] = []
    for attempt_index in range(1, scenario.repeat + 1):
        seed = derive_attempt_seed(run_seed, scenario.case_id, attempt_index)
        if scenario.harness == HARNESS_MODEL and not provider_config.is_mock:
            # 真模型路径本轮零调用：provider 配了真 provider → 诚实 unsupported，不发任何请求。
            items = [
                ItemResult(text=text, status="unsupported", detail=REASON_REAL_MODEL_ZERO_CALL)
                for text in scenario.expected
            ]
            run = None
        else:
            try:
                run = execute(scenario, seed)
            except KeyError as error:
                items = [
                    ItemResult(text=text, status="unsupported", detail=f"harness_execution_error: {error}")
                    for text in scenario.expected
                ]
                run = None
            else:
                items = grade_attempt(scenario.category, scenario.input, scenario.expected, run.observations)
        attempts.append(
            AttemptResult(
                attempt=attempt_index,
                seed=seed,
                verdict=attempt_verdict(items),
                items=items,
                metrics=dict(run.metrics) if run is not None else {},
            )
        )
    verdict = case_verdict(attempts)
    reason = None
    if verdict == VERDICT_UNSUPPORTED:
        reasons = [item.detail for attempt in attempts for item in attempt.items if item.status == "unsupported"]
        reason = "; ".join(sorted(set(reasons)))
    return {
        "case_id": scenario.case_id,
        "category": scenario.category,
        "run_mode": scenario.run_mode,
        "harness": scenario.harness,
        "persona_id": scenario.persona_id,
        "repeat": scenario.repeat,
        "verdict": verdict,
        "reason": reason,
        "attempts": [attempt.to_payload() for attempt in attempts],
        "trace_ref": None,  # 由 run_round 在落盘时回填
        "evidence": {
            "provenance": "reference-mock" if provider_config.is_mock else provider_config.provider,
            "seed_base": run_seed,
        },
    }


def run_round(
    run_seed: int = 7,
    provider_raw: dict[str, Any] | None = None,
    scenarios: list[Scenario] | None = None,
) -> dict[str, Any]:
    """全量一轮：260 case 枚举 → 三路由 → 稳定结果 payload（内存态，无 IO）。"""
    provider_config = parse_provider_config(provider_raw)
    if provider_config.provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"unknown provider {provider_config.provider!r}; supported: {sorted(SUPPORTED_PROVIDERS)}")
    if scenarios is None:
        scenarios = load_scenarios()
    _ = RealModelAdapter()  # 预留接口仅构造；本轮任何路径都不调用 complete()
    case_payloads = [run_case(scenario, run_seed, provider_config) for scenario in scenarios]
    summary = summarize(case_payloads)
    return {
        "schema": RESULTS_SCHEMA_VERSION,
        "meta": {
            "git_sha": _git_sha(),
            "generated_at": datetime.now(UTC).isoformat(),
            "run_seed": run_seed,
            "provider_config": provider_config.to_payload(),
            "real_llm_calls": 0,
            "scenario_source": str(scenarios_path()),
            "scenario_count": len(case_payloads),
            "verdict_semantics": VERDICT_SEMANTICS,
        },
        "summary": summary.to_payload(),
        "cases": case_payloads,
    }


def strip_volatile(payload: dict[str, Any]) -> dict[str, Any]:
    """剔除时间戳/git 等易变字段，供逐字节确定性比对。"""
    cloned = json.loads(json.dumps(payload, ensure_ascii=False))
    cloned["meta"].pop("generated_at", None)
    cloned["meta"].pop("git_sha", None)
    return cloned


def write_evidence(payload: dict[str, Any], out_path: Path) -> None:
    """落盘 results JSON + 逐 case evidence 文件，并回填 trace_ref。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_dir = out_path.parent / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    scenario_by_id = {scenario.case_id: scenario for scenario in load_scenarios()}
    for case in payload["cases"]:
        case_id = case["case_id"]
        scenario = scenario_by_id[case_id]
        evidence_file = evidence_dir / f"{case_id}.json"
        evidence = {
            "schema": RESULTS_SCHEMA_VERSION,
            "case_id": case_id,
            "input": scenario.input,
            "expected": list(scenario.expected),
            "must_preserve": list(scenario.must_preserve),
            "goal": scenario.goal,
            "verdict": case["verdict"],
            "reason": case["reason"],
            "attempts": case["attempts"],
            "provenance": case["evidence"]["provenance"],
        }
        evidence_file.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        case["trace_ref"] = f"evidence/{case_id}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V3 scenario unified runner (260 cases)")
    parser.add_argument("--out", type=Path, default=None, help="write JSON here (default stdout)")
    parser.add_argument("--seed", type=int, default=7, help="base run seed (default 7)")
    parser.add_argument(
        "--provider-config",
        type=Path,
        default=None,
        help="provider config JSON; real providers are reserved interfaces and stay zero-call this round",
    )
    args = parser.parse_args(argv)

    provider_raw = None
    if args.provider_config:
        provider_raw = json.loads(args.provider_config.read_text(encoding="utf-8"))
    payload = run_round(run_seed=args.seed, provider_raw=provider_raw)
    if args.out:
        write_evidence(payload, args.out)
        print(f"wrote {payload['summary']['total']} case results -> {args.out}", file=sys.stderr)
        print(
            f"summary: pass={payload['summary']['pass']} fail={payload['summary']['fail']} "
            f"unsupported={payload['summary']['unsupported']} real_llm_calls={payload['meta']['real_llm_calls']}",
            file=sys.stderr,
        )
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
