#!/usr/bin/env bash
# scripts/mobile/ios_screenshot.sh — Take screenshot from booted iOS Simulator
# Usage: bash scripts/mobile/ios_screenshot.sh [output_name]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCREENSHOT_DIR="$ROOT_DIR/artifacts/e2e/screenshots/ios"
mkdir -p "$SCREENSHOT_DIR"

log() { echo "[$(date '+%H:%M:%S')] [ios-screenshot] $*"; }

NAME="${1:-screenshot_$(date '+%Y%m%d_%H%M%S')}"
OUTPUT="$SCREENSHOT_DIR/${NAME}.png"

log "Taking screenshot: $OUTPUT"
xcrun simctl io booted screenshot "$OUTPUT" 2>/dev/null || {
  log "ERROR: Failed to take screenshot. Is simulator booted?"
  exit 1
}
log "Screenshot saved: $OUTPUT"
echo "$OUTPUT"
