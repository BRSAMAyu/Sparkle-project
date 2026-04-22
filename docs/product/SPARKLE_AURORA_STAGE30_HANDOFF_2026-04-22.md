# SPARKLE AURORA Stage 30 Handoff

Date: 2026-04-22

Status: Local implementation complete for Path A, with targeted verification evidence attached below.

## 1. Final Accept Matrix

| WS | Status | Evidence |
| --- | --- | --- |
| WS-MC-BIAS-UNIFY | PASS | `backend/app/services/metacognition_service.py`, `backend/tests/unit/test_metacognition_service.py`, `backend/tests/unit/test_bias_unify_cold_start.py` |
| WS-MC-CONFIDENCE-PROXY | PASS | `backend/app/services/metacognition_registry.py`, `docs/aurora/stage30_confidence_proxies.md`, `backend/tests/unit/test_confidence_proxy_registry.py` |
| WS-MC-PROCESS-SCAFFOLDING | PASS | `backend/app/orchestration/prompts.py`, `docs/aurora/stage30_process_scaffolding_templates.md`, `backend/tests/unit/test_process_scaffolding_trigger.py` |
| WS-MC-DASHBOARD | PASS | `backend/app/api/v1/profile_transparency.py`, `mobile/lib/features/user/presentation/widgets/metacognition_panel_card.dart`, `mobile/test/widget/metacognition_panel_test.dart` |
| WS-MC-GUARD | PASS | `scripts/check_rule_ao_no_diagnostic_labels.py`, `scripts/check_rule_ao_not_in_router.py`, `scripts/check_metacognition_scaffolding_decoupled.py`, `backend/tests/unit/test_rule_ao_diagnostic_ban.py`, `backend/tests/unit/test_scaffolding_combine_matrix.py`, `backend/tests/unit/test_metacognition_kill_switch.py` |

## 2. Path Choice

Path selected: Path A.

Why:
- Bias unify, dashboard, process scaffolding, and FSM combine are all wired live behind kill switches.
- Rule AO guards are registered in `scripts/rule_guard_manifest.tsv`.
- Daily recompute and task-completion recompute are both present.

## 3. Bias Aggregate Evidence

Local synthetic verification:
- `sample_size=19` stays filtered from Aggregator and process scaffolding.
- `sample_size=20` becomes eligible for Aggregator output.
- Dashboard rendering verified at `sample_size=24`.
- Process scaffolding rendering verified at `sample_size=22`.

Source tests:
- `backend/tests/unit/test_bias_unify_cold_start.py`
- `backend/tests/unit/test_metacognition_service.py`

## 4. Confidence Proxy Snapshot

Registered proxies: 5.

List:
- `revision_frequency`
- `self_correction_rate`
- `question_to_statement_ratio`
- `time_to_first_action`
- `completion_vs_estimate_delta_sign`

Primary registry:
- `docs/aurora/stage30_confidence_proxies.md`
- `backend/app/services/metacognition_registry.py`

## 5. Process Scaffolding Template Snapshot

Registered templates: 8.

Primary registry:
- `docs/aurora/stage30_process_scaffolding_templates.md`
- `backend/app/services/metacognition_registry.py`

Contract:
- template-only
- `sample_size >= 20`
- `abs(bias_mean) >= 0.3`
- 72h cooldown

## 6. Rule AO Diagnostic Ban Evidence

Blacklist doc:
- `docs/aurora/rule_ao_banned_phrases.md`

Guards:
- `scripts/check_rule_ao_no_diagnostic_labels.py`
- `scripts/check_rule_ao_not_in_router.py`
- `scripts/check_metacognition_scaffolding_decoupled.py`

Local result:
- AO guard PASS
- diagnostic label test PASS
- runtime auto-disable-on-hit test PASS

## 7. Scaffolding Combine Matrix Evidence

Combine contract:
- `docs/aurora/stage30_scaffolding_combine.md`

Implementation:
- `backend/app/scaffolding/scaffolding_fsm.py`

Verification:
- `backend/tests/unit/test_scaffolding_combine_matrix.py`
- 9 matrix combinations passed

## 8. Aggregator v1.11 and AQ Evidence

Schema:
- `backend/app/state_aggregator/schema.py`
- `proto/user_state.proto`

Generated code refreshed with:
- `make proto-gen`

AQ:
- `scripts/check_rule_aq_python_proto_parity.py`
- local result PASS

## 9. Dashboard Language Contract

Language contract doc:
- `docs/aurora/stage30_language_contract.md`

Runtime/template source:
- `backend/app/services/metacognition_registry.py`

UI:
- `mobile/lib/features/user/presentation/widgets/metacognition_panel_card.dart`
- `mobile/lib/features/user/presentation/screens/profile_screen.dart`

## 10. Router Zero-Hit Evidence

Guards/tests:
- `scripts/check_rule_ao_not_in_router.py`
- `backend/tests/unit/test_metacog_not_router.py`

Local result:
- PASS

## 11. Scaffolding Decouple Evidence

Guard:
- `scripts/check_metacognition_scaffolding_decoupled.py`

Local result:
- PASS

## 12. Boundary With SufficiencyJudge

Boundary stance preserved:
- metacognition stays in `MetacognitionService`
- sufficiency remains in Stage 20 sufficiency paths
- router and sufficiency modules do not read metacognition fields

Local evidence:
- metacognition field is Aggregator-only
- router zero-hit tests PASS

## 13. LLM Budget

Process scaffolding is template fill only.

Observed implementation posture:
- no free-form metacognition generation
- no new dashboard-side LLM call
- no mobile-side synthesis

Note:
- exact production cost telemetry was not benchmarked in this local turn

## 14. Kill-Switch 4-Way Exercise

Service:
- `backend/app/services/aurora_stage30_metacognition_kill_switch_service.py`

Coverage:
- main mode
- dashboard child mode
- process scaffolding child mode
- FSM combine child mode

Evidence:
- `backend/tests/unit/test_metacognition_kill_switch.py`

## 15. Test and Guard Counts

Local command results:
- `scripts/run_all_rule_guards.sh --rule AO` PASS
- `scripts/run_all_rule_guards.sh --rule AQ` PASS
- `scripts/stage30/gate_final.sh` PASS
- targeted backend suite: 59 passed
- targeted mobile suite: 3 passed
- gate_final backend subset: 26 passed

Also updated schema-version assertions from `user_state.v1.10` to `user_state.v1.11` in existing aggregator contract tests.

## 16. Stage 31 Preconditions

- Keep Rule AO registered and green.
- Preserve `sample_size < 20` hard gate.
- Keep metacognition out of Router.
- Keep SufficiencyJudge and Metacognition separate.
- Keep process scaffolding template-only.
- Keep ScaffoldingFSM reading metacognition through Aggregator only.

## Verification Scope Note

This handoff documents local implementation and targeted verification. Full Stage 17-29.5 regression was not run in this turn.
