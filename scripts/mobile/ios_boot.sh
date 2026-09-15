#!/usr/bin/env bash
# scripts/mobile/ios_boot.sh — Boot an iOS Simulator for testing
# Usage: bash scripts/mobile/ios_boot.sh [device_name]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] [ios-boot] $*"; }

# ── Check xcrun ──
command -v xcrun >/dev/null 2>&1 || { log "ERROR: xcrun not found. Xcode required."; exit 1; }

# ── Check for already booted device ──
BOOTED=$(xcrun simctl list devices booted -j 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
devices = []
for runtime, devs in data.get('devices', {}).items():
    for d in devs:
        if d.get('state') == 'Booted':
            devices.append(d)
if devices:
    print(devices[0]['udid'])
" 2>/dev/null || true)

if [ -n "$BOOTED" ]; then
  log "Already booted simulator: $BOOTED"
  echo "$BOOTED"
  exit 0
fi

# ── Select device ──
DEVICE_QUERY="${1:-iPhone 16}"
log "Looking for simulator matching: $DEVICE_QUERY"

# Find an available device
DEVICE_UDID=$(xcrun simctl list devices available -j 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
query = '$DEVICE_QUERY'.lower()
for runtime, devs in data.get('devices', {}).items():
    # Prefer iOS runtimes
    if 'ios' not in runtime.lower():
        continue
    for d in devs:
        if query in d.get('name', '').lower() and d.get('isAvailable', False):
            print(d['udid'])
            sys.exit(0)
# Fallback: any available iPhone
for runtime, devs in data.get('devices', {}).items():
    if 'ios' not in runtime.lower():
        continue
    for d in devs:
        if 'iphone' in d.get('name', '').lower() and d.get('isAvailable', False):
            print(d['udid'])
            sys.exit(0)
print('')
" 2>/dev/null || true)

if [ -z "$DEVICE_UDID" ]; then
  log "ERROR: No suitable iOS simulator found."
  log "Available devices:"
  xcrun simctl list devices available 2>/dev/null | grep -i iphone || true
  exit 1
fi

# ── Boot device ──
log "Booting simulator: $DEVICE_UDID"
xcrun simctl boot "$DEVICE_UDID" 2>/dev/null || log "Device may already be booted."

# Wait for boot
for i in $(seq 1 30); do
  STATE=$(xcrun simctl list devices -j 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
for runtime, devs in data.get('devices', {}).items():
    for d in devs:
        if d['udid'] == '$DEVICE_UDID':
            print(d.get('state', 'Unknown'))
" 2>/dev/null || echo "Unknown")
  if [ "$STATE" = "Booted" ]; then
    log "Simulator booted: $DEVICE_UDID"
    echo "$DEVICE_UDID"
    exit 0
  fi
  sleep 2
done

log "ERROR: Simulator did not boot within 60s."
exit 1
