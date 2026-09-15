#!/bin/bash

###########################################
# Flutter Design System Migration Script
###########################################
#
# 此脚本自动化迁移从旧设计系统 (System A) 到新设计系统 (System B)
#
# 使用方式:
#   chmod +x scripts/migrate_design_system.sh
#   ./scripts/migrate_design_system.sh mobile
#
# 操作:
#   1. 替换所有导入语句
#   2. 用 DS.* 替换 AppDesignTokens.*
#   3. 检查剩余的旧系统引用

set -e

FLUTTER_APP_DIR="${1:-.}"

echo "🎨 开始 Flutter 设计系统迁移..."
echo "📂 目标目录: $FLUTTER_APP_DIR"
echo ""

# 验证目录
if [ ! -d "$FLUTTER_APP_DIR/lib" ]; then
  echo "❌ 错误: 找不到 $FLUTTER_APP_DIR/lib 目录"
  exit 1
fi

# 1. 替换导入 - System A theme.dart
echo "📦 替换导入 (System A: theme.dart)..."
find "$FLUTTER_APP_DIR/lib" -name "*.dart" -type f -exec sed -i '' \
  "s|import 'package:sparkle/app/theme.dart';|import 'package:sparkle/core/design/design_system.dart';|g" {} \;

# 2. 替换导入 - System C sparkle_theme.dart
echo "📦 替换导入 (System C: sparkle_theme.dart)..."
find "$FLUTTER_APP_DIR/lib" -name "*.dart" -type f -exec sed -i '' \
  "s|import 'package:sparkle/core/design/sparkle_theme.dart';|import 'package:sparkle/core/design/design_system.dart';|g" {} \;

# 3. 替换导入 - System A design_tokens.dart
echo "📦 替换导入 (System A: design_tokens.dart)..."
find "$FLUTTER_APP_DIR/lib" -name "*.dart" -type f -exec sed -i '' \
  "s|import 'package:sparkle/core/design/design_tokens.dart';|import 'package:sparkle/core/design/design_system.dart';|g" {} \;

# 4. 替换 AppDesignTokens -> DS
echo "🎯 替换 AppDesignTokens 为 DS..."
find "$FLUTTER_APP_DIR/lib" -name "*.dart" -type f -exec sed -i '' \
  's/AppDesignTokens\./DS\./g' {} \;

# 5. 检查并报告剩余的旧系统引用 (排除 core/design 目录)
echo ""
echo "🔍 扫描剩余的旧系统引用 (排除设计系统本身的文件)..."
OLD_REFS=$(find "$FLUTTER_APP_DIR/lib" -name "*.dart" -type f \
  ! -path "*/core/design/*" \
  ! -path "*/app/theme.dart" \
  -exec grep -l "AppThemes\|AppDesignTokens\|SparkleTheme" {} \; 2>/dev/null || true)

if [ -n "$OLD_REFS" ]; then
  echo "⚠️  找到以下应用文件中还有旧系统引用 (需要修复):"
  echo "$OLD_REFS" | while read file; do
    echo "  - $file"
  done
  echo ""
  echo "请查看这些文件并检查是否需要进一步修改"
  echo ""
else
  echo "✅ 没有在应用文件中找到旧系统引用"
fi

echo ""
echo "✨ 迁移完成！"
echo ""
echo "后续步骤:"
echo "1. cd $FLUTTER_APP_DIR && flutter clean"
echo "2. flutter pub get"
echo "3. flutter analyze"
echo "4. flutter run"
echo ""
echo "💡 提示: 如果遇到颜色不匹配的问题，请检查使用的是否是:"
echo "   - DS.brandPrimary (新的橙色 0xFFFF6B35)"
echo "   - context.sparkleColors (通过 BuildContext 访问)"
