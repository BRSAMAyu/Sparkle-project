# Rule BC - Idempotency Key Required

凡是 HTTP 写接口里会造成资产变动或奖励状态变化的入口，必须显式解析 `Idempotency-Key`。

Stage 39 当前锁定的 handler：

- [shop.py](/Users/brsama/code/GitHub/Sparkle-project-stage39/backend/app/api/v1/shop.py)
- [photons.py](/Users/brsama/code/GitHub/Sparkle-project-stage39/backend/app/api/v1/photons.py)
- [achievements.py](/Users/brsama/code/GitHub/Sparkle-project-stage39/backend/app/api/v1/achievements.py)
- [check_rule_bc_idempotency_key.py](/Users/brsama/code/GitHub/Sparkle-project-stage39/scripts/guards/check_rule_bc_idempotency_key.py)

Guard 约束：

1. 商店购买必须解析 `Idempotency-Key`，并进入服务端幂等分支。
2. Photon 转账/管理员调整、契约创建/取消、内部成就事件处理，必须至少在 handler front door 接受该 header。
3. 幂等键必须按 `user_id` 作用域隔离，禁止跨用户共享结果。

Stage 40 若把更多资产写入口切到真幂等存储，应继续沿用本规则，不得绕过 header front door。
