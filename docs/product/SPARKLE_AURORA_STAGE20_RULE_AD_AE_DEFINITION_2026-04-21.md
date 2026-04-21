# SPARKLE Aurora Stage 20 Rule AD + AE Definition (2026-04-21)

> Status: locked for Stage 20 implementation
> Scope: Sufficiency Judge + Conflict Resolver + their Router / Memory call sites

## 1. Rule AD

One-sentence definition:

`Sufficiency Judge` 是确定性规则评分器，输出必须分 `task_sufficiency` 与 `context_sufficiency` 两路；Router 仅可基于 `task_sufficiency` 做分支，`context_sufficiency` 只能进入 prompt caveat。

Mandatory constraints:

1. Sufficiency Judge must be pure-rule and may not invoke any LLM.
2. The Stage 20 v1 scoring formula is frozen before measurement.
3. Inputs are limited to Aggregator state, Working Memory snapshot, and current-turn parsed routing signals.
4. Every output must include `missing_dimensions` for explainability.

Frozen Stage 20 v1 task-scoring formula:

`task_score = intent_clarity * 0.40 + target_object_resolved * 0.35 + constraint_explicit * 0.25`

Each sub-dimension is discretized to `0.0`, `0.5`, or `1.0`.

Forbidden scenarios:

1. Merging task and context signals into one score
2. Branching Router logic on `context_sufficiency`
3. Feeding any sufficiency output into Stage 18 push policy or delivery
4. Using sufficiency output to bypass Rule Z social boundaries
5. Writing sufficiency output back into Aggregator source systems

## 2. Rule AE

One-sentence definition:

`Conflict Resolver` 是确定性优先级裁决器；任一冲突必须留下 `conflict_resolution_record`，严禁静默覆盖。

Frozen priority chain:

`explicit_correction > inferred_extraction(rule-based) > inferred_extraction(LLM) > working_memory`

Same-lane tie-breakers:

1. higher confidence wins
2. if confidence ties, newer wins
3. if confidence and time both tie, keep both and emit `unresolved_conflict`

Forbidden scenarios:

1. Cross-user conflict arbitration
2. Skipping `evidence_token` validation
3. Promoting LLM-extracted records to rule-based priority
4. Hard-deleting overridden records instead of soft-retracting them
5. Feeding Conflict Resolver output into Stage 18 push policy or delivery

## 3. CI Guard Entry Points

1. `scripts/check_rule_ad_sufficiency_split.py`
2. `scripts/check_rule_ae_conflict_audit.py`

## 4. Stage 17 Carry-Forward Note

The Stage 17 Rule Z HMAC form remains:

`HMAC-SHA256(key=mentioning_user_id || mentioned_user_id_or_null, msg=normalized_person_name)`

Current Stage 17 implementation uses `mentioned_user_id_or_null = null` because the mentioned party is not resolved to a registered Sparkle user.

If a future governed upgrade resolves the mentioned party to a Sparkle account, the key must upgrade from:

`f"{user_id}:null"`

to:

`f"{user_id}:{mentioned_user_id}"`

That upgrade is only allowed with:

1. a one-time historical hash recomputation script
2. a dedup pass over the user-owned mention rows
3. an explicit governance review confirming Rule Z no-cross-user-join guarantees remain intact
