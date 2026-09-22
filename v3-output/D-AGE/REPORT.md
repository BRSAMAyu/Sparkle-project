# D-AGE 任务报告：修复 prod PostgreSQL 缺 Apache AGE 导致星图断链（P0）

> 2026-09-22 ｜ wt87（基于 main@3fdd34bd）｜ 交付 `changes.patch`（4 文件，+383/-12），禁 commit/push

## 根因

- `docker-compose.prod.yml` 的 `db` 用裸 `pgvector/pgvector:pg16`（无 AGE），且 prod 链上没有任何 AGE 初始化步骤；星图（知识图谱）在生产直接不可用。
- dev 侧（`docker-compose.yml`，`make dev-up`）是正确参照：`sparkle_db` 从 `docker/pgvector-age.Dockerfile` 构建（PG16 + pgvector + AGE `PG16/v1.6.0-rc0`），并有 one-shot 服务 `sparkle_age_init` 跑 `backend/scripts/init_age_extension.py`（`CREATE EXTENSION vector/age` + 建 `sparkle_galaxy` 图谱与基础 label）。
- 诊断出处：`v3-output/DL-D-R1/CLOUD_DEPLOY.md` 缺口 #1（P0），其给定的正式修复方向（prod db 改 build pgvector-age + init 进流程）与本 patch 一致。

## 改动

| 文件 | 内容 |
| --- | --- |
| `docker-compose.prod.yml` | ① `db`：`image: pgvector/pgvector:pg16` → 与 dev 同源 `build`（`docker/pgvector-age.Dockerfile`，`AGE_REF: PG16/v1.6.0-rc0`），产物 tag `sparkle/pgvector-age:pg16`（与 CLOUD_DEPLOY 手工兜底命令的 tag 一致，预构建镜像可直接命中不重建）；② 新增 one-shot `db_age_init`（复用 `db_migrate` 模式：backend 镜像 + `python scripts/init_age_extension.py`，depends_on `db` healthy → `db_migrate` completed，`SERVICE_ROLE=age-init`，256M 限额）；③ `backend`/`agent`/`celery_worker`/`celery_glm_batch_worker`/`celery_beat` 五个消费方 `depends_on.db_age_init: service_completed_successfully` |
| `docker-compose.celery.yml` | `sparkle_db` 同样的裸 pgvector → 同源 build（同款次生 bug 一并修，避免 celery 独立栈复活该问题） |
| `scripts/guards/check_rule_bn_prod_db_age_parity.py` | 新守卫（纯标准库、缩进解析 compose）：dev 源真值校验 + prod db 禁裸 pgvector/必须同 dockerfile 同 AGE_REF 同 context + `db_age_init` 存在性/命令/镜像同 db_migrate/依赖链 + 五消费方依赖 + celery 栈。违规码 BN001-BN042；支持 `--prod/--dev/--celery` 覆盖路径（用于基线回归演示） |
| `scripts/rule_guard_manifest.tsv` | 登记 `BN` 行（BM 之后），进 `run_all_rule_guards.sh` |

单一事实源：prod/celery 均引用 dev 同一 `docker/pgvector-age.Dockerfile`，未复制 Dockerfile。未引入新机制：init 走既有 `db_migrate` one-shot 模式，脚本用 dev 同一份 `init_age_extension.py`（backend 镜像 `COPY . .` 自带 `scripts/`，Alembic 仍是 schema 唯一入口，AGE init 只做 extension/graph，先迁移后 AGE）。

## 验证证据

- `docker compose -f docker-compose.prod.yml config -q`：**通过**（补齐既有 `:?` 必填哑变量：IMAGE_TAG/TRUSTED_PROXIES/ALLOWED_ORIGINS/ALERTMANAGER_*/GRAFANA_*/MINIO_ROOT_*；这些必填项与本次改动无关，真机由 .env 提供）。渲染确认 `db` build context/dockerfile/AGE_REF 正确、`db_age_init` 依赖链与资源限额正确。
- `docker compose -f docker-compose.celery.yml config -q`：通过。
- dev：`docker-compose.yml` 本 patch 零改动（`git status` 佐证）；在 /tmp 沙箱（同内容文件+哑 .env，规避 `sparkle_age_init` 的 `env_file: .env` 既有要求）`config -q` base 与 base+dev overlay 均 exit 0，无回归。
- 守卫：当前树 `RULE BN OK`（直接跑 + `run_all_rule_guards.sh --rule BN` 均绿）；对 HEAD 旧版两份 compose（拷贝至 /tmp）跑出 BN010/BN011/BN020/BN031×5/BN041/BN042 全部命中、exit 1（守卫确实能抓回归）。邻位 BM/DB-HEAD 经 runner 仍绿（manifest 改动无损）。
- compose 相关仓库测试：检索 tests_e2e/backend tests，无 compose 配置校验类测试可跑。

## 需真机部署验证清单（本机未起栈/未构建镜像，LIGHT 纪律）

1. `docker/pgvector-age.Dockerfile` 在目标服务器架构上构建成功（AGE 从源码编译，aarch64/amd64 均需过一遍；首次构建较慢）。
2. 已有 prod 数据卷（`./postgres_data` 存量数据）上 `CREATE EXTENSION IF NOT EXISTS vector/age` 实际生效；若原卷是裸 pgvector 镜像初始化的，AGE .so 由新镜像提供后扩展应可补装——需实测确认无版本/目录冲突。
3. `init_age_extension.py` 在 prod 卷上的幂等性（二次 `docker compose up` / `rm -rf sparkle_db_age_init` 后重跑：graph/label "already exists" 分支）。
4. `db_age_init` 失败时的行为符合预期（one-shot 失败 → 五个消费方不启动，故障可见而非静默断链）。
5. 真机 `docker compose -f docker-compose.prod.yml up -d db`（或 `up --build db db_age_init`）全链路 + `GET /api/v1/galaxy/*` 探针（CLOUD_DEPLOY.md §验证缺口 #1 的断言）。
6. 服务器侧需 git clone（build context `.` 指仓库根，`docker/` 目录必须在 checkout 内）——与 CLOUD_DEPLOY 缺口 #2 的 bootstrap clone 流一致。
7. CI 的 `pgvector/pgvector:pg16` service 容器（`.github/workflows/ci.yml`、`e2e-tests.yml` 共 6 处）仍是裸镜像，AGE 相关测试在 CI 会走降级路径——是否升级 CI 镜像属后续决策，未纳入本卡。
8. `backend/docs/ALIYUN_DEPLOYMENT_GUIDE.md:254` 文档内嵌 compose 片段仍是裸 pgvector（陈旧文档），建议接线 bootstrap 时顺手更正。
