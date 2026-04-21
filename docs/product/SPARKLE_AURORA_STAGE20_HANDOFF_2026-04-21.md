# SPARKLE Aurora Stage 20 Handoff (2026-04-21)

> Status: engineering closeout baseline after autonomous Stage 20 execution
> Scope note: Stage 20 lands the first deterministic sufficiency split, system-level conflict arbitration audit, and write-only route history substrate without opening any online learning consumer.

## 1. Final Accept Matrix

| Workstream | Status | Notes |
| --- | --- | --- |
| `Gate S20-0` | accept | Stage 12 baseline, Rule V, Rule K/Z/AB/AC carry-forward replay, and Stage 19 handoff prerequisites remained green before Stage 20 sweeps |
| `WS-SCQ-RULES` | accept | Rule AD + AE definition landed; Stage 17 carry-forward HMAC note and closeout baseline reconfirm completed |
| `WS-SJ-CORE` | accept | deterministic `SufficiencyJudgeService`, frozen v1 formula, cold dataset contract, and judgment persistence landed |
| `WS-CR-CORE` | accept | `ConflictResolverService`, audit tables, unresolved-conflict queue, and shadow-mode parallel comparison landed |
| `WS-SCQ-AGGREGATOR-INTEGRATE` | accept | `user_state.v1.2` now exposes read-only task/context sufficiency summaries with 30s TTL |
| `WS-SJ-ROUTER-CONSUME` | accept | Router follow-up branch only keys off task sufficiency; context sufficiency is reduced to prompt caveat text |
| `WS-RH-CORE` | accept | `routing_decision_log` write path and `decision_id`-only outcome backfill landed |
| `WS-SCQ-MOBILE-DECL` | accept | memory front door now exposes unresolved conflicts as a user-arbitrated “待你确认” surface |
| `Gate S20-FINAL` | accept | targeted backend `22 passed`, targeted mobile `6 passed`, proto sync fallback, and Rule AD/AE guards all passed |

## 2. What Stage 20 Actually Achieved

Stage 20 makes Aurora explicitly admit three things it previously only implied:

1. whether the current task is sufficiently specified to proceed
2. whether competing facts were rejected, overridden, or escalated to the user
3. what routing decision was taken and whether that decision later received any outcome signal

It proves:

1. sufficiency is now deterministically split into `task_sufficiency` and `context_sufficiency`
2. Router may branch on task sufficiency, but context sufficiency is still prompt-only and never a control-flow signal
3. conflict overrides no longer happen silently; every live or shadow comparison leaves audit evidence
4. unresolved conflicts can be surfaced and arbitrated from the memory front door
5. route history is collected for future Bayesian wire-on without opening any Stage 20 online reader

It does not prove:

1. Bayesian consumption of route history
2. any LLM-based sufficiency or conflict judge
3. cross-user conflict arbitration
4. push consumption of sufficiency, conflict, or route-history signals

## 3. Verification Evidence

### Stage 20 targeted backend sweep

- `22 passed`
  - `test_sufficiency_judge_schema.py`
  - `test_sufficiency_judge_service.py`
  - `test_sufficiency_aggregator_integration.py`
  - `test_user_state_schema_contract.py`
  - `test_state_aggregator_service.py`
  - `test_router_sufficiency_branch.py`
  - `test_follow_up_question_templates.py`
  - `test_conflict_resolver_service.py`
  - `test_route_history_service.py`
  - `test_route_history_performance.py`
  - `test_memory_unresolved_conflicts_api.py`

### Stage 20 targeted mobile sweep

- `6 passed`
  - `unresolved_conflicts_section_test.dart`
  - `memory_panel_screen_test.dart`
  - `memory_panel_screen_test.dart` (legacy carry-forward panel path)
  - `memory_panel_v2_test.dart`
  - `memory_auto_memory_panel_test.dart`
  - `subject_type_filter_test.dart`

### Governance Guards

- `scripts/check_rule_ad_sufficiency_split.py`
- `scripts/check_rule_ae_conflict_audit.py`

## 4. Representative Landed Files

- [sufficiency_judge_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/sufficiency_judge_service.py)
- [conflict_resolver_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/conflict_resolver_service.py)
- [route_history_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/route_history_service.py)
- [memory_inferred_write_lane.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/memory_inferred_write_lane.py)
- [routing_engine.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/routing_engine.py)
- [memory.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/api/v1/memory.py)
- [aurora_stage20.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/models/aurora_stage20.py)
- [memory_panel_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/memory/presentation/screens/memory_panel_screen.dart)
- [unresolved_conflicts_section.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/memory/presentation/widgets/unresolved_conflicts_section.dart)

## 5. Hard Boundaries Still Locked

1. Sufficiency Judge remains pure-rule and frozen-formula.
2. `context_sufficiency` remains prompt caveat only; it is not a router branch condition.
3. Conflict Resolver remains single-user only and may not cross user boundaries.
4. `routing_decision_log` remains write-only for Stage 20 except single-row `decision_id` outcome backfill.
5. push remains permanently isolated from sufficiency, conflict, and route-history signals.

## 6. Honest Gaps And Deferred Work

1. Conflict Resolver defaults to shadow mode until real disagreement data supports a live cutover.
2. unresolved conflicts can now be arbitrated, but Stage 20 intentionally keeps that UX inside the memory front door instead of broader product surfaces.
3. Route History records are collected, but no Stage 20 service is allowed to read them for online adaptation yet.

## 7. Carry-Forward Resolution

1. Stage 17 handoff is now expanded to closeout-baseline form.
2. Rule Z now explicitly documents the `f"{user_id}:null"` to `f"{user_id}:{mentioned_user_id}"` migration contract.
3. Router A/B placeholder evidence remains deferred to the real-user gate and is no longer treated as development debt.

## 8. Stage 21 Obligations

1. Stage 21 Skill selection must consume Aggregator + Conflict Resolver outputs instead of building a parallel fact view.
2. Rule AF is now the locked governance slot for Skill cross-user sharing.
3. If Sufficiency stays in logging-only mode on any path, Skill selection must remain independent of sufficiency signals.

## 9. Stage 20 Outcome Lock

Stage 20 is complete as an engineering stage.

Its locked outcome is:

1. Aurora can now deterministically represent “I know enough” versus “I need one more task-level answer”
2. fact conflicts are now auditable objects instead of silent side effects
3. routing decisions are now paired with outcome-ready identifiers for future Bayesian wire-on
4. Stage 21 inherits a cleaner substrate instead of having to build around unresolved state
