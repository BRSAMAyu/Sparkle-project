#!/bin/bash
# Sparkle Demo 版本安装脚本
# 用途: 一键设置 Demo 开发环境

set -e

echo "🎯 Sparkle Demo Environment Setup"
echo "=================================="
echo ""

# 检查 Flutter 是否安装
if ! command -v flutter &> /dev/null; then
  echo "❌ Flutter is not installed"
  echo "   Please install Flutter first: https://flutter.dev/docs/get-started/install"
  exit 1
fi

echo "✅ Flutter detected: $(flutter --version | head -1)"
echo ""

# 进入项目目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 1. 安装依赖
echo "📦 Installing dependencies..."
flutter pub get
echo ""

# 2. 修复 isar SDK 兼容性
echo "🔧 Fixing isar_flutter_libs compatibility..."
bash fix_isar_sdk.sh
echo ""

# 3. 生成代码 (可选)
read -p "🤔 Run code generation (build_runner)? This may take a while. [y/N]: " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "⚙️  Running build_runner..."
  flutter pub run build_runner build --delete-conflicting-outputs
  echo ""
fi

# 4. 检查设备
echo "📱 Checking available devices..."
flutter devices
echo ""

# 5. 提示后续步骤
echo "✅ Demo environment setup complete!"
echo ""
echo "🚀 Next steps:"
echo ""
echo "   Run on device/emulator:"
echo "   $ flutter run --dart-define=DEMO_MODE=true"
echo ""
echo "   Build Android APK:"
echo "   $ flutter build apk --dart-define=DEMO_MODE=true --release --split-per-abi"
echo ""
echo "   Build for iOS (macOS only):"
echo "   $ flutter build ios --dart-define=DEMO_MODE=true --release --no-codesign"
echo ""
echo "   Build for Web:"
echo "   $ flutter build web --dart-define=DEMO_MODE=true --release"
echo ""
echo "📝 Note: DEMO_MODE=true enables mock data and disables backend requirements"
echo ""
