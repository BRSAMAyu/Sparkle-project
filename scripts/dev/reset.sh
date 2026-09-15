#!/usr/bin/env bash
# scripts/dev/reset.sh — Reset local development environment to clean state
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] [reset] $*"; }

# ── 1. Stop everything ──
log "Stopping all services..."
bash "$ROOT_DIR/scripts/dev/down.sh" 2>&1 | tail -3

# ── 2. Remove Docker volumes ──
log "Removing Docker data volumes..."
cd "$ROOT_DIR"
docker compose down -v --remove-orphans >>"$LOG_DIR/docker_reset.log" 2>&1 || true

# ── 3. Clean logs ──
log "Cleaning backend logs..."
rm -rf "$ROOT_DIR/backend/logs/local/"*.log 2>/dev/null || true

# ── 4. Clean artifacts ──
log "Cleaning E2E artifacts..."
rm -rf "$ROOT_DIR/artifacts/e2e/logs/"* 2>/dev/null || true
rm -rf "$ROOT_DIR/artifacts/e2e/screenshots/"*/*  2>/dev/null || true
rm -rf "$ROOT_DIR/artifacts/e2e/videos/"*/* 2>/dev/null || true
rm -rf "$ROOT_DIR/artifacts/e2e/reports/"* 2>/dev/null || true

# ── 5. Clean Flutter build cache ──
if [ -d "$ROOT_DIR/mobile" ]; then
  log "Cleaning Flutter build cache..."
  (cd "$ROOT_DIR/mobile" && flutter clean >>"$LOG_DIR/flutter_clean.log" 2>&1) || true
fi

log "Reset complete. Run scripts/dev/up.sh to start fresh."
