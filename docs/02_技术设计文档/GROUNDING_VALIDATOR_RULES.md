# Grounding Validator Rules (v1)

## Purpose
Define the mandatory validation layer for all execution paths. Validator must have the authority to reject execution.

## Rule Categories

### 1) Schema Validation (Hard Fail)
- ExecutablePlan schema version is supported.
- Required fields present.
- `tool_calls` non-empty.
- Params are valid JSON and within size limits.

### 2) Business Rules (Hard Fail)
- User permissions and quotas.
- Resource availability (inventory, schedule conflicts, focus windows).
- Tool call compatibility with current system state.
- Task type allowed for user plan status.

### 3) Safety & Security (Hard Fail)
- Blocklisted tool names or parameters.
- Sensitive actions require double confirm or HITL.
- No hidden data exfiltration or unsafe payloads.

### 4) Pre-flight Checks (Soft/Hard)
- External API reachability (soft fail; allow retry).
- Rate limit budget within thresholds.
- Estimated cost within allowed budget.

### 5) Compensation and Irreversibility
- If `compensation_call` missing, `point_of_no_return=true`.
- `point_of_no_return=true` requires explicit confirmation or HITL.

## Output Contract
```json
{
  "is_valid": true,
  "failure_reason": "string|null",
  "risk_flags": ["string"],
  "requires_confirmation": false,
  "requires_hitl": false
}
```

## Minimal Allowlist (Phase 1)
- Only allow tools in a predefined list.
- Reject unknown tools.
- Reject parameters exceeding size limits.

## Roadmap
- Phase 1: schema + allowlist + basic business rules.
- Phase 2: full business rules + security patterns.
- Phase 3: adaptive validation based on historical failures.
