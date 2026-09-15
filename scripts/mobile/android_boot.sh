#!/usr/bin/env bash
# scripts/mobile/android_boot.sh — Boot an Android Emulator for testing
# Usage: bash scripts/mobile/android_boot.sh [avd_name]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] [android-boot] $*"; }

command -v adb >/dev/null 2>&1 || { log "ERROR: adb not found. Install Android SDK."; exit 1; }

# ── Check for already running device ──
DEVICES=$(adb devices 2>/dev/null | grep -v "List" | grep -v "^$" | wc -l | tr -d ' ')
if [ "$DEVICES" -gt 0 ]; then
  log "Android device(s) already connected:"
  adb devices -l 2>/dev/null | grep -v "List"
  # Return the first device
  adb devices 2>/dev/null | grep -v "List" | grep -v "^$" | head -1 | awk '{print $1}'
  exit 0
fi

# ── Find emulator command ──
EMULATOR_CMD=""
for candidate in "$ANDROID_HOME/emulator/emulator" "$ANDROID_SDK_ROOT/emulator/emulator" \
  "$HOME/Library/Android/sdk/emulator/emulator"; do
  if [ -x "$candidate" ]; then
    EMULATOR_CMD="$candidate"
    break
  fi
done

if [ -z "$EMULATOR_CMD" ]; then
  # Try finding in PATH
  EMULATOR_CMD=$(command -v emulator 2>/dev/null || true)
fi

if [ -z "$EMULATOR_CMD" ]; then
  log "ERROR: emulator command not found. Install Android SDK."
  exit 1
fi

# ── List available AVDs ──
AVD_NAME="${1:-}"
if [ -z "$AVD_NAME" ]; then
  # Pick first available AVD
  AVD_NAME=$("$EMULATOR_CMD" -list-avds 2>/dev/null | head -1 || true)
fi

if [ -z "$AVD_NAME" ]; then
  log "ERROR: No Android Virtual Device found."
  log "Create one with: avdmanager create avd -n test -k 'system-images;android-34;google_apis;x86_64'"
  exit 1
fi

log "Booting emulator: $AVD_NAME"
"$EMULATOR_CMD" -avd "$AVD_NAME" -no-snapshot-save -no-audio -no-boot-anim \
  -gpu swiftshader_indirect >"$LOG_DIR/android_emulator.log" 2>&1 &
EMU_PID=$!

# ── Wait for boot ──
log "Waiting for emulator to boot..."
for i in $(seq 1 60); do
  BOOT_COMPLETE=$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)
  if [ "$BOOT_COMPLETE" = "1" ]; then
    DEVICE=$(adb devices 2>/dev/null | grep -v "List" | grep "emulator" | head -1 | awk '{print $1}')
    log "Emulator booted: $DEVICE (AVD: $AVD_NAME)"
    echo "$DEVICE"
    exit 0
  fi
  sleep 2
done

log "ERROR: Emulator did not boot within 120s."
kill "$EMU_PID" 2>/dev/null || true
exit 1
