#!/bin/bash
# ⛔ DEPRECATED (FIX-577, 2026-09-28) — DO NOT USE. File kept as history, body
# intentionally NOT repaired.
#
# Dead-debt adjudication (FIX-563R1 发现1 尾巴): since FIX-563 (containers
# renamed sparkle_*→sparkle_proj_*, compose project finalized as
# sparkle-project) every `docker run` below fails loud — `--network
# sparkle-flutter_default` is a project name that no longer exists, and the
# env URLs reference `sparkle_redis:6379`, which resolves to nothing on this
# repo's network (service name is `redis`, container `sparkle_proj_redis`).
#
# Why deprecate instead of repair: this script's capability face is a strict
# subset of `make celery-up` — that target additionally starts the glm_batch
# worker, takes real credentials from .env (this script hardcodes
# change-me), and runs on the pinned sparkle-project_default network; the
# declarative equivalent is `docker compose -f docker-compose.celery.yml up
# -d`. Repairing a third divergent celery entry point would recreate exactly
# the Makefile/script drift FIX-563R1 flagged.
#
# ➜ Use instead:
#     make celery-up          # worker + glm_batch + beat (FLOWER_ENABLE=1 adds flower)
#     make celery-status / make celery-stop / make celery-logs-worker
#     docker compose -f docker-compose.celery.yml up -d   # compose path

# Quick start script for Celery services

echo "🚀 Starting Celery Task Queue System..."

# Check if backend image exists
if ! docker image ls | grep -q "sparkle_backend"; then
    echo "❌ Backend image not found. Please build it first:"
    echo "   cd backend && docker build -t sparkle_backend ."
    exit 1
fi

# Check if Redis is running
if ! docker ps | grep -q "sparkle_proj_redis"; then
    echo "❌ Redis not running. Please start main services first:"
    echo "   docker compose up -d redis"
    exit 1
fi

# Start Celery services
echo "✅ Starting Celery Worker and Beat..."
docker run -d \
    --name sparkle_proj_celery_worker \
    --network sparkle-flutter_default \
    -e DATABASE_URL=postgresql://postgres:change-me@sparkle_db:5432/sparkle \
    -e REDIS_URL=redis://:change-me@sparkle_redis:6379/1 \
    -e CELERY_BROKER_URL=redis://:change-me@sparkle_redis:6379/1 \
    -e CELERY_RESULT_BACKEND=redis://:change-me@sparkle_redis:6379/2 \
    -v $(pwd)/backend:/app \
    sparkle_backend \
    celery -A app.core.celery_app worker -l info -Q high_priority,default,low_priority --concurrency=2

docker run -d \
    --name sparkle_proj_celery_beat \
    --network sparkle-flutter_default \
    -e DATABASE_URL=postgresql://postgres:change-me@sparkle_db:5432/sparkle \
    -e REDIS_URL=redis://:change-me@sparkle_redis:6379/1 \
    -e CELERY_BROKER_URL=redis://:change-me@sparkle_redis:6379/1 \
    -v $(pwd)/backend:/app \
    sparkle_backend \
    celery -A app.core.celery_app beat -l info

# Start Flower
echo "✅ Starting Flower monitoring..."
docker run -d \
    --name sparkle_proj_flower \
    --network sparkle-flutter_default \
    -p 5555:5555 \
    mher/flower:1.2.0 \
    celery --broker=redis://:change-me@sparkle_redis:6379/1 flower --port=5555

echo ""
echo "✅ Celery services started!"
echo ""
echo "📊 Services:"
echo "   - Worker: docker logs -f sparkle_proj_celery_worker"
echo "   - Beat: docker logs -f sparkle_proj_celery_beat"
echo "   - Flower: http://localhost:5555"
echo ""
echo "🔄 Useful commands:"
echo "   make celery-logs-worker"
echo "   make celery-logs-beat"
echo "   make celery-flower"
echo "   make celery-status"
