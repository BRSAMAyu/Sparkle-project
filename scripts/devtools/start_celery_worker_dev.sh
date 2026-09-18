#!/usr/bin/env bash
# Dev 环境本机 Celery worker 启动脚本（MR-3 配套 runbook）。
#
# 背景：文档上传链 confirm-upload 后 `process_stored_file.delay` 需要 worker
# 消费；本机 dev 栈此前从未运行 worker，上传链在第 2 步即无人消费（409）。
#
# 用法：
#   bash scripts/devtools/start_celery_worker_dev.sh          # nohup 后台启动
#   bash scripts/devtools/start_celery_worker_dev.sh stop     # 停止
#   bash scripts/devtools/start_celery_worker_dev.sh status   # 查看存活
#
# 备选（docker 方式）：make celery-up（需要 sparkle_backend 镜像）。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
LOG_FILE="${SPARKLE_CELERY_LOG:-/tmp/sparkle_celery_worker.log}"
PID_FILE="${SPARKLE_CELERY_PID:-/tmp/sparkle_celery_worker.pid}"
QUEUES="${SPARKLE_CELERY_QUEUES:-high_priority,default,low_priority,glm_batch}"
CONCURRENCY="${SPARKLE_CELERY_CONCURRENCY:-2}"
PYTHON_BIN="${SPARKLE_PYTHON:-}"

if [[ -z "${PYTHON_BIN}" ]]; then
  for candidate in backend/.venv/bin/python /opt/homebrew/bin/python3.11 python3.11 python3; do
    if [[ -x "${ROOT_DIR}/${candidate}" || "${candidate}" == python3* ]] && command -v "${candidate}" >/dev/null 2>&1; then
      PYTHON_BIN="${candidate}"
      break
    fi
  done
fi

worker_pid() {
  [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null && cat "${PID_FILE}" || true
}

case "${1:-start}" in
  start)
    if [[ -n "$(worker_pid)" ]]; then
      echo "✅ Celery worker already running (pid $(cat "${PID_FILE}"))"
      exit 0
    fi
    cd "${BACKEND_DIR}"
    echo "🚀 Starting Celery worker (queues=${QUEUES}, concurrency=${CONCURRENCY})..."
    nohup "${PYTHON_BIN}" -m celery -A app.core.celery_app worker \
      -l info -Q "${QUEUES}" --concurrency="${CONCURRENCY}" \
      >> "${LOG_FILE}" 2>&1 &
    echo $! > "${PID_FILE}"
    sleep 3
    if kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
      echo "✅ Worker started (pid $(cat "${PID_FILE}"), log ${LOG_FILE})"
      echo "   Verify: grep -m1 'ready' ${LOG_FILE}"
    else
      echo "❌ Worker failed to start; last log lines:"
      tail -20 "${LOG_FILE}" || true
      exit 1
    fi
    ;;
  stop)
    pid="$(worker_pid)"
    if [[ -n "${pid}" ]]; then
      kill "${pid}" && echo "🛑 Stopped worker (pid ${pid})"
    else
      echo "No running worker found"
    fi
    ;;
  status)
    pid="$(worker_pid)"
    if [[ -n "${pid}" ]]; then
      echo "✅ Worker alive (pid ${pid})"
    else
      echo "⛔ Worker not running; start with: $0"
      exit 1
    fi
    ;;
  *)
    echo "Usage: $0 [start|stop|status]"
    exit 2
    ;;
esac
