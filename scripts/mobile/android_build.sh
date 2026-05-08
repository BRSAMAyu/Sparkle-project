#!/usr/bin/env bash
# scripts/mobile/android_build.sh — Build Flutter APK for Android
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] [android-build] $*"; }

cd "$ROOT_DIR/mobile"

# ── Dependencies ──
log "Getting Flutter dependencies..."
flutter pub get >"$LOG_DIR/android_pub_get.log" 2>&1

log "Generating l10n..."
flutter gen-l10n >"$LOG_DIR/android_gen_l10n.log" 2>&1 || true

# ── Build APK ──
log "Building debug APK..."
if flutter build apk --debug >"$LOG_DIR/android_build.log" 2>&1; then
  APK_PATH="$ROOT_DIR/mobile/build/app/outputs/flutter-apk/app-debug.apk"
  log "Build succeeded: $APK_PATH"
else
  log "ERROR: Android build failed. See $LOG_DIR/android_build.log"
  tail -50 "$LOG_DIR/android_build.log"
  exit 1
fi
