# scripts/deploy/ — 生产部署脚本

一键部署与发布脚本目录。

| 脚本 | 用途 |
|---|---|
| `bootstrap.sh` | 云端一键部署总入口（D-BOOTSTRAP）：preflight → .env 云端装配（`.env.production.example` 基线 + `.env.cloud.example` 安全 overlay）→ 镜像拉取 → DB → 迁移 → 扩展初始化（AGE/pgvector）→ MinIO 桶 → 全栈拉起 → readiness → smoke 探针 → 摘要。幂等可重跑；`--plan` 干跑；`--with-demo-seed` 演示数据；`--skip-smoke`；`--lean-observability`（8G 单机裁观测）。方案底稿：`v3-output/DL-D-R1/CLOUD_DEPLOY.md`。 |

日常发版/蓝绿切换不在本目录，见 `scripts/deploy-prod.sh`；备份恢复见 `scripts/backup_prod_data.sh` / `scripts/restore_prod_data.sh`。

快速开始：

```bash
make cloud-plan                                    # 干跑：打印将执行的步骤，不做任何变更
make cloud-up ARGS="--domain api.example.com"      # 真实部署
```
