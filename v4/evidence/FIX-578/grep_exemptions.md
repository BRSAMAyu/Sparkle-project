# FIX-578 grep 豁免清单

修后全仓 `sparkle_db:5432|sparkle_redis:6379|sparkle_minio:`（及同族带出 `sparkle_tempo:4317`、裸 `REDIS_HOST=sparkle_redis`、活文档旧容器名）逐命中归类。原则：**可执行消费=改；真服务键=零触碰；历史/冻结/他域=豁免登记**。

## A. 已修（可执行消费，本卡改动面）

- `docker-compose.yml`（24 处）、`docker-compose.celery.yml`（8 处）、`Makefile` celery-up（9 处）、`scripts/run_e2e_smoke.sh`（4 处）、`backend/scripts/celery_acceptance.py`（2 处）：redis/tempo URL 与 REDIS_HOST → 服务键
- 五 env 模板 `.env.example` / `.env.deploy.example` / `.env.production.example` / `backend/.env.example` / `backend/gateway/.env.example`：REDIS_HOST/REDIS_URL/CELERY_* → `redis`（prod 栈 `redis` 亦为服务键；prod compose 全 env 透传）
- `backend/app/config/settings.py` / `backend/gateway/internal/config/config.go`：本地桥映射集与 REDIS_HOST 默认值 lockstep
- 活文档三件：`QUICK_START_CELERY.md`（容器名/网络名 14 处）、`CELERY_DEPLOYMENT_GUIDE.md`（28 处）、`11_Docker配置详解.md`（1 处勘误）

## B. 零触碰（真服务键面，F563 豁免对它们成立）

- 全部 `@sparkle_db:5432`/`POSTGRES_HOST=sparkle_db` 残留（docker-compose.yml 7、celery compose 2、Makefile 3、run_e2e_smoke 1、celery_acceptance 1、模板 8、`backend/alembic.ini`、`backend/create_test_user.py`、`scripts/devtools/create_test_user.py`、`backend/docs/ALIYUN_DEPLOYMENT_GUIDE.md:213`、`11_Docker配置详解.md` DB 行、CELERY_DEPLOYMENT_GUIDE:94）：`sparkle_db` 为 docker-compose.yml/celery compose 的服务键，网络内可解析
- `BACKEND_URL=http://sparkle_api:8000`、`AGENT_ADDRESS=sparkle_agent:50051` 等：`sparkle_api/sparkle_agent/sparkle_gateway` 均为服务键（键名未分化），可解析
- `sparkle_redis_data/sparkle_minio_data/sparkle_postgres_data` 等：volume 键名，F563 红线（卷名不动），非 DNS

## C. 豁免登记（不动，逐项归因）

| 文件 | 归因 |
|---|---|
| `scripts/devtools/start_celery.sh`（8 处 URL 旧值） | **V3-FIX-577 卡面裁决域**：已标 DEPRECATED「body intentionally NOT repaired」，本卡仅按 F577R1-C2 转派在三处弃用指引补 caveat，脚本体维持不修（防双改冲突） |
| `backend/tests/unit/test_redis_fixture_isolation.py`（2）、`backend/tests/unit/test_phase0_production_hardening.py`（1）、`backend/tests/unit/test_tracing_export_config.py`（1）、`backend/test_fv06_rbac_contract.py`（7）、`backend/gateway/internal/config/config_rbac_test.go`（4） | 测试夹具/契约断言：URL 字符串为解析逻辑输入样本，非 DNS 消费；本卡回归实测全绿（24 passed / go config ok） |
| `k8s/base/secrets-and-configmaps.yaml`（2，`@sparkle_db:5432`） | k8s DNS 自成体系，与 compose 网络无关；base manifests 未定义同名 Service（疑整体陈置）——非 celery 路径，超本卡面，留 k8s 卡核 |
| `docs/engineering/SECURITY_RBAC_2026-05-02.md`（7） | 2026-05-02 时点安全规格史录（含 RBAC 角色命名），非操作手册 |
| `v3/**`（DYNAMIC_ISSUES.md、.sparkle_v3_fleet_state.json）、`v3-output/**`（5 文件）、`v4/evidence/FIX-563/**`（3）、`v4/evidence/V4-B06/env_redacted_snapshot.txt` | 冻结历史/台账叙述/证据快照，写作时点实录 |
| `docs/03_功能实现指南/CELERY_DEPLOYMENT_GUIDE.md:94` 的 `@sparkle_db:5432` | 服务键面（B 类），该文件其余 28 处旧名已修 |

## D. 遗留登记（本卡发现、不修，建议后续派卡核）

1. **prod compose db 服务键=`db`**（容器 `sparkle_proj_db`，别名 {db, sparkle_proj_db}）：`sparkle_db:5432` 在 **prod 栈**网络不可解析；`.env.production.example` 的 DATABASE_URL 族若喂 prod compose（blue/green）则同族悬空。消费流（prod compose vs Aliyun docker-compose.yml 单栈）未在本卡取证范围内证实，越面改动风险大于收益——登记待 prod 部署卡核。
2. **k8s base manifests 陈置嫌疑**：`sparkle_db` 在 k8s/base 无对应 Service 定义（C 表第 3 行），若 k8s 面仍活则 DATABASE_URL 悬空，随 k8s 卡核。
3. **`11_Docker配置详解.md:36` `grpc://sparkle_backend:50051`**：`sparkle_backend` 非 compose 服务键（主栈为 sparkle_agent/镜像名 sparkle_backend 混写），文档示例陈旧疑误；非本卡三模式家族，未顺手修（登记）。
4. **celery compose standalone 的 OTEL `tempo:4317`**：standalone 面无 tempo 服务可解析（修前 `sparkle_tempo` 同样不可解析，非劣化）；standalone 部署本就依赖主栈可观测面，随 compose 结构卡（如有）一并裁决。
