# OPS-QUIRKS — 三个登记运维疑点调查报告

> 卡：OPS-QUIRKS（生产运维线，C×D 纵队）｜worktree wt194｜2026-09-23
> 性质：纯研究零代码。全程只读：docker 仅 `inspect/logs/exec(psql SELECT、redis-cli CONFIG GET/INFO/SCAN/XINFO/TTL/TYPE/XLEN)`；未重启任何容器/进程；未写活库。
> 交付物：仅本文件。Redis 密码从主仓 `backend/.env` 读入 shell 变量用于只读认证，未落盘未外传、零凭据出现在本文。

---

## ① PG 容器 stdout 自 09-17 零日志（PROD-LOG「去向待查」）

### 实查证据

**日志配置（docker inspect，只读）**

- `sparkle_db` 日志驱动：`{"Type":"json-file","Config":{}}` —— **无任何轮转上限**（无 max-size/max-file）；三个 compose 文件（`docker-compose.yml` / `.prod.yml` / `.dev.yml`）中 `logging:` 键出现次数均为 **0**，即全部容器都在裸奔默认配置。
- 容器 Created `2026-09-17T04:03:40Z`，StartedAt `2026-09-20T16:05:33Z`（09-19 磁盘事故 exit 133 后的重启时间点，与 AGENTS.md 事故记录吻合）。

**PG 侧日志去向（容器内 SHOW，只读）**

```
logging_collector = off
log_destination   = stderr        → 全部日志走 stderr → docker json-file
log_directory     = log（collector 关闭时不生效；/var/lib/postgresql/data/log/ 不存在，实查确认）
log_min_duration_statement = -1   → 慢查询日志本来就关（PROD-LOG 感叹慢查询面缺失的另一原因）
log_checkpoints   = on（PG16 默认），checkpoint_timeout=5min → 理论上每 5 分钟必有一条日志
```

**判定日志"消失"的机制——json 日志文件被撕裂，且 docker logs 静默失败**。多个只读探针的原始输出：

| 探针 | 结果 |
|---|---|
| `docker logs --timestamps \| wc -l`（全程正读） | **957 行，全部 09-17 04:03→10:33:13 UTC**，CLI exit 0、stderr 无任何报错，**静默终止** |
| `docker logs --since 2026-09-18T00:00:00Z \| wc -l` | **0 行**（任何 ≥09-18 的 --since 窗口均 0） |
| `--tail 3 / --tail 8` | 正常返回 09-23 00:49~00:54 的 checkpoint 日志（尾部健康） |
| `--tail 200000`（第 1 次） | 142,342 行，起点 09-18 19:59:28，**终点停在 09-18 23:55:36**（当日错误风暴块），未到达 09-23 |
| `--tail 100000`（第 2 次） | 42,338 行，起点 09-18 20:05:03，越过 09-19/09-20 直到当下 |
| `--tail 50000`（第 3 次） | ~20.9k 行，起点 **09-19 13:15:53**（事故日 FATAL `password authentication failed for user "postgres"` 风暴），按日分布 09-19:7758 / 09-20:13131 / 09-22:1849 / 09-23:151（09-21 为零 → 当日栈未开机） |

三次大 `--tail` 得到**三个不同止点、互不一致的残片**，且全部 exit 0 无报错。结论：日志文件在 09-17→09-20（磁盘事故窗口）被撕裂成多个损坏区（ENOSPC 写失败/虚机崩溃留下的 torn record + 稀疏洞），docker 的日志读取器一旦碰到损坏记录就**无声停止**；文件不同区域在不同读法下时通时不通。**不存在任何"日志重定向到别处"**——collector off + stderr 直写，去向就是 docker json 文件本身，是文件坏了。

**PROD-LOG 的观察由此解释**：其"stdout 自 09-17 10:33 UTC 后零日志"正是从头部正读撞上第一个损坏点（09-17 10:33:13 恰是 09-17 开发日最后一行 `unexpected EOF on client connection`——收工断连时刻）。

**审计黑洞窗口**（经 docker logs 不可恢复）：约 `[09-17 10:33 → 09-18 19:59]` 与 `[09-18 23:55 → 09-20 16:05]`——后者**恰好覆盖磁盘事故本身**（MISCONF 风暴、exit 133 时刻），当时 PG 视角的完整过程永久缺失（仅有岛状残片，如上述 09-19 13:15 的认证失败风暴）。

**顺带取证（可读残片内的真实日志，各一条线即可）**：09-18 四小时窗口有 10,222 条 ERROR（其中 9,494 条 `current transaction is aborted`，chat_messages 去重 INSERT 模式，旧代码）；09-19 认证失败 FATAL 风暴；**至今仍在复发**的 `Role "sparkle" does not exist`（可读区 81 条，最近 09-23 00:32 UTC——某客户端硬编码 user=sparkle 连库，而 `.env` 的 `POSTGRES_USER=brsama`，疑 GUI 工具/旧 DSN）；以及残片尾部的 **现行错误**：09-22 21:13 UTC 多条 `INSERT INTO cards ... type "card_lifecycle_enum" does not exist`（有代码在活库上跑未迁移的 card 写路径，建议舰队核实是哪个 worktree/进程在打共享库）。

### 裁决

非重定向、非 collector、非轮转吞掉——**docker json 日志文件在 09-19 磁盘事故中被撕裂，docker logs 对损坏区的读取静默失败**。这是三个疑点里唯一"已发生且不可逆"的损失（审计黑洞），且暴露三个运维缺陷：损坏静默无告警、无轮转上限（慢性磁盘风险，09-18 错误风暴 4 小时写了 ~10MB，复发则旧病重演）、慢查询日志关闭。

### 最小修建议（S）

1. `docker-compose.yml` 给 `sparkle_db`（连带 redis/minio）加 `logging: {driver: json-file, options: {max-size: "50m", max-file: "5"}}`；
2. `docker compose up -d --force-recreate sparkle_db` 换新日志文件（数据卷不动，秒级窗口，建议合入窗口由主会话执行）；
3. 可选一行：db service command 加 `-c log_min_duration_statement=500`，打开 PROD-LOG 想要的慢查询面；
4. 验收：重建后 `docker logs --since <重建时刻> | tail` 可见启动横幅且 --since 全窗可用。

**不修的风险面**：审计/排障面持续缺失且**坏了不报错**（下次事故依旧盲飞）；无上限 json 日志在错误风暴复发时重演磁盘耗尽（本次事故的直接前科）；慢查询面持续为零。

---

## ② Redis AOF 关闭（PROD-LOG「生产评估开启」）

### 实查证据

**运行时配置（`CONFIG GET`，只读）**：`appendonly=no`（INFO: `aof_enabled:0`，`aof_rewrites:0`）；`save=3600 1/300 100/60 10000`（纯 RDB 默认档）；`maxmemory=536870912`（512MB）、`maxmemory-policy=volatile-lru`；`stop-writes-on-bgsave-error=yes`；`dir=/var/lib/redis-stack`。健康面：`rdb_last_bgsave_status:ok`，上次快照 09-23 08:52:58 CST（调查时 9 分钟前），`changes_since_last_save=29`，DBSIZE=4268，`used_memory=10.68M`（512MB 上限遥不可及）。

**配置漂移实锤**：仓库根 `redis.conf:11-16` 明确写着 `maxmemory 3gb / volatile-lru / appendonly yes / appendfsync everysec`——但 `docker-compose.yml:60` 的 `command: redis-stack-server --requirepass ... --maxmemory 512mb --maxmemory-policy volatile-lru` **完全覆盖了它**（无 appendonly 参数），且 redis service 的 volumes 只挂数据卷（`sparkle_redis_data:/data`）、**从未挂载 redis.conf**。即：**"开 AOF"的既定意图是死配置，从未生效过**。

**丢了会痛的键盘点（--scan 全量 4268 键 + 逐类 TTL/TYPE/长度抽样）**：

| 键类 | 量级 | TTL | 丢失痛感 |
|---|---|---|---|
| `idempotency:evt:sparkle_events:<id>`（事件幂等/去重锁） | 2509 | 有（样本 77619s≈21.6h） | 中：崩溃回滚→事件重放窗口；但**金额路径有 PG 侧兜底**（PHOTON-IDEM 首胜唯一索引+FOR UPDATE 行锁），不会双发钱 |
| `sparkle_events` 流本体 | XLEN=2153，多消费组，pending=0、lag=0 | 无 TTL（流） | 中：环形 maxlen=50000（`event_bus.py:986-994`），消费即时→未消费丢失窗口极小 |
| `lg_blob:*`（langgraph checkpoint）、`run_ledger:*`、`trace:*` | 数十/组 | lg_blob≈20.3h | 低：本就是带 TTL 的可丢中间态 |
| `predictive:next_intent`(299)/`user:prefs`(122)/`aurora:*`/`spine:*` 等缓存 | 千级 | 多有 TTL | 低：可重建 |
| 网关面（rate/session/token 等，REDIS_URL 同 /0 库） | 74 | 有 | 低-中：auth fail-closed 模式下重启窗口有瞬时 401（PROD-LOG ②-10 已记） |
| `community_events`(XLEN=4)/`cqrs:stream:*`(len=0) | 微 | 无 | 低 |

另：内存 10.68M/512MB，`volatile-lru` 下无 TTL 键（流类）不参与驱逐——当前量级无忧，生产定容需点名无 TTL 键类。

### 裁决

**参赛期：保持纯 RDB，不动。** 理由：(1) 写量极小（快照间变更仅 29），丢失窗口内损失≈0；(2) 唯一"丢不得"的金额路径已有 PG 侧恰一次兜底，Redis 丢数据最坏是事件重放/缓存重建；(3) 09-19 实证了磁盘压力+持久化失败=MISCONF 全局拒写——在磁盘纪律尚未工具化时开 AOF everysec 反而**放大**该故障面；(4) 战役中途不动运行栈（本卡纪律）。

**生产期：开 AOF（everysec），且先修死配置。** 上述意图已在 `redis.conf` 里躺了一直没生效——这不是"要不要开"的问题，是**配置漂移**问题。

### 最小修建议（S）

生产部署 manifest（`docker-compose.prod.yml` 或 k8s）里让 redis 真正吃到 AOF：command 追加 `--appendonly yes --appendfsync everysec`（或挂载 redis.conf），**同时统一 maxmemory 口径**（conf 3gb vs 实跑 512mb——注意容器 mem limit 仅 768M，3gb 会先撞 cgroup，两者须一起定容）；上线前 staging 演练一次 BGREWRITEAOF + 磁盘水位告警。`stop-writes-on-bgsave-error` 维持 yes（数据面 fail-fast 优于静默丢）。

**不修的风险面**：参赛期不动=接受"崩溃丢一个快照间隔"（当前实测≈0 痛感）；生产期不修死配置=AOF 永远停留在"以为开了"的状态，事件流/幂等键在宕机时整体回滚一个 RDB 间隔，非金额副作用（通知、统计行为）可能重复。

---

## ③ `extra_data=None` 落库为字符串 `'null'`（PHOTON-IDEM micro-debt）

### 实查证据

**序列化点**：模型 `backend/app/models/shop.py:75` —— `extra_data = Column(JSON, nullable=True, ...)`（表 `photon_transaction_history`，:65）。SQLAlchemy JSON 类型的 `none_as_null` 默认为 **False**：绑定值为 Python `None` 时不产生 SQL NULL，而是经 json 序列化为 `'null'` 字面量入库。这正是机制——两条写路径同源：
- ORM 路径：`photon_service.py:335/:387/:453/:531`（`transaction_metadata = extra_data if extra_data is not None else metadata`，`metadata` 缺省时也是 `{}` 之外的 None 分支可达）；
- 原子路径（PHOTON-IDEM 卡新增）：`photon_service.py:247-277`，`bindparam("extra_data", type_=JSON)` 走同一个 JSON bind processor——与 ORM **逐字节一致**（PHOTON-IDEM 对比实验已证），均为 `'null'`。

**活库footprint（只读 SELECT，2026-09-23）**：

```
total=297 | extra_data::text='null' 的行=3 | extra_data IS NULL（SQL NULL）的行=0
值域分布：{"reason":"guest_experience_seed"}×170、achievement_name 类×55+、combo 类×3、'null'×3 …
```

即 297 行里 **0 行 SQL NULL**——所有"无元数据"写入全部变成 `'null'` 字面量，占比 1%。

**读侧消费方盘点**：

- Python ORM 读：`photon_service.py:303` `"extra_data": existing_transaction.extra_data or transaction_metadata` —— JSON null 反序列化回 Python `None`，`or` 惯用法与 SQL NULL **行为完全一致**（往返透明）；
- SQL 级谓词：全仓 grep 无任何 `extra_data IS NULL` / `extra_data->>` / jsonb 函数消费（app+gateway）；
- Go 网关：`internal/db/models.go:4309` 的 `ExtraData []byte` 属于 `InterventionFeedback`（**另一张表** intervention_feedback，非 photon）；photon 相关无网关消费方；该字段非测试代码引用为 **0**；
- `app/api/v1/photons.py:212-232` 的 `request.extra_data` 是请求 schema 字段（写侧输入），非读侧。

### 裁决

**参赛期：不修。** 当前消费面（ORM `or` 惯用法 + 无 SQL 谓词 + 无网关读者）对 `'null'` 与 SQL NULL 完全无感；live footprint 3 行；改模型反而在过渡期制造"新行 NULL / 旧行 'null'"的两种空值并存，**扩大**不一致。

### 最小修建议（若要做，S；建议只入生产前清单）

一行模型改动 + 一次性数据订正，捆绑成一个迁移：
1. `app/models/shop.py:75`：`Column(JSON, nullable=True, none_as_null=True)`；
2. 同迁移内 `UPDATE photon_transaction_history SET extra_data = NULL WHERE extra_data::text = 'null';`（把存量 3 行拉齐，避免双空值并存）；
3. 同 pattern 还存在于 `models/intervention.py` 等表，若修建议连带盘点（`grep -rn "Column(JSON, nullable=True" app/models`）。

**不修的风险面**：任何未来的 SQL 级审计（`IS NULL`）、json→jsonb 迁移/归一化会把这 3+ 行错分类（列是 `json` 非 `jsonb`，`IS NULL` 静默漏判无报错）；债务随写入线性累积（当前 ~1% 写入带 None）。行为性破坏：零。

---

## 收工核查

- [x] 全程只读：docker 仅 inspect/logs/exec（psql 只 SELECT/SHOW、redis-cli 只 CONFIG GET/INFO/SCAN/TYPE/TTL/XLEN/XINFO）；未重启容器与进程，未写活库，未改任何产品代码与配置
- [x] /tmp 探针产物已清（`/tmp/q1_*` 已删，ls 验证无残留）；无后台进程、无模拟器/浏览器/HEAVY 任务
- [x] 交付物仅本文件（无 patch，纯研究卡）；零凭据出现在本文
- [x] 引用均为实查输出或 file:line 原文核对（wt194 基线）
