# 本地发布前最终启动与验收 Checklist

更新时间：2026-03-31  
适用范围：本地发布前最后一次全链路启动、健康确认、模拟器验收。  
适用对象：开发者、QA、发布负责人。

关联文档：
- `/Users/brsama/code/GitHub/Sparkle-project/docs/verification/本地最终签收基线说明_2026-03-30.md`
- `/Users/brsama/code/GitHub/Sparkle-project/docs/verification/系统模块验收清单_2026-03-31.md`
- `/Users/brsama/code/GitHub/Sparkle-project/docs/05_部署与运维/服务器全套环境与服务配置指南_2026-03-31.md`

---

## 1. 这份清单解决什么问题

这份清单不是“怎么开发”，而是“准备发布前，我本地到底应该按什么顺序把所有环境拉起来，并确认它们真的可用”。

本轮确认过的关键约束：

- 本机 `5432` 应该让给 Docker 内的 `sparkle_db`
- 监控栈需要单独确认 `3000 / 3100 / 4317 / 9090 / 9093`
- 最终验收默认走完整监控模式，不走 `docker-compose.dev.yml`
- iOS 与 Android 都必须基于最新后端状态重新构建并起到模拟器

---

## 2. 最终启动命令

### 2.1 启动前清场

先确认 Docker Desktop 已启动：

```bash
docker version
docker compose version
```

停掉本机 PostgreSQL，避免 `5432` 冲突：

```bash
brew services stop postgresql@16
lsof -nP -iTCP:5432 -sTCP:LISTEN
```

预期：

- `brew services list` 中 `postgresql@16` 为 `none`
- `5432` 之后只应由 Docker 监听

如果你必须保留本机 PostgreSQL，不要硬抢端口，改仓库根 `.env` 中的 `SPARKLE_DB_PORT`。

### 2.2 启完整业务栈 + 监控栈

在仓库根目录执行：

```bash
docker compose up -d
docker compose ps
```

当前完整模式应包含：

- `sparkle_db`
- `sparkle_redis`
- `sparkle_minio`
- `sparkle_api`
- `sparkle_agent`
- `sparkle_gateway`
- `celery_worker`
- `celery_glm_batch_worker`
- `sparkle_tempo`
- `sparkle_prometheus`
- `sparkle_alertmanager`
- `sparkle_loki`
- `sparkle_promtail`
- `sparkle_grafana`

如果只是日常开发、暂时不验监控，可用轻量模式：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

---

## 3. 启动后健康检查

### 3.1 核心业务健康

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8080/api/v1/health
curl -fsS http://127.0.0.1:9000/minio/health/live
nc -z 127.0.0.1 50051 && echo grpc_ok
docker exec sparkle_redis redis-cli -a change-me ping
```

预期：

- API 返回 `healthy`
- Gateway 返回 `status: ok`
- MinIO 返回 `200 OK`
- gRPC 端口可连
- Redis 返回 `PONG`

### 3.2 Celery 健康

```bash
docker exec sparkle-project-celery_worker-1 celery -A app.core.celery_app inspect ping
docker exec sparkle-project-celery_glm_batch_worker-1 celery -A app.core.celery_app inspect ping
```

预期：

- 普通 worker 和 `glm-batch` worker 都返回 `pong`

### 3.3 GraphRAG / AGE 健康

```bash
docker exec sparkle_db psql -U brsama -d sparkle -c "LOAD 'age'; SELECT extname FROM pg_extension ORDER BY 1; SELECT graphid, name, namespace FROM ag_catalog.ag_graph;"
```

预期：

- 扩展中至少有 `age`、`vector`
- 存在 `sparkle_galaxy`

---

## 4. 监控栈验收命令

```bash
curl -I -s http://127.0.0.1:3000/login | head -n 5
curl -s http://127.0.0.1:9090/-/healthy
curl -s http://127.0.0.1:9093/-/healthy
curl -s http://127.0.0.1:3100/ready
nc -z 127.0.0.1 4317 && echo tempo_ok
```

预期：

- Grafana 登录页返回 `200`
- Prometheus 返回 `Prometheus Server is Healthy.`
- Alertmanager 返回 `OK`
- Loki 返回 `ready`
- Tempo `4317` 端口可连

默认本地入口：

- Grafana: `http://127.0.0.1:3000`
- Prometheus: `http://127.0.0.1:9090`
- Alertmanager: `http://127.0.0.1:9093`

---

## 5. 移动端最终启动命令

### 5.1 Flutter 依赖

```bash
cd mobile
flutter pub get
flutter devices
```

### 5.2 Android

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/mobile
flutter run -d emulator-5554 --debug
```

### 5.3 iOS

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/mobile
flutter run -d 79461B43-C730-47C4-9994-10CA7C5546BD --debug
```

如果要只做重新构建，不立即 attach：

```bash
cd mobile
flutter build apk --debug
flutter build ios --simulator --debug
```

---

## 6. 人工验收最小路径

两端都要过一遍：

1. 进入首页，确认不白屏、不报错。
2. 切换首页 / 星图 / 对话 / 社群 / 我的五个主 Tab。
3. 发一条对话消息，确认 WebSocket 与回包正常。
4. 打开星图/学习路径相关页面，确认 GraphRAG 主链不空白。
5. 看一次上传或依赖 MinIO 的页面，确认对象存储链路可用。
6. 打开 Grafana 首页，确认监控面板可访问。

Android 额外确认：

- 不再出现 `System UI isn't responding`
- 首屏进入后无持续 loading 卡死

iOS 额外确认：

- 后端重启后不再持续出现 `localhost:8080` connection refused

---

## 7. 常用故障排查命令

看容器状态：

```bash
docker compose ps
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

看核心日志：

```bash
docker logs --tail 100 sparkle_api
docker logs --tail 100 sparkle_gateway
docker logs --tail 100 sparkle_agent
docker logs --tail 100 sparkle_prometheus
docker logs --tail 100 sparkle_grafana
```

看端口占用：

```bash
lsof -nP -iTCP:5432 -iTCP:6379 -iTCP:8000 -iTCP:8080 -iTCP:9000 -iTCP:9001 -iTCP:50051 -iTCP:3000 -iTCP:3100 -iTCP:4317 -iTCP:9090 -iTCP:9093 -sTCP:LISTEN
```

如果监控栈镜像拉取异常：

- 不要反复 `docker compose down`
- 先单独 `docker pull`
- 若 `latest` 卡住，优先固定版本镜像

---

## 8. 本轮推荐基线

当前本地可重复执行的推荐命令组：

```bash
cd /Users/brsama/code/GitHub/Sparkle-project

brew services stop postgresql@16

docker compose up -d

curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8080/api/v1/health
curl -fsS http://127.0.0.1:9000/minio/health/live
curl -s http://127.0.0.1:9090/-/healthy
curl -s http://127.0.0.1:9093/-/healthy
curl -s http://127.0.0.1:3100/ready

cd mobile
flutter pub get
flutter run -d emulator-5554 --debug
flutter run -d 79461B43-C730-47C4-9994-10CA7C5546BD --debug
```

结论：

- 这份清单可以作为“发布前最后一次本地全环境拉起”的唯一执行入口
- 若这里全部通过，再进入专项人工体验签收
