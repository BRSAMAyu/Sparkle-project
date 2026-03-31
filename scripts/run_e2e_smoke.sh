#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

COMPOSE=(docker compose)
GENERATED_ENV_SENTINEL="${ROOT_DIR}/.e2e-smoke-generated-env"

POSTGRES_DB="${POSTGRES_DB:-sparkle}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-password}"
REDIS_PASSWORD="${REDIS_PASSWORD:-redispassword}"
JWT_SECRET="${JWT_SECRET:-ci-smoke-jwt-secret-with-32-plus-chars}"
ADMIN_SECRET="${ADMIN_SECRET:-ci-smoke-admin-secret-with-32-plus-chars}"
INTERNAL_API_KEY="${INTERNAL_API_KEY:-ci-smoke-internal-api-key}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin123}"

PYTHON_DATABASE_URL="${PYTHON_DATABASE_URL:-postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:5432/${POSTGRES_DB}}"
PYTHON_REDIS_URL="${PYTHON_REDIS_URL:-redis://:${REDIS_PASSWORD}@127.0.0.1:6379/0}"
GRPC_HOST="${GRPC_HOST:-127.0.0.1}"
GRPC_PORT="${GRPC_PORT:-50051}"
GATEWAY_HOST="${GATEWAY_HOST:-127.0.0.1}"
GATEWAY_PORT="${GATEWAY_PORT:-8080}"
LIVE_API_BASE_URL="${LIVE_API_BASE_URL:-http://127.0.0.1:8000/api/v1}"
LIVE_GATEWAY_BASE_URL="${LIVE_GATEWAY_BASE_URL:-http://127.0.0.1:8080/api/v1}"
LIVE_WS_BASE_URL="${LIVE_WS_BASE_URL:-ws://127.0.0.1:8080}"
LOCAL_SMOKE_USERNAME="${LOCAL_SMOKE_USERNAME:-chat_test}"
LOCAL_SMOKE_PASSWORD="${LOCAL_SMOKE_PASSWORD:-Chat123456}"


ensure_env_file() {
  if [[ -f "${ROOT_DIR}/.env" ]]; then
    return
  fi

  cat > "${ROOT_DIR}/.env" <<EOF
ENVIRONMENT=development
DEBUG=True
POSTGRES_HOST=sparkle_db
POSTGRES_PORT=5432
POSTGRES_DB=${POSTGRES_DB}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
DB_HOST=sparkle_db
DB_PORT=5432
DB_NAME=${POSTGRES_DB}
DB_USER=${POSTGRES_USER}
DB_PASSWORD=${POSTGRES_PASSWORD}
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@sparkle_db:5432/${POSTGRES_DB}
REDIS_HOST=sparkle_redis
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_URL=redis://:${REDIS_PASSWORD}@sparkle_redis:6379/0
MINIO_ROOT_USER=${MINIO_ROOT_USER}
MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=${MINIO_ROOT_USER}
MINIO_SECRET_KEY=${MINIO_ROOT_PASSWORD}
MINIO_BUCKET=sparkle-files
MINIO_USE_SSL=false
MINIO_AUTO_CREATE_BUCKET=true
JWT_SECRET=${JWT_SECRET}
ADMIN_SECRET=${ADMIN_SECRET}
INTERNAL_API_KEY=${INTERNAL_API_KEY}
BACKEND_URL=http://sparkle_api:8000
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317
CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@sparkle_redis:6379/1
CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@sparkle_redis:6379/2
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=change_me
ENABLE_CONTEXT_FOCUSING=true
ENABLE_CONTEXT_SEMANTIC_GATING=true
ENABLE_CONTEXT_BRIEFING=true
ENABLE_CONTEXT_FOCUS_METADATA=true
ENABLE_SESSION_FEEDBACK_ADAPTATION=true
ENABLE_ADAPTIVE_PRESENTATION=true
ENABLE_STRUCTURED_NEXT_ACTIONS=true
ENABLE_BLOCKED_TEMPERATURE=true
ENABLE_UX_PRESENTATION_METADATA=true
ENABLE_PERCEPTIBLE_INTELLIGENCE=true
ENABLE_PROACTIVE_INSIGHTS=true
ENABLE_PLAN_REASONING_SUMMARY=true
ENABLE_WEEKLY_LEARNING_REPORT=true
ENABLE_PROGRESS_COMPARISONS=true
EOF
  touch "${GENERATED_ENV_SENTINEL}"
}


cleanup_generated_env() {
  if [[ -f "${GENERATED_ENV_SENTINEL}" ]]; then
    rm -f "${ROOT_DIR}/.env" "${GENERATED_ENV_SENTINEL}"
  fi
}


wait_for_container() {
  local container_name="$1"
  local timeout_seconds="${2:-180}"
  local elapsed=0

  while (( elapsed < timeout_seconds )); do
    local status
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container_name}" 2>/dev/null || true)"
    if [[ "${status}" == "healthy" || "${status}" == "running" ]]; then
      return 0
    fi
    sleep 3
    elapsed=$((elapsed + 3))
  done

  echo "Timed out waiting for container ${container_name} to become healthy" >&2
  return 1
}


wait_for_http() {
  local url="$1"
  local timeout_seconds="${2:-120}"
  local elapsed=0

  while (( elapsed < timeout_seconds )); do
    if curl -fsS "${url}" >/dev/null; then
      return 0
    fi
    sleep 3
    elapsed=$((elapsed + 3))
  done

  echo "Timed out waiting for HTTP endpoint ${url}" >&2
  return 1
}


compose_up() {
  ensure_env_file
  "${COMPOSE[@]}" up -d --build sparkle_db redis
  "${COMPOSE[@]}" up -d --build sparkle_agent sparkle_api
  "${COMPOSE[@]}" up -d --build --no-deps sparkle_gateway

  wait_for_container "sparkle_db" 180
  wait_for_container "sparkle_redis" 180
  wait_for_container "sparkle_agent" 180
  wait_for_container "sparkle_api" 180
  wait_for_container "sparkle_gateway" 180

  wait_for_http "http://127.0.0.1:8000/health" 180
  wait_for_http "http://127.0.0.1:8080/api/v1/health" 180
  wait_for_http "http://127.0.0.1:8080/api/v1/health/cqrs" 180
}


compose_migrate() {
  "${COMPOSE[@]}" exec -T sparkle_api sh -lc "cd /app && alembic upgrade head"
}


run_grpc_smoke() {
  FULL_STACK_TESTS=1 \
  JWT_SECRET="${JWT_SECRET}" \
  DATABASE_URL="${PYTHON_DATABASE_URL}" \
  REDIS_URL="${PYTHON_REDIS_URL}" \
  GRPC_HOST="${GRPC_HOST}" \
  GRPC_PORT="${GRPC_PORT}" \
  PYTHONPATH="${ROOT_DIR}/backend" \
  python3 -m pytest backend/tests/integration/test_grpc_streaming_integration.py -m smoke -v
}


run_websocket_smoke() {
  FULL_STACK_TESTS=1 \
  JWT_SECRET="${JWT_SECRET}" \
  DATABASE_URL="${PYTHON_DATABASE_URL}" \
  REDIS_URL="${PYTHON_REDIS_URL}" \
  GATEWAY_HOST="${GATEWAY_HOST}" \
  GATEWAY_PORT="${GATEWAY_PORT}" \
  PYTHONPATH="${ROOT_DIR}/backend" \
  python3 -m pytest backend/tests/integration/test_websocket_full_stack.py -m smoke -v
}


run_flutter_smoke() {
  (
    cd "${ROOT_DIR}/mobile"
    flutter test test/integration/full_stack_e2e_test.dart \
      --dart-define=LIVE_API_BASE_URL="${LIVE_API_BASE_URL}" \
      --dart-define=LIVE_GATEWAY_BASE_URL="${LIVE_GATEWAY_BASE_URL}" \
      --dart-define=LIVE_WS_BASE_URL="${LIVE_WS_BASE_URL}" \
      --dart-define=LOCAL_SMOKE_USERNAME="${LOCAL_SMOKE_USERNAME}" \
      --dart-define=LOCAL_SMOKE_PASSWORD="${LOCAL_SMOKE_PASSWORD}" \
      -r compact
  )
}


seed_smoke_user() {
  LOCAL_SMOKE_USERNAME="${LOCAL_SMOKE_USERNAME}" \
  LOCAL_SMOKE_PASSWORD="${LOCAL_SMOKE_PASSWORD}" \
  python3 - <<'PY'
import json
import os
import urllib.error
import urllib.request

payload = json.dumps({
    "username": os.environ["LOCAL_SMOKE_USERNAME"],
    "email": f'{os.environ["LOCAL_SMOKE_USERNAME"]}@example.com',
    "password": os.environ["LOCAL_SMOKE_PASSWORD"],
    "accepted_tos": True,
    "accepted_privacy": True,
    "tos_version": "ci-smoke",
    "privacy_version": "ci-smoke",
    "agreed_locale": "zh-CN",
}).encode()
request = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/auth/register",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=20) as response:
        status = response.getcode()
except urllib.error.HTTPError as exc:
    status = exc.code
    if status not in {400, 409}:
        raise
assert status in {200, 201, 400, 409}, status
PY
}


print_logs() {
  "${COMPOSE[@]}" logs --tail=50 sparkle_db redis sparkle_agent sparkle_api sparkle_gateway || true
}


compose_down() {
  "${COMPOSE[@]}" down -v --remove-orphans || true
  cleanup_generated_env
}


usage() {
  cat <<EOF
Usage: scripts/run_e2e_smoke.sh <command>

Commands:
  up         Start core compose stack and wait for health checks
  migrate    Run Alembic upgrade head inside sparkle_api
  grpc       Run gRPC smoke tests
  websocket  Run WebSocket smoke tests
  flutter    Run Flutter full-stack smoke tests
  seed-user  Ensure the live smoke login user exists
  logs       Print last 50 lines from core service logs
  down       Stop compose stack and clean generated env file
EOF
}


case "${1:-}" in
  up)
    compose_up
    ;;
  migrate)
    compose_migrate
    ;;
  grpc)
    run_grpc_smoke
    ;;
  websocket)
    run_websocket_smoke
    ;;
  flutter)
    run_flutter_smoke
    ;;
  seed-user)
    seed_smoke_user
    ;;
  logs)
    print_logs
    ;;
  down)
    compose_down
    ;;
  *)
    usage
    exit 1
    ;;
esac
