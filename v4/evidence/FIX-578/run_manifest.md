# FIX-578 run_manifest — celery env URL 旧容器名 DNS 悬空收口

- 卡：V3-FIX-578（P2，F577 修复中发现并登记，台账 459 行）
- 分支：`fix/v4/f578-celery-dns-resolution`（自 main `8aaa655e` 开出，执行中并入 main `ba41c339` 含 FIX-577 闭账）
- worktree：`/Users/brsama/code/GitHub/wtF578`
- 执行：FIX-578 agent，2026-09-29

## 缺陷定性（取证结论，非翻案）

FIX-563 将本仓 compose `container_name` 单侧分化 `sparkle_*→sparkle_proj_*`。user-defined 网络上可解析名=别名集，compose 自动注入 **{服务键, container_name}**（现役栈实证见 verification.md §1）。分叉后：

| 名字 | 服务键 | 容器名 | 网络别名集 | 可解析？ |
|---|---|---|---|---|
| `sparkle_db` | `sparkle_db`（键即旧名，未分化） | `sparkle_proj_db` | {sparkle_db, sparkle_proj_db} | ✓（服务键面） |
| `sparkle_redis` | `redis`（已非此名） | `sparkle_proj_redis` | {redis, sparkle_proj_redis} | **✗ 悬空** |
| `sparkle_minio` | `minio` | `sparkle_proj_minio` | {minio, sparkle_proj_minio} | **✗ 悬空**（全仓无 URL 消费，仅卷名 `sparkle_minio_data`） |
| `sparkle_tempo` | `tempo` | `sparkle_proj_tempo` | {tempo, sparkle_proj_tempo} | **✗ 悬空**（OTEL endpoint 消费） |

F563 grep 豁免清单 §A 前设「服务名两仓均未分化，URL 内 DNS 全保留」对 `sparkle_db/sparkle_api/sparkle_agent/sparkle_gateway`（真服务键）成立，对 `sparkle_redis/sparkle_tempo`（旧容器名≠服务键）不成立——单行 grep 漏网络语义，与 F563R1 发现1 同族。**缺陷成立，修法落地。**

## 改动面（15 文件 +112/-112 核心 commit `ad5bbf47`；caveat 回填与证据随闭账 commit）

- `docker-compose.yml`：api/agent/celery_worker/celery_glm_batch_worker/celery_beat/sparkle_gateway 的 `REDIS_URL`/`REDIS_HOST`/`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` 全族 `sparkle_redis→redis`（18 处）；api OTEL `sparkle_tempo:4317→tempo:4317`；`@sparkle_db:5432` 系服务键零触碰
- `docker-compose.celery.yml`：worker/beat/flower URL `→redis`（6 处）、OTEL `→tempo`（2 处）
- `Makefile`：celery-up 三 worker + flower broker `@sparkle_redis:6379→@redis:6379`（9 处）；`sparkle-project_default` 网络内按主栈别名集解析；`celery-flush` 的 `docker exec sparkle_proj_redis` 本就正确
- `scripts/run_e2e_smoke.sh`：生成 env 的 REDIS_HOST/REDIS_URL/CELERY_* `→redis`（BACKEND_URL=sparkle_api 系真服务键零触碰）
- `backend/scripts/celery_acceptance.py`：`docker run --network sparkle-project_default` env URL `→redis`
- 五 env 模板（`.env.example`/`.env.deploy.example`/`.env.production.example`/`backend/.env.example`/`backend/gateway/.env.example`）：REDIS_HOST/REDIS_URL/CELERY_* `→redis`（prod 栈 redis 亦为服务键，prod compose 全 env 透传无硬编码）
- `backend/app/config/settings.py` + `backend/gateway/internal/config/config.go`：本地桥 lockstep——`127.0.0.1` 映射集 `(sparkle_db, sparkle_redis)` 增 `redis`（存量 .env 旧值兼容保留），`REDIS_HOST` 默认值 `→redis`（host 跑进程经映射落 127.0.0.1，docker 内返回原值走网络解析）
- 活文档：`QUICK_START_CELERY.md`（容器名 `sparkle_celery_*`/`sparkle_flower`→`sparkle_proj_*`、exec 目标 `sparkle_redis`→`sparkle_proj_redis`、`--network sparkle-flutter_default`→`sparkle-project_default`）、`CELERY_DEPLOYMENT_GUIDE.md`（同族容器名+env URL+OTEL）、`docs/02_技术设计文档/11_Docker配置详解.md`（网络示例 `redis://redis:6379` 勘误+分化注记）
- F577R1-C2 转派回填：三处弃用指引（start_celery.sh 头部块、scripts/devtools/README.md、QUICK_START_CELERY.md 方式 B）补 caveat——替代路径 URL 已由本卡修正可用，脚本体内死债维持不修

## 红线

零 up/down/restart/run（取证仅 `docker network inspect`/`docker inspect`/`docker ps`/`compose config` 渲染）；不改任何服务键/container_name/volume 名（F563/F577 结构零触碰）；主 checkout 零改动；临时哑值 `.env` 用后即删未入库（gitignore 61 行覆盖）；不 push。
