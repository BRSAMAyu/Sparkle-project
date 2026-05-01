# 科大讯飞语音转文字快速开始指南

## 🚀 快速开始

### 1. 获取科大讯飞API密钥

1. 访问 [科大讯飞开放平台](https://www.xfyun.cn/)
2. 注册账号并登录
3. 进入控制台，创建应用
4. 获取API Key和API Secret

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp backend/.env.example backend/.env

# 编辑环境变量文件
vim backend/.env
```

在`.env`文件中添加以下配置：

```bash
# STT服务选择
STT_PROVIDER=xunfei

# 科大讯飞API配置
XUNFEI_API_KEY=your_xunfei_key
XUNFEI_API_SECRET=your_xunfei_secret
XUNFEI_STT_DOMAIN=iat
XUNFEI_STT_LANGUAGE=zh-CN
XUNFEI_STT_SAMPLE_RATE=16000
XUNFEI_STT_EOS_MS=6000
```

### 3. 安装依赖

#### Python后端
```bash
cd backend
pip install websockets
```

#### Flutter移动端
```bash
cd mobile
flutter pub get
```

### 4. 启动服务

```bash
# 启动所有服务（Go网关、Python后端、数据库、Redis等）
make dev-all

# 或者分别启动
make gateway-dev      # Go网关
make grpc-server      # Python gRPC服务
```

### 5. 运行移动端

```bash
cd mobile
flutter run
```

## 🎯 使用方法

### 在聊天界面使用语音输入

1. 打开任意对话框
2. 长按语音输入按钮（麦克风图标）
3. 说话（支持中英文混合）
4. 松开按钮停止录音
5. 语音识别结果会自动填入文本框
6. 可编辑后发送

### 录音状态说明

- **灰色麦克风**: 空闲状态，点击开始录音
- **蓝色麦克风 + 时长**: 正在录音，显示录制时长
- **旋转圆圈**: 正在处理语音识别
- **错误提示**: 录音或识别失败时显示错误信息

## 🔧 配置说明

### 科大讯飞参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `XUNFEI_API_KEY` | 科大讯飞API密钥 | 必填 |
| `XUNFEI_API_SECRET` | 科大讯飞API密钥 | 必填 |
| `XUNFEI_STT_DOMAIN` | 语音识别领域 | `iat` |
| `XUNFEI_STT_LANGUAGE` | 目标语言 | `zh-CN` |
| `XUNFEI_STT_SAMPLE_RATE` | 采样率（Hz） | `16000` |
| `XUNFEI_STT_EOS_MS` | 静音检测阈值（毫秒） | `6000` |

## 🐛 常见问题

### 1. 录音权限被拒绝

**问题**: 提示"没有麦克风权限"

**解决**:
1. 检查系统设置中是否授予麦克风权限
2. iOS: 设置 → Sparkle → 麦克风 → 开启
3. Android: 设置 → 应用 → Sparkle → 权限 → 麦克风 → 允许

### 2. 科大讯飞API调用失败

**问题**: 提示"科大讯飞语音识别失败"

**解决**:
1. 检查`.env`文件中的API密钥是否正确
2. 检查网络连接是否正常
3. 检查科大讯飞账户余额是否充足
4. 查看后端日志获取详细错误信息

### 3. 语音识别准确率低

**问题**: 识别结果不准确

**解决**:
1. 确保在安静环境中录音
2. 说话清晰，语速适中
3. 检查`XUNFEI_STT_EOS_MS`参数，调整静音检测阈值

### 4. 音频格式问题

**问题**: 不同平台音频格式不兼容

**解决**:
1. 确保使用16kHz采样率
2. 确保使用PCM格式
3. 检查移动端的`record`包配置

## 📊 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 录音延迟 | < 100ms | 从开始录音到发送第一帧音频 |
| 转写响应时间 | < 2s | 首段识别结果返回时间 |
| 识别准确率 | > 90% | 中文语音识别准确率 |
| 内存使用 | < 100MB | 音频录制和处理内存占用 |
| 网络流量 | < 100KB/s | 音频流传输带宽 |

## 🔍 调试技巧

### 查看后端日志

```bash
# 查看Python服务日志
docker compose logs -f grpc-server

# 查看Go网关日志
docker compose logs -f gateway
```

### 查看移动端日志

```bash
# Android
adb logcat | grep "Flutter"

# iOS
# 在Xcode中查看日志
```

### 测试科大讯飞API

```bash
# 使用curl测试API（需要先获取鉴权URL）
curl -X POST "https://iat.xf-yun.com/v1/iat" \
  -H "Authorization: YOUR_AUTHORIZATION" \
  -H "Date: YOUR_DATE" \
  -H "Host: iat.xf-yun.com" \
  -d "audio_data"
```

## 📝 开发注意事项

### 1. 音频格式
- 确保输出纯净的PCM格式（16kHz, 16bit, Little Endian）
- 不同平台可能需要不同的音频格式处理

### 2. 安全性
- API密钥必须存储在后端，绝不暴露在移动端
- 使用HTTPS/WSS连接
- 实现适当的错误处理和重试机制

### 3. 用户体验
- 录音状态可视化
- 实时转写反馈
- 清晰的错误提示
- 权限申请引导

### 4. 性能优化
- 避免过度缓冲
- 实现VAD（静音检测）
- 合理的超时设置
- 内存使用优化

## 📚 更多资源

- [完整技术文档](STT_INTEGRATION_SUMMARY.md)
- [科大讯飞API文档](https://www.xfyun.cn/doc/asr/iat/doc.html)
- [Flutter record包文档](https://pub.dev/packages/record)
- [WebSocket协议](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

---

**版本**: 1.0.0
**更新时间**: 2026-01-21
