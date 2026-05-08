#!/usr/bin/env bash
# scripts/dev/down.sh — Stop all Sparkle local services
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] [down] $*"; }

log "Stopping Docker services..."
cd "$ROOT_DIR"

# Stop Celery first if running
if docker compose ps --format '{{.Name}}' 2>/dev/null | grep -q celery; then
  log "Stopping Celery workers..."
  make celery-stop >"$LOG_DIR/celery_down.log" 2>&1 || true
fi

# Stop all Docker services
docker compose down --remove-orphans >>"$LOG_DIR/docker_down.log" 2>&1 || true
log "Docker services stopped."

# Kill any stray Python/Go processes on known ports
for port in 50051 8000 8080; do
  pid=$(lsof -ti :"$port" 2>/dev/null || true)
  if [ -n "$pid" ]; then
    log "Killing process on port $port (PID: $pid)..."
    kill "$pid" 2>/dev/null || true
  fi
done

log "All services stopped."
