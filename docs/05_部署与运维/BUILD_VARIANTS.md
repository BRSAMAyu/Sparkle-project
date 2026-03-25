# Flutter 构建变体指南

本文档说明如何为不同目标市场构建应用。

## 构建变体

### 国内版（默认推荐）

适用于中国大陆用户，使用极光推送和微信登录。

```bash
# 禁用 Google 服务（Firebase、Google Sign-In）
flutter build apk --dart-define=ENABLE_GOOGLE_SERVICES=false

# 或使用 Makefile
make mobile-build-china
```

**特点：**
- ✅ 极光推送（JPush）正常工作
- ✅ 微信登录正常工作
- ✅ Apple 登录正常工作
- ❌ Firebase 推送不可用
- ❌ Google 登录不可用
- ✅ 无需 VPN 构建

### 国际版

适用于海外用户，使用 Firebase 推送和 Google 登录。

```bash
# 启用 Google 服务（默认）
flutter build apk

# 或显式指定
flutter build apk --dart-define=ENABLE_GOOGLE_SERVICES=true
```

**特点：**
- ✅ Firebase 推送（FCM）正常工作
- ✅ Google 登录正常工作
- ✅ Apple 登录正常工作
- ⚠️ 首次构建可能需要 VPN（下载 Google SDK）
- ⚠️ 极光推送也可用（作为备用）

## 编译时常量

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `ENABLE_GOOGLE_SERVICES` | `true` | 是否启用 Google 服务（Firebase、Google 登录） |
| `FCM_ENABLED` | `true` | 是否启用 FCM（需要 ENABLE_GOOGLE_SERVICES=true） |
| `JPUSH_ENABLED` | `true` | 是否启用极光推送 |
| `JPUSH_APP_KEY` | - | 极光推送 App Key |
| `WECHAT_APP_ID` | - | 微信 App ID |
| `WECHAT_UNIVERSAL_LINK` | - | 微信 Universal Link（iOS） |

## Makefile 目标

```bash
# 国内版构建
make mobile-build-china

# 国际版构建
make mobile-build-intl

# 仅生成 Dart protobufs
make mobile-proto

# 生成 protobufs + build_runner
make mobile-gen

# 运行应用
make mobile-run
```

## 平台特定配置

### Android

国内版和国际版使用相同的 APK，但运行时行为不同：
- 检测设备区域
- 自动选择推送渠道（JPush 或 FCM）

### iOS

iOS 需要为不同市场使用不同的 Bundle ID：
- 国内版：`com.sparkle.china`
- 国际版：`com.sparkle.intl`

配置位置：`mobile/ios/Runner.xcodeproj`

## 首次构建注意事项

### 国内版
无需特殊配置，直接构建即可。

### 国际版
首次构建需要下载 Google SDK，建议：
1. 开启 VPN
2. 执行构建命令
3. 依赖会被缓存，后续构建无需 VPN

```bash
# 首次构建（需要 VPN）
flutter build apk --dart-define=ENABLE_GOOGLE_SERVICES=true

# 后续构建（使用缓存，无需 VPN）
flutter build apk --dart-define=ENABLE_GOOGLE_SERVICES=true
```

## 常见问题

### Q: 国内版能否使用 FCM？
A: 不建议。FCM 在国内网络环境下不稳定，推荐使用极光推送。

### Q: 国际版能否使用极光推送？
A: 可以。极光推送支持海外用户，但建议使用 FCM 获得最佳体验。

### Q: 如何同时支持国内外用户？
A: 使用国际版构建，应用会根据设备区域自动选择推送渠道：
- 国内用户 → 极光推送
- 海外用户 → FCM
