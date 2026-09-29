# FIX-563 grep 豁免清单

改后全仓 grep 旧容器名家族（`sparkle_db|sparkle_redis|sparkle_minio|sparkle_api|sparkle_agent|sparkle_gateway|sparkle_age_init|sparkle_celery*|sparkle_tempo|sparkle_prometheus|sparkle_alertmanager|sparkle_loki|sparkle_promtail|sparkle_grafana` 及 dash 形）残 1073 行，逐类归因如下。**可执行容器操作 + 旧名 = 0**（verification.md §2）。

## A. 服务名 / 容器内 DNS 引用（设计上不改：FIX-563 只动 container_name，服务名两仓均未分化）

服务名是 compose 服务键、depends_on 键、compose 子命令参数、user-defined 网络的 DNS 名——改了反而破坏运行面。

- `.env.example` / `.env.deploy.example` / `.env.production.example` / `backend/.env.example` / `backend/gateway/.env.example` / `backend/alembic.ini`：`POSTGRES_HOST=sparkle_db`、`@sparkle_db:5432`、`@sparkle_redis:6379` 等 host 配置
- `backend/app/config/settings.py`（host 白名单与默认值）、`backend/gateway/internal/config/config.go` + `config_rbac_test.go`（viper 默认/host 判别）、`backend/tests/`（conftest hostname 判别、URL 夹具、x05b/q06/quota 注释）、`backend/test_fv06_rbac_contract.py`、`backend/create_test_user.py`、`backend/scripts/celery_acceptance.py` URL 常量、`backend/app/core/{rate_limiting,business_metrics,metrics}.py`（sparkle_agent_* 为 metric 名与内网降级 URL）、`backend/app/api/v1/vocabulary.py`、`backend/app/services/{guest_seed,inventory}_service.py`（wt766 史注）、`backend/gateway/cmd/server/setup.go`、`backend/alembic/versions/c17_*_create_service_roles.py`（DB 角色名 sparkle_gateway 等，非容器）
- compose 内部：`docker-compose.yml` 服务键/depends_on/env `AGENT_ADDRESS=sparkle_agent:50051` 等、`docker-compose.celery.yml` OTEL endpoint `sparkle_tempo:4317`、`docker-compose.prod.yml` volume 键（`sparkle_*_data`，卷名不动）与注释（dev 服务名指涉）
- `k8s/base/secrets-and-configmaps.yaml`（k8s 内 DNS）、`scripts/chaos_drill.sh`（全 compose ps/unpause 服务名）、`scripts/production_readiness_check.sh`（compose ps 服务名）、`scripts/dev_local_stack.sh`/`scripts/devtools/setup_env.sh`/`scripts/dev/up.sh`/`Makefile:26`（compose up 服务名）、`scripts/run_e2e_smoke.sh`（compose up/exec/logs + env host）、`scripts/deploy/bootstrap.sh`（prod 服务 db/redis）、`scripts/guards/check_rule_bn_prod_db_age_parity.py`（compose 服务名解析）、`.github/actions/age-postgres/action.yml`、`.github/workflows/{ci,e2e-tests}.yml`（sparkle_age_init=服务名/CI 服务注释）、`Makefile` celery docker run 的 `-e …@sparkle_db:5432`（网络内 DNS）
- 监控 job/面板名：`monitoring/sparkle_slo_alerts.yml`、`sparkle_production_baseline_alerts.yml`、`grafana-dashboards/sparkle-api-health.json`、`sparkle-production-admin-ops.json`（job 标签，非容器名）、`monitoring/targets/dev/{gateway,backend}.yml` targets（服务名 DNS）
- `mobile/lib/.../community_agent_provider.dart`（`sparkle_agent` 为社区账号常量，与容器无关）、`backend/test_session_id.py`/`test_websocket_client.py`/JWT issuer `sparkle-gateway`、`scripts/loadtest/*`（issuer）、`scripts/deploy_k8s.sh`+`k8s/`（k8s 资源名 sparkle-gateway，非 compose 容器）、`docker-compose.prod.yml` 镜像名 `sparkle-gateway`（ghcr image）

## B. 历史记录 / 证据 / 冻结工件（只读史实，按写作时点指旧名；RUNBOOK 对照表注明换算）

- `v3-output/**`（全部 REPORT/REVIEW/patch/复现件，含 WT784 first3minutes.sh、WT815-F556 等冻结工件）
- `v4/evidence/**` 既有件（V4-P03/V4-B04/V4-B06/V4-U11/V4-Q03/V4-Q04/FIX-571 run_manifest 等对当时在跑容器名的实录）；本卡新证据除外
- `v3/`：`06_agent_fleet/DYNAMIC_ISSUES.md`（V3-FIX-557/563 行的事故叙述——状态字段本卡更新，叙述保留）、`TEAM_HANDOFF.md`、`HANDOVER-20260925.md`、`09_evidence/j01_*`、`.sparkle_v3_fleet_state.json`
- `v4/00_context/source_notes/S18-S20`、`v4/READING_ROOM.html`
- `docs/competition/**`（多端实测/接力日志/系统审查 round1-round2/大创市赛）、`mobile/docs/competition/**`
- dated 手册与总结：`docs/05_部署与运维/全环境全链路部署启动对齐手册_2026-03-19.md`、`服务器全套环境与服务配置指南_2026-03-31.md`、`production_deployment_guide.md`（唯一命中为 compose up 服务名，A 类）、`backend/DATA_PIPELINE_REPAIR_SUMMARY.md`、`docs/03_功能实现指南/CELERY_DEPLOYMENT_GUIDE.md`（URL DNS，A 类）、`docs/engineering/SECURITY_RBAC_2026-05-02.md`、`docs/engineering/db_migration_rollback_plan.md`（compose start 服务名，A 类）
- `scripts/ops_rollback_smoke.py:117`（wt771 实录注释）、`backend/DATA_PIPELINE_REPAIR_SUMMARY.md`

## C. 本卡故意写入的旧名提及（跨仓注记/对照表/语义说明）

- `scripts/RESTACK_RUNBOOK.md`：对照表列 sparkle-cosmos 侧旧名、09-28 复盘、历史文档换算注记
- `scripts/dev/up.sh`：门注释（两仓名对照）、legacy 在跑 NOTE、步骤 4 注释（旧债沿革）
- `scripts/dev/smoke.sh` / `logs.sh` / `tool/e2e/collect_logs.py`：dash 形旧债收口注记
- `scripts/dev-stage3.sh`：`grep -qx sparkle_db` 分支=**故意接受 cosmos 栈在位**（双仓任一可跑）；提示文本列两仓名
- `scripts/ops/service_supervisor.py`：absent/误挂语义注释（旧名沿革）
- `scripts/ops_rollback_smoke.py` 上游 `up.sh` 语义连锁注释（A/B 类边界，实为 B）
- `backend/.env.local.example`、`mobile/integration_test/j02_fastpath_journey_test.dart`：新旧名换算注记
- `docs/02_技术设计文档/11_Docker配置详解.md`：分化注记（服务名列+新容器名列并列）
- `monitoring/grafana-dashboards/sparkle-data-services.json`：job 正则显式并列旧名（`sparkle_db|sparkle_proj_db`，兼容未重建窗口）
- `monitoring/targets/{dev,prod}/agent.yml`、`prometheus.yml` 头注：分化前 static 同名通吃前提的沿革说明
- `v4/evidence/FIX-563/**`：本卡证据自身
