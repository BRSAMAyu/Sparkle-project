# JITAI SQAM

## ID1

- `generate_hints()` 在消费 `z_score` 与 `confidence` 前先做 `math.isfinite()` 校验。

## ST1

- 稳定性仍由 Stage 27 kill switch 与 cooldown / daily budget 承担，Stage 32 不改阈值。

## DP1

- 对外事件总线只发 `user_id_hash`，保留 Redis 内部 key 明文以利排障。

## SM1

- JITAI 的情绪相关 nudges 受 Predictive `risk_level` 手递手约束，高风险时不放行 mood-only deviation。
