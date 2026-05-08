#!/usr/bin/env bash
# scripts/dev/up.sh — Start Sparkle local development infrastructure
# Wraps: make dev-up, docker compose, dev_local_stack.sh
# Starts: PostgreSQL, Redis, MinIO, AGE extension, knowledge index
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] [up] $*"; }
die() { echo "[$(date '+%H:%M:%S')] [up] FATAL: $*" >&2; exit 1; }

# ── 1. Check prerequisites ──
log "Checking prerequisites..."

command -v docker >/dev/null 2>&1 || die "docker not found. Install Docker Desktop."
docker info >/dev/null 2>&1 || die "Docker daemon not running. Start Docker Desktop."

if ! command -v make >/dev/null 2>&1; then
  die "make not found."
fi

# ── 2. Start Docker infrastructure ──
log "Starting Docker services (PostgreSQL, Redis, MinIO)..."
if ! (cd "$ROOT_DIR" && docker compose up -d sparkle_db redis minio) >"$LOG_DIR/docker_up.log" 2>&1; then
  cat "$LOG_DIR/docker_up.log"
  die "Docker compose up failed. Check $LOG_DIR/docker_up.log"
fi
log "Docker services started."

# ── 3. Wait for PostgreSQL ──
log "Waiting for PostgreSQL..."
for i in $(seq 1 30); do
  if docker exec sparkle-db pg_isready -U "${POSTGRES_USER:-brsama}" >/dev/null 2>&1; then
    log "PostgreSQL ready."
    break
  fi
  if [ "$i" -eq 30 ]; then
    die "PostgreSQL not ready after 30s."
  fi
  sleep 1
done

# ── 4. Wait for Redis ──
log "Waiting for Redis..."
for i in $(seq 1 15); do
  if docker exec sparkle-redis redis-cli ping >/dev/null 2>&1; then
    log "Redis ready."
    break
  fi
  if [ "$i" -eq 15 ]; then
    die "Redis not ready after 15s."
  fi
  sleep 1
done

# ── 5. Initialize AGE extension ──
log "Initializing Apache AGE extension..."
if [ -f "$ROOT_DIR/scripts/dev_local_stack.sh" ]; then
  # Source the AGE init logic from existing script
  export POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
  export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
  export POSTGRES_USER="${POSTGRES_USER:-brsama}"
  export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-change-me}"
  export POSTGRES_DB="${POSTGRES_DB:-sparkle}"
  (
    cd "$ROOT_DIR/backend"
    export PATH="$ROOT_DIR/backend/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
    for attempt in 1 2 3 4 5; do
      if .venv/bin/python scripts/init_age_extension.py >/dev/null 2>&1; then
        echo "AGE schema ready."
        break
      fi
      echo "AGE init attempt $attempt failed, retrying..."
      sleep 3
    done
  ) || log "WARNING: AGE init failed (non-fatal for basic dev)"
fi

# ── 6. Initialize knowledge index ──
log "Initializing knowledge index..."
(
  cd "$ROOT_DIR/backend"
  export PATH="$ROOT_DIR/backend/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
  .venv/bin/python scripts/init_redis_index.py >/dev/null 2>&1 && log "Knowledge index ready." || log "WARNING: Knowledge index init failed (non-fatal)"
) || true

# ── 7. Run Alembic migrations ──
log "Running database migrations..."
(
  cd "$ROOT_DIR/backend"
  export PATH="$ROOT_DIR/backend/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
  export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://${POSTGRES_USER:-brsama}:${POSTGRES_PASSWORD:-change-me}@${POSTGRES_HOST:-127.0.0.1}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-sparkle}?sslmode=disable}"
  .venv/bin/alembic upgrade head >>"$LOG_DIR/migration.log" 2>&1 && log "Migrations applied." || log "WARNING: Migration failed (check $LOG_DIR/migration.log)"
) || true

# ── 8. Seed demo data (optional) ──
if [ "${SEED_DEMO:-false}" = "true" ]; then
  log "Seeding demo data..."
  (
    cd "$ROOT_DIR/backend"
    export PATH="$ROOT_DIR/backend/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
    .venv/bin/python scripts/seed_demo_user_enhanced.py >>"$LOG_DIR/seed.log" 2>&1 && log "Demo data seeded." || log "WARNING: Demo seed failed"
  ) || true
fi

# ── 9. Summary ──
log "========================================="
log "Infrastructure UP."
log "  PostgreSQL:  localhost:${POSTGRES_PORT:-5432}"
log "  Redis:       localhost:${REDIS_PORT:-6379}"
log "  MinIO:       localhost:9000 (console: 9001)"
log ""
log "Next: Start services with:"
log "  make grpc-server    # Python AI Engine (port 50051)"
log "  make api-server     # Python REST API (port 8000)"
log "  make gateway-dev    # Go Gateway (port 8080)"
log "========================================="
