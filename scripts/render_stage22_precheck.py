#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "docs/product/stage22_precheck.md"


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def main() -> int:
    stage25 = REPO_ROOT / "backend/app/agents/reflection_agent.py"
    stage27 = REPO_ROOT / "backend/app/services/theater/prediction_theater_service.py"
    stage29 = REPO_ROOT / "backend/app/scaffolding/scaffolding_fsm.py"

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
"""
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
