# Docker 配置详解

> **版本**: v1.0
> **日期**: 2026-01-10
> **文件**: `docker-compose.yml`

## 1. 概述

Sparkle 使用 Docker Compose 编排所有服务。本配置涵盖了基础设施（DB, Redis, MinIO）和应用服务（Gateway, Engine, Worker）。

## 2. 服务清单

### 2.1 基础设施 (Infrastructure)

| 服务名 | 容器名（FIX-563 分化后） | 镜像 | 端口 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `sparkle_db` | `sparkle_proj_db` | `pgvector/pgvector:pg16` | 5432 | 核心数据库，支持向量扩展 |
| `redis` | `sparkle_proj_redis` | `redis/redis-stack-server` | 6379 | 缓存、队列、会话存储 |
| `minio` | `sparkle_proj_minio` | `minio/minio` | 9000/9001 | 对象存储 (S3 兼容) |

> FIX-563：本仓 `container_name` 单侧分化加 `_proj_` 中缀（与 sparkle-cosmos 仓的 `sparkle_*` 容器名区分，根除跨仓同名误击）；**compose 服务名/容器内 DNS 不变**，服务间访问仍用服务名。对照表与 `-p` 纪律见 `scripts/RESTACK_RUNBOOK.md`。

### 2.2 应用服务 (Applications)

| 服务名 | 构建路径 | 端口 | 说明 |
| :--- | :--- | :--- | :--- |
| `sparkle_gateway` | `./backend/gateway` | 8080 | Go 网关，处理 WebSocket 和 HTTP |
| `sparkle_backend` | `./backend` | 8000/50051 | Python AI 引擎 (REST + gRPC) |
| `celery_worker` | `./backend` | - | 异步任务消费者 |
| `celery_beat` | `./backend` | - | 定时任务调度器 |

## 3. 网络配置 (Networking)

所有服务运行在默认的 `default` 网络中，通过服务名相互访问。

- **Gateway -> Engine**: `grpc://sparkle_backend:50051`
- **Engine -> DB**: `postgresql://.../sparkle_db:5432`
- **Engine -> Redis**: `redis://redis:6379`（服务名 `redis`；FIX-563 容器名已分化为 `sparkle_proj_redis`，旧 `sparkle_redis` 主机名在网络内不可解析——FIX-578 勘误）

## 4. 卷挂载 (Volumes)

为了数据持久化，我们将容器内的数据目录挂载到宿主机：

- `postgres_data`: `/var/lib/postgresql/data`
- `redis_data`: `/data`
- `minio_data`: `/data`

## 5. 环境变量 (Environment Variables)

我们支持 `.env` 文件配置。

- `DB_PASSWORD`: 数据库密码
- `JWT_SECRET`: 鉴权密钥
- `INTERNAL_API_KEY`: 内部服务通信密钥

## 6. 常用操作

```bash
# 启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f sparkle_gateway

# 进入数据库容器
docker compose exec sparkle_db psql -U postgres sparkle

# 重启特定服务
docker compose restart celery_worker
```
