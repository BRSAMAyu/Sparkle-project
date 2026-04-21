# SPARKLE Aurora Stage 17 Rule Z Definition (2026-04-20)

> Status: locked for Stage 17 implementation
> Scope: any Stage 17 inferred write whose subject is a person, relationship, or commitment

## 1. One-Sentence Rule

用户 A 提到人物 B 时，只能在 A 自己的画像中生成派生事实；这些事实不得写入 B 的画像、不得跨用户聚合、不得作为可识别的身份数据导出。

## 2. Mandatory Constraints

1. Every Stage 17 social inferred write must set `mentioned_entity_owner_user_id == user_id`.
2. Any read that observes mismatched ownership must hard-fail instead of silently degrading.
3. Mentioned-entity identity must use HMAC-SHA256 and may not use raw names, global SHA-1, or unsalted hashes.
4. Raw names must never be stored as lookup keys.
5. Human-readable context must resolve through `evidence_token` back to the original turn, not by reading a name from the memory row.

## 3. HMAC Boundary

Required form:

`mentioned_entity_hash = HMAC-SHA256(key=mentioning_user_id || mentioned_user_id_or_null, msg=normalized_person_name)`

Rejected forms:

1. `SHA1(normalized_person_name)`
2. `SHA256(normalized_person_name)` without an ownership-bound key
3. any raw-name equality lookup across users

## 4. Architecture Red Lines

1. No global person index table may be created.
2. No cross-user join on `mentioned_entity_hash` is allowed.
3. No Router, recommender, or learner path may treat social mention facts as cold-start priors in Stage 17.

## 5. Forbidden Scenarios

1. Searching “all users who mentioned Zhang San”
2. Counting how many users mentioned a real person
3. Using `person_mention` as a cold-start recommendation feature
4. Showing raw mention text in support or ops tooling
5. Feeding Stage 17 social mention data into Stage 21 learner `source_state`

## 6. Stage 17 Enforcement

Stage 17 enforces Rule Z through:

1. static CI guard extensions in `scripts/check_rule_k_write_paths.py`
2. namespace isolation via `social_context`
3. ownership-bound read-side filtering

## 7. HMAC Upgrade Path

Stage 17 intentionally uses the ownership-bound key form `f"{user_id}:null"` because the mentioned party is not yet resolved to a registered Sparkle user.

If a future governed upgrade resolves the mentioned party to a Sparkle account, the key form must upgrade to `f"{user_id}:{mentioned_user_id}"`. That upgrade is only allowed with:

1. a one-time historical hash recomputation pass
2. a dedup step over the owner's existing mention rows
3. an explicit governance review confirming the Rule Z no-cross-user-join boundary still holds
