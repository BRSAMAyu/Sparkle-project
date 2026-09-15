#!/bin/bash
# Sparkle - isar_flutter_libs Android SDK 兼容性修复脚本
# 用途: 修复 isar_flutter_libs 3.1.0+1 与 Android SDK 36 的兼容性问题
# 问题: isar 使用 compileSdkVersion 30，但依赖的 androidx.startup 需要 API 31+ (android:attr/lStar)

set -e

echo "🔧 Fixing isar_flutter_libs Android SDK compatibility..."
echo ""

# 检测操作系统
if [[ "$OSTYPE" == "darwin"* ]]; then
  SED_INPLACE="sed -i ''"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  SED_INPLACE="sed -i"
else
  echo "⚠️  Unsupported OS: $OSTYPE"
  exit 1
fi

# 查找 isar_flutter_libs 在 pub cache 中的位置
ISAR_PACKAGE=$(find "$HOME/.pub-cache/hosted" -type d -name "isar_flutter_libs-3.1.0+1" 2>/dev/null | head -1)

if [ -z "$ISAR_PACKAGE" ]; then
  echo "❌ isar_flutter_libs-3.1.0+1 not found in pub cache"
  echo "   Please run 'flutter pub get' first"
  exit 1
fi

ISAR_BUILD_FILE="$ISAR_PACKAGE/android/build.gradle"

if [ ! -f "$ISAR_BUILD_FILE" ]; then
  echo "❌ build.gradle not found: $ISAR_BUILD_FILE"
  exit 1
fi

# 检查是否已经修复
if grep -q "compileSdkVersion 36" "$ISAR_BUILD_FILE"; then
  echo "✅ isar_flutter_libs already fixed (compileSdkVersion 36)"
  echo "   Location: $ISAR_BUILD_FILE"
  exit 0
fi

# 创建备份
BACKUP_FILE="${ISAR_BUILD_FILE}.backup"
if [ ! -f "$BACKUP_FILE" ]; then
  cp "$ISAR_BUILD_FILE" "$BACKUP_FILE"
  echo "📦 Created backup: $BACKUP_FILE"
fi

# 执行修复
if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i '' 's/compileSdkVersion 30/compileSdkVersion 36/g' "$ISAR_BUILD_FILE"
else
  sed -i 's/compileSdkVersion 30/compileSdkVersion 36/g' "$ISAR_BUILD_FILE"
fi

# 验证修复
if grep -q "compileSdkVersion 36" "$ISAR_BUILD_FILE"; then
  echo "✅ Successfully fixed isar_flutter_libs"
  echo "   Changed: compileSdkVersion 30 → 36"
  echo "   Location: $ISAR_BUILD_FILE"
  echo ""
  echo "📝 Note: This fix will be reset if you run:"
  echo "   - flutter pub cache repair"
  echo "   - Delete .pub-cache directory"
  echo "   Just re-run this script after that."
else
  echo "❌ Fix failed - please check manually"
  exit 1
fi
