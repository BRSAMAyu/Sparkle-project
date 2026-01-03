# 🎯 Command Reference Card

**Phase 0 Complete - Ready for Production**

---

## 🚀 Quick Start Commands

### Start Everything (30 seconds)
```bash
make dev-all
```

### Verify Installation (1 minute)
```bash
cd backend && python tests/integration/final_validation.py --all
```

### Check Health
```bash
curl http://localhost:8080/health
curl http://localhost:50051/health
```

---

## 🔧 Daily Operations

### Service Management
```bash
# Start all services
make dev-all

# Start Celery only
make celery-up

# Check status
make celery-status

# View logs
make celery-logs-worker
make celery-logs-beat

# Restart services
make celery-restart

# Stop services
make celery-stop

# Clear queue (⚠️ use with caution)
make celery-flush
```

### Monitoring Access
```bash
# Celery Flower (Task Monitor)
make celery-flower
# → http://localhost:5555

# Prometheus (Metrics)
open http://localhost:9090

# Grafana (Dashboards)
open http://localhost:3000
# Default: admin / admin
```

---

## 🧪 Testing Commands

### All Tests
```bash
cd backend && pytest
```

### Security Tests
```bash
cd backend && pytest tests/unit/test_llm_safety.py -v
cd backend && pytest tests/unit/test_llm_quota.py -v
cd backend && pytest tests/unit/test_llm_output_validator.py -v
```

### Task Management Tests
```bash
cd backend && pytest tests/unit/test_task_manager.py -v
cd backend && pytest tests/integration/test_task_manager_integration.py -v
```

### Performance Tests
```bash
# Stress test (1000 fast tasks)
cd backend && python tests/performance/test_celery_stress.py --scenario=1 --tasks=1000

# Benchmark suite
cd backend && python tests/performance/benchmark_suite.py

# Smart tuner
cd backend && python tests/performance/worker_tuner.py
```

### Final Validation
```bash
# Run all validation checks
cd backend && python tests/integration/final_validation.py --all

# Run specific tests
cd backend && python tests/integration/final_validation.py --security
cd backend && python tests/integration/final_validation.py --performance
cd backend && python tests/integration/final_validation.py --integration
```

---

## 📊 Monitoring & Debugging

### Check Metrics
```bash
# LLM metrics
curl -s "http://localhost:9090/api/v1/query?query=llm_calls_total" | jq .

# Task metrics
curl -s "http://localhost:9090/api/v1/query?query=celery_task_completed_total" | jq .

# Security events
curl -s "http://localhost:9090/api/v1/query?query=llm_security_events_total" | jq .
```

### Check Alerts
```bash
curl http://localhost:9093/api/v1/alerts | jq .
```

### Check Celery Status
```bash
# Worker status
docker exec sparkle-celery-worker celery -A app.core.celery_app status

# Active tasks
docker exec sparkle-celery-worker celery -A app.core.celery_app inspect active

# Scheduled tasks
docker exec sparkle-celery-worker celery -A app.core.celery_app inspect scheduled
```

### Check Logs
```bash
# Python gRPC server
docker logs sparkle-grpc-server --tail 50

# Gateway
docker logs sparkle-gateway --tail 50

# Celery Worker
docker logs sparkle-celery-worker --tail 50

# Celery Beat
docker logs sparkle-celery-beat --tail 50
```

---

## 🔍 Troubleshooting Commands

### Service Won't Start
```bash
# Check port usage
lsof -i :8080,50051,5555,9090

# Check container status
docker compose ps

# View all logs
docker compose logs -f
```

### Celery Issues
```bash
# Check Redis connection
docker exec sparkle-redis redis-cli ping

# Check worker health
docker exec sparkle-celery-worker celery -A app.core.celery_app inspect ping

# Restart worker
docker restart sparkle-celery-worker
```

### Database Issues
```bash
# Check migrations
cd backend && alembic current
cd backend && alembic heads

# Apply migrations
cd backend && alembic upgrade head

# Check connection
docker exec sparkle-postgres psql -U sparkle -c "SELECT 1;"
```

---

## 📝 Maintenance Commands

### Database
```bash
# Create migration
cd backend && alembic revision -m "description"

# Apply migration
cd backend && alembic upgrade head

# Rollback migration
cd backend && alembic downgrade -1
```

### Docker Cleanup
```bash
# Remove unused containers
docker system prune -f

# Remove unused images
docker image prune -a -f

# Remove unused volumes
docker volume prune -f
```

### Cache Clear
```bash
# Clear Redis
docker exec sparkle-redis redis-cli FLUSHALL

# Clear Celery queue
make celery-flush
```

---

## 🚨 Emergency Commands

### Immediate Stop
```bash
# Stop everything
docker compose down

# Stop Celery only
make celery-stop
```

### Emergency Logs
```bash
# Collect all logs
docker logs sparkle-grpc-server > /tmp/emergency.log 2>&1
docker logs sparkle-gateway >> /tmp/emergency.log 2>&1
docker logs sparkle-celery-worker >> /tmp/emergency.log 2>&1
```

### Rollback
```bash
# Restore previous version
git checkout previous-stable-tag

# Restore database
docker exec -i sparkle-postgres psql -U sparkle sparkle < /backup/pre-deploy.sql

# Restart
docker compose up -d
```

---

## 📚 Documentation Quick Access

### Essential Docs
```bash
# Quick start
cat QUICK_START_PRODUCTION.md

# Deployment plan
cat docs/WEEK4_PRODUCTION_DEPLOYMENT_PLAN.md

# Checklists
cat PRODUCTION_DEPLOYMENT_CHECKLIST.md

# Performance tuning
cat docs/PERFORMANCE_TUNING_GUIDE.md

# Complete summary
cat PHASE0_COMPLETE_FINAL_SUMMARY.md
```

### Configuration Files
```bash
# Production Celery config
cat backend/config/production_celery.py

# Prometheus config
cat monitoring/prometheus-celery.yml

# Alert rules
cat monitoring/celery_alerts.yml
```

---

## ✅ Pre-Deployment Checklist

Run these before production deployment:

```bash
# 1. All tests pass
cd backend && pytest

# 2. Security validation
cd backend && python tests/integration/final_validation.py --security

# 3. Performance validation
cd backend && python tests/integration/final_validation.py --performance

# 4. Integration validation
cd backend && python tests/integration/final_validation.py --integration

# 5. All services healthy
make celery-status
curl http://localhost:8080/health
curl http://localhost:50051/health

# 6. Metrics flowing
curl http://localhost:9090/api/v1/query?query=up

# 7. Alerts configured
curl http://localhost:9093/api/v1/alerts
```

---

## 🎯 Success Indicators

### ✅ All Systems Go
```bash
# Should return "pong"
docker exec sparkle-celery-worker celery -A app.core.celery_app inspect ping

# Should return 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health

# Should show metrics
curl -s http://localhost:9090/api/v1/query?query=up | jq '.data.result | length'
# Expected: >0

# Should show no critical alerts
curl -s http://localhost:9093/api/v1/alerts | jq '.data | length'
# Expected: 0 (or only warnings)
```

---

**Version**: 1.0
**Last Updated**: 2026-01-03
**Status**: ✅ Production Ready
