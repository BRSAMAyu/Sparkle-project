#!/bin/bash
# 代码生成脚本 - 生成 JSON 序列化代码

set -e

echo "🔥 Sparkle - 代码生成脚本"
echo "===================================="
echo ""

cd "$(dirname "$0")/.."

echo "📦 获取依赖..."
flutter pub get
echo ""

echo "🔧 清理旧的生成文件..."
flutter packages pub run build_runner clean
echo ""

echo "⚙️  生成代码（JSON 序列化、Riverpod 等）..."
flutter packages pub run build_runner build --delete-conflicting-outputs
echo ""

echo "✅ 代码生成完成！"
echo ""
echo "生成的文件包括："
echo "  - *.g.dart (JSON 序列化代码)"
echo "  - *.freezed.dart (如果使用 freezed)"
echo ""
