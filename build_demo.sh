#!/bin/bash
# Sparkle Demo 版本自动打包脚本
# 用途: 创建带 Mock 数据的独立演示版本

set -e

echo "🚀 Building Sparkle Demo Version..."
echo ""

# 进入 mobile 目录
cd mobile

# 清理
echo "🧹 Cleaning previous builds..."
flutter clean
flutter pub get
echo ""

# Android APK
echo "📱 Building Android APK (Release)..."
flutter build apk \
  --dart-define=DEMO_MODE=true \
  --release \
  --split-per-abi
echo "✅ Android APK built"
echo ""

# Web
echo "🌐 Building Web version..."
flutter build web \
  --dart-define=DEMO_MODE=true \
  --release
echo "✅ Web version built"
echo ""

# iOS (仅在 macOS 上)
if [[ "$OSTYPE" == "darwin"* ]]; then
  echo "🍎 Building iOS (no codesign)..."
  flutter build ios \
    --dart-define=DEMO_MODE=true \
    --release \
    --no-codesign
  echo "✅ iOS built"
  echo ""
fi

# 创建分发目录
echo "📦 Organizing builds..."
cd ..
mkdir -p demo_builds

# 复制构建产物
cp mobile/build/app/outputs/flutter-apk/app-armeabi-v7a-release.apk demo_builds/sparkle-demo-android-arm.apk 2>/dev/null || true
cp mobile/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk demo_builds/sparkle-demo-android-arm64.apk 2>/dev/null || true
cp mobile/build/app/outputs/flutter-apk/app-x86_64-release.apk demo_builds/sparkle-demo-android-x64.apk 2>/dev/null || true

# 复制 Web 版本
rm -rf demo_builds/sparkle-demo-web
cp -r mobile/build/web demo_builds/sparkle-demo-web

# 创建 README
cat > demo_builds/README.md << 'EOF'
# Sparkle Demo Builds

## 📱 Android APK

选择适合你设备的版本：

- **sparkle-demo-android-arm64.apk** (推荐，适用于大多数现代 Android 设备)
- **sparkle-demo-android-arm.apk** (适用于较老的 32 位设备)
- **sparkle-demo-android-x64.apk** (适用于 x86 架构设备/模拟器)

### 安装方法：

1. 在手机上下载 APK 文件
2. 打开文件管理器，点击下载的 APK
3. 允许安装未知来源应用
4. 点击安装

## 🌐 Web 版本

Web 版本位于 `sparkle-demo-web/` 目录。

### 本地预览：

```bash
cd sparkle-demo-web
python3 -m http.server 8000
# 访问 http://localhost:8000
```

### 部署到 Vercel：

```bash
cd sparkle-demo-web
vercel --prod
```

## 📝 说明

- ✅ 所有数据都是模拟的
- ✅ 无需后端服务器
- ✅ 完整功能演示
- ⚠️ 不会保存用户数据
EOF

echo "✅ Done! Distribution package created"
echo ""
echo "📦 Builds available in: demo_builds/"
echo ""
echo "📱 Android APKs:"
ls -lh demo_builds/*.apk 2>/dev/null | awk '{print "   - " $9 " (" $5 ")"}'
echo ""
echo "🌐 Web version:"
echo "   - demo_builds/sparkle-demo-web/"
echo ""
echo "🎯 Next steps:"
echo "   1. Test the builds on real devices"
echo "   2. Upload APK to Firebase App Distribution or Google Play"
echo "   3. Deploy Web version to Vercel/Netlify"
echo ""
echo "💡 Quick deploy Web:"
echo "   cd demo_builds/sparkle-demo-web && vercel --prod"
echo ""
