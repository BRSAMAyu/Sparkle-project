# SPARKLE Aurora / Stage 4 Codex Handoff (2026-04-19)

> **Status**: Archived historical handoff snapshot
> **Branch**: `Aurora-&-adaptive-harness-engineering`
> **Current mode**: strategic + governance-sensitive; do **not** resume normal feature execution blindly
> **Primary purpose**: let a new Codex safely continue from the current repo state without rereading the full multi-day conversation
> **Superseded by**:
> - `SPARKLE_AURORA_STAGE4_RETROACTIVE_AUDIT_2026-04-19.md` v4
> - corrective commits `4f90c1c6` (`WS-D` revert) and `573edf54` (`WS-C.1` backend CRUD tests)
> - final Stage 4 Wave 2 landing commits `804e28f9` (`WS-D`), `2d2b4a5a` (`WS-B.2`), and `448ef9e3` (`WS-E`)

> **Historical note**:
> This handoff captures the repo state before Stage 4 Wave 2 execution resumed. It remains useful for reconstructing the governance incident and the pre-remediation context, but it is no longer the current operational state of the branch.

---

## 1. Executive Summary

This repository has completed:

- `Stage 3 repo-side delivery`
- `Stage 4 vision alignment`
- `Stage 4 engineering structure`
- `Stage 4 dispatch planning`

But **Stage 4 execution did not follow the approved dispatch sequence**.

A single commit:

- `cd2f844b` — `stage 4 part1`

bundled work from multiple Stage 4 workstreams/waves ahead of the signed gate process.

That governance break was later detected by Claude. In response, the current Codex:

1. stopped new Stage 4 feature work
2. wrote a retroactive audit
3. strengthened the audit based on Claude + GLM review
4. prepared a revert of premature `WS-D` work
5. added missing `WS-C.1` backend CRUD tests
6. drafted `Rule G` into the Stage 4 dispatch plan

### The single most important instruction for the next Codex

**Do not resume Stage 4 feature implementation yet.**

The repo is currently in a **post-audit / pre-decision** state:

- audit is ready for Claude / GLM review
- `WS-D` has been reverted in the working tree but not committed
- new backend tests for `WS-C.1` exist but are not committed
- dispatch plan `v3` exists in the working tree but is not committed

The next Codex should treat this as a **governance checkpoint**, not a normal coding checkpoint.

---

## 2. Current Source-of-Truth Documents

Read these in this order:

1. [SPARKLE_AURORA_STAGE3_CHECKPOINT_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE3_CHECKPOINT_2026-04-19.md)
   - repo-side Stage 3 completion checkpoint

2. [SPARKLE_AURORA_STAGE4_VISION_ALIGNMENT_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE4_VISION_ALIGNMENT_2026-04-19.md)
   - strategic intent for Stage 4
   - this is the product/architecture constitution for Stage 4

3. [SPARKLE_AURORA_STAGE4_ENGINEERING_STRUCTURE_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE4_ENGINEERING_STRUCTURE_2026-04-19.md)
   - engineering translation of the vision

4. [SPARKLE_AURORA_STAGE4_DISPATCH_PLAN_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE4_DISPATCH_PLAN_2026-04-19.md)
   - operational dispatch rules / workstreams / gates
   - currently modified in working tree as draft `v3`

5. [SPARKLE_AURORA_STAGE4_RETROACTIVE_AUDIT_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE4_RETROACTIVE_AUDIT_2026-04-19.md)
   - current retroactive audit for the Stage 4 governance break
   - currently untracked / not committed yet

Useful supporting docs:

- [SPARKLE_AURORA_GATE0_SCHEMA_2026-04-17.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_GATE0_SCHEMA_2026-04-17.md)
- [SPARKLE_AURORA_ORCHESTRATOR_INTEGRATION.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_ORCHESTRATOR_INTEGRATION.md)
- [SPARKLE_AURORA_SHADOW_COMPARISON_REPORT_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_SHADOW_COMPARISON_REPORT_2026-04-19.md)
- [SPARKLE_AURORA_WSM_CUTOVER_RUNBOOK_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_WSM_CUTOVER_RUNBOOK_2026-04-19.md)

---

## 3. Strategic State: What Stage 4 Actually Means

Stage 4 is **not** “continue taking over more trigger points.”

Stage 4 was redefined and signed as:

1. **Aurora async-ification**
   - `inline`
   - `nearline`
   - `long-horizon`

2. **Conversation routing split**
   - `direct`
   - `workflow`
   - `task_assistant`

3. **TaskGuidance system**
   - human guide is default
   - AI guide is on-demand
   - closed-loop inside Sparkle, not “export a prompt to another AI”

4. **Task Assistant Dormant Mode**
   - lightweight mode
   - initial Aurora injection only
   - no live re-steering inside the session by default

5. **Budget / eval / activation prep**
   - prove the system is economically viable and operationally governable

Important non-goals already signed:

- no `pre-tool-selection takeover` in Stage 4
- no `pre-response-formatting takeover` in Stage 4
- no new queue system beyond Celery
- no stealth Gate 0 schema edits
- no early real-user rollout expansion

---

## 4. Stage 4 Governance Incident

### What happened

The intended Stage 4 path was:

- sign docs
- dispatch Wave `1a` agents `A/B/C`
- clear `Gate S4-1`
- dispatch Wave `1b`
- clear `Gate S4-2`
- etc.

Instead, commit `cd2f844b` landed a batch crossing:

- `WS-A.1`
- `WS-C.1`
- `WS-F.1`
- `WS-B.1`
- `WS-C.2`
- and part of `WS-D`

This is the event being retroactively audited.

### Why it matters

The project spent several rounds designing:

- Gate 0
- Stage 3 gates
- Stage 4 dispatch rules

specifically to avoid “engineering inertia runs ahead of product governance.”

So the issue is not merely “too much code in one commit.”
It is that the **governance chain was bypassed**.

### Current institutional fix

Dispatch plan draft `v3` now includes:

- **Rule G · Single-WS-per-Agent Commit Discipline**

The next Codex should preserve and defend this rule.

---

## 5. Current Workstream Disposition

Per the current retroactive audit:

| Workstream | Current status |
| --- | --- |
| `WS-A.1` Async Substrate | **conditional retroactive accept candidate** |
| `WS-C.1` TaskGuidance Skeleton | **conditional retroactive accept candidate** |
| `WS-F.1` Benchmark and Guardrails Prep | **retroactive accept candidate** |
| `WS-B.1` Routing-Mode Seam | **conditional retroactive accept candidate with quantified caveat** |
| `WS-C.2` TaskGuidance Productization | **retroactive accept candidate** |
| `WS-D` Task Assistant Dormant Mode | **partial / not accepted / revert recommended** |

### Meaning of those conditions

#### `WS-A.1`
- blocked by a `P1` constitutional violation signal
- nearline currently reaches into `AuroraEngine` directly from `backend/app/aurora/tasks.py`
- this is not “normal tech debt”; it is an architecture-policy issue

#### `WS-C.1`
- backend CRUD evidence was originally weak
- current Codex added explicit backend tests to close this gap

#### `WS-B.1`
- routing seam is implemented
- but part of future `WS-B.2` trigger logic was effectively pre-spent in `_classify_routing_mode(...)`

#### `WS-D`
- should **not** be treated as green
- should **not** be continued
- current recommendation is to **revert**, not quarantine

---

## 6. Current Working Tree State

At the moment of handoff, `git status --short` shows:

### Stage 4 corrective work in progress

- modified:
  - [backend/app/api/v1/chat.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/api/v1/chat.py)
  - [mobile/lib/core/constants/app_constants.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/constants/app_constants.dart)
  - [mobile/lib/features/chat/data/repositories/chat_repository.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/chat/data/repositories/chat_repository.dart)
  - [mobile/lib/features/task/presentation/providers/task_chat_provider.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/task/presentation/providers/task_chat_provider.dart)
  - [docs/product/SPARKLE_AURORA_STAGE4_DISPATCH_PLAN_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE4_DISPATCH_PLAN_2026-04-19.md)
- deleted:
  - [backend/app/task_assistant/__init__.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/task_assistant/__init__.py)
  - [backend/app/task_assistant/schemas.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/task_assistant/schemas.py)
  - [backend/app/task_assistant/service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/task_assistant/service.py)
- untracked:
  - [backend/tests/api/test_task_guidance_api.py](/Users/brsama/code/GitHub/Sparkle-project/backend/tests/api/test_task_guidance_api.py)
  - [docs/product/SPARKLE_AURORA_STAGE4_RETROACTIVE_AUDIT_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE4_RETROACTIVE_AUDIT_2026-04-19.md)

Interpretation:

- these changes are the **post-audit corrective patch**
- they are intentionally **not yet committed**
- they should be reviewed before any new Stage 4 development resumes

### Unrelated repo noise / separate review track

These files are also modified but are **not** part of the Stage 4 corrective patch:

- [Makefile](/Users/brsama/code/GitHub/Sparkle-project/Makefile)
- [backend/gateway/go.mod](/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/go.mod)
- [backend/gateway/go.sum](/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/go.sum)
- [backend/gateway/internal/infra/logger/logger.go](/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/infra/logger/logger.go)
- [scripts/dev_local_stack.sh](/Users/brsama/code/GitHub/Sparkle-project/scripts/dev_local_stack.sh)

Do **not** mix their review with the Stage 4 governance review.

---

## 7. Evidence Already Collected

### Backend verification

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/api/test_task_guidance_api.py \
  tests/aurora/test_deterministic_performance_baseline.py \
  tests/aurora/test_stage4_eval_guardrails.py \
  tests/unit/orchestrator/mixins/test_routing_engine_stage4.py -q
```

Result:
- `11 passed`

Notes:
- includes the newly added `WS-C.1` backend CRUD test coverage

### Full backend Aurora baseline

```bash
cd backend && ./.venv/bin/python -m pytest tests/aurora -q
```

Result captured earlier in this cycle:
- `78 passed, 1 warning`

Important:
- the remaining warning is the `P1` report-only finding in `backend/app/aurora/tasks.py`

### Flags-off routing seam proof

```bash
cd backend && \
  AURORA_ACTIVE=false \
  AURORA_SHADOW_MODE=false \
  AURORA_ROUTING_MODE_ENABLED=false \
  ./.venv/bin/python -m pytest tests/unit/orchestrator/mixins/test_routing_engine_stage4.py -q
```

Result:
- `3 passed`

### Frozen schema proof

```bash
git diff 31812c94..cd2f844b -- backend/app/aurora/schemas/
```

Result:
- no output

### Corpus V1 size proof

```bash
cd backend && PYTHONPATH=. ./.venv/bin/python - <<'PY'
from tests.aurora.stage4_eval_support import build_corpus_v1_cases
from collections import Counter
cases = build_corpus_v1_cases()
print('count', len(cases))
print('categories', dict(Counter(c.category for c in cases)))
print('routing', dict(Counter(c.routing_target for c in cases)))
PY
```

Result:
- `count 20`

### Mobile proof after `WS-D` revert prep

```bash
cd mobile && flutter analyze \
  lib/core/constants/app_constants.dart \
  lib/features/chat/data/repositories/chat_repository.dart \
  lib/features/task/presentation/providers/task_chat_provider.dart \
  lib/features/task/presentation/widgets/task_chat_panel.dart \
  lib/features/task/presentation/widgets/guidance/task_guidance_surface.dart \
  test/widget/j1_frontend_closure_test.dart \
&& flutter test test/widget/j1_frontend_closure_test.dart
```

Result:
- analyze: `No issues found!`
- widget test: `6 passed`

Interpretation:
- the `WS-D` revert prep did not break `WS-C.2`

---

## 8. Immediate Required Next Steps for the New Codex

Do these in order:

1. **Do not implement new Stage 4 features**
   - no `WS-D`
   - no new wave dispatch
   - no “just small follow-up” coding

2. **Present the current audit/correction state to the user / reviewers**
   - the user explicitly asked for a handoff doc
   - use this doc + the retroactive audit doc as the review package

3. **Let Claude / GLM review the corrected audit state**
   - especially:
     - `P1` severity wording
     - `WS-B.1` quantified scope caveat
     - `WS-D revert` recommendation
     - `Rule G`

4. **Wait for the user’s per-WS decisions**
   The open decision matrix is:
   - `WS-A.1`: conditional accept?
   - `WS-C.1`: conditional accept?
   - `WS-F.1`: accept?
   - `WS-B.1`: conditional accept with caveat?
   - `WS-C.2`: accept?
   - `WS-D`: revert vs any alternative?

5. **Only after that**
   - decide whether to commit the corrective patch
   - decide whether to revert from history / keep with audit trail
   - decide how Stage 4 dispatch resumes

---

## 9. Things the New Codex Should Not Misread

### Do not misread “tests are green” as “governance is repaired”
That is false.

The repo now has enough technical evidence to review, but the governance decision is still pending.

### Do not misread `WS-D` sidecar code as a baseline to continue from
It should currently be treated as **reverted / to be removed**, not as “half-finished groundwork.”

### Do not misread `WS-B.1` as perfectly scoped
It already contains trigger logic that future `WS-B.2` would otherwise own.

### Do not misread `Rule G` as optional
It is the institutional response to the Stage 4 overreach incident.

---

## 10. Suggested Short Status for Human Teammates

If the next Codex needs a one-paragraph human-facing summary:

> Stage 4 is currently in a post-audit review state, not a normal execution state. A single earlier commit (`cd2f844b`) bundled multiple workstreams ahead of the approved dispatch sequence. That has now been retroactively audited, `WS-D` has been prepared for rollback, missing `WS-C.1` backend tests have been added, and Rule G has been drafted into the dispatch plan. The next step is reviewer/user adjudication per workstream, not more Stage 4 implementation.

---

## 11. Final Instruction

If you are the next Codex, your job is **not** to be fast here.

Your job is to:

- preserve the audit trail
- avoid expanding scope
- help the human make a clean per-workstream decision
- and only then resume disciplined Stage 4 execution

That is the safest way to protect both the product vision and the engineering governance we spent multiple rounds establishing.
