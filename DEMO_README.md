# Sparkle Demo 版本构建指南

本文档说明如何构建和分发 Sparkle 的 Demo 版本（带 Mock 数据，无需后端服务器）。

## 🎯 快速开始

### 方式 1: 自动化安装（推荐）

```bash
cd mobile
bash install_demo.sh
```

这会自动完成：
- ✅ 检查 Flutter 环境
- ✅ 安装项目依赖
- ✅ 修复 isar_flutter_libs Android SDK 兼容性问题
- ✅ 可选运行代码生成

### 方式 2: 手动步骤

```bash
cd mobile

# 1. 安装依赖
flutter pub get

# 2. 修复 isar SDK 兼容性（必须！）
bash fix_isar_sdk.sh

# 3. 运行 Demo
flutter run --dart-define=DEMO_MODE=true
```

---

## 📱 构建发布版本

### Android APK

```bash
# 在项目根目录运行
bash build_demo.sh

# 或手动构建
cd mobile
bash fix_isar_sdk.sh  # 确保先修复兼容性
flutter build apk --dart-define=DEMO_MODE=true --release --split-per-abi
```

**输出位置**: `mobile/build/app/outputs/flutter-apk/`
- `app-arm64-v8a-release.apk` - 推荐，适用于大多数现代设备
- `app-armeabi-v7a-release.apk` - 适用于较老的 32 位设备
- `app-x86_64-release.apk` - 适用于 x86 模拟器

### iOS (仅 macOS)

```bash
cd mobile
bash fix_isar_sdk.sh
flutter build ios --dart-define=DEMO_MODE=true --release --no-codesign
```

### Web

```bash
cd mobile
flutter build web --dart-define=DEMO_MODE=true --release
```

**部署**: `mobile/build/web/` 目录可直接上传到静态托管服务（Vercel/Netlify/GitHub Pages）

---

## 🔧 常见问题

### 1. Android 构建失败: `android:attr/lStar not found`

**原因**: isar_flutter_libs 3.1.0+1 默认使用 `compileSdkVersion 30`，但其依赖需要 API 31+。

**解决方案**:
```bash
cd mobile
bash fix_isar_sdk.sh
```

这个脚本会自动将 `~/.pub-cache/hosted/pub.dev/isar_flutter_libs-3.1.0+1/android/build.gradle` 中的 `compileSdkVersion 30` 修改为 `36`。

**注意**: 以下操作会重置此修复，需要重新运行脚本：
- `flutter pub cache repair`
- 删除 `.pub-cache` 目录
- 其他开发者首次拉取代码

### 2. WeChat 登录不可用

**原因**: Demo 版本禁用了 fluwx (WeChat SDK) 以避免编译问题。

**解决方案**: 这是预期行为。Demo 版本仅支持 Google 和 Apple 登录。如需 WeChat 登录，请使用完整版本。

### 3. 构建速度慢

**优化建议**:
- 使用 `--split-per-abi` 只构建目标架构
- 首次构建后，增量构建会快很多
- 调整 `android/gradle.properties` 中的 JVM 内存设置：
  ```properties
  org.gradle.jvmargs=-Xmx8G
  ```

---

## 📦 分发 Demo 版本

### Android APK

**方式 1: 本地分发**
```bash
# 通过 ADB 安装
adb install mobile/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk

# 或传输到设备后通过文件管理器安装
```

**方式 2: Firebase App Distribution**
```bash
# 安装 Firebase CLI
npm install -g firebase-tools

# 上传到 Firebase
firebase appdistribution:distribute \
  mobile/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk \
  --app YOUR_APP_ID \
  --groups testers
```

**方式 3: GitHub Releases**
```bash
# 使用 gh CLI
gh release create demo-v1.0 \
  mobile/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk \
  --title "Sparkle Demo v1.0" \
  --notes "Demo version with mock data"
```

### Web 版本

**Vercel 部署**:
```bash
cd mobile/build/web
vercel --prod
```

**Netlify 部署**:
```bash
cd mobile/build/web
netlify deploy --prod --dir .
```

**GitHub Pages**:
```bash
# 将 mobile/build/web 内容推送到 gh-pages 分支
cd mobile/build/web
git init
git add .
git commit -m "Deploy demo"
git remote add origin YOUR_REPO_URL
git push -f origin main:gh-pages
```

---

## 🔐 Demo 模式说明

通过 `--dart-define=DEMO_MODE=true` 启用 Demo 模式后：

### ✅ 启用的功能
- Mock 用户数据和学习记录
- 模拟 AI 对话和任务推荐
- 完整 UI/UX 展示
- Google/Apple 社交登录（可选）
- 离线数据存储

### ❌ 禁用的功能
- WeChat 登录（因 SDK 兼容性）
- 真实后端 API 调用
- 数据持久化到云端
- 第三方集成（Sentry 等）

### 📝 实现细节

Demo 模式通过以下方式实现：

**1. 编译时常量**:
```dart
const bool isDemoMode = bool.fromEnvironment('DEMO_MODE', defaultValue: false);
```

**2. Mock 数据服务**:
```dart
if (isDemoMode) {
  return DemoDataService();
} else {
  return RealApiService();
}
```

**3. 条件编译**:
```dart
if (!isDemoMode) {
  await Sentry.init(...);
}
```

---

## 🛠️ 脚本说明

### `mobile/fix_isar_sdk.sh`
修复 isar_flutter_libs Android SDK 兼容性问题。

**功能**:
- 自动查找 pub cache 中的 isar_flutter_libs
- 修改 `compileSdkVersion 30` → `36`
- 创建备份文件
- 跨平台支持 (macOS/Linux)

**使用**:
```bash
cd mobile
bash fix_isar_sdk.sh
```

### `mobile/install_demo.sh`
一键设置 Demo 开发环境。

**功能**:
- 检查 Flutter 安装
- 安装项目依赖
- 自动调用 `fix_isar_sdk.sh`
- 可选运行代码生成
- 显示后续步骤提示

**使用**:
```bash
cd mobile
bash install_demo.sh
```

### `build_demo.sh` (项目根目录)
自动构建所有平台的 Demo 版本。

**功能**:
- 自动清理旧构建
- 自动修复 isar 兼容性
- 构建 Android APK (split-per-abi)
- 构建 Web 版本
- 构建 iOS (仅 macOS)
- 组织输出到 `demo_builds/` 目录

**使用**:
```bash
bash build_demo.sh
```

---

## 📚 相关文档

- [DEMO_BUILD_GUIDE.md](./DEMO_BUILD_GUIDE.md) - 详细构建指南
- [CLAUDE.md](./CLAUDE.md) - 项目架构文档
- [README.md](./README.md) - 项目概览

---

## 🆘 获取帮助

遇到问题？

1. **检查日志**: 构建失败时查看完整错误堆栈
2. **清理重试**: `flutter clean && flutter pub get && bash fix_isar_sdk.sh`
3. **更新依赖**: `flutter pub upgrade --major-versions`
4. **提交 Issue**: 到 GitHub Issues 报告问题

---

**最后更新**: 2026-02-02
**适用版本**: Sparkle v0.3.0+
