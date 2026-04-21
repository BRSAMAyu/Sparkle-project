# Sparkle Aurora Full Audit Protocol

> Version: 2.0 / 2026-04-21
> Scope: Stage 4-29 loop-based repo audit
> Mode: baseline audit first, optional closeout second

## Purpose

This protocol defines a reusable, loop-based audit process for a large staged codebase.

It separates three artifacts clearly:

1. **Raw loop outputs**: `docs/product/audit_findings/loop*.md`
2. **Normalized final report**: `docs/product/SPARKLE_AURORA_FULL_AUDIT_STAGE4-29_2026-04-21.md`
3. **Machine state**: `docs/product/audit_state.json`

The key rule is:

- Loop files may contain provisional severities.
- The final report is the authority after cross-validation.
- If post-audit fixes are applied, they must be recorded explicitly as closeout actions rather than silently rewriting baseline counts.

## Audit Flow

1. Read `docs/product/audit_state.json`
2. Execute the next pending loop
3. Write raw findings to a loop file
4. Update `audit_state.json`
5. After all loops complete, normalize findings in the final report
6. Optional: apply narrow closeout fixes for confirmed medium issues
7. Record any closeout in both the final report and `audit_state.json`

## Loop Design

### Loop 1
Critical infrastructure:

- schema/proto parity
- generated-code freshness
- router field usage
- CI guard coverage

### Loop 2
Recent stages:

- Stages 29-25
- handoff claims vs code constants
- test existence and claimed artifacts

### Loop 3
Mid stages:

- Stages 24-20
- migration continuity
- import-chain survival

### Loop 4
Early stages:

- Stages 19-4
- foundational file survival
- stale path/import breakage

### Loop 5
Governance quality:

- all named rules
- guard quality rating
- CI wiring
- missing automation

### Loop 6
Security and cross-validation:

- cross-user isolation
- Alembic chain topology
- re-check of earlier findings

### Loop 7
Final synthesis:

- dedupe
- severity normalization
- false-positive resolution
- final report generation

## Severity Model

- `P0`: fundamental law violation, real cross-user leak, corruption, or broken wire contract
- `P1`: governance gap, strong bypass risk, or claim/implementation mismatch with practical impact
- `P2`: defense-in-depth gap, doc drift, guard fragility, naming drift, or test-count ambiguity
- `False Positive`: initially suspicious, later disproven by deeper code-path or architecture review

## Output Requirements

Each loop file should contain:

- loop name and timestamp
- what was checked
- finding table with file references
- verified-ok table
- short summary

The final report should contain:

- executive summary
- coverage
- contract sync status
- governance and CI quality
- migration health
- security matrix
- final findings register
- false-positive table
- closeout status
- recommendations

`audit_state.json` should contain:

- lifecycle status
- loop list
- deliverable paths
- baseline counts
- open counts after closeout, if any
- closeout actions

## Closeout Rules

Closeout is optional and happens only **after** the audit has already established baseline counts.

Valid closeout candidates:

- low-risk defense-in-depth fixes
- guard hardening
- documentation synchronization
- test additions that prove a fix

Invalid closeout candidates:

- broad refactors
- feature work
- silent reclassification without evidence
- rewriting raw loop outputs to hide what was initially found

## Good Practice

- Keep loop files honest and local to what that loop actually saw
- Normalize only in the final report
- Preserve historical baseline counts, then record what was fixed afterward
- Prefer evidence over interpretation when a finding is borderline
