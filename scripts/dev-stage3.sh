#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"

# Start infra (Postgres/Redis/MinIO) if needed
# FIX-557 铁律：本地共享数据面（sparkle_db/redis/minio）属主是 sparkle-cosmos 仓 compose。
# 本仓 compose 与其同名容器冲突，直接 `make dev-up` 会踩容器名/数据卷陷阱——
# 仅在共享三容器全部健康时继续，否则提示按 cosmos 仓启动，不自动重建。
if docker ps --format '{{.Names}}' | grep -qx sparkle_db \
  && docker ps --format '{{.Names}}' | grep -qx sparkle_redis \
  && docker ps --format '{{.Names}}' | grep -qx sparkle_minio; then
  : # 共享数据面在位，继续
else
  echo "⚠️  共享数据面容器（sparkle_db/redis/minio）未全部运行。" >&2
  echo "    数据面属主=sparkle-cosmos 仓 compose（FIX-557），请在该仓启动后再跑本脚本。" >&2
  exit 1
fi

# Start Python gRPC server
# FIX-571：裸 `python` 在无 venv PATH 下不存在；走仓内 venv 感知启动脚本（make grpc-server 同路径）
if ! lsof -nP -iTCP:50051 -sTCP:LISTEN >/dev/null 2>&1; then
  (cd "$ROOT_DIR/backend" && nohup bash scripts/run_grpc_with_env.sh > "$LOG_DIR/grpc_server.log" 2>&1 &)
fi

# Start FastAPI backend (port 8000)
if ! lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  (cd "$ROOT_DIR/backend" && nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/backend_api.log" 2>&1 &)
fi

# Start Gateway (port 8080)
# FIX-571：`go run cmd/server/main.go` 只编译单文件，多文件包下 undefined 符号——
# 改为整包构建后运行（scripts/dev_local_stack.sh 同路径）
if ! lsof -nP -iTCP:8080 -sTCP:LISTEN >/dev/null 2>&1; then
  (cd "$ROOT_DIR/backend/gateway" && nohup bash -lc 'set -a; source .env; set +a; go build -o bin/gateway ./cmd/server && exec ./bin/gateway' > "$LOG_DIR/gateway.log" 2>&1 &)
fi

sleep 3

echo "Stage 3 services started. Logs in $LOG_DIR"

echo "Health checks:"
set +e
curl -fsS http://localhost:8000/health >/dev/null && echo "- backend: OK" || echo "- backend: FAIL"
curl -fsS http://localhost:8080/api/v1/health >/dev/null && echo "- gateway: OK" || echo "- gateway: FAIL"
set -e

echo "Run websocket test: cd backend && python test_websocket_client.py"
