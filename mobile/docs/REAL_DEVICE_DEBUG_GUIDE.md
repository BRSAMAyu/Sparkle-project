# Sparkle 真机联调指南

> **项目**: Sparkle AI Learning Assistant
> **更新时间**: 2026-01-31
> **适用场景**: Flutter Android 真机调试

---

## 📋 目录

1. [环境准备](#环境准备)
2. [设备配置](#设备配置)
3. [端口映射](#端口映射)
4. [构建与安装](#构建与安装)
5. [常见问题排查](#常见问题排查)
6. [日志查看](#日志查看)
7. [LLM 调试](#llm-调试)

---

## 🔧 环境准备

### 1.1 检查开发环境

```bash
# 检查 Flutter
flutter --version
flutter doctor -v

# 检查 ADB
~/Library/Android/sdk/platform-tools/adb --version
```

### 1.2 启动后端服务

```bash
cd /Users/a/code/sparkle-flutter

# 启动基础设施（DB、Redis、MinIO）
make dev-all

# 等待服务启动
docker compose ps
```

**预期输出**:
```
sparkle_api        running
sparkle_gateway    running
sparkle_db         running
sparkle_redis      running
sparkle_minio      running
```

### 1.3 验证后端服务

```bash
# 检查网关健康状态
curl http://localhost:8080/health

# 检查 API 健康状态
curl http://localhost:8000/health
```

---

## 📱 设备配置

### 2.1 开启开发者选项

1. **设置** → **关于手机**
2. 连续点击 **版本号** 7 次
3. 返回 **设置** → **系统和更新** → **开发者人员选项**
4. 开启以下选项：
   - ✅ **USB 调试**
   - ✅ **USB 安装**（重要！）
   - ✅ **仅充电模式下允许 ADB 调试**（可选）

### 2.2 连接设备

```bash
# 检查设备连接
~/Library/Android/sdk/platform-tools/adb devices

# 预期输出
# List of devices attached
# 95db2f70    device
```

### 2.3 配置 Wi-Fi

确保设备和 Mac 在 **同一 Wi-Fi 网络**。

```bash
# 查看 Mac 的 IP 地址
ipconfig getifaddr en0
# 示例输出: 192.168.31.51
```

---

## 🌐 端口映射

### 3.1 ADB Reverse 推荐方案

**推荐使用 ADB Reverse**，无需修改代码即可使用 localhost：

```bash
# 映射网关端口
~/Library/Android/sdk/platform-tools/adb reverse tcp:8080 tcp:8080

# 验证映射
~/Library/Android/sdk/platform-tools/adb reverse --list
# 预期输出: UsbFfs tcp:8080 tcp:8080
```

### 3.2 备选方案：局域网 IP

如果 ADB Reverse 不可用，使用局域网 IP：

```bash
# 构建时指定设备 URL
flutter build apk --debug \
  --dart-define=ANDROID_DEVICE_URL=http://192.168.31.51:8080
```

**注意**: 需要将 `api_constants.dart` 中的默认 URL 改为局域网 IP。

---

## 🔨 构建与安装

### 4.1 构建 APK

```bash
cd /Users/a/code/sparkle-flutter/mobile

# Debug 构建（推荐用于调试）
flutter build apk --debug

# Release 构建（性能测试）
flutter build apk --release
```

### 4.2 安装到设备

```bash
# 首次安装
~/Library/Android/sdk/platform-tools/adb install \
  build/app/outputs/flutter-apk/app-debug.apk

# 替换已有安装（加 -r 参数）
~/Library/Android/sdk/platform-tools/adb install -r \
  build/app/outputs/flutter-apk/app-debug.apk
```

### 4.3 启动应用

在设备上手动点击 Sparkle 应用图标启动。

---

## 🐛 常见问题排查

### 5.1 APK 安装失败

**错误**: `INSTALL_FAILED_USER_RESTRICTED`

**解决方案**:
1. 检查开发者选项中 **USB 安装** 是否开启
2. 在设备上允许 USB 调试授权
3. 如果仍失败，使用 pm install 绕过：

```bash
~/Library/Android/sdk/platform-tools/adb shell pm install \
  -r /data/local/tmp/app-debug.apk

# 先推送到设备
~/Library/Android/sdk/platform-tools/adb push \
  build/app/outputs/flutter-apk/app-debug.apk \
  /data/local/tmp/app-debug.apk
```

### 5.2 网络连接失败

**症状**: 应用显示 "网络错误" 或 "连接失败"

**排查步骤**:

```bash
# 1. 检查端口映射
~/Library/Android/sdk/platform-tools/adb reverse --list

# 2. 测试网关连接
curl http://localhost:8080/health

# 3. 查看 Gateway 日志
docker logs sparkle_gateway --tail 50

# 4. 查看是否有认证错误
docker logs sparkle_gateway | grep "Auth"
```

### 5.3 WebSocket 连接失败

**症状**: 聊天页面无法发送消息

**检查清单**:

```bash
# 1. 确认 WebSocket 连接
docker logs sparkle_gateway | grep "WebSocket connected"

# 2. 检查端口映射
~/Library/Android/sdk/platform-tools/adb reverse --list | grep 8080

# 3. 重新映射（如果丢失）
~/Library/Android/sdk/platform-tools/adb reverse tcp:8080 tcp:8080

# 4. 重启应用（设备上完全关闭后重新打开）
```

### 5.4 登录失败

**错误**: "Login failed" 或 401 Unauthorized

**排查**:

```bash
# 1. 检查用户是否存在
docker exec sparkle_db psql -U sparkle -c \
  "SELECT username, email FROM users WHERE username = 'device_test_user';"

# 2. 检查后端日志
docker logs sparkle_api | grep -i "login\|auth"

# 3. 测试登录 API
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "device_test_user", "password": "DeviceTest123"}'
```

**测试账户**:
- 用户名: `device_test_user`
- 密码: `DeviceTest123`

### 5.5 LLM 无响应

**症状**: 发送消息后 UI 卡住，无 AI 回复

**检查流程**:

```bash
# 1. 检查 WebSocket 消息是否到达网关
docker logs sparkle_gateway --since 1m | grep -E "message|ReadMessage"

# 2. 检查 gRPC 连接
docker logs sparkle_api | grep -i "grpc\|streamchat"

# 3. 检查 LLM 配置
grep "LLM_PROVIDER\|LLM_API_KEY" backend/.env

# 4. 查看 Orchestrator 日志
docker logs sparkle_api | grep -i "orchestrator\|sufficiency"
```

### 5.6 消息显示溢出

**症状**: 长消息无法正确显示

**解决方案**: 已在 `chat_bubble.dart` 中修复，长消息会限制在屏幕高度的 50% 并可滚动。

---

## 📊 日志查看

### 6.1 网关日志

```bash
# 实时监控
docker logs -f sparkle_gateway

# 查看最近 100 行
docker logs sparkle_gateway --tail 100

# 查看最近 5 分钟
docker logs sparkle_gateway --since 5m

# 过滤 WebSocket 相关
docker logs sparkle_gateway | grep -i "websocket\|connected\|message"

# 过滤错误
docker logs sparkle_gateway | grep -i "error"
```

### 6.2 API 日志

```bash
# 实时监控
docker logs -f sparkle_api

# 查看聊天请求
docker logs sparkle_api | grep -i "chat\|stream"

# 查看错误
docker logs sparkle_api | grep -i "error\|exception\|traceback"

# 查看数据库查询
docker logs sparkle_api | grep "SELECT\|INSERT\|UPDATE"
```

### 6.3 组合日志查看

```bash
# 同时查看网关和 API
docker logs sparkle_gateway --tail 50 &
docker logs sparkle_api --tail 50
```

---

## 🤖 LLM 调试

### 7.1 LLM 配置检查

```bash
# 查看当前 LLM 配置
grep -E "^LLM_|^DASHSCOPE_|^ZHIPU_" /Users/a/code/sparkle-flutter/backend/.env
```

**预期配置**:
```
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=sk-xxxxx
DASHSCOPE_CHAT_MODEL=qwen-plus
```

### 7.2 测试 LLM 连接

```bash
# 进入 API 容器
docker exec -it sparkle_api bash

# 测试 LLM 调用（Python）
python << 'EOF'
import os
from app.services.llm_service import llm_service

async def test():
    response = await llm_service.chat(
        messages=[{"role": "user", "content": "你好"}],
        model="qwen-plus"
    )
    print(response)

import asyncio
asyncio.run(test())
EOF
```

### 7.3 查看完整聊天链路

```bash
# 在一个终端监控网关
docker logs -f sparkle_gateway | grep -v "Auth token"

# 在另一个终端监控 API
docker logs -f sparkle_api | grep -E "StreamChat|orchestrator|message"

# 发送测试消息后观察日志流
```

### 7.4 Orchestrator 状态机调试

```bash
# 查看 sufficiency check
docker logs sparkle_api | grep "sufficiency"

# 查看队列处理
docker logs sparkle_api | grep "queue\|Draining"

# 查看 tool 调用
docker logs sparkle_api | grep "tool\|function"
```

---

## 🔑 关键文件位置

### Flutter 关键文件

```
mobile/lib/
├── core/
│   ├── constants/
│   │   └── api_constants.dart          # API URL 配置
│   └── network/
│       ├── api_client.dart              # HTTP 客户端
│       └── api_interceptor.dart         # 请求拦截器
├── features/
│   ├── auth/
│   │   └── presentation/
│   │       └── providers/auth_provider.dart  # 认证状态管理
│   ├── chat/
│   │   ├── data/
│   │   │   ├── repositories/
│   │   │   │   ├── chat_repository.dart       # 聊天数据仓库
│   │   │   │   └── task_repository.dart       # 任务数据仓库
│   │   │   └── services/
│   │   │       └── websocket_chat_service_v2.dart  # WebSocket 服务
│   │   └── presentation/
│   │       ├── providers/
│   │       │   └── chat_provider.dart       # 聊天状态管理
│   │       └── widgets/
│   │           ├── chat_input.dart         # 输入框组件
│   │           └── chat_bubble.dart        # 消息气泡
│   └── task/
│       └── presentation/
│           └── screens/
│             └── task_create_screen.dart   # 任务创建页面
```

### 后端关键文件

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py                    # 认证 API
│   │       ├── chat.py                    # 聊天 API
│   │       └── tasks.py                   # 任务 API
│   ├── orchestration/
│   │   └── orchestrator.py                # 对话编排器
│   └── services/
│       ├── llm_service.py                # LLM 服务
│       └── agent_grpc_service.py         # gRPC 服务
└── gateway/
    └── internal/
        └── handler/
            └── chat_orchestrator.go       # Go 网关聊天处理
```

---

## 🚀 快速调试流程

### 场景 1: 登录功能

```bash
# 1. 确认服务运行
docker compose ps

# 2. 检查端口映射
~/Library/Android/sdk/platform-tools/adb reverse --list

# 3. 查看登录日志
docker logs sparkle_api | grep -i "login\|auth" | tail -20

# 4. 测试登录 API
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "device_test_user", "password": "DeviceTest123"}'
```

### 场景 2: 聊天功能

```bash
# 1. 检查 WebSocket 连接
docker logs sparkle_gateway | grep "WebSocket connected" | tail -5

# 2. 监控消息流（一边发送消息一边查看）
docker logs -f sparkle_gateway | grep -v "Auth token\|GET /api/v1/tasks"

# 3. 检查 gRPC 调用
docker logs sparkle_api | grep -i "streamchat\|grpc" | tail -20

# 4. 查看 Orchestrator 日志
docker logs sparkle_api | grep -i "orchestrator" | tail -30
```

### 场景 3: 任务创建

```bash
# 1. 监控任务创建请求
docker logs sparkle_api | grep -i "create.*task\|POST.*tasks"

# 2. 查看错误
docker logs sparkle_api | grep -i "error\|validation"

# 3. 检查数据库
docker exec sparkle_db psql -U sparkle -c \
  "SELECT * FROM tasks ORDER BY created_at DESC LIMIT 5;"
```

---

## 📱 设备上的调试

### 查看 Flutter 日志

如果需要查看设备上的 Flutter 日志：

```bash
# 查看 Android 日志
~/Library/Android/sdk/platform-tools/adb logcat

# 过滤 Sparkle 应用
~/Library/Android/sdk/platform-tools/adb logcat | grep "sparkle"

# 过滤 WebSocket 日志
~/Library/Android/sdk/platform-tools/adb logcat | grep -i "ws\|websocket"
```

### 截图和录屏

```bash
# 截图
~/Library/Android/sdk/platform-tools/adb shell screencap -p \
  /sdcard/screen.png
~/Library/Android/sdk/platform-tools/adb pull \
  /sdcard/screen.png

# 录屏（需要 Android 4.4+）
~/Library/Android/sdk/platform-tools/adb shell screenrecord /sdcard/demo.mp4
# 按 Ctrl+C 停止录制
~/Library/Android/sdk/platform-tools/adb pull /sdcard/demo.mp4
```

---

## 🔧 环境重置

### 完全重置步骤

```bash
# 1. 停止所有服务
docker compose down

# 2. 清理数据卷（可选，会清除数据库）
docker compose down -v

# 3. 重新启动
make dev-all

# 4. 等待服务就绪
docker compose ps

# 5. 重新映射端口
~/Library/Android/sdk/platform-tools/adb reverse tcp:8080 tcp:8080

# 6. 重新构建并安装 APK
cd mobile
flutter clean
flutter build apk --debug
~/Library/Android/sdk/platform-tools/adb install -r \
  build/app/outputs/flutter-apk/app-debug.apk
```

---

## 📞 获取帮助

### 收集诊断信息

遇到问题时，收集以下信息：

```bash
# 1. 系统信息
flutter doctor -v > ~/Desktop/flutter_doctor.txt
~/Library/Android/sdk/platform-tools/adb devices > ~/Desktop/adb_devices.txt

# 2. 网关日志
docker logs sparkle_gateway --tail 500 > ~/Desktop/gateway_logs.txt

# 3. API 日志
docker logs sparkle_api --tail 500 > ~/Desktop/api_logs.txt

# 4. 环境配置
cat /Users/a/code/sparkle-flutter/backend/.env > ~/Desktop/env_config.txt

# 5. 设备截图
~/Library/Android/sdk/platform-tools/adb shell screencap -p \
  /sdcard/error_screen.png
~/Library/Android/sdk/platform-tools/adb pull /sdcard/error_screen.png \
  ~/Desktop/error_screen.png
```

### 常用调试命令速查

```bash
# 快速检查服务状态
docker compose ps

# 快速查看最近错误
docker logs sparkle_gateway --tail 100 | grep -i error
docker logs sparkle_api --tail 100 | grep -i error

# 快速重启服务
docker compose restart sparkle_gateway sparkle_api

# 快速重新安装 APK
flutter build apk --debug && \
  ~/Library/Android/sdk/platform-tools/adb install -r \
  build/app/outputs/flutter-apk/app-debug.apk

# 快速检查端口映射
~/Library/Android/sdk/platform-tools/adb reverse --list

# 快速查看 WebSocket 连接
docker logs sparkle_gateway | grep "WebSocket" | tail -10
```

---

## ✅ 调试检查清单

在报告问题前，请确认：

- [ ] 设备已连接并授权 USB 调试
- [ ] ADB reverse 端口映射已设置
- [ ] Docker 服务全部运行
- [ ] 使用测试账户登录成功
- [ ] 已查看相关日志（网关/API）
- [ ] 已尝试重启应用和服务
- [ ] 已收集截图和错误信息

---

**文档版本**: 1.0.0
**最后更新**: 2026-01-31
**维护者**: Claude Code
