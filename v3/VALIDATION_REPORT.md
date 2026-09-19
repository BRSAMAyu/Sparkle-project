# Sparkle V3 Agent Execution Pack — Validation Report

**Validation date:** 2026-09-19  
**Scope:** validates the **execution pack itself** (structure, task graph, scenario corpus, orchestration helpers, and internal references). It does **not** claim that Sparkle V3 product code has already implemented or passed these gates.

## 1. Pack integrity

- V3-only task cards: **107**
- Task dependency graph: **acyclic**
- Initial parallel frontier: **exactly 6 tasks** — `B-01` … `B-06`
- Module portfolio matrix: **42 Flutter feature modules** represented
- Evaluation scenarios: **260**
- Golden Journeys: **20**
- Simulator personas: **10**
- Fleet helper tests: task selection / claim / review-ready / completion state transitions smoke-tested
- Pack unit tests: **4 passed**
- `10_tools/validate_pack.py`: **PASS**, zero errors

## 2. What was structurally verified

### Task system

The validator checks:
- unique task IDs;
- all dependencies resolve;
- no dependency cycle;
- task cards exist for every task;
- required schema fields are present;
- initial baseline cards are schedulable without component-lock conflict;
- referenced V3 files exist.

The initial frontier is intentionally six independent baseline cards:

1. `B-01` — 42-module product portfolio / reachability truth;
2. `B-02` — data truth, mock pollution, metric lineage;
3. `B-03` — cross-platform journey simulator harness;
4. `B-04` — visual baseline and L2–L5 review harness;
5. `B-05` — current model / embedding / voice / OCR / cost capability probe;
6. `B-06` — V3 entity map and duplicate source-of-truth audit.

They are the first six because V3 must inspect the **current** V2.5 repository rather than assume the historical snapshot is still exact.

### Evaluation system

`05_metrics_eval/scenarios_v3.jsonl` contains **260** executable product scenarios across:

- first value;
- memory;
- conflict arbitration;
- Human / Agent / Hybrid allocation;
- Agent Runtime;
- UI states;
- proactive behavior;
- RAG / knowledge;
- security / isolation;
- cross-module journeys;
- community;
- performance / cost.

`05_metrics_eval/GOLDEN_JOURNEYS.md` defines **20** high-value end-to-end journeys. They require visible UI operation and persisted-state evidence rather than API-only success.

### Module coverage

`00_context/MODULE_MATRIX.csv` contains **42 module rows**. V3 deliberately does not treat every module as a first-class destination: each is classified by desired role (core surface, contextual capability, secondary surface, Labs/hidden, retire/decide) so that existing code volume cannot dictate the user experience.

## 3. Validation commands executed

```bash
python 10_tools/validate_pack.py
pytest -q tests/test_pack.py
python 10_tools/next_tasks.py --limit 6
```

Latest observed result:

```text
validator: ok=true
107 tasks
260 scenarios
4 tests passed
initial schedulable tasks: B-01..B-06 (six tasks)
```

The scheduler order may vary by risk/resource sorting; the set of six baseline tasks is invariant.

## 4. Expected warnings

The validator reports two possible legacy product-name warnings inside:

- `09_research/V2_ENGINEERING_CONTEXT_20260917.md`
- `09_research/PROJECT_SNAPSHOT_V3_20260919.md`

These files are immutable historical/source snapshots and intentionally preserve their original wording. The V3 product and package use the canonical name **Sparkle**.

## 5. Claims this report does NOT make

This pack validation does **not** prove:

- the current Sparkle repository is at the same SHA as the supplied snapshot;
- all V2.5 in-progress fixes are currently merged;
- real model/provider credentials are available;
- embedding, STT, TTS, OCR, push, or remote deployment are currently operational;
- Android/Web/macOS Golden Journeys pass today;
- V3 personalization produces the target uplift;
- V3 is already commercially ready.

Those are deliberately assigned to V3 cards and must be proved from the live repository and real execution evidence.

## 6. Completion doctrine

A V3 card is not complete because code exists or an endpoint returns 200. It is complete only when its acceptance criteria are demonstrated on the current integration HEAD with the required automated, simulator/visual, model-trace, persistence, negative-case, and independent-review evidence.

`Q-08` is the only card allowed to declare the V3 commercial release candidate complete.
