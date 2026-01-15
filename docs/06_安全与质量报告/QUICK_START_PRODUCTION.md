# 🚀 快速开始 - 生产部署

**Phase 0 已完成！** 现在可以开始生产部署。

---

## ⚡ 5分钟快速启动

### 1️⃣ 验证环境 (1分钟)
```bash
# 检查依赖
docker --version          # 应显示 20.x+
python --version          # 应显示 3.10+
cd backend && pytest --version  # 应显示 pytest 7.x+
```

### 2️⃣ 启动基础设施 (2分钟)
```bash
# Terminal 1: 启动所有服务
make dev-all

# 等待所有容器启动 (约30秒)
# 检查状态
docker compose ps
```

### 3️⃣ 运行验证测试 (1分钟)
```bash
# Terminal 2: 运行完整验证
cd backend && python tests/integration/final_validation.py --all

# 预期输出: ✅ ALL TESTS PASSED
```

### 4️⃣ 查看监控 (1分钟)
```bash
# 打开监控面板
make celery-flower          # Celery监控: http://localhost:5555
open http://localhost:9090  # Prometheus
open http://localhost:3000  # Grafana (默认密码: admin/admin)
```

---

## 📋 生产部署清单

### 部署前检查 (Day 4 Morning)
```bash
# 1. 停止测试环境
make dev-down

# 2. 创建备份
cd backend && alembic upgrade head  # 确保迁移最新
docker exec sparkle-postgres pg_dump -U sparkle sparkle > backup.sql

# 3. 验证配置
cat backend/config/production_celery.py
cat backend/app/config.py
```

### 部署步骤 (Day 4 Afternoon)
```bash
# 14:00 - 数据库迁移
cd backend && alembic upgrade head

# 14:15 - 启动基础设施
docker compose up -d redis postgres

# 14:30 - 启动 Python gRPC
docker compose up -d grpc-server

# 14:45 - 启动 Celery
cd backend && make celery-up

# 15:00 - 启动 Gateway
cd backend/gateway && make gateway-dev

# 15:15 - 启动监控
docker compose up -d prometheus grafana alertmanager

# 15:30 - 运行烟雾测试
cd backend && python tests/integration/smoke_test.py
```

### 验证部署
```bash
# 检查所有服务健康
curl http://localhost:8080/health
curl http://localhost:50051/health
docker exec sparkle-celery-worker celery -A app.core.celery_app inspect ping

# 检查指标
curl http://localhost:9090/api/v1/query?query=up

# 检查告警
curl http://localhost:9093/api/v1/alerts
```

---

## 🎯 核心功能验证

### 1. LLM安全防护
```bash
# 测试提示注入检测
cd backend && python -m pytest tests/unit/test_llm_safety.py -v

# 测试配额限制
cd backend && python -m pytest tests/unit/test_llm_quota.py -v
```

### 2. 任务管理
```bash
# 检查 Celery 状态
docker exec sparkle-celery-worker celery -A app.core.celery_app status

# 查看活动任务
docker exec sparkle-celery-worker celery -A app.core.celery_app inspect active
```

### 3. 性能基准
```bash
# 运行压力测试
cd backend && python tests/performance/test_celery_stress.py --scenario=1 --tasks=1000

# 预期: >100 tasks/sec, >99% 成功率
```

### 4. 监控告警
```bash
# 访问 Grafana
open http://localhost:3000

# 导入仪表板:
# - Celery Official: ID 12345
# - Python Metrics: ID 12346
```

---

## 🔧 常用命令速查

### 服务管理
```bash
# 启动所有
make dev-all

# 查看状态
make celery-status

# 查看日志
make celery-logs-worker
make celery-logs-beat

# 重启服务
make celery-restart

# 停止服务
make celery-stop

# 清空队列 (谨慎!)
make celery-flush
```

### 测试验证
```bash
# 所有测试
cd backend && pytest

# 仅安全测试
cd backend && pytest tests/unit/test_llm_*.py -v

# 仅性能测试
cd backend && python tests/performance/test_celery_stress.py

# 最终验证
cd backend && python tests/integration/final_validation.py --all
```

### 监控查看
```bash
# Flower (Celery监控)
make celery-flower
# 访问: http://localhost:5555

# Prometheus
open http://localhost:9090

# Grafana
open http://localhost:3000
# 默认: admin / admin
```

---

## 🚨 故障排查

### 问题: 服务启动失败
```bash
# 1. 检查端口占用
lsof -i :8080,50051,5555,9090

# 2. 检查容器日志
docker logs sparkle-grpc-server --tail 50
docker logs sparkle-gateway --tail 50

# 3. 检查环境变量
env | grep -E "(REDIS|DATABASE|LLM)"
```

### 问题: Celery Worker 不工作
```bash
# 1. 检查 Worker 状态
docker exec sparkle-celery-worker celery -A app.core.celery_app inspect ping

# 2. 检查 Redis 连接
docker exec sparkle-redis redis-cli ping

# 3. 查看 Worker 日志
docker logs sparkle-celery-worker --tail 100
```

### 问题: 监控无数据
```bash
# 1. 检查 Prometheus
curl http://localhost:9090/healthy

# 2. 检查指标端点
curl http://localhost:8080/metrics

# 3. 重启监控服务
docker compose restart prometheus
```

---

## 📊 性能基准参考

### 优秀指标
- 吞吐量: >200 tasks/sec
- P95延迟: <50ms
- 失败率: <1%
- 内存增长: <10MB/千任务

### 良好指标
- 吞吐量: 100-200 tasks/sec
- P95延迟: 50-100ms
- 失败率: 1-3%
- 内存增长: 10-50MB

### 需要优化
- 吞吐量: 50-100 tasks/sec
- P95延迟: 100-500ms
- 失败率: 3-5%
- 内存增长: 50-100MB

### 严重问题
- 吞吐量: <50 tasks/sec
- P95延迟: >500ms
- 失败率: >5%
- 内存增长: >100MB

---

## 🎯 成功标准

### 部署成功 (第一小时)
✅ 所有服务运行
✅ 无 critical 告警
✅ 任务正常处理
✅ 指标正常采集
✅ 日志无异常

### 稳定运行 (第一天)
✅ 100% 任务成功率
✅ 性能在基准内
✅ 零安全事件
✅ 告警功能正常
✅ 用户反馈良好

### 生产就绪 (第一周)
✅ 99.9% 可用性
✅ 性能稳定
✅ 成本可控
✅ 扩展性验证
✅ 团队熟练

---

## 📚 完整文档

### 必读文档
1. **`docs/WEEK4_PRODUCTION_DEPLOYMENT_PLAN.md`** - 4天详细计划
2. **`PRODUCTION_DEPLOYMENT_CHECKLIST.md`** - 100+项检查清单
3. **`docs/PERFORMANCE_TUNING_GUIDE.md`** - 性能调优指南
4. **`PHASE0_COMPLETE_FINAL_SUMMARY.md`** - 完整总结

### 技术文档
- `docs/深度技术讲解教案_完整版.md` - 技术深度指南
- `docs/02_技术设计文档/02_知识星图系统设计_v3.0.md` - 架构设计
- `backend/config/production_celery.py` - 生产配置模板

---

## 🆘 紧急求助

### 如果遇到严重问题

1. **立即停止部署**
   ```bash
   make celery-stop
   docker compose down
   ```

2. **恢复到之前版本**
   ```bash
   git checkout previous-stable-tag
   docker compose up -d
   ```

3. **联系团队**
   - Slack: #incident-response
   - Email: backend@sparkle.ai
   - Phone: +86-XXX-XXXX-XXXX

4. **收集日志**
   ```bash
   docker logs sparkle-grpc-server > /tmp/error.log
   docker logs sparkle-gateway >> /tmp/error.log
   docker logs sparkle-celery-worker >> /tmp/error.log
   ```

---

## 🎉 恭喜！

**Phase 0 已完美完成！**

你现在拥有:
- ✅ 5层LLM安全防护
- ✅ 完整的任务管理系统
- ✅ 全面的性能测试套件
- ✅ 生产级监控告警
- ✅ 详细的部署文档

**准备开始生产部署吧！** 🚀

---

**快速开始版本**: 1.0
**最后更新**: 2026-01-03
**状态**: ✅ 生产就绪
