# CI-AGE 任务报告：CI 数据库镜像 AGE 对齐 + 部署指南陈旧段修复

> 2026-09-22 ｜ wt96（基于 main@fd85f9b5）｜ 交付 `changes.patch`（4 文件，+~460/-~500），禁 commit/push
> 兑现 D-AGE 报告遗留清单 #7（CI 6 处裸 pgvector）与 #8（ALIYUN_DEPLOYMENT_GUIDE.md:254 陈旧段）

## 一、6 处裸镜像的对齐方式与论证

### 基线（改动前）

| # | 位置 | 现状 |
| --- | --- | --- |
| 1 | `.github/workflows/ci.yml:150`（backend-test） | `services.postgres` = 裸 `pgvector/pgvector:pg16`，无任何 AGE init |
| 2 | `.github/workflows/ci.yml:328`（simulation-benchmark） | 同上（DB `sparkle_simulation_ci`） |
| 3 | `.github/workflows/ci.yml:491`（db-schema-check） | 同上（DB `sparkle_ci`） |
| 4 | `.github/workflows/e2e-tests.yml:25`（python-e2e） | 同上（DB `sparkle_test`） |
| 5 | `.github/workflows/e2e-tests.yml:113`（go-e2e） | 同上 |
| 6 | `.github/workflows/e2e-tests.yml:216`（fullstack-e2e） | 同上（DB `sparkle`） |

危害确认：`backend/tests` 图谱链路全部 mock cypher（`test_graph_rag.py:62`），CI 从未对真 AGE 跑过图谱（假绿）；root `tests_e2e/test_galaxy_e2e.py` 属真图谱 E2E；gateway 侧 `galaxy_sync.go` worker 消费 AGE。

### 选型：a（CI 内 build 同一 Dockerfile）+ GHA cache，弃 b/c

- **机制硬约束**：GHA `services:` 在 job 任何 step 之前启动，**不可能"先 build 再让 service 用"**。因此选 a 必然把 service 容器改为 **step 托管容器**（build → `docker run` → 健康等待 → init step），这正是卡面"CI services 不支持多命令时给 init step"的彻底形态。
- **弃 b（GHCR 预发布镜像）**：①按卡面规则先验证匿名 push——GHCR push 永远需要认证，**不可行，触发降级条款**；②即使加 publish job，首次发布包默认 **private**，而 services 无法先 `docker login` 再拉取（services 先于 step），private 包 service 拉取必死，改 public 需仓库外手动 UI 操作（本仓无 GHCR 凭证配置，gitleaks 步注释亦自证 personal repo）；③引入第二分发渠道（漂移/pin 管理成本），且 prod 实际消费的是本地 build（`sparkle/pgvector-age:pg16`），GHCR 无人消费。
- **弃 c（复用 buildx cache 的变体）**：与 a 同为 in-job build，仅缓存机制差异；`cache-from/to: type=gha` 就是 buildx 官方 GHA 缓存后端，无更优空间。
- **落地形态**：新增复合 action `.github/actions/age-postgres/action.yml`（单一事实源引用 `docker/pgvector-age.Dockerfile`，`AGE_REF=PG16/v1.6.0-rc0` 与 dev/prod compose 及 Rule BN 口径一致；`load: true, push: false, cache-from/to: type=gha,mode=max`），6 个 job 统一 `uses: ./.github/actions/age-postgres`，杜绝 6 处复制粘贴。冷构建约 5-8 分钟（AGE 源码编译），命中 GHA cache 后近秒级恢复。

### 逐 job 落点（改动后）

| Job | 对齐方式 | 特殊处理 |
| --- | --- | --- |
| backend-test | service → action（step 托管） | 依赖安装后追加 **dev 同款 one-shot init**（见下节） |
| simulation-benchmark | 同上 | action 挂 `if: run_benchmark == 'true'`——基准确需运行才 build/起容器（比原 service 无条件常驻更省） |
| db-schema-check | 同上，但 **`age-init: none`** | 刻意不装 age 扩展：本 job 对比的是 fresh 迁移链终态 pg_dump（Makefile R2-08-06 口径，schema.sql 已核验只含 pgcrypto+vector、无 AGE 对象），预装 age 会制造 dump 假漂移。镜像级对齐仍保留（同源 .so 在库） |
| python-e2e | 同上 | 见下节 init 顺序；顺带修了 setup-db 的两处既有缺陷（见"顺带修复"） |
| go-e2e | 同上（extensions 级） | galaxy_sync worker 消费 AGE；Go job 无 Python 依赖，不做 one-shot |
| fullstack-e2e | 同上 | DB 名从 `sparkle` 统一为 `sparkle_test`（容器首启即建，与后续 DATABASE_URL 一致） |

## 二、AGE init 在 CI 的对齐方式

dev 参照 = `sparkle_age_init` one-shot 跑 `backend/scripts/init_age_extension.py`（两部分：① `ensure_database_extensions(("vector","age"))`；② 建 `sparkle_galaxy` 图谱 + 基础 vertex/edge label）。CI 对齐为两层：

1. **扩展层（全部 6 job）**：action 内 `docker exec psql` 执行 `CREATE EXTENSION IF NOT EXISTS vector/age`（等价于 `app/main.py:465` lifespan 的扩展自举半边），无需 Python 依赖即可用。
2. **图谱层（backend-test / python-e2e / fullstack-e2e，凡有 Python 依赖且真正吃 DB 的 job）**：逐字跑 dev 同一份 one-shot——`python backend/scripts/init_age_extension.py`，`DATABASE_URL` 用 asyncpg scheme 对齐 dev compose 写法。该脚本失败即 `exit 1`，与 prod `db_age_init` 同等严格度（真红优于假绿）。
3. **顺序对齐 dev**：先图谱 init 后 alembic（dev 是 `sparkle_age_init` 随 `compose up` 先行、迁移由 `make sync-db` 后行）。python-e2e/fullstack-e2e 中 one-shot 均置于 `alembic upgrade head` 之前。

**顺带修复（同一 init 对齐的必要前提，共 3 处）**：
- e2e-tests.yml 两处 `psql -U sparkle` 不带 `-d` 会连去不存在的 "sparkle" 库（官方 postgres 镜像只建 `POSTGRES_DB`）——删除多余的 DROP/CREATE（容器首启已建库，重置反而把刚做的 AGE init 清掉）；
- workflow 级 `POSTGRES_DB: sparkle` 与实际库名不符 → 统一 `sparkle_test` 并加注释。

## 三、文档修复清单（`backend/docs/ALIYUN_DEPLOYMENT_GUIDE.md`，共 12 处）

| # | 位置（改后行号） | 陈旧点 → 修复 | 依据（main 现状） |
| --- | --- | --- | --- |
| D1 | L38-44 | 推荐 2核/4G → 内存 ≥8G/磁盘 ≥20G，与 bootstrap 资源门对齐 | `scripts/deploy/bootstrap.sh` `MIN_DISK_MB=20480 / MIN_MEM_MB=7168` |
| D2 | L46-61 | 手装 docker-compose v1 独立二进制 → `get.docker.com` 自带 compose v2 插件 + `docker compose version` 验证 | bootstrap.sh `compose()` 全用 `docker compose` |
| D3 | L70-77 | 安全组放行 5432 到 0.0.0.0/0（与自身警告矛盾）→ 移除该行，改为禁止开放 + SSH 隧道口径 | prod compose `db` 无 ports；全部非 nginx 端口仅 127.0.0.1 绑定 |
| D4 | L190-222 | 手写 `.env.production` 模板（OPENAI 主力、POSTGRES_* 键名、HS256）→ 指向真实模板三件套 + `[MUST CHANGE]` 校验门 + 模型现状 | `.env.production.example`（DATABASE_URL L67/DB_* L71-73/IMAGE_TAG L382-384）、`backend/.env.example` L72-75（`LLM_PROVIDER=qwen` + dashscope）、L111-117（MiniMax batch）、L119-134（GLM 保留条目：OCR/免费层不受影响）、`scripts/check_production_secrets.py` |
| D5 | L224-252 | **核心陈旧段（原 :254）**：手改 compose 内嵌裸 `pgvector/pgvector:pg16` + 不存在的服务名 → 整段重写为 prod compose 现实：AGE 同源构建 + one-shot 链 + GHCR 镜像 + bootstrap 入口 | `docker-compose.prod.yml` db/db_migrate/db_age_init（D-AGE@3c6c1d82）、Rule BN 守卫、`Makefile` cloud-up/cloud-plan |
| D6 | L254-279 | `docker-compose exec sparkle_api alembic upgrade head` + 陈旧 head `5f2b9b3c0e6f` + 引用已不存在的 `SessionLocal` 的管理员脚本 → one-shot 日志验证 + `alembic current` + AGE 就绪探针；文档不再钉死 head 号 | 当前 head `x07_20260921`（本机对迁移链实算）；`app/db/session.py` 仅 `AsyncSessionLocal` |
| D7 | L307-334 | AndroidManifest meta-data / Xcode User-Defined 注入（虚构机制）+ 不存在的 `mobile/lib/core/config/api_config.dart` → 唯一机制 `--dart-define` + 真实文件 `mobile/lib/core/constants/api_constants.dart`（节选） | `rg API_BASE_URL mobile/android` 无命中；api_constants.dart L5/L26-38 |
| D8 | L336-342 | axios/config.js 的 JS Web 应用（不存在）→ Flutter Web `--dart-define` | 仓库无 JS 前端；api_constants 有 kIsWeb 分支 |
| D9 | L105-112 | 宿主机手装 nginx 占 80/443 → 标注 compose 内置 nginx 已占 80/443、TLS 容器内终结、勿再宿主安装；旧手配降级为参考 | prod compose nginx `ports: 80/443` + `./nginx/nginx.conf` + `${SSL_CERT_DIR:-./ssl}` |
| D10 | L345-386 等 | §8 验证/监控/备份/故障排除的 v1 `docker-compose` 命令与 `sparkle_gateway/sparkle_api/postgres` 服务名 → v2 `docker compose -f docker-compose.prod.yml` + 真实服务名（gateway_blue/green、backend、db）；备份脚本改 `db` + `DB_USER/DB_NAME` | prod compose 服务清单；`scripts/deploy-prod.sh`（IMAGE_TAG 必填、蓝绿 upstream.conf） |
| D11 | L368-386 | 自建 deploy.yml（appleboy + build + 手动 alembic）→ 现实发布链：CI build job 推 GHCR + `scripts/deploy-prod.sh` 蓝绿 + bootstrap 首部署 | ci.yml build job（GHCR push@main/tag）、deploy-prod.sh L1-40 |
| D12 | L177-188 | 克隆 `sparkle-flutter.git` 占位仓库名 → `Sparkle-project` + 注明必须克隆到仓库根（build context 依赖） | 仓库实际名称；prod compose `build.context: .` |

## 四、验证证据

- **YAML 解析**（uv+pyyaml）：`ci.yml` / `e2e-tests.yml` / `.github/actions/age-postgres/action.yml` 全部 `safe_load` 通过；断言两 workflow 已无任何 postgres service 容器；action `using: composite`、5 steps、6 inputs 结构正确。
- **actionlint 1.7.7**（官方 release 二进制）：对全部 workflows + 复合 action **exit 0 零告警**（含 `uses: ./.github/actions/age-postgres` 引用与 inputs 匹配校验）。
- **Rule BN 守卫**：`python3 scripts/guards/check_rule_bn_prod_db_age_parity.py` → `RULE BN OK`（本次零触碰 compose 三件套与 Dockerfile）。
- **裸镜像清零**：`rg "image: pgvector"` 全仓 `.github/` 零命中；残留 3 处 `pgvector/pgvector:pg16` 字样均为注释/文档中的历史指称（ci.yml:158、action.yml:7、guide:227）。
- **Patch 自洽**：`git apply --reverse --check changes.patch` 通过（patch 与 HEAD→worktree 增量严格一致，Leader 可直接对 main `git apply`）。
- **文档逐处依据**：第三节表格右列逐一给出 main 现状锚点；代码围栏 46 处配平；全文无残留 v1 `docker-compose` 命令。
- **根因核验**：迁移链实算单 head（`x07_20260921`）；`schema.sql` 无 AGE 对象（支撑 db-schema-check 的 `age-init: none` 决策）；`init_age_extension.py` 失败路径 `sys.exit(1)`。

## 五、诚实申报：留待下次 push 后观察的点（本卡 LIGHT，未真跑 CI/未 build 镜像）

1. **AGE 镜像冷构建时长**：首跑约 5-8 分钟（apt build 工具链 + AGE 源码编译）；GHA cache 命中后应近秒级。若超过 job 预算（backend-test 40m）需再议。
2. **`init_age_extension.py` 在 CI 的首跑表现**：需要 backend 全量依赖可导入（与 pytest 同链路，风险低）；若红，属真红——看 `docker logs`/step 日志定位是依赖还是 AGE 会话语义（`LOAD 'age'`）问题。
3. **backend-test 是否因 AGE 可用而翻出新红**：图谱相邻代码从降级路径切到真实路径（`is_database_extension_available("age")` 翻转）是本卡的预期效果，翻红即"假绿"修复，按新事实处理。
4. **db-schema-check 的 dump diff**：预期与改动前逐字节一致（AGE 镜像不改变迁移链终态 dump）；若出现 age 相关 diff 即我对迁移链的判断有误，回滚该 job 的镜像对齐并重查。
5. **e2e-tests.yml（paused, workflow_dispatch）**：手动触发验证；另有两处**申报未修**的相邻既有缺陷——`cd backend && pytest tests_e2e/` 路径不存在（tests_e2e 在仓库根），以及 codecov `fail_ci_if_error: true` 的凭证依赖。属路径级错误修复，超出本卡"镜像+init 对齐"边界，建议另开小卡。
6. **GHA cache 占用**：AGE 镜像层约数百 MB 进 10G repo cache 池，与既有 build job 的 gha cache 共存，量级无虞。

## 六、收工核查声明

- [x] 一切修改仅在 wt96 内；主仓只读，未在仓库根/家目录/共享目录创建任何文件
- [x] 未 commit / 未 push；产物仅 `v3-output/CI-AGE/changes.patch` + `REPORT.md`（随 worktree 生命周期）
- [x] 红线未触碰：`docker/pgvector-age.Dockerfile`、`docker-compose.prod.yml`、`docker-compose.celery.yml`、`docker-compose.yml` 零改动（git status 佐证：仅 2 个 workflow + 1 个文档 + 新增 action 目录）
- [x] 未引入任何密钥/凭证（CI 用公开镜像 pull + 本地 build；文档示例全部占位符）
- [x] /tmp 自清：actionlint 二进制与 tarball 已删（见收工命令）；无其他 /tmp 产物、无进程残留、未动 Docker/模拟器（LIGHT 任务）
- [x] 树操作合规：全程未 stash/reset/clean/切分支，`git status --short` 前后比对一致（3 modified + 2 untracked 交付物）
