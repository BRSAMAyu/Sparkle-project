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
RESTART_STACK_ON_BOOT="${SGW_RESTART_STACK_ON_BOOT:-auto}"
RUNTIME_ENV_FILE="${SGW_RUNTIME_ENV_FILE:-$HOME/.sparkle_sgw_runtime.env}"

mkdir -p "$STATE_DIR"
touch "$LOG_PATH"
trap 'code=$?; echo "[sgw] runner failed at line $LINENO (exit $code)" | tee -a "$LOG_PATH"; exit $code' ERR

if [[ -f "$RUNTIME_ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$RUNTIME_ENV_FILE"
fi

export PYTHONPATH="$ROOT_DIR/backend${PYTHONPATH:+:$PYTHONPATH}"
export SPARKLE_MEMORY_INFERRED_WRITE_ENABLED="${SPARKLE_MEMORY_INFERRED_WRITE_ENABLED:-true}"
export SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED="${SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED:-false}"
export DEBUG="${DEBUG:-false}"
export DB_ECHO="${DB_ECHO:-false}"
export DB_POOL_SIZE="${DB_POOL_SIZE:-30}"
export DB_MAX_OVERFLOW="${DB_MAX_OVERFLOW:-0}"
export POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export POSTGRES_USER="${POSTGRES_USER:-brsama}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-change-me}"
export POSTGRES_DB="${POSTGRES_DB:-sparkle}"
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}?sslmode=disable}"
export REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export REDIS_URL="${REDIS_URL:-redis://${REDIS_HOST}:${REDIS_PORT}/0}"
export LOCAL_STACK_AGE_REQUIRED="${LOCAL_STACK_AGE_REQUIRED:-false}"
export AGE_INIT_RETRIES="${AGE_INIT_RETRIES:-8}"
export AGE_INIT_SLEEP_SECONDS="${AGE_INIT_SLEEP_SECONDS:-3}"
export SGW_WALL_CLOCK_HOURS="${SGW_WALL_CLOCK_HOURS:-18}"
if [[ -n "${SGW_API_KEY:-}" ]]; then
  export SGW_LLM_PROVIDER="${SGW_LLM_PROVIDER:-api}"
else
  export SGW_LLM_PROVIDER="${SGW_LLM_PROVIDER:-claude_cli}"
fi
export SGW_API_BASE_URL="${SGW_API_BASE_URL:-https://open.bigmodel.cn/api/coding/paas/v4}"
export SGW_API_MODEL="${SGW_API_MODEL:-glm-4.7}"
export SGW_API_TEMPERATURE="${SGW_API_TEMPERATURE:-0.3}"
export SGW_API_TIMEOUT_SECONDS="${SGW_API_TIMEOUT_SECONDS:-45}"
export SGW_API_CLEAR_THINKING="${SGW_API_CLEAR_THINKING:-true}"
export SGW_CLAUDE_MIN_PARALLEL="${SGW_CLAUDE_MIN_PARALLEL:-1}"
export SGW_CLAUDE_INITIAL_PARALLEL="${SGW_CLAUDE_INITIAL_PARALLEL:-2}"
export SGW_CLAUDE_MAX_PARALLEL="${SGW_CLAUDE_MAX_PARALLEL:-8}"
export SGW_CLAUDE_MIN_INTERVAL_SECONDS="${SGW_CLAUDE_MIN_INTERVAL_SECONDS:-10}"
export SGW_CLAUDE_TIMEOUT_SECONDS="${SGW_CLAUDE_TIMEOUT_SECONDS:-45}"
if [[ "${SGW_LLM_PROVIDER}" == "api" ]]; then
  export SGW_CLAUDE_RATE_LIMIT_BACKOFF_SECONDS="${SGW_CLAUDE_RATE_LIMIT_BACKOFF_SECONDS:-120}"
else
  export SGW_CLAUDE_RATE_LIMIT_BACKOFF_SECONDS="${SGW_CLAUDE_RATE_LIMIT_BACKOFF_SECONDS:-300}"
fi
export SGW_CLAUDE_SCALE_UP_COOLDOWN_SECONDS="${SGW_CLAUDE_SCALE_UP_COOLDOWN_SECONDS:-600}"
export SGW_CLAUDE_CEILING_PROBE_COOLDOWN_SECONDS="${SGW_CLAUDE_CEILING_PROBE_COOLDOWN_SECONDS:-1800}"
export SGW_CLAUDE_EFFORT="${SGW_CLAUDE_EFFORT:-low}"
export SGW_CLAUDE_MODEL="${SGW_CLAUDE_MODEL:-haiku}"
export SGW_AUDIT_SAMPLE_RATE="${SGW_AUDIT_SAMPLE_RATE:-0.12}"
export SGW_AUDIT_BACKLOG_SOFT_CAP="${SGW_AUDIT_BACKLOG_SOFT_CAP:-40}"
export SGW_AUDIT_START_AFTER_TURNS="${SGW_AUDIT_START_AFTER_TURNS:-240}"
export SGW_AUDIT_PAUSE_BACKLOG_THRESHOLD="${SGW_AUDIT_PAUSE_BACKLOG_THRESHOLD:-120}"
export SGW_AUDIT_MAX_PARALLEL="${SGW_AUDIT_MAX_PARALLEL:-1}"
export SGW_SESSION_TURN_SLICE="${SGW_SESSION_TURN_SLICE:-1}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "SGW python runtime not found: $PYTHON_BIN" | tee -a "$LOG_PATH"
  exit 1
fi

if [[ "$SGW_LLM_PROVIDER" == "claude_cli" ]]; then
  if ! command -v claude >/dev/null 2>&1; then
    echo "claude CLI not found in PATH" | tee -a "$LOG_PATH"
    exit 1
  fi

  if ! claude auth status >/dev/null 2>&1; then
    echo "claude CLI is not authenticated" | tee -a "$LOG_PATH"
    exit 1
  fi
elif [[ -z "${SGW_API_KEY:-}" ]]; then
  echo "SGW API provider selected but SGW_API_KEY is missing" | tee -a "$LOG_PATH"
  exit 1
fi

SHOULD_RESTART_STACK="false"
if [[ "$RESTART_STACK_ON_BOOT" == "true" ]]; then
  SHOULD_RESTART_STACK="true"
elif [[ "$RESTART_STACK_ON_BOOT" == "auto" && ! -f "$CHECKPOINT_PATH" ]]; then
  SHOULD_RESTART_STACK="true"
fi

if [[ "$SHOULD_RESTART_STACK" == "true" ]]; then
  echo "[sgw] restarting local stack with SGW env" | tee -a "$LOG_PATH"
  "$ROOT_DIR/scripts/dev_local_stack.sh" down >>"$LOG_PATH" 2>&1 || true
  "$ROOT_DIR/scripts/dev_local_stack.sh" up >>"$LOG_PATH" 2>&1
elif ! curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1 || ! curl -fsS http://127.0.0.1:8080/api/v1/health >/dev/null 2>&1; then
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
    --wall-clock-hours "$SGW_WALL_CLOCK_HOURS"
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
