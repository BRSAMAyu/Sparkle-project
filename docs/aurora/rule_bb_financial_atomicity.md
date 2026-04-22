# Rule BB - Financial Atomicity

任何涉及 `Photon`、奖励、成就解锁、质押/扣减的多步流程，必须满足以下之一：

1. 同一数据库事务内完成。
2. 或使用显式补偿型 saga，并留下可审计的 before/after 痕迹。

Stage 39 当前锁定的高风险热点：

- [achievement_engine.py](/Users/brsama/code/GitHub/Sparkle-project-stage39/backend/app/services/achievement_engine.py)
- [photon_service.py](/Users/brsama/code/GitHub/Sparkle-project-stage39/backend/app/services/photon_service.py)
- [check_rule_bb_financial_atomicity.py](/Users/brsama/code/GitHub/Sparkle-project-stage39/scripts/guards/check_rule_bb_financial_atomicity.py)

Guard 约束：

1. `photon_service` 必须保留原子扣减路径，不得回退到 check-then-act。
2. `achievement_engine` 必须保留事务嵌套/外部事务接力，避免成就解锁与奖励发放分离提交。

Stage 40 若新增其他资产变动入口，必须把对应文件加入 Rule BB guard 扫描范围。
