#!/usr/bin/env bash
# MyPy 棘轮门（CI）：存量类型债只降不升。
# 口径：cd backend && mypy app（吃 backend/pyproject.toml 含 warn_return_any，与基线口径合一——
# 根目录口径恒少 269 条 no-any-return，见 WT289-MYPY-BURN1 报告）；基线在 quality/mypy_baseline.txt。
set -euo pipefail
COUNT="$(cd backend && mypy app --ignore-missing-imports --no-error-summary 2>/dev/null | grep -c 'error:' || true)"
BASELINE="$(cat quality/mypy_baseline.txt)"
echo "mypy errors: ${COUNT} / baseline: ${BASELINE}"
if [ "${COUNT}" -gt "${BASELINE}" ]; then
  echo "::error::mypy errors ${COUNT} > baseline ${BASELINE} — fix new type errors or (after cleanup) lower the baseline"
  exit 1
fi
if [ "${COUNT}" -lt "${BASELINE}" ]; then
  echo "improvement — lower quality/mypy_baseline.txt to ${COUNT} in this PR"
fi
