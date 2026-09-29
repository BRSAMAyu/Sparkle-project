# FIX-571 run_manifest — 共享数据面三联事故修复（P1）

- 执行：FIX-571 fleet 修复 agent（worktree `wtF571`，分支 `fix/v4/f571-dataplane`，基点 main@`5f3aead4`）
- 日期：2026-09-29 09:03–09:40 (+0800)
- 约束执行情况：FIX-557 铁律全程遵守（未改 sparkle-cosmos 仓任何文件；凭据修复走 SQL 层 ALTER ROLE/CREATE ROLE，未动容器 env）；三容器零重建零销毁；无用户数据删除；新密码零回显零入库（本文占位符）；备份先行；死信回放前逐条留档。

## 0. 修复前状态（pre-state，09:05–09:12 实测）

| 项 | 实测 |
|---|---|
| 共享容器 | sparkle_db / sparkle_redis / sparkle_minio 均 Up 18h (healthy)；`docker inspect` sparkle_db：compose project=sparkle-cosmos、卷=sparkle-cosmos_sparkle_postgres_data（FIX-557 真数据面） |
| 驻留栈进程 | 网关 PID 77602 `/tmp/sparkle_gateway`（09-28 09:55:45 起，早于全部 Q04 依赖合并）；uvicorn PID 70080（09-28 20:10:46 起，缺 U07）；grpc PID 51857（09-29 07:52:25 起，孤儿） |
| DB 角色（卷内） | postgres / sparkle_celery / sparkle_engine / sparkle_gateway / sparkle_readonly / wt*_scratch —— **无 `brsama` 角色** |
| host 侧鉴权 | `PGPASSWORD=<backend/.env POSTGRES_PASSWORD> psql -h 127.0.0.1 -U brsama` → **FATAL password authentication failed for user "brsama"**（角色不存在；exit 2）；`PGPASSWORD=<容器 env POSTGRES_PASSWORD> psql -U postgres` → **FATAL password authentication failed for user "postgres"**（hash 陈旧；exit 2）；容器内 socket psql → OK（exit 0） |
| backend/gateway .env | POSTGRES_USER 均=brsama、POSTGRES_DB=sparkle、POSTGRES_PASSWORD 两者一致；REDIS_PASSWORD backend 有效（PONG）/ gateway 陈旧（后续 WRONGPASS 实锤）；MINIO_KEYS gateway 陈旧（后续 Access Key 不存在实锤） |
| 队列 | `LLEN queue:billing`=0；`LLEN queue:billing:dead_letter`=**230**（94 唯一 request_id，单条最多 8 份重复死信；failed_at UTC 09-28T22:27–23:59 = 本地 09-29 06:27–07:59，Q04 恢复推挤竞争窗）；229 条 wtq04-*（error=password authentication failed for user "postgres"——坏凭据 worker 所为）+1 条 cb6aac13-*（ForeignKeyViolation token_usage_user） |
| token_usage | 1451 行；max(created_at)=2026-09-28 23:42:02.89（Q04 恢复批）；此后零写入——数据面停摆实锤 |

## 1. 备份（动手前，铁律 2）

```
mkdir -p /Users/brsama/backups/fix571 && chmod 700 ...                     # exit 0
docker exec sparkle_db pg_dumpall -U postgres > \
  /Users/brsama/backups/fix571/fix571_pgdumpall_20260929_091336.sql        # exit 0
# 产物 192MB；grep -c "PostgreSQL database dump complete" = 14；stderr 0 行
# sha256 前 16 位：0b69a4e5d4112790；chmod 600；路径在两仓与 wtF571 之外，不入库
```

## 2. 事故① DB host 侧鉴权修复（SQL 层，零 env 改动）

```
PW_ENV=$(docker exec sparkle_db printenv POSTGRES_PASSWORD)                # 运行时变量，零回显
APW=$(grep POSTGRES_PASSWORD Sparkle-project/backend/.env)                 # 运行时变量，零回显
docker exec -i -e RPW="$PW_ENV" -e APW="$APW" sparkle_db \
  psql -U postgres -d postgres -v ON_ERROR_STOP=1 -v rpw=:'$RPW' -v apw=:'$APW' <<SQL
ALTER ROLE postgres WITH PASSWORD :'rpw';        -- 卷内 hash 对齐容器 env（env 属 cosmos 面不改，改 DB 侧）
CREATE ROLE brsama  WITH LOGIN SUPERUSER PASSWORD :'apw';  -- 补建本仓两 .env 指向的缺失角色
SELECT rolname, rolsuper, rolcanlogin FROM pg_roles WHERE rolname IN ('postgres','brsama');
SQL
# 输出：ALTER ROLE / CREATE ROLE / brsama|t|t + postgres|t|t；alter-exit=0
```

验证（exit 0 全部）：
- `PGPASSWORD=<APW> psql -h 127.0.0.1 -U brsama -d sparkle` → `host-auth-brsama-ok, current_user=brsama`
- `PGPASSWORD=<PW_ENV> psql -h 127.0.0.1 -U postgres -d sparkle` → `host-auth-postgres-ok`
- 容器内 socket `psql -U $POSTGRES_USER` → `in-container-ok`（未受影响）

语义注记：postgres 角色密码对齐容器 env 后，cosmos 仓 .env（已轮换值）host 侧恢复可用；Q04 曾引用的 git 史初始凭据自此失效（轮换意图的落实，非破坏）。sparkle_celery/engine/gateway/readonly 等旧角色未动（最小干预）。

## 3. 事故③ 驻留栈按当前 main 重启（含启动命令修复）

停旧（SIGTERM 全部优雅退出，未用 SIGKILL）：
```
kill -TERM 77602 70080 51857        # exit 0；5s 后 4 进程（含 wrapper 70079）全部 gone
# 三端口 50051/8000/8080 释放（lsof 计数=0）
```

起新（main 检出 /Users/brsama/code/GitHub/Sparkle-project，重启时点 main=**13814d3c**；不跑 `make dev-up`——避开 FIX-557 容器名/数据卷陷阱）：

| 服务 | 实际生效路径 | 结果 |
|---|---|---|
| API :8000 | `nohup uvicorn app.main:app --host 0.0.0.0 --port 8000`（dev-stage3.sh 原式） | PID 3585，09:16:32 起，/health 200 |
| gRPC :50051 | 首试 dev-stage3 式 `nohup python grpc_server.py` → **FAIL**（`nohup: python: No such file or directory`）；改 `nohup bash scripts/run_grpc_with_env.sh`（venv 感知，make grpc-server 同路径）期间另一 fleet 会话恰好前台执行 `make grpc-server`（PID 4895，09:17:42 起）抢先用同一修复路径启动成功；本卡重复实例 4998 已 SIGTERM 收敛（SO_REUSEPORT 双绑 split-brain 消除），单引擎归一 | PID 4895，current main，五服务 reflection 可见（agent.v1.AgentService/error_book/galaxy.v1/inference/stt） |
| 网关 :8080 | `go run cmd/server/main.go` **FAIL**（单文件编译 undefined: initCQRS 等——多文件包）→ 改 `go build -o bin/gateway ./cmd/server && exec ./bin/gateway`（dev_local_stack.sh 同路径）；首起 **Redis WRONGPASS**（gateway/.env REDIS 凭据陈旧）→ 对齐 backend/.env 有效值（本仓 git-ignored 本地文件，运行时修正）；再起 **MinIO Access Key 不存在** → 从容器 env 运行时读取 MINIO_ROOT_USER/PASSWORD 对齐 gateway/.env；09:20:56 起 | PID 6588，/api/v1/health 200 |

链路验证：
```
POST :8080/api/v1/auth/guest?guest_id=fix571-probe-*  → 200（0.86s，access_token+user id）
users 表 username LIKE 'fix571-%' → 2 行（引擎经新凭据真实落库）
```

**脚本面修复（入本卡 commit）**：`scripts/dev-stage3.sh` 三处——①`make dev-up` 换成共享三容器健康门（缺失即报 FIX-557 属主提示退出，不再自动 compose up 踩坑）；②grpc 启动改 `run_grpc_with_env.sh`（修 `python` 不存在）；③网关改整包 `go build ./cmd/server`（修单文件编译）。`bash -n` 过。

## 4. 事故② 坏凭据竞争 worker 停用 + 死信清点回放

坏凭据 worker 随旧栈（70080/51857/77602）停止；新栈凭据修复后为唯一消费方（单栈内 engine+api 两 worker 属产品常态拓扑）。

**留档（回放前）**：230 条全量快照 → `v4/evidence/FIX-571/dead_letter_archive_230.jsonl`（sha256 前 16 位 `0defcc744c40977d`；内容为计费元数据 request_id/user_id/session_id/model/tokens/cost/时间，无凭据）。

**消费正常验证（先于回放，铁律 6）**：RPUSH 5 条已在库记录入 `queue:billing` → 15s 内队列排空至 0；dead_letter 保持 230（无新增死信）；token_usage 保持 1451（duplicate 静默跳过语义正确）→ 消费链路健康。

**回放（产品自身队列路径，非直插）**：94 条唯一记录逐条 RPUSH `queue:billing`（回放前基线：93/94 已在库〔Q04 自身 worker 落库+58 行直插恢复批覆盖〕，1 条待落=cb6aac13）：

```
pushed=94；push-exit=0
20s 后：queue:billing=0（全部消费）
dead_letter=231（+1：cb6aac13 复现 ForeignKeyViolation——其 user 行已不存在，用户删除后计费不可落库）
token_usage=1451（93 条 duplicate 跳过；无伪造行）
```

**清死信**：队列现存 231 条 = 旧 230（与留档逐条 entrywise 比对一致：request_id+failed_at 全匹配）+ 新 1（cb6aac13，failed_at UTC 01:23:27=本地 09:23，本轮回放产生）。`LTRIM queue:billing:dead_letter 230 -1`（trim-exit=0）→ **dead_letter=1**，仅留不可解的 cb6aac13（用户已删，按「不伪造、失败留档」保留在队列与归档中）。

### 回放去向总账

| 去向 | 条目 | 说明 |
|---|---|---|
| 已在库（duplicate 跳过） | 93 唯一 id / 230 条目中的重复死信 | Q04 期 worker 正常批 + Q04 58 行直插恢复批已覆盖，回放经队列复验 dedup 语义 |
| 回放失败留档 | 1（cb6aac13-55e1-405a-90f7-4fcf068c5d7d） | user 515fc368… 已删除 → token_usage_user_id FK 违约；no_generation_model/0tok；保留于 dead_letter 与归档 |
| 队列终态 | `queue:billing`=0；`queue:billing:dead_letter`=1 | 152 行历史丢失为 Q04 红项④既有事实（记录已被坏凭据 worker 消费吞没，本卡不可逆恢复；流内 usage 帧+Q04 恢复批已对账补偿），预防=本卡单消费方修复 |

## 5. 修复后终态（09:38 合并复验，全部 exit 0）

1. host 鉴权 brsama（本仓 .env）→ OK user=brsama
2. host 鉴权 postgres（容器 env 值）→ OK
3. guest auth :8080 → 200
4. `queue:billing`=0，`queue:billing:dead_letter`=1
5. token_usage=1451 行
6. /health（:8000）=200，/api/v1/health（:8080）=200
7. users 表 fix571-* 探针行=2

## 6. 密钥占位对照（零回显承诺）

| 占位符 | 实际来源 |
|---|---|
| `<POSTGRES_PASSWORD@backend/.env>` | Sparkle-project/backend/.env 与 backend/gateway/.env（两处一致） |
| `<POSTGRES_PASSWORD@sparkle_db容器env>` | sparkle_db 容器 POSTGRES_PASSWORD（cosmos compose 注入） |
| `<REDIS_PASSWORD@backend/.env>` | backend/.env REDIS_PASSWORD（实测 PONG 的有效值） |
| `<MINIO_ROOT_USER/PASSWORD@容器env>` | sparkle_minio 容器 env |

## 7. 遗留风险与移交

1. **引擎进程属主**：现驻留引擎 PID 4895 由另一 fleet 会话的前台 `make grpc-server` 持有（09:17:42 起）；若该会话收尾时终止它，用 `make grpc-server`（仓内规范路径，本卡已修 dev-stage3.sh 等效命令）重启即可，凭据面已通。
2. **栈代码时点**：驻留栈运行于重启时点 main=13814d3c；其后 main 前进至 062d6666，含一笔 backend 产品变更 9cb9d961（FIX-562 spark 通道门，与数据面无关）——下次自然重启带上。
3. **gateway/.env 对齐为本地运行时修正**：该文件 git-ignored，只修复了本机本检出；其他机器/检出需同法对齐 REDIS/MINIO 凭据（建议 FIX-563 ops 卡在单侧分化时统一）。
4. **uvicorn 运行时**：homebrew python3.11 的 uvicorn（与旧驻留一致），非 .venv；功能验证通过，统一化可随下次重启改 venv。
5. **LLM 全链 chat roundtrip 未跑**（避免真实模型支出）；引擎 LLM 连通性不受本卡影响（env 值未变）。鉴权/DB/Redis/队列/网关五面均实测通过。
6. **初始凭据失效**：postgres 角色已对齐轮换值，cosmos git 史初始凭据 host 侧自此不可用（预期行为）。
