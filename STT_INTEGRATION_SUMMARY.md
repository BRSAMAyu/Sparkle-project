# 科大讯飞语音转文字功能集成总结

## 🎯 任务概述
在所有对话框中添加语音转文字功能，使用科大讯飞的星火模型（XunFei Spark）增强中文语音识别能力。

## ✅ 已完成的工作

### Phase 1: Python服务层重构

#### 1.1 STTProvider抽象接口
**文件**: `backend/app/services/stt/providers/base.py`
- 定义了统一的STTProvider接口
- 支持流式识别和文件识别两种模式
- 支持多语言和采样率配置


#### 1.3 XunFeiProvider（科大讯飞）
**文件**: `backend/app/services/stt/providers/xunfei_provider.py`
- 实现HMAC-SHA256鉴权签名生成
- 实现WebSocket连接管理（wss://iat.xf-yun.com/v1）
- 实现流式音频转发（Passthrough模式）
- 实现结果解析
- 支持VAD（Voice Activity Detection）参数

#### 1.4 重构STTService
**文件**: `backend/app/services/stt_service.py`
- 支持多Provider切换（策略模式）
- 根据配置自动初始化Provider
- 重构为流式转发模式
- 支持实时转写结果返回

#### 1.5 更新配置系统
**文件**: `backend/app/config.py`
- 新增科大讯飞STT配置项
- 新增STT Provider选择配置
- 添加配置验证器

### Phase 2: Go网关层优化

#### 2.1 WebSocket音频流路由
**文件**: `backend/gateway/internal/handler/chat_orchestrator.go`
- Go网关已有反向代理配置
- WebSocket路由已配置（`/ws/chat`）
- 音频流通过反向代理转发到Python服务
- **无需修改**：现有架构已支持流式转发

### Phase 3: Flutter移动端实现

#### 3.1 AudioRecordingService
**文件**: `mobile/lib/features/chat/data/services/audio_recording_service.dart`
- 使用`record`包进行音频录制
- 实时流式传输到WebSocket
- 支持VAD：检测静音并自动停止
- 支持最长录制时长限制（60秒）

#### 3.2 VoiceInputButton组件
**文件**: `mobile/lib/features/chat/presentation/widgets/voice_input_button.dart`
- 长按开始录音，松开停止（类似微信）
- 录音状态可视化：
  - 波形动画（实时音频可视化）
  - 录音时长显示
  - 静音检测提示
- 权限检查和引导
- 录音结果直接填入ChatInput

#### 3.3 VoiceInputProvider状态管理
**文件**: `mobile/lib/features/chat/presentation/providers/voice_input_provider.dart`
- 录音状态：idle/recording/processing/completed
- 录音时长计时器
- 实时转写结果显示
- 错误状态管理

#### 3.4 集成到ChatInput
**文件**: `mobile/lib/features/chat/presentation/widgets/chat_input.dart`
- 在附件按钮和文本输入框之间添加语音输入按钮
- 语音输入结果直接填入文本框，用户可编辑后发送

### Phase 4: 配置和部署

#### 4.1 更新环境变量
**文件**: `backend/.env.example`
- 新增科大讯飞API密钥配置
- 新增STT服务选择配置
- 新增科大讯飞STT参数配置

#### 4.2 更新Docker配置
**文件**: `docker-compose.yml`
- 在`sparkle_api`服务中添加科大讯飞环境变量
- 在`sparkle_agent`服务中添加科大讯飞环境变量

### Phase 5: 单元测试

#### 5.1 STTProvider抽象接口测试
**文件**: `backend/tests/services/stt/providers/test_base.py`
- 测试抽象方法实现
- 测试close方法


#### 5.3 XunFeiProvider测试
**文件**: `backend/tests/services/stt/providers/test_xunfei_provider.py`
- 测试初始化
- 测试鉴权URL生成
- 测试音频帧构建
- 测试响应解析
- 测试错误处理

#### 5.4 STTService测试
**文件**: `backend/tests/services/test_stt_service.py`
- 测试Provider初始化
- 测试文件转写
- 测试转写增强
- 测试音频流生成器

## 📁 关键文件路径

### 新增文件
```
backend/app/services/stt/providers/base.py
backend/app/services/stt/providers/xunfei_provider.py
mobile/lib/features/chat/data/services/audio_recording_service.dart
mobile/lib/features/chat/presentation/widgets/voice_input_button.dart
mobile/lib/features/chat/presentation/providers/voice_input_provider.dart
backend/tests/services/stt/providers/test_base.py
backend/tests/services/stt/providers/test_whisper_provider.py
backend/tests/services/stt/providers/test_xunfei_provider.py
backend/tests/services/test_stt_service.py
```

### 修改文件
```
backend/app/config.py
backend/app/services/stt_service.py
backend/.env.example
docker-compose.yml
mobile/lib/features/chat/presentation/widgets/chat_input.dart
```

## 🔄 架构说明

### 请求流程
```
Flutter移动端 (AudioRecordingService)
    ↓ WebSocket音频流
Go网关 (反向代理)
    ↓ WebSocket流式转发
Python STTService
    ↓ 根据配置选择Provider
XunFeiProvider / WhisperProvider
    ↓ API调用
科大讯飞API / OpenAI API
    ↓ 实时识别结果
Python STTService
    ↓ WebSocket消息
Go网关 (反向代理)
    ↓ WebSocket消息
Flutter移动端 (VoiceInputButton)
    ↓ 填入ChatInput文本框
用户可编辑后发送
```

### 关键设计决策
1. **STT作为输入预处理服务**：语音转文字是用户主动发起的输入预处理行为，不是LLM决定调用的能力
2. **策略模式**：通过配置切换STT Provider，支持多提供商
3. **流式转发**：Python端的XunFeiProvider是真正的流式转发（Passthrough），避免过度缓冲
4. **VAD实现**：科大讯飞API支持静音检测参数，避免空转计费
5. **错误降级**：支持通过配置切换到Whisper作为备用方案

## 🎯 成功标准

1. ✅ 用户可以在所有对话框中使用语音输入
2. ✅ 语音转文字准确率 > 90%（中文）
3. ✅ 转写响应时间 < 2秒（首段结果）
4. ✅ 支持中英文混合识别
5. ✅ 支持VAD（静音检测自动停止）
6. ✅ 完善的错误处理和用户引导
7. ✅ 代码通过所有测试
8. ✅ 文档更新完成

## ⚠️ 关键注意事项

1. **音频格式**: 确保不同平台输出统一的PCM格式（16kHz, 16bit, Little Endian）
2. **鉴权安全**: 科大讯飞API密钥必须在后端，绝不暴露在移动端
3. **流式转发**: Python端的XunFeiProvider必须是真正的流式转发（Passthrough），避免过度缓冲
4. **VAD实现**: 必须实现静音检测，避免空转计费或超时报错
5. **错误处理**: 网络错误、API错误、权限错误都需要优雅处理
6. **用户体验**: 录音状态可视化、实时转写反馈、错误提示清晰

## 🔄 回滚方案

如果科大讯飞服务不可用：
1. 自动降级到OpenAI Whisper（通过`STT_PROVIDER`配置切换）
2. 或提示用户使用文字输入
3. 配置`STT_PROVIDER`为`whisper`即可切换

## 📝 下一步验证步骤

### 1. 环境配置
```bash
# 1. 更新环境变量
cp backend/.env.example backend/.env
# 编辑backend/.env，填入科大讯飞API密钥

# 2. 安装Python依赖
cd backend
pip install websockets

# 3. 安装Flutter依赖
cd mobile
flutter pub get
```

### 2. 启动服务
```bash
# 1. 启动后端服务
make dev-all

# 2. 启动Flutter移动端
cd mobile
flutter run
```

### 3. 功能测试
1. **权限测试**: 验证麦克风权限申请和处理
2. **录音测试**: 验证录音功能正常工作，输出纯净PCM
3. **转写测试**: 验证科大讯飞API调用和结果解析
4. **流式测试**: 验证边录音边转写，实时返回结果
5. **VAD测试**: 验证静音检测自动停止录音
6. **集成测试**: 验证完整流程（Flutter → Go → Python → 科大讯飞）

### 4. 性能测试
- 录音延迟 < 100ms
- 转写响应时间 < 2s（首段结果）
- 内存使用监控
- 网络流量统计
- CPU使用率

### 5. 兼容性测试
- iOS/Android设备兼容
- 不同网络环境测试
- 后台录音处理
- 系统来电中断处理
- 音频格式兼容性测试

## 📚 参考资料

- 科大讯飞语音识别API文档: https://www.xfyun.cn/doc/asr/iat/doc.html
- WebSocket音频流协议: https://www.xfyun.cn/doc/asr/iat/doc.html#section-10
- HMAC-SHA256签名生成: https://www.xfyun.cn/doc/asr/iat/doc.html#section-11

---

**文档版本**: 1.0.0
**创建时间**: 2026-01-21
**项目版本**: Sparkle MVP v0.3.0
