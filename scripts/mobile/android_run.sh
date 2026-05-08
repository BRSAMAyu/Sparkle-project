#!/usr/bin/env bash
# scripts/mobile/android_run.sh — Run Flutter app on Android device/emulator
# Usage: bash scripts/mobile/android_run.sh [DEVICE_ID]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] [android-run] $*"; }

DEVICE="${DEVICE_ID:-${1:-}}"

cd "$ROOT_DIR/mobile"

if [ -n "$DEVICE" ]; then
  log "Running app on: $DEVICE"
  flutter run -d "$DEVICE" 2>&1 | tee "$LOG_DIR/flutter_android_run.log"
else
  log "Running app on default device..."
  flutter run 2>&1 | tee "$LOG_DIR/flutter_android_run.log"
fi
