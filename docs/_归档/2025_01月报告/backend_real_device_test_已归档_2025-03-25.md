# 真机联调完整流程指南

## 概述

本文档提供 Sparkle 项目的完整真机联调流程，确保 Android/iOS/macOS 平台与后端服务的稳定通信。

## 前置条件

### 硬件要求
- macOS 开发机（iOS/macOS 开发必需）
- Android 真机或模拟器（API 21+）
- iOS 真机（iOS 12+）或模拟器
- 同一 Wi-Fi 网络（真机调试）

### 软件要求
- Flutter SDK (3.19+)
- Xcode (15.0+) - iOS/macOS 开发
- Android Studio - Android 开发
- Docker Desktop - 后端服务

### 服务启动

```bash
# 1. 启动基础服务
cd /Users/a/code/sparkle-flutter
make dev-all

# 2. 启动网关和 API
make gateway-dev
make grpc-server

# 3. 验证服务
curl http://localhost:8080/health
curl http://localhost:8000/health
```

## 网络配置

### 获取本机 IP

```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1
# 输出示例: inet 192.168.1.100 netmask 0xffffff00 broadcast 192.168.1.255

# 记录 IP 地址: 192.168.1.100
```

### 配置移动端 API URL

#### Android

**真机配置** (`mobile/android/app/src/main/AndroidManifest.xml`):

```xml
<meta-data
    android:name="API_BASE_URL"
    android:value="http://192.168.1.100:8080" />
```

**模拟器配置** - 使用 `10.0.2.2`:

```xml
<meta-data
    android:name="API_BASE_URL"
    android:value="http://10.0.2.2:8080" />
```

#### iOS/macOS

已配置 `NSLocalNetworkUsageDescription` 和 `NSAllowsLocalNetworking`（参见 `docs/IOS_LOCAL_NETWORK_PERMISSIONS.md`）

**真机配置** - 在 Xcode 中:
1. 打开 `mobile/ios/Runner.xcworkspace`
2. 选择 `Runner` target
3. `Build Settings` -> `User-Defined`
4. 添加 `API_BASE_URL` = `http://192.168.1.100:8080`

**模拟器配置** - 使用 `localhost`:

```dart
// mobile/lib/core/config/api_config.dart
const String apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8080',
);
```

## 后端验证

### 1. 检查数据库迁移

```bash
docker exec sparkle_api alembic current
# 应输出: 5f2b9b3c0e6f (head)

docker exec sparkle_db psql -U postgres -d sparkle -c "
SELECT tablename FROM pg_tables 
WHERE schemaname='public' AND tablename LIKE 'event_%';"
# 应输出:
#   event_outbox
#   event_sequence_counters
```

### 2. 创建测试用户

```bash
# 方法 1: 使用 API
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "device_test_user",
    "email": "device_test@sparkle.com",
    "password": "DeviceTest123"
  }'

# 方法 2: 使用脚本
cd backend
python3 create_test_user.py
```

### 3. 验证关键端点

```bash
# 获取 Token
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"device_test_user","password":"DeviceTest123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 测试 Onboarding
curl -X POST http://localhost:8080/api/v1/profile/onboarding \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"learning_goal":"测试学习目标","study_time_minutes":30}'

# 测试任务创建
curl -X POST http://localhost:8080/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"learning","title":"测试任务","description":"验证端到端流程"}'
```

## 移动端测试清单

### 1. 基础启动测试

| 平台 | 测试项 | 预期结果 |
|------|--------|----------|
| Android | App 启动 | 无 Crash，显示登录页 |
| iOS | App 启动 | 无 Crash，显示登录页 |
| macOS | App 启动 | 无 Crash，显示登录页 |

### 2. 认证链路测试

| 测试项 | 操作 | 预期结果 |
|--------|------|----------|
| 注册 | 使用新用户注册 | 200，返回 user + token |
| 重复注册 | 使用已存在用户名 | 200，错误提示"用户名已注册" |
| 登录成功 | 使用测试用户登录 | 200，自动跳转主页 |
| 登录失败 | 错误密码登录 | 200，错误提示"用户名或密码不正确" |

### 3. Onboarding 测试

| 测试项 | 操作 | 预期结果 |
|--------|------|----------|
| 提交画像 | 选择学习目标并提交 | 200，返回 `{"status":"ok"}` |
| 数据保存 | 刷新 App | 学习目标保持 |
| 跳过流程 | 跳过 Onboarding | 允许跳过或引导完成 |

### 4. 任务管理测试

| 测试项 | 操作 | 预期结果 |
|--------|------|----------|
| 创建任务 | 创建学习任务 | 200，返回任务 ID |
| 任务列表 | 查看任务列表 | 显示新创建的任务 |
| 任务详情 | 点击任务 | 显示任务详情 |

### 5. 聊天功能测试

| 测试项 | 操作 | 预期结果 |
|--------|------|----------|
| WebSocket 连接 | 进入聊天页面 | 连接成功，无错误 |
| 发送消息 | 发送文本消息 | 收到 AI 回复 |
| 错误处理 | 断网后发送 | 显示错误提示，不 Crash |

### 6. 稳定性测试

| 测试项 | 操作 | 预期结果 |
|--------|------|----------|
| 内存泄漏 | 长时间使用 | 内存稳定 |
| 网络切换 | Wi-Fi ↔ 4G | 自动重连 |
| 后台恢复 | App 切回前台 | 状态恢复 |

## 调试技巧

### 查看网络请求日志

**Flutter (Dart)**:

```dart
// mobile/lib/core/network/api_interceptor.dart
@override
void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
  print('API Request: ${options.method} ${options.uri}');
  print('Headers: ${options.headers}');
  print('Body: ${options.data}');
  handler.next(options);
}
```

**查看日志**:
```bash
# Android
flutter logs | grep "API Request"

# iOS
flutter logs | grep "API Request"

# macOS
open -a Console
# 过滤进程: flutter
```

### 抓包调试

**使用 Charles Proxy**:

1. 安装 [Charles Proxy](https://www.charlesproxy.com/)
2. 安装 SSL 证书 (Help -> SSL Proxying -> Install Charles Root Certificate)
3. 配置代理: Proxy -> SSL Proxying Settings -> Add `*:8080`
4. 移动设备连接到同一 Wi-Fi
5. 设置设备 HTTP 代理指向开发机 IP:8888

**使用 mitmproxy**:

```bash
pip install mitmproxy
mitmproxy --listen-host 0.0.0.0 --listen-port 8080 --ssl-insecure

# 移动设备设置代理到 <开发机IP>:8080
```

### 后端日志查看

```bash
# 网关日志
docker compose logs -f sparkle_gateway

# API 日志
docker compose logs -f sparkle_api

# gRPC Agent 日志
docker compose logs -f sparkle_agent

# 过滤错误
docker compose logs sparkle_gateway | grep -i "error\|5[0-9][0-9]"
```

### 数据库查询

```bash
# 查看用户
docker exec sparkle_db psql -U postgres -d sparkle -c "
SELECT id, username, email, created_at FROM users ORDER BY created_at DESC LIMIT 5;"

# 查看 Outbox 积压
docker exec sparkle_db psql -U postgres -d sparkle -c "
SELECT COUNT(*) as pending FROM event_outbox WHERE published_at IS NULL;"

# 查看最近错误
docker exec sparkle_db psql -U postgres -d sparkle -c "
SELECT * FROM chat_messages ORDER BY created_at DESC LIMIT 5;"
```

## 常见问题排查

### Q1: Android 真机无法连接

**症状**: 网络请求超时或连接被拒绝

**检查**:
```bash
# 1. 确认后端服务运行
curl http://localhost:8080/health

# 2. 确认防火墙允许 8080 端口
# macOS: 系统偏好设置 -> 安全性与隐私 -> 防火墙

# 3. 确认 Android 设备在同一网络
# 设置 -> Wi-Fi -> 查看当前网络

# 4. 使用 adb 测试连接
adb shell ping 192.168.1.100
```

**解决方案**:
1. 确保后端监听 `0.0.0.0` 而不是 `127.0.0.1`
2. 检查 `docker-compose.yml` 端口映射:
   ```yaml
   ports:
     - "8080:8080"  # 正确
     # - "127.0.0.1:8080:8080"  # 错误，只监听本地
   ```

### Q2: iOS 真机请求失败

**症状**: `The network connection was lost`

**检查**:
1. 确认 iOS 版本 ≥ 12
2. 确认 `Info.plist` 包含 `NSLocalNetworkUsageDescription`
3. 确认 `NSAllowsLocalNetworking` = `true`

**解决方案**:
```xml
<!-- mobile/ios/Runner/Info.plist -->
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
</dict>
```

### Q3: 证书错误 (SSL)

**症状**: `CERTIFICATE_VERIFY_FAILED`

**原因**: 开发环境使用 HTTP 而不是 HTTPS

**解决方案**: 确保使用 `http://` 协议

```dart
// 错误
final apiUrl = 'https://192.168.1.100:8080';

// 正确
final apiUrl = 'http://192.168.1.100:8080';
```

### Q4: WebSocket 连接断开

**症状**: 聊天页面连接不稳定

**检查**:
```bash
# 查看网关 WebSocket 日志
docker compose logs sparkle_gateway | grep -i "websocket"
```

**解决方案**:
1. 确保 Gateway 服务稳定
2. 实现 WebSocket 自动重连
3. 添加心跳检测

### Q5: 数据迁移未应用

**症状**: `relation event_outbox does not exist`

**解决方案**:
```bash
# 重新应用迁移
docker exec sparkle_api alembic upgrade head

# 验证版本
docker exec sparkle_api alembic current
```

## 性能基准

### 启动时间

| 平台 | 冷启动 | 热启动 |
|------|--------|--------|
| Android | < 3s | < 1s |
| iOS | < 2s | < 0.5s |
| macOS | < 1.5s | < 0.3s |

### API 响应时间

| 端点 | 目标 | 实际 |
|------|------|------|
| 登录 | < 500ms | ~300ms |
| Onboarding | < 300ms | ~200ms |
| 任务创建 | < 400ms | ~250ms |
| 任务列表 | < 300ms | ~150ms |

### 内存占用

| 平台 | 空闲 | 加载时 |
|------|------|--------|
| Android | < 80MB | < 150MB |
| iOS | < 60MB | < 120MB |
| macOS | < 50MB | < 100MB |

## 测试报告模板

```markdown
## 真机联调测试报告

**测试日期**: YYYY-MM-DD
**测试人员**: [姓名]
**设备信息**:
- Android: [型号] [系统版本]
- iOS: [型号] [系统版本]
- 后端版本: [Git commit hash]

### 测试结果

| 测试项 | Android | iOS | macOS |
|--------|---------|-----|-------|
| 基础启动 | ✅ | ✅ | ✅ |
| 用户注册 | ✅ | ✅ | ✅ |
| 用户登录 | ✅ | ✅ | ✅ |
| Onboarding | ✅ | ✅ | ✅ |
| 任务创建 | ✅ | ✅ | ✅ |
| 聊天功能 | ✅ | ✅ | N/A |

### 发现问题

1. [问题描述]
   - 复现步骤:
   - 预期行为:
   - 实际行为:
   - 日志截图:

### 后续计划

- [ ] 修复问题 1
- [ ] 回归测试
- [ ] 发布版本
```

## 相关文档

- [Event Outbox 迁移](EVENT_OUTBOX_MIGRATION.md)
- [iOS 本地网络权限](IOS_LOCAL_NETWORK_PERMISSIONS.md)
- [API 配置管理](API_CONFIG_MANAGEMENT.md)

## 更新历史

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-01-30 | 1.0.0 | 初始版本，完整联调流程 |
