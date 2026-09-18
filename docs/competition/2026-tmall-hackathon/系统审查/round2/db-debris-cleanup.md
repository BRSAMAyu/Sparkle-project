# DB Debris 清理 — 脚本落地与演练库验证报告

- 执行：数据库运维清理专项（round2 schema 审计移交项处置）
- 基线：`main@b8f4e7d8`；挂账来源 `b21dce46`（[schema-consistency-audit.md](schema-consistency-audit.md) §三 P1 / §四处置 3）
- patch：[db-debris-cleanup.patch](db-debris-cleanup.patch)

---

## 一、产出

| 工件 | 说明 |
|---|---|
| `scripts/devtools/db_debris_cleanup.py` | 清理脚本：默认 `--dry-run`（只读，列项+行数+磁盘估算）；`--apply` 逐项 `DROP TABLE ... CASCADE` / `DROP COLUMN`，前后存在性校验+操作日志；交互终端下 `--apply` 需输入库名确认（`--non-interactive` 供演练/CI） |
| `docs/engineering/DB_DEBRIS_CLEANUP.md` | runbook：何时跑（先演练后真库）、如何核对、回滚=重建 dev 库流程 |
| README 登记 | `docs/engineering/README.md`、`scripts/devtools/README.md` 各 +1 行 |

**清理项总数：32**（29 张 db-only 会话遗留整表 + `tasks.scheduled_at/timezone/version` 三列）。

**tasks 三列判定**（任务 3）：迁移链 grep 证实 `scheduled_at` 仅出现在 `s40b1c2d3e4_add_aurora_runtime_v1.py` 且目标表为 `aurora_scheduled_wakes`；`timezone`/`version` 无任何 tasks 相关迁移操作 → 三列在迁移链上**无来源**，定性 db-only（audit 报告 §三 P1 原判），**脚本删，无需 alembic drop 迁移**。

**明确不做**：白名单另三列（`cards.archived_at`/`chat_messages.metadata`/`user_settings.accessibility_settings`）为**迁移链上 MIG-only 死列**，删除须走 alembic drop 迁移（移交清单第 1 条），脚本结构性禁止触碰。

## 二、脚本安全设计

1. 清单即授权：仅对常量 `DEBRIS_TABLES`(29)/`DEBRIS_COLUMNS`(3)（誊抄 `orm_migration_audit.py` 白名单，注明来源 commit）生成 DDL，无动态目标；`tasks` 整表删除有 assert 硬禁。
2. 依赖保护：DROP 前查入边 FK 与视图/物化视图依赖，凡白名单外对象引用 → 拒删该项（防 CASCADE 波及），exit 1 提示人工。
3. 幂等：全语句 `IF EXISTS` + 前后存在性校验，重复执行空转 exit 0。

## 三、演练验证（2026-09-18）

环境：dev 库 39 个活动连接，`CREATE DATABASE ... TEMPLATE` 不可用 → 全量 `pg_dump -Fc`（1.4 MB，库体积 36 MB）+ `pg_restore` 克隆出 `sparkle_debris_rehearsal`（263 表含 alembic_version，tasks 38 列，与源一致）。

| 验证项 | 结果 |
|---|---|
| dry-run 识别 | 32/32 项，拒删 0；行数合计 588（29 张遗留表全空 + tasks 196 行×3 列），磁盘估算 ≈2.0 MiB（克隆库 1.5 MiB） |
| `--apply`（演练库） | DROP TABLE ×29 + DROP COLUMN ×3，拒删/失败 0，后置校验全过，exit 0 |
| 删除集精确性 | sparkle−rehearsal 表差集 == 白名单 29 张（True）；列差集恰为 `tasks` 三列（True）；演练库无多出的表/列 |
| 表数收敛 | 262 → 233（= 迁移链表数，差值 29 吻合） |
| 主业务表完好 | users=54、tasks=196、cards=0 与源一致；chat_messages 112 vs 110 为 dev 库演练期间实时写入（新行 created_at 14:37 > dump 时刻），非 restore 丢失 |
| 幂等 | 二次 `--apply`：0 删除、全 SKIP、exit 0；三次 dry-run：`已缺席 32` |
| 收尾 | `DROP DATABASE sparkle_debris_rehearsal WITH (FORCE)` 已删；dev 库 `sparkle` 全程只读，表数 262 未变 |

## 四、真库执行（待运维，本次未做）

按纪律本次**未动 dev 库任何对象**。真库执行流程、核对清单与回滚（重建 dev 库）见
[docs/engineering/DB_DEBRIS_CLEANUP.md](../../../engineering/DB_DEBRIS_CLEANUP.md)。
同实例残库 `sparkle_rt02_probe`/`sparkle_repro_t42`/`sr8r2_ct8_mig`/`sr8r2_mig` 属独立
DATABASE，不在脚本范围，runbook 附录给出手动 DROP 命令，运维确认后处置。
