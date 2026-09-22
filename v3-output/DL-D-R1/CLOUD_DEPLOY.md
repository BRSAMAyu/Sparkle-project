# CLOUD_DEPLOY — Sparkle 云端一键部署方案（D 线 R1 研究稿）

> 轮次：D 线第一棒 · 纯研究/方案轮（零代码改动）｜ 2026-09-22 ｜ worktree wt82（wt82-v3 @ main 54427431）
> 目标：支撑「投资人给钱即可上线」——一台 VPS + 一个域名 + 一组 API Key → 30 分钟内全栈可演示。
> 边界申报：本文所有成本数字均为**估算**（无一手询价来源，WebSearch 配额受限）；所有仓库现状论断带 file:line 证据；伪代码/分步 shell 仅为**草案**，本轮不落任何可执行脚本文件。

---

## 1. 现状盘点：已具备 / 缺口

### 1.1 已具备（盘点结论：生产化程度远超一般参赛项目）

| 资产 | 位置 | 状态与要点 |
|---|---|---|
| 生产 Compose 全栈（17 服务） | `docker-compose.prod.yml` | nginx(TLS) + gateway_blue/green（蓝绿）+ backend + agent + celery_worker + celery_beat + db + redis + minio + 全套可观测（prometheus/grafana/loki/tempo/alertmanager/node_exporter/cadvisor/promtail）；每服务有 healthcheck、内存 limits/reservations（:1-61）、非 root UID（:106 `SPARKLE_APP_UID=10001`）；`app` 网络 `internal: true`（:867）数据库/Redis/MinIO 不暴露公网 |
| 迁移自动化 | `docker-compose.prod.yml:64-75`（db_migrate one-shot `alembic upgrade head`）+ `backend/docker-entrypoint.sh`（SERVICE_ROLE=api 时亦跑迁移） | 迁移是 compose 依赖链的第一环（backend/agent/celery 全部 `depends_on: db_migrate: service_completed_successfully`） |
| Redis 三账号 ACL 隔离 | `docker-compose.prod.yml:547-577` | gateway/engine/celery 三组独立密码 + key 前缀白名单，非 root 用户禁 @dangerous |
| MinIO 桶与最小权限初始化 | `docker-compose.prod.yml:600-643`（minio_rbac_init one-shot） | uploads/exports/backups 三桶 + 三组专属凭据；`make init-minio-buckets`（Makefile:140-142）为引擎侧等价物 |
| Nginx 边缘 | `nginx/nginx.conf` + `nginx/upstream.conf` | 80→443 强跳、TLS1.2/1.3、HSTS/CSP 等安全头（:77-82）、限速区 general 30r/s・auth 5r/s・chat 10r/s（:45-47）、WS upgrade + 3600s read timeout（:93-97，长连接不被掐） |
| 蓝绿发布脚本 | `scripts/deploy-prod.sh` | pull → 起新色 → 容器网络内健康检查 30 次 → 改 upstream.conf → nginx reload → smoke；`SMOKE_URLS=/api/v1/health /api/v1/health/cqrs` |
| 备份/恢复 | `scripts/backup_prod_data.sh`、`scripts/restore_prod_data.sh` | PG dump + Redis + MinIO 数据，sha256 校验，`KEEP_DAYS=7` 滚动保留 |
| 部署验证 | `scripts/verify_deployment.sh`（健康+延迟）、`scripts/production_readiness_check.sh`（T7.3.5-7 上线前检查单）、`scripts/check_production_secrets.py`（`.env.production.example:16` 引用） | |
| Secrets 校验面 | `.env.production.example`（601 行，[MUST CHANGE]/[RECOMMENDED]/[OPTIONAL] 三级标注）+ prod compose 用 `${VAR:?must be set}` 硬失败（如 :116-117 TRUSTED_PROXIES/ALLOWED_ORIGINS、:585-586 MINIO_ROOT、:711-713 alertmanager webhook、:837-838 grafana 管理密码） | 配错=起不来，不会带病上线 |
| 镜像发布 | `.github/workflows/ci.yml:652-700` | CI 构建并推送 `ghcr.io/<owner>/sparkle-gateway` 与 `sparkle-backend` |
| K8s 备选路径 | `k8s/base`（backend/gateway/hpa/kustomization/secrets）、`k8s/prod`（blue/green + active-service） | 单 VPS 阶段不用，留作规模化路径 |
| AGE 镜像与初始化工具 | `docker/pgvector-age.Dockerfile`（pgvector:pg16 + AGE PG16/v1.6.0-rc0 编译安装）、`backend/scripts/init_age_extension.py`（ensure vector+age 扩展） | 材料齐但**未接进 prod compose**（见缺口 #1） |
| 演示数据种子 | `backend/scripts/seed_demo_user_enhanced.py`（演示账号+计划+聊天会话+任务+成就+星图皮肤，1121-1225 行区间可见 Plan/ChatSession/Task/GalaxySkin 灌入）、`scripts/init_local_fixture.py`（seed_demo_user + 社群/知识节点）、`make fixture-init`（Makefile:500-502） | 本地链路完备，未接部署流（见缺口 #6） |
| 游客体验链路 | `backend/app/api/v1/auth.py:860-1041`（/guest、/upgrade-guest、/upgrade-guest/social）+ `backend/app/services/guest_seed_service.py` | 游客登录即播种演示数据、可后续转正——这是「扫码即体验」的后端地基，已存在 |
| 移动端服务器适配钩子 | `mobile/lib/core/constants/api_constants.dart:7-15` | `--dart-define=API_BASE_URL / WS_BASE_URL / API_CERT_SHA256` 全部可注入；release 模式对 http:// 有告警（:26-31） |
| 证书脚本 | `scripts/ssl/setup_certs.sh`（Let's Encrypt → ./ssl）、`scripts/ssl/generate_dev_certs.sh` | |

### 1.2 缺口清单（按严重度排序；「挡住上线」= 挡住「给钱即可上线」）

| # | 缺口 | 严重度 | 证据 | 影响 |
|---|---|---|---|---|
| 1 | **prod DB 镜像无 Apache AGE**：prod compose db 用 `pgvector/pgvector:pg16`，无 age 扩展；dev compose 有 `sparkle_age_init` 服务而 prod 没有；Alembic 基线只建 `vector`（`backend/alembic/versions/cc9383c4c29f_full_baseline_schema.py:32`），age 靠 `init_age_extension.py` 事后补——该步骤不在任何 prod 流程里 | **P0** | `docker-compose.prod.yml:511`；对比 `docker-compose.yml:30`（dev 有 age_init）；`docker/pgvector-age.Dockerfile` 存在但全仓无引用 | 星图/知识图谱（Apache AGE）在生产直接不可用——**演示核心卖点断链**。2026-05 主方案已诊断（`docs/05_部署与运维/REMOTE_DEPLOYMENT_MASTER_PLAN_2026-05-02.md` Phase2 任务2.1），至今未修 |
| 2 | **无一条「git clone → 上线」的 bootstrap 一键流**：deploy-prod.sh 假设 .env/证书/镜像四件事都已就绪；readiness/verify 脚本各管一段，没有串联 + 种子 + 端到端探针的总入口 | **P0** | `scripts/deploy-prod.sh:3-14`（入口即要求 IMAGE_TAG 且只管蓝绿切换）；`scripts/` 下无 bootstrap/install 类脚本 | 「投资人给钱」到「可演示」之间仍是 3-5 个人日的手工拼装（主方案 P0-P7 估 8-12 天） |
| 3 | **`LLM_QUOTA_ENABLED` 默认 False**（注释自述"为演示录制关闭配额检查"）——按此默认上云，用户日 token 配额（LLMCostGuard）形同虚设，只剩分类目日预算熔断兜底 | **P1** | `backend/app/config/settings.py:409` | 成本面少一层；云上 .env 必须显式置 true（本方案 §4.4 已纳入） |
| 4 | **prod compose 默认带 glm_batch 专用 worker**（`-Q glm_batch --autoscale=6,2`）且 `.env.production.example` `GLM_BATCH_ENABLED=true`——参展单机场景它是纯成本风险面：一旦有历史回积/误投递就立刻开烧 LLM 调用（停车道语义详见 `backend/app/core/queue_backpressure.py:6-14`：O-07 背压上限 glm_batch=200 自动丢弃，`settings.py:435`） | **P1** | `docker-compose.prod.yml:435-471`；`.env.production.example:278-293` | 云上默认应 **scale=0 / 关闭**（本方案 §4.4）；需要离线批处理时再手动拉起并先清队列 |
| 5 | **Android 明文流量全开 + 默认指向 localhost**：`usesCleartextTraffic="true"`；baseUrl 兜底 `http://localhost:8080` | **P1** | `mobile/android/app/src/main/AndroidManifest.xml:25`；`mobile/lib/core/constants/api_constants.dart:33,50` | 出包必须 `--dart-define=API_BASE_URL=https://…`；release 包仍允许明文是安全/合规减分项（评审可见），建议 release manifest 覆盖关闭 |
| 6 | **演示数据未接入部署流**：seed 脚本存在但依赖 backend venv + 显式跑 `make fixture-init`，prod 部署后无种子步骤；演示账号密码默认值在生产环境会主动抛错（`seed_demo_user_enhanced.py:33-35`：production 下必须显式传 LOCAL_SMOKE_PASSWORD） | **P2** | `Makefile:500-502`；`backend/scripts/seed_demo_user_enhanced.py:31-35` | bootstrap 里补一步容器内 seed（§5 步骤 6） |
| 7 | **可观测栈对单 VPS 偏重**：监控 7 容器 reservations 合计约 0.9G、limits 约 3.9G；redis 单容器 limit 4G（`docker-compose.prod.yml:37-39`） | **P2** | `docker-compose.prod.yml:47-61,645-861` | 8G 单机建议裁掉 loki/promtail/tempo/cadvisor（§3.1 组合 B）或上 16G |
| 8 | **gateway 代码默认值仍指 localhost**（compose 环境变量已覆盖，不阻塞 compose 部署，但手工部署/排错会踩） | **P2** | `backend/gateway/internal/config/config.go:531`（AGENT_ADDRESS 默认 localhost:50051）；prod compose :119 已覆盖为 `agent:50051` | 低优先；主方案 Phase2 任务2.2 的遗留 |
| 9 | 无落地页/下载页静态站点（分发侧缺口，详见 GROWTH_ASSETS.md §2） | **P2** | 全仓无 landing/QR 资产 | 不挡 API 上线，挡「扫码→体验」漏斗 |
| 10 | 无支付通道（微信/支付宝/IAP 全无）——不挡部署，但是 MONETIZATION.md 的最大实现缺口 | **P2（对本卡）** | 全仓无 payment/iap 模块；gateway `internal/service/billing.go` 只有缓存省钱计算器 | |

---

## 2. 目标拓扑与成本估算（全估算）

### 2.1 拓扑：单 VPS 全栈（参展/首批用户够用）

沿用 prod compose 现成蓝绿结构，不引入新组件：

```
手机 APK (API_BASE_URL=https://api.<域名>)
        │ HTTPS/WSS (TLS1.2+)
        ▼
nginx :443  ──► gateway_blue :8080（active）/ gateway_green（standby）   [edge 网络]
        │ gRPC(内网明文，单机可接受) / HTTP
        ▼
agent :50051  +  backend :8000  +  celery_worker + celery_beat          [app 内网]
        ▼
PostgreSQL(pgvector+AGE)  Redis(redis-stack, ACL)  MinIO                 [app 内网]
可观测: prometheus + grafana + alertmanager(+node_exporter)  仅 127.0.0.1，SSH 隧道访问
```

gRPC 单机内网明文可接受（主方案已注明：跨主机才需 `GRPC_REQUIRE_TLS=true`；prod compose :120/:333 默认即 false）。

### 2.2 组合建议与月成本估算表

> 全部为**估算**：取 2026 年国内主流云（阿里云/腾讯云）轻量应用服务器公开价位的量级经验值，未做实时询价；实际以采购时报价为准。假设：用户量 ≤500 DAU、LLM 全走外部 API（DeepSeek/智谱 flash 档）、MinIO 自托管。

| 组合 | 规格 | 适用 | 月成本估算（估算） | 假设 |
|---|---|---|---|---|
| **A. 参展演示最小** | 轻量 4C8G + 80G SSD + 8Mbps | 展会/评审演示，10-50 并发体验 | VPS ¥150-300；域名 ¥5-30/月摊；SSL ¥0（Let's Encrypt/云免费证书）；LLM API ¥50-300 | 裁掉 loki/promtail/tempo/cadvisor；glm_batch worker 停 |
| **B. 首批真实用户** | 4C8G→8C16G + 托管 PG（可选） | 100-500 DAU | VPS ¥300-800（16G 档）；托管 PG ¥200-400（可选替代，含自动备份）；LLM API ¥300-1500 | agent 高并发内存可达 3-4G（主方案附录 B），8G 内存需监控裁剪，16G 全栈舒适 |
| **C. 规模化** | K8s（repo 已有 kustomize blue/green + hpa） | >1000 DAU | 另案 | `k8s/base`+`k8s/prod` 已备 |

**固定项（全估算）**：域名 .com 约 ¥60-80/年（.cn 更低）；SSL 用 Let's Encrypt 免费路径（`scripts/ssl/setup_certs.sh` 已备）；对象存储自托管 MinIO 无额外费用，云 OSS 替代约 ¥10-50/月；SMTP 用国内邮件推送服务约 ¥0-30/月（低量）。

**参展推荐：组合 A 起步，预算约 ¥250-650/月（估算）**——这就是「投资人给钱」的第一张发票量级。

域名/HTTPS/证书方案：
1. 买域名 → DNS A 记录 `api.<域名>` → VPS IP；
2. `sudo certbot certonly --standalone -d api.<域名>`（或云厂商免费证书下载 Nginx 格式）；
3. `scripts/ssl/setup_certs.sh api.<域名> ./ssl` 拷入 `./ssl/`（prod compose :87 挂载 `${SSL_CERT_DIR:-./ssl}` → nginx `/etc/nginx/ssl`）；
4. 续期：`/etc/letsencrypt/renewal-hooks/deploy/` 放拷贝 + `docker compose -f docker-compose.prod.yml exec nginx nginx -s reload`（主方案 §2.3 已有现成草案）。

---

## 3. 一键部署设计（bootstrap 全流程草案）

### 3.0 设计原则

- **入口唯一**：`make cloud-up`（或 `bash scripts/bootstrap_prod.sh`）一条命令走完全部；幂等（重复执行安全）；每步失败即停并打印「下一步人做什么」。
- ** Secrets 三面分离**（§4）：本地 dev 不动；云上用 `.env` + `check_production_secrets.py` 门禁；CI 用 GitHub Secrets 出镜像。
- **先决条件机器可查**：docker/compose 版本、磁盘 ≥20G、内存 ≥7G、80/443 未占用、DNS 已生效、`./ssl/` 有证书、`.env` 过 secret 校验——任何一条不满足直接列出缺项退出。

### 3.1 全流程草案（伪代码 / 分步 shell，本轮不落脚本文件）

```bash
# ============ scripts/bootstrap_prod.sh（草案，本轮不创建） ============
#!/usr/bin/env bash
set -euo pipefail
# 用法: sudo bash scripts/bootstrap_prod.sh --domain api.example.com --image-tag <tag>

step0_preflight() {
  # 0.1 系统自检: ubuntu 22.04+/debian 12, 磁盘 df -m /opt >= 20G, 内存 free >= 7G
  # 0.2 安装 docker + compose v2 (get.docker.com), usermod -aG docker
  # 0.3 ufw: allow 22/80/443; 其余默认 deny（5432/6379/8000/50051/9000/3000/9090 全部只在内网）
  # 0.4 DNS 校验: dig +short $DOMAIN == 本机公网 IP
  # 0.5 [ -f ssl/fullchain.pem && ssl/privkey.pem ] || 提示先跑 scripts/ssl/setup_certs.sh
  # 0.6 python3 scripts/check_production_secrets.py <(grep -v '^#' .env)   # secrets 门禁
}

step1_env() {
  # 交互式或 --env-file 注入 .env（三套差异面见 §4）
  # 生成器草案（替代手填，密钥全部现生成，绝不入库）:
  #   gen() { openssl rand -hex 32; }
  #   写入: SECRET_KEY/JWT_SECRET/ADMIN_SECRET/INTERNAL_API_KEY/POSTGRES_PASSWORD/
  #         REDIS_PASSWORD(+三角色派生)/MINIO_ROOT_PASSWORD/GRAFANA_ADMIN_PASSWORD
  #   人工只填: LLM_API_KEY(至少一个 provider) / ALERTMANAGER_*_WEBHOOK_URL / SMTP_*
  #   RS256: openssl genpkey -algorithm RSA 4096 → JWT_PRIVATE_KEY/JWT_PUBLIC_KEY
  #          (ALGORITHM=RS256, .env.production.example:44-49 的既定方案)
}

step2_images() {
  # 方案一（有 ghcr 权限）: docker compose -f docker-compose.prod.yml pull
  # 方案二（无 CI 产物）: 本机构建（注意 AGENTS.md 硬规则：本地验证 Go 用 CGO_ENABLED=0，
  #   但 Dockerfile 内多阶段构建自带 linux/amd64 工具链，不受本机 Xcode/cgo 影响）
}

step3_gap_fix() {
  # !!! 缺口 #1 的临时绕法（正式修复应改 prod compose 的 db 服务为 build pgvector-age）:
  #   docker build -f docker/pgvector-age.Dockerfile -t sparkle/pgvector-age:pg16 .
  #   以 override compose（docker-compose.prod.override.yml，仅服务器上存在）替换 db 镜像
  # 参展精简（可选，8G 内存时）:
  #   docker compose -f docker-compose.prod.yml up -d \
  #     --scale loki=0 --scale promtail=0 --scale tempo=0 --scale cadvisor=0
}

step4_up() {
  # docker compose -f docker-compose.prod.yml up -d
  # 依赖链自动保证: db healthy → db_migrate(alembic upgrade head) → backend/agent/celery
  # 等待: 轮询 db_migrate 容器 exit 0；backend /health；gateway /api/v1/health
}

step5_age_init() {  # 缺口 #1 的另一半：age 扩展创建不在 Alembic 链内
  # docker compose -f docker-compose.prod.yml exec backend \
  #   python scripts/init_age_extension.py          # ensure vector + age + 默认图谱
  # docker compose -f docker-compose.prod.yml exec backend \
  #   python scripts/init_redis_index.py            # RAG 向量索引（make init-rag 等价）
  # （minio 桶已由 minio_rbac_init one-shot 自动建，无需 make init-minio-buckets）
}

step6_seed() {     # 参展演示数据（§6 详述）
  # docker compose -f docker-compose.prod.yml exec -e LOCAL_SMOKE_PASSWORD=<强密码> backend \
  #   python scripts/seed_demo_user_enhanced.py     # 演示账号+计划+会话+成就+皮肤
  # 可选: python scripts/seed_phase2_demo_data.py / demo_polaris_scenario.py
}

step7_smoke() {
  # 复用现成脚本，不新造轮子:
  #   bash scripts/verify_deployment.sh https://$DOMAIN          # 外部视角健康+延迟
  #   bash scripts/deploy-prod.sh 的 SMOKE_URLS 同款: /api/v1/health /api/v1/health/cqrs
  # 端到端探针（新增逻辑，草案）:
  #   TOKEN=$(curl -fsS -X POST https://$DOMAIN/api/v1/auth/guest | jq -r .access_token)
  #   → 用该 token 发一条 WS 聊天（复用 backend/scripts/e2e_multiturn_test.py 思路，
  #     指向 https://$DOMAIN 而非 localhost）→ 断言收到流式回复
  #   → GET /api/v1/galaxy/* 断言 AGE 图谱可查询（验缺口 #1 修复生效）
}

step8_post() {
  # 备份 cron: crontab 加 scripts/backup_prod_data.sh（KEEP_DAYS=7 已内置）
  # 监控访问: 提示 grafana/prometheus 仅绑 127.0.0.1，用 ssh -L 隧道
  # 打印交付物: 演示账号、APK 出包命令（§7）、本机 .env 备份位置提醒（不打印内容）
}

main() { step0_preflight; step1_env; step2_images; step3_gap_fix; step4_up; step5_age_init; step6_seed; step7_smoke; step8_post; }
```

时间预算（估算）：网络与镜像就绪时，**preflight→smoke 全程 15-30 分钟**；首次冷构建镜像再加 20-40 分钟。

### 3.2 升级路径

日常发版走现成 `scripts/deploy-prod.sh`（蓝绿 + 健康门 + 自动回滚段），bootstrap 只负责「从零到第一次上线」。二者衔接点：bootstrap 最后一步打印 deploy-prod.sh 用法。

---

## 4. Secrets 注入方案：.env 三套差异面

| 维度 | 本地 dev（`.env`，已存在不入库） | 云上 prod（`/opt/sparkle/.env`） | CI（GitHub Secrets） |
|---|---|---|---|
| 模板 | `.env.example`（9.3KB）+ `backend/.env.example` | `.env.production.example`（601 行）→ 复制后全填 | 不落 .env，只喂镜像构建 |
| 密钥强度 | 可弱/占位 | `check_production_secrets.py` 拒绝 `your_`/`replace_with` 前缀（模板 :6-9 自述）；≥32 字符 | 只需 ghcr push 凭据（GITHUB_TOKEN 内置） |
| 数据库 | 本机 localhost:5432 | `sparkle_db:5432` 容器名 + 强密码 + 三角色 RBAC URL（模板 :75-79） | N/A |
| LLM key | 本地个人 key | 专用 key + **预算闸门全开**（见下） | N/A |
| JWT | HS256 默认 | **RS256** 非对称 + key version 轮换位（模板 :44-56） | N/A |
| 网关强制项 | 可缺省 | `TRUSTED_PROXIES`/`ALLOWED_ORIGINS`/`ADMIN_SECRET`/`INTERNAL_API_KEY` 缺失即 crash（prod compose :116-124 `:?`） | N/A |
| 兜底纪律 | — | `.env` chmod 600；永不入 git；**严禁从主仓复制 .env**（AGENTS.md 磁盘纪律） | — |

**云上默认值必须覆盖的三个「演示友好、生产危险」开关**（本卡核心增量结论）：

```bash
# 追加进云上 .env（模板里没有或默认值反着的，全部显式写）:
LLM_QUOTA_ENABLED=true            # 覆盖 settings.py:409 的 False（演示录制默认）
GLM_BATCH_ENABLED=false           # 覆盖 .env.production.example:278 true；停车道云上默认熄火
RUN_BUDGET_DEFAULTS_ENABLED=true  # settings.py:421 默认已是 true，显式钉死
LLM_DAILY_BUDGET_USD=5            # 云上建议从默认 10 收紧起步（settings.py:410；估算：参展 50 人体验远用不满）
RAG_DAILY_BUDGET_USD=1            # 默认 2 收半（settings.py:411）
AURORA_DAILY_BUDGET_USD=2         # 默认 5 收紧（settings.py:412）
BATCH_LANE_DAILY_BUDGET_USD=0.5   # 保持默认（settings.py:631）；即使 glm_batch 意外启用也有 0.5USD 熔断
QUEUE_BACKPRESSURE_LIMITS_JSON={"glm_batch": 200}   # 保持 O-07 现值（settings.py:435）
```

理由链：`cost_controller.py:149-152` 四桶预算 + Redis 有界降级（:125-129）、`queue_backpressure.py` 硬顶、`budget_matrix.py` run 面派生（free 150k tokens/$0.5/run、pro 600k/$2，`settings.py:422-427`）构成三层兜底；`LLM_QUOTA_ENABLED=true` 把用户日配额层（`llm_quota.py:79-93`，`llm_tokens:{uid}:{date}` 100k tokens/日、80% 预警、紧急模式 ×2）补齐为第四层。**四层全开，才敢把 API key 放进投资人可见的服务器。**

---

## 5. 参展演示数据种子方案

**现状**：种料齐全，缺的只是「部署后自动跑一次」的接线（缺口 #6）。

| 料 | 脚本 | 产出 | 生产可用性 |
|---|---|---|---|
| 主演示账号 | `backend/scripts/seed_demo_user_enhanced.py`（`make fixture-init` 的第一半） | 账号 chat_test（密码生产环境必须经 `LOCAL_SMOKE_PASSWORD` 显式注入，:33-35 已防呆）、学习计划×3（含「数据结构期中冲刺」SPRINT 计划，:1186-1225）、聊天会话+消息（:504-530）、任务、成就、星图皮肤/称号（:1121-1137） | 直接可用；幂等（select-then-insert 防重） |
| 社群/知识节点 | `backend/scripts/setup_smoke_test_data.py`（经 `init_local_fixture.py` 第二半） | 社群帖子、知识节点 | 可用 |
| 极光叙事场景 | `backend/scripts/demo_polaris_scenario.py` | 预置光子场景演示 | 需试跑确认（本轮未验证，LIGHT 纪律不跑） |
| 游客即体验 | `auth.py:860` `/guest` → `guest_seed_service.seed_guest_user_data` | 扫码进 app 免注册、自动播种完整体验数据 | **已生产就绪**，是参展漏斗的后端地基 |
| 清场 | `backend/scripts/clean_demo_data.py` | 展后清理演示数据 | 可用 |

**灌入路径**：bootstrap step6（§3.1）在容器内执行 seed 脚本（backend 镜像里已带 scripts/），无需宿主机 venv——比本地 `make fixture-init` 更干净。演示账号密码进 `.env`（`LOCAL_SMOKE_PASSWORD`），海报上的体验入口则走 `/guest` 游客链路，**演示账号本身不上二维码**（防被改密码/灌脏数据）。

---

## 6. 上线前检查单

### 6.1 安全

- [ ] `ENVIRONMENT=production` + `DEBUG=False`（settings 校验器强制，模板 :22-24）
- [ ] 五密钥全换新：SECRET_KEY / JWT_SECRET / ADMIN_SECRET / INTERNAL_API_KEY / POSTGRES_PASSWORD（`openssl rand -hex 32`；`check_production_secrets.py` 通过）
- [ ] JWT 升 RS256 + JWT_ISSUER/AUDIENCE 与网关一致（config.go:538-539 默认 sparkle-gateway/sparkle-app）
- [ ] `TRUSTED_PROXIES` = 本机 docker 网段或 LB IP；`ALLOWED_ORIGINS` 只含 `https://api.<域名>`；`ALLOW_WS_QUERY_TOKEN=false`（模板 :350-356 三项默认已对）
- [ ] nginx 侧已带 HSTS/CSP/X-Frame-Options DENY（nginx.conf:77-82）+ auth 5r/s・chat 10r/s 限速；网关内还有分布式限流中间件（`backend/gateway/internal/middleware/` rate_limit* 全家）——双层限流齐备
- [ ] 密钥轮换位确认：`SPARKLE_JWT_KEY_VERSION=v1` + `SPARKLE_JWT_PREVIOUS_KEY`（模板 :54-56）
- [ ] Android release 包关明文（缺口 #5）；`API_CERT_SHA256` 证书钉扎注入（api_constants.dart:15）
- [ ] Grafana 管理密码非默认；`GF_USERS_ALLOW_SIGN_UP=false`（prod compose :839 已默认）
- [ ] ufw 只开 22/80/443；数据面端口全部内网（compose `app` 网络 `internal: true`）

### 6.2 成本

- [ ] §4 的 8 行预算 env 全部落 .env；`LLM_QUOTA_ENABLED=true` 为部署验收必查项
- [ ] **glm_batch 停车道处置**：云上默认不起专用 worker（`docker compose ... up -d --scale celery_glm_batch_worker=0`，或 GLM_BATCH_ENABLED=false 双保险）；确需离线批处理时：先 `celery-flush` 语义清空 glm_batch 队列 → 手动拉起 → 用完即停。验收探针：`sparkle_queue_backpressure_drops_total{queue="glm_batch"}` 有增长且费用面无异常即健康
- [ ] 预算熔断演练（可选项，上线一周内）：人工把 LLM_DAILY_BUDGET_USD 调到 0.01 观察 BUDGET_EXCEEDED 终态 UX（`backend/app/api/v1/chat.py:517` 预算终态不进自我修正；`run_state_machine.py` BUDGET_EXCEEDED 终态）
- [ ] 备份 cron 就位 + 首次备份落盘校验（backup_prod_data.sh 自带 sha256）
- [ ] LLM provider 至少两个 key（主 + 备 provider，模板 :153-243 的多 provider 面已支持故障切换）

### 6.3 可观测（最小集）

- [ ] 保留：prometheus + grafana + alertmanager + node_exporter（资源占用小、看板现成：`monitoring/grafana-dashboards/`）
- [ ] 8G 单机裁掉：loki/promtail/tempo/cadvisor（估算省 ~1.5G 内存上限；日志用 `docker compose logs --since` 兜底）——16G 则全套保留
- [ ] alertmanager webhook 必填（compose `:?` 硬门，:711-713）——参展期接一个微信群机器人 webhook 即可
- [ ] 首查面板四件套：`sparkle_queue_depth`（背压）、`COST_DAILY_BUDGET_USD`/`BUDGET_UTILIZATION`（成本桶）、`sparkle_queue_backpressure_drops_total`、网关 /health 与 /api/v1/health/cqrs（make smoke 同款三探针，Makefile:144-180）
- [ ] SLO 告警文件已挂载（prod compose :676-682 六份告警规则），参展期至少保留 baseline 与 SLO 两组

---

## 7. 移动端出包（参展 sideload 分发）

```bash
cd mobile && flutter build apk --release \
  --dart-define=API_BASE_URL=https://api.<域名> \
  --dart-define=WS_BASE_URL=wss://api.<域名> \
  --dart-define=API_CERT_SHA256=<Pin 提取> \
  --dart-define=ENABLE_GOOGLE_SERVICES=false \
  --dart-define=FCM_ENABLED=false        # 国内市场变体（Makefile:480-482 mobile-build-china 同款）
```

证据：api_constants.dart:7-15（三个 dart-define 钩子）+ :37-45（override 优先于平台兜底）；Makefile:480-482（中国版参数先例）。**缺口 #5 修复前，release 包明文开关仍开着**——出包检查单里必须含「反编译确认无 cleartext」或先修 manifest。

---

## 8. 结论

「投资人给钱即可上线」的真实距离 = **两个 P0 补丁**（AGE 镜像接进 prod compose + age 初始化进流程；bootstrap 总入口脚本）+ **一张云上 .env 默认值表**（§4，尤其三个演示友好开关）+ **一条 seed 接线**。其余（蓝绿、备份、监控、证书、镜像 CI、游客体验）全部已在仓库里，这是本项目对投资人最有说服力的资产之一——方案不是「我们要做」，而是「补三个缺口，把已有的东西串起来」。
