#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/backend/logs/local"
PID_DIR="$ROOT_DIR/backend/logs/local/pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

start_infra() {
  (cd "$ROOT_DIR" && docker compose up -d sparkle_db redis minio)
}

service_port() {
  case "$1" in
    api) echo "8000" ;;
    gateway) echo "8080" ;;
    grpc) echo "50051" ;;
    *) return 1 ;;
  esac
}

wait_for_http() {
  local url="$1"
  local name="$2"
  local attempts="${3:-30}"

  for ((i=1; i<=attempts; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name is ready"
      return 0
    fi
    sleep 2
  done

  echo "$name failed readiness check: $url"
  return 1
}

wait_for_container_health() {
  local container="$1"
  local attempts="${2:-30}"
  local status

  for ((i=1; i<=attempts; i++)); do
    status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container" 2>/dev/null || true)"
    if [[ "$status" == "healthy" || "$status" == "running" ]]; then
      echo "$container is $status"
      return 0
    fi
    sleep 2
  done

  echo "$container did not become ready"
  return 1
}

start_service() {
  local name="$1"
  local cmd="$2"
  local log_file="$LOG_DIR/${name}.log"
  local pid_file="$PID_DIR/${name}.pid"

  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "$name already running (pid $(cat "$pid_file"))"
    return
  fi

  local pid
  pid="$(
    ROOT_DIR="$ROOT_DIR" LOG_FILE="$log_file" START_CMD="$cmd" python3 - <<'PY'
import os
import subprocess

root = os.environ["ROOT_DIR"]
log_file = os.environ["LOG_FILE"]
cmd = os.environ["START_CMD"]

with open(log_file, "ab", buffering=0) as log:
    proc = subprocess.Popen(
        ["/bin/bash", "-lc", f"cd {subprocess.list2cmdline([root])} && {cmd}"],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    print(proc.pid)
PY
  )"
  echo "$pid" >"$pid_file"
  echo "started $name (pid $pid)"
}

stop_service() {
  local name="$1"
  local pid_file="$PID_DIR/${name}.pid"
  local port

  port="$(service_port "$name" 2>/dev/null || true)"

  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    kill "$(cat "$pid_file")"
    rm -f "$pid_file"
    echo "stopped $name"
  else
    echo "$name pid not running"
  fi

  if [[ -n "$port" ]]; then
    local port_pids
    port_pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -n "$port_pids" ]]; then
      echo "$port_pids" | xargs kill 2>/dev/null || true
      echo "stopped $name listener(s) on :$port"
    fi
  fi

  rm -f "$pid_file"
}

status_service() {
  local name="$1"
  local pid_file="$PID_DIR/${name}.pid"
  local port

  port="$(service_port "$name" 2>/dev/null || true)"

  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "$name: running (pid $(cat "$pid_file"))"
    return
  fi

  if [[ -n "$port" ]] && lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "$name: running (listener on :$port)"
    return
  fi

  echo "$name: stopped"
}

smoke() {
  curl -fsS http://127.0.0.1:8000/health >/dev/null
  curl -fsS http://127.0.0.1:8080/api/v1/health >/dev/null
  curl -fsS http://127.0.0.1:8080/api/v1/health/cqrs >/dev/null
  echo "smoke: ok"
}

case "${1:-}" in
  up)
    start_infra
    wait_for_container_health "sparkle_db"
    wait_for_container_health "sparkle_redis"
    wait_for_container_health "sparkle_minio"
    start_service "grpc" "export PATH='$ROOT_DIR/backend/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin'; export PYTHONPATH='$ROOT_DIR/backend'; cd '$ROOT_DIR/backend' && exec /bin/bash scripts/run_grpc_with_env.sh"
    start_service "api" "export PATH='$ROOT_DIR/backend/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin'; cd '$ROOT_DIR/backend' && exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env"
    wait_for_http "http://127.0.0.1:8000/health" "api"
    start_service "gateway" "export PATH='/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin'; cd '$ROOT_DIR/backend/gateway' && go build -o bin/gateway ./cmd/server && exec ./bin/gateway"
    wait_for_http "http://127.0.0.1:8080/api/v1/health" "gateway"
    start_service "summarization_worker" "export PATH='$ROOT_DIR/backend/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin'; export PYTHONPATH='$ROOT_DIR/backend'; cd '$ROOT_DIR/backend' && exec python scripts/start_summarization_worker.py --worker-id local-summary"
    start_service "billing_worker" "export PATH='$ROOT_DIR/backend/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin'; export PYTHONPATH='$ROOT_DIR/backend'; cd '$ROOT_DIR/backend' && exec python scripts/start_billing_worker.py"
    ;;
  down)
    stop_service "billing_worker"
    stop_service "summarization_worker"
    stop_service "gateway"
    stop_service "api"
    stop_service "grpc"
    (cd "$ROOT_DIR" && docker compose stop sparkle_db redis minio >/dev/null)
    ;;
  status)
    (cd "$ROOT_DIR" && docker compose ps)
    status_service "summarization_worker"
    status_service "billing_worker"
    status_service "grpc"
    status_service "api"
    status_service "gateway"
    ;;
  smoke)
    smoke
    ;;
  *)
    echo "usage: scripts/dev_local_stack.sh {up|down|status|smoke}"
    exit 1
    ;;
esac
