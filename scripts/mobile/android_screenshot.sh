#!/usr/bin/env bash
# scripts/mobile/android_screenshot.sh — Take screenshot from Android device
# Usage: bash scripts/mobile/android_screenshot.sh [DEVICE_ID] [output_name]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCREENSHOT_DIR="$ROOT_DIR/artifacts/e2e/screenshots/android"
mkdir -p "$SCREENSHOT_DIR"

log() { echo "[$(date '+%H:%M:%S')] [android-screenshot] $*"; }

DEVICE="${DEVICE_ID:-${1:-}}"
NAME="${2:-screenshot_$(date '+%Y%m%d_%H%M%S')}"
OUTPUT="$SCREENSHOT_DIR/${NAME}.png"

ADB_ARGS=""
[ -n "$DEVICE" ] && ADB_ARGS="-s $DEVICE"

log "Taking screenshot: $OUTPUT"
adb $ADB_ARGS exec-out screencap -p > "$OUTPUT" 2>/dev/null || {
  log "ERROR: Failed to take screenshot."
  exit 1
}
log "Screenshot saved: $OUTPUT"
echo "$OUTPUT"
