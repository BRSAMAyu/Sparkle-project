# ASR 与文档清洗 API 文档

## 概述

本文档描述 Sparkle 项目中两个核心功能的 API 使用方法：
- **ASR (Automatic Speech Recognition)**: 语音转文字服务
- **文档清洗 (Document Cleaning)**: 文档解析与 OCR 功能

---

## 一、ASR 语音转文字服务

### 1.1 服务配置

ASR 服务支持以下配置（通过环境变量）：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `STT_PROVIDER` | `zhipu` | 语音识别提供商（目前仅支持 `zhipu`） |
| `STT_ENHANCE_ENABLED` | `true` | 是否启用文本增强（标点、分段） |

**注意**: `xunfei` 提供商已废弃，系统会自动迁移到 `zhipu`。

### 1.2 WebSocket 流式转写

#### 连接端点
```
ws://localhost:8080/ws/asr
```

#### 认证方式
在连接 URL 中携带 JWT Token：
```
ws://localhost:8080/ws/asr?token=<your_jwt_token>
```

#### 消息格式

**客户端 → 服务端：音频数据**
```json
{
  "type": "audio",
  "data": "<base64_encoded_audio>",
  "sample_rate": 16000,
  "format": "pcm"
}
```

**服务端 → 客户端：转写结果**
```json
{
  "type": "transcript",
  "text": "转写的文字内容",
  "is_final": false,
  "confidence": 0.95
}
```

**服务端 → 客户端：错误信息**
```json
{
  "type": "error",
  "code": "AUDIO_TOO_LARGE",
  "message": "音频数据超过限制"
}
```

#### 连接流程

1. 客户端建立 WebSocket 连接
2. 发送音频数据块（建议每次 100-500ms 音频）
3. 接收实时转写结果
4. 发送 `{"type": "end"}` 结束会话
5. 接收最终转写结果

### 1.3 REST API 文件转写

#### 请求
```bash
POST /api/v1/asr/transcribe
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <audio_file>
language: zh-CN (可选)
```

#### 响应
```json
{
  "text": "完整转写文本",
  "duration_seconds": 5.2,
  "confidence": 0.92
}
```

### 1.4 错误码

| 错误码 | 说明 |
|--------|------|
| `AUDIO_TOO_LARGE` | 音频数据超过大小限制 |
| `UNSUPPORTED_FORMAT` | 不支持的音频格式 |
| `CONNECTION_TIMEOUT` | WebSocket 连接超时 |
| `RECOGNITION_FAILED` | 语音识别失败 |
| `UNAUTHORIZED` | 未授权访问 |

### 1.5 支持的音频格式

- PCM (raw audio, 16kHz, 16-bit, mono)
- WAV (推荐)
- M4A/AAC
- MP3 (需转码)

### 1.6 限制

- 单次音频最大时长：60 秒
- WebSocket 连接超时：30 秒无活动
- 最大并发连接数：10

---

## 二、文档清洗服务

### 2.1 支持的文件格式

| 格式 | 扩展名 | OCR 支持 |
|------|--------|----------|
| PDF | `.pdf` | ✅ |
| Word | `.docx` | N/A |
| PowerPoint | `.pptx` | N/A |
| JPEG | `.jpg`, `.jpeg` | ✅ (必须) |
| PNG | `.png` | ✅ (必须) |
| WebP | `.webp` | ✅ (必须) |
| GIF | `.gif` | ✅ (必须) |

### 2.2 REST API

#### 启动清洗任务

```bash
POST /api/v1/documents/clean
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <document_file>
options: {
  "enable_ocr": true,
  "ocr_engine": "zhipu"
}
```

**参数说明：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable_ocr` | boolean | `true` | 是否启用 OCR |
| `ocr_engine` | string | `zhipu` | OCR 引擎（`zhipu` 或 `local`） |

**响应：**
```json
{
  "task_id": "task-abc123",
  "status": "queued",
  "message": "任务已创建"
}
```

#### 查询任务状态

```bash
GET /api/v1/documents/clean/{task_id}
Authorization: Bearer <token>
```

**响应：**
```json
{
  "task_id": "task-abc123",
  "status": "completed",
  "percent": 100,
  "message": "处理完成",
  "result": {
    "summary": "清洗后的文本内容...",
    "char_count": 1234,
    "mode": "full",
    "full_text_preview": "前500字符预览..."
  }
}
```

#### 任务状态说明

| 状态 | 说明 |
|------|------|
| `queued` | 等待处理 |
| `processing` | 正在处理 |
| `completed` | 处理完成 |
| `failed` | 处理失败 |

### 2.3 OCR 引擎对比

| 引擎 | 优点 | 缺点 | 推荐场景 |
|------|------|------|----------|
| `zhipu` (GLM OCR) | 高精度、支持复杂排版 | 需要网络、有配额限制 | 扫描件、手写内容 |
| `local` (Tesseract) | 离线可用、无配额限制 | 精度较低 | 清晰印刷文档 |

### 2.4 文件大小限制

| 格式 | 最大大小 |
|------|----------|
| PDF | 50 MB |
| DOCX | 20 MB |
| PPTX | 20 MB |
| 图片 | 10 MB |

### 2.5 错误码

| HTTP 状态码 | 错误信息 | 说明 |
|-------------|----------|------|
| 400 | `INVALID_FILE_TYPE` | 不支持的文件类型 |
| 400 | `FILE_TOO_LARGE` | 文件超过大小限制 |
| 400 | `INVALID_MAGIC_BYTES` | 文件头与扩展名不匹配 |
| 401 | `UNAUTHORIZED` | 未授权访问 |
| 413 | `PAYLOAD_TOO_LARGE` | 请求体过大 |
| 500 | `PROCESSING_FAILED` | 处理失败 |
| 501 | `DEPENDENCY_MISSING` | 依赖未安装（如 Pillow） |

---

## 三、安全机制

### 3.1 魔数验证

文档清洗服务会验证文件的实际格式，防止：
- 扩展名伪装攻击
- 恶意文件上传

支持的魔数检测：
- PDF: `%PDF-`
- Office 文档 (ZIP): `PK\x03\x04`
- PNG: `\x89PNG\r\n\x1a\n`
- JPEG: `\xFF\xD8\xFF`
- GIF: `GIF87a` 或 `GIF89a`
- WebP: `RIFF....WEBP`

### 3.2 认证要求

所有 API 请求需要携带有效的 JWT Token：
```
Authorization: Bearer <token>
```

Token 有效期由 `ACCESS_TOKEN_EXPIRE_MINUTES` 配置（默认 1440 分钟）。

---

## 四、最佳实践

### 4.1 ASR 使用建议

1. **音频质量**：使用 16kHz 采样率、单声道录制
2. **网络环境**：确保稳定的网络连接，避免丢包
3. **分段发送**：每 100-500ms 发送一次音频数据
4. **静音检测**：长时间静音时暂停发送，节省带宽

### 4.2 文档清洗建议

1. **OCR 选择**：
   - 扫描件、照片：使用 `zhipu` 引擎
   - 清晰 PDF：可关闭 OCR 加快处理
2. **文件预处理**：
   - 图片建议先压缩到 2MB 以内
   - PDF 建议去除不必要的图片层
3. **轮询间隔**：任务状态查询建议间隔 1-2 秒

---

## 五、示例代码

### 5.1 Flutter ASR 示例

```dart
import 'package:web_socket_channel/web_socket_channel.dart';

class AsrService {
  WebSocketChannel? _channel;

  void startTranscription(String token, Function(String) onResult) {
    _channel = WebSocketChannel.connect(
      Uri.parse('ws://localhost:8080/ws/asr?token=$token'),
    );

    _channel!.stream.listen((event) {
      final data = jsonDecode(event);
      if (data['type'] == 'transcript') {
        onResult(data['text']);
      }
    });
  }

  void sendAudio(Uint8List audioData) {
    _channel?.sink.add(jsonEncode({
      'type': 'audio',
      'data': base64Encode(audioData),
      'sample_rate': 16000,
    }));
  }

  void stopTranscription() {
    _channel?.sink.add(jsonEncode({'type': 'end'}));
  }
}
```

### 5.2 文档清洗示例

```dart
import 'package:dio/dio.dart';

Future<CleaningResult> cleanDocument(File file, {bool enableOcr = true}) async {
  final dio = Dio();
  final formData = FormData.fromMap({
    'file': await MultipartFile.fromFile(file.path),
    'options': jsonEncode({
      'enable_ocr': enableOcr,
      'ocr_engine': 'zhipu',
    }),
  });

  // 启动任务
  final response = await dio.post(
    '/api/v1/documents/clean',
    data: formData,
  );
  final taskId = response.data['task_id'];

  // 轮询结果
  while (true) {
    await Future.delayed(Duration(seconds: 1));
    final statusResponse = await dio.get('/api/v1/documents/clean/$taskId');
    final status = statusResponse.data['status'];

    if (status == 'completed') {
      return CleaningResult.fromJson(statusResponse.data['result']);
    } else if (status == 'failed') {
      throw Exception(statusResponse.data['message']);
    }
  }
}
```

---

## 六、gRPC Proto 定义

### 6.1 Proto 文件位置

ASR 服务的 gRPC 接口定义位于：
```
proto/stt_service.proto
```

### 6.2 服务定义

```protobuf
service STTService {
  // 流式语音转文字（双向流）
  rpc StreamSpeechToText(stream AudioChunk) returns (stream TranscriptionResult);

  // 文件转写（批量处理）
  rpc TranscribeAudio(TranscribeRequest) returns (TranscribeResponse);

  // 文本增强（LLM 后处理）
  rpc EnhanceTranscript(EnhanceRequest) returns (EnhanceResponse);
}
```

### 6.3 核心消息类型

#### AudioChunk（音频数据块）
| 字段 | 类型 | 说明 |
|------|------|------|
| `data` | bytes | 音频二进制数据 |
| `sample_rate` | int32 | 采样率 (Hz) |
| `format` | string | 格式: "pcm", "opus", "wav" |
| `language` | string | 语言代码: "zh-CN", "en-US" |
| `end_of_stream` | bool | 是否结束流 |

#### TranscriptionResult（转写结果）
| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | 转写文本 |
| `is_final` | bool | 是否为最终结果 |
| `confidence` | float | 置信度 (0.0-1.0) |
| `session_id` | string | 会话 ID |
| `error` | TranscriptionError | 错误信息（如有） |

#### TranscribeRequest（文件转写请求）
| 字段 | 类型 | 说明 |
|------|------|------|
| `audio_data` | bytes | 音频文件内容 |
| `filename` | string | 文件名 |
| `language` | string | 语言代码 |
| `enable_enhancement` | bool | 是否启用增强 |

### 6.4 生成代码

运行以下命令生成 Go/Python/Dart 代码：
```bash
make proto-gen
```

生成目录：
- **Go**: `backend/gateway/gen/stt/v1/`
- **Python**: `backend/app/gen/stt/v1/`
- **Dart**: `mobile/lib/gen/stt/v1/`

### 6.5 gRPC 调用示例（Python）

```python
import grpc
from app.gen.stt.v1 import stt_service_pb2, stt_service_pb2_grpc

async def transcribe_file(audio_path: str) -> str:
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = stt_service_pb2_grpc.STTServiceStub(channel)

        with open(audio_path, 'rb') as f:
            audio_data = f.read()

        request = stt_service_pb2.TranscribeRequest(
            audio_data=audio_data,
            filename=audio_path,
            language='zh-CN',
            enable_enhancement=True,
        )

        response = await stub.TranscribeAudio(request)
        return response.enhanced_text or response.text
```

### 6.6 错误码枚举

```protobuf
enum STTErrorCode {
  STT_ERROR_CODE_UNSPECIFIED = 0;
  STT_ERROR_CODE_AUDIO_TOO_LARGE = 1;
  STT_ERROR_CODE_UNSUPPORTED_FORMAT = 2;
  STT_ERROR_CODE_INVALID_SAMPLE_RATE = 3;
  STT_ERROR_CODE_NO_SPEECH_DETECTED = 4;
  STT_ERROR_CODE_RECOGNITION_FAILED = 5;
  STT_ERROR_CODE_PROVIDER_UNAVAILABLE = 6;
  STT_ERROR_CODE_RATE_LIMITED = 7;
  STT_ERROR_CODE_UNAUTHORIZED = 8;
  STT_ERROR_CODE_INTERNAL_ERROR = 9;
}
```

---

## 七、变更日志

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-03-15 | 1.0.0 | 初始版本，支持 ASR 和文档清洗 API |
| 2026-03-15 | 1.1.0 | 添加图片格式 OCR 支持 (JPG/PNG/WebP/GIF) |
| 2026-03-15 | 1.2.0 | 添加 STT gRPC Proto 标准化定义 |
