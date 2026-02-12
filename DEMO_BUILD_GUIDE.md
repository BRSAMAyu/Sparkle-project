# Sparkle Demo 版本打包指南

**目标**: 打包一个独立的、带完整 Mock 数据的演示版本，无需后端服务器
**用途**: Beta 测试、产品演示、App Store 预览版
**状态**: ✅ 项目已有完整 Demo 系统支持

---

## 📋 当前 Demo 系统概览

### ✅ 已有的 Demo 基础设施

你的项目已经有完善的 Demo 模式支持：

1. **DemoDataService** (`lib/core/services/demo_data_service.dart`)
   - 提供完整的 Mock 数据
   - 涵盖所有功能模块 (用户、任务、计划、星图、聊天等)
   - 支持动态更新 (如头像切换)

2. **环境变量控制** (`lib/main.dart:52-53`)
   ```dart
   const isDemoMode = bool.fromEnvironment('DEMO_MODE');
   DemoDataService.isDemoMode = isDemoMode;
   ```

3. **Repository 层集成**
   - 所有 Repository 都有 `if (DemoDataService.isDemoMode)` 检查
   - Demo 模式下返回 Mock 数据，不发送网络请求

### 📊 Demo 数据覆盖范围

| 模块 | 覆盖情况 | Mock 数据 |
|------|---------|----------|
| **用户系统** | ✅ 完整 | 虚拟用户、等级、偏好设置 |
| **任务系统** | ✅ 完整 | 15+ 示例任务，多种状态 |
| **计划系统** | ✅ 完整 | 学习计划、里程碑 |
| **知识星图** | ✅ 完整 | 50+ 知识节点、连接关系 |
| **聊天系统** | ✅ 完整 | 示例对话历史 |
| **成就系统** | ✅ 完整 | 解锁/未解锁成就 |
| **社区系统** | ✅ 完整 | 学习小组、讨论 |

---

## 🚀 打包方案

### 方案 A: 移动应用 (推荐 ⭐)

#### Android APK/AAB

**特点**:
- ✅ 最通用，适合 Beta 测试
- ✅ 可直接分发或上传 Google Play Internal Testing
- ✅ 包大小: ~50-80MB

**打包命令**:

```bash
cd mobile

# 1. Debug APK (快速测试)
flutter build apk --dart-define=DEMO_MODE=true --debug

# 2. Release APK (Beta 分发)
flutter build apk --dart-define=DEMO_MODE=true --release

# 3. App Bundle (Google Play)
flutter build appbundle --dart-define=DEMO_MODE=true --release

# 输出位置:
# build/app/outputs/flutter-apk/app-release.apk
# build/app/outputs/bundle/release/app-release.aab
```

**分发方式**:
- 📧 直接发送 APK 给测试用户
- 🔗 上传到 Firebase App Distribution
- 🏪 Google Play Internal Testing Track

#### iOS IPA

**特点**:
- ✅ TestFlight 分发
- ⚠️ 需要 Apple Developer 账号 ($99/年)
- ⚠️ 需要在 macOS 上打包

**打包命令**:

```bash
cd mobile

# 1. 构建
flutter build ios --dart-define=DEMO_MODE=true --release

# 2. 使用 Xcode 打开
open ios/Runner.xcworkspace

# 3. 在 Xcode 中:
# - Product > Archive
# - Distribute App > Ad Hoc (直接分发) 或 App Store Connect (TestFlight)
```

**分发方式**:
- ✈️ TestFlight (推荐)
- 📱 通过 `.ipa` 文件直接安装

---

### 方案 B: Web 应用

**特点**:
- ✅ 无需安装，浏览器直接访问
- ✅ 最容易分享 (一个 URL)
- ✅ 自动更新
- ⚠️ 性能略低于原生

**打包命令**:

```bash
cd mobile

# 构建 Web 版本
flutter build web --dart-define=DEMO_MODE=true --release

# 输出位置: build/web/
```

**部署方式**:

#### 1. GitHub Pages (免费)

```bash
# 方法 A: 使用 gh-pages 分支
cd build/web
git init
git add .
git commit -m "Deploy Demo"
git branch -M gh-pages
git remote add origin https://github.com/yourusername/sparkle-demo.git
git push -u origin gh-pages --force

# 访问: https://yourusername.github.io/sparkle-demo/
```

#### 2. Vercel (免费，推荐)

```bash
# 安装 Vercel CLI
npm i -g vercel

# 部署
cd build/web
vercel --prod

# 会得到一个 URL: https://sparkle-demo.vercel.app
```

#### 3. Firebase Hosting (免费)

```bash
# 安装 Firebase CLI
npm install -g firebase-tools

# 初始化
firebase login
firebase init hosting

# 部署
firebase deploy --only hosting

# 访问: https://your-project.web.app
```

#### 4. Netlify (免费)

```bash
# 拖拽 build/web 文件夹到 https://app.netlify.com/drop
# 或使用 CLI:
npm install netlify-cli -g
cd build/web
netlify deploy --prod
```

---

### 方案 C: 桌面应用

**特点**:
- ✅ 完整的桌面体验
- ✅ 独立运行，无需浏览器
- ⚠️ 包体积较大 (100-200MB)

#### Windows

```bash
cd mobile
flutter build windows --dart-define=DEMO_MODE=true --release

# 输出位置: build/windows/x64/runner/Release/
# 打包成 .zip 或使用 Inno Setup 制作安装程序
```

#### macOS

```bash
cd mobile
flutter build macos --dart-define=DEMO_MODE=true --release

# 输出位置: build/macos/Build/Products/Release/sparkle.app
# 打包成 .dmg
```

#### Linux

```bash
cd mobile
flutter build linux --dart-define=DEMO_MODE=true --release

# 输出位置: build/linux/x64/release/bundle/
# 打包成 .tar.gz 或 .deb
```

---

## 🎨 优化 Demo 体验

### 1. 添加 Demo 标识

在 UI 上显示 "Demo 模式"，让用户知道这是演示版本：

```dart
// lib/main.dart 中添加
class MyApp extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      // ...
      builder: (context, child) {
        return Stack(
          children: [
            child!,
            // Demo 标识
            if (DemoDataService.isDemoMode)
              Positioned(
                top: 50,
                right: 10,
                child: Container(
                  padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    gradient: DS.secondaryGradient,
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(
                        color: DS.brandPrimary.withOpacity(0.3),
                        blurRadius: 8,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.science, size: 16, color: DS.brandPrimaryConst),
                      SizedBox(width: 4),
                      Text(
                        'DEMO',
                        style: TextStyle(
                          color: DS.brandPrimaryConst,
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}
```

### 2. 添加功能引导

创建一个 Demo 专用的引导页面：

```dart
// lib/features/demo/demo_welcome_screen.dart
class DemoWelcomeScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.rocket_launch, size: 80, color: DS.brandPrimary),
              SizedBox(height: 24),
              Text(
                '欢迎体验 Sparkle Demo',
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              SizedBox(height: 16),
              Text(
                '这是一个功能完整的演示版本\n所有数据都是模拟的，不会连接到服务器',
                style: TextStyle(
                  fontSize: 16,
                  color: DS.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),
              SizedBox(height: 48),
              _buildFeatureCard('🌟 知识星图', '探索 50+ 知识节点'),
              _buildFeatureCard('✅ 智能任务', '体验 AI 驱动的学习规划'),
              _buildFeatureCard('💬 AI 对话', '与学习助手互动'),
              _buildFeatureCard('🎯 专注模式', '高效学习工具'),
              SizedBox(height: 32),
              CustomButton.primary(
                text: '开始探索',
                onPressed: () => Navigator.pushReplacementNamed(context, '/home'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFeatureCard(String icon, String text) {
    return Container(
      margin: EdgeInsets.only(bottom: 12),
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Text(icon, style: TextStyle(fontSize: 24)),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              text,
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}
```

### 3. 禁用不必要的功能

在 Demo 模式下禁用需要后端的功能：

```dart
// 示例: 在设置页面禁用账号登出
if (!DemoDataService.isDemoMode)
  ListTile(
    title: Text('退出登录'),
    onTap: _handleLogout,
  )
else
  ListTile(
    title: Text('退出登录'),
    subtitle: Text('Demo 模式下不可用'),
    enabled: false,
  ),
```

---

## 📦 完整打包脚本

创建自动化打包脚本：

```bash
#!/bin/bash
# build_demo.sh

echo "🚀 Building Sparkle Demo Version..."

cd mobile

# 清理
echo "🧹 Cleaning..."
flutter clean
flutter pub get

# Android
echo "📱 Building Android APK..."
flutter build apk --dart-define=DEMO_MODE=true --release --split-per-abi

# Web
echo "🌐 Building Web..."
flutter build web --dart-define=DEMO_MODE=true --release

# iOS (可选，需要 macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
  echo "🍎 Building iOS..."
  flutter build ios --dart-define=DEMO_MODE=true --release --no-codesign
fi

# 创建分发包
echo "📦 Creating distribution package..."
mkdir -p ../demo_builds
cp build/app/outputs/flutter-apk/app-armeabi-v7a-release.apk ../demo_builds/sparkle-demo-android-arm.apk
cp build/app/outputs/flutter-apk/app-arm64-v8a-release.apk ../demo_builds/sparkle-demo-android-arm64.apk
cp build/app/outputs/flutter-apk/app-x86_64-release.apk ../demo_builds/sparkle-demo-android-x64.apk
cp -r build/web ../demo_builds/sparkle-demo-web

echo "✅ Done! Builds available in demo_builds/"
echo ""
echo "📱 Android: demo_builds/sparkle-demo-android-*.apk"
echo "🌐 Web: demo_builds/sparkle-demo-web/"
```

使用方法：

```bash
chmod +x build_demo.sh
./build_demo.sh
```

---

## 🎯 推荐的分发策略

### Beta 测试阶段

**方案**: Android APK + Web 版本

1. **Android APK**
   - 上传到 Google Play Internal Testing
   - 或使用 Firebase App Distribution
   - 发送测试链接给 Beta 用户

2. **Web 版本**
   - 部署到 Vercel/Netlify
   - 最容易访问，无需安装
   - 适合快速展示

### App Store 提交阶段

**方案**: 完整的 Release 版本

1. **iOS**: TestFlight → App Store
2. **Android**: Internal Testing → Closed Testing → Open Testing → Production

---

## ⚠️ Demo 模式注意事项

### 1. 数据持久化

Demo 模式下的数据修改不会保存：

```dart
// 考虑添加本地存储支持
class DemoDataService {
  // 使用 SharedPreferences 保存 Demo 数据状态
  Future<void> saveDemoState() async {
    final prefs = await SharedPreferences.getInstance();
    // 保存当前状态
  }

  Future<void> loadDemoState() async {
    final prefs = await SharedPreferences.getInstance();
    // 恢复状态
  }
}
```

### 2. 网络请求

确保所有网络请求都有 Demo 模式检查：

```dart
// ✅ 正确
Future<List<Task>> getTasks() async {
  if (DemoDataService.isDemoMode) {
    return DemoDataService().demoTasks;
  }
  // 正常网络请求
}

// ❌ 错误 - 会尝试连接服务器
Future<List<Task>> getTasks() async {
  return await apiClient.get('/tasks');
}
```

### 3. 性能

Demo 数据应该适量：

- ✅ 50-100 个节点的星图 (演示效果好)
- ❌ 1000+ 个节点 (性能差，不适合演示)

---

## 📋 发布检查清单

### 打包前

- [ ] 确认 Demo 数据完整且有代表性
- [ ] 测试所有核心功能在 Demo 模式下正常工作
- [ ] 添加 Demo 标识和引导
- [ ] 清理调试代码和 console.log
- [ ] 更新版本号和构建号

### 打包

- [ ] 执行 `flutter clean && flutter pub get`
- [ ] 使用 `--release` 模式构建
- [ ] 使用 `--dart-define=DEMO_MODE=true`
- [ ] 测试打包后的应用

### 分发

- [ ] 准备 App 图标和截图
- [ ] 编写 Beta 测试说明文档
- [ ] 设置反馈收集方式 (问卷/邮件)
- [ ] 记录已知问题列表

---

## 🎉 快速开始 (TL;DR)

### 最简单的方式

```bash
cd mobile

# 1. 打包 Android APK
flutter build apk --dart-define=DEMO_MODE=true --release

# 2. 分发
# 将 build/app/outputs/flutter-apk/app-release.apk 发送给测试用户

# 或者部署 Web 版本
flutter build web --dart-define=DEMO_MODE=true --release
cd build/web
vercel --prod  # 或 netlify deploy --prod
```

---

## 📊 各平台对比

| 平台 | 打包难度 | 分发难度 | 用户体验 | 包大小 | 推荐指数 |
|------|---------|---------|---------|--------|---------|
| **Android APK** | ⭐ 简单 | ⭐ 简单 | ⭐⭐⭐ 优秀 | ~60MB | ⭐⭐⭐⭐⭐ |
| **Web** | ⭐ 简单 | ⭐ 超简单 | ⭐⭐ 良好 | ~5MB | ⭐⭐⭐⭐⭐ |
| **iOS** | ⭐⭐⭐ 中等 | ⭐⭐ 中等 | ⭐⭐⭐ 优秀 | ~70MB | ⭐⭐⭐⭐ |
| **桌面** | ⭐⭐ 较易 | ⭐⭐ 中等 | ⭐⭐⭐ 优秀 | ~150MB | ⭐⭐⭐ |

---

## 🚀 我的建议

**最佳组合**: **Android APK + Web 版本**

**理由**:
1. ✅ **覆盖最广**: Android 用户量大 + Web 无平台限制
2. ✅ **部署简单**: 无需复杂配置
3. ✅ **成本低**: 完全免费
4. ✅ **迭代快**: 可以快速更新

**实施步骤**:
```bash
# 1. 打包 Android
flutter build apk --dart-define=DEMO_MODE=true --release --split-per-abi

# 2. 部署 Web
flutter build web --dart-define=DEMO_MODE=true --release
cd build/web && vercel --prod

# 3. 分发
# - Android APK: 上传到 Firebase App Distribution
# - Web: 分享 Vercel URL
```

**预期效果**:
- 📱 Android 用户: 下载 APK 安装体验
- 💻 其他用户: 访问 Web 版本体验
- 🎯 测试覆盖率: ~90% 的潜在用户

---

**创建日期**: 2026-02-02
**项目**: Sparkle (星火) AI Learning Assistant
**用途**: Beta 测试和产品演示
