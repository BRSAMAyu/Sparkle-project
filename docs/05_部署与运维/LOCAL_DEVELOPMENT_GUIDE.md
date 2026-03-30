# Sparkle 本地开发环境启动指南

> **文档版本**: 1.0.0
> **最后更新**: 2026-03-30
> **适用系统**: macOS (Apple Silicon)

---

## 目录

1. [系统架构概览](#1-系统架构概览)
2. [前置依赖](#2-前置依赖)
3. [服务启动顺序](#3-服务启动顺序)
4. [详细启动步骤](#4-详细启动步骤)
5. [验证检查清单](#5-验证检查清单)
6. [常见问题与解决方案](#6-常见问题与解决方案)
7. [已修复的关键问题](#7-已修复的关键问题)
8. [端口映射表](#8-端口映射表)

---

## 1. 系统架构概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        iOS Simulator                                 │
│                     Flutter Mobile App                               │
│                    (localhost dynamic)                               │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP/WebSocket
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Go Gateway (8080)                               │
│              - JWT 认证                                               │
│              - WebSocket 连接管理                                     │
│              - REST API 反向代理                                      │
│              - 缓存层                                                 │
└──────────────┬─────────────────────────────────┬────────────────────┘
               │ REST API                        │ gRPC
               ▼                                 ▼
┌──────────────────────────┐    ┌──────────────────────────────────────┐
│  Python FastAPI (8000)   │    │    Python gRPC Server (50051)        │
│  - /api/v1/auth/*        │    │    - StreamChat 流式对话              │
│  - /api/v1/users/*       │    │    - AI Agent 编排                    │
│  - /api/v1/tasks/*       │    │    - LangGraph FSM 状态机             │
│  - 业务逻辑 REST API      │    │    - RAG 检索增强                    │
└──────────┬───────────────┘    └───────────────┬──────────────────────┘
           │                                    │
           └──────────────┬─────────────────────┘
                          │
           ┌──────────────┼──────────────┐
           ▼              ▼              ▼
    ┌────────────┐  ┌──────────┐  ┌─────────────┐
    │ PostgreSQL │  │  Redis   │  │   MinIO     │
    │  +pgvector │  │  Stack   │  │  (S3兼容)   │
    │   (5432)   │  │  (6379)  │  │   (9000)    │
    └────────────┘  └──────────┘  └─────────────┘
```

---

## 2. 前置依赖

### 2.1 必需软件

| 软件 | 版本要求 | 安装命令 | 验证命令 |
|------|---------|---------|---------|
| **Docker Desktop** | 4.x+ | 官网下载 | `docker --version` |
| **Go** | 1.21+ | `brew install go` | `go version` |
| **Python** | 3.11+ | `brew install python@3.11` | `python3 --version` |
| **Poetry** | 1.7+ | `pip install poetry` | `poetry --version` |
| **Flutter** | 3.16+ | 官网下载 | `flutter --version` |
| **Xcode** | 15+ | App Store | `xcodebuild -version` |
| **Buf** | 1.x | `brew install bufbuild/buf/buf` | `buf --version` |

### 2.2 项目依赖安装

```bash
# 1. Python 依赖
cd /Users/brsama/code/GitHub/Sparkle-project/backend
poetry install

# 2. Go 依赖
cd /Users/brsama/code/GitHub/Sparkle-project/backend/gateway
go mod download

# 3. Flutter 依赖
cd /Users/brsama/code/GitHub/Sparkle-project/mobile
flutter pub get
```

---

## 3. 服务启动顺序

**关键原则**: 按依赖关系从底层到上层启动

### 2026-03-30 补充说明

默认本地数据库基线统一为 `127.0.0.1:5432`。  
如果你因为本机冲突改了数据库端口，必须同时同步仓库根 `.env`、`backend/.env`、`backend/gateway/.env`；不要只改其中一处。  
当前应以**有效配置 + 真实监听端口**为准，并在进入模拟器前执行：

```bash
make env-check
make local-signoff-preflight
```

如果 `local-signoff-preflight` 失败，先修配置或底层依赖，不要继续点应用。

```
启动顺序:
1. Docker Desktop (基础设施)
2. Docker Compose 服务 (PostgreSQL, Redis, MinIO)
3. Celery Worker + Beat (异步任务)
4. Python gRPC Server (AI 引擎)
5. Python FastAPI (REST API)
6. Go Gateway (反向代理)
7. iOS Simulator + Flutter App (客户端)
```

---

## 4. 详细启动步骤

### 4.1 启动 Docker Desktop

```bash
# 打开 Docker Desktop (macOS)
open -a Docker

# 等待 Docker 就绪 (最多等待 60 秒)
until docker info > /dev/null 2>&1; do
  echo "Waiting for Docker..."
  sleep 3
done
echo "Docker is ready!"
```

### 4.2 启动基础设施 (Docker Compose)

```bash
cd /Users/brsama/code/GitHub/Sparkle-project

# 启动所有基础设施服务
docker compose up -d postgres redis minio

# 验证服务状态
docker compose ps

# 期望输出:
# NAME                    STATUS    PORTS
# sparkle-postgres-1      running   0.0.0.0:5432->5432/tcp
# sparkle-redis-1         running   0.0.0.0:6379->6379/tcp
# sparkle-minio-1         running   0.0.0.0:9000-9001->9000-9001/tcp
```

### 4.3 数据库迁移

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/backend

# 应用数据库迁移
alembic upgrade head

# 验证迁移状态
alembic current
```

### 4.4 启动 Celery (异步任务队列)

```bash
cd /Users/brsama/code/GitHub/Sparkle-project

# 使用 Makefile 启动
make celery-up

# 或手动启动
celery -A app.celery_app worker --loglevel=info &
celery -A app.celery_app beat --loglevel=info &

# 验证 Celery 状态
make celery-status
```

### 4.5 启动 Python gRPC Server

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/backend

# 激活虚拟环境
source $(poetry env info -p)/bin/activate

# 启动 gRPC 服务
python -m app.grpc_server

# 或使用 Makefile
make grpc-server

# 验证 gRPC 服务
grpcurl -plaintext localhost:50051 list
```

### 4.6 启动 Python FastAPI

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/backend

# 激活虚拟环境
source $(poetry env info -p)/bin/activate

# 启动 FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 验证 FastAPI
curl http://localhost:8000/health
# 期望: {"status": "healthy", ...}
```

### 4.7 启动 Go Gateway

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/backend/gateway

# 启动 Go Gateway (带热重载)
make gateway-dev

# 或直接运行
go run cmd/server/main.go

# 验证 Gateway
curl http://localhost:8080/health
# 期望: {"status": "running", ...}
```

### 4.8 启动 iOS Simulator + Flutter App

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/mobile

# 打开 iOS Simulator
open -a Simulator

# 等待模拟器启动
sleep 5

# 选择目标设备 (可选)
xcrun simctl boot "iPhone 17 Pro" 2>/dev/null || true

# 运行 Flutter 应用
flutter run -d ios

# 或指定设备
flutter run -d "iPhone 17 Pro"
```

---

## 5. 验证检查清单

### 5.1 服务健康检查

```bash
# 一键检查所有服务
make smoke

# 最终签收前统一自检
make local-signoff-preflight

# 最终本地签收 smoke 组合
make local-final-signoff

# 或手动逐项检查:

# Docker
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# PostgreSQL
pg_isready -h localhost -p 5432

# Redis
redis-cli ping
# 期望: PONG

# MinIO
curl http://localhost:9000/minio/health/live

# Python FastAPI
curl http://localhost:8000/health

# Python gRPC
grpcurl -plaintext localhost:50051 list

# Go Gateway
curl http://localhost:8080/health
```

### 5.2 端到端功能测试

```bash
# 1. 测试游客登录
curl -X POST "http://localhost:8080/api/v1/auth/guest" \
  -H "Content-Type: application/json" \
  -d '{"guest_id": "test-guest-123"}'

# 期望: {"access_token": "...", "token_type": "bearer", ...}

# 2. 测试 WebSocket 连接
wscat -c "ws://localhost:8080/ws/chat" \
  -H "Authorization: Bearer <token>"

# 3. 在模拟器中测试 UI
# - 打开应用
# - 点击"游客登录"
# - 验证进入主页
```

---

## 6. 常见问题与解决方案

### 6.1 Docker 相关

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `Cannot connect to Docker daemon` | Docker Desktop 未启动 | `open -a Docker` 并等待启动 |
| 端口被占用 | 之前的服务未正确关闭 | `docker compose down` 然后 `docker compose up -d` |
| 容器无法启动 | 磁盘空间不足 | 清理 Docker: `docker system prune -a` |

### 6.2 Python 相关

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `ModuleNotFoundError` | 虚拟环境未激活 | `source $(poetry env info -p)/bin/activate` |
| `Redis connection refused` | Redis 未启动 | `docker compose up -d redis` |
| `Alembic version mismatch` | 迁移未应用 | `alembic upgrade head` |

### 6.3 Go 相关

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `proto: not found` | Proto 未生成 | `make proto-gen` |
| `sqlc: not found` | SQLC 未安装 | `go install github.com/sqlc-dev/sqlc/cmd/sqlc@latest` |
| 编译错误 | 依赖缺失 | `go mod tidy && go mod download` |

### 6.4 Flutter/iOS 相关

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `FirebaseApp.configure() crash` | 无 GoogleService-Info.plist | 已修复: 改为可选初始化 |
| `CocoaPods error` | Pod 未安装 | `cd ios && pod install` |
| 模拟器黑屏 | 模拟器卡死 | 重启模拟器: `xcrun simctl shutdown all` |

---

## 7. 已修复的关键问题

### 7.1 Firebase 初始化崩溃 (iOS)

**问题**: iOS 应用在无 `GoogleService-Info.plist` 时崩溃

**修复文件**: `mobile/ios/Runner/AppDelegate.swift`

**修复内容**:
```swift
// 修复前 (崩溃)
FirebaseApp.configure()

// 修复后 (可选初始化)
if let googleServicePath = Bundle.main.path(forResource: "GoogleService-Info", ofType: "plist") {
    if FirebaseApp.app() == nil {
        FirebaseApp.configure()
    }
    Messaging.messaging().delegate = self
}
```

### 7.2 Go 编译错误 - Timestamp 类型不匹配

**问题**: `pgtype.Timestamp` 与 `pgtype.Timestamptz` 类型不匹配

**修复文件**: `backend/gateway/internal/cqrs/outbox/repository.go`

**修复内容**:
```go
// outbox 表使用 Timestamptz (schema.sql 定义)
func (r *Repository) InsertWithTx(ctx context.Context, tx pgx.Tx, msg *OutboxMessage) error {
    // ...
    created: pgtype.Timestamptz{Time: msg.Created, Valid: true},  // 使用 Timestamptz
}

// event_store 表使用 Timestamp
func (r *Repository) SaveWithTx(ctx context.Context, tx pgx.Tx, event *Event) error {
    // ...
    CreatedAt: pgtype.Timestamp{Time: event.CreatedAt, Valid: true},  // 使用 Timestamp
}
```

### 7.3 Python 语法错误 - 多余括号

**问题**: `focus_service.py` 中有多余的闭括号

**修复文件**: `backend/app/services/focus_service.py:263`

**修复内容**:
```python
# 修复前
return result if isinstance(result, list) else []))

# 修复后
return result if isinstance(result, list) else []
```

### 7.4 Python event_bus 作用域错误

**问题**: `event_bus` 在条件块内导入，但在外部使用

**修复文件**: `backend/app/main.py`

**修复内容**:
```python
# 修复前 - event_bus 导入在 if 块内
if cache_service.redis:
    from app.core.event_bus import event_bus
    # ...
# nudge_consumer 在 if 块外使用 event_bus -> UnboundLocalError

# 修复后 - 将 nudge_consumer 移入 if 块内
if cache_service.redis:
    from app.core.event_bus import event_bus
    # ... capsule_consumer ...
    nudge_consumer = NudgeEventConsumer(event_bus=event_bus)
    nudge_consumer_task = asyncio.create_task(nudge_consumer.start())
    app.state.nudge_consumer_task = nudge_consumer_task
```

### 7.5 Go 未使用导入

**问题**: `file_handler.go` 有未使用的 `fmt` 导入

**修复文件**: `backend/gateway/internal/handler/file_handler.go`

**修复内容**: 删除未使用的 `import "fmt"`

---

## 8. 端口映射表

| 服务 | 端口 | 协议 | 用途 |
|------|------|------|------|
| PostgreSQL | 5432 | TCP | 主数据库 + pgvector |
| Redis | 6379 | TCP | 缓存 + Session + Pub/Sub |
| Redis Insight | 8001 | HTTP | Redis 管理界面 (可选) |
| MinIO API | 9000 | HTTP | S3 兼容对象存储 |
| MinIO Console | 9001 | HTTP | MinIO 管理界面 |
| Python FastAPI | 8000 | HTTP | REST API 服务 |
| Python gRPC | 50051 | gRPC | AI Agent 服务 |
| Go Gateway | 8080 | HTTP/WS | 反向代理 + WebSocket |
| Prometheus | 9090 | HTTP | 指标收集 (可选) |
| Grafana | 3000 | HTTP | 监控面板 (可选) |
| Flower | 5555 | HTTP | Celery 监控 (可选) |

---

## 9. 快速启动脚本

### 9.1 一键启动所有服务

```bash
#!/bin/bash
# 文件: scripts/start_all.sh

set -e

echo "🚀 启动 Sparkle 本地环境..."

# 1. 确保 Docker 运行
echo "📦 检查 Docker..."
until docker info > /dev/null 2>&1; do
  echo "   等待 Docker 启动..."
  sleep 3
done

# 2. 启动基础设施
echo "🗄️  启动基础设施..."
docker compose up -d postgres redis minio

# 3. 等待数据库就绪
echo "⏳ 等待数据库..."
sleep 5

# 4. 数据库迁移
echo "📊 应用数据库迁移..."
cd backend && alembic upgrade head && cd ..

# 5. 启动 Celery
echo "🔄 启动 Celery..."
make celery-up

# 6. 启动后端服务 (后台)
echo "🐍 启动 Python 服务..."
cd backend
source $(poetry env info -p)/bin/activate
python -m app.grpc_server &
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
cd ..

# 7. 启动 Go Gateway
echo "🔷 启动 Go Gateway..."
cd backend/gateway
make gateway-dev &
cd ../..

# 8. 启动 iOS 模拟器
echo "📱 启动 iOS 模拟器..."
open -a Simulator
sleep 5

# 9. 启动 Flutter 应用
echo "📱 启动 Flutter 应用..."
cd mobile
flutter run -d ios &

echo "✅ 所有服务启动完成!"
echo ""
echo "访问地址:"
echo "  - Go Gateway:    http://localhost:8080"
echo "  - FastAPI Docs:  http://localhost:8000/docs"
echo "  - MinIO Console: http://localhost:9001"
```

### 9.2 一键停止所有服务

```bash
#!/bin/bash
# 文件: scripts/stop_all.sh

echo "🛑 停止 Sparkle 本地环境..."

# 停止 Python 进程
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "python -m app.grpc_server" 2>/dev/null || true

# 停止 Celery
make celery-stop 2>/dev/null || true

# 停止 Go Gateway
pkill -f "go run cmd/server" 2>/dev/null || true

# 停止 Flutter
pkill -f "flutter run" 2>/dev/null || true

# 停止 Docker 服务 (可选)
# docker compose down

echo "✅ 所有服务已停止"
```

---

## 10. 环境变量配置

### 10.1 必需的环境变量

创建 `backend/.env` 文件:

```env
# 数据库
DATABASE_URL=postgresql+asyncpg://sparkle:sparkle@localhost:5432/sparkle
DATABASE_SYNC_URL=postgresql://sparkle:sparkle@localhost:5432/sparkle

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=sparkle

# JWT
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# LLM (可选 - 用于 AI 功能)
OPENAI_API_KEY=your-openai-api-key
# 或
ANTHROPIC_API_KEY=your-anthropic-api-key

# 功能开关
DEBUG=true
ENABLE_AGENT_GRAPH_V2=true
ENABLE_SUMMARIZATION_WORKER=true
```

---

## 11. 日志查看

```bash
# 查看所有 Docker 日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f postgres
docker compose logs -f redis

# 查看 Python 日志 (如果使用 uvicorn)
# 日志输出到 stdout

# 查看 Go Gateway 日志
# 日志输出到 stdout

# 查看 Celery 日志
make celery-logs-worker
```

---

**文档结束**

如有问题，请参考:
- 开发文档入口: `docs/README.md`
- 架构概览: `docs/00_项目概览/02_技术架构.md`
- API 参考: `docs/02_技术设计文档/03_API参考.md`
