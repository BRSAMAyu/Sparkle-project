#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"

# Start infra (Postgres/Redis/MinIO) if needed
make -C "$ROOT_DIR" dev-up >/dev/null 2>&1 || true

# Start Python gRPC server
if ! lsof -nP -iTCP:50051 -sTCP:LISTEN >/dev/null 2>&1; then
  (cd "$ROOT_DIR/backend" && nohup python grpc_server.py > "$LOG_DIR/grpc_server.log" 2>&1 &)
fi

# Start FastAPI backend (port 8000)
if ! lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  (cd "$ROOT_DIR/backend" && nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/backend_api.log" 2>&1 &)
fi

# Start Gateway (port 8080)
if ! lsof -nP -iTCP:8080 -sTCP:LISTEN >/dev/null 2>&1; then
  (cd "$ROOT_DIR/backend/gateway" && nohup bash -lc 'set -a; source .env; set +a; go run cmd/server/main.go' > "$LOG_DIR/gateway.log" 2>&1 &)
fi

sleep 3

echo "Stage 3 services started. Logs in $LOG_DIR"

echo "Health checks:"
set +e
curl -fsS http://localhost:8000/health >/dev/null && echo "- backend: OK" || echo "- backend: FAIL"
curl -fsS http://localhost:8080/api/v1/health >/dev/null && echo "- gateway: OK" || echo "- gateway: FAIL"
set -e

echo "Run websocket test: cd backend && python test_websocket_client.py"
