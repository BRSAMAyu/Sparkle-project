# iOS/macOS 本地网络权限配置指南

## 概述

在真机和 iOS 模拟器上进行本地开发时，需要配置本地网络权限才能访问运行在本机的开发服务器（如 `http://192.168.x.x:8080`）。

## 权限说明

### NSLocalNetworkUsageDescription

**iOS 14+ / macOS 11+** 要求应用在使用 Bonjour 或本地网络时，必须在 `Info.plist` 中声明使用原因并在首次访问时获得用户授权。

### NSAllowsLocalNetworking

**iOS 9+ / macOS 10.11+** 默认禁用 HTTP 本地网络连接。需要显式允许以访问 `http://localhost` 或局域网 IP。

## 配置步骤

### 1. iOS (mobile/ios/Runner/Info.plist)

已配置的权限：

```xml
<key>NSLocalNetworkUsageDescription</key>
<string>需要连接到本地开发服务器以进行API调试和数据同步</string>

<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

### 2. macOS (mobile/macos/Runner/Info.plist)

已配置的权限：

```xml
<key>NSLocalNetworkUsageDescription</key>
<string>需要连接到本地开发服务器以进行API调试和数据同步</string>

<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

## 获取本机 IP 地址

### macOS

```bash
# 方法 1: 查看 IP 地址
ifconfig | grep "inet " | grep -v 127.0.0.1

# 方法 2: 仅获取局域网 IP
ipconfig getifaddr en0  # Wi-Fi
ipconfig getifaddr en1  # 有线网络
```

### Windows

```powershell
ipconfig | findstr "IPv4"
```

### Linux

```bash
hostname -I | awk '{print $1}'
```

## 移动端 API 配置

### Android

Android 模拟器使用特殊别名访问主机：

```dart
// mobile/lib/core/config/api_config.dart
const String apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8080',  // Android 模拟器
);
```

**真机配置**:
```dart
const String apiBaseUrl = 'http://192.168.x.x:8080';  // 替换为实际 IP
```

### iOS 真机

```dart
const String apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://192.168.x.x:8080',  // 替换为实际 IP
);
```

### iOS 模拟器

```dart
const String apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8080',  // iOS 模拟器可直接用 localhost
);
```

## 环境变量配置

### 通过命令行构建

```bash
# Android 真机
flutter run --dart-define=API_BASE_URL=http://192.168.1.100:8080

# iOS 真机
flutter run -d ios --dart-define=API_BASE_URL=http://192.168.1.100:8080
```

### 通过 .env 文件（推荐）

创建 `mobile/.env`:

```bash
API_BASE_URL=http://192.168.1.100:8080
```

使用 `flutter_dotenv` 加载:

```dart
import 'package:flutter_dotenv/flutter_dotenv.dart';

await dotenv.load(fileName: ".env");
final apiBaseUrl = dotenv.env['API_BASE_URL'] ?? 'http://localhost:8080';
```

## 验证连接

### 1. 检查网络可达性

```bash
# 从开发机测试
curl http://192.168.x.x:8080/health

# 从移动设备浏览器测试
# 打开 Safari/Chrome 访问: http://192.168.x.x:8080/health
```

### 2. 检查防火墙

**macOS**:
```bash
# 系统偏好设置 -> 安全性与隐私 -> 防火墙
# 确保允许传入连接
```

**Windows**:
```powershell
# Windows Defender 防火墙 -> 允许应用通过防火墙
# 允许 Python 或 Docker Desktop
```

### 3. 检查服务监听地址

确保后端服务监听 `0.0.0.0` 而不是 `127.0.0.1`:

```bash
# docker-compose.yml
services:
  sparkle_gateway:
    ports:
      - "8080:8080"
    # 确保没有 extra_hosts 限制
```

## 常见问题

### Q1: iOS 真机提示"无法连接到服务器"

**检查清单**:
1. 设备与开发机在同一 Wi-Fi 网络
2. 后端服务正在运行 (`docker compose ps`)
3. IP 地址正确 (`ifconfig` 查看)
4. 防火墙允许端口 8080
5. 使用 `http://` 而不是 `https://`

### Q2: macOS 提示"App 想要使用本地网络"

**正常行为**: 首次启动时点击"允许"

### Q3: Android 模拟器无法连接

**解决方案**: 使用 `10.0.2.2` 而不是 `localhost`

```dart
// Android 模拟器特殊别名
const String androidEmulatorUrl = 'http://10.0.2.2:8080';
```

### Q4: iOS 模拟器可以连接但真机不行

**原因**: 真机无法访问 `localhost`

**解决方案**: 使用局域网 IP

```dart
final apiBaseUrl = Platform.isIOS && !Platform.isIOS 
    ? 'http://192.168.x.x:8080'  // 真机
    : 'http://localhost:8080';    // 模拟器
```

## 生产环境配置

发布到 App Store / TestFlight 时，应该：

1. **移除本地网络权限** (如果不需要)
2. **使用生产环境 API URL**
3. **禁用 `NSAllowsArbitraryLoads`**

```xml
<!-- 生产环境 Info.plist -->
<key>NSAppTransportSecurity</key>
<dict>
    <!-- 仅允许特定域名 -->
    <key>NSExceptionDomains</key>
    <dict>
        <key>api.yourapp.com</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <false/>
            <key>NSIncludesSubdomains</key>
            <true/>
        </dict>
    </dict>
</dict>
```

## 相关文档

- [Apple Developer - Local Network Privacy](https://developer.apple.com/documentation/bundleresources/protecting_the_users_privacy/about_ios_local_network_privacy)
- [Configuring App Transport Security](https://developer.apple.com/documentation/security/preventing_insecure_network_connections)
- `docs/EVENT_OUTBOX_MIGRATION.md` - 事件发布链路迁移
- `docs/REAL_DEVICE_INTEGRATION_TEST.md` - 真机联调完整流程
