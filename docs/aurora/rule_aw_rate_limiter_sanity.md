# Rule AW - Rate Limiter Dimensional Sanity

任何 token bucket / leaky bucket / sliding window 的限流实现，必须显式满足以下要求：

1. 代码注释必须声明 `elapsed_unit` 和 `rate_unit`。
2. 关键计算行必须给出量纲等式注释，例如：
   `tokens_added = (elapsed_ms / 1000.0) * (rate_per_s)`
3. 必须存在 `*_DimensionalCorrectness` 单元测试，覆盖至少一个固定 `elapsed/rate` 组合。
4. 必须暴露可观测性：
   - `rate_limiter_tokens_current`
   - `rate_limiter_rejections_total`

Stage 36 将该规则锁定到：

- [distributed_rate_limiter.go](/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/middleware/distributed_rate_limiter.go)
- [distributed_rate_limiter_test.go](/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/internal/middleware/distributed_rate_limiter_test.go)
- [check_rule_aw_rate_limiter_sanity.py](/Users/brsama/code/GitHub/Sparkle-project/scripts/guards/check_rule_aw_rate_limiter_sanity.py)
