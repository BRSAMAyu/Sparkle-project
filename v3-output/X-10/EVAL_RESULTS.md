# X-10 Action Engine E2E — Scenario Results

- git SHA: `20f9b200` ｜ 运行：2026-09-21 13:51 UTC ｜ 场景源：`x10_action_e2e_scenarios_v1.json`
- 判定语义：判定器对 DB 真相独立复算（不信执行器自述）；零真实 LLM（`real_llm_calls=0` 强制断言）

## 总览

| 指标 | 值 |
|---|---|
| 场景总数 | 77 |
| pass / fail / error | **77 / 0 / 0** |
| allocation 达标率（acceptance①） | **100.00%**（28/28；mode target 22/22，offer guard 6/6） |
| high-risk auto（acceptance①） | **0**（不变式覆盖 5 场景） |
| false success（acceptance①） | **0** |
| 总延迟 / 均值 | 157226 ms / 2041.9 ms（纯服务层墙钟） |
| 成本面（O-07 口径的确定性下界） | LLM 调用 0 次 / 0 token；服务操作 184 次 |

## 家族 × 类别覆盖矩阵

| family | n | pass | fail | error |
|---|---|---|---|---|
| allocation | 28 | 28 | 0 | 0 |
| authorization | 10 | 10 | 0 | 0 |
| proposal | 12 | 12 | 0 | 0 |
| run_steps | 13 | 13 | 0 | 0 |
| outcome | 10 | 10 | 0 | 0 |
| journey | 4 | 4 | 0 | 0 |

categories: allocation（learning_guard×3, explicit_intent×2, tool_advantage×2, gray_zone×2, time_modifier×1, ownership_default×1, high_risk×4, embodiment×1, privacy×2, confidence×1, user_preference×3, vet_guard×6）；authorization（auto_grant×2, irreversible×2, pure_rule×3, commit_gate×3）；proposal（commit_receipt×2, idempotency×3, terminal_closed×3, ttl_expiry×2, optimistic_concurrency×1, input_validation×1）；run_steps（step_plan×2, step_execution×1, owner_discipline×2, handoff×1, idempotent_resume×3, awaiting_recovery×1, cancel_expiry×2, resume_guard×1）；outcome（truth_classification×3, coverage_rule×2, failure_preserved×1, partial_not_promoted×1, run_receipt×1, idempotency×1, audit_without_exposure×1）；journey（golden_journey×4）

## 逐场景矩阵（六元组判定）

| scenario | family | journey | verdict | decision 摘要 | latency ms | cost(llm/ops) |
|---|---|---|---|---|---|---|
| alloc_a01_learning_user_core_writing | allocation | - | PASS | hybrid | 540.8 | 0/1 |
| alloc_a02_training_practice_user_core | allocation | - | PASS | hybrid | 290.5 | 0/1 |
| alloc_a03_learning_explicit_self | allocation | - | PASS | human | 288.9 | 0/1 |
| alloc_a04_learning_adversarial_full_pressure | allocation | - | PASS | hybrid | 286.6 | 0/1 |
| alloc_a05_delegated_mechanical_batch | allocation | - | PASS | agent | 285.7 | 0/1 |
| alloc_a06_delegated_retrieval | allocation | - | PASS | agent | 288.2 | 0/1 |
| alloc_a07_delegated_advantage_unverified | allocation | - | PASS | hybrid | 365.4 | 0/1 |
| alloc_a08_delegated_urgent_t1_promotion | allocation | - | PASS | agent | 287.2 | 0/1 |
| alloc_a09_shared_research_hybrid | allocation | - | PASS | hybrid | 286.1 | 0/1 |
| alloc_a10_high_risk_low_tool_human | allocation | - | PASS | human | 287.7 | 0/1 |
| alloc_a11_high_risk_shared_hybrid_approval | allocation | - | PASS | hybrid | 293.9 | 0/1 |
| alloc_a12_medium_irreversible_r1 | allocation | - | PASS | hybrid | 286.6 | 0/1 |
| alloc_a13_critical_restricted_human_only | allocation | - | PASS | human | 289.3 | 0/1 |
| alloc_a14_embodiment_required_hybrid | allocation | - | PASS | hybrid | 285.8 | 0/1 |
| alloc_a15_restricted_explicit_delegate_downgraded | allocation | - | PASS | human | 287.7 | 0/1 |
| alloc_a16_sensitive_delegated_hybrid | allocation | - | PASS | hybrid | 288.8 | 0/1 |
| alloc_a17_low_confidence_r6 | allocation | - | PASS | hybrid | 285.6 | 0/1 |
| alloc_a18_explicit_self_mechanical | allocation | - | PASS | human | 289.1 | 0/1 |
| alloc_a19_prefer_agent_low_tool_t2 | allocation | - | PASS | hybrid | 287.0 | 0/1 |
| alloc_a20_prefer_human | allocation | - | PASS | human | 288.6 | 0/1 |
| alloc_a21_prefer_mixed | allocation | - | PASS | hybrid | 288.4 | 0/1 |
| alloc_a22_insufficient_factors_gray | allocation | - | PASS | hybrid | 286.2 | 0/1 |
| alloc_a23_vet_complete_answer_learning_rejected | allocation | - | PASS | human | 289.4 | 0/1 |
| alloc_a24_vet_draft_user_core_rejected | allocation | - | PASS | human | 283.9 | 0/1 |
| alloc_a25_vet_mechanical_high_risk_needs_approval | allocation | - | PASS | hybrid | 285.8 | 0/1 |
| alloc_a26_vet_restricted_all_supply_forbidden | allocation | - | PASS | human | 286.3 | 0/1 |
| alloc_a27_vet_sensitive_complete_answer_downgrade | allocation | - | PASS | hybrid | 307.2 | 0/1 |
| alloc_a28_vet_unknown_kind_rejected | allocation | - | PASS | hybrid | 299.6 | 0/1 |
| auth_z01_service_auto_grant_executes | authorization | - | PASS | auto | 759.4 | 0/1 |
| auth_z02_no_grant_stays_confirmation | authorization | - | PASS | confirmation | 297.3 | 0/1 |
| auth_z03_irreversible_target_never_auto | authorization | - | PASS | confirmation | 296.7 | 0/1 |
| auth_z04_pure_medium_risk_not_low | authorization | - | PASS | confirmation | 292.4 | 0/1 |
| auth_z05_pure_irreversible_low_risk | authorization | - | PASS | confirmation | 287.0 | 0/1 |
| auth_z06_pure_unclassified_unreversible_declared | authorization | - | PASS | confirmation | 289.0 | 0/1 |
| auth_z07_pure_human_approval_flag | authorization | - | PASS | confirmation | 292.9 | 0/1 |
| auth_z08_commit_without_confirmation_denied | authorization | - | PASS | confirmation | 289.9 | 0/2 |
| auth_z09_commit_with_confirmation_allowed | authorization | - | PASS | confirmation | 288.8 | 0/2 |
| auth_z10_commit_auto_and_missing_record | authorization | - | PASS | auto | 291.2 | 0/3 |
| prop_p01_approve_complete_receipt_and_honest_minutes | proposal | - | PASS | confirmation | 459.2 | 0/2 |
| prop_p02_reapprove_idempotent_replay | proposal | - | PASS | confirmation | 395.9 | 0/3 |
| prop_p03_recreate_same_key_single_proposal | proposal | - | PASS | confirmation | 312.8 | 0/2 |
| prop_p04_same_key_different_payload_replays_existing | proposal | - | PASS | confirmation | 299.3 | 0/2 |
| prop_p05_reject_terminal_task_unchanged | proposal | - | PASS | confirmation | 308.7 | 0/2 |
| prop_p06_cancel_terminal_task_unchanged | proposal | - | PASS | confirmation | 416.9 | 0/3 |
| prop_p07_expired_approve_persists_expired | proposal | - | PASS | confirmation | 299.5 | 0/3 |
| prop_p08_sweep_expires_stale_batch | proposal | - | PASS | confirmation | 302.1 | 0/3 |
| prop_p09_version_conflict_rolls_back_to_pending | proposal | - | PASS | confirmation | 321.6 | 0/3 |
| prop_p10_terminal_closed_after_reject | proposal | - | PASS | confirmation | 301.0 | 0/3 |
| prop_p11_create_batch_effects_enriched | proposal | - | PASS | confirmation | 485.0 | 0/2 |
| prop_p12_field_whitelist_violation_no_proposal | proposal | - | PASS | - | 295.8 | 0/1 |
| run_r01_define_plan_persisted | run_steps | - | PASS | run_plan[agent,human] | 295.3 | 0/2 |
| run_r02_plan_conflict_rejected | run_steps | - | PASS | run_plan[agent] | 295.6 | 0/4 |
| run_r03_agent_step_completed_and_stamped | run_steps | - | PASS | run_plan[agent,human] | 301.8 | 0/4 |
| run_r04_owner_discipline_agent_cannot_complete_human_step | run_steps | - | PASS | run_plan[human] | 297.0 | 0/4 |
| run_r05_owner_discipline_user_cannot_complete_agent_step | run_steps | - | PASS | run_plan[agent] | 299.5 | 0/5 |
| run_r06_await_user_step_explicit_handoff | run_steps | - | PASS | run_plan[agent,human] | 301.1 | 0/5 |
| run_r07_user_complete_resumes_exactly_once | run_steps | - | PASS | run_plan[agent,human] | 302.8 | 0/6 |
| run_r08_double_confirm_same_key_first_wins | run_steps | - | PASS | run_plan[hybrid] | 336.6 | 0/6 |
| run_r09_double_confirm_different_keys_still_once | run_steps | - | PASS | run_plan[hybrid] | 303.0 | 0/6 |
| run_r10_cold_start_awaiting_recovery | run_steps | - | PASS | run_plan[agent,human] | 305.5 | 0/6 |
| run_r11_late_confirm_after_cancel_rejected | run_steps | - | PASS | run_plan[human] | 350.0 | 0/6 |
| run_r12_late_confirm_after_wait_expiry_rejected | run_steps | - | PASS | run_plan[human] | 303.3 | 0/6 |
| run_r13_resume_cannot_inject_terminal | run_steps | - | PASS | run_plan[human] | 444.0 | 0/5 |
| outc_o01_user_click_completion_self_reported | outcome | - | PASS | complete | 385.5 | 0/2 |
| outc_o02_declared_artifact_unverified_stays_self_reported | outcome | - | PASS | complete | 408.3 | 0/2 |
| outc_o03_succeeded_run_receipt_upgrades_actual | outcome | - | PASS | complete_with_run_receipt | 395.3 | 0/4 |
| outc_o04_focus_below_threshold_self_reported | outcome | - | PASS | complete_with_focus_observation | 394.2 | 0/2 |
| outc_o05_focus_above_threshold_actual | outcome | - | PASS | complete_with_focus_observation | 417.5 | 0/2 |
| outc_o06_abandoned_negative_preserved_never_actual | outcome | - | PASS | abandon | 320.0 | 0/2 |
| outc_o07_partial_run_neutral_never_positive | outcome | - | PASS | run_partial | 306.8 | 0/2 |
| outc_o08_failed_run_negative | outcome | - | PASS | run_failed | 300.5 | 0/2 |
| outc_o09_derive_outcome_id_idempotent | outcome | - | PASS | idempotency_probe | 300.3 | 0/0 |
| outc_o10_recorded_event_content_free | outcome | - | PASS | event_payload_probe | 386.8 | 0/1 |
| journey_gj04_stuck_clarification_rescope | journey | GJ04 | PASS | human | 131965.1 | 0/5 |
| journey_gj05_human_evidence_galaxy | journey | GJ05 | PASS | human | 646.5 | 0/3 |
| journey_gj06_agent_approval_run_receipt | journey | GJ06 | PASS | alloc:hybrid | 435.7 | 0/9 |
| journey_gj07_hybrid_prep_await_resume | journey | GJ07 | PASS | alloc:hybrid | 429.8 | 0/12 |

## 失败 case 清单

本轮无失败 case（77/77；判定器有效性由 gate 测试的 7 组变异红证独立保证——判定器对谎报/幂等破坏/极性翻转/LLM 泄漏全部判红）。
