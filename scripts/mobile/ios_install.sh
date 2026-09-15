#!/usr/bin/env bash
# scripts/mobile/ios_install.sh — Install Flutter app to booted iOS Simulator
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] [ios-install] $*"; }

APP_PATH="$ROOT_DIR/mobile/build/ios/iphonesimulator/Runner.app"

if [ ! -d "$APP_PATH" ]; then
  log "ERROR: App not built. Run scripts/mobile/ios_build.sh first."
  exit 1
fi

# Get booted device UDID
DEVICE_UDID=$(xcrun simctl list devices booted -j 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
for runtime, devs in data.get('devices', {}).items():
    for d in devs:
        if d.get('state') == 'Booted':
            print(d['udid'])
            sys.exit(0)
" 2>/dev/null || true)

if [ -z "$DEVICE_UDID" ]; then
  log "ERROR: No booted iOS simulator found. Run scripts/mobile/ios_boot.sh first."
  exit 1
fi

log "Installing app to simulator: $DEVICE_UDID"
xcrun simctl install "$DEVICE_UDID" "$APP_PATH" 2>&1 | tee "$LOG_DIR/ios_install.log"
log "App installed."
