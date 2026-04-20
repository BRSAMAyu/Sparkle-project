# SPARKLE Aurora Stage 17 Handoff (2026-04-20)

> Status: engineering closeout baseline after autonomous Stage 17 execution
> Scope note: Stage 17 was executed under the explicit governance addendum that the gray-window framework is owned by a separate Claude Code stream and does not block this stage's engineering gate.
> Repository note: Stage 17 work is landed in the workspace and validated locally; Rule G atomic git slicing is still pending, so `stage17_progress.md` intentionally keeps `commits: pending`.

## 1. Final Accept Matrix

| Workstream | Status | Notes |
| --- | --- | --- |
| `Gate S17-0` | accept | Stage 12 frozen baseline, Rule V regression, Rule K guard, and Stage 13-17 carry-forward replay all passed before final sweep |
| `WS-SOC-RULE-Z` | accept | Rule Z definition landed; Rule K guard upgraded with Stage 17 social-memory checks |
| `WS-SOC-NAMESPACE` | accept | `social_context` is isolated from `community_context`; prompt rendering is bounded and default-OFF |
| `WS-SOC-EXTRACT` | accept | `subject_type` classifier, HMAC social hash, rate limiting, and degraded backpressure queue landed |
| `WS-SOC-COMMIT` | accept | `due_at` / `resolved_at` metadata, parser, and Alembic migration landed |
| `WS-ACCT-MVP` | accept | overdue commitments now surface through a thin read path and mobile front door without push |
| `WS-SOC-ROUTER-READ` | accept | `SocialContextProvider` + `RouterContextReader` landed as a prompt-only compatibility seam |
| `WS-SOC-MOBILE` | accept | memory front door shows subject metadata, pending commitments, and per-type switches |
| `WS-SOC-KILL` | accept | admin revoke supports `subject_type` targeting and immediate Accountability disappearance |
| `Gate S17-FINAL` | accept | targeted backend/mobile sweeps passed and required Stage 17 artifacts now exist |

## 2. What Stage 17 Actually Achieved

Stage 17 turns Stage 16's governed inferred write lane into a bounded read surface for three narrowly scoped consumers:

1. social-memory extraction and storage
2. Accountability MVP pending-commitment visibility
3. Router prompt-context compatibility for Stage 18 provider migration

It proves:

1. inferred episodic rows now carry `subject_type`, `due_at`, `resolved_at`, and Rule Z social metadata
2. social facts are isolated inside `social_context` and are not silently injected through `community_context`
3. overdue commitments can be surfaced and resolved without deleting evidence
4. Router now has a frozen `SocialContextProvider -> FrozenSocialSnapshot` seam for the Stage 18 Aggregator swap
5. per-`subject_type` revocation works without disabling the whole inferred lane

It does not prove:

1. live gray-window readiness
2. Router decision-branch consumption of social facts
3. proactive notifications or push recovery loops
4. cross-user person resolution

## 3. Verification Evidence

### Carry-forward replay

- Stage 12 frozen baseline: `144 passed`
- Rule V regression suite: `8 passed`
- Rule K / Rule Z static guard: `0 violation`
- Stage 13+14+15+16+17 carry-forward backend sweep: `28 passed`

### Stage 17 targeted sweeps

- Stage 17 targeted backend sweep: `27 passed`
  - `test_rule_z_guard.py`
  - `test_social_namespace_isolation.py`
  - `test_memory_subject_type_extraction.py`
  - `test_commitment_parser.py`
  - `test_accountability_mvp_service.py`
  - `test_router_context_reader.py`
  - `test_social_kill_switch.py`
  - `test_memory_inferred_write_lane.py`
- Stage 17 targeted mobile sweep: `51 tests passed`
  - `flutter test test/features/memory/ test/features/home/`

### Artifacts

- Rule Z:
  [SPARKLE_AURORA_STAGE17_RULE_Z_DEFINITION_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE17_RULE_Z_DEFINITION_2026-04-20.md)
- Accountability audit:
  [SPARKLE_AURORA_STAGE17_ACCT_HEALTH_AUDIT_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE17_ACCT_HEALTH_AUDIT_2026-04-20.md)
- Router prompt audit:
  [SPARKLE_AURORA_STAGE17_ROUTER_AB_REPORT_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE17_ROUTER_AB_REPORT_2026-04-20.md)
- Progress log:
  [stage17_progress.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/stage17_progress.md)

## 4. Representative Landed Files

- [memory_inferred_write_lane.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/memory_inferred_write_lane.py)
- [memory_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/memory_service.py)
- [commitment_parser.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/commitment_parser.py)
- [accountability_mvp_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/accountability_mvp_service.py)
- [router_context_reader.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/routing/router_context_reader.py)
- [social_context_provider.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/routing/social_context_provider.py)
- [memory_panel_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/memory/presentation/screens/memory_panel_screen.dart)
- [memory_settings_screen.dart](/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/memory/presentation/screens/memory_settings_screen.dart)

## 5. Hard Boundaries Still Locked

1. `social_context` is prompt context only and may not become a routing decision signal in Stage 17.
2. `person_mention` / `relationship` facts may not participate in recommender, learner, or cross-user joins.
3. Accountability remains a read-and-resolve surface only; no push, badge, or red-dot behavior was added.
4. gray-window governance is still external to this engineering closeout and was not rewritten here.

## 6. Known Limits And Honest Gaps

1. `mentioned_entity_hash` intentionally uses the HMAC key form `user_id:null`.
   This is deliberate in Stage 17 because the mentioned party is not resolved to a Sparkle account. It preserves the Rule Z no-cross-user-join boundary, but it also means same-real-person cross-user matching is impossible until a separately governed future upgrade exists.
2. The Router A/B artifact is now a source-based engineering audit, not a live model-behavior benchmark.
   That is acceptable for Stage 17 because the snapshot is still prompt-only and default-OFF, but any stronger claim about prompt drift must be revisited in Stage 18/19 before broader rollout.
3. Rule G atomic git commits are still pending.
   The code and tests are landed locally, but the final commit slicing by workstream has not yet been performed.

## 7. Stage 18 Obligations

1. `RouterContextReader` must be replaced by an Aggregator-backed `SocialContextProvider` implementation without changing the public provider contract.
2. Stage 18 must establish a pull-only frozen `user_state.v1` surface rather than expanding Router-local decision logic.
3. If any future live prompt-drift benchmark shows KL divergence in `[0.2, 0.3]`, Stage 19B must front-load a Sufficiency Judge before stronger consumption is allowed.
4. Working Memory in Stage 19A must treat Aggregator output as its upstream source instead of building a parallel ad-hoc state view.

## 8. Stage 17 Outcome Lock

Stage 17 is complete as an engineering stage.

Its locked outcome is:

1. Stage 16 inferred episodic memory now supports bounded social and commitment semantics under Rule Z governance
2. the mobile memory front door can disclose, filter, resolve, and revoke those semantics
3. Router has only a read-only compatibility seam, not a new decision path
4. Stage 18 inherits an explicit obligation to replace the temporary reader with a frozen Aggregator-backed provider
