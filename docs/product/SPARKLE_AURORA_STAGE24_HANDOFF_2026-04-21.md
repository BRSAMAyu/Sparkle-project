# SPARKLE Aurora Stage 24 Handoff

## Final Accept Matrix

- WS-AP-IR: implemented
- WS-AP-COMPILER: implemented
- WS-AP-SCHEDULER: implemented
- WS-AP-GUARD: implemented

## IR v1 Snapshot

- Spec: `docs/aurora/stage24_policy_ir_spec.md`
- Snapshot: `docs/aurora/stage24_policy_ir_schema_v1.json`

## Template Library

- due reminders: `3d`, `1d`, `0d`
- peer missed partner notify: `>=3d`
- overdue downgrade priority: `2d`
- overdue lower difficulty: `5d`
- success streak positive feedback: `>=7d`
- overdue retro request: `1d without outcome`

## Path

- Path A
- Reason: compiler, scheduler, kill-switch, aggregator v1.5, and mobile read-only summary all wired end to end.

## SQAM Evidence

- ID1: deterministic `policy_id + trigger + action`
- ST1: compiler idempotence tests
- DP1: 8 template entries across time and event triggers
- SM1: policy metrics for compiled/scheduled/triggered/budget/cooldown

## Aggregator v1.5 Diff

- Added `pending_policies` read-only summary to user-state schema and proto.

## Redline Evidence

- partner notifications require explicit `accountability:partner_consent:true`
- missing consent or partner id blocks notify_partner execution

## Validation

- Backend tests: see Stage 24 scripts
- Mobile tests: pending policy summary rendering
- Guards: `check_rule_ai_policy_purity.py`, `check_policy_ir_schema.py`

## Stage 25 Preconditions

- Observe live/shadow metrics before widening rollout
- Decide whether commitment metadata should grow from tag-based consent into a first-class schema
