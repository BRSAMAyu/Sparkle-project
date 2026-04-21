# SPARKLE Aurora Stage 21 Handoff (2026-04-21)

> Status: engineering closeout baseline after autonomous Stage 21 execution
> Scope note: Stage 21 turns reusable user-approved handling patterns into first-class Skill records without letting Skill content leak into Aggregator state or Router branch logic.

## 1. Final Accept Matrix

| Workstream | Status | Notes |
| --- | --- | --- |
| `Gate S21-0` | accept | Stage 12 baseline, Rule V replay, Rule K/Z/AB/AC/AD/AE carry-forward guards, and Stage 20 handoff obligations remained green before Stage 21 sweeps |
| `WS-SK-RULE-AF` | accept | Rule AF definition, numbered-history note for skipped Rule AA, frozen prompts, trigger keyword file, and CI guards landed |
| `WS-SK-SCHEMA` | accept | frozen `skill.v1`, `user_skills` / `shared_skills` / moderation queue migrations, store CRUD, and 50-item cap landed |
| `WS-SK-EXTRACT` | accept | explicit-trigger-only extraction, frozen keyword matcher, user-confirmed draft flow, and outcome metrics landed |
| `WS-SK-SELECTION` | accept | Aggregator `v1.3` only exposes active skill metadata; Router injects prompt-only skill context and writes `skills_injected` to route history |
| `WS-SK-SHARE` | accept | private-vs-shared physical isolation, PII and injection checks, moderation queue, anonymous publish, fork snapshot semantics, and revoke-new-forks path landed |
| `WS-SK-MOBILE` | accept | profile entry, “我的方式” manager, draft creation, edit/delete/toggle/share/unshare, shared catalog, and fork flow landed |
| `WS-SK-KILL` | accept | Store / Selection / Share three-tier kill switches and admin API landed independently |
| `Gate S21-FINAL` | accept | targeted backend and mobile sweeps, Rule AF guards, trigger-purity guard, route-history guard, and route-history skill field checks all passed |

## 2. What Stage 21 Actually Achieved

Stage 21 makes Skill a governed product object instead of an implicit prompt trick.

It proves:

1. Skill creation is now explicit, user-visible, and bounded by frozen schema rules.
2. Skill content is physically separated from Aggregator state; only summaries enter `user_state.v1.3`.
3. Skill activation is prompt-only. It can shape wording and tool preference context, but it cannot steer Router branching.
4. unresolved fact conflicts now block skill activation on matching topic keys instead of letting conflicting context silently shape prompt injection.
5. cross-user sharing is opt-in per skill, anonymous at publish time, fork-based at adoption time, and non-social by design.
6. Stage 22 Bayesian wiring now has a single sanctioned future read path through `routing_decision_log.skills_injected`.

It does not prove:

1. Bayesian learning from skill usage.
2. automatic LLM discovery of latent skills.
3. any marketplace, ranking, or social reputation layer around shared skills.
4. any use of sufficiency signals for skill activation or suppression.

## 3. Verification Evidence

### Stage 21 targeted backend sweep

- `31 passed`
  - `test_skill_schema_contract.py`
  - `test_skill_store_service.py`
  - `test_skill_extract_service.py`
  - `test_skill_selection_service.py`
  - `test_skill_selection_aggregator_integration.py`
  - `test_skill_share_service.py`
  - `test_stage21_kill_switch.py`
  - `test_skills_api.py`
  - `test_memory_admin_api.py`
  - `test_route_history_service.py`
  - `test_route_history_performance.py`
  - `test_user_state_schema_contract.py`
  - `test_working_memory_aggregator_integration.py`

### Stage 21 targeted mobile sweep

- `10 passed`
  - `skill_models_test.dart`
  - `skill_management_screen_test.dart` (`8` widget scenarios)
  - `skill_management_route_test.dart`

### Governance Guards

- `scripts/check_rule_af_skill_share_isolation.py`
- `scripts/check_rule_af_skill_pii_pipeline.py`
- `scripts/check_skill_extract_trigger_purity.py`
- `scripts/check_route_history_skill_field.py`

### Observability

The minimum Stage 21 metric set is live:

1. `sparkle_skill_count_per_user`
2. `sparkle_skill_extract_draft_accept_rate`
3. `sparkle_skill_selection_activation_rate`
4. `sparkle_skill_share_pipeline_latency_seconds`

## 4. Representative Landed Files

- [skill_schema.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/skill_schema.py)
- [skill_store/service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/skill_store/service.py)
- [skill_extract_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/skill_extract_service.py)
- [skill_selection_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/skill_selection_service.py)
- [skill_content_reader.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/skill_content_reader.py)
- [skill_share/service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/skill_share/service.py)
- [route_history_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/route_history_service.py)
- [routing_engine.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/routing_engine.py)
- [schema.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/state_aggregator/schema.py)
- [service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/state_aggregator/service.py)
- [skills.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/api/v1/skills.py)
- [skill_management_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/skill_management_screen.dart)
- [profile_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/profile_screen.dart)
- [skill_api_service.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/services/skill_api_service.dart)

## 5. Hard Boundaries Still Locked

1. Skill extraction still requires explicit user consent or explicit manual creation.
2. Skill content still cannot enter Aggregator. `pattern_template`, `examples`, and raw activation rules remain outside `user_state`.
3. Skill selection still cannot read `task_sufficiency` or `context_sufficiency`.
4. Router still cannot branch on skill metadata or activation score.
5. Shared skill publication still cannot preserve `author_user_id`, expose cross-user usage statistics, or create any backchannel telemetry.
6. shared catalog rows still cannot be queried by Aggregator providers; only forked `user_skills` copies are eligible for user-state summaries.
7. Route history remains write-only for Stage 21; `skills_injected` is written now and reserved for Stage 22 readers later.

## 6. Honest Gaps And Deferred Work

1. Shared skill publishing remains default-off behind `SPARKLE_SKILL_SHARE_ENABLED` until real-user safety review decides whether Path A or B1 should be the production posture.
2. Skill extraction is intentionally conservative: it recognizes only frozen trigger phrases and explicit confirmation flows, not latent behavioral patterns.
3. `usage_count` remains a UI-facing counter and should not become a separate analytics substrate.
4. forked skill snapshots intentionally do not inherit later source updates or withdrawal notices, which keeps privacy and non-social guarantees stronger than discoverability.

## 7. Carry-Forward And Alignment Notes

1. Stage 20 handoff obligation is satisfied: Stage 21 Skill selection consumes Aggregator plus Conflict Resolver output and blocks on unresolved topic conflicts.
2. Stage 20 handoff obligation is satisfied: Skill selection remains independent from sufficiency whether Sufficiency Judge is logging-only or live on any path.
3. Stage 21 writes `skills_injected` into `routing_decision_log` instead of creating a parallel skill activity log, preserving the Stage 22 no-parallel-history promise.
4. Rule AA remains permanently skipped and unreused; the live rule chain now proceeds through `AF`.

## 8. Stage 22 Obligations

1. Stage 22 Bayesian wire-on must read skill injection evidence from `routing_decision_log.skills_injected`.
2. Stage 22 must combine Route History, Sufficiency, and Skill usage evidence without creating a parallel capture layer.
3. Stage 22 must re-run the Stage 14 SQAM four-dimensional measurement with the new source-state design.
4. Stage 23 keeps Rule `AG` reserved for Accountability governance.

## 9. Stage 21 Outcome Lock

Stage 21 is complete as an engineering stage.

Its locked outcome is:

1. Sparkle now has a governed private Skill Store with explicit user control.
2. shared skills can move across users only as anonymous, reviewed, forked snapshots.
3. Router can receive skill context without compromising Aggregator integrity or routing determinism.
4. Stage 22 inherits a single, auditable future input path for skill-aware Bayesian adaptation instead of another sidecar log system.
