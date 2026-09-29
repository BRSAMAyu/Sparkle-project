# V4-FIX-582 第一相诊断 — Q04 揭案运行栈事故三联（只读取证 + 根因 + 修复计划）

- 执行：FIX-582 fleet 修复 agent（worktree `wtF582`，分支 `agent/v4/f582`，基点 155aceec）
- 日期：2026-09-29（本机本地 UTC+8；DB 时钟 Etc/UTC 12:09 UTC 时点采样；fleet notes 走自有日钟 2026-09-30 序）
- 本相边界：**零写零 restart 零清理**——对运行栈仅 `docker inspect` / `docker exec psql SELECT` / `redis-cli TYPE|LLEN|LRANGE|PING` / `curl health` / 配置指纹比对。Q01 留下的 hybrid 僵尸 run 与僵尸事务属 FIX-583 活证据，只读记录未触碰。
- 密钥纪律：全部凭据以「长度 + sha256 前 12 位指纹」呈现，零回显零落盘。

---

## 0. 核心结论（先读这个）

1. **三联主面已被 FIX-571（P1）修复并闭账**（台账 :449 `FIXED@6110b6a5`，2026-09-29 09:03–09:40 +0800 执行窗口，证据 `v4/evidence/FIX-571/`）。本卡独立复测逐项证实其修复在当前栈上**仍然成立**（§1）。
2. **FIX-582 是对 FIX-571 的重复登记**：Q08 scout（fleet 钟序 30:20）聚合 Q04 limitations §2（09-28 时点的静态证据文档）时，未对台账 FIX-571 行（已 FIXED）与 fleet notes 04:30 闭账笔做查重，把已修复事故再次立卡。时间线见 §2.4。
3. 残余风险面 5 项（§4）：legacy service roles 未落地、双 superuser 身份与 .env 轮换脆弱模式、DLQ 1 条 FK 留档、驻留栈跑在已删除的 wtQ01 cwd（F583 协调面）、台账查重流程缺口。全部**可热修或登记即可，无需停栈窗口**。
4. **Q08 影响重估**：scout R1 所述「LIVE_STACK 面全撞墙」已不成立——PG host 侧鉴权双路通、计费流动、死信清零（1 条留档）。Q08 真正的 LIVE_STACK 阻塞项只剩 **F583 hybrid 挂死（正在实时复现）** 与 M18 unattributed 历史占比（不可逆，如实报）。建议 leader 对 Q08 相关格解除「因 F582 BLOCKED」的预登记。

---

## 1. 三联逐联取证（本卡独立实测，2026-09-29）

### 1.1 联① 共享 PG 鉴权 — 现状：**已修复（571），双路 AUTH_OK**

**拓扑事实**：运行容器 sparkle_db 属 compose project `sparkle-cosmos`（workdir `/Users/brsama/code/GitHub/sparkle-cosmos`，FIX-557 数据面属主），启动于 2026-09-29T07:31:16Z（healthy）。数据卷 `sparkle-cosmos_sparkle_postgres_data` CreatedAt=**2026-09-17T04:03:40Z**（.env 最后写入 09-17 11:33 +0800 ≈ 03:33 UTC，**卷在轮换后 30 分钟重建**，initdb 烘入的即轮换后密码；数据连续性佐证：token_usage 最老行 09-18，users 覆盖 09-16 起）。

**pg_hba.conf**（卷内实测）：local/127.0.0.1/::1 = trust；`host all all all scram-sha-256`——宿主经发布端口来访（docker 网桥来路）必走 scram，与「host 侧损坏」的观察面一致。

**role 面（pg_authid 实测）**：

| role | rolcanlogin | rolsuper | 密码 | 本卡实测 host 侧鉴权 |
|---|---|---|---|---|
| postgres | t | t | SCRAM(133) | 容器 env 密码 → **AUTH_OK** |
| brsama | t | t | SCRAM(133) | Sparkle-project 两 .env 密码 → **AUTH_OK** |
| sparkle_gateway | t | f | SCRAM(133) | 容器 env 密码 → **FATAL 28P01 password authentication failed**（孤儿密码，无任何现行 .env 与之匹配） |
| sparkle_engine | t | f | **NULL** | 任何密码均不可登录（设计残缺，见 §4 R-1） |
| sparkle_celery | t | f | **NULL** | 同上 |
| sparkle_readonly | t | f | **NULL** | 同上 |

**凭据指纹**：容器 env `POSTGRES_PASSWORD` len=19 sha256:`3601f490715a` ＝ cosmos 仓 `.env` 同键指纹 ＝ 卷内 postgres role 现行 hash（AUTH_OK 实证）。`POSTGRES_USER=postgres`，`POSTGRES_DB=sparkle`。

**与 Q04 记录的差异定性**：Q04（09-28）所见「容器 env 与卷内 hash 不匹配、host 侧 scram 全部失败、token_usage 停在 09-28 09:18」对应的是**当时在跑的旧容器实例**（env 烘于轮换前，卷 hash 已是轮换后值）。09-29 07:28–07:31 三容器被同一轮 compose 动作重建，env 重读对齐，superuser 路径自愈；571 又以 SQL 层 `ALTER ROLE postgres`+`CREATE ROLE brsama` 把两条应用身份正式接通（其 run_manifest §2 实录）。本卡复测与 571 落账完全一致。

### 1.2 联② 计费死信 — 现状：**已修复（571），队列空、消费健康、1 条 FK 留档**

| 项 | 实测（2026-09-29 12:0x UTC） |
|---|---|
| `queue:billing` | TYPE=none（空，BLPOP 正常等待态） |
| `queue:billing:dead_letter` | TYPE=list，**LLEN=1**（571 时点为 230） |
| 残留条目 | request_id `cb6aac13-55e1-405a-90f7-4fcf068c5d7d`，model=`no_generation_model`，0 token；error=**ForeignKeyViolationError** `token_usage_user_id_fkey`（user `515fc368…` 不在 users 表）；failed_at=2026-09-29T01:23:27Z。571 manifest 判「不可解留档留队」，与本卡复测一致——该 user 行缺失是请求事务回滚（F583 hybrid 挂死族）的下游症状 |
| `token_usage` | 1471 行；最老 09-18；**最新 2026-09-29 11:56:55 UTC（采样前 ~13 分钟）——计费持续流动**；09-28 全天 558 行（Q04 自起栈与其恢复批的写入） |
| 探针落库 | users 中 `fix571-%` 2 行（571 的 guest auth 探针真实落库佐证） |
| 152 行历史丢失 | 不可逆（571 闭账定谳：流内 usage 帧 + Q04 58 行直插恢复批已补偿；M18 unattributed 占比面为永久性历史事实） |

**残留条目的因果归属**：FK 违约不是凭据问题，而是「billing 记录独立入队 vs user 行随请求事务回滚」的结构性竞态（F583 挂死放大其发生概率）。死信机制本身工作正常（重试 3 次→转死信），无需修复机制。

### 1.3 联③ 凭据漂移 — 现状：**REDIS/MINIO 四方一致；POSTGRES 为「双 superuser 身份」格局**

四方凭据指纹表（`/Users/brsama/code/GitHub/` 下）：

| 凭据 | cosmos `.env` (09-17) | cosmos `backend/.env` (09-17) | Sparkle-project `backend/.env` (09-24) | Sparkle-project `gateway/.env` (09-29 09:20) | 容器 env 实测 |
|---|---|---|---|---|---|
| POSTGRES_USER | postgres | postgres | **brsama** | **brsama** | postgres |
| POSTGRES_PASSWORD | 19c `3601f490715a` | 同左 | **9c `e2186dbdb1bb`** | 同左 | 19c `3601f490715a` |
| REDIS_PASSWORD | 22c `958412cb07ed` | 同左 | 同左 | 同左 | requirepass 同指纹（PONG） |
| MINIO_ROOT_PASSWORD/SECRET_KEY | 22c `bd2bb4a80661` | — | 同左 | 同左（无 ROOT 键） | `bd2bb4a80661` |
| MINIO_ROOT_USER/ACCESS_KEY | sparkle_minio / 13c `17bba33c9806` | — | 同左 | 同左 | sparkle_minio |
| POSTGRES_HOST | sparkle_db | sparkle_db | sparkle_db | **127.0.0.1** | — |

- REDIS/MINIO：四方与容器 env **全一致**（571 manifest §3 实录了 gateway/.env 的 REDIS WRONGPASS 与 MINIO Access Key 不存在两次失败，均在 09-29 09:20 运行时对齐——该文件 mtime 与其对齐时刻吻合）。**漂移已消除**。
- POSTGRES：不是「漂移未修」，而是**两套身份并存且均为 SUPERUSER**：cosmos 面=postgres（容器 env 同源），Sparkle-project 面=brsama（571 补建，superuser）。两路都通（§1.1）。
- PG 连接实况：`pg_stat_activity` datname=sparkle 共 47 连接 **全部 usename=postgres**（驻留栈全组件走 cosmos 面）。brsama 身份现无活跃消费者（gateway 现用启动环境覆盖）。sparkle_gateway role（c17 迁移的最小权限设计）无任何使用方。

### 1.4 F583 活证据只读记录（未触碰）

- `pg_stat_activity`：**6 对**「`idle in transaction`（document_chunks SELECT，事务龄 10m–2h05m）+ 同族 `active` Lock 等待（agent_runs SELECT）」——hybrid start 扇出在请求事务内挂死的实时形态，**且新对仍在以 ~10–20 分钟节奏新增**（采样窗内最新一对事务龄仅 10 分钟）。
- `agent_runs` 非终结行：09-25 11 行（QUEUED/RUNNING，4 天陈旧）+ 09-29 当日 4 行 RUNNING（10:04/10:14/10:41/11:26 UTC）。
- 驻留四进程（uvicorn :8000 / grpc :50051 / gateway :8080 / celery）cwd 均= `/Users/brsama/code/GitHub/wtQ01/backend(±gateway)`，lstart 2026-09-29 15:57–16:01 +0800；**wtQ01 worktree 已被裁撤**（`git worktree list` 5 棵无 Q01；目录已不存在，进程持已删 cwd 运行）——fleet note 33:30「Q01 栈四进程保持（供 R1 复测）」的延续，571 所重启的 main 驻留栈已被 Q01 栈有意取代。处置权归 F583/协调窗口，本卡不碰。

---

## 2. 根因因果链（何时引入 / 为什么没被发现）

### 2.1 联① 鉴权损坏

```
09-17 11:33 (+0800)  cosmos .env 轮换 POSTGRES_PASSWORD
09-17 12:03          数据卷重建（initdb 烘入新值）——hash 已是「新」
      （在跑的旧容器 env 烘于轮换前 → env=旧值 vs 卷=新值，host 侧 scram 全败）
09-28 09:55          驻留栈（坏凭据）起 → Q04 实测留证「鉴权损坏」
09-29 07:28–07:31    三容器被 compose 重建 → env 重读=新值，superuser 路径自愈
09-29 09:03–09:40    FIX-571：ALTER ROLE postgres 对齐 env + CREATE ROLE brsama 对齐本仓 .env
```

**引入机制**：`POSTGRES_PASSWORD` 只在 initdb 时生效、容器 env 只在容器创建时烘入——「轮换 .env」与「数据面」之间没有强制同步点，卷 09-17 重建后反而把不匹配固定成「env 陈旧 vs 卷新」形态。**未被发现的原因**：驻留进程连容器内 socket（trust 路径）不受影响，只有 host 侧（scram）路径暴露； fleet 日常心跳只查容器 healthy（healthcheck 走容器内 pg_isready trust），不探 host 侧鉴权。

### 2.2 联② 计费死信

09-28 驻留 worker 持坏凭据（flush 失败）+ Q04 自起栈 worker 同抢 `queue:billing` → 消费竞争：152 行计量被吞、RPUSH 恢复不收敛、驻留栈计费全进死信（571 清点时 230 条目/94 唯一，其中 229 条 error=password authentication failed for user "postgres"——坏凭据 worker 所致的铁证）。**未被发现的原因**：死信无告警面；计量「丢失」在流内 usage 帧口径下不可见，直到 Q04 主动做计费完整性对账才揭出。修复：571 停旧栈→单消费方→先验证消费→回放归档。

### 2.3 联③ 凭据漂移

三方 .env（cosmos 根/backend、Sparkle-project backend/gateway）在 09-17 轮换时未做联动对齐，gateway 侧 REDIS/MINIO 维持旧值；571 修复栈启动时以 WRONGPASS/Access Key 错误暴露并运行时对齐。**结构性残留**：POSTGRES 双身份（见 §4 R-2）。

### 2.4 F582 重复登记的流程根因

```
09-29 18:25  Q04 验收揪出三联 → 立卡 FIX-571（P1）
09-30 02:05  FIX-571 派单（fleet 钟序）
09-30 04:30  FIX-571 闭账 FIXED@6110b6a5（台账 :449）
09-30 30:20  Q08 scout 聚合：读 V4-Q04/limitations §2（09-28 静态证据）→ 登记 FIX-582 OPEN
```

scout 的证据源是**证据文档而非台账行**：Q04 limitations §2 至今仍以现在时描述三联（文档未随 571 回写「已修复」注记），scout 又未对台账做同因查重 → 重复立卡。**这同时解释了为什么「Q04 揭案至今无派修卡」的印象错误**——派修卡一直存在（571），且已完成。

---

## 3. 修复计划（第二相候选——本轮不执行，等 leader 排窗口）

| # | 残余面 | 修法 | 风险 | 回滚单位 | 窗口 |
|---|---|---|---|---|---|
| R-1 | **legacy service roles 未落地**（sparkle_engine/celery/readonly 无密码不可登录；sparkle_gateway 孤儿密码；c17 迁移的最小权限设计落空，全栈 superuser 直连） | 方案 A（建议）：SQL 层 `DROP ROLE` 三无密码 role + sparkle_gateway 处置（改密对齐或文档化废弃）+ 把「最小权限服务 role」登记为已知债。方案 B：补密启用 + 服务迁移——大动线，收益低 | A：近零（三 role 无连接、无对象归属，drop 前查 `pg_stat_activity`/`pg_depend` 复核）。B：服务批量改配置，回归面大 | 单 role（SQL 可逆重建成对） | 可热修（在线 SQL，无需停栈）；若选 B，并入 F583 后的重启窗口 |
| R-2 | **双 superuser 身份 + .env 轮换脆弱模式**（同 §2.1 机制可复发；brsama/postgres 双 superuser 亦越权面） | ①只读「env↔卷 hash 漂移探针」进守卫（心跳或 `scripts/run_all_rule_guards.sh`：指纹比对，零密钥回显）；②文档登记双身份格局与「轮换 .env 必须同步 ALTER ROLE 或重建卷」操作对；③收敛单身份留作债（须 leader 裁决，涉及两仓 .env 属主） | 探针只读零风险；身份收敛触及两仓凭据面，超出本卡 | 探针单文件 | 可热修 |
| R-3 | **DLQ 1 条 FK 留档**（cb6aac13，永久不可插入） + M18 unattributed 历史占比 | 维持 571 裁决「留档留队」（本卡已存快照 `raw/dlq_snapshot_20260929.jsonl`）；可选：改键 `queue:billing:dead_letter:archive` 归位；M18 面如实报不修 | 近零 | 单条目 LPUSH/LREM | 可热修；不做亦可 |
| R-4 | **驻留栈跑在已删 wtQ01 cwd**（四进程持已删目录运行；571 所启 main 栈已被取代） | **本卡不处置**——是 F583 R1 复测的保留栈（fleet note 33:30 明令保持）；随 F583 修复后由其重启面收口 | 若误重启=毁 F583 审查链（红线） | — | F583 协调窗口 |
| R-5 | **台账查重流程缺口**（本次重复登记的流程根因） | 派单/立卡前对台账同因行 grep 查重义务写入接力机制或 scout 模板；Q04 limitations §2 追加「已由 571 修复」回写注记（文档勘误，随本卡或 leader 指派） | 零 | 文档单点 | 可热修 |

**窗口需求总结**：三联主面**无需任何窗口**（已修复）；残余面除 R-1 方案 B 外全部可热修、可由任意空槽小卡消化；与 F583 的唯一协调点是「不要动驻留四进程」与（若选 R-1B）合并重启窗口。

### Q08 LIVE_STACK 面影响重估

| scout R1 原判 | 本卡重估 |
|---|---|
| 共享 PG host 侧鉴权损坏 → 撞墙 | **解除**：双路 AUTH_OK（§1.1） |
| 计费死信 → M18 计费完整性复验难看 | **部分解除**：队列空、消费健康；仅 152 行历史 unattributed 占比为永久事实，如实报即可 |
| 凭据漂移 → 栈自起隔离端口模式 | **解除**：REDIS/MINIO 四方一致；自起隔离模式可保留为稳健实践 |
| （scout 未列） | **真阻塞项=F583**：hybrid 挂死实时复现中（§1.4），LIVE_STACK 的 hybrid/回执腿在其修复前不可测 |

---

## 4. 证据绑定

- 命令面：`docker inspect`（容器 env/labels/volume CreatedAt）、`docker exec sparkle_db psql -U postgres`（pg_hba/pg_authid/pg_stat_activity/token_usage/users 只读 SELECT、双 role 登录实测）、`redis-cli TYPE/LLEN/LRANGE/PING/DBSIZE`、`curl /minio/health/live`、`ps/lsof`（进程 cwd/lstart）、`git worktree list`、两仓 .env 指纹脚本。全程零写零重启零清理。
- 产物：`raw/dlq_snapshot_20260929.jsonl`（DLQ 全量 1 条快照，计费元数据，无凭据）。
- 关联证据：`v4/evidence/FIX-571/{run_manifest.md,summary.md,dead_letter_archive_230.jsonl}`；`v4/evidence/V4-Q04/limitations.md` §2；台账 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` :449（FIX-571）/ :465（FIX-582）；fleet notes [2026-09-30 02:05/04:30/30:20/33:30]。
