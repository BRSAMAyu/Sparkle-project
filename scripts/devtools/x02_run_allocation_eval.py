#!/usr/bin/env python3
"""X-02 · Action Allocation blind-eval report generator.

跑 backend/tests/fixtures/action_allocation_eval_v1.json 的盲评基准（规则层独跑），
生成 v3-output/X-02/EVAL_RESULTS.md（含逐场景表、类别分布、reason 命中分布、
结构性不变式核对）。一次性评测脚本（scripts/devtools 规范收口）。

用法（backend 目录、worktree 内）：
    SECRET_KEY=... python3.11 ../scripts/devtools/x02_run_allocation_eval.py <worktree-root>

不触 DB、不调 LLM（规则层口径）。
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.action_allocation_policy import (  # noqa: E402
    AllocationFactors,
    _high_risk,
    _learning_guard_active,
    decide_allocation,
)


def main() -> int:
    worktree = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else BACKEND.parent
    fixture = BACKEND / "tests" / "fixtures" / "action_allocation_eval_v1.json"
    out_dir = worktree / "v3-output" / "X-02"
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = json.loads(fixture.read_text(encoding="utf-8"))
    scenarios = payload["scenarios"]

    rows = []
    reason_counter: Counter[str] = Counter()
    cat_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "hit": 0})
    mode_counter: Counter[str] = Counter()
    invariant_failures: list[str] = []

    for scenario in scenarios:
        factors = AllocationFactors.coerce(scenario["factors"])
        decision = decide_allocation(factors)
        ok = decision.mode == scenario["target"]
        rows.append((scenario, decision, ok))
        reason_counter.update(decision.why)
        cat_stats[scenario["category"]]["n"] += 1
        cat_stats[scenario["category"]]["hit"] += int(ok)
        mode_counter[decision.mode] += 1

        sid = scenario["id"]
        if _learning_guard_active(factors) and decision.mode == "agent":
            invariant_failures.append(f"{sid}: learning guard -> agent")
        if factors.privacy == "restricted" and decision.mode != "human":
            invariant_failures.append(f"{sid}: restricted privacy -> {decision.mode}")
        if factors.embodiment_required is True and decision.mode == "agent":
            invariant_failures.append(f"{sid}: embodiment -> agent")
        if factors.privacy == "sensitive" and decision.mode == "agent":
            invariant_failures.append(f"{sid}: sensitive privacy -> agent")
        if _high_risk(factors):
            if decision.mode == "agent":
                invariant_failures.append(f"{sid}: high-risk -> agent")
            if not decision.requires_human_approval:
                invariant_failures.append(f"{sid}: high-risk without approval flag")

    total = len(rows)
    hits = sum(1 for _, _, ok in rows if ok)
    accuracy = hits / total

    lines: list[str] = []
    lines.append("# X-02 Human/Agent/Hybrid Allocation — Blind Scenario Eval")
    lines.append("")
    lines.append(
        f"- 评测集：`backend/tests/fixtures/action_allocation_eval_v1.json`（**{total} 场景**，"
        f"{len(cat_stats)} 类：{', '.join(sorted(cat_stats))}）"
    )
    lines.append(
        "- 口径：**规则层独跑**（`SPARKLE_ALLOCATION_SEMANTIC_ENABLED=False`；`decide_allocation` 纯函数）——"
        "数字可复现、不依赖 LLM"
    )
    lines.append(
        "- 盲评机制：fixture target 标注自 v3/02_core_systems/HUMAN_AGENT_HYBRID.md §2-§4 原则"
        "（标注只看文档默认规则，rubric 盲跑只见 factors 不见 target）"
    )
    lines.append(
        "- 复现：`cd backend && pytest tests/unit/test_action_allocation_eval.py -q`"
        "（阈值守卫：≥0.90、high-risk auto=0、学习类 agent=0、逐场景不变式）"
    )
    lines.append(f"- 环境：wt4 @ 1ea854c9 + X-02 改动 ｜ 运行日期：{date.today().isoformat()}")
    lines.append("")
    lines.append("## 基准数字（rule 层）")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|---|---|")
    lines.append(f"| overall accuracy | **{accuracy:.4f}**（{hits}/{total}） |")
    lines.append(
        f"| mode 分布 | agent {mode_counter['agent']} / hybrid {mode_counter['hybrid']} / human {mode_counter['human']} |"
    )
    lines.append(f"| 结构性不变式违例 | **{len(invariant_failures)}** |")
    lines.append("")
    lines.append("### 验收专项")
    lines.append("")
    high_risk_rows = [r for r in rows if r[0]["category"] == "high_risk"]
    auto_agent = [s["id"] for s, d, _ in high_risk_rows if d.mode == "agent"]
    lines.append(
        f"- **high-risk auto=0**：{len(high_risk_rows)} 个 high-risk 场景 auto-agent 命中 = "
        f"**{len(auto_agent)}**，且全部携带 `requires_human_approval`"
    )
    learning_rows = [r for r in rows if _learning_guard_active(AllocationFactors.coerce(r[0]["factors"]))]
    learning_agent = [s["id"] for s, d, _ in learning_rows if d.mode == "agent"]
    lines.append(
        f"- **学习目标不代写**：{len(learning_rows)} 个学习守卫生效场景 agent 命中 = "
        f"**{len(learning_agent)}**（含 4 个全压力叠加对抗样例：显式代办×偏好agent×紧急）"
    )
    lines.append("")
    lines.append("### 类别分布（n / 命中）")
    lines.append("")
    lines.append("| category | n | hit | miss |")
    lines.append("|---|---|---|---|")
    for cat in sorted(cat_stats):
        stats = cat_stats[cat]
        lines.append(f"| {cat} | {stats['n']} | {stats['hit']} | {stats['n'] - stats['hit']} |")
    lines.append("")
    lines.append("### 规则命中分布（决策可审计性）")
    lines.append("")
    lines.append(" · ".join(f"{reason} {count}" for reason, count in sorted(reason_counter.items())))
    lines.append("")
    if invariant_failures:
        lines.append("## 不变式违例（必须为空）")
        lines.extend(f"- {f}" for f in invariant_failures)
        lines.append("")
    lines.append("## 逐场景结果")
    lines.append("")
    for scenario, decision, ok in rows:
        mark = "OK" if ok else f"MISS(target={scenario['target']})"
        lines.append(
            f"- **{scenario['id']}** [{scenario['category']}] {scenario['summary']} → "
            f"`{decision.mode}` {mark} ｜ why={'/'.join(decision.why)} ｜ conf={decision.confidence:.2f}"
        )
    lines.append("")
    lines.append("## 口径声明（诚实边界）")
    lines.append("")
    lines.append(
        "- 本基准的 target 与 rubric 同源于 HUMAN_AGENT_HYBRID.md 且同工标注：它证明"
        "**rubric 与文档原则的一致性 + 回归防护**，不等价于独立多标注者一致性；"
    )
    lines.append(
        "- 真正的硬验收是结构性不变式（high-risk auto=0 / 学习不代写 / restricted=human）——"
        "它们按因子动态判定、与标签无关；"
    )
    lines.append("- 语义灰区（D6）的真实增益由真实 LLM 冒烟另行评估（见 REPORT，≤5 次预算）。")

    (out_dir / "EVAL_RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"accuracy={accuracy:.4f} ({hits}/{total}) invariants_failed={len(invariant_failures)}")
    print(f"written: {out_dir / 'EVAL_RESULTS.md'}")
    return 0 if accuracy >= 0.90 and not invariant_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
