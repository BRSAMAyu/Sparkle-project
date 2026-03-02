# Stable Rollout Playbook (Research Track -> Production Track)

## Scope
This playbook is for the Sparkle planning/reasoning rollout where stability is the primary objective.

## Guardrails
- `negative_feedback_rate`
- `fallback_rate`
- `stable_cohort_q_gap`
- `p95_latency_ms`

Trigger rollback when any guardrail exceeds threshold for 2 consecutive windows.
Rollback SLA target: <= 10 minutes.

## Rollout stages
1. Internal 100% (24h)
2. External 5% (24h)
3. External 10% (24h)
4. External 30% (24h)
5. External 100%

## Flag matrix (phase baseline)
These values are environment-level overrides. Keep source defaults unchanged.

### Internal validation baseline
- `ENABLE_REASONING_VERIFIER_V1=true`
- `ENABLE_BUDGETED_PLAN_SEARCH_V1=true`
- `ENABLE_PLAN_REPAIR_V1=true`
- `ENABLE_LEARNING_CONTROL_PLANE=true`
- `ENABLE_POLICY_CANDIDATE_PIPELINE=true`
- `ENABLE_META_LEARNING_CHANNEL_ROUTING=true`
- `ENABLE_META_LEARNING_CHANNEL_PROMPT=false`
- `ENABLE_META_LEARNING_CHANNEL_TOOLCHAIN=false`
- `ENABLE_META_POLICY_COMPOSER_V1=false`
- `ENABLE_META_FAIRNESS_GUARDRAIL=false`

### Progressive channel activation
- Start: routing only.
- Then: prompt (research track pass + manual approval).
- Then: toolchain (research track pass + manual approval).
- Enable `ENABLE_META_POLICY_COMPOSER_V1=true` at low external traffic only.
- Enable `ENABLE_META_FAIRNESS_GUARDRAIL=true` on internal first, then external.

## Rollback order
1. Toolchain channel
2. Prompt channel
3. Routing channel
4. Plan search
5. Reasoning verifier
6. Baseline strategy

## Weekly operations checklist
- Daily: rollup + candidate generation health check.
- Weekly: policy review with `channel_health`, `new_user_transfer_gain`, `long_tail_guardrail`, `rollback_recommendation`.
- Bi-weekly: strategy package review and top failure mode coverage check.

## Required report fields
- `channel_health`
- `rollback_recommendation`
- `new_user_transfer_gain`
- `long_tail_guardrail`
- `failure_mode_topn`
- `required_next_candidate_focus`
