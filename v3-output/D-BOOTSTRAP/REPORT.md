# D-BOOTSTRAP 报告（归档摘要）

- 交付：scripts/deploy/bootstrap.sh（782 行幂等总入口，--plan/--with-demo-seed/--skip-smoke/--lean-observability）+ .env.cloud.example（云端安全 overlay：LLM_QUOTA_ENABLED=true/GLM_BATCH_ENABLED=false/预算 5-1-2-0.5/占位门禁拒绝未填密钥）+ scripts/deploy/README.md + Makefile cloud-up/cloud-plan。
- 验证：bash -n 过；--plan 干跑 9 步全绿（主会话复跑确认）；合并装配 last-wins 实测；门禁双路径函数级测试；compose config -q 过；密钥正则扫描零命中。
- 与 D-AGE 撞面：运行时探测 age_init one-shot 存在即走 compose 路径（D-AGE 已合入 main，自动生效）。
- 未真机部署项：镜像 pull/迁移等待/AGE exec/WS 探针/公网探活——清单在任务回执与脚本注释。
- 设计偏离：不自动生成密钥（防静默轮换炸卷），改模板+占位门禁。
- patch 备份于 Sparkle-sysrev/backup/2026-09-22/D-BOOTSTRAP/。
