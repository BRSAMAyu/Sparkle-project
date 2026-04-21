# Sparkle Aurora Full Audit Protocol

> Version: 2.0 / 2026-04-21
> Time budget: 90 minutes (7 loops × ~12 min each)
> This file is the single source of truth for the loop-based audit mechanism.
> Each loop reads this file + audit_state.json, executes the next pending task, and updates state.

## Role

You are an independent auditor performing a multi-loop full-project audit of Sparkle Aurora (Stage 4-29). You do NOT modify any source code. You only read files, search code, and write findings.

## State Machine

1. Read `docs/product/audit_state.json`
2. Find the first phase with `"status": "pending"`
3. Execute that phase's work (see Phase Definitions below)
4. Write findings to `docs/product/audit_findings/loop{N}_{name}.md`
5. Update `docs/product/audit_state.json`: set phase status to `"done"`, increment `current_loop`, update `last_updated_at`, update findings counts and coverage
6. If all phases are `"done"`, set top-level `"status": "complete"`

## Output Format Per Phase

```markdown
# Loop {N}: {Phase Name}

> Executed: {ISO timestamp}
> Sub-agents used: {count and types}
> Duration: {approximate minutes}

## Findings

| # | Severity | Stage | Category | Finding | File:Line | Evidence |
|---|----------|-------|----------|---------|-----------|----------|
| L{N}-1 | P0/P1/P2 | S29 | ... | ... | ... | ... |

## Verified OK

| # | Stage | Claim | Verified In | Notes |
|---|-------|-------|-------------|-------|
| V{N}-1 | S29 | ... | file:line | ... |

## Summary

- P0 findings: {count}
- P1 findings: {count}
- P2 findings: {count}
- Items verified OK: {count}
- False positives: {count}
```

Severity definitions:
- **P0**: Violates project fundamental law (proto→gen→impl), security hole, data loss risk, cross-user leak
- **P1**: Claim-implementation mismatch, rule bypass possible, CI gap, migration chain break
- **P2**: Doc drift, naming inconsistency, code smell, missing telemetry

## Sub-Agent Strategy

Each loop should use **3-5 Explore agents in parallel** to maximize coverage within the 12-minute window. Sub-agents should:
- Be given specific file lists and grep patterns
- Return structured findings with file:line references
- Focus on one verification dimension each (e.g., one agent for schema sync, one for test existence, one for guard quality)

## Phase Definitions

### Loop 1: Critical Infrastructure (~12 min)

**Target files** (read ALL of these):
- `backend/app/state_aggregator/schema.py` — extract every `StateFieldEnvelope` field name and schema_version
- `proto/user_state.proto` — extract every field in `UserStateV1` message
- `backend/app/state_aggregator/service.py` — verify each field has a builder
- `backend/app/orchestration/routing_engine.py` — grep for all Aggregator field reads
- `.github/workflows/ci.yml` — search for all `check_rule` and `gate_final` references
- `backend/app/gen/` — check if `user_state_pb2.py` exists (Python proto generated code)
- `backend/app/gen/userstate/` — check for Go generated code
- `mobile/lib/gen/` — check for Dart generated code

**Work items** (use 4 sub-agents in parallel):

**Agent A — Schema-Proto Sync**:
1. Read `backend/app/state_aggregator/schema.py` completely
2. Extract every field name from `StateFieldEnvelope` definitions
3. Read `proto/user_state.proto` completely
4. Extract every field in `UserStateV1` message
5. Build a field-by-field comparison table: Python schema vs proto
6. Mark any field present in Python but absent in proto (or vice versa) with severity

**Agent B — Service-Router Coverage**:
1. Read `backend/app/state_aggregator/service.py`
2. List every `_build_*` method and the field it builds
3. Read `backend/app/orchestration/routing_engine.py` (or `dual_core_router.py`)
4. Grep for all Aggregator field reads (sufficiency, achievement, calendar, skill, srl, foresight, traits, scene, reflection, etc.)
5. List every field read with line numbers
6. Flag any field read that is NOT explicitly whitelisted in a governance rule

**Agent C — CI Guard Coverage**:
1. Read `.github/workflows/ci.yml`
2. Extract ALL `check_rule` and `gate_final` script references
3. Glob for ALL guard scripts in `scripts/stage*/` directories
4. Compute coverage: how many guard scripts are referenced in CI vs total existing
5. Flag any stage with guard scripts but no CI reference

**Agent D — Generated Code Verification**:
1. Check if `backend/app/gen/` contains Python proto generated code (`*_pb2.py`, `*_pb2_grpc.py`)
2. Check if `backend/gateway/gen/` contains Go generated code
3. Check if `mobile/lib/gen/` contains Dart generated code
4. For each generated file, verify its modification date is AFTER the corresponding `.proto` file
5. If Python proto generated code is completely missing, flag as P0

### Loop 2: Recent Stage Deep Verification (29-25) (~12 min)

**Target**: Read 5 handoff docs + verify key claims in code.

**Sub-agents**: Use 3 agents in parallel:
- **Agent A**: Stages 29 + 28
- **Agent B**: Stages 27 + 26
- **Agent C**: Stage 25

For each Stage:
1. Read handoff: `docs/product/SPARKLE_AURORA_STAGE{N}_HANDOFF_2026-04-21.md`
2. Extract ALL file paths mentioned in handoff
3. For each file: verify it exists using Glob (flag any missing)
4. For key constants (thresholds, version strings, enum values): grep the actual code to confirm match
5. For claimed test files: verify they exist, count test functions, verify test count matches handoff claim
6. For claimed guard scripts: verify they exist and contain expected logic
7. For claimed Alembic migrations: verify file exists and contains expected revision ID
8. Cross-check Aggregator version claim against actual schema.py
9. Verify kill-switch service exists and has expected mode constants

**Additional deep checks for these recent stages**:
- Verify EventBus event types mentioned in handoff are actually registered in `backend/app/core/event_bus.py`
- Verify Redis stream names and consumer groups match handoff claims
- Verify TTL values mentioned in handoff match actual code

### Loop 3: Mid Stage Verification (24-20) (~12 min)

Same methodology as Loop 2, covering Stages 24, 23, 22, 21, 20.

**Sub-agents**: Use 3 agents:
- **Agent A**: Stages 24 + 23
- **Agent B**: Stages 22 + 21
- **Agent C**: Stage 20

Same verification checklist as Loop 2, plus:
1. For each stage, verify that later stages did NOT delete or rename files it depends on
2. Check for import chain breaks: grep for imports of files claimed by these stages
3. Verify migration chain links: each stage's migration should reference the previous stage's migration as `down_revision`

### Loop 4: Early Stage Verification (19-4) (~12 min)

**Lighter touch** — these are older stages, focus on:

**Sub-agents**: Use 3 agents:
- **Agent A**: Stages 19 + 18 + 17 + 16
- **Agent B**: Stages 15 + 14 + 13 + 12 + 11 + 10 + 9 + 8
- **Agent C**: Stages 7 + 6 + 5 + 4

For each Stage:
1. Read handoff, extract 3-5 most critical file paths
2. Verify those files still exist (not deleted by later stages)
3. Verify key services mentioned still exist
4. Focus on potential breakage: did later stages modify files that earlier stages depended on?
5. For governance rules introduced: verify the rule's guard script still passes
6. Check for stale code: any imports pointing to deleted/renamed modules?

**Specific known issues to verify** (from audit_state.json):
- `proto_sync_3_fields_missing` — are there really 3 fields in Python but not in proto?
- `python_proto_gen_missing` — is Python generated code really absent?
- `ci_only_rule_k` — does CI only check Rule K?
- `stage19_22_migration_gap` — is there a gap in the migration chain between Stages 19-22?

### Loop 5: Governance Rule Guard Quality (~12 min)

**Target**: All 24 governance rules (G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, Y, Z, AB, AC, AD, AE, AH, AI, AJ, AK, AL, AM, AN).

**Sub-agents**: Use 4 agents:
- **Agent A**: Rules G, H, I, J, K, L, M (base rules from Stages 4-8)
- **Agent B**: Rules N, O, P, Q, R, S, T, U, V (boundary/eval/close rules)
- **Agent C**: Rules Y, Z, AB, AC, AD, AE (Stage 16-22 rules)
- **Agent D**: Rules AH, AI, AJ, AK, AL, AM, AN (Stage 23-29 rules)

For each rule with a guard script:
1. Read the guard script source code completely
2. Classify its checking method: string-match / AST / runtime / hybrid
3. Assess bypass risk: can an import alias, dynamic import, or string concat evade it?
4. Check CWD dependency: does it use hardcoded relative paths?
5. Rate: ROBUST / ADEQUATE / FRAGILE
6. Verify the guard is actually called in CI (`.github/workflows/ci.yml`) or in `gate_final.sh`

For rules WITHOUT guard scripts:
1. Flag as P1 finding
2. Check if the rule's constraint is enforced by any other mechanism (test file, CI step, convention)
3. If no enforcement exists at all, escalate to P0

### Loop 6: Cross-User Security + Alembic Chain + Cross-Validation (~12 min)

**Part A: Cross-user isolation** (15 subsystems)

**Sub-agent A** — For each subsystem listed in audit_state.json under "subsystems":
1. Find its core service file
2. Grep for all database query patterns (`SELECT`, `WHERE`, `filter`, `.query`, `session.execute`, `session.scalars`)
3. Verify every query includes `user_id` filtering
4. Flag any query that could return cross-user data
5. Check for raw SQL that might bypass ORM user_id filters
6. Pay special attention to aggregation queries (COUNT, SUM, AVG) — do they filter by user_id?

**Part B: Alembic chain**

**Sub-agent B**:
1. List all `s*-prefixed` migration files in `backend/alembic/versions/`
2. For each: read its `revision` and `down_revision`
3. Build the full chain graph: verify every migration links to exactly one parent (except the root)
4. Flag any broken links (referenced revision doesn't exist)
5. Flag any Stage with handoff claiming migration but file missing
6. Check for migration ordering anomalies (e.g., Stage 23 migration pointing to Stage 25 as parent)

**Part C: Cross-validation**

**Sub-agent C**:
1. Read ALL previous finding files (loop1 through loop5)
2. For each P0 finding: re-verify with a fresh grep/read. Confirm or downgrade to P1/P2/false-positive.
3. For each P1 finding: re-verify 50% (at minimum). Confirm or downgrade.
4. For each P2 finding: spot-check 25%. Confirm or downgrade.
5. Record in `audit_state.json` cross_validation section: confirmed, false_positive, needs_investigation counts
6. Special focus: re-check the 7 known_issues from audit_state.json

### Loop 7: Final Synthesis (~12 min)

**No sub-agents needed** — this is a synthesis loop.

1. Read ALL finding files (loop1-loop6)
2. Read `docs/product/audit_state.json` for cross-validation results
3. De-duplicate findings (same issue found by multiple loops)
4. Merge cross-validation results from loop 6
5. Generate final report at `docs/product/SPARKLE_AURORA_FULL_AUDIT_STAGE4-29_2026-04-21.md`

**Final report structure**:
```markdown
# Sparkle Aurora Full Audit Report (Stage 4-29)

> Date: 2026-04-21
> Auditor: GLM-observer (independent, loop-based)
> Duration: ~90 minutes
> Method: 7-loop state-file-driven audit with cross-validation

## §0 Executive Summary
- [Overall health rating: ROBUST / ADEQUATE / NEEDS_ATTENTION / CRITICAL]
- [Total findings: P0 x, P1 y, P2 z]
- [Key risks in 3 bullet points]
- [Immediate action items]

## §1 Method & Coverage
- Loops executed: 7
- Stages audited: X/26
- Rules audited: X/24
- Subsystems audited for cross-user: X/15
- Cross-validation rate: X%
- Known issues resolved: X/7

## §2 Aggregator/Proto Sync Status
- [Field comparison table]
- [Version progression: v1.0 → v1.10]
- [Any sync gaps]

## §3 Router Branch Safety
- [Fields read by router]
- [Which are whitelisted vs unwhitelisted]
- [Rule compliance status]

## §4 Per-Stage Handoff Consistency (summary table)
| Stage | Handoff Exists | Files Verified | Tests Verified | Migrations OK | Issues |
|-------|---------------|----------------|----------------|---------------|--------|

## §5 Governance Rule Quality
| Rule | Guard Exists | Method | Rating | Bypass Risk | CI Coverage |
|------|-------------|--------|--------|-------------|-------------|

## §6 CI Automation Coverage
- Guard scripts in CI: X/Y
- Coverage percentage: Z%
- Gaps and recommendations

## §7 Alembic Chain Health
- Total migrations: X
- Chain continuity: OK/BROKEN
- Breaks listed with details

## §8 Cross-User Security Matrix
| Subsystem | Queries Audited | All Filtered | Issues |
|-----------|----------------|-------------|--------|

## §9 Confirmed Findings
### P0 (Critical)
| # | Stage | Finding | File:Line | Action Required |
|---|-------|---------|-----------|----------------|

### P1 (High)
| # | Stage | Finding | File:Line | Action Required |
|---|-------|---------|-----------|----------------|

### P2 (Medium)
| # | Stage | Finding | File:Line | Notes |
|---|-------|---------|-----------|-------|

## §10 False Positives Clarified
| # | Original Finding | Why False Positive | Confirmed By |
|---|-----------------|-------------------|-------------|

## §11 Cross-Validation Results
- Total findings re-examined: X
- Confirmed: X
- Downgraded: X
- False positives: X

## §12 Recommendations (prioritized)
1. [P0 fixes — immediate]
2. [P1 fixes — this week]
3. [P2 fixes — next sprint]
4. [Process improvements]
```

6. Update `docs/product/audit_state.json`:
   - Set top-level status to `"complete"`
   - Fill in final findings_total counts
   - Fill in coverage section with actual numbers
   - Set all phases to `"done"`

## Subsystem List (for cross-user audit)

| # | Subsystem | Core File | Stage |
|---|-----------|-----------|-------|
| 1 | Memory Write | memory_inferred_write_lane.py | 16 |
| 2 | Social Context | router_context_reader.py | 17 |
| 3 | Push Delivery | push_delivery_service.py | 18 |
| 4 | Working Memory | working_memory/service.py | 19 |
| 5 | Sufficiency Judge | sufficiency_judge_service.py | 20 |
| 6 | Conflict Resolver | conflict_resolver_service.py | 20 |
| 7 | Route History | route_history_service.py | 20 |
| 8 | Skill System | skill_store_service.py | 21 |
| 9 | Bayesian Learner | persistent_bayesian_learner.py | 23 |
| 10 | Policy Compiler | policy_compiler_service.py | 24 |
| 11 | Reflection | reflection_agent.py | 25 |
| 12 | Scene | scene_consolidation_service.py | 26 |
| 13 | Foresight/PersDyn | persdyn_attractor_service.py | 27 |
| 14 | Traits | traits_merge_service.py | 28 |
| 15 | SRL Tracker | srl_phase_tracker_service.py | 29 |

## Anti-Patterns (DO NOT)

- DO NOT modify any source code
- DO NOT run tests
- DO NOT skip a verification because "it was probably fine"
- DO NOT mark a finding as confirmed without re-reading the actual file
- DO NOT produce findings without file paths and line numbers
- DO NOT exceed the scope of the current loop's phase definition
- DO NOT trust handoff claims without code-level verification
- DO NOT downgrade a finding without concrete evidence it was a false positive

## Completion Check

When updating `audit_state.json`, verify:
- All phases have `"status": "done"`
- `findings_total.p0`, `findings_total.p1`, `findings_total.p2` are accurate
- The final report file has been written
- Coverage numbers are filled in
- Cross-validation section is complete

If all phases are done, set top-level status to `"complete"` and STOP.
