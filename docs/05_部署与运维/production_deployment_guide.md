# Sparkle Production Deployment Guide

## Architecture Overview

```
┌─ Flutter Mobile ─┐
│  1,064 .dart files│
│  39 feature modules│
└────────┬──────────┘
         │ WebSocket / REST
┌────────▼──────────┐
│  Go Gateway (:8080)│  16 middleware: Auth, Rate Limit, CORS, Security Headers
└────────┬──────────┘
         │ gRPC
┌────────▼──────────┐
│  Python Engine     │  FastAPI (:8000) + gRPC (:50051)
│  319+ .py files    │  LangGraph FSM + 30+ services
└────────┬──────────┘
         │
┌────────▼──────────┐
│  PostgreSQL 16     │  143 tables, pgvector, Apache AGE
│  + Redis Stack     │  Session cache, rate limit, event bus
│  + MinIO           │  Object storage
└───────────────────┘
```

## Prerequisites

- Docker + Docker Compose (v2+)
- Go 1.22.0, Python 3.11, Flutter 3.24.0
- Buf (proto generation)
- 8GB RAM minimum, 16GB recommended

## Deployment Steps

### 1. Infrastructure
```bash
docker compose up -d sparkle_db redis minio
# Wait for healthy: docker compose ps
```

### 2. Database Migration
```bash
cd backend
alembic upgrade head
```

### 3. Configuration
```bash
# Copy and edit environment
cp .env.example .env
# Required settings:
# - DATABASE_URL, REDIS_URL
# - SECRET_KEY (strong, 32+ chars)
# - JWT_SECRET
# - LLM_API_KEY
```

### 4. Self-Check
```bash
make env-check && make local-signoff-preflight
```

### 5. Start Services
```bash
# Python gRPC server
make grpc-server

# Python REST API
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Go Gateway
make gateway-dev
```

### 6. Smoke Test
```bash
make smoke
```

### 7. Seed Demo Data
```bash
cd backend && python scripts/seed_demo_user_enhanced.py
```

## Monitoring Stack

| Service | Port | Purpose |
|---------|------|---------|
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000 | Dashboards |
| Loki | 3100 | Log aggregation |
| Tempo | 4317 | Distributed tracing |
| Alertmanager | 9093 | Alert routing |

## Health Check Endpoints

- `GET /api/v1/health` — Gateway health
- `GET /health` — Python backend health
- gRPC reflection at `localhost:50051` (debug only)

## Rollback Procedure

1. Identify the commit to roll back to: `git log --oneline -20`
2. Create rollback branch: `git checkout -b rollback/<commit>`
3. Redeploy: restart all services
4. Verify: `make smoke`

## Alert Rules (11 SLO Rules)

| Alert | Severity | Condition |
|-------|----------|-----------|
| SparkleGatewayDown | P1 | Gateway unreachable 2m |
| SparkleBackendDown | P1 | Backend unreachable 2m |
| SparkleBackendHigh5xxRate | P2 | 5xx > 2% for 10m |
| SparkleBackendP95LatencyHigh | P2 | P95 > 1.5s for 10m |
| SparkleEventStreamLagHigh | P2 | Lag > 120s |

Runbook: `monitoring/runbooks/incident_response.md`
