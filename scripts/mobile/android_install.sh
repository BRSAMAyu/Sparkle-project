#!/usr/bin/env bash
# scripts/mobile/android_install.sh — Install APK to connected Android device
# Usage: bash scripts/mobile/android_install.sh [DEVICE_ID]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] [android-install] $*"; }

APK_PATH="$ROOT_DIR/mobile/build/app/outputs/flutter-apk/app-debug.apk"

if [ ! -f "$APK_PATH" ]; then
  log "ERROR: APK not built. Run scripts/mobile/android_build.sh first."
  exit 1
fi

DEVICE="${DEVICE_ID:-${1:-}}"
ADB_ARGS=""
if [ -n "$DEVICE" ]; then
  ADB_ARGS="-s $DEVICE"
fi

log "Installing APK to device..."
adb $ADB_ARGS install -r "$APK_PATH" 2>&1 | tee "$LOG_DIR/android_install.log"
log "APK installed."
