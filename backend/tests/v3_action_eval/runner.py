"""X-10 · 评测 Runner —— 一键跑完场景集，产出稳定 results JSON（六元组+判定）.

用法（backend/ 下）::

    SECRET_KEY=test .venv/bin/python -m tests.v3_action_eval.runner --out /tmp/x10.json

结果 schema（``sparkle.x10.action-e2e.results.v1``）固定键集；每 case =
六元组（decision/execution/result/outcome/latency/cost）+ 独立判定（checks 全留痕）。
零真实 LLM（``meta.real_llm_calls`` 恒 0 并被判定器强制断言）。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .dbfixture import ScenarioDB
from .executors import EXECUTORS
from .scenario_schema import Scenario, load_scenarios, scenarios_path
from .verdicts import judge_scenario

RESULTS_SCHEMA_VERSION = "sparkle.x10.action-e2e.results.v1"

VERDICT_SEMANTICS = (
    "x10-action-e2e: every scenario executes the REAL service layer (ActionCommandService / "
    "AgentRunService / TaskService / allocation policy / outcome capture+ledger) against a real "
    "DB schema fixture; verdicts are recomputed independently from persisted truth (DB re-read + "
    "pure-function re-derivation), never from the executor's own claims; unsupported work is "
    "reported as failure, never silently skipped; zero real LLM calls"
)


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
    except Exception:  # noqa: BLE001
        return "unknown"


async def run_scenario(scenario: Scenario) -> dict[str, Any]:
    """单场景：独立 DB → 真实服务执行 → 六元组 → 独立判定。"""
    started = time.perf_counter()
    async with ScenarioDB() as db:
        try:
            ctx = await db.new_context(auto_grant=bool(scenario.inputs.get("user_auto_grant")))
            executor = EXECUTORS[scenario.family]
            run = await executor(scenario, ctx)
            total_ms = (time.perf_counter() - started) * 1000
            phase_ms = {s["op"]: s["elapsed_ms"] for s in (s.to_payload() for s in run.steps)}
            six = {
                "decision": run.decision,
                "execution": {
                    "steps": [s.to_payload() for s in run.steps],
                    "service_ops": ctx.service_ops,
                    "op_sequence": list(ctx.extras.get("ops", [])),
                },
                "result": run.result,
                "outcome": run.outcome,
                "latency": {"total_ms": round(total_ms, 3), "phases": phase_ms},
                "cost": {"llm_calls": 0, "llm_tokens": 0, "service_ops": ctx.service_ops, "db_transactions": len(run.steps)},
            }
        except Exception as exc:  # noqa: BLE001 — 执行崩溃也是评测结果（诚实记录，不粉饰）
            total_ms = (time.perf_counter() - started) * 1000
            six = {
                "decision": {},
                "execution": {"steps": [], "service_ops": 0, "op_sequence": []},
                "result": {"executor_crashed": True},
                "outcome": {},
                "latency": {"total_ms": round(total_ms, 3), "phases": {}},
                "cost": {"llm_calls": 0, "llm_tokens": 0, "service_ops": 0, "db_transactions": 0},
                "executor_error": f"{type(exc).__name__}: {exc}",
            }
        verdict = await judge_scenario(scenario, six, ctx)
        if six.get("executor_error"):
            verdict["verdict"] = "error"
            verdict["error_detail"] = verdict.get("error_detail") or six["executor_error"]
    return {
        "scenario_id": scenario.scenario_id,
        "family": scenario.family,
        "category": scenario.category,
        "journey": scenario.journey,
        "summary": scenario.summary,
        "verdict": verdict,
        "six_tuple": {k: six[k] for k in ("decision", "execution", "result", "outcome", "latency", "cost")},
        "executor_error": six.get("executor_error"),
    }


async def run_round(scenarios: list[Scenario] | None = None) -> dict[str, Any]:
    """全量一轮（串行；结果 payload 内存态，无 IO）。"""
    scenarios = scenarios if scenarios is not None else load_scenarios()
    cases: list[dict[str, Any]] = []
    for scenario in scenarios:
        case = await run_scenario(scenario)
        cases.append(case)
    return {
        "schema": RESULTS_SCHEMA_VERSION,
        "meta": {
            "git_sha": _git_sha(),
            "generated_at": datetime.now(UTC).isoformat(),
            "scenario_source": str(scenarios_path()),
            "scenario_count": len(cases),
            "real_llm_calls": 0,
            "verdict_semantics": VERDICT_SEMANTICS,
        },
        "summary": summarize(cases),
        "cases": cases,
    }


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """验收口径汇总（acceptance①/② 的直接数据面）。"""
    total = len(cases)
    passed = sum(1 for c in cases if c["verdict"]["verdict"] == "pass")
    failed = sum(1 for c in cases if c["verdict"]["verdict"] == "fail")
    errored = sum(1 for c in cases if c["verdict"]["verdict"] == "error")
    false_success = sum(1 for c in cases if c["verdict"].get("false_success"))
    high_risk_auto = sum(1 for c in cases if c["verdict"].get("high_risk_auto"))

    by_family: dict[str, dict[str, int]] = {}
    for case in cases:
        family = case["family"]
        by_family.setdefault(family, {"total": 0, "pass": 0, "fail": 0, "error": 0})
        by_family[family]["total"] += 1
        by_family[family][case["verdict"]["verdict"]] += 1

    allocation_cases = [c for c in cases if c["family"] == "allocation"]
    allocation_passed = sum(1 for c in allocation_cases if c["verdict"]["verdict"] == "pass")

    def _has_check(case: dict[str, Any], check_id: str) -> bool:
        return any(check["id"] == check_id for check in case["verdict"]["checks"])

    def _check_hit(case: dict[str, Any], check_id: str) -> bool:
        return any(check["id"] == check_id and check["passed"] for check in case["verdict"]["checks"])

    mode_cases = [c for c in allocation_cases if _has_check(c, "target.mode")]
    mode_hits = sum(1 for c in mode_cases if _check_hit(c, "target.mode"))
    offer_cases = [c for c in allocation_cases if _has_check(c, "target.offer_allowed")]
    offer_hits = sum(1 for c in offer_cases if _check_hit(c, "target.offer_allowed"))
    high_risk_cases = [
        c for c in allocation_cases if _has_check(c, "invariant.high_risk_auto_zero")
    ]
    high_risk_auto_hits = sum(
        1 for c in high_risk_cases if not _check_hit(c, "invariant.high_risk_auto_zero")
    )

    allocation_total = len(allocation_cases)
    allocation_accuracy = (allocation_passed / allocation_total) if allocation_total else 0.0

    latencies = [c["six_tuple"]["latency"]["total_ms"] for c in cases]
    failed_cases = [
        {
            "scenario_id": c["scenario_id"],
            "family": c["family"],
            "category": c["category"],
            "verdict": c["verdict"]["verdict"],
            "failed_checks": [
                {"id": check["id"], "expected": check.get("expected"), "actual": check.get("actual")}
                for check in c["verdict"]["checks"]
                if not check["passed"]
            ],
            "error_detail": c["verdict"].get("error_detail"),
        }
        for c in cases
        if c["verdict"]["verdict"] != "pass"
    ]

    return {
        "total": total,
        "pass": passed,
        "fail": failed,
        "error": errored,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "allocation": {
            "total": allocation_total,
            "passed": allocation_passed,
            "accuracy": round(allocation_accuracy, 4),
            "mode_target": {"total": len(mode_cases), "hits": mode_hits},
            "offer_guard": {"total": len(offer_cases), "hits": offer_hits},
            "target_min_accuracy": 0.90,
            "meets_target": allocation_accuracy >= 0.90,
        },
        "high_risk": {
            "scenarios_with_invariant": len(high_risk_cases),
            "auto_agent_violations": high_risk_auto_hits,
            "high_risk_auto_zero": high_risk_auto_hits == 0,
        },
        "false_success_count": false_success,
        "false_success_zero": false_success == 0,
        "global_high_risk_auto": high_risk_auto,
        "by_family": by_family,
        "latency_ms": {
            "total": round(sum(latencies), 1) if latencies else 0.0,
            "mean": round(sum(latencies) / len(latencies), 1) if latencies else 0.0,
            "max": round(max(latencies), 1) if latencies else 0.0,
        },
        "cost": {
            "real_llm_calls": 0,
            "llm_tokens": 0,
            "service_ops_total": sum(c["six_tuple"]["cost"]["service_ops"] for c in cases),
        },
        "failed_cases": failed_cases,
    }


def strip_volatile(payload: dict[str, Any]) -> dict[str, Any]:
    """剔除时间戳/git 等易变字段（逐字节比对用）。"""
    cloned = json.loads(json.dumps(payload, ensure_ascii=False))
    cloned["meta"].pop("generated_at", None)
    cloned["meta"].pop("git_sha", None)
    return cloned


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="X-10 action engine E2E evaluation runner")
    parser.add_argument("--out", type=Path, default=None, help="write results JSON here (default stdout summary)")
    parser.add_argument("--family", type=str, default=None, help="run a single family (debug)")
    args = parser.parse_args(argv)

    import asyncio

    scenarios = load_scenarios()
    if args.family:
        scenarios = [s for s in scenarios if s.family == args.family]
    payload = asyncio.run(run_round(scenarios))
    summary = payload["summary"]
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            f"wrote {summary['total']} case results -> {args.out}",
            file=sys.stderr,
        )
    print(
        json.dumps(
            {
                "total": summary["total"],
                "pass": summary["pass"],
                "fail": summary["fail"],
                "error": summary["error"],
                "allocation_accuracy": summary["allocation"]["accuracy"],
                "high_risk_auto_violations": summary["high_risk"]["auto_agent_violations"],
                "false_success": summary["false_success_count"],
                "latency_total_ms": summary["latency_ms"]["total"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
