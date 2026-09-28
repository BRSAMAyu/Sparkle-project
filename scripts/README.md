# scripts/ — 部署、治理守卫与运维脚本

治理守卫、部署脚本与本目录单页运维手册的集合。目录规范见
`docs/engineering/REPOSITORY_STANDARDS.md`：一次性脚本入 `scripts/devtools/`
（每脚本一行用途注释），会话产物与运行时数据不入库。

## 文档索引

| 文档 | 用途 |
|---|---|
| [RESTACK_RUNBOOK.md](RESTACK_RUNBOOK.md) | 本机 dev 栈数据面重建手册——**sparkle_db 属主铁律**（真数据卷属 sparkle-cosmos 仓，重建前必查 `docker inspect` 卷前缀）+ 09-28 事故复盘与纠偏步骤（FIX-557） |

## 主要脚本（按用途）

- 部署：`deploy/bootstrap.sh`（云端一键部署总入口）、`deploy-prod.sh`（蓝绿发版/回滚）、`backup_prod_data.sh` / `restore_prod_data.sh` / `install_backup_cron.sh`、`ssl/`
- 治理守卫：`check_rule_*.py`（清单见 `rule_guard_manifest.tsv`，入口 `run_all_rule_guards.sh`）
- 契约/密钥检查：`check_proto_contract.py`、`check_production_secrets.py`、`check_openapi_contract.py` 等 `check_*.py`

> 新增文档必须登记进本 README（REPOSITORY_STANDARDS 规则）。
