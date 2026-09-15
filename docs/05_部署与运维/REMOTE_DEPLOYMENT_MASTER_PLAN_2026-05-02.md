# Sparkle 远端部署主方案 (Master Plan)

> **文档性质**: 从当前状态到远端部署的完整多阶段实施方案
> **版本**: 1.1.0（含批判性审查修正）
> **日期**: 2026-05-02
> **前提假设**: 拥有一台公网服务器（Linux x86_64，8C16G+，Ubuntu 22.04+），一个域名，基本的 Linux 运维能力

---

## 全局架构：目标拓扑

```
┌─────────────────────────────────────────────────────────────────┐
│  用户手机 (Flutter App)                                         │
│  API_BASE_URL=https://api.sparkle.com                          │
│  WS_BASE_URL=wss://api.sparkle.com                             │
└──────────────┬──────────────────────────────────────────────────┘
               │ HTTPS / WSS (TLS 1.2+)
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  服务器 (公网 IP: x.x.x.x)                                      │
│                                                                 │
│  ┌──────────────┐                                               │
│  │  Nginx       │  :80 → 301 redirect → :443                   │
│  │  :443 TLS    │──┼──> gateway_blue:8080  (active)            │
│  │  :80         │──┼──> gateway_green:8080 (standby)           │
│  └──────┬───────┘  │                                           │
│         │          │  Docker Network: sparkle_app (internal)    │
│  ┌──────▼───────┐  │                                           │
│  │  Go Gateway  │──┘  :8080                                    │
│  │  (Blue/Green)│                                              │
│  └──┬──────┬────┘                                              │
│     │gRPC¹ │HTTP                                               │
│  ┌──▼──┐  ┌▼──────────┐                                       │
│  │Agent│  │Backend API│  :8000                                 │
│  │:50051  │:8000      │                                        │
│  │  ²   │  │          │                                        │
│  └──┬──┘  └──┬────────┘                                       │
│     │        │                                                  │
│  ┌──▼────────▼──┐  ┌──────────┐  ┌───────┐                    │
│  │  PostgreSQL   │  │  Redis   │  │ MinIO │                    │
│  │  :5432        │  │  :6379   │  │ :9000 │                    │
│  │  pgvector+AGE │  │  Stack   │  │       │                    │
│  └───────────────┘  └──────────┘  └───────┘                    │
│                                                                 │
│  ┌─────────────────────────────────────────────┐                │
│  │  监控: Prometheus + Grafana + Loki + Tempo  │                │
│  │  (仅绑定 127.0.0.1，通过 SSH 隧道访问)        │                │
│  └─────────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────┘

¹ gRPC 在单机 Docker 部署中走内部网络（sparkle_app），无需 TLS；
  跨主机/多节点部署时需启用 GRPC_REQUIRE_TLS=true 并提供证书。
² Agent 高并发下内存可达 3-4GB，见附录 B 调整。
```

---

## 阶段总览

| 阶段 | 名称 | 目标 | 预估时间 | 前置依赖 |
|------|------|------|---------|---------|
| P0 | 现状盘点与前置条件 | 确认现有资产，准备外部资源 | 0.5 天 | 无 |
| P1 | 服务器基础设施 | 服务器就绪，DNS 解析，防火墙 | 1 天 | P0 |
| P2 | 代码层修复 | 修复部署阻塞问题 | 1-2 天 | 无（可与 P1 并行） |
| P3 | Docker 部署上线 | 全栈服务启动，内部连通 | 1 天 | P1 + P2 |
| P4 | 移动端远端适配 | Flutter 可连接远端服务器 | 1 天 | P3 |
| P5 | 端到端验证 | 全链路功能验收 | 1 天 | P3 + P4 |
| P6 | 生产加固 | 安全、监控、备份、合规 | 3-5 天 | P5 |
| P7 | 持续运维 | 日志、告警、升级流程 | 持续 | P6 |

**关键路径**: P0 → P1 → P3 → P4 → P5 → P6
**可并行**: P2 可与 P1 同时进行

---

## Phase 0: 现状盘点与前置条件

### 0.1 现有资产清单

#### 服务器端 — 已就绪

| 资产 | 文件 | 状态 |
|------|------|------|
| 开发 Docker Compose | `docker-compose.yml` | ✅ 17 服务，完整 |
| 生产 Docker Compose | `docker-compose.prod.yml` | ⚠️ 需修复 AGE 镜像 |
| Python Dockerfile | `backend/Dockerfile` | ✅ 多阶段，非 root |
| Go Gateway Dockerfile | `backend/gateway/Dockerfile` | ✅ 多阶段，非 root |
| PG+AGE Dockerfile | `docker/pgvector-age.Dockerfile` | ✅ pgvector + AGE |
| Nginx 配置 | `nginx/nginx.conf` + `upstream.conf` | ✅ TLS + 蓝绿 |
| 蓝绿部署脚本 | `scripts/deploy-prod.sh` | ✅ 含回滚 |
| 备份恢复脚本 | `scripts/backup_prod_data.sh` | ✅ |
| 环境变量模板 | `.env.example` (245 行) | ✅ |
| 监控栈 | `monitoring/` | ✅ 全套 |
| K8s 清单 | `k8s/` | ✅ Kustomize 蓝绿 |
| CI/CD | `.github/workflows/cd_k8s.yml` | ✅ |

#### 服务器端 — 需修复

| 问题 | 严重度 | 详见 |
|------|--------|------|
| prod DB 镜像缺少 AGE | P0 | Phase 2 任务 2.1 |
| 无 SSL 证书自动化 | P0 | Phase 2 任务 2.3 |
| Gateway 默认配置 localhost | P1 | Phase 2 任务 2.2 |
| 生产部署无 migration 步骤 | P1 | Phase 2 任务 2.4 |

#### 移动端 — 需修复

| 问题 | 严重度 | 详见 |
|------|--------|------|
| 默认 URL 全 localhost | P0 | Phase 4 任务 4.1 |
| Android 明文全开 | P1 | Phase 6 任务 6.2 |
| iOS ATS 全禁用 | P1 | Phase 6 任务 6.3 |
| Application ID 占位符 | P1 | Phase 6 任务 6.1 |

### 0.2 外部资源准备清单

| 资源 | 说明 | 获取方式 |
|------|------|---------|
| 公网服务器 | 8C16G+，100GB SSD，Ubuntu 22.04 | 云服务商购买 |
| 域名 | 如 `sparkle.com` 或 `sparkle-app.cn` | 域名注册商 |
| SSL 证书 | 通配符或单域名 | Let's Encrypt (免费) 或云服务商 |
| LLM API Key | 至少一个 provider (DeepSeek/智谱/OpenAI) | 各 AI 平台注册 |
| SMTP 服务 | 用于邮件验证和密码重置 | SendGrid/Mailgun 或自建 |
| 推送服务 | JPush (国内) 或 FCM (海外) | 极光/Google 注册 |

### 0.3 服务器最低配置

```
CPU:      8 核 (AI 推理 + Go + Python + DB)
内存:     16 GB (Agent 2G + API 1G + DB 2G + Redis 4G + 其他 ~4G)
存储:     100 GB SSD (DB + 日志 + 对象存储)
带宽:     10 Mbps+ (WebSocket 长连接)
系统:     Ubuntu 22.04 LTS / Debian 12
Docker:   v24+ with Compose v2
```

**注意**: 如果使用外部 LLM API（非本地部署），内存可降至 8GB。如果 MinIO 对象存储使用云 OSS 替代，存储可降至 50GB。

---

## Phase 1: 服务器基础设施准备

### 1.1 服务器初始化

```bash
# 1. 系统更新
sudo apt update && sudo apt upgrade -y

# 2. 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 3. 安装 Docker Compose (通常随 Docker 一起安装)
docker compose version

# 4. 创建应用目录
sudo mkdir -p /opt/sparkle
sudo chown $USER:$USER /opt/sparkle

# 5. 安装辅助工具
sudo apt install -y certbot nginx curl git
```

### 1.2 DNS 配置

```
# 在域名 DNS 管理面板添加:
A    api.sparkle.com        → 服务器公网 IP
A    sparkle.com             → 服务器公网 IP (官网, 可选)
CNAME www.sparkle.com        → sparkle.com (可选)
```

### 1.3 防火墙规则

```bash
# 仅开放必要端口
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (certbot 验证 + 重定向)
sudo ufw allow 443/tcp     # HTTPS + WSS
sudo ufw enable

# 确认以下端口 **不** 对外开放 (仅 Docker 内部通信):
# 5432  PostgreSQL
# 6379  Redis
# 8000  Python FastAPI
# 50051 gRPC
# 9000  MinIO API
# 3000  Grafana
# 9090  Prometheus
```

### 1.4 SSL 证书获取

```bash
# 方案 A: Let's Encrypt (推荐)
sudo certbot certonly --standalone -d api.sparkle.com

# 证书文件位置:
# /etc/letsencrypt/live/api.sparkle.com/fullchain.pem
# /etc/letsencrypt/live/api.sparkle.com/privkey.pem

# 自动续期 (certbot 自动添加 cron)
sudo certbot renew --dry-run

# 方案 B: 云服务商免费证书 (如阿里云/腾讯云)
# 下载 Nginx 格式证书
```

### 1.5 代码部署到服务器

```bash
# 方案 A: Git Clone (推荐)
cd /opt/sparkle
git clone https://github.com/BRSAMAyu/Sparkle-project.git .
# 切换到目标分支
git checkout main  # 或特定 release tag

# 方案 B: Docker 镜像 (CI/CD 自动构建)
# 在 GitHub Actions 构建后直接 pull
docker compose -f docker-compose.prod.yml pull
```

**验证点**:
- [ ] 服务器 SSH 可连接
- [ ] Docker 运行正常 (`docker run hello-world`)
- [ ] DNS 解析正确 (`nslookup api.sparkle.com`)
- [ ] 防火墙仅开放 22/80/443
- [ ] SSL 证书获取成功
- [ ] 代码已克隆到 `/opt/sparkle`

---

## Phase 2: 代码层修复

> 本阶段所有修改在本地开发环境完成，通过 git commit + push 到服务器。

### 2.1 修复生产数据库镜像 (P0 — 阻塞)

**问题**: `docker-compose.prod.yml:370` 使用 `pgvector/pgvector:pg16`，缺少 AGE 扩展，知识星图功能不可用。

**修复**: `docker-compose.prod.yml`

```yaml
# 修改前 (约第 369-374 行):
  db:
    image: pgvector/pgvector:pg16

# 修改后:
  db:
    build:
      context: .
      dockerfile: docker/pgvector-age.Dockerfile
      args:
        AGE_REF: PG16/v1.6.0-rc0
```

同步调整 db 服务的 environment 和 healthcheck 保持不变，确保 PostgreSQL 调优参数保留。

### 2.2 修复 Gateway 默认配置 (P1)

**问题**: Go Gateway 多个默认值指向 localhost，虽然 docker-compose 覆盖了，但应修正以避免手动部署时踩坑。

**修复**: `backend/gateway/internal/config/config.go`

```go
// 修改第 452 行:
// 旧: viper.SetDefault("AGENT_ADDRESS", "localhost:50051")
// 新: viper.SetDefault("AGENT_ADDRESS", "sparkle_agent:50051")

// 修改第 478 行:
// 旧: viper.SetDefault("BACKEND_URL", "http://localhost:8000")
// 新: viper.SetDefault("BACKEND_URL", "http://sparkle_api:8000")

// 修改第 488 行:
// 旧: viper.SetDefault("MINIO_ENDPOINT", "localhost:9000")
// 新: viper.SetDefault("MINIO_ENDPOINT", "minio:9000")
```

同时更新 `backend/gateway/.env.example:23`:
```
# 修改:
# 旧: AGENT_ADDRESS=localhost:50051
# 新: AGENT_ADDRESS=sparkle_agent:50051
```

### 2.3 添加 SSL 证书自动化脚本 (P0)

创建 `scripts/ssl/setup_certs.sh`:

```bash
#!/usr/bin/env bash
# 从 Let's Encrypt 复制证书到项目 ssl/ 目录
set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain>}"
CERT_DIR="${2:-./ssl}"
SRC="/etc/letsencrypt/live/$DOMAIN"

mkdir -p "$CERT_DIR"
cp "$SRC/fullchain.pem" "$CERT_DIR/fullchain.pem"
cp "$SRC/privkey.pem"   "$CERT_DIR/privkey.pem"
chmod 644 "$CERT_DIR/fullchain.pem"
chmod 600 "$CERT_DIR/privkey.pem"

echo "✅ SSL certificates copied to $CERT_DIR"
```

添加证书续期 hook 到 `/etc/letsencrypt/renewal-hooks/deploy/01-copy-to-sparkle.sh`:
```bash
#!/bin/bash
DOMAIN="api.sparkle.com"
cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" /opt/sparkle/ssl/fullchain.pem
cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" /opt/sparkle/ssl/privkey.pem
chmod 600 /opt/sparkle/ssl/privkey.pem
# 重载 Nginx 容器
cd /opt/sparkle && docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

### 2.4 生产部署加入 DB 迁移步骤 (P1)

**修复**: 在 `scripts/deploy-prod.sh` 中，启动 backend 服务前加入迁移步骤:

```bash
# 在启动 backend 服务之前，添加:
echo ">>> Running database migrations..."
docker compose -f docker-compose.prod.yml run --rm backend \
  alembic upgrade head
echo "✅ Migrations complete"
```

### 2.5 修复 Gateway .env.example 中的 AGENT_ADDRESS

```bash
# backend/gateway/.env.example 第 23 行:
# 旧: AGENT_ADDRESS=localhost:50051
# 新: AGENT_ADDRESS=sparkle_agent:50051
```

### 2.6 合并安全修复分支 (前置依赖)

当前 `fix/quality-audit-deep-2026-05-02` 分支包含以下 P1 安全修复，**必须先合并到 main** 再执行部署：

| 修复项 | 影响范围 | 文件 |
|--------|---------|------|
| P1-Go-1 PII 明文日志 → hashUserIDForLog | 5 个 handler 文件 | `gateway/internal/handler/*.go` |
| P1-Sec-1 gRPC TLS 配置验证 | Agent 启动 | `docker-compose.prod.yml:259` |
| P1-Go-3 JWT audience 时序攻击 | 认证流程 | `gateway/internal/middleware/auth.go` |

```bash
# 确认修复分支已合并:
git log --oneline main..fix/quality-audit-deep-2026-05-02 | head -5
# 如果未合并:
git checkout main
git merge fix/quality-audit-deep-2026-05-02
git push origin main
```

> **⚠️ 警告**: 跳过此步骤将导致生产环境存在 PII 泄露风险。

**验证点**:
- [ ] `docker-compose.prod.yml` 的 db 服务使用 AGE 镜像
- [ ] Gateway 默认值指向 Docker 服务名而非 localhost
- [ ] SSL 证书脚本可执行
- [ ] 部署脚本包含迁移步骤
- [ ] 安全修复分支 (`fix/quality-audit-deep-2026-05-02`) 已合并到 main
- [ ] 所有修改已 commit + push

---

## Phase 3: Docker 部署上线

### 3.1 环境变量配置

```bash
cd /opt/sparkle
cp .env.example .env
```

编辑 `.env`，**必须修改**的变量:

```bash
# === 必改项 ===
ENVIRONMENT=production
DEBUG=False

# 数据库
POSTGRES_PASSWORD=<强密码，32字符+>
DB_PASSWORD=<同上>
DATABASE_URL=postgresql://sparkle_admin:<密码>@db:5432/sparkle

# Redis
REDIS_PASSWORD=<强密码，32字符+>
REDIS_URL=redis://:<密码>@redis:6379/0

# 安全密钥 (用 openssl rand -hex 32 生成)
JWT_SECRET=<生成>
SECRET_KEY=<生成>
INTERNAL_API_KEY=<生成>
ADMIN_SECRET=<生成>

# AI 服务 (至少配置一个)
LLM_API_KEY=<API Key>
LLM_API_BASE_URL=https://api.deepseek.com/v1  # 或其他 provider

# 对象存储
MINIO_ROOT_USER=<用户名>
MINIO_ROOT_PASSWORD=<强密码>
MINIO_ACCESS_KEY=<同 MINIO_ROOT_USER>
MINIO_SECRET_KEY=<同 MINIO_ROOT_PASSWORD>

# Celery 任务队列（docker-compose.prod.yml 通过 Redis URL 自动推导，
# 但显式声明更安全）
CELERY_BROKER_URL=redis://:<REDIS密码>@redis:6379/1
CELERY_RESULT_BACKEND=redis://:<REDIS密码>@redis:6379/2

# SSL
SSL_CERT_DIR=./ssl

# 镜像 (如果走本地构建)
IMAGE_TAG=latest
GATEWAY_IMAGE=sparkle-gateway
BACKEND_IMAGE=sparkle-backend

# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=<强密码>
```

### 3.2 SSL 证书就位

```bash
# 复制证书到项目
bash scripts/ssl/setup_certs.sh api.sparkle.com ./ssl

# 验证
ls -la ssl/
# 应看到 fullchain.pem 和 privkey.pem
```

### 3.2b PostgreSQL 性能调优 (可选但推荐)

`docker-compose.prod.yml` 已通过 PG command 参数预设了调优值，可通过 `.env` 覆盖:

```bash
# 在 .env 中添加 (根据服务器配置调整):
POSTGRES_MAX_CONNECTIONS=200       # 默认 200
POSTGRES_SHARED_BUFFERS=256MB      # 物理内存的 25%，建议不超过 1GB
POSTGRES_EFFECTIVE_CACHE_SIZE=768MB # 物理内存的 50-75%
POSTGRES_WORK_MEM=16MB             # 每个排序/哈希操作的内存
POSTGRES_MAINTENANCE_WORK_MEM=128MB # VACUUM/CREATE INDEX 内存
```

> 这些参数已内置于 docker-compose.prod.yml 的 db command 中，
> 仅在需要偏离默认值时才需在 .env 中显式设置。

### 3.3 构建与启动

```bash
# 构建所有镜像 (首次较慢，约 10-20 分钟)
docker compose -f docker-compose.prod.yml build

# 启动基础设施
docker compose -f docker-compose.prod.yml up -d db redis minio

# 等待健康检查通过
echo "Waiting for DB and Redis..."
sleep 15
docker compose -f docker-compose.prod.yml ps  # 确认 healthy

# 运行数据库迁移
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 初始化 AGE 扩展和图 schema
# 注意: init_age_extension.py 已包含扩展检查 + 基础 schema（图谱 + 基本顶点/边标签）
docker compose -f docker-compose.prod.yml run --rm backend \
  python scripts/init_age_extension.py

# 可选: init_graph_schema.py 基于 GraphSchema 模型创建完整标签集，
# 如果 init_age_extension.py 的基础标签不够用，追加执行:
# docker compose -f docker-compose.prod.yml run --rm backend \
#   python scripts/init_graph_schema.py

# 启动应用服务
docker compose -f docker-compose.prod.yml up -d backend agent celery_worker celery_beat

# 等待应用就绪 (约 30-60s)
sleep 30
docker compose -f docker-compose.prod.yml ps

# 启动 Gateway (蓝绿)
docker compose -f docker-compose.prod.yml up -d gateway_blue gateway_green

# 启动 Nginx
docker compose -f docker-compose.prod.yml up -d nginx

# 启动监控
docker compose -f docker-compose.prod.yml up -d prometheus grafana loki tempo promtail alertmanager
```

### 3.3b 创建初始测试用户

首次部署后数据库为空，Phase 5 验收需要用户数据:

```bash
# 创建测试用户 + 演示数据 (成就、星图、社区等)
docker compose -f docker-compose.prod.yml run --rm backend \
  python scripts/seed_demo_user_enhanced.py

# 验证用户已创建
docker compose -f docker-compose.prod.yml exec db \
  psql -U sparkle_admin -d sparkle -c "SELECT id, username FROM users LIMIT 5;"
```

> **⚠️ 注意**: 此脚本创建的是演示用户，密码为开发默认值。
> Phase 6 上线前应删除或修改此用户密码。
>
> 如果只需要一个空用户用于手动注册测试，可以跳过此步骤 —
> App 的注册流程会自动创建用户。但成就系统、星图、社区等需要
> 种子数据才能在 Phase 5 中完整验收。

### 3.4 部署后验证

```bash
# 1. 所有服务运行状态
docker compose -f docker-compose.prod.yml ps
# 期望: 所有服务 healthy 或 running

# 2. Gateway 健康检查
curl -k https://api.sparkle.com/health
# 期望: {"status": "ok", ...}

# 3. 内部连通性 (在服务器上)
curl http://localhost:8080/healthz     # Gateway liveness
curl http://localhost:8080/readyz      # Gateway readiness
curl http://localhost:8000/health      # Python API

# 4. TLS 验证
curl -vI https://api.sparkle.com 2>&1 | grep "SSL connection"
# 期望: SSL connection using TLSv1.3

# 5. WebSocket 验证
wscat -c wss://api.sparkle.com/ws/chat
# 期望: 连接建立 (可能返回 401，但说明链路通)

# 5b. 确认 WebSocket 长连接超时配置
grep proxy_read_timeout /opt/sparkle/nginx/nginx.conf
# 期望: proxy_read_timeout 3600s (已预配置，防止 60s 默认超时导致断连)

# 6. gRPC 验证 (服务器内部)
docker compose -f docker-compose.prod.yml exec agent \
  python -c "import socket; s=socket.socket(); s.settimeout(3); s.connect(('localhost',50051)); s.close(); print('gRPC OK')"
```

**验证点**:
- [ ] 所有 Docker 容器 healthy
- [ ] `https://api.sparkle.com/health` 返回 200
- [ ] TLS 证书有效
- [ ] WebSocket 可建立连接
- [ ] `proxy_read_timeout 3600s` 已确认（Nginx 长连接）
- [ ] PostgreSQL 调优参数已生效（`SHOW shared_buffers;`）
- [ ] 测试用户/种子数据已创建
- [ ] Prometheus 可抓取指标
- [ ] Grafana 可访问 (通过 SSH 隧道)

---

## Phase 4: 移动端远端适配

### 4.1 Flutter 构建配置

Flutter 已支持通过 `--dart-define` 传入远端 URL:

```bash
# Android APK 构建 (连接远端服务器)
flutter build apk \
  --dart-define=API_BASE_URL=https://api.sparkle.com \
  --dart-define=WS_BASE_URL=wss://api.sparkle.com \
  --dart-define=API_CERT_SHA256=<SHA-256指纹>

# Android App Bundle (上架 Play Store)
flutter build appbundle \
  --dart-define=API_BASE_URL=https://api.sparkle.com \
  --dart-define=WS_BASE_URL=wss://api.sparkle.com

# iOS 构建
flutter build ios \
  --dart-define=API_BASE_URL=https://api.sparkle.com \
  --dart-define=WS_BASE_URL=wss://api.sparkle.com
```

获取证书 SHA-256 指纹:
```bash
echo | openssl s_client -connect api.sparkle.com:443 2>/dev/null | \
  openssl x509 -pubkey -noout | \
  openssl pkey -pubin -outform DER | \
  openssl dgst -sha256 -binary | base64
```

### 4.2 验证 URL 解析逻辑

确认 `mobile/lib/core/constants/api_constants.dart` 的行为:
- `_baseUrlOverride` 非空时直接使用 (✅ 正确)
- `wsBaseUrl` 从 `API_BASE_URL` 自动推导为 `wss://` (✅ 正确)
- Release 模式下会警告不安全连接 (✅ 有提示)

### 4.3 构建 Makefile 快捷命令

在 `Makefile` 中添加:

```makefile
# === 远端部署构建 ===
SERVER_URL ?= https://api.sparkle.com
WS_URL ?= wss://api.sparkle.com
CERT_HASH ?=

mobile-build-prod-apk:
	cd mobile && flutter build apk \
		--dart-define=API_BASE_URL=$(SERVER_URL) \
		--dart-define=WS_BASE_URL=$(WS_URL) \
		$(if $(CERT_HASH),--dart-define=API_CERT_SHA256=$(CERT_HASH),)

mobile-build-prod-ios:
	cd mobile && flutter build ios \
		--dart-define=API_BASE_URL=$(SERVER_URL) \
		--dart-define=WS_BASE_URL=$(WS_URL) \
		$(if $(CERT_HASH),--dart-define=API_CERT_SHA256=$(CERT_HASH),)
```

使用:
```bash
make mobile-build-prod-apk SERVER_URL=https://api.sparkle.com CERT_HASH=sha256/xxxx
```

### 4.4 本地验证

在构建前，可以用开发模式快速验证远端连通:

```bash
# iOS 模拟器连远端
flutter run \
  --dart-define=API_BASE_URL=https://api.sparkle.com \
  --dart-define=WS_BASE_URL=wss://api.sparkle.com

# Android 模拟器连远端 (注意: 10.0.2.2 不会指向远端)
flutter run \
  --dart-define=API_BASE_URL=https://api.sparkle.com \
  --dart-define=WS_BASE_URL=wss://api.sparkle.com
```

### 4.5 网络安全配置 — Debug/Release 双轨策略

> **⚠️ 重要**: ATS 收紧和 network_security_config 必须区分 debug/release，
> 否则 Phase 4 本地验证时将无法连接 localhost。此处仅做条件配置，
> 硬性收紧放在 Phase 6。

**Android — 条件式安全配置**（立即创建）:

创建 `mobile/android/app/src/main/res/xml/network_security_config.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <!-- Release: 仅允许生产域名 -->
    <domain-config cleartextTrafficPermitted="false">
        <domain includeSubdomains="true">sparkle.com</domain>
    </domain-config>

    <!-- Debug: 允许本地开发 -->
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>
</network-security-config>
```

在 `AndroidManifest.xml` 添加引用:
```xml
<application android:networkSecurityConfig="@xml/network_security_config" ...>
```

> 此配置 debug 包仍可连接 localhost，release 包仅允许 sparkle.com。
> Phase 6 将添加证书固定（pin-set）。

**iOS — 暂保持宽松 ATS**:

当前 `NSAllowsArbitraryLoads=true` 保持不变直到 Phase 6。
在 Phase 4 本地验证阶段，需同时测试 localhost（模拟器）和远端（真机）。
收紧 ATS 移至 Phase 6，届时所有验证已完成。

**验证点**:
- [ ] Flutter 编译通过
- [ ] App 启动后 API_BASE_URL 日志显示正确
- [ ] 注册/登录请求到达服务器 (查看 Gateway 日志)
- [ ] WebSocket 连接建立成功
- [ ] Android network_security_config.xml 已创建（debug 放行 localhost，release 限域名）
- [ ] 本地开发模式仍可连接 localhost

---

## Phase 5: 端到端功能验证

### 5.1 基础连通性测试

```bash
# 从手机 (安装构建好的 APK) 测试:

1. 注册新用户
   → 检查: 服务器 gateway 日志出现 POST /api/v1/auth/register 200

2. 登录
   → 检查: 获得 access_token + refresh_token

3. WebSocket 连接
   → 检查: gateway 日志出现 WebSocket upgrade, 连接建立

4. 发送聊天消息
   → 检查: gRPC → Python Agent → LLM 调用 → 流式响应
```

### 5.2 核心功能验收矩阵

| # | 功能 | 测试方法 | 依赖服务 | 预期结果 |
|---|------|---------|---------|---------|
| 1 | 用户注册/登录 | App 注册 → 登录 | Gateway + DB | 200, token 返回 |
| 2 | AI 对话 | 发送消息 → 等待回复 | Gateway → Agent → LLM | 流式文本返回 |
| 3 | 任务管理 | 创建/完成/放弃任务 | Gateway + DB | CRUD 正常 |
| 4 | 计划管理 | 创建计划 → 生成任务 | Agent + DB | 计划 + 子任务创建 |
| 5 | 知识星图 | 查看星图 | Agent + pgvector + AGE | 节点渲染 |
| 6 | 成就系统 | 完成任务查看成就 | Agent + DB | 成就解锁 |
| 7 | 社区功能 | 查看动态/加好友 | Gateway + DB | 社区数据返回 |
| 8 | 文件上传 | 上传图片 | Gateway + MinIO | 文件存储成功 |
| 9 | 专注模式 | 开始专注计时 | Agent + DB | 计时器运行 |
| 10 | 离线恢复 | 断网→发消息→重连 | WebSocket + Isar | 消息补发成功 |

### 5.3 服务器端日志排查

```bash
# Gateway 日志
docker compose -f docker-compose.prod.yml logs -f gateway_blue --tail=100

# Python Agent 日志
docker compose -f docker-compose.prod.yml logs -f agent --tail=100

# Python API 日志
docker compose -f docker-compose.prod.yml logs -f backend --tail=100

# 数据库连接
docker compose -f docker-compose.prod.yml exec db \
  psql -U sparkle_admin -d sparkle -c "SELECT count(*) FROM users;"

# Redis 连接
docker compose -f docker-compose.prod.yml exec redis \
  redis-cli -a <密码> ping
```

**验证点**:
- [ ] 注册登录通过
- [ ] AI 对话有流式响应
- [ ] 任务/计划 CRUD 正常
- [ ] 知识星图可加载
- [ ] WebSocket 断连重连正常
- [ ] 无 500 错误 (检查日志)

---

## Phase 6: 生产加固

### 6.1 Application ID 修正

**文件**: `mobile/android/app/build.gradle.kts`

```kotlin
// 修改:
// 旧: applicationId = "com.example.sparkle"
// 新: applicationId = "com.sparkle.app"  // 或你的实际包名
```

**文件**: `mobile/ios/Runner.xcodeproj/project.pbxproj`
- 修改 PRODUCT_BUNDLE_IDENTIFIER 为 `com.sparkle.app`

### 6.2 Android 网络安全加固

**创建**: `mobile/android/app/src/main/res/xml/network_security_config.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <!-- 生产域名: 强制 HTTPS -->
    <domain-config cleartextTrafficPermitted="false">
        <domain includeSubdomains="true">sparkle.com</domain>
        <pin-set>
            <pin digest="SHA-256">你的证书指纹</pin>
            <pin digest="SHA-256">备用证书指纹</pin>
        </pin-set>
    </domain-config>

    <!-- 本地开发 (仅 debug) -->
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>
</network-security-config>
```

**修改**: `mobile/android/app/src/main/AndroidManifest.xml`

```xml
<!-- 添加 android:networkSecurityConfig -->
<application
    android:networkSecurityConfig="@xml/network_security_config"
    ...>
```

### 6.3 iOS ATS 收紧

> **前置**: Phase 4.5 已完成 Android 网络安全双轨配置。
> 此处收紧 iOS ATS，此时所有远端验证已通过（Phase 5），收紧不会影响开发。

**文件**: `mobile/ios/Runner/Info.plist`

```xml
<!-- 替换现有 NSAppTransportSecurity 部分: -->
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <false/>
    <key>NSAllowsLocalNetworking</key>
    <true/>
    <key>NSExceptionDomains</key>
    <dict>
        <key>sparkle.com</key>
        <dict>
            <key>NSIncludesSubdomains</key>
            <true/>
            <key>NSTemporaryExceptionMinimumTLSVersion</key>
            <string>TLSv1.2</string>
        </dict>
    </dict>
</dict>
```

同时为 Android network_security_config.xml 添加证书固定（在 Phase 4.5 基础上增强）:

```xml
<!-- 在 sparkle.com 的 domain-config 中添加 pin-set: -->
<domain-config cleartextTrafficPermitted="false">
    <domain includeSubdomains="true">sparkle.com</domain>
    <pin-set>
        <pin digest="SHA-256">你的证书指纹</pin>
        <pin digest="SHA-256">备用证书指纹（用于证书轮换）</pin>
    </pin-set>
</domain-config>
```

### 6.4 第三方服务密钥配置

替换所有占位符:

| 服务 | 占位符 | 操作 |
|------|--------|------|
| JPush | `YOUR_JPUSH_APPKEY` | 注册极光推送，填入真实 Key |
| WeChat | `YOUR_WECHAT_APP_ID` | 注册微信开放平台 |
| Google | `YOUR-CLIENT-ID` | 注册 Google Cloud Console |

如果暂时不使用某服务，可先注释掉相关代码。

### 6.5 监控访问安全

```bash
# Grafana 通过 SSH 隧道访问 (不要对外开放)
ssh -L 3000:127.0.0.1:3000 user@sparkle.com
# 然后在浏览器打开 http://localhost:3000

# Prometheus 同理
ssh -L 9090:127.0.0.1:9090 user@sparkle.com
```

`docker-compose.prod.yml` 已正确绑定 `127.0.0.1`:
- Grafana: `127.0.0.1:3000:3000`
- Prometheus: `127.0.0.1:9090:9090`
- Loki: `127.0.0.1:3100:3100`

### 6.6 数据库备份自动化

```bash
# 添加到 crontab (每天凌晨 3 点)
crontab -e
# 添加:
0 3 * * * /opt/sparkle/scripts/backup_prod_data.sh >> /opt/sparkle/logs/backup.log 2>&1
```

### 6.7 日志轮转

```bash
# Docker 日志轮转
# 创建 /etc/docker/daemon.json:
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  }
}

sudo systemctl restart docker
```

**验证点**:
- [ ] Application ID 已更改
- [ ] Android network_security_config.xml 存在
- [ ] iOS ATS 已收紧
- [ ] 第三方 Key 已替换或注释
- [ ] 监控端口不对外暴露
- [ ] 备份 cron 已设置
- [ ] Docker 日志轮转已配置

---

## Phase 7: 持续运维

### 7.1 日常运维命令

```bash
# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看实时日志
docker compose -f docker-compose.prod.yml logs -f --tail=50

# 重启单个服务
docker compose -f docker-compose.prod.yml restart gateway_blue

# 蓝绿切换
bash scripts/deploy-prod.sh switch

# 数据库迁移 (新版本上线时)
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
```

### 7.2 升级流程

```bash
# 1. 拉取最新代码
cd /opt/sparkle && git pull origin main

# 2. 构建新镜像
docker compose -f docker-compose.prod.yml build

# 3. 运行迁移
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 4. 蓝绿部署 (自动回滚)
bash scripts/deploy-prod.sh deploy

# 5. 验证
bash scripts/verify_deployment.sh
```

### 7.3 故障排查清单

| 症状 | 排查步骤 |
|------|---------|
| App 连不上 | 1. `curl https://api.sparkle.com/health` 2. 检查 Nginx 容器 3. 检查 SSL 证书 |
| AI 不回复 | 1. 检查 agent 日志 2. 检查 LLM API Key 3. 检查 gRPC 连通 |
| WebSocket 断连 | 1. 检查 Nginx proxy_read_timeout 2. 检查 Gateway 日志 3. 检查 Redis |
| 数据库错误 | 1. `docker compose exec db pg_isready` 2. 检查迁移状态 3. 检查连接池 |
| 内存不足 | 1. `docker stats` 2. 调整 resource limits 3. 检查 Redis 内存策略 |

### 7.4 关键监控告警

已配置的 SLO 告警 (无需额外操作):

| 告警 | 条件 | 通知方式 |
|------|------|---------|
| GatewayDown | 2m 不可达 | Alertmanager → Webhook/Email |
| BackendDown | 2m 不可达 | Alertmanager → Webhook/Email |
| High5xxRate | 5xx > 2% 持续 10m | Alertmanager → Warning |
| HighLatency | P95 > 1.5s 持续 10m | Alertmanager → Warning |
| EventStreamLag | 延迟 > 120s | Alertmanager → Warning |

---

## 附录 A: 快速部署 Checklist (一页纸版)

```
□ 服务器就绪 (8C16G, Ubuntu 22.04, Docker 安装)
□ DNS 解析: api.sparkle.com → 服务器 IP
□ 防火墙: 仅 22/80/443 开放
□ SSL 证书获取 (Let's Encrypt)
□ 代码克隆到 /opt/sparkle
□ 安全修复分支已合并到 main (Phase 2.6)
□ Phase 2 代码修复已合并
□ .env 填写完成 (含 Celery broker/result backend)
□ SSL 证书复制到 ssl/ 目录
□ PostgreSQL 调优参数确认 (shared_buffers 等)
□ docker compose build 成功
□ 基础设施启动 (db, redis, minio healthy)
□ 数据库迁移 (alembic upgrade head)
□ AGE 扩展初始化 (init_age_extension.py)
□ 测试用户/种子数据已创建
□ 应用服务启动 (backend, agent, gateway, celery healthy)
□ Nginx 启动，proxy_read_timeout 3600s 确认
□ https://api.sparkle.com/health 返回 200
□ Flutter 构建 (含 --dart-define)
□ Android network_security_config.xml 已创建
□ App 注册登录通过
□ AI 对话有响应
□ 监控可访问 (SSH 隧道)
□ 备份 cron 设置
```

## 附录 B: 服务器资源规划

### 推荐配置 (支持 100 并发用户)

| 服务 | 内存 | CPU | 磁盘 | 备注 |
|------|------|-----|------|------|
| PostgreSQL | 2 GB | 2 核 | 20 GB SSD | shared_buffers=256MB, work_mem=16MB |
| Redis | 2 GB | 1 核 | 5 GB | session + event streams + rate limit 实际远低于 4GB |
| MinIO | 1 GB | 0.5 核 | 按需 | 可替换为云 OSS |
| Backend API | 1 GB | 1 核 | - | |
| gRPC Agent | **3 GB** | 2 核 | - | LangGraph + LLM SDK 高并发可达 3-4GB |
| Go Gateway | 512 MB | 1 核 | - | 蓝绿各一份，共 1 GB |
| Celery Worker | 1 GB | 1 核 | - | |
| Celery Batch Worker | **1 GB** | 1 核 | - | GLM 批处理（docker-compose.yml 中有定义） |
| Nginx | 128 MB | 0.5 核 | - | |
| 监控栈 | 1.5 GB | 1 核 | 10 GB | Prometheus + Grafana + Loki + Tempo |
| **总计** | **~13 GB** | **~10 核** | **~35 GB + 对象存储** | |

> **⚠️ 注意**: gRPC Agent 在高并发场景下可能需要 4GB。
> 如果 LLM API 延迟高导致请求堆积，LangGraph FSM 上下文会持续占用内存。
> 建议初始部署设 3GB，监控一周后根据 `sparkle_agent` 内存指标调整。

### 最低配置 (验证/演示用)

16 GB 服务器可运行全部服务（含 Batch Worker）。若使用外部 LLM API 且 MinIO 换用云 OSS，8 GB 即可（不含 Batch Worker）。

---

## 附录 C: 关键文件索引

| 用途 | 文件路径 |
|------|---------|
| 开发 Docker Compose | `docker-compose.yml` |
| 生产 Docker Compose | `docker-compose.prod.yml` |
| 环境变量模板 | `.env.example` |
| Gateway 环境变量 | `backend/gateway/.env.example` |
| Nginx 主配置 | `nginx/nginx.conf` |
| Nginx 上游配置 | `nginx/upstream.conf` |
| 蓝绿部署脚本 | `scripts/deploy-prod.sh` |
| K8s 部署脚本 | `scripts/deploy_k8s.sh` |
| 备份脚本 | `scripts/backup_prod_data.sh` |
| 恢复脚本 | `scripts/restore_prod_data.sh` |
| AGE 初始化 | `backend/scripts/init_age_extension.py` |
| Flutter URL 配置 | `mobile/lib/core/constants/api_constants.dart` |
| Gateway 默认配置 | `backend/gateway/internal/config/config.go` |
| gRPC 服务入口 | `backend/grpc_server.py` |
| 健康检查 | `backend/gateway/internal/handler/health.go` |

---

**文档版本**: 1.1.0（含批判性审查修正）
**最后更新**: 2026-05-02
**下一步**: 执行 Phase 0 (资源准备) → Phase 1 (服务器初始化) → Phase 2 (代码修复，可并行)

---

## 修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-05-02 | 初始版本 |
| 1.1.0 | 2026-05-02 | 批判性审查修正：① Phase 2.6 安全修复对齐 ② init 脚本关系澄清 ③ Phase 4.5 双轨网络配置 ④ Celery 配置补充 ⑤ 资源估算调优 ⑥ PG 调优说明 ⑦ 初始测试用户 ⑧ WebSocket 超时确认 |
