"""E-04 runner — CLI（确定性，机读输出）。

用法（backend/ 下）：

    SECRET_KEY=test /opt/homebrew/bin/python3.11 -m tests.ai_face_eval.runner            # 静态门禁（stdout=机读 JSON）
    SECRET_KEY=test /opt/homebrew/bin/python3.11 -m tests.ai_face_eval.runner --probe baseline    # 真模型基线（30 次预算）
    SECRET_KEY=test /opt/homebrew/bin/python3.11 -m tests.ai_face_eval.runner --probe converged   # 收敛复测（30 次预算）
    SECRET_KEY=test /opt/homebrew/bin/python3.11 -m tests.ai_face_eval.runner --gate     # 全量门禁（静态+run+floors+收敛）
    SECRET_KEY=test /opt/homebrew/bin/python3.11 -m tests.ai_face_eval.runner --face action       # 单面静态明细
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from .ai_face_schema import Case, load_suite
from .faces import ADAPTERS, live_prompts
from .gate import (
    evaluate_convergence,
    evaluate_floors,
    evaluate_run_gate,
    evaluate_static_gate,
)
from .prompt_registry import sha256_text

HERE = Path(__file__).parent


def rule_drift_errors(cases: list[Case]) -> list[str]:
    """live 规则层 vs 冻结 runtime_expectation 逐 case 比对（漂移绊线）。"""
    errors = []
    for case in cases:
        adapter = ADAPTERS[case.sub_suite]
        try:
            view = adapter.rule_view(case.payload)
        except Exception as exc:  # noqa: BLE001 — 规则层异常也是漂移
            errors.append(f"{case.case_id}: rule layer raised {type(exc).__name__}: {exc}")
            continue
        ok, reason = view.matches_expectation(case.runtime_expectation)
        if not ok:
            errors.append(f"{case.case_id}: {reason}")
    return errors


def static_payload(face: str | None = None) -> dict[str, Any]:
    cases = load_suite()
    if face:
        cases = [c for c in cases if c.face == face]
    prompts = live_prompts()
    drift = rule_drift_errors(cases)
    gate = evaluate_static_gate(load_suite(), prompts, rule_drift_errors(load_suite()), require_floors=False)
    from .ai_face_schema import coverage_report

    return {
        "gate": {
            "passed": gate.passed,
            "failing_checks": gate.failing_checks(),
            "checks": gate.checks,
        },
        "rule_drift_errors": drift,
        "coverage": coverage_report(load_suite()),
        "live_prompt_shas": {sub: sha256_text(text) for sub, text in prompts.items()},
    }


def full_gate_payload() -> dict[str, Any]:
    cases = load_suite()
    prompts = live_prompts()
    static = evaluate_static_gate(cases, prompts, rule_drift_errors(cases), require_floors=True)

    checks = list(static.checks)
    baseline_path = HERE / "real_model_baseline.json"
    converged_path = HERE / "real_model_converged.json"
    evidence: dict[str, Any] = {
        "baseline_present": baseline_path.is_file(),
        "converged_present": converged_path.is_file(),
    }
    if baseline_path.is_file() and converged_path.is_file():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        converged = json.loads(converged_path.read_text(encoding="utf-8"))
        run_gate = evaluate_run_gate(converged)
        floors_gate = evaluate_floors(converged)
        conv_gate = evaluate_convergence(baseline, converged)
        checks.extend(run_gate.checks)
        checks.extend(floors_gate.checks)
        checks.extend(conv_gate.checks)
        evidence["run_gate_failing"] = run_gate.failing_checks()
        evidence["floors_gate_failing"] = floors_gate.failing_checks()
        evidence["convergence_gate_failing"] = conv_gate.failing_checks()
        evidence["baseline_calls"] = baseline.get("budget", {}).get("total")
        evidence["converged_calls"] = converged.get("budget", {}).get("total")
    passed = all(c["passed"] for c in checks)
    return {"gate_passed": passed, "checks": checks, "evidence": evidence}


def main(argv: list[str]) -> int:
    if "--probe" in argv:
        from .real_model import run_probe

        round_label = argv[argv.index("--probe") + 1] if len(argv) > argv.index("--probe") + 1 else "baseline"
        out = HERE / f"real_model_{round_label}.json"
        report = asyncio.run(run_probe(round_label, out_path=out))
        print(json.dumps({"round": round_label, "calls_used": report["budget"]["total"], "out": str(out), "error": report.get("error")}, ensure_ascii=False))
        return 0 if not report.get("error") else 1
    if "--gate" in argv:
        payload = full_gate_payload()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["gate_passed"] else 1
    face = None
    if "--face" in argv and len(argv) > argv.index("--face") + 1:
        face = argv[argv.index("--face") + 1]
    print(json.dumps(static_payload(face), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
