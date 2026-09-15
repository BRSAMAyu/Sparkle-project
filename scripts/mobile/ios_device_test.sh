#!/usr/bin/env bash
# scripts/mobile/ios_device_test.sh — Test on real iOS device
# Usage: DEVICE_ID=xxx bash scripts/mobile/ios_device_test.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
REPORT_DIR="$ROOT_DIR/artifacts/e2e/reports"
SCREENSHOT_DIR="$ROOT_DIR/artifacts/e2e/screenshots/ios"
mkdir -p "$LOG_DIR" "$REPORT_DIR" "$SCREENSHOT_DIR"

REPORT_FILE="$REPORT_DIR/IOS_DEVICE_TEST_REPORT.md"

log() { echo "[$(date '+%H:%M:%S')] [ios-device] $*"; }

# ── Detect device ──
DEVICE="${DEVICE_ID:-}"
if [ -z "$DEVICE" ]; then
  DEVICE=$(flutter devices 2>/dev/null | grep -i 'iphone' | grep -v simulator | head -1 | awk '{print $1}' || true)
fi

if [ -z "$DEVICE" ]; then
  log "No iOS device found. Connect a device or set DEVICE_ID."
  {
    echo "# iOS Device Test Report"
    echo ""
    echo "**Status**: SKIPPED — No iOS device connected"
    echo "**Date**: $(date)"
    echo ""
    echo "Connect an iPhone and set DEVICE_ID to run this test."
  } > "$REPORT_FILE"
  exit 0
fi

log "Testing on device: $DEVICE"

# ── Prepare ──
cd "$ROOT_DIR/mobile"
flutter clean >"$LOG_DIR/ios_device_clean.log" 2>&1 || true
flutter pub get >"$LOG_DIR/ios_device_pubget.log" 2>&1
flutter gen-l10n >"$LOG_DIR/ios_device_l10n.log" 2>&1 || true
(cd ios && pod install >"$LOG_DIR/ios_device_pod.log" 2>&1) || true

# ── Build ──
log "Building for device..."
BUILD_OK=true
flutter build ios --debug >"$LOG_DIR/ios_device_build.log" 2>&1 || {
  BUILD_OK=false
  BUILD_ERROR=$(tail -20 "$LOG_DIR/ios_device_build.log")
}

if [ "$BUILD_OK" = "false" ]; then
  # Check for signing issues
  SIGNING_ISSUE=""
  grep -qi "signing\|provisioning\|certificate\|team" "$LOG_DIR/ios_device_build.log" && SIGNING_ISSUE="yes"

  {
    echo "# iOS Device Test Report"
    echo ""
    echo "**Status**: BUILD FAILED"
    echo "**Date**: $(date)"
    echo "**Device**: $DEVICE"
    echo ""
    if [ -n "$SIGNING_ISSUE" ]; then
      echo "## Signing Issue Detected"
      echo ""
      echo "The build failed due to code signing. Fix in Xcode:"
      echo "1. Open \`ios/Runner.xcworkspace\` in Xcode"
      echo "2. Select Runner target → Signing & Capabilities"
      echo "3. Set your Development Team"
      echo "4. Verify Bundle ID is unique"
      echo "5. Ensure a valid provisioning profile is selected"
      echo ""
    fi
    echo "## Build Error"
    echo ""
    echo "\`\`\`"
    echo "$BUILD_ERROR"
    echo "\`\`\`"
  } > "$REPORT_FILE"
  log "Build failed. Report: $REPORT_FILE"
  exit 1
fi

# ── Run ──
log "Installing and running on device..."
flutter run -d "$DEVICE" --debug >"$LOG_DIR/ios_device_run.log" 2>&1 &
RUN_PID=$!

# Wait for app to start (30s)
sleep 30

# ── Check for crashes ──
CRASHES=$(grep -ciE "crash|fatal|exception|terminated" "$LOG_DIR/ios_device_run.log" 2>/dev/null || echo "0")

# ── Report ──
{
  echo "# iOS Device Test Report"
  echo ""
  echo "**Status**: $([ "$CRASHES" -eq 0 ] && echo "RUNNING" || echo "CRASH DETECTED")"
  echo "**Date**: $(date)"
  echo "**Device**: $DEVICE"
  echo ""
  echo "## Build"
  echo "- Status: PASS"
  echo ""
  echo "## Runtime"
  echo "- Crash indicators: $CRASHES"
  echo "- Log: \`artifacts/e2e/logs/ios_device_run.log\`"
  echo ""
  echo "## Next Steps"
  echo "- Run integration tests: \`DEVICE_ID=$DEVICE bash scripts/test/run_e2e.sh\`"
  echo "- Check logs: \`bash scripts/dev/logs.sh --save\`"
} > "$REPORT_FILE"

log "Report: $REPORT_FILE"

# Kill the running app
kill "$RUN_PID" 2>/dev/null || true

[ "$CRASHES" -gt 0 ] && exit 1 || exit 0
