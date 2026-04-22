#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/backend/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  if command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3.11)"
  else
    PYTHON_BIN="python3"
  fi
fi
export SECRET_KEY="${SECRET_KEY:-rule-guard-secret-0123456789abcdef}"
export JWT_SECRET="${JWT_SECRET:-rule-guard-jwt-0123456789abcdef}"

MANIFEST_PATH="${REPO_ROOT}/scripts/rule_guard_manifest.tsv"
RULE_FILTER=""
JOBS=1
LIST_ONLY=0

usage() {
  cat <<'EOF'
Usage: scripts/run_all_rule_guards.sh [--rule AB] [--jobs 4] [--manifest path] [--list]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rule)
      RULE_FILTER="$(printf '%s' "${2:-}" | tr '[:lower:]' '[:upper:]')"
      shift 2
      ;;
    --jobs)
      JOBS="${2:-1}"
      shift 2
      ;;
    --manifest)
      MANIFEST_PATH="${2:-}"
      shift 2
      ;;
    --list)
      LIST_ONLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "${MANIFEST_PATH}" ]]; then
  echo "manifest not found: ${MANIFEST_PATH}" >&2
  exit 1
fi

RULES=()
COMMANDS=()
while IFS=$'\t' read -r rule command; do
  [[ -z "${rule}" ]] && continue
  [[ "${rule}" =~ ^# ]] && continue
  if [[ -n "${RULE_FILTER}" && "${rule}" != "${RULE_FILTER}" ]]; then
    continue
  fi
  RULES+=("${rule}")
  COMMANDS+=("${command}")
done < "${MANIFEST_PATH}"

if [[ ${#RULES[@]} -eq 0 ]]; then
  echo "no rules selected" >&2
  exit 1
fi

if [[ "${LIST_ONLY}" -eq 1 ]]; then
  printf '%s\n' "${RULES[@]}"
  exit 0
fi

run_one() {
  local rule="$1"
  local command="$2"
  local output_file="$3"
  local status_file="$4"

  {
    echo "[Rule ${rule}] START"
    if env REPO_ROOT="${REPO_ROOT}" PYTHON_BIN="${PYTHON_BIN}" bash -lc "cd \"${REPO_ROOT}\" && ${command}"; then
      echo "[Rule ${rule}] DONE"
      printf '0' > "${status_file}"
    else
      local code=$?
      echo "[Rule ${rule}] DONE (${code})"
      printf '%s' "${code}" > "${status_file}"
    fi
  } > "${output_file}" 2>&1
}

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

if [[ "${JOBS}" -gt 1 && "${#RULES[@]}" -gt 1 ]]; then
  RUNNING=()
  for idx in "${!RULES[@]}"; do
    run_one "${RULES[idx]}" "${COMMANDS[idx]}" "${TMP_DIR}/${RULES[idx]}.log" "${TMP_DIR}/${RULES[idx]}.status" &
    RUNNING+=("$!")
    if [[ "${#RUNNING[@]}" -ge "${JOBS}" ]]; then
      wait "${RUNNING[0]}"
      RUNNING=("${RUNNING[@]:1}")
    fi
  done
  for pid in "${RUNNING[@]}"; do
    wait "${pid}"
  done
else
  for idx in "${!RULES[@]}"; do
    run_one "${RULES[idx]}" "${COMMANDS[idx]}" "${TMP_DIR}/${RULES[idx]}.log" "${TMP_DIR}/${RULES[idx]}.status"
  done
fi

FAILURES=()
for idx in "${!RULES[@]}"; do
  rule="${RULES[idx]}"
  cat "${TMP_DIR}/${rule}.log"
  if [[ "$(cat "${TMP_DIR}/${rule}.status")" != "0" ]]; then
    FAILURES+=("${rule}")
  fi
done

if [[ ${#FAILURES[@]} -gt 0 ]]; then
  echo "rule guards failed: ${FAILURES[*]}" >&2
  exit 1
fi

echo "all rule guards passed (${#RULES[@]} rules)"
