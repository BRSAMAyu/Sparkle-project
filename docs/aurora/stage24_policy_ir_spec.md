# Aurora Stage 24 Policy IR Spec

- Version: `v1`
- Schema ID: `policy_ir.v1`
- Frozen At: `2026-04-21T00:00:00Z`

## Purpose

Stage 24 compiles commitment accountability into a pure-rule executable IR. The IR is the single source of truth between compiler output and scheduler execution.

## Contract

```text
PolicyRule {
  policy_id: string
  commitment_id: uuid
  user_id: uuid
  trigger: {
    type: "time_before_due" | "streak_break" | "overdue_by" | "peer_missed" | "success_streak"
    params: object
  }
  action: {
    type: "notify_user" | "notify_partner" | "downgrade_priority" | "lower_difficulty"
    params: object
  }
  constraints: {
    daily_budget?: int
    cooldown_hours?: int
    partner_consent_required?: bool
  }
  context: {
    commitment_summary: string
    commitment_due_at?: datetime
    commitment_created_at?: datetime
    evidence_token?: string
    partnership_id?: uuid
    partner_id?: uuid
    partner_consent_granted: bool
    tags: string[]
    metadata: object
  }
  version: "v1"
}
```

## Compatibility

- `v1` is frozen.
- Any schema change requires a version bump and a new snapshot file.
- `scripts/stage24/check_policy_ir_schema.py` blocks drift against the frozen snapshot.

## Template Library

- `due_reminder_3d`
- `due_reminder_1d`
- `due_reminder_0d`
- `peer_missed_3d_partner_notify`
- `overdue_priority_2d`
- `overdue_difficulty_5d`
- `success_streak_7d_positive_feedback`
- `retro_request_overdue_1d`
