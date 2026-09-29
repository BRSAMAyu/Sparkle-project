#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"

# Start infra (Postgres/Redis/MinIO) if needed
# FIX-557/FIX-563 数据面在位门：本仓容器名已单侧分化（sparkle_proj_db/redis/minio），
# sparkle-cosmos 仓保持 sparkle_db/redis/minio 旧名——两栈任一在位即可（引擎进程走
# localhost 端口，不逐容器名对接）；两者皆缺则提示按对照表启动，本脚本不自动重建。
# 对照表与 -p 纪律见 scripts/RESTACK_RUNBOOK.md。
if docker ps --format '{{.Names}}' | grep -qx sparkle_proj_db \
  && docker ps --format '{{.Names}}' | grep -qx sparkle_proj_redis \
  && docker ps --format '{{.Names}}' | grep -qx sparkle_proj_minio; then
  : # 本仓（sparkle-project）数据面在位，继续
elif docker ps --format '{{.Names}}' | grep -qx sparkle_db \
  && docker ps --format '{{.Names}}' | grep -qx sparkle_redis \
  && docker ps --format '{{.Names}}' | grep -qx sparkle_minio; then
  echo "NOTE: 数据面为 sparkle-cosmos 仓栈（sparkle_db/redis/minio，FIX-563 前共享形态），本脚本不动它。" >&2
else
  echo "⚠️  数据面容器未全部运行（本仓=sparkle_proj_db/redis/minio；cosmos 仓=sparkle_db/redis/minio）。" >&2
  echo "    按仓库对应启动（对照表见 scripts/RESTACK_RUNBOOK.md）；本脚本不自动重建。" >&2
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
