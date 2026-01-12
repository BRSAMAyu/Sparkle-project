#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="mobile/lib/presentation"
HAS_RG=0
TARGET_FILES=()
DIFF_FAILED=0

if command -v rg >/dev/null 2>&1; then
  HAS_RG=1
fi

if [ ! -d "$TARGET_DIR" ]; then
  echo "UI lint target not found: $TARGET_DIR"
  exit 0
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  collect_all_files() {
    local files
    if [ "$HAS_RG" -eq 1 ]; then
      files=$(rg --files -g "*.dart" "$TARGET_DIR" || true)
    else
      files=$(find "$TARGET_DIR" -type f -name "*.dart" || true)
    fi
    if [ -n "$files" ]; then
      while IFS= read -r file; do
        if [ -f "$file" ]; then
          TARGET_FILES+=("$file")
        fi
      done <<< "$files"
    fi
  }

  if [ -n "${GITHUB_BASE_REF:-}" ]; then
    base_ref="origin/${GITHUB_BASE_REF}"
    if git rev-parse "$base_ref" >/dev/null 2>&1; then
      diff_files=$(git diff --name-only --diff-filter=ACMRTUXB "$base_ref"...HEAD -- "$TARGET_DIR" || true)
      [ -z "$diff_files" ] && DIFF_FAILED=0
    else
      DIFF_FAILED=1
    fi
  else
    diff_files=$(git diff --name-only --diff-filter=ACMRTUXB -- "$TARGET_DIR" || true)
    if [ -z "$diff_files" ]; then
      diff_files=$(git diff --cached --name-only --diff-filter=ACMRTUXB -- "$TARGET_DIR" || true)
    fi
  fi

  if [ "$DIFF_FAILED" -eq 1 ]; then
    collect_all_files
  elif [ -n "${diff_files:-}" ]; then
    while IFS= read -r file; do
      if [ -f "$file" ]; then
        TARGET_FILES+=("$file")
      fi
    done <<< "$diff_files"
  elif git status --porcelain -- "$TARGET_DIR" | grep -q .; then
    collect_all_files
  fi
fi

if [ "${#TARGET_FILES[@]}" -eq 0 ]; then
  echo "UI lint passed (no presentation changes)."
  exit 0
fi

fail=0

check() {
  local label="$1"
  local pattern="$2"
  local exclude="${3:-}"
  local output

  if [ "$HAS_RG" -eq 1 ]; then
    output=$(rg -n --color=never "$pattern" "${TARGET_FILES[@]}" || true)
  else
    output=$(grep -InE "$pattern" "${TARGET_FILES[@]}" || true)
  fi
  if [ -n "$exclude" ] && [ -n "$output" ]; then
    if [ "$HAS_RG" -eq 1 ]; then
      output=$(printf '%s\n' "$output" | rg --color=never -v "$exclude" || true)
    else
      output=$(printf '%s\n' "$output" | grep -vE "$exclude" || true)
    fi
  fi

  if [ -n "$output" ]; then
    echo "$label"
    echo "$output"
    echo
    fail=1
  fi
}

check "[Color literals] Color(0x...)" "Color\\(0x[0-9A-Fa-f]+\\)"
check "[Material colors] Colors.* (except transparent)" "Colors\\.[A-Za-z_]+" "Colors\\.transparent"
check "[Font size] fontSize:" "fontSize\\s*:"
check "[EdgeInsets] all/symmetric/only" "EdgeInsets\\.(all|symmetric|only)\\("
check "[BorderRadius] circular" "BorderRadius\\.circular\\("
check "[Brightness access] Theme.of(context).brightness" "Theme\\.of\\(context\\)\\.brightness"
check "[Brightness constants] Brightness.dark" "Brightness\\.dark"
check "[Dark mode flags] isDark" "isDark"

if [ "$fail" -ne 0 ]; then
  echo "UI lint failed. Please replace hardcoded values with design tokens."
  exit 1
fi

echo "UI lint passed."
