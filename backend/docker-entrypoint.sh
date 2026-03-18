#!/bin/bash
set -e

# Docker entrypoint: run DB migrations then start the requested service
echo "🔧 Sparkle container starting (SERVICE_ROLE=${SERVICE_ROLE:-api})..."

# Run Alembic migrations (only from the API role, not from gRPC or Celery)
if [ "${SERVICE_ROLE}" = "api" ] || [ "${RUN_MIGRATIONS}" = "true" ]; then
    echo "📦 Running database migrations..."
    alembic upgrade head
    echo "✅ Migrations complete"
fi

# Hand off to the CMD passed in (uvicorn / grpc_server.py / celery)
exec "$@"
