# Sparkle Deployment Guide

更新时间：2026-03-22

这份文档是服务器部署的最小入口。更完整的部署准备与发布前检查见：

- [阶段 6 部署前最终准备清单](/Users/brsama/code/GitHub/Sparkle-project/docs/deployment/阶段6_部署前最终准备清单_2026-03-22.md)
- [全环境全链路部署启动对齐手册](/Users/brsama/code/GitHub/Sparkle-project/docs/deployment/全环境全链路部署启动对齐手册_2026-03-19.md)

## 1. 必填环境变量

后端与网关的样例配置来源：

- [backend/.env.example](/Users/brsama/code/GitHub/Sparkle-project/backend/.env.example)
- [backend/gateway/.env.example](/Users/brsama/code/GitHub/Sparkle-project/backend/gateway/.env.example)

至少需要准备：

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `INTERNAL_API_KEY`
- `BACKEND_URL`
- `AGENT_ADDRESS`
- `MINIO_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MINIO_BUCKET`
- `DASHSCOPE_API_KEY`
- `DEEPSEEK_API_KEY`
- `ZHIPU_API_KEY`
- `SILICONFLOW_API_KEY`
- `XIAOMI_MIMO_API_KEY`
- `XUNFEI_APP_ID`
- `XUNFEI_API_KEY`
- `XUNFEI_API_SECRET`

生产建议：

- `DEMO_MODE=false`
- `ALLOWED_ORIGINS` 只允许正式域名
- Guest 是否开放单独评估，不要沿用本地 demo 策略

## 2. 服务启动顺序

推荐顺序：

1. PostgreSQL
2. Redis
3. MinIO / S3
4. Python API
5. Python Agent gRPC
6. Go Gateway
7. Celery Worker
8. Celery Beat
9. GLM Batch Worker

## 3. 初始化步骤

```bash
docker compose up -d
cd backend && .venv/bin/python -m alembic upgrade head
make init-rag
make init-minio-buckets
cd backend && PYTHONPATH=. .venv/bin/python scripts/init_shop.py init
```

上线前确认：

- Alembic 已到 `head`
- Redis 图索引已初始化
- 对象存储桶已存在
- 商城种子与必要基础数据已完成

## 4. 健康检查

最小健康检查：

- `GET /health`
- `GET /ready`
- `GET /api/v1/health`
- `GET /api/v1/health/cqrs`

如果使用反向代理，还需要确认：

- WebSocket upgrade 正常
- `wss://.../ws/chat` 可连接
- 长连接超时不会被代理提前切断

## 5. 回滚

最小回滚策略：

- 应用版本回滚到上一镜像
- 配置回滚到上一版 `.env`
- 数据库迁移执行 `alembic downgrade -1`，或采用 forward-fix

在生产上做数据库回滚前，必须先确认该迁移可逆且不会破坏增量数据。

## 6. 发布前闸门

本地发布前至少完成：

```bash
make local-acceptance
make flutter-analyze-gate
make quality-budget-check
```

当前一份可回溯的最终验收快照见：

- [acceptance_snapshot_20260322_final.log](/Users/brsama/code/GitHub/Sparkle-project/docs/verification/acceptance_snapshot_20260322_final.log)
