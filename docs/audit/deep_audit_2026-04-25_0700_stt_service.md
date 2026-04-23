# 深度审计 #63 — STT Service 语音转文字完整链路

> **日期**: 2026-04-25 07:00
> **模块**: STT Service — Provider 抽象 → 智谱/讯飞双通道 → 文件转写 → WebSocket 流式 → LLM 增强 → FastAPI 端点
> **范围**: 5 核心文件, 1 关联文件
> **总计**: 5 个文件, ~950 行
> **审计员**: Chris (Session 5 复核+新审模式)

---

## 审计范围

STT (Speech-to-Text) 服务是 Sparkle 语音输入的核心。支持文件转写（POST）和实时流式（WebSocket）两种模式，底层对接智谱 GLM-ASR 和科大讯飞两个 Provider，带自动 fallback 和 LLM 后处理增强。

### 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `backend/app/services/stt_service.py` | 256 | STT 门面：Provider 管理、fallback、文件/流式转写、LLM 增强 |
| `backend/app/services/stt/providers/base.py` | 70 | Provider 抽象基类（transcribe_stream + transcribe_file + close） |
| `backend/app/services/stt/providers/zhipu_provider.py` | 254 | 智谱 GLM-ASR-2512：文件上传 API + PCM 缓冲分段 + ffmpeg 转码 |
| `backend/app/services/stt/providers/xunfei_provider.py` | 319 | 科大讯飞：WebSocket iAT v2 协议 + HMAC 鉴权 + 流式/文件双模式 |
| `backend/app/api/v1/stt.py` | 115 | FastAPI 端点：POST /transcribe + WS /stream + 认证 |

---

## 数据流图

```
┌─────────────────────────────────────────────────────────────────────┐
│  Flutter Mobile                                                      │
│  ┌─ 录音 UI ─┐   ┌─ 文件选择 ─┐                                    │
│  │ WebSocket  │   │ POST /     │                                    │
│  │ /stt/stream│   │ transcribe │                                    │
│  └─────┬──────┘   └─────┬──────┘                                    │
└────────┼────────────────┼───────────────────────────────────────────┘
         │                │
┌────────┼────────────────┼───────────────────────────────────────────┐
│  Go Gateway / FastAPI                                                │
│  stt.py:75-90  WS auth     stt.py:29-71  Upload + validate         │
│         │                      │                                     │
│         ▼                      ▼                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  STTService (stt_service.py)                                  │  │
│  │  ┌─ handle_websocket_stream() ─┐  ┌─ transcribe_file() ──┐  │  │
│  │  │ _create_audio_stream_gen()  │  │ ordered_providers     │  │  │
│  │  │ → provider.transcribe_stream│  │ → provider[0].file   │  │  │
│  │  │                             │  │ → fallback to [1]    │  │  │
│  │  │ stream_provider (优先讯飞)  │  │ → LLM enhance        │  │  │
│  │  └─────────────────────────────┘  └──────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                      │                                     │
│         ▼                      ▼                                     │
│  ┌─────────────────┐  ┌──────────────────┐                         │
│  │ XunFeiProvider   │  │ ZhipuProvider     │                       │
│  │ WebSocket iAT v2 │  │ HTTP /audio/trans │                       │
│  │ HMAC-SHA256 auth │  │ Bearer token auth │                       │
│  └─────────────────┘  └──────────────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 审计发现

### P0 — 严重缺陷

#### P0-1: XunFeiProvider.transcribe_stream 在异常时将错误信息作为转录文本 yield — 语音输入被替换为错误消息
**文件**: `xunfei_provider.py:173, 259-261`
**严重性**: P0 — 错误消息作为正常文本传播到消费方

```python
# :173 — 无凭证时 yield 错误文本
if not self.app_id or not self.api_key or not self.api_secret:
    yield "科大讯飞API密钥未配置"  # ← 作为转录文本返回！
    return

# :259-261 — 连接异常时 yield 错误文本
except Exception as exc:
    logger.error(f"科大讯飞语音识别失败: {exc}")
    yield f"科大讯飞语音识别失败: {exc}"  # ← 作为转录文本返回！
```

**影响**: `stt_service.py:206-207` 将 yield 的文本通过 WebSocket 发送给客户端：
```python
async for text in active_provider.transcribe_stream(audio_stream):
    await websocket.send_json({"type": "transcription", "text": text, "is_final": False})
```
客户端会收到 `{"type": "transcription", "text": "科大讯飞语音识别失败: xxx"}`，用户看到错误消息被当作识别结果。如果客户端直接将此文本提交为聊天消息，用户会发送一条包含内部错误信息的消息。

**修复方向**: 使用专用异常或返回 `None` 标记错误，`stt_service.py` 在 yield 前检查是否为错误文本。

#### P0-2: stt_service.py handle_websocket_stream 在 finally 中关闭所有 Provider — 影响其他并发请求
**文件**: `stt_service.py:219-220`
**严重性**: P0 — 并发请求互相干扰

```python
finally:
    # Cleanup
    for provider in self._ordered_providers():
        await provider.close()  # ← 关闭所有 provider，影响其他并发请求
```

**影响**: `stt_service` 是模块级单例（:256），其 `provider` 和 `backup_provider` 被所有请求共享。当一个 WebSocket 流结束后调用 `provider.close()`，如果此时另一个请求正在使用同一个 provider，会导致后者连接被意外关闭。XunFei 的 `close()` 当前是空操作，但 Zhipu 的 `close()` 也是空操作——这意味着 `close()` 如果未来添加实际清理逻辑（如连接池关闭），将立即导致并发问题。

**修复方向**: 不要在单个请求的 finally 中关闭共享 provider。Provider 生命周期应由进程级 shutdown 管理。

---

### P1 — 重要问题

#### P1-1: XunFeiProvider.transcribe_file 在错误时返回错误字符串而非抛出异常 — fallback 无法触发
**文件**: `xunfei_provider.py:268-315`
**严重性**: P1

```python
# :268-269 — 无凭证时返回字符串
if not self.app_id or not self.api_key or not self.api_secret:
    return "科大讯飞API密钥或AppID未配置"  # ← 返回字符串，不抛异常

# :271-272 — 文件不存在时返回字符串
if not os.path.exists(file_path):
    return "文件不存在"  # ← 返回字符串，不抛异常

# :311-315 — 超时/异常时返回错误字符串
except Exception as exc:
    logger.error(f"文件语音识别失败: {exc}")
    return f"文件语音识别失败: {exc}"  # ← 返回字符串，不抛异常
```

`stt_service.py:137-138` 的 fallback 逻辑依赖 `_should_try_backup(text)` 检查返回文本中是否包含错误标记词：
```python
if index < len(providers) - 1 and self._should_try_backup(text):
    raise RuntimeError(text)
```
虽然 `_should_try_backup` 包含 `"未配置"` 和 `"识别失败"` 等关键词，但这是一种脆弱的文本匹配 fallback 机制——如果错误消息措辞改变，fallback 会静默失效。

**修复方向**: Provider 应在失败时抛出异常（如 `STTProviderError`），由 `stt_service.py` 的 except 块统一处理 fallback。

#### P1-2: XunFeiProvider._parse_response 解析错误时 raise RuntimeError(str(message)) — 异常消息来自外部服务
**文件**: `xunfei_provider.py:108`
**严重性**: P1

```python
code = data.get("code")
if code not in (0, None):
    message = data.get("message") or data.get("desc") or "未知错误"
    raise RuntimeError(str(message))  # ← 讯飞服务端错误消息直接暴露
```

讯飞 API 返回的错误消息可能包含内部信息。这个 RuntimeError 会被 `transcribe_stream` 的 except 捕获（:259）然后作为 yield 文本返回给客户端。

**修复方向**: 使用通用错误消息替换外部服务消息，原始消息仅记录到日志。

#### P1-3: ZhipuProvider._run_command 将 stderr 直接暴露在 RuntimeError 中 — 命令注入信息泄露
**文件**: `zhipu_provider.py:229-230`
**严重性**: P1

```python
message = stderr.decode("utf-8", errors="ignore").strip() or stdout.decode(...)
raise RuntimeError(message or f"命令执行失败: {' '.join(command)}")
```

ffmpeg/ffprobe 的 stderr 输出可能包含文件系统路径、编码器版本等内部信息。此 RuntimeError 最终通过 `stt_service.py` 返回给客户端。

#### P1-4: stt_service.py close() 在每个 WebSocket 请求结束时被调用 — 但 Provider 是单例
**文件**: `stt_service.py:219-220`
**严重性**: P1（与 P0-2 相关但独立）

Provider 的 `close()` 方法被频繁调用（每个 WS 连接结束一次），但 Provider 对象从未被重新创建。如果 `close()` 未来添加了连接池或 HTTP client 的清理逻辑，第二次请求将使用已关闭的 provider。

#### P1-5: stt.py WebSocket /stream 端点缺少速率限制 — 可被滥用为免费 ASR 代理
**文件**: `stt.py:74-90`
**严重性**: P1

POST /transcribe 受 `save_upload_file` 的文件大小限制保护，但 WebSocket /stream 端点无速率限制、无音频时长限制。攻击者可通过 WebSocket 发送超长音频流，持续消耗 ASR API 配额。

---

### P2 — 改进建议

#### P2-1: XunFeiProvider HMAC 鉴权使用 MD5-based formatdate — 安全性足够但非最佳实践
**文件**: `xunfei_provider.py:53`

`formatdate(timeval=None, localtime=False, usegmt=True)` 使用 RFC 2822 格式日期。讯飞协议本身要求这种格式，所以不是代码问题，但 HMAC key 在代码中直接使用 `self.api_secret.encode("utf-8")`，如果 settings 配置有误（如包含尾随空格），签名会静默失败。

#### P2-2: STTService._should_try_backup 使用硬编码中文关键词列表 — 缺少类型化错误码
**文件**: `stt_service.py:89-107`

14 个 fallback 标记词中 7 个是中文。如果 Provider 返回英文错误消息（如 ZhipuProvider 的 `"file too large"`），fallback 可能不触发。

#### P2-3: ZhipuProvider 每次调用 transcribe_audio_bytes 都创建新的 httpx.AsyncClient — 无连接复用
**文件**: `zhipu_provider.py:141`

```python
async with httpx.AsyncClient(timeout=self.timeout) as client:
    response = await client.post(...)
```

每次转录创建新 HTTP client，无法复用 TCP 连接。在高频调用场景下增加了延迟。

---

## 合规项

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 认证保护 | PASS (POST) / PASS (WS) | POST: get_current_user; WS: decode_token |
| 文件大小限制 | PASS | save_upload_file 带 max_size + allowed_extensions + content_types |
| Provider 抽象 | PASS | 基类 ABC + 多 Provider + fallback |
| 异常处理 | PARTIAL | 异常被捕获但作为正常文本返回 (P0-1, P1-1) |
| 资源清理 | PARTIAL | 临时文件清理 OK, Provider 生命周期管理有误 (P0-2) |
| 并发安全 | FAIL | 单例 Provider 在并发 WS 请求中被 close() (P0-2) |

---

## 统计

| 级别 | 数量 |
|------|------|
| P0 | 2 |
| P1 | 5 |
| P2 | 3 |
| **总计** | **10** |

---

## 修复优先级建议

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | 错误作为文本 yield | Provider 抛异常或返回 None，Service 层区分 | 低（~15 行） |
| P0-2 | 并发 WS 关闭共享 Provider | 移除 finally 中的 provider.close() | 低（~2 行） |
| P1-1 | transcribe_file 返回错误字符串 | 改为抛异常 | 中（~20 行） |
| P1-5 | WS 端点无速率限制 | 添加音频时长限制或请求频率限制 | 中 |

---

## 跨轮次因果链

| 本轮发现 | 关联轮次 | 关联模式 |
|----------|---------|---------|
| P0-1 (错误作为文本 yield) | Round #55 P0-2 (finish_reason STOP) | 外部服务返回的错误被当作正常结果传播 |
| P0-2 (并发 close 共享 Provider) | Round #56 P0-4 (ChatRepository 多实例) | 单例对象生命周期管理不当 |
| P1-2 (str(message) 泄露) | Round #5 S5 (str(e) 泄露 29处) | 外部服务错误消息通过异常传播到客户端 |
| P1-5 (WS 无速率限制) | Round #6 (Rate Limiting) | WebSocket 端点速率限制覆盖不完整 |
