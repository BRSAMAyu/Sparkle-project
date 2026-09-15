#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PRECHECK_PATH = REPO_ROOT / "docs/product/stage22_precheck.md"
BASELINE_PATH = REPO_ROOT / "docs/product/stage22_prompt_coverage_baseline.md"
ERROR_REPLAN_PATH = REPO_ROOT / "backend/app/services/error_replan_bridge.py"
LEARNER_PATH = REPO_ROOT / "backend/app/services/intervention_strategy_learner.py"
OUTCOME_VERIFIER_PATH = REPO_ROOT / "backend/app/services/card_protocol/outcome_verifier.py"


def _parse_coverage_ratio() -> float | None:
    text = BASELINE_PATH.read_text(encoding="utf-8")
    match = re.search(r"coverage_ratio:\s*([0-9.]+)", text)
    return float(match.group(1)) if match else None


def _parse_table_rows() -> dict[str, str]:
    rows: dict[str, str] = {}
    text = PRECHECK_PATH.read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.startswith("|") or line.startswith("| ---"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) != 3 or parts[0] == "item":
            continue
        rows[parts[0]] = parts[1]
    return rows


def _trigger_types() -> tuple[str, ...]:
    text = ERROR_REPLAN_PATH.read_text(encoding="utf-8")
    match = re.search(r"TRIGGERING_ERROR_TYPES\s*=\s*\{([^}]+)\}", text, re.S)
    if not match:
        return ()
    return tuple(
        sorted(
            {
                token
                for token in re.findall(r'"([^"]+)"', match.group(1))
                if token.strip()
            }
        )
    )


def _cohort_fallback_registered() -> bool:
    learner_text = LEARNER_PATH.read_text(encoding="utf-8")
    verifier_text = OUTCOME_VERIFIER_PATH.read_text(encoding="utf-8")
    return (
        "goal_type_only" in learner_text
        and 'for key in ("goal_type", "knowledge_level", "learning_style")' in verifier_text
    )


def check_rule_ag() -> list[str]:
    violations: list[str] = []
    if not PRECHECK_PATH.exists():
        violations.append("AG001 missing docs/product/stage22_precheck.md")
    if not BASELINE_PATH.exists():
        violations.append("AG002 missing docs/product/stage22_prompt_coverage_baseline.md")
    if violations:
        return violations

    coverage_ratio = _parse_coverage_ratio()
    if coverage_ratio is None or coverage_ratio < 0.70:
        violations.append(f"AG003 prompt coverage baseline below threshold: {coverage_ratio}")

    rows = _parse_table_rows()
    required_rows = {"trigger_type_count", "registered_trigger_types", "cohort_fallback_registered", "baseline_gate"}
    missing_rows = sorted(required_rows - rows.keys())
    if missing_rows:
        violations.append(f"AG004 precheck table missing rows: {missing_rows}")

    trigger_types = _trigger_types()
    if len(trigger_types) < 6:
        violations.append(f"AG005 expected >=6 trigger types, found {len(trigger_types)}")

    if rows.get("trigger_type_count") == "FAIL":
        violations.append("AG006 precheck recorded trigger_type_count as FAIL")
    if rows.get("cohort_fallback_registered") == "FAIL":
        violations.append("AG007 precheck recorded cohort_fallback_registered as FAIL")
    if rows.get("baseline_gate") == "ESCALATE":
        violations.append("AG008 precheck recorded baseline_gate as ESCALATE")

    if not _cohort_fallback_registered():
        violations.append("AG009 cohort fallback code path is not registered in learner/verifier")
    return violations


def main() -> int:
    violations = check_rule_ag()
    if violations:
        print("[Rule AG] FAIL")
        for item in violations:
            print(item)
        return 1
    coverage_ratio = _parse_coverage_ratio() or 0.0
    trigger_types = _trigger_types()

    print(
        "[Rule AG] PASS - Stage 22 baseline prerequisites remain registered "
        f"(coverage_ratio={coverage_ratio:.3f}, trigger_types={len(trigger_types)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
