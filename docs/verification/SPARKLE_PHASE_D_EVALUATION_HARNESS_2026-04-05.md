# Sparkle Phase D Evaluation Harness

> Date: 2026-04-05  
> Scope: Phase D regression harness v1 for body-aware selection, canonical fallback reporting, and blocked-organ simulation

## Runtime Entry Point

- Service: `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/capability_selection_evaluator.py`
- Fixture: `/Users/brsama/code/GitHub/Sparkle-project/backend/tests/fixtures/phase_d_body_awareness_baseline_scenarios.json`
- Integration test: `/Users/brsama/code/GitHub/Sparkle-project/backend/tests/integration/test_capability_selection_evaluator.py`
- Scorecards: `/Users/brsama/code/GitHub/Sparkle-project/docs/verification/SPARKLE_PHASE_D_EVALUATION_SCORECARDS_2026-04-05.json`

## What It Scores

- selection correctness
- grounding win rate
- specialist escalation precision
- unnecessary escalation rate
- cost discipline
- user-facing coherence
- scenario error cases

## Modes

- `regression_guided`
  Uses the D0 fixture expectations to keep broad policy regressions stable.
- `strict_runtime`
  Compiles requirements from the actual turn context only, then simulates blocked or unavailable organs to verify fallback behavior without expected-need injection.

## Commands

```bash
cd backend
pytest tests/services/test_capability_selection_evaluator.py tests/integration/test_capability_selection_evaluator.py -v
```

```bash
cd backend
./.venv/bin/python - <<'PY'
import json
from app.services.capability_selection_evaluator import CapabilitySelectionEvaluator
svc = CapabilitySelectionEvaluator()
print(json.dumps(svc.evaluate(mode="regression_guided"), ensure_ascii=False, indent=2))
print(json.dumps(svc.evaluate(mode="strict_runtime"), ensure_ascii=False, indent=2))
PY
```

## Latest Result

- `regression_guided`
  - status: `pass`
  - selection correctness: `0.9`
  - grounding win rate: `0.4`
  - specialist escalation precision: `1.0`
  - unnecessary escalation rate: `0.0`
  - cost discipline: `0.9`
  - user-facing coherence: `1.0`
- `strict_runtime`
  - status: `pass`
  - selection correctness: `0.8812`
  - grounding win rate: `0.4`
  - specialist escalation precision: `1.0`
  - unnecessary escalation rate: `0.0`
  - cost discipline: `0.9`
  - user-facing coherence: `1.0`
  - blocked-organ simulations covered:
    - retrieval path unavailable
    - specialist path unavailable
    - higher-priority in-band model unavailable

## Interpretation

- `pass` means the selector is now measurably using live-body availability, canonical capability IDs, and explicit fallback reporting across the D0 scenario pack.
- This harness is intentionally a regression harness v1, not final product proof.
- `strict_runtime` is the freeze gate for this pass because it verifies live-body fallback behavior without expected-need injection.
- Final Phase D truth still comes from live turns, human eval, and whether the governed choices improve grounding, plan quality, and trust without unacceptable cost drift.
