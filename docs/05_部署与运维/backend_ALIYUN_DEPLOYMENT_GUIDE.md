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

推荐配置：
- **CPU**: 2核及以上
- **内存**: 4GB 及以上
- **系统**: Ubuntu 22.04 或 CentOS 8+
- **带宽**: 5Mbps 及以上

### 1.2 安装必要软件

```bash
# SSH 连接到服务器
ssh root@your-server-ip

# 更新系统
apt update && apt upgrade -y  # Ubuntu/Debian
# 或
yum update -y  # CentOS

# 安装 Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# 安装 Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
docker-compose --version

# 安装 Nginx（用于 HTTPS 反向代理）
apt install nginx -y  # Ubuntu/Debian
# 或
yum install nginx -y  # CentOS
```

## 第二步：配置安全组规则

### 2.1 阿里云控制台配置

登录阿里云控制台 → ECS → 安全组 → 配置规则，添加以下入方向规则：

| 协议类型 | 端口范围 | 授权对象 | 描述 |
|----------|----------|----------|------|
| TCP | 22 | 你的IP/32 | SSH（限制你的IP） |
| TCP | 80 | 0.0.0.0/0 | HTTP（自动跳转HTTPS） |
| TCP | 443 | 0.0.0.0/0 | HTTPS |
| TCP | 8080 | 0.0.0.0/0 | API Gateway（开发环境） |
| TCP | 5432 | 0.0.0.0/0 | PostgreSQL（生产环境建议限制） |

⚠️ **生产环境**: 5432 端口应仅允许内网访问或特定IP

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

# 克隆代码（使用你的 Git 仓库）
git clone https://github.com/your-username/sparkle-flutter.git .
# 或使用 SSH
git clone git@github.com:your-username/sparkle-flutter.git .
```

### 4.2 配置环境变量

```bash
cd backend

# 创建生产环境配置
cat > .env.production << 'ENV_CONF'
# === 数据库配置 ===
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=sparkle
POSTGRES_PASSWORD=your_strong_password_here
POSTGRES_DB=sparkle

# === Redis 配置 ===
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# === MinIO 配置 ===
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_USE_SSL=false

# === JWT 配置 ===
JWT_SECRET_KEY=your_jwt_secret_key_change_this
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# === API 配置 ===
GATEWAY_PORT=8080
API_PORT=8000
GRPC_PORT=50051

# === 外部 API ===
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1

# === 环境标识 ===
ENVIRONMENT=production
DEBUG=false

# === CORS 配置（允许你的域名） ===
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
ENV_CONF

# 使用生产配置启动
export $(cat .env.production | xargs)
```

### 4.3 修改 docker-compose.yml

确保服务只绑定 localhost 或使用内部网络：

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: sparkle_db
    environment:
      POSTGRES_USER: sparkle
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: sparkle
    volumes:
      - postgres_data:/var/lib/postgresql/data
    # 生产环境：不暴露 5432 到公网
    ports:
      - "127.0.0.1:5432:5432"
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sparkle"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis/redis-stack-server:latest
    container_name: sparkle_redis
    restart: always
    # 不暴露到公网
    ports:
      - "127.0.0.1:6379:6379"

  sparkle_gateway:
    build: ./gateway
    container_name: sparkle_gateway
    ports:
      - "127.0.0.1:8080:8080"  # 通过 Nginx 代理
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - postgres
      - redis
    restart: always

  sparkle_api:
    build: .
    container_name: sparkle_api
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - postgres
      - redis
    restart: always

  sparkle_agent:
    build: .
    container_name: sparkle_agent
    command: python -m grpc_server
    ports:
      - "127.0.0.1:50051:50051"
    environment:
      - POSTGRES_HOST=postgres
    depends_on:
      - postgres
    restart: always

volumes:
  postgres_data:
```

## 第五步：数据库迁移

```bash
cd /opt/sparkle/backend

# 启动服务（首次）
docker-compose up -d

# 等待数据库就绪
sleep 10

# 执行数据库迁移
docker-compose exec sparkle_api alembic upgrade head

# 验证迁移版本
docker-compose exec sparkle_api alembic current
# 应输出: 5f2b9b3c0e6f (head)

# 创建管理员用户（可选）
docker-compose exec sparkle_api python -c "
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.user import User

db = SessionLocal()
admin = User(
    username='admin',
    email='admin@yourdomain.com',
    hashed_password=get_password_hash('your_admin_password'),
    is_active=True,
    is_superuser=True
)
db.add(admin)
db.commit()
print('Admin user created')
"
```

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

**Android** (`mobile/android/app/src/main/AndroidManifest.xml`):

```xml
<meta-data
    android:name="API_BASE_URL"
    android:value="https://api.yourdomain.com" />
```

**iOS** - 在 Xcode 中:
1. `Build Settings` → `User-Defined`
2. 添加 `API_BASE_URL` = `https://api.yourdomain.com`

或运行时指定:
```bash
flutter run --dart-define=API_BASE_URL=https://api.yourdomain.com
```

**Dart 代码** (`mobile/lib/core/config/api_config.dart`):

```dart
class ApiConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://api.yourdomain.com', // 生产环境
  );
  
  // 开发环境切换
  static const bool isProduction = bool.fromEnvironment('dart.vm.product');
  
  static String get apiUrl => isProduction 
      ? baseUrl 
      : 'http://192.168.31.51:8080'; // 本地开发
}
```

### 7.2 Web 前端配置

```javascript
// config.js
const API_BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://api.yourdomain.com'
  : 'http://localhost:8080';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});
```

## 第八步：验证部署

```bash
# 1. 检查服务状态
docker-compose ps

# 2. 检查 Nginx
systemctl status nginx

# 3. 测试 HTTPS 访问
curl -I https://api.yourdomain.com/health

# 4. 测试 API
curl -X POST https://api.yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your_username","password":"your_password"}'

# 5. 查看日志
docker-compose logs -f sparkle_gateway
docker-compose logs -f sparkle_api
tail -f /var/log/nginx/sparkle_error.log
```

## 第九步：设置自动部署（可选）

### 9.1 使用 GitHub Actions

创建 `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/sparkle
            git pull origin main
            docker-compose pull
            docker-compose up -d --build
            docker-compose exec sparkle_api alembic upgrade head
```

## 监控和维护

### 日志查看

```bash
# 服务日志
docker-compose logs -f --tail=100

# Nginx 访问日志
tail -f /var/log/nginx/sparkle_access.log

# 系统日志
journalctl -u docker -f
```

### 数据库备份

```bash
# 创建备份脚本
cat > /opt/backup-sparkle.sh << 'BACKUP_SCRIPT'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/backups
mkdir -p $BACKUP_DIR

docker-compose exec -T postgres pg_dump -U sparkle sparkle | gzip > $BACKUP_DIR/sparkle_$DATE.sql.gz

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
# 检查 Gateway 是否运行
docker-compose ps sparkle_gateway

# 检查 Gateway 日志
docker-compose logs sparkle_gateway

# 检查 Nginx 配置
nginx -t
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
# 检查数据库是否运行
docker-compose ps postgres

# 检查数据库日志
docker-compose logs postgres

# 测试连接
docker-compose exec postgres psql -U sparkle -d sparkle -c "SELECT 1;"
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
