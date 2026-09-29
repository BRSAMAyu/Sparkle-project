# FIX-578 verification — DNS 取证、URL↔alias 对照、渲染与回归

## 1. DNS 现状取证（只读，2026-09-29 本机）

本机现役栈为 sparkle-cosmos 仓（cosmos 侧），sparkle-project 栈未起（其网络 `sparkle-project_default` 存在但空）——alias 机制以现役栈实证 + 目标仓 compose 渲染推证：

```
$ docker ps --format '{{.Names}}\t{{.Networks}}'
sparkle_db     sparkle-cosmos_default
sparkle_redis  sparkle-cosmos_default
sparkle_minio  sparkle-cosmos_default

$ docker inspect sparkle_redis sparkle_db sparkle_minio --format '{{.Name}} | svc: {{index .Config.Labels "com.docker.compose.service"}} | NetAliases: {{range ...}}{{$v.Aliases}} {{end}}'
/sparkle_redis | svc: redis       | NetAliases: [sparkle_redis redis]
/sparkle_db    | svc: sparkle_db  | NetAliases: [sparkle_db sparkle_db]
/sparkle_minio | svc: minio       | NetAliases: [sparkle_minio minio]
```

**机制实证**：compose 在 project 网络注入别名 = {服务键, container_name}。cosmos 侧 redis 服务键=`redis`、容器名=`sparkle_redis`（分化前形态）→ 两名皆解析；本仓 FIX-563 后服务键仍=`redis`、容器名=`sparkle_proj_redis` → 别名集 {redis, sparkle_proj_redis}，`sparkle_redis` 不在其中 ⇒ **悬空实锤**。`sparkle_db` 恰为服务键 ⇒ 一直可解析（F563 豁免对它碰巧成立）。`docker network inspect sparkle-cosmos_default` Containers 仅列 Name/IPv4（Aliases 在 endpoint 侧，inspect 容器面取得，上表）。

目标仓渲染面：`docker compose -f docker-compose.yml config` 服务键清单 = sparkle_db / sparkle_age_init / redis / minio / sparkle_api / sparkle_agent / celery_worker / celery_glm_batch_worker / celery_beat / sparkle_gateway / tempo / prometheus / alertmanager / loki / promtail / grafana；容器名全 `sparkle_proj_*`。celery compose 服务键 = celery_worker / celery_beat / flower / redis / sparkle_db（容器名同 `sparkle_proj_*`）。Makefile（F577 钉死 `COMPOSE_PROJECT_NAME ?= sparkle-project`）celery-up 用 `docker run --network sparkle-project_default` → 解析面即主栈别名集。

## 2. URL↔alias 对照表（修后渲染值逐一对账）

`docker compose config` 渲染实测（哑值 .env，用后即删）：

| 渲染 URL（host:port） | 消费者 | host 归属 | 别名集（主栈网络） | 判定 |
|---|---|---|---|---|
| `redis://:…@redis:6379/0` | sparkle_api / sparkle_agent | 服务键 `redis` | {redis, sparkle_proj_redis} | ✓ |
| `redis://:…@redis:6379/1`（broker） | celery_worker / glm / beat（主+celery compose） | 同上 | 同上 | ✓ |
| `redis://:…@redis:6379/2`（result） | celery_worker / glm | 同上 | 同上 | ✓ |
| `redis:6379`（无 scheme，Go 面 host:port） | sparkle_gateway REDIS_URL | 同上 | 同上 | ✓ |
| `REDIS_HOST=redis` | 同上各服务 | 同上 | 同上 | ✓ |
| `postgresql…@sparkle_db:5432` | 全栈 DATABASE_URL（主+celery compose） | 服务键 `sparkle_db` | {sparkle_db, sparkle_proj_db} | ✓（零触碰） |
| `http://tempo:4317` | api/celery worker/beat OTEL | 服务键 `tempo` | {tempo, sparkle_proj_tempo} | ✓ |
| （修前）`sparkle_redis:6379` | — | 旧容器名，≠服务键，≠新容器名 | ∅ | ✗ 悬空（缺陷本体） |
| （修前）`sparkle_tempo:4317` | — | 同上 | ∅ | ✗ 悬空（同族带出） |

celery compose standalone（自带 redis/sparkle_db 服务，profile celery）：`redis`/`sparkle_db` 服务键同网络自解析 ✓；OTEL `tempo` 仅在并入主栈时可解析（standalone 无 tempo 服务——修前 `sparkle_tempo` 两种形态皆悬空，修后至少不劣化、主栈形态正确，standalone OTEL 缺靶为既有能力面，limitations 登记）。

## 3. 渲染与静态验证（全 exit 0）

```
docker compose -f docker-compose.yml config --quiet            → exit 0
docker compose -f docker-compose.dev.yml config --quiet        → exit 0
docker compose -f docker-compose.prod.yml config --quiet       → exit 0（哑值补 IMAGE_TAG/TRUSTED_PROXIES 等 :? 门）
docker compose -f docker-compose.celery.yml --profile celery config --quiet → exit 0
docker compose -f docker-compose.yml -f docker-compose.services.yml config --quiet → exit 0（overlay 正确组合面）
docker compose -f docker-compose.yml -f docker-compose.celery.yml config --quiet   → exit 0
make -n celery-up                                              → exit 0
bash -n scripts/run_e2e_smoke.sh                               → exit 0
python -m py_compile backend/app/config/settings.py backend/scripts/celery_acceptance.py → exit 0
gofmt -l backend/gateway/internal/config/config.go             → 空输出
```

prod / services 两文件 standalone 渲染失败为**既有环境变量门**（`:?` 必填 + overlay depends_on），非本卡引入（base 同形，补齐哑值后全过）。

## 4. 测试回归

| 套件 | 结果 | 判定 |
|---|---|---|
| backend 单测（redis fixture isolation + phase0 hardening + tracing export） | **24 passed, 2 skipped**（exit 0） | ✓ 含 URL 改写/normalize 面与 OTEL endpoint 面 |
| scripts/tests/test_service_supervisor.py | 7 collected：**6 passed, 1 failed** | 失败项 `test_once_cli_green_on_healthy_decoy` 为 **daemon 环境态 base 同败**：主 checkout（main `ba41c339`，未含本卡改动）单测复测同败（exit 1）——与本卡零改动面（`git diff --name-only` 无 supervisor/probe/ops 文件）互证，非回归。与 F577R1 receipt「失败项 daemon 环境态 base 同败归因」同口径 |
| scripts/tests/test_o05_restore_consistency.py | **14 passed**（exit 0） | ✓ |
| backend/gateway `go test ./internal/config/` | **ok**（exit 0） | ✓ 本地桥 lockstep 改动面 |

## 5. 残余 grep 对账

修后全仓 `sparkle_redis:6379|sparkle_minio:|sparkle_tempo:4317|REDIS_HOST=sparkle_redis`：可执行消费面 **0 残留**。`@sparkle_db:5432` 残留全部为服务键面（合法）。逐文件归类见 grep_exemptions.md。
