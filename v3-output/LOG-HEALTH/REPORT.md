# LOG-HEALTH — wt194 三裁决的落地件（PG 日志轮转+慢查询 / prod Redis AOF 接线）

> 卡：LOG-HEALTH（D 纵队·部署运维线）｜worktree wt197｜基线 bdb24948｜2026-09-23
> 依据：`v3-output/OPS-QUIRKS/REPORT.md` 裁决 1（PG json 日志无轮转+撕裂+慢查询关）与裁决 2（Redis 参赛期纯 RDB、生产期 AOF+修配置漂移）。
> 性质：纯文件改动 + `docker compose config` 解析验证 + 一次性临时容器探针（逐个 `--rm`/`down` 回收）。**未重启/未 force-recreate 任何既有容器，未 commit/push，零凭据。**
> 交付物：本文件 + `changes.patch`（`docker-compose.yml`、`docker-compose.prod.yml`、`redis.conf` 三文件，+53/−8）。

---

## ① 两件的形制裁决（为什么是这个形制）

### 裁决 1 落地：PG 日志轮转 + 慢查询

| 项 | dev（docker-compose.yml） | prod（docker-compose.prod.yml） | 形制理由 |
|---|---|---|---|
| logging 轮转 | `json-file, max-size 50m, max-file 5`（sparkle_db + **连带 redis/minio**，即裁决原文全量） | `json-file, max-size 100m, max-file 5`（仅 db，按卡面范围） | dev 50m×5=250MB 上限：就是裁决给出的示例值，且 dev 机即 16GB 内存/09-19 磁盘事故的事主机，错误风暴实测写速 ~10MB/4h（裁决证据），250MB≈风暴下 4 天余量，从紧保盘；prod 100m×5=500MB：prod PG stdout 是审计面（裁决认定审计黑洞是唯一不可逆损失），保留期取 dev 的 2 倍，仍有硬上限使风暴复发不再威胁磁盘，prod 服务器磁盘+既有磁盘水位告警下 500MB 属零头，100m 单文件也降低最重日志生产者的轮换频率 |
| 慢查询 | 新增 `command: [postgres, -c, log_min_duration_statement=500]`（值写死 500） | 在 db 既有 command 列表追加 `-c "log_min_duration_statement=${POSTGRES_LOG_MIN_DURATION_STATEMENT:-500}"` | dev 服务原本无 command（用基础镜像默认 CMD），dev 也没有 db 侧 `${…}` 参数化风格、不挂 PG 配置文件 → 命令行参数是唯一与现状一致的机制；显式重申 `postgres` 是因为基础镜像 `pgvector/pgvector:pg16` 的 CMD 即 postgres（已核对 Dockerfile，FROM 无 ENTRYPOINT 变更，安全）。prod db 的 command 块里每个旋钮都是 `${POSTGRES_*:-默认}` 形制 → 新参数完全跟随（运维可经 env 调阈值，置 `-1` 关闭），不引入新形制 |

两文件现状 `logging:` 键出现次数均为 0（wt194 已证），本次为首个轮转形制，无对齐对象；`driver: json-file` 显式写明（默认即 json-file，但把轮转意图钉在文件里）。

### 裁决 2 落地：prod Redis AOF 接线 —— 挂 conf（已有），修两处断点

**接线方式取"挂载 redis.conf"而非 command 追加 `--appendonly`**，理由：prod compose 自初始提交（1722e6dc）就挂了 `./redis.conf:/redis-stack.conf` 且 entrypoint `exec redis-stack-server /redis-stack.conf`——AOF 意图早已在 prod manifest 里，裁决说的"从未被挂载"是 **dev compose**（dev redis 只挂数据卷、command 覆盖一切）。已逐项核对 conf 与 prod 需求一致：`appendonly yes / appendfsync everysec / no-appendfsync-on-rewrite yes / auto-aof-rewrite 100%/64mb`＝裁决生产姿态；`maxmemory 3gb` vs prod 容器上限 4G（x-resources redis 锚）＝裁决要求的"一起定容"已成立（1G 余量供 AOF rewrite fork CoW）；`aclfile /tmp/users.acl` 与 entrypoint 生成的 ACL 契合。若改走 command 追加参数，反而制造第二条真源、继续漂移。

**但验证探针发现 AOF 落地断成两截，均已修**：

1. **数据面断点（conf 无法表达的坑）**：`redis-stack-server` 包装脚本（镜像内实读）启动 redis-server 时**命令行强制追加 `--dir /var/lib/redis-stack`**（CLI 参数覆盖 conf 内任何 `dir`）——RDB 和 AOF 都会落进容器层、绕过 `./redis_data:/data` 挂载，容器重建即全失，AOF 形同虚设。修法：entrypoint 脚本里 conf 路径后追加 `--dir /data`（包装脚本 `$*` 透传在尾部，redis-server CLI 后到者生效）。**临时容器实测**：`dir=/data, appendonly=yes, appendfsync=everysec, maxmemory=3221225472(3gb)`、ACL 认证通过——生产 AOF 才真正吃到。conf 里不加 `dir` 行（会是死配置），改为注释说明。
2. **部署面断点（本卡最重要的发现，P0）**：prod redis 的多行 `command: |` 脚本**会被 compose 在加载期按空格/换行 shell-split 成词表**——实测容器真实 Cmd 变成 `sh -c cat …`（只执行首词 `cat`，读 stdin 即退，`restart: unless-stopped` 下等于无限崩溃循环）。即**基线的 prod redis 服务从未可能启动过它的 ACL+conf 启动脚本**。修法：command 改**列表形式（单元素脚本串）**，compose 对列表元素逐字透传不 split。实测：完整脚本执行、ACL 文件生成（`$${VAR}`→env 展开正常）、容器存活。

## ② 实现清单

1. `docker-compose.yml`（dev）：
   - `sparkle_db`：新增 `command`（postgres + `log_min_duration_statement=500`，带一行注释）；新增 `logging`（json-file 50m×5，带注释引用裁决）；
   - `redis`、`minio`：各新增同款 `logging` 50m×5（裁决 1 原文"连带 redis/minio"）；
   - dev redis 的 command/卷**一字未动**（参赛期本机纯 RDB 是裁决 2 本身）。
2. `docker-compose.prod.yml`：
   - `db`：command 列表追加 `log_min_duration_statement=${POSTGRES_LOG_MIN_DURATION_STATEMENT:-500}`；新增 `logging`（json-file 100m×5，带注释）；
   - `redis`：command 字符串形式 → 列表形式（脚本内容逐字保留，含原 ACL 四行 heredoc），尾部追加 `--dir /data`，脚本内注释说明两处机制与出处。
3. `redis.conf`：**零指令变更**，仅新增注释：`dir` 禁写原因（包装脚本 CLI 覆盖）、`protected-mode yes` 是死配置（包装脚本 CLI 强制 `no`）、maxmemory 3gb 与 4G 上限的配容关系。
4. 验证（全部通过，未起栈）：
   - `docker compose --profile monitoring config`（dev，exit 0）；`docker compose -f docker-compose.prod.yml config`（exit 0）；compose 5.0.2；
   - 渲染核对：dev 3 个 logging 块 + 慢查询参数在位；prod db 参数/轮转在位；prod redis command 完整保留为单元素列表；
   - logging opts 守侧实测：临时容器 `--log-opt max-size/max-file` daemon 接受无报错；
   - redis 行为实测（临时容器 ×3，逐个回收）：断点 1、2 各自的故障复现与修复验证（见上）。

## ③ 冲突面声明

本卡改动 3 文件：`docker-compose.yml`、`docker-compose.prod.yml`、`redis.conf`（+新增 `v3-output/LOG-HEALTH/`）。

- vs **wt193**（backend loguru 日志改造）：动 `backend/app` 日志代码，不涉 compose/redis.conf → **零重叠**；
- vs **wt195**（mobile galaxy）：动 `mobile/` → **零重叠**；
- vs **wt196**（backend 测试）：动 backend 测试 → **零重叠**。

合入管线内本卡无并行写同一文件的已知对手卡；patch 为纯追加式小块，`--3way` 冲突面极小。

## ④ 诚实申报

1. **裁决勘误**：OPS-QUIRKS 裁决 2 的"redis.conf 从未被挂载"仅对 dev compose 成立；prod compose 自初始提交即挂载。本卡据此把 prod 的工作重心从"接上"变为"核实+修断点"。
2. **超卡片字面的一处改动**：prod redis command 字符串→列表形式。字面卡面只要求"接上 AOF"，但探针证明基线形制下该服务**从未可能执行启动脚本**（P0，AOF 接线在其上层，不修则裁决 2 在 prod 无处落地）。脚本内容逐字保留，仅形式变更+尾部 `--dir /data`。
3. **发现但未修（越界，移交）**：同文件 `minio_rbac_init` 有**同一疾病**——多行 `command: |` 被 split 成 `[set, -eu, mc, alias, …]`，`sh -c "set …"` 立即 exit 0，**静默不建桶不配策略**，而 gateway 依赖它 `service_completed_successfully`——prod 部署后上传链路会静默坏死。修法与本卡 redis 相同（列表形式），一行形制变更；因属 minio 子系统、非本卡裁决范围，未动，**建议合入窗口连台修或立即派卡**。
4. **行为影响面**：dev/prod db 重建成后慢查询（>500ms）将进 docker logs（正是 PROD-LOG 想要的面）；dev db 首次带 command 重建属 `--force-recreate` 动作（见⑤，本卡未执行）。prod redis 修复后首次启动 `./redis_data` 为空——历史快照若存在于旧容器层 `/var/lib/redis-stack`，需在重建前 `docker cp` 打捞（若 prod 从未用本文件起过栈则无此包袱，"云端部署已备"口径下大概率如此）。
5. **临时容器申报**：全程新建一次性容器 4 个（镜像脚本实读 ×1 自动 `--rm`；故障复现 ×1；修复验证 ×2；其中 compose 项目 `wt197ctest` 已 `down`+删目录）——不发布端口、不挂运行栈任何卷/数据，与运行栈零接触；全部已回收并核对。
6. **占位 .env 申报**：worktree 无 `.env`（应然），`docker compose config` 的 `env_file:` 存在性检查需要它——曾两度创建**零字节空文件**并随即删除（每次 ls 验证不存在）；未写入任何键值、未进 patch。
7. 零凭据：所有验证用 `dummy / example.invalid / probe-pass` 假值；未读主仓 `backend/.env`。
8. 未 commit / 未 push；未重启、未 force-recreate 任何既有容器；未执行任何裁决中标注"部署动作"的步骤。

## ⑤ 收工核查与合入方步骤

**收工核查**

- [x] 改动仅 3 文件 + v3-output/LOG-HEALTH/（`git status`：3 modified + untracked 目录）
- [x] 两 compose `config` 解析 exit 0（渲染+运行双层验证）；`.env` 占位已删（ls 确认）；/tmp 探针产物全清（ctest 项目、渲染快照、基线副本）
- [x] 无后台进程、无 HEAVY 任务、未触碰运行容器/模拟器/浏览器
- [x] 交付物 = 本文件 + `changes.patch`；零凭据；无 commit/push

**合入方步骤（部署动作，本卡一律未执行）**

1. 备份 → `git apply --3way v3-output/LOG-HEALTH/changes.patch`（FLEET-BRIEF §6 管线）。
2. dev：`docker compose up -d --force-recreate sparkle_db`（秒级窗口，数据卷不动）；验收按裁决 1：`docker logs --since <重建时刻> sparkle_db | tail` 见启动横幅、`--since` 全窗可用、慢查询行出现。dev redis/minio 的 logging 在其下次自然重建时生效，**不要**为日志单独 force-recreate dev redis（参赛期裁决不动其运行栈）。
3. prod（下个部署窗口）：若 prod 曾用旧文件起过 redis，重建前先 `docker cp <旧容器>:/var/lib/redis-stack/. ./redis_data/` 打捞历史持久化；随后 `up -d` 重建 redis（新列表式 command + `--dir /data` 生效）。验收：`redis-cli CONFIG GET dir appendonly appendfsync` → `/data · yes · everysec`；`ls ./redis_data/appendonlydir` 出现 AOF 文件。
4. prod staging 按裁决 2 演练一次 `BGREWRITEAOF` + 磁盘水位告警确认（AOF rewrite 的磁盘峰值面）。
5. 可选：prod `.env` 增 `POSTGRES_LOG_MIN_DURATION_STATEMENT`（默认 500，置 `-1` 关闭）；**P0 移交**：`minio_rbac_init` 同病修复（列表形式，参照本 patch redis hunk）宜同窗口处理，否则 prod 上传链路静默坏死。
