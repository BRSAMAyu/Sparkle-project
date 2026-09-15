#!/usr/bin/env bash
# scripts/mobile/ios_run.sh — Run Flutter app on iOS Simulator
# Usage: bash scripts/mobile/ios_run.sh [--debug|--release]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] [ios-run] $*"; }

MODE="${1:---debug}"

cd "$ROOT_DIR/mobile"

# ── Get booted device ──
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
  log "No booted simulator. Booting one..."
  DEVICE_UDID=$(bash "$ROOT_DIR/scripts/mobile/ios_boot.sh") || exit 1
fi

log "Running app on simulator: $DEVICE_UDID (mode: $MODE)"
flutter run -d "$DEVICE_UDID" "$MODE" 2>&1 | tee "$LOG_DIR/flutter_ios_run.log"
