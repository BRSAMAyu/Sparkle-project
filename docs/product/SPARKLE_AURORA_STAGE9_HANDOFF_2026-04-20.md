# SPARKLE Aurora Stage 9 Handoff (2026-04-20)

> **Status**: engineering closeout baseline after autonomous Stage 9 execution
> **Purpose**: record the final landed Stage 9 workstreams, verification evidence, carried-forward limits, and the clean entry conditions for the next stage.

## 1. Final Accept Matrix

| Workstream | Status | Branch-tip commit | Notes |
| --- | --- | --- | --- |
| `WS-MET1` | accept | `4cebcc3d` | formalized prompt / inference utilization and landed backend aggregation hooks |
| `WS-IC1` | accept | `53c9c1cd` | exposed the canonical profile front door as an in-chat read surface with evidence-class legibility |
| `WS-IC2` | accept | `ba88af9f` | landed chat-native profile correction through the User Correction lane only |
| `WS-EV2` | accept | `98938aa6` | upgraded the evaluator to a rubric-driven runner with optional LLM-attached metadata |

## 2. What Stage 9 Actually Achieved

From the user-facing side, Stage 9 turned the profile system from a settings-like surface into a chat front door. The user can now ask what Sparkle currently believes, read a canonical profile card inside chat, and route claim corrections through the proper truth lane instead of being bounced back to hidden system plumbing.

From the system side, Stage 9 made two previously vague areas measurable and governable. Prompt / inference utilization now has a formal metric carrier, and the evaluator is no longer just a hardcoded fixture scorer: it produces rubric records, diagnostic summaries, and explicit metadata about whether scoring is rubric-only or LLM-attached, while staying inside `evaluation_records_only`.

## 3. Verification Evidence

### Frozen baseline re-run

Stage 8 compatibility baseline was re-run after all Stage 9 work closed:

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

Branch-tip baseline result:

- `144 passed`
- `0 failed`

### Stage 9 backend sweep

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/tools/test_growth_tools.py \
  tests/profile/eval/test_profile_eval_runner.py \
  tests/unit/test_prompt_signal_closure.py \
  tests/unit/test_ai_ops_dashboard.py \
  tests/unit/test_stage9_utilization_metrics.py \
  -q
```

- backend Stage 9 sweep: `27 passed`

### Stage 9 mobile sweep

```bash
cd mobile && flutter test \
  test/features/user/ \
  test/widget/profile_front_door_action_card_test.dart
```

- mobile Stage 9 sweep: `15 tests passed`

## 4. Rule-G Chain

Stage 9 landed under single-WS commits:

- `4cebcc3d` `feat(stage9): land WS-MET1 utilization baseline`
- `53c9c1cd` `feat(stage9): land WS-IC1 in-chat profile front door`
- `ba88af9f` `feat(stage9): land WS-IC2 in-chat profile correction lane`
- `98938aa6` `feat(stage9): land WS-EV2 rubric evaluator upgrade`

Stage-level documentation artifacts also landed without reopening WS scope:

- `2a514b1e` `docs(stage9): add dispatch plan and prerequisite artifacts`

## 5. Known Limits Carried Forward

1. `WS-IC1` and `WS-IC2` now expose readable evidence classes, but the front door still uses source / freshness / surface markers rather than clickable per-item `L0` evidence ids.
2. Chat correction is now a real User Correction lane, but it is still most reliable when the target claim id is explicit or comes from the immediately preceding front-door payload.
3. `WS-EV2` supports rubric-only and optional LLM-attached metadata, but no production LLM judge is wired in yet.
4. Graph-as-diagnostic remains infrastructure-first rather than a finished product surface.
5. Continuous-learning / distillation remains outside the user front door.
6. Tokenizer-aware inline budget precision (`RB1`) remains deferred.

## 6. Hard Constraints Inherited Forward

1. Rule K remains hard: no fact writes outside the allowed layered lanes.
2. Rule L remains hard: closure claims require a real consumer or runner path.
3. Rule M remains hard: no third compiler may emerge.
4. Rule N remains hard: a failing Rule K CI guard is merge-blocking.
5. Rule O remains hard: bounded steering allowlists must not expand silently.
6. Rule P remains hard: chat-originated profile correction must stay in the User Correction lane and must not pass through Aurora / L3 / strategy state.
7. Rule Q remains hard: in-chat profile claims must keep evidence class legible.
8. Rule R remains hard: evaluator outputs stay inside `evaluation_records_only`.

## 7. Next Entry Conditions

The next stage should treat the following as frozen baseline facts and must not relitigate them without regression evidence:

- prompt / inference utilization has a formal Stage 9 collection contract
- the canonical profile front door exists as an in-chat read surface
- chat-originated profile correction is real and remains separate from Stage 8 strategy steering
- the evaluator is rubric-driven and read-only, with optional LLM attachment metadata

The next stage should start from the remaining explicit product gaps:

- graph-as-diagnostic productization
- continuous-learning and distillation path integration
- stronger target-resolution and evidence-linking for open-ended in-chat profile correction
- utilization thresholding and interpretation beyond the current baseline metric carrier
