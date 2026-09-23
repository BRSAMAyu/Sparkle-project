# D-DEPLOY 报告 — 云端一键部署就绪度研究与方案（纯研究零代码）

> 轮次：D 纵队 · 云端部署线 ｜ 2026-09-23 ｜ worktree wt185（基线 d2265244）
> 使命：商业化 + 云端一键部署中的「部署就绪度审计 + 可执行部署方案」。
> 边界申报：本轮零代码零测试零外部调用；所有 file:line 引用均在本 worktree 真实读文件核实；
> 所有成本数字均为**估算 + 时效（2026-09）**，无一手询价来源。
> 与既有卡的关系：本卡是 `v3-output/DL-D-R1/CLOUD_DEPLOY.md`（R1 方案稿）→ `D-AGE`（prod DB 镜像补 AGE）→ `D-BOOTSTRAP`（bootstrap.sh 一键流）之后的**就绪度复核与收尾缺口清单**，不是从零设计。

---

## 0. 结论速览（TL;DR）

1. **就绪度远超一般参赛项目，主线链路当日可上线**。`scripts/deploy/bootstrap.sh`（782 行，D-BOOTSTRAP 交付）+ `docker-compose.prod.yml`（22 服务）+ `make cloud-up` 已构成「git clone → .env 装配 → 镜像 → DB → 迁移 → AGE/向量初始化 → MinIO 桶 → 全栈 → readiness → chat 探针」的完整一键流；R1 稿的缺口 #1（prod DB 无 AGE）已被 D-AGE 关闭（prod db 现在构建自 `docker/pgvector-age.Dockerfile`，`docker-compose.prod.yml:547-552`）。
2. **剩余缺口集中在 5 处**（§2）：prometheus 抓取目标名与 prod 拓扑脱节（G1，P1）、备份未 cron 化/未异地（G2，P1）、无 4G 级精简 profile（G3，P1，仅当选 2C4G 档）、镜像国内拉取（G4，P2）、TLS 续期未自动化（G5，P2）。全部有 ≤1 天量级的最小解。
3. **推荐档位：档一 B（2C8G 单机 VPS，`--lean-observability`）**。理由：评委扫码可用 + 日活<百级的负载对单机绰绰有余；8G 恰好越过 bootstrap 的 7G 内存门（`bootstrap.sh:52` `MIN_MEM_MB=7168`）；现有脚本**零改动**可跑。2C4G 档需要新写精简 compose overlay（工作量 M，§3 档一 A 给出裁剪单）。
4. **国内合规流程项要提前 2-3 周启动**：域名 ICP 备案（国内云主机用域名对外必须备案，免费但流程性等待）。这是纯流程缺口，不写进代码也绕不过。
5. **安全面总评良好**：生产拓扑仅 nginx 暴露 80/443（唯一例外见 §5 G6 dev compose）；限流三层（nginx 区限速 + 网关混合限流 + Redis 分布式令牌桶）；.env 全家被 gitignore 且有占位门禁；成本红线（LLM 日预算/配额/GLM 批量道熄火）在 `.env.cloud.example` 全部钉死。

---

## 1. 现状盘点（真实文件证据）

### 1.1 本地开发栈（`docker-compose.yml`，15 服务）

| 服务 | 要点 | 证据 |
|---|---|---|
| sparkle_db | PG16 + pgvector + Apache AGE（`AGE_REF: PG16/v1.6.0-rc0`），数据在 named volume `sparkle_postgres_data`，**端口绑 127.0.0.1** | `docker-compose.yml:3-28` |
| sparkle_age_init | one-shot 跑 `backend/scripts/init_age_extension.py`（ensure vector+age） | `docker-compose.yml:30-52` |
| redis | redis-stack-server 7.4，`--requirepass`，maxmemory 512mb volatile-lru，绑 127.0.0.1 | `docker-compose.yml:54-73` |
| minio | 2025-09-07 release，9000/9001 绑 127.0.0.1，ROOT 凭据 `:?` 硬失败 | `docker-compose.yml:75-102` |
| sparkle_api | FastAPI，`RUN_MIGRATIONS=true`（entrypoint 里跑 alembic），健康探针 `/health` | `docker-compose.yml:104-203` |
| sparkle_agent | `python grpc_server.py`（:50051），健康探针是 TCP 连通 50051 | `docker-compose.yml:205-304` |
| celery_worker ×1 + glm_batch ×1 + beat ×1 | 队列清单见 §1.6 | `docker-compose.yml:306-435` |
| sparkle_gateway | :8080 —— **注意：唯一不绑 127.0.0.1 的端口**（`${SPARKLE_GATEWAY_PORT:-8080}:8080`），详见 §5 | `docker-compose.yml:437-497` |
| 可观测 6 件套 | tempo/prometheus/alertmanager/loki/promtail/grafana，全部绑 127.0.0.1 | `docker-compose.yml:499-641` |
| dev 裁观测 | `docker-compose.dev.yml` 用 profiles 把 6 个观测容器挂到 `monitoring` profile（自述省 ~1.5GB RAM） | `docker-compose.dev.yml:1-33` |

另有 `docker-compose.services.yml`（routing/learning/visualization 三个 8001-8003 微服务形制）与 `docker-compose.celery.yml`（独立 celery+flower 形制）——**均非主线部署形态**，盘点登记不展开。

### 1.2 生产栈（`docker-compose.prod.yml`，22 服务）

与 dev 的关键形制差异（全部为生产强化）：

- **边缘**：nginx 容器独占 80/443，TLS 证书挂载 `${SSL_CERT_DIR:-./ssl}`，与蓝绿网关同在 `edge` 网络；`docker-compose.prod.yml:101-124`
- **双网络隔离**：`edge`（nginx+网关）与 `app`（`internal: true`，:903-908）——db/redis/minio/backend/agent/观测栈**没有任何 ports 映射**，公网不可达；
- **蓝绿网关**：gateway_blue/gateway_green 同镜像双实例，切换由 `scripts/deploy-prod.sh` 改写 `nginx/upstream.conf` + reload 完成；
- **迁移 one-shot 化**：`db_migrate`（`alembic upgrade head`，:64-75）与 `db_age_init`（`scripts/init_age_extension.py`，:79-99）是 one-shot 服务，backend/agent/celery 全部 `depends_on: db_migrate/db_age_init: service_completed_successfully`（:316-324、:406-414 等）——**迁移时机 = 每次全栈 up 之前强制串行**；
- **Redis 三账号 ACL**：gateway/engine/celery 三组独立密码 + key 前缀白名单，禁 `@admin @dangerous`（:588-618；`redis.conf` maxmemory 3gb + AOF everysec）；
- **MinIO RBAC one-shot**：`minio_rbac_init` 建 uploads/exports/backups 三桶 + 三组最小权限凭据（:641-684）；
- **观测栈**：prod 版增加 node_exporter + cadvisor，数据卷 named volume 持久化；全部端口绑 127.0.0.1（查看面走 SSH 隧道，`bootstrap.sh:716` 摘要自述）；
- **每服务内存 limits/reservations**（:1-61 锚点表）：合计 limits ≈ 17.1G、reservations ≈ 5.5G（本轮逐服务累加；含 redis limit 4G :37-39、agent 2G :17-21、db 2G :32-36）——这是 §3 档位设计的直接依据；
- **非 root**：应用容器统一 `user: ${SPARKLE_APP_UID:-10001}`（:130 等）；
- **硬失败门**：`TRUSTED_PROXIES`/`ALLOWED_ORIGINS`/`MINIO_ROOT_*`/`ALERTMANAGER_*_WEBHOOK_URL`/`GRAFANA_ADMIN_*` 用 `:?must be set` 语法（:140-141、:626-627、:752-754、:878-879）——配错起不来，不带病上线。

### 1.3 Makefile 部署相关目标

| 目标 | 内容 | 证据 |
|---|---|---|
| `cloud-plan` / `cloud-up` | 一键部署总入口/干跑，转调 `scripts/deploy/bootstrap.sh` | `Makefile:182-189` |
| `dev-up` / `dev-up-all` | 基础设施 / 全栈（含 preflight：缺 .env 提示 + `check_shadowing.py`） | `Makefile:23-41` |
| `db-migrate` | **单头门禁内置**：`alembic heads` 计数 ≠1 直接失败，FORCE_STAMP=1 才允许 stamp | `Makefile:52-91` |
| `db-dump` | schema.sql 从一次性 fresh 迁移库导出（防 dev 库带外污染），非部署路径但是 schema 纪律证据 | `Makefile:97-123` |
| `smoke` | 配置自检 + backend `/health` + 网关 `/api/v1/health` + `/api/v1/health/cqrs` | `Makefile:144-180` |
| `init-minio-buckets` / `init-rag` / `sync-rag` | 引擎侧 MinIO 桶 / Redis 向量索引（bootstrap 的 exec 兜底路径引用后者） | `Makefile:130-142` |
| `local-*` 验收族 | config-check → fixture → smoke → auth/community/worker/file-pipeline → grpc/ws 集成 | `Makefile:514-569` |

### 1.4 .env 模板体系（四模板三层标注）

| 模板 | 定位 | 证据 |
|---|---|---|
| `.env.example`（9.3K） | 本地开发基线 | 仓库根 |
| `.env.local.example`（6.7K） | 本地验收 | 仓库根 |
| `.env.production.example`（22K） | **完整生产基线**，`[MUST CHANGE]/[RECOMMENDED]/[OPTIONAL]` 三级标注 | 仓库根；分级标注见 :23-38 等 |
| `.env.cloud.example`（6K） | **云上 overlay**（D-BOOTSTRAP 交付）：钉死 `ENVIRONMENT=production`/`DEBUG=False`/`LLM_QUOTA_ENABLED=true`/`GLM_BATCH_ENABLED=false`，日预算 5/1/2/0.5 美元档，glm_batch 背压 200 | `.env.cloud.example:24-49` |

bootstrap 的装配与门禁：`cat 基线 overlay > .env && chmod 600`（`bootstrap.sh:223-246`），占位符识别 + 18 个必填项 + ≥1 个 LLM key + 4 个安全钉死项校验（`bootstrap.sh:152-221`）。

### 1.5 scripts/ 部署脚本族（全部实存）

| 脚本 | 行数 | 职责 |
|---|---|---|
| `scripts/deploy/bootstrap.sh` | 782 | 一键总入口（9 步 + 摘要），`--plan` 干跑 / `--with-demo-seed` / `--lean-observability` / `--domain` / `--image-tag`，幂等可重跑 |
| `scripts/deploy-prod.sh` | 129 | 日常发版：蓝绿切换 + 健康门 30 次 + smoke + 180s 观察 + 失败自动回切 + 90s 排空 |
| `scripts/backup_prod_data.sh` | 74 | PG dump gzip + Redis RDB + MinIO tar，sha256sums + manifest，`KEEP_DAYS=7` 滚动清理 |
| `scripts/restore_prod_data.sh` | 61 | 恢复配套 |
| `scripts/ssl/setup_certs.sh` | 24 | Let's Encrypt 证书拷入 `./ssl`（依赖宿主机先 `certbot certonly --standalone`） |
| `scripts/ssl/generate_dev_certs.sh` | 27 | 自签证书（内网演示） |
| `scripts/verify_deployment.sh` | 31 | 公网健康 + 延迟验证（延迟仅 warning） |
| `scripts/run_e2e_smoke.sh` | — | 全栈 E2E smoke（自装配 .env 的 CI 形制） |
| `scripts/deploy_k8s.sh` | 77 | k8s 路径入口（`k8s/base`+`k8s/prod` blue/green+kustomize；单 VPS 阶段不启用） |
| `scripts/check_production_secrets.py` | — | 占位/弱密钥扫描（`minioadmin`/`password` 等黑名单 + provider 凭据形状检测） |
| `scripts/check_cors_config.py` | — | 生产 CORS 通配符守卫 |
| `scripts/seed_demo_user_enhanced.py` / `scripts/clean_demo_data.py` | — | 演示数据种子/清场（production 下必须显式传 `LOCAL_SMOKE_PASSWORD`，见 `seed_demo_user_enhanced.py:55-57`） |

### 1.6 引擎 Worker 进程拓扑

- **uvicorn（FastAPI :8000）**：镜像 `ENTRYPOINT docker-entrypoint.sh` + `CMD ["uvicorn", "app.main:app", "--host 0.0.0.0", "--port 8000"]`（`backend/Dockerfile:105-109`）；entrypoint 在 `SERVICE_ROLE=api` 或 `RUN_MIGRATIONS=true` 时先跑 `alembic upgrade head`（`backend/docker-entrypoint.sh:7-11`）；
- **gRPC（:50051）**：`python grpc_server.py`，注册 AgentService/ErrorBookService/GalaxyService/STTService/InferenceService 五个 servicer + reflection + OTel gRPC 服务端插桩（`backend/grpc_server.py:31-92`）；带 `AuthInterceptor`（:40）——引擎不鉴权用户、但校验内部调用方，分层规则成立；
- **Celery 队列清单（4 条）**：`high_priority`/`default`/`glm_batch`/`low_priority`，默认兜底队列 `default`（`backend/app/core/celery_app.py:110-131`）；显式路由样例：embedding→high、错题批量/胶囊批量→glm_batch、清理/预测校验→low（:133-160 区间）；背压硬顶 `{"glm_batch": 200}`（`.env.cloud.example:49`）；
- **beat 计划任务**：`cost-wvpl-daily-refresh`（05:10）、`cleanup-every-day`、`daily-report`、`health-check`（每小时）、`policy-compiler-due-scan`（每 30s）、`checkpoint-nudge`（08:00）、`absence-scan`（每 30min）等（`backend/app/core/celery_app.py:1020-1060` 区间）——**beat 是常驻必跑组件，省不掉**；
- **worker 编排形制**：prod 常规道 `-Q high_priority,default,low_priority --concurrency=4`（:431）、glm_batch 道 `--autoscale=6,2`（:470，云上被 `--scale 0` 双保险熄火，`bootstrap.sh:522-526`）、beat 单实例（:510）。

### 1.7 数据库迁移策略

- **单头链成立**：本轮离线解析 `backend/alembic/versions/` 全部 163 个迁移文件建图（revision/down_revision 多行元组解析），**heads 恰为 1 个：`photidem_20260923`**（含多个 merge 节点如 `merge_lane_d_lane_k_2026_04_26.py`）。与 `Makefile db-migrate` 的单头门禁（`Makefile:56-73`）和仓库硬规则一致；
- **prod 执行时机**：`db_migrate` one-shot 串在 DB healthy 之后、应用起之前（§1.2）；bootstrap 步骤 4 等待 exit 0、超时 600s（`bootstrap.sh:425-434`）；
- **注意点（非缺口）**：`docker-entrypoint.sh` 让 api 角色也会再跑一次迁移——compose 依赖链已保证 db_migrate 先完成，因此 entrypoint 内第二次迁移是幂等空操作；两处迁移入口并存是刻意的双保险（手工 docker run 场景兜底）；
- **AGE/向量初始化**：`db_age_init` one-shot（prod）+ `init_redis_index.py`（RAG 向量索引，`bootstrap.sh:482-486`，失败 WARN 不阻塞）。

### 1.8 可观测面现状（指标出口盘点）

| 出口 | 内容 | 证据 |
|---|---|---|
| 网关 `/metrics` | promhttp 标准出口；限流器计数 `sparkle_rate_limiter_redis_fallback_total`、`sparkle_rate_limiter_redis_errors_total{error_type}`、`rate_limiter_tokens_remaining` 直方图、`rate_limiter_rejections_total{reason}`；CQRS metrics | `backend/gateway/cmd/server/setup.go:492`；`backend/gateway/internal/middleware/distributed_rate_limiter.go:15-45` |
| 引擎 `/metrics` | prometheus-fastapi-instrumentator 全局出口（2026-09-20 曾因缺 expose 而 404，已修） | `backend/app/main.py:845-846` |
| 安全监控计数器（PROD-FIX-1 刚加） | `sparkle_security_monitor_start_failures_total`、`sparkle_security_monitor_background_task_failures_total`——SecurityMonitor 启动即验 + 运行期死亡不再静默（签名漂移修复） | `backend/app/core/security_monitor.py:34-43`；`backend/app/main.py:205-214、792-794` |
| 图谱监控 | `/api/v1/graph_monitor/prometheus/metrics` 独立出口 | `backend/app/api/v1/graph_monitor.py:29、451` |
| 告警规则 | celery_alerts / SLO / production_baseline / t6_slo / sqam / recording_rules 六组规则文件挂进 prometheus | `monitoring/prometheus.yml:10-16`；`docker-compose.prod.yml:717-723` |
| 日志 | promtail 挂 docker.sock → loki；应用日志卷（dev） | `docker-compose.prod.yml:851-871` |
| 抓取目标 | 见 §2 G1——**目标名与 prod 拓扑部分脱节** | `monitoring/prometheus.yml:24-70` |

---

## 2. 缺口分析（现状 / 缺口 / 最小解）

### G1 (P1) Prometheus 抓取目标名与 prod 服务拓扑脱节
- **现状**：`monitoring/prometheus.yml` 抓 `sparkle_gateway:8080`、`sparkle_api:8000`、`sparkle_agent:50051`、`sparkle_celery:9808`（:22-68）。dev compose 里这些 container_name 存在，故 dev 全绿。
- **缺口**：prod compose 服务名为 `backend`/`gateway_blue`/`gateway_green`，container_name 为 `sparkle_backend`/`sparkle_gateway_blue|green`（`docker-compose.prod.yml:242、128、185`）——`sparkle_gateway` 与 `sparkle_api` 在 prod 的 `sparkle_app` 网络内**都解析不到**（网关抓取、后端抓取静默断）；`sparkle_celery:9808` 则**两种形制下都没有对应 exporter 容器**（全仓无 9808 监听者）。只有 `sparkle_agent` 恰好命中 prod container_name（:338）能抓到。
- **影响**：上云后 Grafana 的网关限流/CQRS/SLO 面板大面积 no-data，告警规则（六组）空转——演示期「出事先知道」的能力打折。
- **最小解（S）**：prometheus.yml 目标改为在两个形制下都可解析的名字——prod 侧加 `gateway_blue:8080`、`gateway_green:8080`、`backend:8000` 三个 target（Docker DNS 对 user-defined 网络按服务名解析），或改用文件服务发现；`sparkle_celery` target 删除或补一个 `prometheus-community/celery-exporter` 容器（后者工作量 M，可缓）。

### G2 (P1) 备份未 cron 化、未异地化
- **现状**：`backup_prod_data.sh` 能产出 PG+Redis+MinIO 三件套备份包（含校验和、7 天滚动清理）；bootstrap 摘要里给了 cron 建议行（`bootstrap.sh:723`）；MinIO 有 `sparkle-backups` 桶（`docker-compose.prod.yml:653`）。
- **缺口**：cron 是「建议人工去配」，没有落地机制；备份只落本机 `./backups`——**单机磁盘损坏 = 全部演示数据蒸发**；backup 脚本读 `REDIS_PASSWORD` 环境变量默认空（:14），prod 三账号 ACL 形制下需显式传 default 账号密码才能 RDB。
- **最小解（S）**：① bootstrap 加一步「安装 cron 条目 + 校验首次备份」或产出 `systemd timer` 单元；② 收尾加一行 `mc mirror ./backups/最新包 minio/OSS/备份桶`（或 rclone 到对象存储）实现异地——对象存储 40GB 级成本约 ¥5-10/月（估算+时效 2026-09）。

### G3 (P1，仅 2C4G 档) 无 4G 级精简 profile
- **现状**：prod 22 服务 limits 合计 ≈17.1G / reservations ≈5.5G（§1.2）；`--lean-observability` 裁 loki/promtail/tempo/cadvisor 后仍 limits ≈15.4G / reservations ≈5.3G；bootstrap 内存门 7G（`bootstrap.sh:52`）。
- **缺口**：2C4G 主机装不下现成任何组合——不是「慢」，是 OOM 风险（2026-09-19 磁盘/内存事故同型风险，AGENTS.md 纪律同理适用于云端单机）。
- **最小解（M，约 0.5-1 天 + 真机验证）**：新增 `docker-compose.minimal.yml` override（或 bootstrap 加 `--tiny-profile`）：gateway_green `--scale 0`（放弃蓝绿，回滚改用镜像 tag）、glm_batch 保持 scale 0、可观测只留 prometheus（limit 降到 512M）+ alertmanager、celery 常规道 `--concurrency=2`、redis limit 降至 1G（`redis.conf` maxmemory 同步 512mb）、agent limit 1.5G。裁后 limits ≈ 7G / 实际驻留 ≈ 3-3.5G，4G 主机 + 2G swap 可稳。**注意**：蓝绿退役后 `deploy-prod.sh` 的滚动发布语义降级为「停旧起新」，需在文档标注维护窗口。

### G4 (P2) 镜像分发：ghcr.io 国内拉取慢/私库需登录
- **现状**：CI 构建并推送 `ghcr.io/<owner>/sparkle-{gateway,backend}`（`.github/workflows/ci.yml:651-712`，tag 策略 sha+tag+latest）；bootstrap 对 pull 失败有排查提示（`bootstrap.sh:399-404`）。
- **缺口**：国内 VPS 拉 ghcr 时快时慢；私有仓库还需 `docker login`。镜像 1-2GB 级，拉取失败是部署现场最常见卡点。
- **最小解（S-M）**：① 演示期把镜像推一份到阿里云 ACR 个人版（免费额度）/腾讯云 TCR 个人版，`GATEWAY_IMAGE/BACKEND_IMAGE` 变量已支持整体替换镜像地址（`docker-compose.prod.yml:65、127`），改 .env 即可；② 或首次部署前在本机 `docker save | ssh docker load`。

### G5 (P2) TLS 证书续期未闭环
- **现状**：`setup_certs.sh` 只做「从 `/etc/letsencrypt/live/<domain>` 拷贝到 `./ssl`」一次性动作（`scripts/ssl/setup_certs.sh:7-24`）；nginx 挂载 `./ssl` 为 :ro。
- **缺口**：certbot 续期后不会自动拷入 + reload nginx——90 天后证书过期，评委扫码报证书错误（演示期最尴尬的事故形态）。
- **最小解（S）**：cron 加 `certbot renew --deploy-hook "bash <repo>/scripts/ssl/setup_certs.sh <domain> ./ssl && docker compose -f docker-compose.prod.yml exec -T nginx nginx -s reload"`；或在 README 登记为部署必配项。

### G6 (P2) 国内云合规：ICP 备案与域名（流程项，非代码）
- **现状**：全流程假设「VPS + 域名」（`bootstrap.sh:5-6`），DNS 校验是 warning-only（:345-356）。
- **缺口**：国内云主机绑 80/443 对外提供 Web 服务，域名必须完成 ICP 备案（云厂商强管控，未备案域名会被阻断）；备案免费但流程通常 1-3 周（估算+时效）。此外 App 若上国内安卓商店还涉及软著/备案等，但**APK 直链分发（`deploy/landing` 形态）不触发应用商店审核**。
- **最小解**：域名实名 + 备案提前启动（与开发并行）；过渡期可用「IP + 自签证书」内网演示（`generate_dev_certs.sh` 已备），或用已备案的备用域名。

### G7 (P3) bootstrap 的 AGE one-shot 探测正则不认识 `db_age_init`
- **现状**：D-BOOTSTRAP 设计了「探测到 compose 内 age_init 服务即走 compose 路径」的撞面规避（`bootstrap.sh:450-455`），探测正则为 `grep -xE '(sparkle_)?age_init'`（:451）。
- **缺口**：D-AGE 实际落地的 prod 服务名叫 **`db_age_init`**（`docker-compose.prod.yml:79`）——正则不命中，永远走 fallback（起 backend 再 `compose exec` 跑 `init_age_extension.py`，:456-481）。
- **影响**：**功能无损**——AGE 扩展初始化仍会发生（`db_age_init` 由 backend/agent/celery 的 `depends_on: service_completed_successfully` 强制先行），fallback 的 exec 在 AGE 镜像上也幂等成功；只是多起一次 backend + 探测逻辑白设。
- **最小解（S）**：正则放宽为 `'(sparkle_)?age_init|db_age_init'`。纯一行修正，可并入任何后续 D 线代码卡。

### G8 (P3) dev compose 网关端口绑 0.0.0.0（仅开发形态）
- **现状**：dev `sparkle_gateway` 端口映射 `${SPARKLE_GATEWAY_PORT:-8080}:8080` 未限定 127.0.0.1（`docker-compose.yml:447`），栈内其余端口全部限定。prod 形制无此问题（网关只在 edge 内网，公网只见 nginx）。
- **影响**：开发机在同一局域网时 8080 裸奔（带 JWT_SECRET 等环境变量跑的完整网关）。
- **最小解（S）**：改为 `127.0.0.1::8080` 形制或 `SPARKLE_GATEWAY_PORT` 文档默认 `127.0.0.1:8080`。演示场景若手机要连开发机，用 `--dart-define` 指向该地址前先评估网络环境。

### 已关闭缺口备案（相对 R1 稿的核销）
| R1 缺口 | 现状 |
|---|---|
| #1 prod DB 无 AGE（P0） | **已关闭**：prod db 构建 `docker/pgvector-age.Dockerfile`（`docker-compose.prod.yml:544-552`）+ `db_age_init` one-shot（:79-99）；守卫 `scripts/guards/check_rule_bn_prod_db_age_parity.py` 存在 |
| #2 无 bootstrap 一键流（P0） | **已关闭**：`scripts/deploy/bootstrap.sh` + `make cloud-up/cloud-plan`（`Makefile:182-189`） |
| #3 `LLM_QUOTA_ENABLED` 默认 False（P1） | **已缓解**：settings 默认仍 False（`backend/app/config/settings.py:419`，注释自述为演示录制），但云上 overlay 钉死 true（`.env.cloud.example:32`）+ bootstrap 门禁校验（`bootstrap.sh:199-200`） |
| #4 glm_batch 云上成本面（P1） | **已缓解**：overlay `GLM_BATCH_ENABLED=false`（`.env.cloud.example:37`）+ bootstrap `--scale celery_glm_batch_worker=0` 双保险（`bootstrap.sh:522-526`） |
| #5 Android 明文流量（P1） | **仍开放**：`android:usesCleartextTraffic="true"`（`mobile/android/app/src/main/AndroidManifest.xml:25`）。出包用 `--dart-define=API_BASE_URL=https://...`（`mobile/lib/core/constants/api_constants.dart:5-7`）后流量是 HTTPS，但 release 包仍允许明文是合规减分项；最小解：release manifest 覆盖关闭（M，动 mobile） |
| #6 演示数据未接部署流（P2） | **已关闭**：bootstrap 步骤 7.5 `--with-demo-seed`（`bootstrap.sh:539-566`，含展后清场提示） |
| #9 无落地页（P2） | **已关闭**：`deploy/landing/index.html` 单文件落地页 + 海报文案（`deploy/README.md:9-14`） |

---

## 3. 部署方案（两档）

> 场景设定：参赛演示（评委扫码可用）+ 日活 < 百级。并发峰值估算：100 DAU × 集中在演示时段 2-3 小时 × 平均 1-2 msg/min ≈ **峰值 <5 QPS 网关层、LLM 并发 <5**——单机余量巨大，瓶颈只会是内存预算而非算力。

### 3.0 两档总览

| | 档一 A：2C4G 极简单机 | 档一 B：2C8G/4C8G 单机（**推荐**） | 档二：单机 + 托管面 |
|---|---|---|---|
| 月成本（估算+时效 2026-09） | ¥60-150（轻量应用服务器促销档；标准 ECS 同规格 ¥150-250） | ¥200-400（4C8G 轻量/ECS 通用档） | ¥200-400 + 托管 PG ¥150-400 + 托管 Redis ¥100-250 ≈ **¥450-1050** |
| 上线耗时（备好域名/key 后） | 0.5-1 天（含写 minimal overlay + 真机调） | **半天内**（现有脚本零改动） | 1-1.5 天（多两套托管实例开通 + 连通改造） |
| 域名/证书 | ¥30-80/年；Let's Encrypt 免费 | 同左 | 同左 |
| LLM 成本 | `.env.cloud.example` 日预算硬顶 $8.5/天（5+1+2+0.5，:43-46）；演示真实用量估 <$2/天（估算：探针 <$0.1/次，`bootstrap.sh:617` 自述） | 同左 | 同左 |
| 备份 | 本机 + cron（G2 解法必须做） | 本机 + cron + 对象存储异地（+¥5-10/月） | **托管自动备份**（PITR），MinIO 数据仍需自备 |
| 运维负担 | 最高（4G 无余量，观测只剩 prometheus） | 中（lean 观测可用，Grafana 面板能看） | 最低（DB/Redis 高可用+自动备份外包） |
| 适用判据 | 纯预算最低、能接受演示期观测裸奔 | **参赛演示最优点** | 已有真实用户/商业化启动后 |

### 3.1 档一 B（推荐）落地方案：2C8G 单机 + 现有一键流

**选型**：国内大厂轻量应用服务器 2C8G（或 4C8G，价差约 ¥100/月，估算+时效）+ Ubuntu 22.04/24.04 + Docker Engine + 60GB+ 系统盘（磁盘纪律同 AGENTS.md：镜像+构建缓存+备份三层占用，bootstrap 已设 20G 磁盘门，`bootstrap.sh:51`）。

**部署形态**：`docker-compose.prod.yml` 全 22 服务 + `--lean-observability`（裁 loki/promtail/tempo/cadvisor，保留 prometheus+grafana+alertmanager+node_exporter——评委演示时「有监控大屏」本身是加分项）。**不裁蓝绿**（8G 装得下，保留零停机发版能力）。

**理由**（相对 2C4G）：
1. bootstrap 内存门 7G（`bootstrap.sh:52、314-317`）——8G 一次过，4G 连 lean 模式都进不了门（G3）；
2. Redis prod 配置 maxmemory 3gb（`redis.conf`）+ db limit 2G，4G 主机必然 OOM 曲线；8G 有 1 个数量级余量覆盖「评委集中扫码」尖峰；
3. 零代码零新组件——**今天是绿色通道**；4G 档则要先写 minimal overlay（G3，M 工作量）。

### 3.2 档二（托管面）增量差异

| 维度 | 变更 | 工作量 |
|---|---|---|
| DB | 云 PG 16 托管版替 `db`+`db_migrate` 容器；**注意 AGE 扩展**：托管 PG 不一定提供 Apache AGE 扩展——星图面可能断链，选型时必须先确认厂商 PG 镜像扩展列表（这是档二的最大隐性门槛） | M（迁移用 `alembic upgrade head` 对托管库跑一次；compose 删 db/db_migrate/db_age_init，DATABASE_URL 指托管） |
| Redis | 托管 Redis 替 `redis` 容器；**三账号 ACL**（:597-604）需映射为托管版的账号体系或退化为多 DB+单账号 | S-M |
| MinIO | 可换云 OSS/S3（`MINIO_USE_SSL=true`、S3 协议兼容，网关已支持变量化 :151-156）；引擎侧 `init_minio_buckets` 语义不变 | S |
| 观测/备份 | 仍留单机（量小不值得托管）；DB 备份职责转移给云厂商 | — |
| 收益 | 自动备份/PITR、免磁盘运维、平滑升配 | 换来月成本 +¥250-650（估算+时效） |

**判据**：参赛演示期不划算（多花钱+AGE 扩展风险）；首轮真实用户（日活>500 或有付费）后再迁，且迁移路径已被 12-factor 化的环境变量面铺好。

---

## 4. 一键化清单：从零到公网可用

> 现状：步骤 0-13 的**执行器已全部存在**（bootstrap.sh 9 步 + 摘要），本清单是「操作者视角的顺序手册 + 每步验证点 + 工作量」，并标注哪几步是 bootstrap 之外的人工项。

| # | 步骤 | 执行/验证 | 工作量 |
|---|---|---|---|
| 0 | 购 VPS（2C8G）+ 域名 + **启动 ICP 备案**（G6，与后续并行） | 域名 A 记录 → VPS IP | S（备案等待 1-3 周是关键路径，估算） |
| 1 | 装 Docker + clone 仓库 | `curl -fsSL https://get.docker.com \| bash`；bootstrap 步骤 0 会校验 daemon/磁盘≥20G/内存≥7G/80+443 空闲（`bootstrap.sh:288-357`） | S |
| 2 | TLS 证书 | `sudo certbot certonly --standalone -d <域名>` → `bash scripts/ssl/setup_certs.sh <域名> ./ssl`；**同时配 renew cron（G5）**；验证：`openssl x509 -in ssl/fullchain.pem -noout -dates` | S |
| 3 | `.env` 装配 | `make cloud-plan` 干跑预览 → 编辑 `.env` 填 18 个必填 + ≥1 个 LLM key + 3 个告警 webhook + JWT RSA 密钥对（`.env.cloud.example:55-92` 每项注明 key 来源与生成命令）；bootstrap 步骤 1 门禁会逐项拒绝占位符并**列出缺哪些**（`bootstrap.sh:204-219`）；验证：门禁输出 `.env 门禁通过` | M（填空项多但每项有指引） |
| 4 | 镜像就绪 | `IMAGE_TAG=<tag>`；ghcr 慢/私库时先做 G4（ACR 副本或 docker load）；验证：`docker compose -f docker-compose.prod.yml pull` 全绿 | S-M |
| 5 | 一键拉起 | `make cloud-up ARGS="--domain <域名> --lean-observability [--with-demo-seed]"`——依次：db/redis 起稳（步骤 3）→ 迁移 one-shot exit 0（步骤 4）→ AGE/RAG 初始化（步骤 5）→ MinIO 三桶（步骤 6）→ 全栈 + nginx（步骤 7，glm_batch 自动 scale 0）→ [种子] → readiness → chat 探针 → 摘要 | S（一条命令） |
| 6 | **健康探针四层验证** | 见下方探针表 | S |
| 7 | 备份上线（G2） | cron：`15 3 * * * bash scripts/backup_prod_data.sh`（bootstrap 摘要 :723 已给模板）+ 对象存储异地一行；验证：手动跑一次、还原演练 `restore_prod_data.sh` 到临时目录 | S |
| 8 | 防火墙 | `ufw allow 22,80,443/tcp && ufw enable`（bootstrap 只打印建议不代改，:342；5432/6379/9000/8000/50051/3000/9090 靠 compose internal + 无端口映射双保险，:343） | S |
| 9 | 移动端出包 | `flutter build apk --release --dart-define=API_BASE_URL=https://<域名> --dart-define=WS_BASE_URL=wss://<域名> --dart-define=ENABLE_GOOGLE_SERVICES=false --dart-define=FCM_ENABLED=false`（bootstrap 摘要 :724-727；常量注入面 `api_constants.dart:5-7`；证书 pinning 可加 `API_CERT_SHA256`，:19） | S |
| 10 | 扫码落地页 | `deploy/landing/index.html` 改 CONFIG 块（APK 直链/二维码）→ 挂 nginx `location /landing/`（`deploy/README.md:26-30` 给了现成 snippet） | S |
| 11 | 日常发版 | `IMAGE_TAG=<新tag> bash scripts/deploy-prod.sh`（蓝绿 + 健康门 + 自动回切 + 排空） | S |

**健康探针四层验证点**（每层都有现成端点，全部已在 bootstrap/Makefile/脚本中使用）：

| 层 | 探针 | 通过判据 | 证据 |
|---|---|---|---|
| 边缘（nginx/TLS） | `curl -sI http://<域名>/... → 301`；`curl -fsS https://<域名>/api/v1/health` | 301 → 443；HTTPS 200 + 证书链有效 | `nginx/nginx.conf:58-60、65-68` |
| 网关 | 内网 `gateway_blue:8080/api/v1/health` + `/api/v1/health/cqrs`（bootstrap readiness 步骤 8，容器网络内 curl 镜像）；公网同路径 | 两路径 200 | `bootstrap.sh:575-601`；`Makefile:159-179` |
| 引擎（FastAPI+gRPC+Celery） | backend `/health`（compose healthcheck）；gRPC TCP 50051 探活（compose healthcheck）；`celery inspect ping`（worker/glm healthcheck）；beat pgrep；深度：`/metrics` 有输出 | 全部 healthy；`docker compose ps` 全绿 | `docker-compose.prod.yml:327-332、417-422、456-461、535-540`；`backend/app/main.py:845-846` |
| 数据面 | db `pg_isready`、redis `redis-cli ping`（ACL 账号）、minio `/minio/health/live`、单 Alembic head | 全部 healthy；`alembic heads` 单头 | `docker-compose.prod.yml:579-584、611-616、632-637`；`Makefile:56-58` |
| 端到端（北极星） | bootstrap smoke：`POST /api/v1/auth/guest` → WS `/ws/chat`（Bearer）→ 收到任意流式帧（产生 1 次最小 LLM 调用） | 首帧 type 非空；失败仅 WARN 不阻塞上线 | `bootstrap.sh:606-693` |

---

## 5. 安全面

### 5.1 公网暴露面（应该收的都已经收）

| 端口 | dev 形制 | prod 形制 | 评价 |
|---|---|---|---|
| 80/443 | 未暴露 | **nginx 独占**（唯一公网面） | 正确 |
| 8080（网关） | `0.0.0.0`（G8） | edge 内网，无公网映射 | prod 正确；G8 为 dev-only |
| 8000（引擎 FastAPI）/ 50051（gRPC） | 127.0.0.1（`docker-compose.yml:114、216`） | **无 ports 映射**（app internal 网络） | 正确；引擎靠网关 `INTERNAL_API_KEY` + `AuthInterceptor`（`grpc_server.py:40`）隔离 |
| 5432/6379/9000-9001 | 127.0.0.1 | 无映射 + `internal: true` | 正确 |
| 3000/9090/9093/3100 等（观测） | 127.0.0.1 | 127.0.0.1 + app 内网 | 正确；查看走 SSH 隧道（`bootstrap.sh:716`） |

注：prod 里 tempo/prometheus 等 app 内网容器仍写了 `127.0.0.1` 端口映射（如 :696-697、:726）——在 `internal: true` 网络上端口发布行为依 Docker 版本可能不生效，但它们本就供宿主机 SSH 隧道查看，真机部署时验证一下即可（真机验证项，非阻塞）。

### 5.2 限流（三层，已有实现）

1. **nginx 区限速**：general 30r/s（burst 50）/ auth 5r/s / chat 10r/s（`nginx/nginx.conf:45-47、85`）；
2. **网关应用层**：auth 5 r/s burst 15、api 15 r/s burst 30、galaxy 10/20、admin/internal 独立 limiter，全部 `HybridRateLimitMiddlewareSimple`（本地令牌桶 + Redis 分布式兜底）（`backend/gateway/cmd/server/setup.go:519-522、599`）；
3. **Redis 分布式令牌桶**：Lua 原子脚本，Redis 故障可降级本地且带 Prometheus 计数（`distributed_rate_limiter.go:15-45、47+`）；WS ticket 另有可配置限速（`setup.go:585`）。NoRoute 兜底路径也先过 authRateLimit + body 上限 + 特权路径鉴权（`setup.go:870-886`）——防绕路。

### 5.3 CORS / WS 鉴权

- 网关：`CORSMiddleware` 开关 + `ALLOWED_ORIGINS`，prod compose `:?` 强制显式配置（`setup.go:498-499`；`docker-compose.prod.yml:141、198`）；overlay 默认单域名白名单（`.env.cloud.example:73-76`）；守卫 `scripts/check_cors_config.py` 禁生产 `*`；
- WS：prod 钉死 `ALLOW_WS_QUERY_TOKEN=false`——查询串带 token 的兼容通道在公网关闭，只走 header 鉴权（`docker-compose.prod.yml:142、199`；`bootstrap.sh:615-617` 探针按此实现）。

### 5.4 Secrets 纪律

- `.env`/`.env.*` 全量 gitignore，仅 `*.example` 白名单（`.gitignore:57-66`）——`.env 绝不入库` 红线有机制保障；
- 双重门禁：bootstrap 占位符门禁（`bootstrap.sh:152-219`，与 `check_production_secrets.py` 前缀黑名单对齐，:152 自述）+ prod compose `:?` 硬失败变量（§1.2）；
- overlay 烧钱开关钉死：`LLM_QUOTA_ENABLED=true`、四桶日预算、`GLM_BATCH_ENABLED=false`（§1.4）；`DEBUG=False`/`ENVIRONMENT=production` 由门禁反向校验（值反了拒绝部署）；
- 密钥不自动生成是**刻意设计**（D-BOOTSTRAP 报告：防静默轮换炸卷），人工 `openssl rand -hex 32` 指引在 `bootstrap.sh:218` 门禁输出与 `.env.cloud.example:88-92`（JWT RSA 对生成命令）。

### 5.5 遗留安全债（不阻塞上线，登记）

- Android `usesCleartextTraffic="true"`（G8 相关，§2 已核销表 #5）；
- `JWT_ALGORITHM` 默认 HS256 对称签名（`docker-compose.yml:466`），overlay 建议迁移 RS256 并给出生成命令（`.env.cloud.example:86-92`，RECOMMENDED 级）；
- 自组 Redis ACL 的 default 账号权限是 `~* +@all`（`docker-compose.prod.yml:600`）——三账号隔离已建，default 全权限账号仍存在；备份脚本正依赖它，收紧需同步改备份脚本（M，暂不动）。

---

## 6. 交付与边界申报

- 本轮**零代码改动**：worktree 内仅新增本报告；无 tmp 文件残留（研究全程用管道与只读命令）；
- 本报告全部结论基于 worktree wt185 @ d2265244 的真实文件；`--plan` 干跑、真机部署、公网探活属 D-BOOTSTRAP 报告已申报的「未真机部署项」，本卡不重复申报为缺口，但 §2 G1/G2/G5 的最小解合入后**必须**经一次真机 `cloud-plan` + 部署演练验证；
- 建议合入顺序：G1（S）+ G5（S）+ G7（S）可合成一张小卡；G2（S）+ G4（S-M）一张小卡；G3（M）仅当用户坚持 4G 档才立项。
