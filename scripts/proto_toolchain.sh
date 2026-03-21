#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

IMAGE_NAME="${PROTO_TOOLCHAIN_IMAGE:-sparkle/proto-toolchain:latest}"
USE_DOCKER="${PROTO_USE_DOCKER:-1}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <command>"
  exit 1
fi

run_in_host() {
  cd "${REPO_ROOT}"
  export PATH="$(go env GOPATH 2>/dev/null)/bin:${HOME}/.pub-cache/bin:${HOME}/.local/bin:${PATH}"
  eval "$*"
}

run_in_docker() {
  local cmd="$1"
  if ! docker info >/dev/null 2>&1; then
    echo "WARN: docker daemon is unavailable, falling back to host toolchain (PROTO_USE_DOCKER=0)." >&2
    USE_DOCKER=0
    return
  fi
  if ! docker run --rm \
    -v "${REPO_ROOT}:/workspace" \
    -w /workspace \
    "${IMAGE_NAME}" \
    "export PATH=\"/root/.pub-cache/bin:\$PATH\" && ${cmd}"; then
    echo "WARN: dockerized proto toolchain failed, falling back to host toolchain (PROTO_USE_DOCKER=0)." >&2
    USE_DOCKER=0
    return
  fi
}

case "$1" in
  gen)
    CMD='buf generate --template buf.gen.yaml && buf generate --template buf.gen.dart.yaml && bash scripts/generate_python_protos.sh && python3 scripts/sync_buf_python_stubs.py'
    LEGACY_CMD='make proto-gen-legacy'
    ;;
  lint)
    CMD='buf lint'
    ;;
  breaking)
    AGAINST="${2:-.git#branch=main}"
    CMD="buf breaking --against '${AGAINST}'"
    ;;
  check-generated)
    CMD='tmpdir=$(mktemp -d) && trap "rm -rf \"$tmpdir\"" EXIT && for path in backend/gateway/gen backend/app/gen mobile/lib/gen; do if [ -e "$path" ]; then mkdir -p "$tmpdir/$(dirname "$path")" && cp -R "$path" "$tmpdir/$path"; fi; done && buf generate --template buf.gen.yaml && buf generate --template buf.gen.dart.yaml && bash scripts/generate_python_protos.sh && python3 scripts/sync_buf_python_stubs.py && for path in backend/gateway/gen backend/app/gen mobile/lib/gen; do if [ -e "$path" ] || [ -e "$tmpdir/$path" ]; then diff -ruN "$tmpdir/$path" "$path"; fi; done'
    ;;
  *)
    echo "Unknown subcommand: $1"
    exit 1
    ;;
esac

if [[ "${USE_DOCKER}" == "1" ]]; then
  run_in_docker "${CMD}"
  if [[ "${USE_DOCKER}" == "0" ]]; then
    if [[ "$1" == "gen" ]] && ! run_in_host "${CMD}"; then
      echo "WARN: host buf generation failed, using legacy protoc pipeline." >&2
      run_in_host "${LEGACY_CMD}"
    fi
    if [[ "$1" != "gen" ]]; then
      run_in_host "${CMD}"
    fi
  fi
else
  if [[ "$1" == "gen" ]] && ! run_in_host "${CMD}"; then
    echo "WARN: host buf generation failed, using legacy protoc pipeline." >&2
    run_in_host "${LEGACY_CMD}"
  fi
  if [[ "$1" != "gen" ]]; then
    run_in_host "${CMD}"
  fi
fi
