# SPARKLE Aurora Stage 25 Handoff (2026-04-21)

## 1. Final Accept Matrix

| WS | Status | Evidence |
| --- | --- | --- |
| `WS-RF-READ-API` | PASS | `RouteHistoryService.read_recent_decisions()` + `read_decision_chain()` landed with `user_id` hard requirement and cross-user blocking tests |
| `WS-RF-USER-CONTEXT` | PASS | `ReflectionAgent.reflect(..., user_id=...)` is now the primary entry; review-node call site updated; missing `user_id` raises `AssertionError` |
| `WS-RF-TRIGGER` | PASS | `TaskReflectionService.ELIGIBLE_CATEGORIES` expanded to 6 categories; `OutcomeVerifier` now emits `reflection_trigger_requested` and invokes trigger handling |
| `WS-RF-INJECT` | PASS | `route_history` context injection added with recency window, decision-chain lookup, Rule Y evidence markers, and hard token truncation |
| `WS-RF-QUALITY` | PASS | Rule AJ guards, Stage 25 kill-switch, Rule Y pass-rate downgrade logic, Aggregator `v1.6 recent_reflections`, proto sync, and mobile summary are all in place |

## 2. Path Choice

Path A.

Reason:

1. Reflection now consumes `route_history` in a user-scoped, read-only path.
2. New trigger categories can generate reflection outputs and write them back to `EpisodicMemory.inferred_extraction`.
3. `AURORA_REFLECTION_WIRE_MODE` remains default `off`, but `shadow` and `live` are both implemented and verified.

## 3. Rule AJ Trigger Registry Snapshot

Source of truth: [rule_aj_reflection_triggers.md](/Users/brsama/code/GitHub/Sparkle-project/docs/aurora/rule_aj_reflection_triggers.md)

Registered categories:

1. `too_difficult`
2. `unclear`
3. `abandoned`
4. `intervention_ineffective`
5. `plan_stall`
6. `overload`

Each category has:

1. A prompt template version `v1`
2. An independent env toggle
3. Registry coverage enforced by CI guard

## 4. SQAM Evidence

| Dimension | Result | Evidence |
| --- | --- | --- |
| `ID1` | PASS | 6 trigger categories are uniquely named and mapped in code + registry |
| `ST1` | PASS | `ReflectionAgent` now runs at `temperature=0.3`; trigger-mode tests verify stable entry contract |
| `DP1` | PASS | Rule Y pass-rate gate implemented and context token compliance is tested |
| `SM1` | PASS | Added metrics for trigger fire, context tokens, truncation, Rule Y pass-rate, LLM latency/cost, and skipped executions |

## 5. B3 LLM Budget

Stage 25 keeps reflection to at most one additional LLM call per trigger.

Measured / enforced evidence:

1. `ReflectionAgent` trigger-mode uses a single `generator.chat(...)` call.
2. Context injection is capped at `<= 800` tokens by `AURORA_REFLECTION_CONTEXT_MAX_TOKENS`.
3. Trigger-mode uses `temperature=0.3`.
4. Estimated cost is instrumented from router selection metadata. In unit harness, the synthetic budget path stayed at `~$0.001/trigger`, below the `$0.005` cap.
5. Synthetic trigger-path latency in unit harness was `~120ms`; runtime telemetry now records `sparkle_reflection_llm_latency_seconds`.

## 6. Rule Y Pass Rate

Rule Y write gating now runs on every live/shadow trigger execution.

Verified behavior:

1. Successful trigger write reports pass-rate `1.0`
2. Invalid candidate reports pass-rate `0.0`
3. Three consecutive `<95%` passes auto-degrade `AURORA_REFLECTION_WIRE_MODE` from `live` to `shadow`

## 7. Aggregator v1.6 Diff

New field:

1. `recent_reflections`

Shape:

1. `count`
2. `last_category`
3. `last_at`

Propagation:

1. `backend/app/state_aggregator/schema.py` -> `user_state.v1.6`
2. `proto/user_state.proto` -> regenerated stubs via `make proto-gen`
3. accountability API summary payload -> mobile dashboard model -> widget summary card

## 8. Cross-User Attack Coverage

Blocked cases:

1. `read_recent_decisions(user_id=None)` -> `ValueError`
2. `read_decision_chain(user_id=None, ...)` -> `ValueError`
3. Cross-user `decision_id` lookup returns empty chain
4. Reflection context injection excludes other users’ route-history rows

Primary tests:

1. `test_route_history_read_api.py`
2. `test_rule_aj_user_id_isolation.py`

## 9. Verification Summary

Primary Stage 25 suite:

1. `bash scripts/stage25/gate_final.sh` -> PASS
2. Backend Stage 25 targeted suite -> `50 passed`
3. Mobile Stage 25 widget suite -> `3 passed`

Regression checks:

1. Stage 24 gate -> PASS
2. Stage 24 backend regression bundle -> `39 passed`
3. Stage 23 gate -> PASS
4. Stage 23 regression bundle -> `50 passed`
5. `backend/.venv/bin/python scripts/check_proto_contract.py` -> PASS

Stage 25 governance guards:

1. `check_rule_aj_user_id_isolation.py` -> PASS
2. `check_reflection_trigger_registry.py` -> PASS
3. `check_reflection_user_id_propagation.py` -> PASS

## 10. Stage 26 Preconditions

Stage 26 may now assume:

1. Reflection outputs can be read as a user-scoped, recent summary signal
2. Route-history-backed reflection context is available behind a kill-switch
3. Trigger categories are frozen and registry-backed
4. Rule Y downgrade protection exists for reflection writes
