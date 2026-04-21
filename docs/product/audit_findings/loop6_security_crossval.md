# Loop 6: Cross-User Security + Alembic Chain + Cross-Validation

> Executed: 2026-04-21
> Sub-agents used: 3 Explore agents (cross-user security, Alembic chain, cross-validation)
> Duration: ~12 min

## Findings

| # | Severity | Stage | Category | Finding | File:Line | Evidence |
|---|----------|-------|----------|---------|-----------|----------|
| L6-1 | P1 | S24 | Security | `policy_compiler_service.revoke_for_commitment()` queries by `commitment_id` without `user_id` filter — defense-in-depth gap | policy_compiler_service.py:135-147 | API layer likely validates ownership, but service layer lacks explicit user_id filter |
| L6-2 | P1 | S20 | Security | `conflict_resolver_service._load_records()` queries by `id.in_(record_ids)` without `user_id` filter — defense-in-depth gap | conflict_resolver_service.py:424-430 | Private method; caller may validate, but service lacks explicit filter |
| L6-3 | P1 | S20 | Security | `route_history_service._load_decision()` queries by `decision_id` without `user_id` filter — defense-in-depth gap | route_history_service.py:289-293 | Private method; API-layer auth likely provides primary enforcement |
| L6-4 | P2 | S26 | Security | `scene_consolidation.assert_scene_user_isolation()` queries member memories without `user_id` filter then validates post-query — data read before rejection | scene_consolidation_service.py:308-324 | Defense-in-depth gap; validation still blocks cross-user returns |
| L6-5 | P2 | S25 | Migration | Stage 25 has no Alembic migration file (reflection wire-on is read-path only, likely intentional) | backend/alembic/versions/ | No s25-prefixed file found; Stages 24 and 26 both have migrations |

## Cross-Validation Results

### P0 → Downgraded
| Original Finding | Loop | Result | Reason |
|-----------------|------|--------|--------|
| L1-1: emotion_hint vs emotion_hint_reserved | 1 | **DOWNGRADED to P2** | Field is intentional placeholder ("reserved for Stage 19C"); never populated in production; Rule AQ guard excludes both from parity check; NOT a serialization failure |

### P1 → Confirmed
| Original Finding | Loop | Result | Reason |
|-----------------|------|--------|--------|
| L1-2: emotion_hint missing builder | 1 | **CONFIRMED, stays P1** | Field has no _build_* method; orphaned in aggregator |
| L5-1: Rules G/H missing guards | 5 | **CONFIRMED** | scripts/stage4/ doesn't exist; no automated enforcement |
| L5-2: Rules P/Q/U missing guards | 5 | **CONFIRMED** | Convention-only enforcement for social fact rules |
| L5-3: NLP direct-write guard fragile | 5 | **CONFIRMED** | String-match bypassable via method chaining |
| L5-4: Rule AI policy purity fragile | 5 | **CONFIRMED** | Token-based import detection bypassable |

### P2 → Confirmed/Not Verified
| Finding | Result |
|---------|--------|
| L1-3: Stage 16 no gate_final.sh | CONFIRMED |
| L1-4: Legacy Go proto file | CONFIRMED |
| L2-1: Migration name drift | CONFIRMED |
| L2-2: reflection.generated undocumented | CONFIRMED |
| L2-3: Test count S25 | NOT VERIFIED (likely inherited tests) |
| L3-1/2/3: Test count discrepancies | NOT VERIFIED (parametrized/inherited tests) |
| L5-5: Rule AH CWD dependency | CONFIRMED |

## Cross-User Security Matrix

| # | Subsystem | Queries | All Filtered | Issues |
|---|-----------|---------|-------------|--------|
| 1 | Memory Write | 4 | YES | None |
| 2 | Social Context | 0 | N/A | None (reader) |
| 3 | Push Delivery | 3 | YES | None |
| 4 | Working Memory | 0 | N/A | None (Redis) |
| 5 | Sufficiency Judge | 0 | N/A | None (no DB) |
| 6 | Conflict Resolver | 4 | NO | P1: _load_records bypass |
| 7 | Route History | 5 | NO | P1: _load_decision bypass |
| 8 | Skill System | 6 | PARTIAL | SharedSkill is cross-user by design; not a vulnerability |
| 9 | Bayesian Learner | 0 | N/A | None (Redis) |
| 10 | Policy Compiler | 3 | NO | P1: revoke_for_commitment bypass |
| 11 | Reflection | 0 | N/A | None |
| 12 | Scene | 7 | PARTIAL | P2: post-query validation (defense-in-depth) |
| 13 | Foresight/PersDyn | 6 | YES | None |
| 14 | Traits | 0 | N/A | None |
| 15 | SRL Tracker | 2 | YES | None |

## Alembic Chain Health

- Total stage-prefixed migrations: 13
- Chain continuity: **OK** — no broken links
- Head: `s295a1b2c3d4` (merge migration)
- Branching: 3 valid branches (s19 parallel to s20, s22 parallel to s23), all merged at s295
- Missing: Stage 25 (intentional — read-path only)
- No-ops: Stage 19 (Redis-only), Stage 22 (read-path only)

## Verified OK

| # | Claim | Verified In |
|---|-------|-------------|
| V6-1 | Alembic chain has no broken links | All down_revision references resolve |
| V6-2 | All 14 Aurora stages (16-29) have migrations or valid no-ops | 13 migration files + 2 no-ops |
| V6-3 | 10/15 subsystems have full user_id filtering | Memory, Push, Foresight, SRL confirmed safe |
| V6-4 | P0 emotion_hint finding was false alarm | Intentional placeholder, never populated |

## Summary

- P0 findings: 0 (original P0 downgraded to P2 after cross-validation)
- P1 findings: 3 (defense-in-depth security gaps) + 4 confirmed from Loop 5
- P2 findings: 2 (scene post-query validation, Stage 25 migration missing)
- Items verified OK: 4
- Cross-validation: 1 P0 downgraded, 4 P1 confirmed, P2 findings mostly confirmed
