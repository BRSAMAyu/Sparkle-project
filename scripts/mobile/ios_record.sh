#!/usr/bin/env bash
# scripts/mobile/ios_record.sh — Record video from booted iOS Simulator
# Usage: bash scripts/mobile/ios_record.sh [output_name] [duration_seconds]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VIDEO_DIR="$ROOT_DIR/artifacts/e2e/videos/ios"
mkdir -p "$VIDEO_DIR"

log() { echo "[$(date '+%H:%M:%S')] [ios-record] $*"; }

NAME="${1:-recording_$(date '+%Y%m%d_%H%M%S')}"
DURATION="${2:-30}"
OUTPUT="$VIDEO_DIR/${NAME}.mov"

log "Recording $DURATION seconds to: $OUTPUT"
xcrun simctl io booted recordVideo "$OUTPUT" &
RECORD_PID=$!

sleep "$DURATION"
kill "$RECORD_PID" 2>/dev/null || true
log "Recording saved: $OUTPUT"
echo "$OUTPUT"
