#!/bin/bash
set -euo pipefail

TARGET_URL="$1"
echo "Verifying deployment at $TARGET_URL..."

# 1. Basic Health Check
echo "1. Health Check"
if ! curl -f "$TARGET_URL/api/v1/health" > /dev/null 2>&1; then
  echo "❌ Health check failed"
  exit 1
fi
echo "✅ Health check passed"

# 2. Latency Check
echo "2. Latency Check"
LATENCY=$(curl -w "%{time_total}" -o /dev/null -s "$TARGET_URL/api/v1/health")
if (( $(echo "$LATENCY > 0.5" | bc -l) )); then
  echo "⚠️ Latency too high: ${LATENCY}s (warning only)"
  # exit 1  # Uncomment to enforce strict latency
else
  echo "✅ Latency OK: ${LATENCY}s"
fi

# 3. Smoke Test (Optional - if we had a specific endpoint)
# if ! curl -f -X POST "$TARGET_URL/api/v1/chat" -d '{"message":"test"}' ...
#   echo "Chat API test failed"
# fi

echo "Deployment verified successfully"
exit 0
