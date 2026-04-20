#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
STATE_DIR="${SGW_STATE_DIR:-$ROOT_DIR/.sgw_state}"
REPORT_DATE="$(date +%Y-%m-%d)"
REPORT_PATH="${SGW_REPORT_PATH:-$ROOT_DIR/docs/product/SPARKLE_AURORA_STAGE16_SGW_REPORT_${REPORT_DATE}.md}"
CHECKPOINT_PATH="${SGW_CHECKPOINT_PATH:-$STATE_DIR/sgw_checkpoint.json}"
LOG_PATH="${SGW_LOG_PATH:-$STATE_DIR/sgw_runner.log}"
MAX_RESTARTS="${SGW_MAX_RESTARTS:-12}"
PYTHON_BIN="${SGW_PYTHON_BIN:-$ROOT_DIR/backend/.venv/bin/python}"

mkdir -p "$STATE_DIR"
touch "$LOG_PATH"
trap 'code=$?; echo "[sgw] runner failed at line $LINENO (exit $code)" | tee -a "$LOG_PATH"; exit $code' ERR

export PYTHONPATH="$ROOT_DIR/backend${PYTHONPATH:+:$PYTHONPATH}"
export SPARKLE_MEMORY_INFERRED_WRITE_ENABLED="${SPARKLE_MEMORY_INFERRED_WRITE_ENABLED:-true}"
export SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED="${SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED:-false}"
export DEBUG="${DEBUG:-false}"
export DB_ECHO="${DB_ECHO:-false}"
export DB_POOL_SIZE="${DB_POOL_SIZE:-30}"
export DB_MAX_OVERFLOW="${DB_MAX_OVERFLOW:-0}"
export SGW_CLAUDE_MAX_PARALLEL="${SGW_CLAUDE_MAX_PARALLEL:-1}"
export SGW_CLAUDE_MIN_INTERVAL_SECONDS="${SGW_CLAUDE_MIN_INTERVAL_SECONDS:-15}"
export SGW_CLAUDE_TIMEOUT_SECONDS="${SGW_CLAUDE_TIMEOUT_SECONDS:-45}"
export SGW_CLAUDE_RATE_LIMIT_BACKOFF_SECONDS="${SGW_CLAUDE_RATE_LIMIT_BACKOFF_SECONDS:-300}"
export SGW_CLAUDE_EFFORT="${SGW_CLAUDE_EFFORT:-low}"
export SGW_CLAUDE_MODEL="${SGW_CLAUDE_MODEL:-haiku}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

if ! command -v claude >/dev/null 2>&1; then
  echo "claude CLI not found in PATH" | tee -a "$LOG_PATH"
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "SGW python runtime not found: $PYTHON_BIN" | tee -a "$LOG_PATH"
  exit 1
fi

if ! claude auth status >/dev/null 2>&1; then
  echo "claude CLI is not authenticated" | tee -a "$LOG_PATH"
  exit 1
fi

if ! curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1 || ! curl -fsS http://127.0.0.1:8080/api/v1/health >/dev/null 2>&1; then
  echo "[sgw] local stack not healthy, starting dev stack" | tee -a "$LOG_PATH"
  "$ROOT_DIR/scripts/dev_local_stack.sh" up >>"$LOG_PATH" 2>&1
fi

echo "[sgw] applying backend migrations" | tee -a "$LOG_PATH"
(
  cd "$ROOT_DIR/backend"
  ./.venv/bin/alembic upgrade heads
) >>"$LOG_PATH" 2>&1

restart_count=0
while true; do
  args=(
    "$ROOT_DIR/scripts/sgw/sgw_orchestrator.py"
    --persona-library "$ROOT_DIR/scripts/sgw/persona_library.json"
    --adversarial-playbook "$ROOT_DIR/scripts/sgw/adversarial_playbook.json"
    --report-path "$REPORT_PATH"
    --checkpoint-path "$CHECKPOINT_PATH"
  )

  if [[ -f "$CHECKPOINT_PATH" ]]; then
    args+=(--resume)
  fi

  echo "[sgw] launch attempt $((restart_count + 1))" | tee -a "$LOG_PATH"
  if "$PYTHON_BIN" "${args[@]}" "$@" 2>&1 | tee -a "$LOG_PATH"; then
    echo "[sgw] completed successfully" | tee -a "$LOG_PATH"
    break
  fi

  restart_count=$((restart_count + 1))
  if [[ "$restart_count" -ge "$MAX_RESTARTS" ]]; then
    echo "[sgw] reached max restart count ($MAX_RESTARTS)" | tee -a "$LOG_PATH"
    exit 1
  fi

  echo "[sgw] restart after 30s" | tee -a "$LOG_PATH"
  sleep 30
done
