#!/bin/bash
# 检查硬编码中文字符串

CHANGED_FILES=$(git diff --name-only --diff-filter=ACM | grep "\.dart$" | grep -v ".g.dart" | grep -v ".freezed.dart" | grep -v "app_localizations" || true)

if [ -n "$CHANGED_FILES" ]; then
  HARDCODED=$(grep -l "Text(\['\"]\|[^\"]*[\u4e00-\u9fa5]" $CHANGED_FILES 2>/dev/null || true)

  if [ -n "$HARDCODED" ]; then
    echo "⚠️  发现硬编码中文字符串:"
    echo "$HARDCODED"
    echo ""
    echo "请使用 context.l10n.keyName 代替硬编码文本"
    exit 1
  fi
fi

echo "✅ 未发现硬编码字符串"
