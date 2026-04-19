# SPARKLE Aurora Growth Signal Contract

## Scope

This document defines the WS-G1 one-way achievement -> Aurora uplink. The goal is a read-only sampler, a bounded serializable contract, and a real Aurora consumption path that can safely represent cold-start / empty-state behavior.

## Contract shape

The achievement sampler emits a `GrowthSignalContract` with these stable fields:

- `contract_version`
- `source`
- `user_id`
- `sampled_at`
- `cold_start`
- `fallback_reason`
- `streak_days`
- `achievement_count`
- `recent_achievement_ids`
- `recent_achievement_labels`
- `growth_phase`
- `momentum_score`
- `evidence`
- `limits`

The serialized contract is intentionally bounded:

- recent achievements capped at 5
- evidence items capped at 4
- summary payload is a smaller projection for Aurora-facing reads

## Read-only sampler

`backend/app/orchestration/signal_samplers/achievement_sampler.py` only reads from the achievement service interface. It does not write achievement rows, does not mutate achievement state, and does not import the achievement engine back into Aurora.

Expected read methods:

- `get_streak_stats(user_id)`
- `get_user_achievements(user_id)`

## Aurora consumption path

`backend/app/aurora/signal_aggregator.py` consumes the sampler output and places it into the `achievement_engine` signal slot as:

- `growth_signal_contract`
- `growth_signal_summary`

This keeps the contract live in the snapshot pipeline instead of leaving it as an unused schema file.

## Cold-start behavior

If the achievement service is missing, empty, or returns no usable data, the sampler emits an explicit cold-start contract:

- `cold_start = true`
- `growth_phase = "cold_start"`
- `fallback_reason` explains the absence of usable data
- `momentum_score = 0.0`

## Exact example payload

```json
{
  "contract_version": "ws-g1.2026-04-19.v1",
  "source": "achievement_sampler",
  "user_id": "7b972d7c-2c92-4a3f-9a4e-ff6a0d6f3c50",
  "sampled_at": "2026-04-19T09:00:00",
  "cold_start": false,
  "fallback_reason": null,
  "streak_days": 11,
  "achievement_count": 6,
  "recent_achievement_ids": ["a1", "a2", "a3", "a4", "a5"],
  "recent_achievement_labels": ["First Step", "Momentum Builder", "Consistency", "Explorer", "Closer"],
  "growth_phase": "building",
  "momentum_score": 0.7114,
  "evidence": [
    {
      "kind": "streak",
      "text": "连续打卡 11 天",
      "weight": 0.55
    },
    {
      "kind": "achievement_count",
      "text": "累计解锁 6 个成就",
      "weight": 0.35
    },
    {
      "kind": "recent_achievement",
      "text": "最近成就：First Step、Momentum Builder、Consistency",
      "weight": 0.1
    }
  ],
  "limits": {
    "max_recent_achievements": 5,
    "max_evidence_items": 4
  }
}
```
