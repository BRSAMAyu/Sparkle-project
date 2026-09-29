# 本地数据面重建 Runbook（RESTACK）— 容器属主与跨仓隔离

> 适用面：本机 dev 栈（`docker-compose.yml`）因 Docker Desktop 重启、容器灭失后的重建。
> 不覆盖云端生产部署——那条路走 `scripts/deploy/bootstrap.sh` 与 `deploy/ROLLBACK.md`。
> 来源：FIX-557（2026-09-28 事故复盘，wt815 落册）+ FIX-563（2026-09-29 容器名单侧分化落实施工）。
> 登记见 `scripts/README.md`。

## FIX-563 后的两仓容器名对照表（权威）

本仓（Sparkle-project）compose 的 `container_name` 已**单侧分化**加 `_proj_` 中缀；sparkle-cosmos 仓保持 `sparkle_*` 旧名。同名碰撞（FIX-557 事故形态）自此结构性不存在。

| 数据面 | 本仓容器名（本 RUNBOOK 权威） | sparkle-cosmos 容器名 | 本仓 volume（不变，project 前缀分化） |
|---|---|---|---|
| PostgreSQL | `sparkle_proj_db` | `sparkle_db` | `sparkle-project_sparkle_postgres_data` |
| Redis | `sparkle_proj_redis` | `sparkle_redis` | `sparkle-project_sparkle_redis_data` |
| MinIO | `sparkle_proj_minio` | `sparkle_minio` | `sparkle-project_sparkle_minio_data` |
| 其余服务 | 一律 `sparkle_proj_*`（api/agent/gateway/tempo/prometheus/alertmanager/loki/promtail/grafana/age_init/celery_* 等，见各 compose `container_name`） | 对应 `sparkle_*` | 同左，project 前缀分化 |

**识别口诀：看见 `sparkle_proj_*` = 本仓（Sparkle-project）的数据面；看见不带 `_proj_` 的 `sparkle_*` 容器 = sparkle-cosmos 仓的栈，永远不要从本仓脚本去动它。**

- **服务名（compose service / 容器内 DNS）两仓均未改**：`sparkle_db` / `redis` / `minio` / `sparkle_api` … 照旧。`docker compose up -d sparkle_db`、`.env` 的 `POSTGRES_HOST=sparkle_db`、`depends_on`、容器网络内 URL **不受本分化影响，不要改**。
- **生效时机**：容器名只在容器**下次（重）创建**时生效——正在运行的旧名容器不会被本改动触碰或重命名；本仓栈下次 `up` 起的就是 `sparkle_proj_*` 新名。
- **端口面**：两仓 dev 栈默认发布同一组 host 端口（127.0.0.1 的 5432/6379/9000/9001 等）。分化后两栈同名端口会冲突——`up` 失败报 port binding 即是此因，属 fail-loud 预期；要并存需自行错端口（`SPARKLE_DB_PORT` 等变量），或先显式停掉另一仓栈。

## 铁律（任何重建前必读）

- **永远先显式 project 名**：跨仓/脚本化操作一律带 `-p`（本仓默认 project=目录名 `sparkle-project`，sparkle-cosmos 同理为 `sparkle-cosmos`）。`docker compose -p <project> ps|up|down|logs` 永远只在声明的项目内动作；裸 `docker <动词> <容器名>` 是全局命名空间操作，跨仓误击的根源，脚本里禁止裸调他仓名称。
- **分岭检查**（本仓栈健康自证）：

  ```bash
  docker inspect sparkle_proj_db --format '{{index .Config.Labels "com.docker.compose.project"}} {{range .Mounts}}{{.Name}}{{end}}'
  ```

  期望：project=`sparkle-project`、卷前缀 `sparkle-project_`。`scripts/dev/up.sh` 步骤 2 的预检门（FIX-557 立、FIX-563 扩到 db/redis/minio 三数据面）已自动化该检查。
- **宿主上现役属主（截至 FIX-563 施工期）**：真 dev 数据卷仍挂 sparkle-cosmos 项目名下（`sparkle-cosmos_sparkle_{postgres,redis,minio}_data`），其容器仍是旧名 `sparkle_db`/`sparkle_redis`/`sparkle_minio`（19h 健康运行中，分化按自然重启生效）。本仓首次 `up` 会创建**全新空** `sparkle-project_*` 数据面并跑迁移——这是分化后的预期行为，不是数据丢失；旧数据面原样保留在 sparkle-cosmos 项目下。
- **历史文档注记**：FIX-563 之前写就的部署手册/实录/评审里出现的 `sparkle_db`（docker exec/inspect 语境）按写作时点指旧名，照抄会打错容器——以本对照表为准换算（`sparkle_db`→`sparkle_proj_db` 等）。历史记录正文一律不改写。

## 09-28 事故复盘（FIX-557，5 行，史录不改）

1. Docker Desktop 用户重启 → 3 容器（sparkle_db/redis/minio，时为两仓同名）尽灭，daemon CLI 一度僵死。
2. 幸存进程浅探针绿（gRPC :50051 / uvicorn :8000 尚在）造成"栈还健康"假象；DB 路由实际 500。
3. 从错误仓（Sparkle-project）重建 sparkle_db：旧容器已灭故名字无冲突，静默挂上 `sparkle-project_` 前缀空卷。
4. 空库引发 role/auth 迷宫（`role "postgres" does not exist` 等假象故障），形似"数据丢失"。
5. 顺藤纠偏：inspect 查出挂载卷前缀错误 → 改从 sparkle-cosmos 仓重建 → 全链恢复（guest JWT 实证）；全程真数据卷零写入零损失，垃圾空卷已删。

> FIX-563 落地后该事故形态被根除：本仓再怎么 `up`，创建的都是 `sparkle_proj_*` 唯一名容器，与 sparkle-cosmos 的容器/卷无碰撞面。

## 纠偏步骤（发现挂错卷时——历史窗口仍适用）

1. **停写**：不在被误挂的空库上做任何迁移 / seed / 修数据——先止血，别把两套库都弄脏。
2. **取证**：`docker inspect <容器名> --format "{{range .Mounts}}{{.Name}}{{end}}"`，记下错误前缀输出。
3. **摘除误建容器**：在错误仓目录 `docker compose down`（可加 `-p` 显式声明）。**任何场景绝不带 `-v`**（真数据卷在另一项目名下虽不受影响，禁 `-v` 是纪律不是侥幸）。
4. **正属主重建**：真数据在 sparkle-cosmos 项目时 `cd /Users/brsama/code/GitHub/sparkle-cosmos && make dev-up`；本仓自有数据面则在本仓 `make dev-up`（up.sh 预检门会先核对三数据面卷属主）。
5. **复核属主**：重跑第 2 步命令，确认卷前缀与所在仓 project 标签一致；`docker exec sparkle_proj_db psql -U postgres -c '\dt'`（或对侧 `docker exec sparkle_db …`）见真实表 = 挂对。
6. **闭环 smoke**：health 探针 + guest 登录换 JWT 成功 = 恢复闭环；事故时间线补记台账/接力日志。
7. （可选）确认无误后清垃圾空卷：`docker volume rm <垃圾卷全名>`——删前必须先 `docker volume inspect` 确认它不是任何在跑容器的挂载。
