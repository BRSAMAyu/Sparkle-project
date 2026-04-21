# SPARKLE Aurora Stage 21 Rule AF Definition (2026-04-21)

> Status: locked for Stage 21 implementation
> Scope: cross-user Skill sharing, fork adoption, and public catalog boundaries

Numbering history note:

Memory roadmap drafts once reserved `Rule AA` for cross-user Skill sharing. After Stage 18 introduced `Rule AB`, that early placeholder was permanently skipped and is never reused. The live governance sequence is now:

`Rule Y -> Rule Z -> Rule AB -> Rule AC -> Rule AD -> Rule AE -> Rule AF -> Rule AG`

## 1. Rule AF

One-sentence definition:

`Cross-user Skill sharing` 必须 opt-in per skill、必经 `PII scanner + prompt injection detector + moderation queue` 三步流水线、作者匿名化、采用为 fork 复制、严禁任何反向 telemetry。

Mandatory constraints:

1. Sharing must be enabled per skill; there is no account-level blanket sharing mode.
2. Every publish attempt must pass automated PII scanning before any downstream review step.
3. Every publish attempt must pass a frozen prompt-injection detector before moderation.
4. Every publish attempt must enter a moderation queue, including test and mock environments.
5. Adoption is always a fork copy into the adopter's private `user_skills` store.
6. Shared catalog rows may not retain `author_user_id`; authors are rendered as anonymous only.

Forbidden scenarios:

1. Skill content containing `person_mention`
2. Skill content containing concrete `inferred_extraction` values
3. Preserving `author_user_id` in any adopted fork path
4. Exposing cross-user usage statistics in the shared catalog
5. Any user-to-user recommendation such as “someone like you uses this Skill”
6. Referencing `shared_skills` pool content from Aggregator fields. Only forked copies in `user_skills` may contribute metadata to Aggregator.
7. Reusing shared Skill content as LLM extractor few-shot material
8. Showing cross-user aggregated usage counters to end users

## 2. Required Pipelines

Publish pipeline:

1. deterministic regex PII scan
2. Haiku-backed secondary PII filter using frozen prompt
3. Haiku-backed prompt-injection detector using frozen prompt
4. moderation queue insert
5. approval or reject outcome
6. anonymous shared-catalog publish

Fork pipeline:

1. select approved shared skill
2. copy content into private `user_skills`
3. write `forked_from_share_id`
4. never copy any author identifier

Withdraw pipeline:

1. author revokes share from private Skill panel
2. shared catalog row is soft-deleted / unpublished
3. existing forks remain intact
4. no new forks may be created from withdrawn content

## 3. Daily Limit

Each user may publish at most `3` Skills per UTC day.

## 4. CI Guard Entry Points

1. `scripts/check_rule_af_skill_share_isolation.py`
2. `scripts/check_rule_af_skill_pii_pipeline.py`
