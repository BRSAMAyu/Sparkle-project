#!/usr/bin/env bash
# scripts/mobile/ios_build.sh — Build Flutter app for iOS Simulator
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] [ios-build] $*"; }

cd "$ROOT_DIR/mobile"

# ── 1. Dependencies ──
log "Getting Flutter dependencies..."
flutter pub get >"$LOG_DIR/ios_pub_get.log" 2>&1

log "Generating l10n..."
flutter gen-l10n >"$LOG_DIR/ios_gen_l10n.log" 2>&1 || true

# ── 2. CocoaPods ──
log "Running pod install..."
(cd ios && pod install >"$LOG_DIR/ios_pod_install.log" 2>&1) || {
  log "WARNING: pod install failed. See $LOG_DIR/ios_pod_install.log"
}

# ── 3. Build ──
log "Building for iOS Simulator..."
if flutter build ios --simulator --no-codesign >"$LOG_DIR/ios_build.log" 2>&1; then
  log "iOS Simulator build succeeded."
  log "  Output: build/ios/iphonesimulator/Runner.app"
else
  log "ERROR: iOS Simulator build failed. See $LOG_DIR/ios_build.log"
  tail -50 "$LOG_DIR/ios_build.log"
  exit 1
fi
