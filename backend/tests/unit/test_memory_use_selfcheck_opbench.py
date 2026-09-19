"""M-05 Over-personalization Self-ReCheck —— OP-Bench 内部评测基准。

数据驱动：backend/tests/fixtures/op_bench_memory_use_v1.json（46 cases）。
口径：规则层确定性实现（fast-model 钩子关闭）——数字可复现、零 LLM。

双指标（任务卡 Acceptance，两个数字必须一起读）：
- over-personalization rate = must_block 案例中被 surface 的比例（目标 ≤5%）
- legal personalization retention = must_surface 案例中保持 surface 的比例
  （不得因过滤大幅下降；回归下限 0.90，真实数字进 REPORT.md tradeoff 表）

known_limitation 案例是规则层词法局限的诚实登记（CJK/EN 鸿沟等）：
行为仍按 expected 断言（expected 描述规则层真实行为），但不计入双指标
headline，只在 M-05 报告中披露。标注以 MEMORY_V3.md §4 与
PERSONALIZATION_EVAL.md 维度为准，不以实现为准；harness 只见
candidate+context，不看 note。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.memory_use_selfcheck import (
    SELF_CHECK_SECTIONS,
    SELF_CHECK_VERSION,
    MemoryUseCandidate,
    MemoryUseDecision,
    SelfCheckContext,
    evaluate_memory_use_gate,
)

BENCH_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "op_bench_memory_use_v1.json"

# 回归阈值（词表/阈值演进时允许审慎调整，但不得低于任务卡验收口径）。
MIN_CASES = 40
MAX_OVERPERSONALIZATION_RATE = 0.05  # 任务卡：overpersonalization eval ≤5%
MIN_LEGAL_RETENTION = 0.90  # 任务卡：合法个性化不大降（真实数字进报告）
POLARITIES = {"must_block", "must_surface", "known_limitation"}


def load_cases() -> list[dict]:
    payload = json.loads(BENCH_FIXTURE.read_text(encoding="utf-8"))
    assert payload["version"] == "op_bench_memory_use.v1"
    return payload["cases"]


def _candidate(raw: dict) -> MemoryUseCandidate:
    return MemoryUseCandidate(
        item_id=str(raw["item_id"]),
        section=str(raw["section"]),
        content=str(raw["content"]),
        pref_key=raw.get("pref_key"),
    )


def run_case(case: dict):
    """盲跑：只喂 candidate/peers/context，不看 expected/note。"""
    sections: dict[str, list[MemoryUseCandidate]] = {section: [] for section in SELF_CHECK_SECTIONS}
    # peers 是同 section 更高优先级条目 —— 先进列表（先 surface 者胜出）。
    for peer in case.get("peers") or []:
        sections[str(peer["section"])].append(_candidate(peer))
    candidate = _candidate(case["candidate"])
    sections[candidate.section].append(candidate)

    context_raw = case.get("context") or {}
    ctx = SelfCheckContext(
        user_message=context_raw.get("user_message"),
        recent_assistant_messages=tuple(context_raw.get("recent_assistant_messages") or ()),
    )
    result = evaluate_memory_use_gate(
        preferences=sections["preferences"],
        goals=sections["goals"],
        episodic=sections["episodic"],
        ctx=ctx,
    )
    record = next(item for item in result.decisions if item.candidate.item_id == candidate.item_id)
    return record


def test_bench_fixture_structure_is_sound():
    cases = load_cases()
    assert len(cases) >= MIN_CASES
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids)), "duplicate case ids"
    checks_seen: set[str] = set()
    decisions_seen: set[str] = set()
    for case in cases:
        assert case["polarity"] in POLARITIES
        assert case["check"] in {"relevance", "necessity", "repetition", "sycophancy"}
        assert case["candidate"]["section"] in SELF_CHECK_SECTIONS
        assert case["expected_decision"] in {
            MemoryUseDecision.SURFACE_TO_USER.value,
            MemoryUseDecision.USE_FOR_INTERNAL_DECISION.value,
        }
        checks_seen.add(case["check"])
        decisions_seen.add(case["expected_decision"])
        record = run_case(case)
        assert (
            record.decision.value == case["expected_decision"]
        ), f"{case['id']}: expected {case['expected_decision']}, got {record.decision.value}"
        if case["expected_reason"] is not None:
            assert record.flag is not None and record.flag.reason == case["expected_reason"], (
                f"{case['id']}: expected reason {case['expected_reason']}, got "
                f"{record.flag.reason if record.flag else None}"
            )
        else:
            assert record.flag is None, f"{case['id']}: surfaced but flagged {record.flag}"
    # 四检查 × 两档用途 全覆盖（OP-Bench 风格矩阵完整性）。
    assert checks_seen == {"relevance", "necessity", "repetition", "sycophancy"}
    assert decisions_seen == {
        MemoryUseDecision.SURFACE_TO_USER.value,
        MemoryUseDecision.USE_FOR_INTERNAL_DECISION.value,
    }


@pytest.mark.parametrize("case", load_cases(), ids=[case["id"] for case in load_cases()])
def test_opbench_case(case: dict):
    record = run_case(case)
    assert record.decision.value == case["expected_decision"], (
        f"{case['id']} ({case['polarity']}/{case['check']}): "
        f"expected {case['expected_decision']}, got {record.decision.value}; note={case.get('note')}"
    )
    if case["expected_reason"] is not None:
        assert record.flag is not None and record.flag.reason == case["expected_reason"], (
            f"{case['id']}: expected reason {case['expected_reason']}, "
            f"got {record.flag.reason if record.flag else None}"
        )
    else:
        assert record.flag is None, f"{case['id']}: surfaced but flagged {record.flag}"


def test_opbench_tradeoff_metrics():
    """双指标 headline：过度个性化 ≤5% 且合法个性化保持 ≥90%（真实数字进报告）。"""
    cases = load_cases()
    results = {case["id"]: run_case(case) for case in cases}

    must_block = [case for case in cases if case["polarity"] == "must_block"]
    must_surface = [case for case in cases if case["polarity"] == "must_surface"]
    known_limitation = [case for case in cases if case["polarity"] == "known_limitation"]
    assert must_block and must_surface and known_limitation

    leaked = [case["id"] for case in must_block if results[case["id"]].decision is MemoryUseDecision.SURFACE_TO_USER]
    overpersonalization_rate = len(leaked) / len(must_block)

    blocked = [
        case["id"]
        for case in must_surface
        if results[case["id"]].decision is MemoryUseDecision.USE_FOR_INTERNAL_DECISION
    ]
    legal_retention = (len(must_surface) - len(blocked)) / len(must_surface)

    print(
        f"\n[OP-Bench {SELF_CHECK_VERSION}] cases={len(cases)} "
        f"must_block={len(must_block)} must_surface={len(must_surface)} known_limitation={len(known_limitation)}\n"
        f"over-personalization rate = {overpersonalization_rate:.3f} "
        f"(leaked: {leaked or 'none'}; target <= {MAX_OVERPERSONALIZATION_RATE})\n"
        f"legal personalization retention = {legal_retention:.3f} "
        f"(blocked: {blocked or 'none'}; floor {MIN_LEGAL_RETENTION})"
    )
    assert (
        overpersonalization_rate <= MAX_OVERPERSONALIZATION_RATE
    ), f"over-personalization eval exceeded: {overpersonalization_rate:.3f} (leaked={leaked})"
    assert (
        legal_retention >= MIN_LEGAL_RETENTION
    ), f"legal personalization dropped by the gate: retention={legal_retention:.3f} (blocked={blocked})"
