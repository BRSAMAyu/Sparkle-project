#!/usr/bin/env bash
# scripts/mobile/android_device_test.sh — Test on real Android device
# Usage: DEVICE_ID=xxx bash scripts/mobile/android_device_test.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
REPORT_DIR="$ROOT_DIR/artifacts/e2e/reports"
SCREENSHOT_DIR="$ROOT_DIR/artifacts/e2e/screenshots/android"
mkdir -p "$LOG_DIR" "$REPORT_DIR" "$SCREENSHOT_DIR"

REPORT_FILE="$REPORT_DIR/ANDROID_DEVICE_TEST_REPORT.md"

log() { echo "[$(date '+%H:%M:%S')] [android-device] $*"; }

command -v adb >/dev/null 2>&1 || { log "ERROR: adb not found."; exit 1; }

# ── Detect device ──
DEVICE="${DEVICE_ID:-}"
if [ -z "$DEVICE" ]; then
  DEVICE=$(adb devices 2>/dev/null | grep -v "List" | grep -v "emulator" | grep -v "^$" | head -1 | awk '{print $1}' || true)
fi

if [ -z "$DEVICE" ]; then
  {
    echo "# Android Device Test Report"
    echo ""
    echo "**Status**: SKIPPED — No Android device connected"
    echo "**Date**: $(date)"
    echo ""
    echo "Connect an Android device with USB debugging enabled, or set DEVICE_ID."
  } > "$REPORT_FILE"
  exit 0
fi

log "Testing on device: $DEVICE"

# ── Prepare ──
cd "$ROOT_DIR/mobile"
flutter clean >"$LOG_DIR/android_device_clean.log" 2>&1 || true
flutter pub get >"$LOG_DIR/android_device_pubget.log" 2>&1
flutter gen-l10n >"$LOG_DIR/android_device_l10n.log" 2>&1 || true

# ── Build ──
log "Building debug APK..."
if flutter build apk --debug >"$LOG_DIR/android_device_build.log" 2>&1; then
  BUILD_OK=true
else
  BUILD_OK=false
  BUILD_ERROR=$(tail -20 "$LOG_DIR/android_device_build.log")
fi

if [ "$BUILD_OK" = "false" ]; then
  {
    echo "# Android Device Test Report"
    echo ""
    echo "**Status**: BUILD FAILED"
    echo "**Date**: $(date)"
    echo "**Device**: $DEVICE"
    echo ""
    echo "## Build Error"
    echo ""
    echo "\`\`\`"
    echo "$BUILD_ERROR"
    echo "\`\`\`"
  } > "$REPORT_FILE"
  exit 1
fi

# ── Install ──
log "Installing APK..."
APK_PATH="$ROOT_DIR/mobile/build/app/outputs/flutter-apk/app-debug.apk"
adb -s "$DEVICE" install -r "$APK_PATH" >"$LOG_DIR/android_device_install.log" 2>&1 || {
  log "WARNING: Install failed. See $LOG_DIR/android_device_install.log"
}

# ── Launch ──
PACKAGE="${ANDROID_PACKAGE:-com.example.sparkle}"
log "Launching app: $PACKAGE"
adb -s "$DEVICE" shell monkey -p "$PACKAGE" 1 >"$LOG_DIR/android_device_launch.log" 2>&1 || true

# Wait for app to start
sleep 5

# ── Capture logcat ──
log "Capturing logcat (30s)..."
adb -s "$DEVICE" logcat -c 2>/dev/null || true
sleep 25
adb -s "$DEVICE" logcat -d > "$LOG_DIR/android_device_logcat.log" 2>/dev/null || true

# ── Screenshot ──
adb -s "$DEVICE" exec-out screencap -p > "$SCREENSHOT_DIR/device_launch.png" 2>/dev/null || true

# ── Analyze ──
FATAL=$(grep -c "FATAL EXCEPTION" "$LOG_DIR/android_device_logcat.log" 2>/dev/null || echo "0")
ANR=$(grep -c "ANR in" "$LOG_DIR/android_device_logcat.log" 2>/dev/null || echo "0")
FLUTTER_ERR=$(grep -ciE "FlutterJNI.*exception|PlatformException" "$LOG_DIR/android_device_logcat.log" 2>/dev/null || echo "0")

STATUS="OK"
[ "$FATAL" -gt 0 ] || [ "$ANR" -gt 0 ] && STATUS="CRASH DETECTED"

# ── Report ──
{
  echo "# Android Device Test Report"
  echo ""
  echo "**Status**: $STATUS"
  echo "**Date**: $(date)"
  echo "**Device**: $DEVICE"
  echo ""
  echo "## Build"
  echo "- Status: PASS"
  echo ""
  echo "## Runtime"
  echo "- FATAL EXCEPTION: $FATAL"
  echo "- ANR: $ANR"
  echo "- Flutter errors: $FLUTTER_ERR"
  echo "- Screenshot: \`artifacts/e2e/screenshots/android/device_launch.png\`"
  echo "- Logcat: \`artifacts/e2e/logs/android_device_logcat.log\`"
  echo ""
  echo "## Analysis"
  if [ "$FATAL" -gt 0 ]; then
    echo "### Fatal Exceptions"
    grep -A5 "FATAL EXCEPTION" "$LOG_DIR/android_device_logcat.log" 2>/dev/null || true
    echo ""
  fi
  if [ "$ANR" -gt 0 ]; then
    echo "### ANR"
    grep -A3 "ANR in" "$LOG_DIR/android_device_logcat.log" 2>/dev/null || true
    echo ""
  fi
} > "$REPORT_FILE"

log "Report: $REPORT_FILE"
[ "$STATUS" = "CRASH DETECTED" ] && exit 1 || exit 0
