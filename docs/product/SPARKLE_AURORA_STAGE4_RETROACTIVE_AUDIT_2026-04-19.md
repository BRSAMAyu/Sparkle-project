# SPARKLE Aurora Stage 4 Retroactive Audit (2026-04-19)

> **Status**: Retroactive audit v4 with Stage 4 closeout addendum
> **Audit target**: commit `cd2f844b` (`stage 4 part1`)
> **Branch**: `Aurora-&-adaptive-harness-engineering`
> **Purpose**: reconstruct the governance evidence chain for Stage 4 work that was implemented ahead of the signed dispatch sequence.

---

## 1. Executive Summary

This audit does **not** approve continued Stage 4 execution by default.

It documents that commit `cd2f844b` landed a multi-workstream batch that crossed the intended dispatch boundaries of:

- `WS-A.1` Async Substrate
- `WS-C.1` TaskGuidance Skeleton
- `WS-F.1` Benchmark and Guardrails Prep
- `WS-B.1` Routing-Mode Seam
- `WS-C.2` TaskGuidance Productization
- and a **partial** `WS-D` Task Assistant Dormant Mode implementation

This means Stage 4 execution did **not** follow the signed per-wave / per-agent dispatch discipline.

However, the code and tests now present in the branch provide enough evidence to recommend a **retroactive accept-by-workstream** path for the completed slices, while explicitly marking `WS-D` as **partial / not accepted / not to be continued** until a fresh dispatch decision is made.

Since the initial audit draft:

- `WS-D` revert has landed as commit `4f90c1c6`
- `WS-C.1` backend CRUD coverage has landed as commit `573edf54`
- Claude + GLM independent review has aligned on the workstream decision matrix and on `Rule G`
- `WS-A.1` `P1` repair has landed as commit `79cdb8ad`
- `WS-B.1` scope tightening has landed as commit `a5f5387c`
- `WS-D` rebuilt dormant-mode implementation has landed as commit `804e28f9`
- `WS-B.2` escalation completion has landed as commit `2d2b4a5a`
- `WS-E` closed-loop UX has landed as commit `448ef9e3`

### Audit disposition

| Workstream | Status | Disposition |
| --- | --- | --- |
| `WS-A.1` Async Substrate | implemented + tested | conditional retroactive accept candidate |
| `WS-C.1` TaskGuidance Skeleton | implemented + tested | conditional retroactive accept candidate |
| `WS-F.1` Benchmark and Guardrails Prep | implemented + tested | retroactive accept candidate |
| `WS-B.1` Routing-Mode Seam | implemented + tested | conditional retroactive accept candidate with quantified scope caveat |
| `WS-C.2` TaskGuidance Productization | implemented + tested | retroactive accept candidate |
| `WS-D` Task Assistant Dormant Mode | partial only | **do not accept; revert recommended** |

### Recommended path

This audit recommends the equivalent of **Option B: Retroactive Audit + Accept**:

1. freeze any further Stage 4 implementation
2. treat `WS-D` as partial and out of scope for merge/expansion
3. let Claude + GLM review this audit
4. let the user retroactively decide which completed Stage 4 slices to accept
5. revert `WS-D` partial work rather than quarantining it as future baseline code
6. only then resume Stage 4 dispatch from a clean gate

---

## 2. Governance Finding

The core problem is **process**, not just code shape.

The intended Stage 4 governance model was:

- signed vision alignment
- signed engineering structure
- signed dispatch plan
- Wave `1a` agents `A / B / C` in parallel
- `Gate S4-1`
- Wave `1b` agent `D`
- `Gate S4-2`
- Wave `2`

Instead, commit `cd2f844b` bundled work from multiple waves/workstreams into one batch.

### What was bypassed

- `Gate S4-0` was not explicitly closed by a user-facing execution decision before implementation began
- Wave `1a` did not run as distinct agents `A / B / C`
- `Gate S4-1` was not independently reviewed before `WS-B.1` work appeared
- Wave `1b` work (`WS-B.1`) was folded into the same commit
- `WS-C.2` product surface work also landed before a clean Wave `2` dispatch
- `WS-D` work was started despite not yet being ready for dispatch or review

### Additional governance concern

The same commit also contains files outside the signed Stage 4 dispatch scope:

- `backend/gateway/internal/infra/logger/logger.go`
- `scripts/dev_local_stack.sh`

These are not evaluated in this audit as Stage 4 deliverables and should be reviewed separately.

---

## 3. Commit Inventory

`git show --stat --summary cd2f844b` reports:

- `38` files changed
- `5369` insertions
- `168` deletions

### Stage 4 files inside `cd2f844b`

#### `WS-A.1` candidates

- `backend/app/aurora/context.py`
- `backend/app/aurora/tasks.py`
- `backend/app/aurora/observability/benchmark.py`
- `backend/app/aurora/observability/tiering.py`
- `backend/app/aurora/engine.py`

#### `WS-C.1` candidates

- `backend/app/task_guidance/__init__.py`
- `backend/app/task_guidance/schemas.py`
- `backend/app/task_guidance/store.py`
- `backend/app/services/task_guide_service.py`
- `backend/app/api/v1/tasks.py`
- `mobile/lib/features/task/data/repositories/task_repository.dart`
- `mobile/lib/features/task/presentation/providers/task_provider.dart`

#### `WS-F.1` candidates

- `backend/tests/aurora/stage4_eval_support.py`
- `backend/tests/aurora/test_deterministic_performance_baseline.py`
- `backend/tests/aurora/test_stage4_eval_guardrails.py`

#### `WS-B.1` candidates

- `backend/app/aurora/decision_fns/__init__.py`
- `backend/app/aurora/decision_fns/backbone.py`
- `backend/app/orchestration/routing_engine.py`
- `backend/tests/unit/orchestrator/mixins/test_routing_engine_stage4.py`

#### `WS-C.2` candidates

- `mobile/lib/core/constants/app_constants.dart`
- `mobile/lib/features/plan/data/services/plan_guide_generator.dart`
- `mobile/lib/features/plan/presentation/screens/plan_create_screen.dart`
- `mobile/lib/features/task/presentation/screens/task_detail_screen.dart`
- `mobile/lib/features/task/presentation/widgets/guidance/task_guidance_surface.dart`
- `mobile/test/widget/j1_frontend_closure_test.dart`

#### `WS-D` partial candidates

- `backend/app/api/v1/chat.py`
- `backend/app/task_assistant/__init__.py`
- `backend/app/task_assistant/schemas.py`
- `backend/app/task_assistant/service.py`
- `mobile/lib/features/chat/data/repositories/chat_repository.dart`
- `mobile/lib/features/task/presentation/providers/task_chat_provider.dart`

---

## 4. Verification Evidence

## 4.1 Backend Stage 4 subset

Command:

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/aurora/test_deterministic_performance_baseline.py \
  tests/aurora/test_stage4_eval_guardrails.py \
  tests/aurora/test_policy_and_decision_fns.py \
  tests/unit/orchestrator/mixins/test_routing_engine_stage4.py -q
```

Result:

- `19 passed`
- `1 warning`

Warning:

- report-only `P1` guardrail finding from `backend/app/aurora/tasks.py:127`
- message:
  - `nearline tier must communicate through primitives / prior_outputs, not inline implementations [from app.aurora.engine import AuroraEngine]`

Interpretation:

- `WS-F.1` report-only guardrail is active as intended
- `WS-A.1` / `WS-B.1` code currently passes its test surface
- the warning is **not** ordinary architectural debt; it is evidence that `WS-A.1` currently violates the Stage 4 `P1` constitutional rule at the substrate layer
- therefore `WS-A.1` should be treated as **conditional accept only**, pending a repair plan before `Wave 1b / Gate S4-2`

## 4.2 Backend Aurora suite

Command:

```bash
cd backend && ./.venv/bin/python -m pytest tests/aurora -q
```

Result:

- `78 passed`
- `1 warning`

Interpretation:

- the broader Stage 3 + Stage 4 Aurora baseline still holds
- the same report-only `P1` warning is the only visible degradation in the current suite

## 4.2a Acceptance Verification Addendum

The original audit draft under-verified three dispatch-plan acceptance statements.

They are explicitly checked here.

### A2.1 `WS-A.1` flags-off routing stability

Command:

```bash
cd backend && \
  AURORA_ACTIVE=false \
  AURORA_SHADOW_MODE=false \
  AURORA_ROUTING_MODE_ENABLED=false \
  ./.venv/bin/python -m pytest tests/unit/orchestrator/mixins/test_routing_engine_stage4.py -q
```

Result:

- `3 passed`

Interpretation:

- the `WS-B.1` seam keeps current `direct`-equivalent behavior when the feature flag is off
- this satisfies the relevant flags-off acceptance evidence for `WS-A.1` / `WS-B.1`

### A2.2 `WS-C.1` frozen-schema discipline

Command:

```bash
git diff 31812c94..cd2f844b -- backend/app/aurora/schemas/
```

Result:

- no output

Interpretation:

- the frozen Gate 0 Aurora schema tree was not edited by the Stage 4 batch

### A2.3 Corpus V1 size and distribution

Command:

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
- `categories {'casual_direct': 4, 'workflow_plan': 4, 'task_assistant': 4, 'escalation': 4, 'fallback_or_miss': 4}`
- `routing {'direct': 8, 'workflow': 8, 'task_assistant': 4}`

Interpretation:

- Corpus V1 is not just scaffolded; it is fully materialized at the required `>=20` size with balanced category coverage

## 4.3 Mobile `WS-C.2` surface

Analyze command:

```bash
cd mobile && flutter analyze \
  lib/core/constants/app_constants.dart \
  lib/features/plan/data/services/plan_guide_generator.dart \
  lib/features/plan/presentation/screens/plan_create_screen.dart \
  lib/features/task/data/repositories/task_repository.dart \
  lib/features/task/presentation/providers/task_provider.dart \
  lib/features/task/presentation/screens/task_detail_screen.dart \
  lib/features/task/presentation/widgets/guidance/task_guidance_surface.dart \
  test/widget/j1_frontend_closure_test.dart
```

Result:

- `No issues found!`

Widget test command:

```bash
cd mobile && flutter test test/widget/j1_frontend_closure_test.dart
```

Result:

- `6 passed`

Interpretation:

- `WS-C.2` product surface is currently green on its dedicated analyze + widget surface

## 4.4 Mobile `WS-D` partial surface

Analyze command:

```bash
cd mobile && flutter analyze \
  lib/core/constants/app_constants.dart \
  lib/features/chat/data/repositories/chat_repository.dart \
  lib/features/task/presentation/providers/task_chat_provider.dart \
  lib/features/task/presentation/widgets/task_chat_panel.dart \
  lib/features/task/presentation/screens/task_execution_screen.dart
```

Result:

- exit code `1`
- one new warning attributable to Stage 4 partial work:
  - `lib/features/task/presentation/providers/task_chat_provider.dart:267:44`
  - `unnecessary_null_comparison`
- remaining analyzer output consists of pre-existing `info` items from `task_execution_screen.dart`

Interpretation:

- `WS-D` is not complete and should not be treated as green
- current state is closer to an exploratory seam than an accepted wave deliverable

---

## 5. Workstream-by-Workstream Assessment

## 5.1 `WS-A.1` Async Substrate

### Evidence

- new tier context and async payload carrier in `backend/app/aurora/context.py`
- Celery entrypoints in `backend/app/aurora/tasks.py`
- benchmark/tiering instrumentation in `backend/app/aurora/observability/`
- tests green in the Stage 4 backend subset

### Acceptance mapping

Dispatch-plan acceptance required:

- Celery nearline path exists and is testable
- inline benchmark harness exists with `>=20` representative cases
- no Stage 3 routing regression when flags are off

### Audit judgment

**Conditional retroactive accept candidate**

Reason:

- substrate seams exist
- tests show benchmark/guardrail path is active
- no regression surfaced in the Aurora suite

### Open issue

The report-only `P1` finding in `backend/app/aurora/tasks.py` is a constitutional violation, not ordinary debt:

- `nearline` currently reaches into `AuroraEngine` directly
- the Stage 4 `P1` rule explicitly forbids cross-tier communication except through primitives / `prior_outputs`

This workstream should only be accepted **conditionally** on a repair plan. The recommended path is:

- keep the current code as evidence-bearing substrate work
- require a concrete fix plan before `Wave 1b / Gate S4-2`
- do not silently downgrade this finding to "tracked debt"

## 5.2 `WS-C.1` TaskGuidance Skeleton

### Evidence

- new `backend/app/task_guidance/` sidecar module
- `TaskGuidance` sidecar schema with UUID references
- backend seams in:
  - `backend/app/services/task_guide_service.py`
  - `backend/app/services/task_service.py`
  - `backend/app/api/v1/tasks.py`
- mobile repository/provider seams in:
  - `mobile/lib/features/task/data/repositories/task_repository.dart`
  - `mobile/lib/features/task/presentation/providers/task_provider.dart`

### Acceptance mapping

Dispatch-plan acceptance required:

- sidecar object can be created and retrieved
- repository/provider seams can consume the new object model
- no Gate 0 schema edits

### Audit judgment

**Conditional retroactive accept candidate**

Reason:

- code structure follows the dispatch plan
- mobile seams are in place
- no frozen Aurora schema edits were introduced as part of the sidecar object model

### Evidence closure

The original backend endpoint test gap has now been closed by commit `573edf54`.

Dedicated coverage now exists in:

- `backend/tests/api/test_task_guidance_api.py`

Current result:

- `2 passed`

Covered behaviors:

- create human guidance
- retrieve human guidance
- create AI guidance
- verify UUID-based `source_guidance_id` reference integrity

## 5.3 `WS-F.1` Benchmark and Guardrails Prep

### Evidence

- `backend/tests/aurora/stage4_eval_support.py`
- `backend/tests/aurora/test_deterministic_performance_baseline.py`
- `backend/tests/aurora/test_stage4_eval_guardrails.py`
- current test run: `19 passed, 1 warning`

### Acceptance mapping

Dispatch-plan acceptance required:

- Corpus V1 runnable in CI
- P1 enforcement exists in lint/test/CI form, starting in report-only mode
- Stage 4 eval placeholders ready before Wave 1b

### Audit judgment

**Retroactive accept candidate**

Reason:

- Corpus V1 and guardrail scaffolding are concretely present
- report-only mode behavior is explicit and functioning

## 5.4 `WS-B.1` Routing-Mode Seam

### Evidence

- `RoutingMode` behavior in `backend/app/aurora/decision_fns/backbone.py`
- `backend/app/orchestration/routing_engine.py` consumes routing mode
- dedicated tests in `backend/tests/unit/orchestrator/mixins/test_routing_engine_stage4.py`
- current test run passes

### Acceptance mapping

Dispatch-plan acceptance required:

- `routing_mode` computed and consumed cleanly
- flags-off behavior stable
- no pre-tool-selection / pre-response-formatting takeover

### Audit judgment

**Conditional retroactive accept candidate with quantified scope caveat**

Reason:

- direct/workflow/task_assistant modes exist
- tests confirm flags-off stability and basic mode promotion behavior

### Quantified scope caveat

`WS-B.1` was supposed to add the routing seam and **not** implement full escalation.

Function-level split in `backend/app/aurora/decision_fns/backbone.py`:

- `lines 13-18`
  - `RoutingMode` enum
  - clearly `WS-B.1`
- `lines 21-45`
  - `_PLANNING_MARKERS` and `_TASK_ASSISTANT_MARKERS`
  - routing seam support; still consistent with `WS-B.1`
- `lines 61-80`
  - `_classify_routing_mode(...)`
  - **this is where scope bleeds**
  - `optional.get("task_card_id")` and message marker checks are seam-level
  - but these checks are already escalation-adjacent:
    - `structural_topic_turns >= 2` (`line 73`)
    - `enhanced["frustration_signal"]` (`line 74`)
    - `enhanced["repeated_failure"]` (`line 75`)
    - `core["commitment_conflict"]` (`line 76`)
- `lines 83-123`
  - `decide_backbone_route(...)`
  - still structurally `WS-B.1`, but it now consumes the pre-escalation-sensitive routing classification above

Conclusion:

- `WS-B.1` did **not** implement full workflow escalation orchestration
- but it **did** pre-spend part of the `WS-B.2` trigger logic budget by embedding trigger criteria into routing-mode classification

Future `WS-B.2` dispatch must therefore treat `_classify_routing_mode(...)` as pre-existing seam logic, not as untouched ground.

## 5.5 `WS-C.2` TaskGuidance Productization

### Evidence

- feature flag in `mobile/lib/core/constants/app_constants.dart`
- task guidance surface in `mobile/lib/features/task/presentation/widgets/guidance/task_guidance_surface.dart`
- integration in:
  - `task_detail_screen.dart`
  - `plan_create_screen.dart`
  - `plan_guide_generator.dart`
- dedicated widget test suite passes
- dedicated analyze surface is clean

### Acceptance mapping

Dispatch-plan acceptance required:

- human-guide default generation path
- AI-guide on-demand path
- guide version retrieval / refresh rules
- quality hooks for Corpus V3

### Audit judgment

**Retroactive accept candidate**

Reason:

- user-default + AI-on-demand split is concretely implemented
- product surface is functioning on its dedicated test/analyze surface

## 5.6 `WS-D` Task Assistant Dormant Mode

### Evidence

- new sidecar module:
  - `backend/app/task_assistant/`
- `/chat/task/{task_id}` path now accepts task-assistant context in `backend/app/api/v1/chat.py`
- mobile provider/repository changes:
  - `mobile/lib/features/chat/data/repositories/chat_repository.dart`
  - `mobile/lib/features/task/presentation/providers/task_chat_provider.dart`
- mobile analyze still reports one new warning attributable to this work

### Acceptance mapping

Dispatch-plan acceptance required:

- 5-item initial injection set
- cold-start fallback
- strong-signal refresh rules only
- assistant outcome capture for nearline optimization
- DORMANT remains sidecar/candidate semantics

### Audit judgment

**Partial / not accepted**

Reason:

- implementation was started before proper dispatch
- UI integration is incomplete
- no dedicated acceptance test suite was run for the full dormant-mode path
- this work should not be treated as green simply because some sidecar files exist

### Corrective action landed

The recommended revert has now landed as commit `4f90c1c6`.

Removed surfaces:

- `backend/app/api/v1/chat.py`
- `backend/app/task_assistant/`
- `mobile/lib/features/chat/data/repositories/chat_repository.dart`
- `mobile/lib/features/task/presentation/providers/task_chat_provider.dart`
- `mobile/lib/core/constants/app_constants.dart`

Note:

- the mobile flag cleanup also removed two unreferenced out-of-scope flags that were introduced by `cd2f844b` alongside the dormant-mode batch; they were not pre-existing baseline flags

---

## 6. Additional Audit Notes

## 6.1 Commit vs working-tree reality

The original governance concern assumed "do not commit yet".

As of this audit:

- the Stage 4 batch is **already committed** in `cd2f844b`
- current working-tree changes (`Makefile`, gateway module files, logger, local stack script) are separate and out of scope for this Stage 4 audit

This means the recovery path is no longer "prevent commit" but "decide whether to keep, partially accept, or surgically revert committed Stage 4 slices."

## 6.2 Recommended classification for reviewers

If Claude + GLM review this audit, the cleanest reviewer vocabulary is:

- `accepted retroactively`
- `accepted retroactively with caveat`
- `partial / not accepted`

That matches the reality of the code more closely than pretending the dispatch sequence was followed.

## 6.3 Post-audit remediation landed after the initial draft

After the initial audit draft, three corrective actions were landed as atomic follow-up changes:

1. **`WS-D` partial revert landed**
   - commit: `4f90c1c6`
   - message: `revert(stage4): remove WS-D task assistant dormant mode`
   - scope:
     - `backend/app/api/v1/chat.py`
     - `backend/app/task_assistant/`
     - `mobile/lib/features/chat/data/repositories/chat_repository.dart`
     - `mobile/lib/features/task/presentation/providers/task_chat_provider.dart`
     - `mobile/lib/core/constants/app_constants.dart`

2. **`WS-C.1` backend CRUD proof landed**
   - commit: `573edf54`
   - message: `test(stage4): add WS-C.1 task guidance CRUD coverage`
   - new test file:
     - `backend/tests/api/test_task_guidance_api.py`
   - current result:
     - `2 passed`

3. **Dispatch hardening landed**
   - `SPARKLE_AURORA_STAGE4_DISPATCH_PLAN_2026-04-19.md` is now draft `v3`
   - `Rule G` is explicitly drafted there as the governance follow-up to this incident

These are corrective governance-alignment commits, not resumed Stage 4 feature execution.

## 6.4 Independent review alignment

Independent Claude + GLM review aligned on the following points:

- `WS-A.1`: conditional accept, with the `P1` issue treated as a constitutional violation and repair plan required before `Wave 1b / Gate S4-2`
- `WS-C.1`: conditional accept, with backend CRUD evidence now closed
- `WS-F.1`: accept
- `WS-B.1`: conditional accept with quantified caveat; future `WS-B.2` must treat the current routing classification seam as occupied ground
- `WS-C.2`: accept
- `WS-D`: revert
- `Rule G`: keep in the dispatch plan as a standing governance rule

## 6.5 Branch-tip remediation after audit v2

Two remaining code-level conditions from audit v2 have now been repaired on the current branch tip:

1. **`WS-A.1` `P1` repair landed**
   - commit: `79cdb8ad`
   - `backend/app/aurora/tasks.py` no longer imports or instantiates `AuroraEngine`
   - nearline / long-horizon task entrypoints now consume only:
     - `snapshot` references
     - `prior_outputs` primitives
   - verification:
     - `tests/aurora/test_async_substrate_tasks.py`
     - `tests/aurora/test_stage4_eval_guardrails.py`
     - guardrail report now returns `has_findings False`

2. **`WS-B.1` scope tightening landed**
   - commit: `a5f5387c`
   - `backend/app/aurora/decision_fns/backbone.py` now limits routing-mode classification to:
     - planning markers
     - task-assistant markers
   - it no longer pre-spends escalation-adjacent triggers such as:
     - `structural_topic_turns`
     - `frustration_signal`
     - `repeated_failure`
     - `commitment_conflict`
   - `backend/app/orchestration/routing_engine.py` no longer injects those escalation cues into the Stage 4 routing-mode seam

### Current branch-tip disposition

After commits `4f90c1c6`, `573edf54`, `79cdb8ad`, `a5f5387c`, `804e28f9`, `2d2b4a5a`, and `448ef9e3`, the current branch tip supports the following disposition:

| Workstream | Current branch-tip status |
| --- | --- |
| `WS-A.1` Async Substrate | **accept** |
| `WS-C.1` TaskGuidance Skeleton | **accept** |
| `WS-F.1` Benchmark and Guardrails Prep | **accept** |
| `WS-B.1` Routing-Mode Seam | **accept** |
| `WS-B.2` Escalation Completion | **accept** |
| `WS-C.2` TaskGuidance Productization | **accept** |
| `WS-D` Task Assistant Dormant Mode | **accept** |
| `WS-E` Closed-Loop UX and Product Surface | **accept** |

### Stage 4 closeout addendum

Wave 2 is now implemented and review-ready at the branch tip.

The final Wave 2 landings are:

1. `804e28f9` — `feat(stage4): rebuild WS-D dormant task assistant mode`
2. `2d2b4a5a` — `feat(stage4): complete WS-B.2 escalation flow`
3. `448ef9e3` — `feat(stage4): land WS-E closed-loop chat UX`

Independent Codex verification on the landed code covered:

- `cd backend && ./.venv/bin/python -m pytest tests/unit/test_task_assistant_dormant.py -q` -> `20 passed`
- `cd backend && ./.venv/bin/python -m pytest tests/unit/orchestrator/mixins/test_routing_engine_stage4.py tests/aurora/test_stage4_eval_guardrails.py -q` -> `17 passed`
- `cd mobile && flutter test test/features/task/presentation/providers/task_chat_dormant_test.dart` -> `14 passed`
- `cd mobile && flutter test test/features/chat/presentation/providers/guidance_mode_provider_test.dart test/features/chat/presentation/widgets/capability_ceiling_card_test.dart test/features/chat/presentation/widgets/mode_transition_test.dart` -> `17 passed`
- `cd mobile && flutter analyze lib/features/chat/presentation/providers/chat_provider.dart lib/features/chat/presentation/providers/guidance_mode_provider.dart lib/features/chat/presentation/screens/chat_screen.dart lib/features/chat/presentation/widgets/chat_bubble.dart lib/features/chat/presentation/widgets/chat_mode_selector_sheet.dart lib/features/chat/presentation/widgets/capability_ceiling_card.dart lib/features/chat/presentation/widgets/chat_mode_transition_banner.dart lib/features/chat/presentation/widgets/guidance_mode_toggle.dart` -> `No issues found!`

The earlier `WS-D` revert remains historically correct as an incident-response step. The later rebuild does not invalidate the audit; it closes the previously deferred Wave 2 work under stricter scope, review, and commit discipline.

---

## 7. Recommendation

### Recommended path

Treat Stage 4 as **implementation-complete and ready for final external review / sign-off**.

### Specifically

1. accept `WS-F.1`
2. accept `WS-C.2`
3. accept `WS-A.1`
4. accept `WS-C.1`
5. accept `WS-B.1`
6. accept `WS-B.2`
7. accept `WS-D`
8. accept `WS-E`
9. keep `Rule G`, `Rule H`, and `Rule I` as standing governance controls for future stages

### What this audit does **not** recommend

- it does **not** recommend resuming unordered feature work outside a signed plan
- it does **not** recommend pretending the dispatch sequence was followed
- it does **not** recommend treating constitutional violations as normal debt items

### Dispatch hardening recommendation

The dispatch plan should be upgraded with a new governance rule, not just a history note:

> **Rule G · Single-WS-per-Agent Commit Discipline**: a single agent commit must not touch more than one workstream's primary write zone unless the dispatcher explicitly authorizes a cross-WS batch. Violations default to revert; retroactive accept is the exception and requires independent review.

---

## 8. User-Facing Summary

Stage 4 code has advanced further than the signed dispatch sequence allowed.

The good news is that most of the implemented slices appear technically sound and test green:

- async substrate
- TaskGuidance sidecar
- benchmark/guardrail prep
- routing-mode seam
- TaskGuidance product surface

The bad news is that this happened through one bundled implementation wave instead of the signed gate/agent sequence, and `WS-D` was started prematurely.

The corrective state is now materially stronger than the original audit draft:

- `WS-D` is no longer just "recommended for revert"; the revert has landed
- `WS-C.1` no longer has an endpoint-test gap; the backend CRUD proof has landed
- `Rule G` is written into the dispatch plan
- Claude + GLM review is aligned on the per-workstream disposition matrix

Therefore the honest next step is:

> complete final expert/user review on the landed Stage 4 branch tip, then close Stage 4 and move planning attention to Stage 5 / Wave 3.
