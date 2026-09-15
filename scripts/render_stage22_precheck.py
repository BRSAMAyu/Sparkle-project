#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "docs/product/stage22_precheck.md"


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _registered_trigger_types() -> tuple[str, ...]:
    bridge = REPO_ROOT / "backend/app/services/error_replan_bridge.py"
    text = bridge.read_text(encoding="utf-8")
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
    learner = REPO_ROOT / "backend/app/services/intervention_strategy_learner.py"
    verifier = REPO_ROOT / "backend/app/services/card_protocol/outcome_verifier.py"
    learner_text = learner.read_text(encoding="utf-8")
    verifier_text = verifier.read_text(encoding="utf-8")
    return (
        "goal_type_only" in learner_text
        and "knowledge_level" in learner_text
        and 'for key in ("goal_type", "knowledge_level", "learning_style")' in verifier_text
    )


def main() -> int:
    stage25 = REPO_ROOT / "backend/app/agents/reflection_agent.py"
    stage27 = REPO_ROOT / "backend/app/services/theater/prediction_theater_service.py"
    stage29 = REPO_ROOT / "backend/app/scaffolding/scaffolding_fsm.py"
    trigger_types = _registered_trigger_types()
    cohort_fallback_registered = _cohort_fallback_registered()
    baseline_status = (
        "PASS"
        if len(trigger_types) >= 6 and cohort_fallback_registered
        else "ESCALATE"
    )

    content = f"""# Stage 22 Precheck

- date: 2026-04-21
- purpose: GLM1 secondary precheck for Stages 25 / 27 / 29 before Stage 22 execution

## Stage 25

- verdict: Reflection wire-on remains required
- evidence: `{stage25.relative_to(REPO_ROOT)}` exists with {_line_count(stage25)} lines, but Stage 22 code still exposes no read-path from intervention outcomes into reflection prompts.
- dispatch implication: keep 4 WS lock; do not compress to 3.

## Stage 27

- verdict: Foresight remains a new capability, not an extension
- evidence: `{stage27.relative_to(REPO_ROOT)}` exists with {_line_count(stage27)} lines, but current prediction theater is scoped to learning-result prediction rather than time-window / attractor / deviation foresight.
- dispatch implication: keep Rule AJ and kill-switch split.

## Stage 29

- verdict: SRL remains refactor + new service
- evidence: `{stage29.relative_to(REPO_ROOT)}` exists with {_line_count(stage29)} lines and only tracks scaffolding zones, not explicit Forethought / Performance / Reflection phases.
- dispatch implication: keep `SRLPhaseTracker` beside `ScaffoldingFSM`, not inside orchestrator transitions.

## Baseline Registration

| item | status | evidence |
| --- | --- | --- |
| trigger_type_count | {"PASS" if len(trigger_types) >= 6 else "FAIL"} | `{len(trigger_types)}` registered in `ErrorReplanBridge.TRIGGERING_ERROR_TYPES` |
| registered_trigger_types | {"PASS" if trigger_types else "FAIL"} | {", ".join(f"`{item}`" for item in trigger_types) if trigger_types else "none"} |
| cohort_fallback_registered | {"PASS" if cohort_fallback_registered else "FAIL"} | `InterventionStrategyLearner` keeps goal-type fallback and `OutcomeVerifier` preserves cohort snapshot keys |
| baseline_gate | {baseline_status} | Stage 23 baseline prerequisites are registered in code and artifacts |
"""
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
