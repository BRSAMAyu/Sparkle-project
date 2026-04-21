# SPARKLE Aurora Stage 29.5 Handoff

Date: 2026-04-21
Stage: Repo Hygiene / Governance Repair
Scope: no Stage 30 business expansion

## Executive Summary

Stage 29.5 is complete. The repo hygiene blockers identified after Stage 29 are now repaired:

- Aggregator schema v1.10 is aligned across proto, Python runtime schema, Go, and Dart.
- Python now has generated `user_state_pb2` stubs in workspace, while runtime continues to use the hand-written adapter schema guarded by new Rule AQ parity checks.
- CI now runs a single `all-rule-guards` job that executes 17 rule guards, instead of only Rule K.
- Rule AB now has a formal whitelist and AST-level enforcement.
- Stage 19 and Stage 22 no longer have silent Alembic gaps.
- Missing or weak guards for Y / AG / AE / AJ / AM were replaced with real automated checks.

## Path Choice

Selected path: `beta-with-generated-stubs`

Reason:

1. `backend/app/state_aggregator/schema.py` is already the runtime contract used broadly across the Python backend, so replacing it with a pb2-native wrapper inside this hygiene stage would have created avoidable behavior risk.
2. The original root problem was not only missing runtime parity, but also a broken proto chain on Python. We repaired that chain by generating Python `user_state_pb2.py` and then added Rule AQ so the hand-written runtime schema cannot drift from proto again.
3. This keeps Stage 29.5 narrowly scoped to hygiene while still restoring the `proto -> generated -> implementation` discipline.

## Final Accept Matrix

| workstream | result | notes |
| --- | --- | --- |
| WS-HG-PROTO-SYNC | PASS | `proto/user_state.proto` gained fields 17/18/19; Python `user_state_pb2` generation restored; Rule AQ added |
| WS-HG-CI-GUARDS | PASS | `scripts/run_all_rule_guards.sh` added; `.github/workflows/ci.yml` now runs `all-rule-guards` |
| WS-HG-AB-EXEMPTION | PASS | Rule AB whitelist documented and AST-enforced |
| WS-HG-MIGRATION-FILL | PASS | Stage 19 / 22 no-op revisions added; merged to one head |
| WS-HG-RULE-Y-AG-GUARDS | PASS | dedicated Rule Y / AG guards added and wired into CI |
| WS-HG-AE-AJ-AM-REWRITE | PASS | weak string-match guards replaced with AST/static checks |

## Proto / Schema Alignment

Top-level `UserStateV1` contract now resolves as follows:

| field | proto | Python runtime schema |
| --- | --- | --- |
| `commitment_summary` | yes | yes |
| `pending_policies` | yes | yes |
| `recent_person_mentions` | yes | yes |
| `engagement_state` | yes | yes |
| `learning_state` | yes | yes |
| `working_memory_snapshot` | yes | yes |
| `task_sufficiency_summary` | yes | yes |
| `context_sufficiency_summary` | yes | yes |
| `recent_reflections` | yes | yes |
| `recent_scenes` | yes | yes |
| `foresight_hint` | yes | yes |
| `traits_prior` | yes | yes |
| `srl_phase` | yes | yes |
| `active_skills_summary` | yes | yes |
| `achievement_summary` | yes | yes |
| `calendar_context` | yes | yes |

New proto fields added in Stage 29.5:

- `active_skills_summary = 17`
- `achievement_summary = 18`
- `calendar_context = 19`

Reserved exception pair under Rule AQ:

- Python runtime keeps `emotion_hint` as a historical stub.
- proto keeps `emotion_hint_reserved = 8` as the reserved placeholder.

Generated artifacts refreshed in workspace:

- `backend/app/gen/user_state_pb2.py`
- `backend/app/gen/userstate/v1/user_state_pb2.py`
- `backend/gateway/gen/userstate/v1/user_state.pb.go`
- `mobile/lib/gen/user_state.pb.dart`

Note: these generated paths are currently ignored by repo `.gitignore`, so the Stage 29.5 proof of sync is established through successful `make proto-gen`, local artifact presence, and parity tests rather than tracked diff output.

## Rule Guard Automation

Discovered stage-local gate scripts:

`scripts/stage17/gate_final.sh` through `scripts/stage29/gate_final.sh` were all present, but they were not previously wired into CI.

Stage 29.5 moved the rule truth source to:

- `scripts/rule_guard_manifest.tsv`
- `scripts/run_all_rule_guards.sh`
- `.github/workflows/ci.yml` job: `all-rule-guards`

Current enforced rule set:

`K, Y, Z, AB, AC, AD, AE, AF, AG, AH, AI, AJ, AK, AL, AM, AN, AQ`

Final measured runner baseline:

- full run: `17` rules passed
- elapsed time: `11.89s`
- single-rule mode verified: `bash scripts/run_all_rule_guards.sh --rule Y`

## Rule AB Whitelist

Authoritative docs:

- `docs/aurora/rule_ab.md`
- `docs/aurora/rule_ab_router_whitelist.md`

Registered Router reads:

| field | current code site | allowed boundary |
| --- | --- | --- |
| `task_sufficiency_summary` | `backend/app/orchestration/routing_engine.py:302` | follow-up clarification branch only |
| `context_sufficiency_summary` | `backend/app/orchestration/routing_engine.py:304` | prompt caveat only, never branch condition |
| `active_skills_summary` | `backend/app/orchestration/routing_engine.py:367` | Stage 21 skill selection input only |

AST guard:

- `scripts/check_rule_ab_aggregator_integrity.py`

Result:

- no non-whitelisted Aggregator field reads found in Router code
- no Aggregator write-path violations found

## Migration Repair

Added revisions:

- `backend/alembic/versions/s19c1d2e3f4_stage19_no_schema_change.py`
- `backend/alembic/versions/s22c1d2e3f4_stage22_no_schema_change.py`
- `backend/alembic/versions/s295a1b2c3d4_merge_stage_backfill_heads.py`

`alembic history` head snapshot:

```text
s29a1b2c3d4, s19c1d2e3f4, s22c1d2e3f4 -> s295a1b2c3d4 (head) (mergepoint), Merge Stage 29 and no-op backfill heads.
```

Supporting note:

- full chain explanation: `docs/aurora/alembic_chain_integrity.md`

## Guard Rewrites

New or rewritten guards:

- `scripts/check_rule_y_inferred_extraction.py`
- `scripts/check_rule_ag_baseline_prerequisite.py`
- `scripts/check_rule_ae_conflict_audit.py`
- `scripts/stage25/check_rule_aj_user_id_isolation.py`
- `scripts/stage28/check_rule_am_confidence_cap.py`
- `scripts/check_rule_aq_python_proto_parity.py`
- `scripts/check_rule_z_social_boundary.py`

Supporting utility:

- `scripts/ast_guard_utils.py`

## Verification

Backend tests:

- `44 passed`  
  `backend/tests/unit/test_proto_python_parity.py`  
  `backend/tests/unit/test_ci_guard_runner.py`  
  `backend/tests/unit/test_rule_ab_whitelist_enforcement.py`  
  `backend/tests/unit/test_rule_ab_context_sufficiency_never_branch.py`  
  `backend/tests/unit/test_alembic_chain_linearity.py`  
  `backend/tests/unit/test_rule_y_guard.py`  
  `backend/tests/unit/test_rule_ag_guard.py`  
  `backend/tests/unit/test_rule_ae_rewrite.py`  
  `backend/tests/unit/test_rule_aj_rewrite.py`  
  `backend/tests/unit/test_rule_am_rewrite.py`

- `8 passed`  
  `backend/tests/unit/test_conflict_resolver_service.py`  
  `backend/tests/unit/test_memory_inferred_write_lane.py`

- `26 passed`  
  `backend/tests/unit/test_user_state_schema_contract.py`  
  `backend/tests/unit/test_state_aggregator_service.py`  
  `backend/tests/unit/test_working_memory_aggregator_integration.py`  
  `backend/tests/unit/test_route_history_service.py`  
  `backend/tests/unit/test_big_five_model.py`  
  `backend/tests/unit/test_confidence_cap_enforcement.py`  
  `backend/tests/unit/test_seed_library_stage22.py`

Mobile tests:

- `3 passed`  
  `mobile/test/user_state_proto_fields_test.dart`

Guard runner:

- `bash scripts/run_all_rule_guards.sh --jobs 4`
- result: `all rule guards passed (17 rules)`

## Non-Functional Notes

- No Stage 30 metacognition or other business-scope features were added.
- No kill-switch behavior was intentionally broadened or removed.
- Runtime replay for Stage 20 user arbitration now bypasses the generic inferred-lane minimum-confidence gate only for explicit user-selected conflict replay, preserving existing user-arbitrated behavior without reopening normal write paths.

## Stage 30 Readiness

Stage 30 blockers removed:

1. proto / generated / runtime schema drift is now guarded
2. CI guard execution is now real instead of paper-only
3. Rule AB exceptions are explicit, bounded, and test-enforced
4. Stage 19 / 22 migration gaps are closed
5. missing or weak rule guards are replaced

Stage 30 may proceed on top of this checkpoint.
