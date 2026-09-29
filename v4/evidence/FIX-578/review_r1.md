# FIX-578 R1 独立审查 receipt（2026-09-29，审查员 R1，未参与实现）

- 审查对象：`ad5bbf47`（15 文件核心）+ `b2d4725f`（C2 回填+证据五件套），台账头 `bad143a0`，base `8aaa655e`，worktree `/Users/brsama/code/GitHub/wtF578`，分支 `fix/v4/f578-celery-dns-resolution`
- 红线遵守：零容器生命周期操作（docker 面仅 `docker ps`/`docker network ls`/`docker inspect`/`compose config` 只读渲染）；mutation 探针已还原（`git checkout -- docker-compose.celery.yml` 后 `git status --porcelain` 0 行）；临时哑值 `.env` 两次用后即删（收尾 `git status --porcelain` 0 行）；主 checkout 全程零改动。
- 环境：macOS darwin 25.6.0 arm64，Docker Compose v5.0.2 / daemon 29.8.0；backend pytest 用主 checkout venv（/Users/brsama/code/GitHub/Sparkle-project/backend/.venv）。

## VERDICT: PASS_WITH_CHALLENGES

八个审查靶全部实证通过：别名集机制亲证成立、修法（URL 统一指向 compose 服务键）正确且零越权、全部宣称回归复现（supervisor 项优于宣称）、遗留登记逐项实锤诚实。挑战集中在**验证方法论盲区与证据表述精度**（config.go 默认值残留 + 场景六 compose 版本依赖），不阻塞闭账。

## 逐靶结论（按审查令顺序）

1. **别名集取证亲复验** ✔ 现役 cosmos 栈 `docker inspect sparkle_redis sparkle_db sparkle_minio`：svc=redis→NetAliases [sparkle_redis redis]；svc=sparkle_db→[sparkle_db sparkle_db]；svc=minio→[sparkle_minio minio]——`{服务键, container_name}` 机制实锤，`sparkle_db=服务键、sparkle_redis≠服务键` 判定成立。本仓渲染（哑值 .env 用后即删）：主栈服务键含 redis/minio/tempo/sparkle_db，容器名全 `sparkle_proj_*`；渲染后 URL 主机名清点=redis:6379×11、sparkle_db:5432×7、tempo:4317×1、minio:9000、`REDIS_URL: redis:6379`（gateway host:port 形）——全部 ∈ 对应网络别名集，对照表逐行核过，旧名（除 volume 键 `sparkle_{redis,minio}_data`，F563 红线面）在渲染面 0 出现。
2. **零残留独立 grep（多行感知）** ✔* 独立扫（URL 消费形 `sparkle_redis:[0-9]|@sparkle_redis|sparkle_tempo:|sparkle_minio:[0-9]|REDIS_HOST=sparkle_redis`，yml/py/go/sh/Makefile/env 模板全仓）+ 续行 Join 后 docker-run 块扫描（自校准：先打 start_celery.sh 已知旧名命中确认扫描器有判别力，再扫全量）。命中逐条对照豁免清单：测试夹具（redis_fixture 2、tracing 2 行）、conftest.py:124 与 test_cache_consistency_integration.py:47（宿跑 legacy-hostname 归一逻辑，输入样本非 DNS）、start_celery.sh 体 6 URL（F577 裁决域）、SECURITY_RBAC 史录 4、v3/v4 冻结面——全部在豁免清单覆盖内。**但发现 C1（见发现列表）**：`config.go:668 viper.SetDefault("REDIS_HOST","sparkle_redis")` 为可执行默认值残留，既不在豁免清单亦不被实现方 grep 模式（`REDIS_HOST=sparkle_redis` env 文件形）覆盖。
3. **选名裁决复核** ✔ `git diff e5e5851c^ e5e5851c -- docker-compose.yml` 服务键清单 pre/post **逐字节相同**（SERVICE_KEYS_IDENTICAL），container_name 12 处 sparkle_*→sparkle_proj_*——「服务键跨 F563 不变量」diff 实锤，服务键为最稳面裁决成立。本地桥 lockstep：settings.py:39/config.go:260 映射集增 `redis` 且存量 `sparkle_db/sparkle_redis` 保留（旧 .env 兼容不破）；语义核=宿跑时 REDIS_URL/REDIS_HOST 归一 127.0.0.1（settings.py:1353-1357），容器内原值返回走网络解析；go test ./internal/config/ ok。limitations.md §2 已如实登记「远程真名恰为 redis 被误映射」边界（与既有 sparkle_db 映射同风险面）。
4. **C2 caveat 回填** ✔ 三处在位且与修后事实一致：start_celery.sh:24-29（「replacement paths NOW USABLE…本脚本体维持 F577 裁决不修」）、devtools/README.md:8（同行补「替代路径的 redis/db URL 已由 FIX-578 修正为可解析服务名」）、QUICK_START_CELERY.md:76（方式 B 前 FIX-578 注）。措辞与实际一致（make celery-up 9 处、compose celery 面 URL 已修为可解析服务键；standalone OTEL 缺靶另有 D4 登记，未过度声明）。
5. **mutation 独立** ✔ sed 临时还原 docker-compose.celery.yml 两条 CELERY_BROKER_URL→`@sparkle_redis:6379` → 实现方 verification.md §5 原 pattern `sparkle_redis:6379|sparkle_minio:|sparkle_tempo:4317|REDIS_HOST=sparkle_redis` 命中 2 行（exit 0），渲染面 `CELERY_BROKER_URL: redis://:change-me@sparkle_redis:6379/1` 悬空可见 → `git checkout --` 还原，status 0 dirty。方法对 URL 类有判别力（其盲区见 C1）。
6. **回归重跑** ✔ backend 单测（redis fixture isolation+phase0+tracing）**24 passed 2 skipped**；o05 **14 passed**；supervisor **7 passed**（宣称 6+1——本机 daemon 健康态全绿，失败项 `test_once_cli_green_on_healthy_decoy` 为 daemon 环境态归因进一步坐实：同代码当前环境即绿，且 F578 两 fix commit 零触碰 scripts/tests//ops/（该文件唯一改动来自 F577 `3fb2ee9c` 经合并带入）；伴随 f2b0cd92 台账「Docker 崩溃 45s 自愈」时段吻合）；`go test ./internal/config/` **ok**；`make -n celery-up` 0（9 处 @redis:6379 清点）；`bash -n`/`py_compile`/`gofmt -l` 全零输出。compose 渲染：main/dev/services-overlay/celery standalone/celery overlay（带 `--profile celery`）/prod（补 16 个 `:?` 哑值门）**全 exit 0**——六场景成立，唯场景六裸 `-f yml -f celery.yml`（无 profile）在本机 Compose v5.0.2 失败，见 C2。
7. **遗留四项诚实性** ✔ 逐项独立实锤：(1) prod compose 服务键清单实为 `db/db_age_init/db_migrate/redis/tempo…`（无 sparkle_db），`.env.production.example` 保留 `@sparkle_db:5432` 族 7 处，deploy-prod.sh 直通 `${DATABASE_URL}`——喂 prod compose 即悬空，登记属实且 redis 族已正确改为 `redis`（prod 服务键恰为 redis）；消费流未证实的表述与 deploy-prod.sh 不读 .env.production 的事实相符。(2) k8s/base Service 仅 `sparkle-backend`/`sparkle-gateway`，secrets-and-configmaps.yaml 2 处 `@sparkle_db:5432` 无对应 Service——陈置属实。(3) `11_Docker配置详解.md:36 grpc://sparkle_backend:50051` 在位未修已登记。(4) celery compose standalone 服务集 {redis,sparkle_db,celery_worker,celery_beat,flower} 无 tempo——登记属实；真实起栈待授权窗口已在 limitations §2 显式声明。
8. **零越权** ✔ 两 fix commit 触 23 文件=15+8 与宣称一致；compose diff 唯 env 赋值（REDIS_URL×8/REDIS_HOST×6/CELERY_BROKER×5/CELERY_RESULT×4/OTEL×3）+flower `command:` 内 broker URL（同族），container_name/服务键/volume 键 0 改动；bad143a0 仅台账两 state 文件。本审查全程零容器生命周期操作。

## 发现列表

- **C1 | MEDIUM-LOW | backend/gateway/internal/config/config.go:668** `viper.SetDefault("REDIS_HOST", "sparkle_redis")` 可执行默认值残留旧容器名——commit message 与 grep_exemptions.md A 节宣称「settings.py/gateway config.go …REDIS_HOST 默认值→redis」**对 go 侧不成立**（settings.py:243 已改 `redis`，config.go:668 未动）；verification.md §5 grep 模式（`REDIS_HOST=sparkle_redis` env 文件形）结构性抓不到 Go `SetDefault("REDIS_HOST", "sparkle_redis")` 形，豁免清单 C/D 亦未登记。复现：`grep -n 'SetDefault("REDIS_HOST"' backend/gateway/internal/config/config.go` → 668 行。暴露面=REDIS_HOST 未设且容器内启动 gateway 的路径（本仓无脚本化该路径：compose 显式注入 REDIS_HOST=redis、dev_local_stack.sh 设 127.0.0.1、k8s 面已登记陈置），F563 起既有悬空、非本卡回归；但「可执行消费面旧名 grep 残留 0」的宣称按其字面口径不真。建议随 go 侧小卡改默认值或登记豁免，并复核本族 grep 模式覆盖 Go/Py 字面形。
- **C2 | LOW | verification.md §3 场景六** `docker compose -f docker-compose.yml -f docker-compose.celery.yml config --quiet` 在 Docker Compose **v5.0.2** 无 `--profile celery` 时失败（`sparkle_api depends on undefined service "redis"`：celery 文件的 redis 带 `profiles: [celery]`，合并后服务被 profile 门控）；**base 8aaa655e 同 compose 同形失败**（`celery_glm_batch_worker depends on undefined service "sparkle_db"`，同类）→ 实现方 compose 版本行为差异、非本卡引入；带 `--profile celery` 渲染 exit 0。复现：`docker compose -f docker-compose.yml -f docker-compose.celery.yml config --quiet`（哑 env）exit 1；加 `--profile celery` exit 0。建议证据记录 compose 版本口径。
- **C3 | INFO | v4/evidence/FIX-578/grep_exemptions.md §C 计数** 分类/计数漂移：test_phase0_production_hardening.py 标（1）但其唯一 sparkle 命中是 `@sparkle_db`（B 类服务键形）；test_tracing_export_config.py 实为 2 行标（1）；fv06/config_rbac 两文件实含 `@sparkle_db` 夹具（B 类语义）列于 C。无运行时影响，登记精度问题。
- **C4 | INFO | scripts/dev-stage3.sh:18-19、backend/COMMANDS_QUICK_REFERENCE.md:137 等** 非旧名消费面未入豁免表但语义有效：dev-stage3 对**容器名** `docker ps | grep -qx sparkle_redis` 探测（本机 cosmos 侧同名容器现役在跑，实测成立）、docs `docker exec sparkle_redis`（cosmos 栈操作史录）——容器名操作非 DNS URL 消费，现状为真；后续 cosmos 栈退役时应随 ops 文档卡清理。

## 命令与 exit code 清单（关键项）

| 命令 | exit / 结果 |
|---|---|
| `docker inspect sparkle_redis sparkle_db sparkle_minio`（aliases/svc 标签） | 0；[sparkle_redis redis] / [sparkle_db ×2] / [sparkle_minio minio] |
| `docker compose -f docker-compose.yml config`（哑 .env 用后即删） | 0 |
| 同上 ×`docker-compose.dev.yml` / `-f docker-compose.services.yml` / `prod.yml`（16 哑值门）/ `celery.yml --profile celery` / `yml+celery.yml --profile celery` | 0 ×5 |
| `docker compose -f docker-compose.yml -f docker-compose.celery.yml config --quiet`（无 profile，head） | 1（C2；base 同形败） |
| `make -n celery-up` / grep `@redis:6379` 计数 | 0 / 9 |
| `bash -n run_e2e_smoke.sh` / `py_compile settings.py celery_acceptance.py` / `gofmt -l config.go` | 0 / 0 / 空输出 |
| pytest redis_fixture+phase0+tracing（主 checkout venv） | 24 passed 2 skipped |
| pytest test_o05_restore_consistency.py | 14 passed |
| pytest test_service_supervisor.py（本机 daemon 健康态） | **7 passed**（宣称 6+1 失败项未复现，归因坐实） |
| `go test ./internal/config/` | ok |
| mutation：sed 还原 2×CELERY_BROKER_URL→sparkle_redis → 实现方 §5 grep | 命中 2 行（exit 0）；渲染悬空可见 |
| `git checkout -- docker-compose.celery.yml` + `git status --porcelain` | 0 行（探针还原） |
| `git diff e5e5851c^ e5e5851c` 服务键清单 diff | 空（SERVICE_KEYS_IDENTICAL） |
| `git status --porcelain`（收尾） | 0 行 |

— R1（2026-09-29）
