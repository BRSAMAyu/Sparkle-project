#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

find_python_with_grpc_tools() {
  if python3 - <<'PY' >/dev/null 2>&1
import grpc_tools  # noqa: F401
PY
  then
    echo "python3"
    return 0
  fi

  if [[ -x "${REPO_ROOT}/backend/.venv/bin/python" ]] && "${REPO_ROOT}/backend/.venv/bin/python" - <<'PY' >/dev/null 2>&1
import grpc_tools  # noqa: F401
PY
  then
    echo "${REPO_ROOT}/backend/.venv/bin/python"
    return 0
  fi

  return 1
}

PYTHON_BIN="$(find_python_with_grpc_tools || true)"
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "ERROR: Could not find a Python interpreter with grpc_tools installed." >&2
  exit 1
fi

cd "${REPO_ROOT}"

mkdir -p backend/app/gen

"${PYTHON_BIN}" -m grpc_tools.protoc \
  --proto_path=proto \
  --proto_path=third_party \
  --python_out=backend/app/gen \
  --grpc_python_out=backend/app/gen \
  --pyi_out=backend/app/gen \
  proto/agent_service.proto \
  proto/community_service.proto \
  proto/error_book.proto \
  proto/galaxy_service.proto \
  proto/sparkle/inference/v1/inference.proto \
  proto/sparkle/rag/v1/evidence.proto \
  proto/sparkle/signals/v1/signals.proto \
  proto/stt_service.proto

"${PYTHON_BIN}" -m grpc_tools.protoc \
  --proto_path=proto \
  --proto_path=third_party \
  --python_out=backend/app/gen \
  --pyi_out=backend/app/gen \
  proto/websocket.proto
