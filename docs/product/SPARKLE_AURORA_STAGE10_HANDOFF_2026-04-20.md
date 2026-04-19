# SPARKLE Aurora Stage 10 Handoff (2026-04-20)

> **Status**: engineering closeout baseline after autonomous Stage 10 execution
> **Purpose**: record the final landed Stage 10 workstreams, verification evidence, carried-forward limits, and the clean entry conditions for the next stage.

## 1. Final Accept Matrix

| Workstream | Status | Branch-tip commit | Notes |
| --- | --- | --- | --- |
| `WS-EV3` | accept | `c29f9887` | attached a real Stage 10 LLM-judge adapter to the evaluator runner while preserving `evaluation_records_only` |
| `WS-EVD1` | accept | `c9e7f7b8` | upgraded the in-chat profile front door from source markers to clickable `L0` evidence refs |
| `WS-G2D` | accept | `edae7714` | landed a graph-derived "我哪里弱" diagnostic surface as a user-visible chat card |

Stage-level documentation artifacts also landed without reopening workstream scope:

| Artifact | Commit | Notes |
| --- | --- | --- |
| dispatch plan + prerequisite artifacts | `ea691cd6` | Stage 10 baseline, Rule S/T freeze, and three pre-implementation boundary documents |

## 2. What Stage 10 Actually Achieved

From the user-facing side, Stage 10 made Sparkle's front door more trustworthy and more concrete. The user can now click through from a profile claim to allowed `L0` evidence refs instead of reading only abstract source markers, and can ask "我哪里弱" to receive a graph-derived diagnostic card rather than a generic graph browser answer.

From the system side, Stage 10 deepened two important trust seams without widening write authority. The evaluator now has a real LLM-judge attachment path with explicit contract metadata and graceful downgrade behavior, while graph diagnostics remain consumption-only and evidence drill-down remains bounded to resolver-supported raw-facing refs.

## 3. Verification Evidence

### Frozen Stage 9 baseline re-run

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/aurora \
  tests/api/test_profile_transparency_api.py \
  tests/profile/eval/test_profile_eval_skeleton.py \
  tests/profile/test_intervention_verification_loop.py \
  tests/unit/test_situation_brief.py \
  tests/unit/test_phase2_intervention_pipeline.py \
  -q
```

- Stage 9 frozen baseline: `144 passed`

### Stage 10 backend sweep

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/tools/test_growth_tools.py \
  tests/profile/eval/test_profile_eval_runner.py \
  tests/profile/eval/test_profile_eval_llm_judge.py \
  tests/unit/test_prompt_signal_closure.py \
  tests/unit/test_ai_ops_dashboard.py \
  tests/unit/test_stage9_utilization_metrics.py \
  -q
```

- Stage 10 backend sweep: `31 passed`

### Stage 10 mobile sweep

```bash
cd mobile && flutter test \
  test/features/user/ \
  test/widget/profile_front_door_action_card_test.dart \
  test/widget/graph_diagnostic_card_test.dart
```

- Stage 10 mobile sweep: `17 tests passed`

### Rule K guard

```bash
backend/.venv/bin/python scripts/check_rule_k_write_paths.py
```

- Rule K guard: `✅ Rule K write-path guard passed (35 files scanned)`

## 4. Representative Samples

### 4.1 EV3 judge sample

Real Stage 10 CLI run:

```bash
cd backend && ./.venv/bin/python -m app.services.profile_eval_runner \
  --fixture prediction_accuracy_baseline.json \
  --llm-judge real \
  --pretty
```

Observed sample:

- `runner_version = "stage10.ev3.runner.v1"`
- `scoring_mode = "llm_attached"`
- `judge_contract_version = "stage10.ev3.judge.v1"`
- attached run produced a structured `llm_attachment` payload
- the live sample degraded to rubric score because the judge hit the `8s` timeout budget and returned `fallback_used = true`, `fallback_reason = "TimeoutError"`

This is still governance-correct because the output stayed inside `evaluation_records_only` and did not fail the runner.

### 4.2 Clickable evidence sample

Representative front-door payload excerpt captured from the landed Stage 10 service path:

```json
{
  "evidence_resolution": "l0_clickable_refs",
  "claim_excerpt": {
    "id": "achievement_motivation_response",
    "evidence_refs": [
      {"type": "concept", "id": "9c8f3cb3-bd56-4d55-9bb3-a7bbac2ef001", "schema_version": "concept.v1"},
      {"type": "error", "id": "c5f9d6f1-61fa-4fc0-a0ca-8af50a6b1234", "schema_version": "error.v1"}
    ],
    "evidence_summary": "2 条可点击依据"
  },
  "prediction_excerpt": {
    "id": "overload_risk",
    "evidence_refs": [
      {"type": "concept", "id": "9c8f3cb3-bd56-4d55-9bb3-a7bbac2ef001", "schema_version": "concept.v1"}
    ],
    "evidence_summary": "1 条可点击依据"
  }
}
```

### 4.3 Graph diagnostic sample

Representative Stage 10 tool payload from the landed `graph_diagnostic` surface contract:

```json
{
  "title": "你当前最薄弱的知识点",
  "summary": "当前最弱的是热力学第二定律。",
  "weak_nodes": [
    {
      "node_name": "热力学第二定律",
      "mastery": 41.0,
      "why": "掌握度已经落到明显偏低区间。",
      "prerequisite_names": ["热机效率"],
      "downstream_names": ["熵增方向判断"],
      "route": "/galaxy/node/node-1",
      "prompt": "带我看看这个点为什么会卡住。"
    }
  ],
  "binding_note": "这个诊断面只消费现有 graph / mastery 数据，不会直接改写任何用户状态。"
}
```

## 5. Rule-G Chain

- `ea691cd6` `docs(stage10): add dispatch plan and prerequisite artifacts`
- `c29f9887` `feat(stage10): land WS-EV3 llm judge attachment`
- `c9e7f7b8` `feat(stage10): land WS-EVD1 clickable evidence resolution`
- `edae7714` `feat(stage10): land WS-G2D graph diagnostic surface`

## 6. Known Limits Carried Forward

1. `WS-EV3` has a real judge attachment path, but the live sample on this branch timed out and gracefully fell back to rubric score inside the `8s` budget; Stage 11 should harden runtime availability and latency if we want stronger live-judge coverage.
2. `WS-EVD1` currently resolves only through the existing evidence resolver's supported raw-facing types; unsupported refs still remain explicitly absent or redacted rather than magically resolvable.
3. `WS-G2D` currently ships as a chat-native diagnostic card; it is graph-derived and user-visible, but not yet a richer dedicated Galaxy diagnostic workspace.
4. continuous-learning / distillation remains outside the user-facing product loop.
5. tokenizer-aware inline budget precision (`RB1`) remains deferred.

## 7. Hard Constraints Inherited Forward

1. Rule K remains hard: no fact writes outside the allowed layered lanes.
2. Rule L remains hard: closure claims require a real consumer or runner path.
3. Rule M remains hard: no third compiler may emerge.
4. Rule N remains hard: a failing Rule K CI guard is merge-blocking.
5. Rule O remains hard: bounded steering allowlists must not expand silently.
6. Rule P remains hard: chat-originated profile correction must stay in the User Correction lane and must not pass through Aurora / L3 / strategy state.
7. Rule Q remains hard: in-chat profile claims must keep evidence class legible.
8. Rule R remains hard: evaluator outputs stay inside `evaluation_records_only`.
9. Rule S remains hard: LLM-judge outputs stay isolated to evaluation records and must degrade gracefully.
10. Rule T remains hard: graph-as-diagnostic remains read-only and must not open a new write lane.

## 8. Next Entry Conditions

The next stage should treat the following as frozen baseline facts and must not relitigate them without regression evidence:

1. the evaluator has a real Stage 10 judge attachment path plus explicit fallback semantics
2. the canonical profile front door now supports clickable `L0` evidence refs
3. graph diagnostics now exist as a user-visible read surface
4. Rule K still holds locally and in CI

The next stage should start from the remaining explicit product gaps:

1. live judge stability / timeout hardening
2. dedicated Galaxy diagnostic deepening beyond the chat card
3. continuous-learning / distillation user-visible integration
4. utilization interpretation beyond the current carrier
5. tokenizer-aware inline budget precision (`RB1`)
