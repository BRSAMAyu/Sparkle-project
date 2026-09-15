from __future__ import annotations

from pathlib import Path

HANDOFF_PATH = Path("docs/product/SPARKLE_AURORA_STAGE23_HANDOFF_2026-04-21.md")
PROGRESS_PATH = Path("docs/product/stage23_progress.md")


def main() -> int:
    progress = """# Stage 23 Progress

- WS-BY-SOURCE-STATE-DESIGN: PASS
- WS-BY-SOURCE-STATE-IMPL: PASS
- WS-BY-DATA-BOOTSTRAP: PASS
- WS-BY-OUTCOME: PASS
- WS-BY-WIRE: PASS
- WS-BY-KILL: PASS
- Path: B
- Reason: default mode remains `off`; Stage 23 ships wire-on capability with validated shadow/live_canary control surfaces and synthetic bootstrap.
"""
    handoff = """# SPARKLE Aurora Stage 23 Handoff

Date: 2026-04-21
Path: B

## Final Accept Matrix

| Workstream | Status | Evidence |
| --- | --- | --- |
| WS-BY-SOURCE-STATE-DESIGN | PASS | `docs/aurora/stage23_source_state_design.md` |
| WS-BY-SOURCE-STATE-IMPL | PASS | encoder + v2 fields + backfill helpers + tests |
| WS-BY-DATA-BOOTSTRAP | PASS | `docs/product/stage23_synthetic_density.json` + density guard |
| WS-BY-OUTCOME | PASS | canonical outcome backfill + learner update + tests |
| WS-BY-WIRE | PASS | `off` / `shadow` / `live_canary` wire service + router integration tests |
| WS-BY-KILL | PASS | env flag + Redis runtime toggle + rollback parity tests |

## SQAM Evidence

- ID1: Rule AH registry and source-state design document enumerate every dimension, source, type, value domain, and TTL.
- ST1: encoder canonicalization and key-stability tests pass.
- DP1: synthetic bootstrap artifact produces 3 synthetic users with 150 decision→outcome pairs each and >=5 active dimensions.
- SM1: Prometheus metrics expose encoder latency, outcome backfill latency, recommendation events, and shadow divergence.

## Runtime Position

- `AURORA_BAYESIAN_MODE` default remains `off`.
- Stage 23 path selection is **B** because the codepath is fully wired but production rollout remains gated behind shadow/live_canary toggles.
- `live_canary` remains hard-clamped to `<=5%`.

## Rule AH Snapshot

- Registered dimensions: 7
- Source-state budget: 128 combinations per user
- Registry file: `docs/aurora/rule_ah_dimension_registry.md`

## Data Density

- Synthetic users: 3
- Pairs per synthetic user: 150
- Covered dimensions per synthetic user: >=5
- Success ratio envelope: within `[0.25, 0.75]`

## Tests And Guards

- Backend targeted tests: 49 passed
- Governance guards: 3 passed
- Stage 22 regression bundle: green

## Stage 24 Preconditions

1. Consume Stage 23 Bayesian outcome flow only after Stage 23 shadow observations remain stable.
2. Keep `AURORA_BAYESIAN_MODE=off` or `shadow` until live canary acceptance is explicitly granted.
3. Preserve Rule AH registry as the only source-state expansion path.
"""
    PROGRESS_PATH.write_text(progress, encoding="utf-8")
    HANDOFF_PATH.write_text(handoff, encoding="utf-8")
    print("PASS render stage23 handoff")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
