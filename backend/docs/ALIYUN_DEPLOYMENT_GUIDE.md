# 阿里云服务器部署指南

## 概述

本指南介绍如何在阿里云服务器上部署 Sparkle 后端，使本地前端/移动端能够远程连接。

## 架构说明

```
┌─────────────────────────────────────────────────────────────┐
│                      阿里云服务器                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Nginx     │  │  Gateway    │  │  API/Agent  │         │
│  │   :443      │  │   :8080     │  │   :8000     │         │
│  │   :80       │  │             │  │   :50051    │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                  │
│         └────────────────┴────────────────┘                  │
│                          │                                   │
│                   ┌──────▼──────┐                            │
│                   │ PostgreSQL  │                            │
│                   │    :5432    │                            │
│                   └─────────────┘                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ HTTPS/WSS
                           │
┌──────────────────────────▼─────────────────────────────────┐
│                     本地设备                                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                      │
│  │ Android │  │   iOS   │  │  Web    │                      │
│  └─────────┘  └─────────┘  └─────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

## 第一步：服务器基础配置

### 1.1 购买服务器

推荐配置（与 `scripts/deploy/bootstrap.sh` 的资源门一致：内存 ≥7G、磁盘 ≥20G）：
- **CPU**: 2核及以上
- **内存**: 8GB 及以上（bootstrap 硬门为 7G，低于会拒绝继续部署）
- **系统**: Ubuntu 22.04 或更高
- **带宽**: 5Mbps 及以上

### 1.2 安装必要软件

```bash
# SSH 连接到服务器
ssh root@your-server-ip

# 更新系统
apt update && apt upgrade -y

# 安装 Docker（get.docker.com 同时安装 docker compose v2 插件）
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# 验证 compose v2 插件（仓库部署脚本统一使用 `docker compose`，非旧版独立二进制）
docker compose version
```

## 第二步：配置安全组规则

### 2.1 阿里云控制台配置

登录阿里云控制台 → ECS → 安全组 → 配置规则，添加以下入方向规则：

| 协议类型 | 端口范围 | 授权对象 | 描述 |
|----------|----------|----------|------|
| TCP | 22 | 你的IP/32 | SSH（限制你的IP） |
| TCP | 80 | 0.0.0.0/0 | HTTP（自动跳转HTTPS） |
| TCP | 443 | 0.0.0.0/0 | HTTPS |
| TCP | 8080 | 0.0.0.0/0 | API Gateway（仅开发调试期开放） |

⚠️ **生产环境**: 不要在安全组开放 5432。PostgreSQL 只在 compose 内部网络中监听（`docker-compose.prod.yml` 的 `db` 无公网端口映射），运维访问走服务器本机 `docker exec` 或 SSH 隧道。8080 同理——生产流量统一走 443 由 compose 内置 nginx 反代。

## 第三步：配置域名和 SSL

### 3.1 配置域名

在域名服务商（如阿里云DNS）添加 A 记录：

```
类型: A
主机记录: api
记录值: 你的服务器公网IP
TTL: 600
```

### 3.2 申请 SSL 证书

```bash
# 安装 certbot
apt install certbot python3-certbot-nginx -y

# 申请证书（自动配置 Nginx）
certbot --nginx -d api.yourdomain.com

# 或使用 DNS 验证（推荐用于通配符证书）
certbot certonly --manual --preferred-challenges dns -d "*.yourdomain.com"
```

### 3.3 配置 Nginx

> **推荐路径（现状）**：`docker-compose.prod.yml` 已内置 `nginx` 服务并占用宿主机 80/443
> （挂载 `nginx/nginx.conf` 与 `${SSL_CERT_DIR:-./ssl}` 证书目录），TLS 在容器内终结，
> 网关侧蓝绿切换由 `nginx/upstream.conf` + `scripts/deploy-prod.sh` 管理。
> **不要再在宿主机安装 nginx**（会与 compose 的 80/443 端口冲突）。
> `scripts/deploy/bootstrap.sh` 会装配好这一切。
> 下面手动配置宿主 nginx 的方式仅适用于不使用 prod compose 栈的老旧环境：

```bash
cat > /etc/nginx/sites-available/sparkle << 'NGINX_CONF'
# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS 主配置
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL 证书
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 日志
    access_log /var/log/nginx/sparkle_access.log;
    error_log /var/log/nginx/sparkle_error.log;

    # API Gateway
    location /api/ {
        proxy_pass http://localhost:8080/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://localhost:8080/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
    }
}
NGINX_CONF

# 启用配置
ln -s /etc/nginx/sites-available/sparkle /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

## 第四步：部署代码到服务器

### 4.1 克隆代码

```bash
# 创建项目目录
mkdir -p /opt/sparkle
cd /opt/sparkle

# 克隆代码（把 your-username 换成实际仓库所有者；需克隆到仓库根，
# 因 prod compose 的 db build context 与 nginx/ssl 挂载都以仓库根为基准）
git clone https://github.com/your-username/Sparkle-project.git .
# 或使用 SSH
git clone git@github.com:your-username/Sparkle-project.git .
```

### 4.2 配置环境变量

> **不要手写完整 .env**。仓库自带三份模板（根目录）：
> - `.env.production.example` — 完整基线，`[MUST CHANGE]` 三级标注，
>   自带占位符校验门（`python scripts/check_production_secrets.py`，占位密钥未替换时启动即失败）；
> - `.env.cloud.example` — 云端安全默认值 overlay（`scripts/deploy/bootstrap.sh` 自动装配）；
> - `backend/.env.example` — 后端应用变量全集（本地开发口径）。
>
> 一键部署入口（推荐）：`sudo bash scripts/deploy/bootstrap.sh`（`make cloud-up`），
> 或干跑预览 `make cloud-plan`。它负责 .env 装配、安全检查与全栈拉起。

```bash
# 手动路径：基于完整基线创建根目录 .env 并填值
cd /opt/sparkle
cp .env.production.example .env
# 逐条替换 [MUST CHANGE] 占位值后自检：
python scripts/check_production_secrets.py
```

与旧版指南的差异要点（以模板为准，此处仅列易错项）：

- **数据库**：compose 侧用 `DB_NAME/DB_USER/DB_PASSWORD`，应用侧 `DATABASE_URL`
  指向 `sparkle_db:5432`（asyncpg scheme，见模板 67-73 行示例）。
- **AI 模型**（2026-09 现状，对照 `backend/.env.example`）：
  - 主力 LLM 已切 **Qwen/DashScope**：`LLM_PROVIDER=qwen`、
    `LLM_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`、`LLM_API_KEY=...`；
  - 批量任务档已切 **MiniMax**：`MINIMAX_API_KEY=...`（GLM batch 条目默认不启用、保留待用；
    MiniMax 失败由批任务重试接管，不静默回切）；
  - Zhipu GLM 仍服务 OCR/免费层等条目（`ZHIPU_API_KEY` 按需保留）。
  - 旧指南中的 `OPENAI_API_KEY/OPENAI_BASE_URL` 已非主力配置，OpenAI 兼容协议通过
    `LLM_API_BASE_URL` 指向 DashScope 等兼容端点。
- **镜像来源**：`IMAGE_TAG` + `GATEWAY_IMAGE`/`BACKEND_IMAGE` 指向 GHCR
  （CI 在 main push/tag 时自动发布 `ghcr.io/<owner>/sparkle-gateway|sparkle-backend`）。

### 4.3 数据库与编排：使用 docker-compose.prod.yml（勿手改）

> **现状（2026-09）**：生产编排以 `docker-compose.prod.yml` 为准，**不要再手写或手改
> compose 文件**（旧指南示例里的 `pgvector/pgvector:pg16` 裸镜像与
> `postgres/sparkle_gateway/sparkle_api/sparkle_agent` 服务名均已过时）。

关键点：

- **数据库同源构建**：`db` 服务从 `docker/pgvector-age.Dockerfile` 构建
  （pgvector + Apache AGE，产物 tag `sparkle/pgvector-age:pg16`），与 dev 侧
  `sparkle_db` 同一构建源，由守卫
  `scripts/guards/check_rule_bn_prod_db_age_parity.py`（Rule BN）锁定，防止回退裸 pgvector。
  星图（galaxy/Age 图谱）功能依赖 AGE 扩展——裸 pgvector 镜像会导致生产星图断链。
- **one-shot 初始化链**：`db_migrate`（Alembic 迁移）→ `db_age_init`
  （运行 `backend/scripts/init_age_extension.py`：建 vector/age 扩展 + sparkle_galaxy
  图谱与基础 label，失败即阻断启动），backend/agent/celery 全部等两者成功后才启动。
- **镜像**：应用镜像来自 GHCR（`BACKEND_IMAGE`/`GATEWAY_IMAGE` + `IMAGE_TAG`），
  CI 在 main push/tag 时发布。
- **安全绑定**：公网入口只有 compose 内置 nginx 的 80/443；数据库无公网映射。

```bash
cd /opt/sparkle
# 一键路径（推荐）：装配 .env + 全栈拉起 + smoke 探针
sudo bash scripts/deploy/bootstrap.sh          # 干跑预览: --plan

# 手动路径：拉镜像并启动全栈（迁移与 AGE 初始化由 one-shot 服务自动执行）
docker compose -f docker-compose.prod.yml --env-file .env pull
docker compose -f docker-compose.prod.yml --env-file .env up -d
```

## 第五步：数据库迁移与 AGE 初始化

> **现状**：迁移与 AGE 初始化不再是手动步骤。`docker compose up` 时由 one-shot 服务
> 自动执行：`db_migrate`（Alembic）→ `db_age_init`（vector/age 扩展 + sparkle_galaxy
> 图谱初始化），backend/agent/celery 等服务会等两者成功后才启动。

```bash
cd /opt/sparkle

# 观察迁移与 AGE 初始化（一次性服务，完成后退出）
docker compose -f docker-compose.prod.yml --env-file .env logs db_migrate
docker compose -f docker-compose.prod.yml --env-file .env logs db_age_init

# 验证迁移版本（以 `alembic heads` 为准，版本号随迁移链前进，文档不钉死）
docker compose -f docker-compose.prod.yml --env-file .env exec backend \
  alembic current

# 验证 AGE 就绪（应返回 vector 与 age 两行）
docker compose -f docker-compose.prod.yml --env-file .env exec db \
  psql -U "$DB_USER" -d "$DB_NAME" \
  -c "SELECT extname FROM pg_extension WHERE extname IN ('vector','age') ORDER BY extname;"
```

参展演示数据（可选）：`bash scripts/deploy/bootstrap.sh --with-demo-seed`
（演示账号密码自动生成并写入 .env）。旧指南的手写管理员脚本引用的
`SessionLocal` 已不存在于 `app/db/session.py`（现为 `AsyncSessionLocal`），已移除。

## 第六步：配置防火墙

```bash
# 安装 UFW（Ubuntu）
apt install ufw -y

# 默认策略
ufw default deny incoming
ufw default allow outgoing

# 允许 SSH（已建立的连接）
ufw allow 22/tcp

# 允许 HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# 启用防火墙
ufw enable

# 查看状态
ufw status
```

## 第七步：本地前端配置

### 7.1 移动端配置

> 移动端不读 AndroidManifest meta-data 或 Xcode User-Defined 变量（旧指南写法有误）。
> 唯一注入机制是 `--dart-define`，由 `mobile/lib/core/constants/api_constants.dart` 消费：

```bash
# 运行 / 构建时指定
flutter run --dart-define=API_BASE_URL=https://api.yourdomain.com
flutter build apk --dart-define=API_BASE_URL=https://api.yourdomain.com
```

**Dart 代码** (`mobile/lib/core/constants/api_constants.dart`，节选)：

```dart
class ApiConstants {
  // 通过 --dart-define 注入，例:
  //   flutter run --dart-define=API_BASE_URL=https://api.yourdomain.com
  static const String _baseUrlOverride = String.fromEnvironment('API_BASE_URL');

  static String get baseUrl {
    if (_baseUrlOverride.isNotEmpty) {
      return _baseUrlOverride;
    }
    // 未注入时走内置的 Web/Release/Debug 回退逻辑，详见源文件
    ...
  }
}
```

### 7.2 Web 前端配置

本项目没有独立的 JS Web 应用；Web 端即 Flutter Web（同 `api_constants.dart` 消费链）：

```bash
flutter run -d chrome --dart-define=API_BASE_URL=https://api.yourdomain.com
flutter build web --dart-define=API_BASE_URL=https://api.yourdomain.com
```

## 第八步：验证部署

```bash
# 1. 检查服务状态（服务名以 docker-compose.prod.yml 为准：nginx/gateway_blue/gateway_green/backend/agent/db/redis/minio）
docker compose -f docker-compose.prod.yml ps

# 2. 检查 compose nginx
docker compose -f docker-compose.prod.yml ps nginx

# 3. 测试 HTTPS 访问
curl -I https://api.yourdomain.com/health

# 4. 测试 API
curl -X POST https://api.yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your_username","password":"your_password"}'

# 5. 查看日志
docker compose -f docker-compose.prod.yml logs -f gateway_blue
docker compose -f docker-compose.prod.yml logs -f backend
tail -f /var/log/nginx/sparkle_error.log
```

## 第九步：设置自动部署（可选）

> **现状**：仓库已有完整的发布链路，无需自建 deploy.yml：
> - **镜像发布**：`.github/workflows/ci.yml` 的 build job 在 main push/tag 时
>   构建并推送 `ghcr.io/<owner>/sparkle-gateway` 与 `ghcr.io/<owner>/sparkle-backend`；
> - **发版**：`scripts/deploy-prod.sh`（蓝绿切换：拉新镜像 → 起 green/blue →
>   换 `nginx/upstream.conf` → 排水旧色，迁移与 AGE 初始化由 one-shot 服务随栈执行）；
> - **首部署**：`scripts/deploy/bootstrap.sh` 一条命令（含 .env 安全门与 smoke 探针）。

服务器侧的最小发版循环示例（在服务器上以 cron/手工触发均可）：

```bash
cd /opt/sparkle
git pull origin main
# .env 中设 IMAGE_TAG=<目标tag>（默认 latest）
GATEWAY_IMAGE=ghcr.io/<owner>/sparkle-gateway \
BACKEND_IMAGE=ghcr.io/<owner>/sparkle-backend \
IMAGE_TAG=latest \
bash scripts/deploy-prod.sh
```

## 监控和维护

### 日志查看

```bash
# 服务日志
docker compose -f docker-compose.prod.yml logs -f --tail=100

# Nginx 访问日志（compose nginx 容器内）
docker compose -f docker-compose.prod.yml logs -f nginx

# 系统日志
journalctl -u docker -f
```

### 数据库备份

```bash
# 创建备份脚本（服务名 db；账号库名用 .env 的 DB_USER/DB_NAME）
cat > /opt/backup-sparkle.sh << 'BACKUP_SCRIPT'
#!/bin/bash
set -euo pipefail
cd /opt/sparkle
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/backups
mkdir -p $BACKUP_DIR

docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U "${DB_USER:-sparkle_app}" "${DB_NAME:-sparkle}" | gzip > $BACKUP_DIR/sparkle_$DATE.sql.gz

# 保留最近 7 天的备份
find $BACKUP_DIR -name "sparkle_*.sql.gz" -mtime +7 -delete
BACKUP_SCRIPT

chmod +x /opt/backup-sparkle.sh

# 添加到 crontab（每天凌晨 2 点备份）
crontab -e
# 添加: 0 2 * * * /opt/backup-sparkle.sh
```

### 性能监控

```bash
# 安装监控工具
apt install htop iotop nethogs -y

# 查看 Docker 资源使用
docker stats

# 查看磁盘使用
df -h
```

## 故障排除

### 问题 1: 502 Bad Gateway

```bash
# 检查网关是否运行（蓝绿两色，当前生效色看 nginx/upstream.conf）
docker compose -f docker-compose.prod.yml ps gateway_blue gateway_green

# 检查网关日志
docker compose -f docker-compose.prod.yml logs gateway_blue gateway_green

# 检查 compose nginx 配置
docker compose -f docker-compose.prod.yml exec nginx nginx -t
```

### 问题 2: SSL 证书错误

```bash
# 续期证书
certbot renew

# 测试续期
certbot renew --dry-run
```

### 问题 3: 数据库连接失败

```bash
# 检查数据库是否运行（服务名 db；AGE 镜像 sparkle/pgvector-age:pg16）
docker compose -f docker-compose.prod.yml ps db

# 检查数据库日志
docker compose -f docker-compose.prod.yml logs db

# 测试连接
docker compose -f docker-compose.prod.yml exec db \
  psql -U "${DB_USER:-sparkle_app}" -d "${DB_NAME:-sparkle}" -c "SELECT 1;"
```

## 安全建议

1. **定期更新系统**
   ```bash
   apt update && apt upgrade -y
   ```

2. **限制数据库访问**
   - 不要将 5432 端口暴露到公网
   - 使用强密码
   - 定期备份数据

3. **启用 Fail2ban**
   ```bash
   apt install fail2ban -y
   systemctl enable fail2ban
   ```

4. **配置自动备份**
   - 每日备份数据库
   - 备份到远程存储

5. **监控异常**
   - 设置日志监控告警
   - 监控 CPU/内存/磁盘使用

## 相关文档

- [Event Outbox 迁移](EVENT_OUTBOX_MIGRATION.md)
- [iOS 本地网络权限](IOS_LOCAL_NETWORK_PERMISSIONS.md)
- [真机联调完整流程](REAL_DEVICE_INTEGRATION_TEST.md)
