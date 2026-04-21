# Loop 6: Cross-User Security + Alembic Chain + Cross-Validation

> Executed: 2026-04-21
> Sub-agents used: 3 Explore agents (cross-user security, Alembic chain, cross-validation)
> Duration: ~12 min

> Normalization note: this loop performed the strict re-check that produced the corrected audit baseline. Post-audit closeout later resolved two of the medium defense-in-depth findings and the Rule AH path fragility.

## Findings

| # | Severity | Stage | Category | Finding | File:Line | Evidence |
|---|----------|-------|----------|---------|-----------|----------|
| L6-1 | P2 | S24 | Security | `policy_compiler_service.revoke_for_commitment()` lacked a service-layer `user_id` filter, but caller ownership validation existed upstream | `policy_compiler_service.py:135-147`, `memory_service.py:778-795` | `resolve_commitment()` loads by `id + user_id` before invoking revoke |
| L6-2 | P2 | S20 | Security | `conflict_resolver_service._load_records()` lacked a service-layer `user_id` filter, but `resolve()` validated `candidate.user_id` ownership for every record | `conflict_resolver_service.py:121-123`, `conflict_resolver_service.py:424-430` | upstream ownership guard exists before arbitration |
| L6-3 | FP | S20 | Security | `route_history_service._load_decision()` looked user-agnostic, but is not reachable from an external user-controlled API path | `route_history_service.py:289-293` | public read path uses `_load_decision_for_user()`, raw helper is internal |
| L6-4 | P2 | S26 | Security | `scene_consolidation_service` still validates isolation post-query rather than fully pre-query | `scene_consolidation_service.py:308-324` | defense-in-depth gap remains even though rejection happens before user-visible return |
| L6-5 | P2 | S25 | Audit Hygiene | Historical handoff and migration accounting around Stage 25 remain documentation-heavy rather than fully explicit | handoff + migration topology | no broken chain, but documentation could be clearer |

## Cross-Validation Results

### Reclassified During Strict Re-Check

| Original Concern | Final Baseline Status | Reason |
|------------------|-----------------------|--------|
| `emotion_hint` mismatch was a P0 serialization failure | downgraded to P2 placeholder drift | intentional placeholder pair, never live-populated |
| `revoke_for_commitment()` was a P1 security issue | downgraded to P2 defense-in-depth | upstream caller validates ownership |
| `_load_records()` was a P1 security issue | downgraded to P2 defense-in-depth | arbitration path validates all records against `candidate.user_id` |
| `_load_decision()` was a P1 security issue | false positive | helper is internal and not exposed via external read API |

### Governance Findings Confirmed

| Finding | Result |
|---------|--------|
| Rules `G/H` missing automation | confirmed |
| Rules `P/Q/U` missing automation | confirmed |
| `check_nlp_no_direct_write.py` fragile | confirmed |
| `check_rule_ai_policy_purity.py` fragile | confirmed |

## Cross-User Security Matrix

| # | Subsystem | Status | Notes |
|---|-----------|--------|-------|
| 1 | Memory Write | SAFE | explicit user scoping |
| 2 | Social Context | SAFE | read-only context path |
| 3 | Push Delivery | SAFE | user-scoped |
| 4 | Working Memory | N/A | Redis/transient |
| 5 | Sufficiency Judge | N/A | no DB reads |
| 6 | Conflict Resolver | P2 baseline / fixed in closeout | private loader lacked direct filter, later hardened |
| 7 | Route History | FALSE POSITIVE | public reads are user-scoped |
| 8 | Skill System | PARTIAL BY DESIGN | shared skill records intentionally cross user boundary |
| 9 | Bayesian Learner | N/A | Redis |
| 10 | Policy Compiler | P2 baseline / fixed in closeout | caller validated ownership, later hardened |
| 11 | Reflection | SAFE | no cross-user DB issue found |
| 12 | Scene | P2 open | post-query isolation check |
| 13 | Foresight/PersDyn | SAFE | user-scoped |
| 14 | Traits | N/A | no DB issue found |
| 15 | SRL Tracker | SAFE | user-scoped |

## Alembic Chain Health

- Chain continuity: **OK**
- Head: `s295a1b2c3d4`
- Valid no-op stages: `s19c1d2e3f4`, `s22c1d2e3f4`
- No broken `down_revision` references found

## Verified OK

| # | Claim | Verified In |
|---|-------|-------------|
| V6-1 | Alembic chain has no broken links | revision graph re-check |
| V6-2 | Stage 19 and 22 are explicit no-op schema stages | no-op migration files present |
| V6-3 | Public route history reads are user-scoped | `_load_decision_for_user()` path |
| V6-4 | Proto sync concern was overstated in earlier review | final parity review |

## Summary

- P0 findings: 0
- P1 findings: 0 newly sustained here
- P2 findings: 4 baseline items in this loop
- False positives: 1
- Cross-validation materially reduced the earlier over-reporting
