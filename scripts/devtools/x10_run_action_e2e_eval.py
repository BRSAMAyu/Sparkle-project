#!/usr/bin/env python3
"""X-10 · Action Engine E2E Evaluation 无人值守 runner（一键全量）.

跑 backend/tests/fixtures/x10_action_e2e_scenarios_v1.json 的 77 场景
（allocation × authorization × proposal × run_steps × outcome × GJ04-07），
每场景记录 decision/execution/result/outcome/latency/cost 六元组，判定对 DB
真相独立复算（false success=0 / high-risk auto=0 全局断言）。

用法（worktree 根，backend/.venv 已就绪）::

    backend/.venv/bin/python scripts/devtools/x10_run_action_e2e_eval.py [worktree-root]

产物：v3-output/X-10/{results.json, EVAL_RESULTS.md}
exit 0 = 全部 pass 且 acceptance① 三条硬断言全绿；否则非零（无人值守守卫）。
零真实 LLM、零模拟器、零浏览器、零 gradle。
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "app"))

import os  # noqa: E402

os.environ.setdefault("SECRET_KEY", "x10-eval-unattended")
os.environ.setdefault("EVENT_BUS_MAX_RETRIES", "0")

from tests.v3_action_eval.runner import run_round  # noqa: E402
from tests.v3_action_eval.scenario_schema import coverage_matrix, load_scenarios  # noqa: E402


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _decision_short(decision: dict) -> str:
    if not decision:
        return "-"
    if "mode" in decision:
        return str(decision["mode"])
    if "authorization_mode" in decision:
        return str(decision["authorization_mode"])
    if "allocation_mode" in decision:
        return str(decision["allocation_mode"])
    if "step_plan" in decision:
        owners = ",".join(s.get("owner", "?") for s in decision["step_plan"])
        return f"run_plan[{owners}]"
    if "allocation" in decision:
        alloc = decision.get("allocation") or {}
        return f"alloc:{alloc.get('mode', '?')}"
    if "terminal_action" in decision:
        return str(decision["terminal_action"])
    return "-"


def render_eval_results(payload: dict, out_path: Path) -> None:
    """场景矩阵 + 六元组统计 + 失败清单 → Markdown（机读 JSON 的伴生报告）。"""
    summary = payload["summary"]
    matrix = coverage_matrix(load_scenarios())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = []
    lines.append("# X-10 Action Engine E2E — Scenario Results")
    lines.append("")
    lines.append(f"- git SHA: `{payload['meta']['git_sha']}` ｜ 运行：{now} ｜ 场景源：`{Path(payload['meta']['scenario_source']).name}`")
    lines.append(f"- 判定语义：判定器对 DB 真相独立复算（不信执行器自述）；零真实 LLM（`real_llm_calls=0` 强制断言）")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|---|---|")
    lines.append(f"| 场景总数 | {summary['total']} |")
    lines.append(f"| pass / fail / error | **{summary['pass']} / {summary['fail']} / {summary['error']}** |")
    lines.append(f"| allocation 达标率（acceptance①） | **{summary['allocation']['accuracy']:.2%}**（{summary['allocation']['passed']}/{summary['allocation']['total']}；mode target {summary['allocation']['mode_target']['hits']}/{summary['allocation']['mode_target']['total']}，offer guard {summary['allocation']['offer_guard']['hits']}/{summary['allocation']['offer_guard']['total']}） |")
    lines.append(f"| high-risk auto（acceptance①） | **{summary['high_risk']['auto_agent_violations']}**（不变式覆盖 {summary['high_risk']['scenarios_with_invariant']} 场景） |")
    lines.append(f"| false success（acceptance①） | **{summary['false_success_count']}** |")
    lines.append(f"| 总延迟 / 均值 | {summary['latency_ms']['total']:.0f} ms / {summary['latency_ms']['mean']:.1f} ms（纯服务层墙钟） |")
    lines.append(f"| 成本面（O-07 口径的确定性下界） | LLM 调用 0 次 / 0 token；服务操作 {summary['cost']['service_ops_total']} 次 |")
    lines.append("")
    lines.append("## 家族 × 类别覆盖矩阵")
    lines.append("")
    lines.append("| family | n | pass | fail | error |")
    lines.append("|---|---|---|---|---|")
    for family, stats in summary["by_family"].items():
        lines.append(
            f"| {family} | {stats['total']} | {stats['pass']} | {stats['fail']} | {stats['error']} |"
        )
    lines.append("")
    lines.append("categories: " + "；".join(
        f"{family}（{', '.join(f'{cat}×{n}' for cat, n in cats.items())}）"
        for family, cats in matrix["categories"].items()
    ))
    lines.append("")
    lines.append("## 逐场景矩阵（六元组判定）")
    lines.append("")
    lines.append("| scenario | family | journey | verdict | decision 摘要 | latency ms | cost(llm/ops) |")
    lines.append("|---|---|---|---|---|---|---|")
    for case in payload["cases"]:
        decision_short = _decision_short(case["six_tuple"].get("decision") or {})
        cost = case["six_tuple"].get("cost") or {}
        lines.append(
            f"| {case['scenario_id']} | {case['family']} | {case.get('journey') or '-'} "
            f"| {'PASS' if case['verdict']['verdict'] == 'pass' else case['verdict']['verdict'].upper()} "
            f"| {decision_short} | {case['six_tuple']['latency']['total_ms']:.1f} | {cost.get('llm_calls')}/{cost.get('service_ops')} |"
        )
    lines.append("")
    failed = summary.get("failed_cases") or []
    if failed:
        lines.append("## 失败 case 清单（保留，不粉饰）")
        lines.append("")
        for item in failed:
            lines.append(f"- **{item['scenario_id']}** [{item['family']}/{item['category']}] verdict={item['verdict']}")
            for check in item.get("failed_checks", []):
                lines.append(f"  - `{check['id']}` expected={check['expected']} actual={check['actual']}")
            if item.get("error_detail"):
                lines.append(f"  - error: {item['error_detail']}")
        lines.append("")
    else:
        lines.append("## 失败 case 清单")
        lines.append("")
        lines.append("本轮无失败 case（77/77；判定器有效性由 gate 测试的 7 组变异红证独立保证——判定器对谎报/幂等破坏/极性翻转/LLM 泄漏全部判红）。")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    scenarios = load_scenarios()
    payload_path = REPO_ROOT / "v3-output" / "X-10" / "results.json"
    report_path = REPO_ROOT / "v3-output" / "X-10" / "EVAL_RESULTS.md"
    payload_path.parent.mkdir(parents=True, exist_ok=True)

    payload = run_round_sync(scenarios)
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    render_eval_results(payload, report_path)

    summary = payload["summary"]
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
                "results": str(payload_path),
                "report": str(report_path),
            },
            ensure_ascii=False,
        )
    )
    acceptance_1 = (
        summary["allocation"]["meets_target"]
        and summary["high_risk"]["high_risk_auto_zero"]
        and summary["false_success_zero"]
    )
    print(f"acceptance① allocation>=90% / high-risk auto=0 / false success=0 -> {'PASS' if acceptance_1 else 'FAIL'}")
    return 0 if acceptance_1 and summary["fail"] == 0 and summary["error"] == 0 else 1


def run_round_sync(scenarios):
    import asyncio

    return asyncio.run(run_round(scenarios))


if __name__ == "__main__":
    raise SystemExit(main())
