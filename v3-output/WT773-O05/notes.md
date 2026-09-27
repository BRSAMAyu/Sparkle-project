# WT773 · O-05 · Backup/Restore + Agent Run/Memory Consistency 演练 — notes

- **卡**：`v3/07_tasks/cards/O-05.md`（OPS / Gate V3-6 / Risk: critical / HEAVY / 2 reviewers）
- **基线 SHA**：`a7698ab60b2e04438b21c502fa94713967bc18d7`（main，2026-09-27 轮#262）
- **分支**：`agent/node-b/wt773/o05`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt773-o05`）
- **状态**：`READY_FOR_REVIEW`（GJ08 真 LLM 切片受环境阻塞，见 §7；非 LLM 一致性面与验收其余项全绿）
- **环境铁律遵守**：全程零触碰运行中栈（sparkle_db/sparkle_redis/sparkle_minio 仅 `docker inspect` 只读元数据一次用于缺陷佐证；未 exec、未读写其数据面）。演练全部在一次性资源上：docker network `wt773o05-net` + `wt773o05-{src,rst}-pg`（本地镜像 sparkle-cosmos-sparkle_db:latest，PG 16.15+AGE+pgvector）+ `wt773o05-redis` + `wt773o05-minio`，端口 15432/15433/16379/19000-19001，数据全合成（`drill/seed_source.sql`），用后即删（§9）。

## 1. 卡面验收对照

| 卡面验收 | 结果 |
|---|---|
| 恢复后 GJ03 通过 | ✅ 11/11 steps（`drill/gj03_steps.jsonl`，经网关 :18080→恢复栈） |
| 恢复后 GJ08 通过 | ⚠️ 4/6：非 LLM 面（memory readback/calibration/correction surface）全过；两个 `*_real_llm` chat 步 HTTP 200 但空文本——本环境无 `LLM_API_KEY`，引擎日志实录 `activating demo mode`（§7），不伪造 |
| run query 通过 | ✅ 登录 drill 用户 → GET /runs（列表含 3 个恢复 run）+ GET /runs/{id}（SUCCEEDED/terminal_reason=completed）+ GET /runs/{id}/transitions（4 条 append-only 链完整） |
| 无已删 memory 复活 | ✅ INV-5/INV-7：备份点墓碑行（archived/retracted）恢复后仍墓碑，可召回面计数=基线；负证（把墓碑清空的"复活"形状）被 INV-7 抓住（单测 `test_tombstone_resurrection_red`） |

## 2. 备份覆盖面核查（ archaeology + 实录）

既有资产：`scripts/backup_prod_data.sh`（PG dump + Redis RDB + MinIO tar + sha256sums + 7 天滚动清理）+ `scripts/install_backup_cron.sh`（宿主 crontab 03:15，D-DEPLOY-FIX G2）+ `scripts/restore_prod_data.sh`。

核查结论（HEAD 脚本，一次性栈实测）：

1. **PG**：`pg_dump` 无 `--clean --if-exists`——restore 进非空库为合并语义（见 §3 RED）。
2. **Redis**：backup `redis-cli --rdb` 走复制流，与持久化 dir 无关，OK；restore 写死 `/data/dump.rdb`——redis-stack-server 的 `CONFIG GET dir` 是 **/var/lib/redis-stack**（演练容器实测），写 /data 是无效恢复（V3-FIX-505，§4.3）。
3. **MinIO**：backup/restore 都依赖容器内 `tar`——生产镜像 `quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z` 无 tar（`docker exec sparkle_minio sh -c 'command -v tar'` → 无，只读佐证），backup 实跑 exit 127，`set -e` 使 sha256sums/manifest 从未产出（V3-FIX-504，§4.1）。
4. **config**：栈凭据只存部署 checkout 的 `.env`（`/Users/brsama/code/GitHub/sparkle-cosmos/.env`，仓库内只有 example）——备份包不含 config 时还原得出 schema 起不了栈。HEAD 脚本零 config 覆盖。
5. **manifest**：无 alembic 版本戳/PG 版本/耗时——恢复侧无法核对 schema 代差。

## 3. RED 实录（HEAD 脚本，一次性栈）

起点：rst-pg = 备份点 schema+种子，再叠加 staging 漂移（新增记忆行、硬删一行备份点既有记忆、run2 状态推进+追加迁移、outbox 发布一行+新增一行、processed_events 增一行）。

`bash scripts/restore_prod_data.sh`（HEAD）跑完：**exit=0、日志 2156 条 already-exists/duplicate-key SQL 错误被 psql 静默吞掉**。库面 frankenstate（`drill/red_restore_head.log`）：

| 检查 | 期望（快照语义） | 实测 |
|---|---|---|
| 漂移 ghost 行（备份后新增记忆） | 0 | **1（残留）** |
| 备份后硬删的行 | 1（PITR 找回） | **0** |
| run2 状态被备份后推进为 COMPLETED | 回 EXECUTING（演练种子时代） | **COMPLETED（残留）** |
| 漂移迁移/漂移 outbox/漂移 processed_events | 全 0 | **全残留** |
| MinIO 数据面 | 随包恢复 | **静默跳过（包里就没有 tar——backup 已死在 exit 127）** |

即：非空库恢复 = 假成功 + 混合态；"无已删 memory 复活"在合并语义下无保证。

## 4. 缺陷登记与修复（卡面范围内红→绿）

### V3-FIX-504（已修，本分支）
backup/restore 脚本三缺陷：① `pg_dump` 缺 `--clean --if-exists` → 非空库合并恢复产出假成功混合态（§3，2156 错误/exit 0）；② MinIO 归档依赖容器内 tar，生产镜像无 tar → **cron 每晚备份实际产不出完整包**（exit 127，sha256sums/manifest 未产出，实测佐证 + 修复后 backup 全链 5-7s 产齐）；③ config 覆盖面缺失 + manifest 无 alembic/PG 版本戳。修法：dump 加 `--clean --if-exists`（重放即删后建 = 精确快照，空库路径同样可重放）；MinIO 改 `docker cp` 拷出→宿主机 tar（容器无关，产物名不变）；`.env` 随包（chmod 600，实测 `drill/backup_manifest.json` `config_files`）；manifest 加 `alembic_head`/`postgres_server_version_num`/`backup_duration_seconds`。

### V3-FIX-505（脚本面已修；compose 侧残差保持 OPEN）
redis-stack-server 持久化 dir 是 `/var/lib/redis-stack` 而非 `/data`（演练容器 `CONFIG GET dir` 实测）：restore 写 `/data/dump.rdb` 重启后零加载（`keys loaded: 0` 实录）——**静默无效恢复**。已修：restore 按 `CONFIG GET dir` 动态落盘（实录修复后 `keys loaded: 2`、marker/stream 逐字节核对通过）。**OPEN 残差（超出本卡脚本面）**：docker-compose 挂载卷是 `sparkle_redis_data:/data`，而服务器 RDB 写 `/var/lib/redis-stack`（未挂载）——prod 容器重建即 Redis 全损、容器重启依赖 shutdown-save 兜底；需 compose/启动参数面裁决（`--dir /data` 或改挂载），交 ops 卡处置。

### 交付物
- `scripts/backup_prod_data.sh`（修）/ `scripts/restore_prod_data.sh`（重写）
- `scripts/restore_consistency_check.py`（新，§5）
- `scripts/tests/test_o05_restore_consistency.py`（新，14 用例）

## 5. Agent Run/Memory 一致性不变量表（设计 + 执行结果）

校验器：`scripts/restore_consistency_check.py`（SQLAlchemy sync engine，PG/sqlite 双方言；run 词表从冻结真源 `app.core.run_state_machine` 导入，脱离 checkout 退化副本且有单测对账）。用法：备份点对源库 `--capture-baseline baseline.json`；恢复后 `--baseline baseline.json [--report r.json]`；非零退出=违例。

| # | 不变量 | 判据 | 演练结果（恢复栈） | 单测红证 |
|---|---|---|---|---|
| INV-1 | run 状态封闭词表+终态归因+活性戳 | status∈RunStatus；终态必有 terminal_reason∈词表；heartbeat_at 非空 | PASS（词表源=冻结真源，3 run） | `test_illegal_status_vocabulary_red` / `test_terminal_without_reason_red` |
| INV-2 | run 脊柱投影一致（append-only 末条迁移==状态行） | 每 run 最后一条 agent_run_transitions.to_status == agent_runs.status | PASS（SUCCEEDED 链 4 条完整） | `test_status_projection_drift_red`（备份后推进残留形状） |
| INV-3 | 每 intent 活跃 run 唯一 | 非终态 run 不共享 intent_id（x05 部分唯一索引的应用层镜像） | PASS | `test_active_run_duplication_red` |
| INV-4 | outbox 序列计数器不回填 | `event_sequence_counters.next_sequence >= max(event_outbox.sequence_number)`（口径对齐 `_next_sequence` upsert：行值=最近已分配序号，==max_seq 是稳态） | PASS（6 计数器，含 GJ 流量新写聚合） | `test_counter_rollback_red` / `test_counter_steady_state_equal_passes` |
| INV-5 | memory 墓碑完整 | 可召回面（三墓碑全空）计数≤总数；墓碑分布 | PASS（total=4 recallable=2 archived=1 retracted=1） | （公式破裂分支在 `test_tombstone_resurrection_red` 经 INV-7 覆盖） |
| INV-6 | 引用完整性零孤儿 | agent_runs/episodic_memories/memory_preferences→users、transitions→agent_runs | PASS（4/4 项） | `test_orphan_transitions_red` |
| INV-7 | 快照等价（带基线） | 7 关键表行数 + run 状态分布 + episodic 可召回数 + outbox 发布/总数 + processed_events 数 == 备份点 | PASS（12 项比对；恢复后 GJ 流量写入后同基线复检转 FAIL——灵敏度实录，属正确行为） | `test_ghost_rows_red`（合并恢复 ghost 形状）/ `test_tombstone_resurrection_red` |

## 6. GREEN 实录 + RPO/RTO

环境：一次性四容器栈；源库 251 表（alembic head `wt598_20260927` 全量迁移）+ 合成种子；rst-pg 叠加 §3 同款漂移后跑修复版 restore（`drill/green_restore_final.log`）。

| 项 | 实测 |
|---|---|
| backup（PG+Redis+MinIO+checksum+manifest） | **5-7s**（100KB PG dump/351B RDB/13.7KB MinIO tar，MB 级量级） |
| restore（PG clean 重放 + Redis CONFIG-dir 落盘重启 + MinIO 精确交换） | **6s** |
| 快照等价（INV-7 全 12 项） | PASS：ghost 行清零、备份后硬删行 PITR 找回、run 状态/迁移回滚到备份点、outbox 发布态冻结（已发布不重播/未发布保持待发布）、processed_events 回备份点 |
| MinIO 精确交换负证 | 备份后植入 obj3-drift.txt → restore 后消失；对象内容经 S3 API（mc cat）逐字节核对 |
| Redis 恢复负证 | 修复前 `keys loaded: 0`（写 /data 无效）→ 修复后 `keys loaded: 2`，GET marker/XLEN 逐值核对 |
| 恢复栈真实服务能力 | uvicorn :18000 + Go gateway :18080（worktree 构建，一次跑通）对恢复栈起服务；GJ03 全真链路 11/11 |

**RPO/RTO 判读**（如实）：本实测 = 备份/恢复**操作时长**（RPO 捕获耗时、RTO 的数据面分量）。端到端 RPO 由 cron 周期决定：`install_backup_cron.sh` 默认 03:15 每日 → **最坏数据丢失窗 24h**（卡令如实记录，收紧需改调度，属 ops 裁决）。端到端 RTO 还需叠加容器拉起 + 恢复栈起服务（本演练网关+引擎起服务约 1 分钟内）+ schema 代差迁移时间（manifest alembic 戳 + STRICT_SCHEMA=1 可门）。另：MinIO backup 为运行中服务的尽力一致快照（demo 量级 MB 级 + 低峰 cron）；强一致窗口需停写或卷快照，已注释在脚本。

## 7. GJ03 / GJ08 / run query 实录

- **GJ03**（无 LLM 依赖）：`PASS 11/11`——fresh guest→upgrade→task→today→command path（proposal→approve）→complete+outcome→growth→task truth，全链经网关打到恢复栈。证据 `drill/gj03_steps.jsonl`。
- **GJ08**：`4/6`。PASS：fresh_user / memory_readback / calibration_cards_read / aurora_correction_surface。FAIL：`establish_context_real_llm`、`next_session_real_llm`——HTTP 200 但 `"text": ""`（引擎日志：`LLM API key not configured, activating demo mode` + `api_key is empty for base_url=https://open.bigmodel.cn/...`）。本机与运行时 checkout 的 .env 均无 LLM key（键名枚举核实，未读值），按"无凭据不伪造"如实登记为环境阻塞切片；纠正→下轮适配机制面另有 wt388 A-06 17 用例变异红证钉（GJ08 driver notes 自带口径）。
- **run query**：login（真 bcrypt）→ GET /runs 列表、GET /runs/{id}、GET /runs/{id}/transitions 三面 200 且内容与恢复快照一致。

## 8. 验证门

- 单测：`backend/.venv/bin/python -m unittest scripts.tests.test_o05_restore_consistency` → **14/14 OK**（红绿双路径 + 脚本契约钉 + 词表副本对账）。
- mypy：新文件 `--ignore-missing-imports` → **0 error**；全库棘轮 `scripts/ci/mypy_ratchet.sh` → 见 §10（后台实录）。
- ruff / black(120)：两文件全过。
- dry-run 实录：本文 §3/§6 + `drill/` 目录（red/green 日志、checker JSON、GJ jsonl、backup manifest、seed SQL 全部入库）。

## 9. 一次性资源清单（收尾删除）

`wt773o05-net`、`wt773o05-src-pg`、`wt773o05-rst-pg`、`wt773o05-redis`、`wt773o05-minio`；宿主临时 `/tmp/wt773-o05/`。worktree 内生成物 `backend/app/gen`、`backend/gateway/gen` 均为 gitignored，不入库。运行中生产栈零接触。

## 10. 残差与交接

1. V3-FIX-505 OPEN 残差：prod redis 卷挂载与持久化 dir 错位（§4）——ops 卡处置，本卡只修了 restore 侧。
2. RPO 24h 由 cron 周期决定；异地化（mc mirror 到对象存储）在 `install_backup_cron.sh` 头注已登记待办。
3. GJ08 真 LLM 切片：有 key 环境重跑 `--gj GJ08` 即可补证据（栈与剧本就绪）。
4. 校验器 INV-7 在恢复后有真实写入会按设计转 FAIL（基线过时）；灾后门禁应先跑无基线结构检查（INV-1..6），业务核数通过后再跑带基线比对。
