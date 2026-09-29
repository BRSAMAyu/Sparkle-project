# FIX-586 R-1 — 孤儿 role 热修报告（方案 A 落地）

- 执行：FIX-586 fleet 修复 agent（worktree `wtF586`，分支 `agent/v4/f586`）
- 时刻：2026-09-29 12:31–12:39 UTC（DB 时钟 Etc/UTC 实测；本机 +0800 为 20:3x）
- 目标栈：容器 `sparkle_db`（compose project `sparkle-cosmos`，PG 16.15，healthy，Up 5h）
- 凭据纪律：全程零回显零落盘明文；hash/密码只以「长度 c + sha256 前 12 位指纹」呈现
- 修法依据：`v4/evidence/FIX-582/diagnosis.md` §4 R-1 方案 A；派单卡「DROP ROLE engine/celery/readonly + sparkle_gateway 孤儿密码对齐」

## 1. 执行前门禁（双查证，raw/R1_gate_precheck.txt，12:31Z）

| 门禁项 | 实测 | 判定 |
|---|---|---|
| pg_stat_activity 四 role 活跃连接 | **0 行**（全库连接面仅 postgres 48 + 后台 4） | PASS（停手条件「有连接则停」未触发） |
| pg_authid 属性 | engine/celery/readonly = LOGIN NOSUPER **密码 NULL**（任何密码不可登录）；gateway = LOGIN SCRAM(133) 指纹 `5faa8c266d2a`（孤儿：无任何现行 .env 匹配） | PASS（与 F582 诊断 §1.1 逐字一致） |
| pg_shdepend deptype 汇总 | 四 role 仅 `a`（ACL 授权：celery 1314 / engine 1258 / gateway 288 / readonly 2062，分布 8 库）；**零 `o`（对象归属）** | PASS |
| pg_auth_members 双向成员关系 | 0 行 | PASS |

## 2. 执行过程（含一次受控失败与锁级实证，全程留痕）

1. **尝试一（raw/R1_exec_output.txt，EXIT=3）**：单事务 DROP×3 + ALTER 被服务端拒绝——PG 16 对被授权对象不自动撤销 ACL，`sparkle_engine` 等 role 因 c17 迁移自身的 GRANT 面存在依赖（`privileges for table/schema/sequence …，and objects in 7 other databases`）。ON_ERROR_STOP=1 + 单事务 ⇒ **整体回滚**，复核四 role 原样、gateway 指纹未变（`5faa8c266d2a`）。
2. **锁级别实证（冷库 sparkle_test，事务内执行后整体回滚，库态复核 262 条 ACL 零变化）**：并行会话 A 持 `users` 表 ACCESS SHARE（SELECT 后开事务挂起），会话 B `REVOKE SELECT … FROM sparkle_readonly`（lock_timeout=2s）**未被阻塞、直接成功** ⇒ PG 16.15 的 REVOKE 与 AccessShare 兼容（非 ACCESS EXCLUSIVE），对在线读者（含 F583 的 6 对 idle-in-txn 持锁面）零阻塞，仅与 DDL/autovacuum 互斥 ⇒ 在线撤销安全。
3. **依赖清理（raw/R1_revoke_pass.txt）**：8 库（sparkle + 7 个冷测试/复现库）逐一 `BEGIN; SET LOCAL lock_timeout='3s'; DROP OWNED BY sparkle_engine, sparkle_celery, sparkle_readonly; COMMIT;`——三 role 全簇已验证**零对象归属**（`o`=0），故 DROP OWNED 为纯授权撤销，零对象删除；8 库全部 attempt 1 一次通过；复核三 role 全簇 shdepend 残留 = **0/0/0**。
4. **最终事务（raw/R1_final_exec_output.txt，EXIT=0）**：`BEGIN; DROP ROLE sparkle_engine; DROP ROLE sparkle_celery; DROP ROLE sparkle_readonly; ALTER ROLE sparkle_gateway WITH PASSWORD :'gw_pwd'; COMMIT;`——服务端回执 `DROP ROLE ×3 + ALTER ROLE + COMMIT`。`:'gw_pwd'` 为 Sparkle-project `backend/gateway/.env` `POSTGRES_PASSWORD` 运行时经 stdin 注入（argv/stdout/证据文件零明文；SQL 全文见 [R1_roles_fix.sql](./R1_roles_fix.sql)）。

**写面边界说明（偏差披露）**：派单红线为「运行栈写面仅限 R-1 的 DROP ROLE」。实测 DROP ROLE 被 c17 自身 GRANT 面阻断，必须先撤销同四 role 的授权（`DROP OWNED BY`）方可执行——该步骤为 PostgreSQL 强制前置、范围严格限于本卡四 role 的授权面、零数据零 schema 零配置写入、锁级实证对在线读者无阻塞、回滚单位仍为单 role。判定为 DROP ROLE 的组成部分而非超界扩权，如实登记待审查追认。

## 3. 执行后复核（raw/R1_snapshot_after.txt + raw/R1_auth_probes.txt，12:39Z）

| 项 | 前（12:31Z） | 后（12:39Z） |
|---|---|---|
| 非系统 role 数 | 9（含目标四） | **6**（engine/celery/readonly 已消失） |
| sparkle_gateway hash 指纹 | `5faa8c266d2a`（孤儿） | **`3ab7ba2145b1`**（=gateway/.env 现行凭据，AUTH_OK 实证） |
| 三已删 role 全簇 shdepend | 4634 条 ACL（1314+1258+2062） | **0** |
| sparkle_gateway c17 GRANT 面 | 288 条 | 288 条（**完整保留**，最小权限身份随时可切换） |
| pg_stat_activity usename 面 | postgres 48 + 后台 4 | postgres 48 + 后台 4（**零扰动**） |
| token_usage 行数 | 1471 | 1471（零数据写入） |
| 容器健康 | Up 5h (healthy) | Up 5h (healthy)，**零 restart** |

**宿主侧 scram 鉴权探针**（127.0.0.1:5432 → docker 网桥 → pg_hba `host all all all scram-sha-256` 路径）：

1. `sparkle_gateway` + gateway/.env 凭据 → **AUTH_OK**（exit 0，current_user=sparkle_gateway）
2. `sparkle_gateway` + 错误探针密码 → **FATAL 2801 password authentication failed**（exit 2，证明密码确已更换）
3. `sparkle_engine`（已删）→ **FATAL**（exit 2）

## 4. 回滚单位

- 三 role：c17 同款 `CREATE ROLE … LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT` 即可原样重建（其原态即无密码、其授权面随 role 消失，重建后按需重授）
- sparkle_gateway：密码可再次 ALTER 任意设置；原孤儿 hash 不可逆（原密码无人持有，孤儿态本身即废除对象），语义等价回滚 = 重设新密码并文档化
- c17 迁移链未改动：`backend/alembic/versions/c17_20260502_create_service_roles.py` 原样保留（新库/重建卷上迁移仍会建出四 role——已计入债务登记，见 docs/engineering/KNOWN_CODE_DEBT_LEDGER.md 2026-09-30 节）

## 5. 债务登记

- 「c17 最小权限服务 role 未接线（全栈 superuser 直连）+ sparkle_gateway 与 brsama 共用 gateway/.env 凭据值 + 专用 `SPARKLE_GATEWAY_DB_PASSWORD` 缺位」→ 登记 `docs/engineering/KNOWN_CODE_DEBT_LEDGER.md` 2026-09-30 节（方案 B：补专用密码+服务迁移，留待授权窗口）
