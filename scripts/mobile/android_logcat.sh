#!/usr/bin/env bash
# scripts/mobile/android_logcat.sh — Capture Android logcat
# Usage: bash scripts/mobile/android_logcat.sh [DEVICE_ID] [duration_seconds]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] [android-logcat] $*"; }

DEVICE="${DEVICE_ID:-${1:-}}"
DURATION="${2:-30}"
OUTPUT="$LOG_DIR/android_logcat.log"

ADB_ARGS=""
[ -n "$DEVICE" ] && ADB_ARGS="-s $DEVICE"

log "Clearing logcat..."
adb $ADB_ARGS logcat -c 2>/dev/null || true

log "Capturing logcat for ${DURATION}s: $OUTPUT"
timeout "$DURATION" adb $ADB_ARGS logcat > "$OUTPUT" 2>/dev/null || true
log "Logcat saved: $OUTPUT"

# ── Quick analysis ──
log "Quick analysis:"
FATAL=$(grep -c "FATAL EXCEPTION" "$OUTPUT" 2>/dev/null || echo "0")
ANR=$(grep -c "ANR in" "$OUTPUT" 2>/dev/null || echo "0")
FLUTTER=$(grep -ciE "FlutterJNI|flutter" "$OUTPUT" 2>/dev/null || echo "0")
log "  FATAL: $FATAL  |  ANR: $ANR  |  Flutter lines: $FLUTTER"
