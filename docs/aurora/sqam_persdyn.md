# PersDyn SQAM

## ID1

- `_build_observation_for_day()` 的 5 个维度统一经 `_clamp_unit_interval()` 收敛到 `[0,1]`。

## ST1

- `_ema()` 只接受 `math.isfinite()` 值，遇到非有限中间态直接回落到 `0.0`。

## DP1

- `attractor_updated` 事件仅保留 `user_id / dimensions / updated_at`，不导出 `baseline / variability / recovery_rate / confidence`。

## SM1

- Stage 32 guard 扫描决策路径，禁止把 `mood_valence` 作为单一分支因子。
