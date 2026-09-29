# FIX-563 run_manifest — compose 容器名单侧分化（根除跨仓 ops 误击）

- 执行：FIX-563 fleet 修复 agent（worktree `wtF563`，分支 `fix/v4/f563-container-differentiation`，基点 main@`0949da60`，本地 main 领先 origin/main 12 个 state 提交故取本地 main）
- 日期：2026-09-29 10:20–11:10 (+0800)
- 登记来源：P03 二审 C-4 归属裁决（`v4/evidence/V4-P03/review_r2.md` §5）+ 台账 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` V3-FIX-563 行；承接 FIX-557 台账「长期修法=两仓 compose 容器名分化」
- **不 push**（按派单红线）

## 0. 缺陷与修法

两仓（Sparkle-project / sparkle-cosmos）compose 的 `container_name` 全部同名（`sparkle_db`/`sparkle_redis`/`sparkle_minio`/`sparkle_api`/`sparkle_agent`/`sparkle_gateway`/`sparkle_age_init`/`sparkle_celery_beat`/`sparkle_tempo`/`sparkle_prometheus`/`sparkle_alertmanager`/`sparkle_loki`/`sparkle_promtail`/`sparkle_grafana` 等，docker-compose.yml 14 个全碰撞；celery/services/prod 变体亦然）。容器名是 Docker 全局命名空间，先到先得：从错误仓 `up` 会在灭失窗口静默抢注同名容器并挂对方项目前缀的空卷（FIX-557 实战事故）。修法=本仓 `container_name` **单侧分化**加 `_proj_` 中缀（`sparkle_*`→`sparkle_proj_*`），volume 名本就 project 前缀分化（`sparkle-project_*` vs `sparkle-cosmos_*`）零迁移；分化后本仓再怎么 up 创建的都是唯一名容器，与对仓容器/卷无碰撞面——事故形态被根除而非拦截。

## 1. 改动清单（56 文件 = 54 改 + 2 新增，按类）

### compose（4 文件，44 个 container_name）
- `docker-compose.yml`（14）、`docker-compose.celery.yml`（5）、`docker-compose.prod.yml`（22）、`docker-compose.services.yml`（3）：仅 `container_name:` 行 `sparkle_*`→`sparkle_proj_*`。**服务名/depends_on/容器内 DNS/`volumes:` 节一律未动**（数据面零迁移）。

### 预检门（2 文件）
- `scripts/dev/up.sh`：步骤 2 FIX-557 db 门重构为三数据面循环门（db/redis/minio 各查卷属主：`sparkle-cosmos_*` 挂本仓容器=die、`sparkle-project_*`=OK、absent=放行+legacy 卷 WARNING），原 `SPARKLE_ALLOW_RESTACK` 死锁语义随分化退役（absent+他仓卷不再危险）；新增 legacy 旧名容器在跑的 NOTE（端口冲突预警，不阻断不触碰）。步骤 3/4 exec 改新容器名。
- `scripts/ops/service_supervisor.py`：`DATA_CONTAINER`→`sparkle_proj_db`、`DATA_VOLUME_OWNER_PREFIX`→`sparkle-project_`；owner 预检语义按分化反转（本仓卷=绿、他仓卷挂本仓容器=红、absent=绿带注记——唯一名不可能遮蔽他卷）；`check_data_plane_services` 两 exec 改新名。

### 脚本/工具（18 文件）
- `scripts/dev/`：`healthcheck.sh`（2 exec+minio 探测锚定）、`smoke.sh`（dash 形旧债 `sparkle-db`/`sparkle-redis`→新容器名，P03-R2 登记债收口）、`logs.sh`（服务名/容器名分轨 PAIRS 重构，同修 dash 旧债）
- `scripts/dev_local_stack.sh`（3 wait_for_container_health）、`scripts/dev-stage3.sh`（数据面在位门改为两仓栈任一可接受）、`scripts/run_e2e_smoke.sh`（5 wait_for_container）
- `scripts/backup_prod_data.sh` / `restore_prod_data.sh`（默认容器名 ×6）、`scripts/install_backup_cron.sh`（提示文本）、`scripts/deploy/bootstrap.sh`（计划文本精确化）
- `scripts/devtools/`：`acceptance_memory_revival.py`、`bench_ai_stack_l0_l3.py`、`bench_v4_q04_e2e_latency_cost.py`、`journey_harness/harness/evidence.py`、`q06_perf_bench.py`、`q06_provider_chaos.py`、`run_j01_first3_measurement.sh`、`setup_env.sh`、`start_celery.sh`、`v4_u11_two_account_scenario.py`（容器名常量/exec/探测；URL 内 DNS 全部保留）
- `backend/scripts/celery_acceptance.py`（`BEAT_CONTAINER`）、`tool/e2e/collect_logs.py`（dash 形旧债改服务名）

### Makefile（1 文件）
- `DB_CONTAINER`→`sparkle_proj_db`；celery 手工栈 `docker run --name`/`logs`/`stop`/`rm` ×14 处与 docker-compose.celery.yml 新名对齐；URL 内 `@sparkle_db:5432`/`@sparkle_redis:6379` DNS 保留。

### 测试（1 文件）
- `scripts/tests/test_service_supervisor.py`：owner 预检用例按 FIX-563 语义矩阵重写（本仓卷绿/他仓卷红+note 断言/absent 绿带注记/真机 absent 分支），docstring 第 5 条同步。

### 监控（9 文件 = 7 改 + 2 新增）
- `monitoring/prometheus.yml`：`sparkle_agent_grpc` static「prod 容器名与 dev 服务名同名通吃」前提随分化失效，改 file_sd（job_name 不变，告警/面板零连锁）
- 新增 `monitoring/targets/dev/agent.yml`（服务名 sparkle_agent）/`monitoring/targets/prod/agent.yml`（新容器名 sparkle_proj_agent）——循本文件既定「挂载面即形制开关」教义
- `monitoring/prometheus-celery.yml`（2 容器名 DNS target）、`monitoring/promtail-config.yaml`（2 container selector）、`monitoring/celery_alerts.yml`（runbook 提示）、`monitoring/grafana-dashboards/sparkle-data-services.json`（job 正则补新名，JSON 校验过）、`monitoring/targets/{dev,prod}/backend.yml`（注释更新）

### 文档（17 文件）
- `scripts/RESTACK_RUNBOOK.md` 重写：两仓容器名对照表（权威）、「永远先 `-p` 显式 project 名」纪律、**容器名变更只在下次（重）创建时生效——在跑旧容器不被触碰**注记、端口冲突预期、FIX-557 事故复盘保留为史录、纠偏步骤适配双仓
- live 运维文档 16 件容器名同步：`scripts/README.md`、`scripts/devtools/README.md`、`docs/ops/disaster_recovery_runbook.md`、`docs/05_部署与运维/{ENV_SETUP_GUIDE,RUNBOOK_SEMANTIC_CACHE_VERIFICATION,backend_ALIYUN_DEPLOYMENT_GUIDE,mobile_真机调试指南}.md`、`docs/03_功能实现指南/QUICK_START_CELERY.md`、`docs/02_技术设计文档/11_Docker配置详解.md`（表格改双列：服务名+分化后容器名+分化注记）、`backend/{COMMANDS_QUICK_REFERENCE,EXECUTION_GUIDE}.md`、`backend/docs/{EVENT_OUTBOX_MIGRATION,REAL_DEVICE_INTEGRATION_TEST}.md`、`mobile/docs/REAL_DEVICE_DEBUG_GUIDE.md`、`backend/.env.local.example`、`mobile/integration_test/j02_fastpath_journey_test.dart`（§5 注释）

### 豁免（不改，清单见 `grep_exemptions.md`）
服务名/DNS 引用（`.env*`、alembic.ini、k8s configmaps、settings/config.go、后端测试 URL、compose 子命令、guards 服务名解析）、历史记录（v3-output/**、v4/evidence 既有件、docs/competition/**、v3 fleet state/handover、dated 手册、backend 修数注释）。

## 2. 约束执行情况

- **未动任何运行中容器**：全程零 `docker compose up/down/restart`、零 `docker stop/start/rm`；对 Docker 的全部接触=`docker ps/inspect/volume ls`（只读）+`docker compose config`（静态渲染）。容器名变更在下次自然（重）创建时生效——已写入 RUNBOOK 注记。
- **volume 名零改动**：4 个 compose 的 `volumes:` 节逐字节未动；无数据迁移。
- **零跨仓写入**：sparkle-cosmos 仓全程只读（对照碰撞面时 grep）；本 worktree 之外仅读主仓 venv 的 pytest/pyyaml。
- **不 push**：分支止于本地。
