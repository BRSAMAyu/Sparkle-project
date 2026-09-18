# DB Debris 清理 Runbook（dev 库会话遗留表 + tasks 三列残留）

> 挂账来源：round2 schema 一致性审计（`main@b21dce46`，
> [schema-consistency-audit.md](../competition/2026-tmall-hackathon/系统审查/round2/schema-consistency-audit.md)
> §三 P1 / §四处置 3）。工具：`scripts/devtools/db_debris_cleanup.py`。

## 清什么

dev 库 `sparkle`（public schema）共 **32 项**，全部登记在脚本常量里（誊抄自
`orm_migration_audit.py` 白名单，基线 `main@b8f4e7d8`）：

| 类别 | 数量 | 判定 |
|---|---|---|
| DB-only 会话遗留整表 | 29 | 迁移链/ORM/网关三方均无创建来源，疑为历次审查/探针会话 create_all 或手建产物 |
| `tasks` 残留列 | 3（`scheduled_at`/`timezone`/`version`） | 迁移链从未在 tasks 上建过这三列（迁移链上 `scheduled_at` 仅存在于 `aurora_scheduled_wakes`，不同表），ORM/网关零引用 → **db-only，脚本删，无需 alembic 迁移** |

明确**不**由本脚本清（另行处置）：白名单里另外三列
`cards.archived_at`、`chat_messages.metadata`、`user_settings.accessibility_settings`
是**迁移链上的 MIG-only 死列**——删除必须走 alembic drop 迁移（审计移交清单第 1 条），
脚本删了会让下次 `alembic upgrade` 试图复活它们。17 张迁移-only 死表同理走 alembic 评估。

## 安全边界

- 脚本只能删常量 `DEBRIS_TABLES` / `DEBRIS_COLUMNS` 里明确列出的对象；清单外任何对象受结构性保护。
- 删除前检查入边依赖：白名单外表的 FK / 视图引用存在时**拒删该项**（防 `CASCADE` 波及主业务对象），退出码 1。
- `DROP COLUMN` 不带 CASCADE；`tasks` 表本身被断言禁止整表删除。
- 全部语句 `IF EXISTS` + 执行前后存在性校验 → **幂等**，重复执行无害。

## 何时跑

1. **先演练**（每次清单变更后必做；本 runbook 的演练已于 2026-09-18 执行通过，见
   [round2 报告](../competition/2026-tmall-hackathon/系统审查/round2/db-debris-cleanup.md)）：

   ```bash
   export PGPASSWORD=sparkle_dev_pg_2026
   # ① 全量克隆 dev 库（TEMPLATE 会被活动连接挡住，用 dump/restore）
   pg_dump -h localhost -U postgres -Fc -d sparkle -f /tmp/sparkle_rehearsal_src.dump
   psql -h localhost -U postgres -d postgres -c 'CREATE DATABASE sparkle_debris_rehearsal;'
   pg_restore -h localhost -U postgres -d sparkle_debris_rehearsal --no-owner /tmp/sparkle_rehearsal_src.dump
   # ② 演练库实删
   /opt/homebrew/bin/python3.11 scripts/devtools/db_debris_cleanup.py \
     --database-url "postgresql+psycopg://postgres:sparkle_dev_pg_2026@localhost:5432/sparkle_debris_rehearsal" \
     --apply --non-interactive
   # ③ 核对（见下节）④ 用后即删
   psql -h localhost -U postgres -d postgres -c 'DROP DATABASE sparkle_debris_rehearsal WITH (FORCE);'
   rm /tmp/sparkle_rehearsal_src.dump
   ```

2. **再动真库**（dev 空闲时段，建议先确认没有写密集会话）：

   ```bash
   # dry-run（默认，只读）：核对 32 项、行数、磁盘估算、拒删=0
   /opt/homebrew/bin/python3.11 scripts/devtools/db_debris_cleanup.py
   # 确认无误后实删（交互终端会要求输入目标库名确认）
   /opt/homebrew/bin/python3.11 scripts/devtools/db_debris_cleanup.py --apply
   ```

## 如何核对

- **删除集精确等于白名单**：`sparkle 表数 - 清理后表数 == 29`，且差集逐张对上
  `DEBRIS_TABLES`；`tasks` 列差集恰为三列（可复用 `orm_migration_audit.collect_db_columns`
  做前后对比）。
- **清理后表数收敛**：dev 库 public 基表应从 262 → **233**（= 迁移链表数，alembic_version 不计）。
- **主业务表完好**：抽查 `users`/`tasks` 等行数与清理前一致（演练基线：users=54、tasks=196）。
- **审计归零**：`/opt/homebrew/bin/python3.11 scripts/devtools/orm_migration_audit.py`
  仍应 exit 0（db-only 桶清空后，白名单相应条目可择机收缩——收紧白名单是独立小改动，不与本清理捆绑）。
- **幂等复核**：紧接着再跑一次脚本，应报 `现存待删 0 项（已缺席 32）`、exit 0。

## 回滚

本清理**无对象级回滚**（DROP 不可逆）。回滚 = 重建 dev 库（数据均为本地开发数据，可接受）：

```bash
export PGPASSWORD=sparkle_dev_pg_2026
psql -h localhost -U postgres -d postgres -c 'DROP DATABASE sparkle WITH (FORCE);'
psql -h localhost -U postgres -d postgres -c 'CREATE DATABASE sparkle;'
cd backend && alembic upgrade head            # 重建迁移链终态 schema（233 表）
cd .. && make sync-db                         # schema 快照导出 + SQLC 生成（例行对齐）
```

测试账号按需重建（`scripts/devtools/create_test_user.py` 等）。**不要**用
`scripts/devtools/force_sync_db.py` 重建——它是遗留 `create_all` 路径，正是本清理所
对抗的碎片来源。

误删预防优先于回滚：dry-run 输出里出现任何 `拒删` 标记即停下人工核查；`--apply` 前留一份
`pg_dump -Fc` 快照（36 MB 量级，成本极低）可作为最稳妥的还原点。

## 附：残库（独立于本脚本，运维手动处理）

同实例另有历史会话残库：`sparkle_rt02_probe`、`sparkle_repro_t42`、`sr8r2_ct8_mig`、`sr8r2_mig`。
属独立 DATABASE（非 sparkle 对象），确认无人使用后手动：

```bash
psql -h localhost -U postgres -d postgres -c 'DROP DATABASE sparkle_rt02_probe WITH (FORCE);'
# 其余同理；执行前 pg_dump -Fc 留档一次即可
```
