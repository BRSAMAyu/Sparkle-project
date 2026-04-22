# 深度审计：gRPC StreamChat 调用链（Go Gateway → Python Engine）

> 日期：2026-04-22 00:15
> 范围：Go `client.go` gRPC 客户端 → `chat_orchestrator.go` 流处理 → `agent_service.proto` 契约 → Python `agent_grpc_service.py` → `_normalize_v2_response` 响应标准化

## 审计发现

### P0 — 阻断性问题（3 项）

#### P0-1: Proto `active_tools` 字段 Python 读取但 Go 从未填充
- **位置**: `proto/agent_service.proto:112` (定义) vs `chat_orchestrator_chatflow.go:410-440` (Go 填充) vs `orchestrator.py:694` (Python 读取)
- **问题**: ChatRequest 定义了 `repeated string active_tools = 12`，Python orchestrator 读取该字段用于工具决策，但 Go 客户端从未设置此字段
  ```protobuf
  // proto:112
  repeated string active_tools = 12;
  ```
  ```python
  # orchestrator.py:694 — Python 读取一个永远为空的列表
  active_tools = list(request.active_tools)  # 永远 = []
  ```
- **影响**: Python 侧的工具选择逻辑始终缺失客户端侧的 active_tools 输入，可能影响工具路由决策
- **修复**: Go 在 `buildChatRequest` 时从 session 或请求中提取 active_tools 并填充，或移除该 proto 字段

#### P0-2: StreamChat 错误使用 finish_reason=STOP 而非 ERROR
- **位置**: `backend/app/services/agent_grpc_service.py:257`
- **问题**: 异常路径使用 `STOP` 而非 proto 定义的 `ERROR = 5`
  ```python
  # :257 — 错误场景却用 STOP
  finish_reason=agent_service_pb2.STOP,  # Using STOP as finish reason even for errors
  ```
- **Proto 定义**:
  ```protobuf
  enum FinishReason {
      NULL = 0; STOP = 1; LENGTH = 2; TOOL_CALLS = 3;
      CONTENT_FILTER = 4; ERROR = 5;  // ← 应该用这个
  }
  ```
- **影响**: Go 和 Flutter 无法通过 finish_reason 区分正常完成和错误终止，依赖 error 字段二级判断
- **修复**: 错误路径改为 `finish_reason=agent_service_pb2.ERROR`

#### P0-3: StreamChat 不设置 gRPC status code，错误仅通过 response 传播
- **位置**: `backend/app/services/agent_grpc_service.py:135-260`
- **问题**: StreamChat 方法从不调用 `context.set_code()` 或 `context.set_details()`，而其他 RPC 方法（RetrieveMemory, GetUserProfile 等）都正确设置
  ```python
  # 其他方法 (RetrieveMemory :411-413):
  context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
  context.set_details("user_id and query_text are required")

  # StreamChat — 无 set_code 调用，错误仅通过 yield ChatResponse(error=...) 传播
  ```
- **影响**: Go 侧 gRPC client 的 `Recv()` 仅收到 `io.EOF` 而非具体错误码，无法区分超时、不可用、参数错误等
- **修复**: 在 StreamChat 的 error path 中添加 `context.set_code(grpc.StatusCode.INTERNAL)` 等

---

### P1 — 重要问题（5 项）

#### P1-1: 流中断无恢复机制，用户必须手动重试
- **位置**: `backend/gateway/internal/handler/chat_orchestrator.go:500-512`
- **问题**: gRPC 连接在流式传输中中断时，Go 仅发送 "Stream interrupted" 错误并终止
  ```go
  if err != nil {
      log.Printf("Stream recv error: %v", err)
      r.SendError("aborted", "Stream interrupted", true)
      break  // 整个流终止，无恢复
  }
  ```
- **影响**: 网络抖动导致用户丢失 AI 正在生成的完整回复，且无法恢复
- **修复**: 实现请求级 resume token，允许客户端从中断点继续接收

#### P1-2: Go 流接收无背压控制
- **位置**: `backend/gateway/internal/handler/chat_orchestrator.go:491-589`
- **问题**: `stream.Recv()` 循环以最大速度接收并立即转发 WebSocket，无缓冲区检查
- **影响**: 慢客户端（弱网）下 Go 内存堆积，极端情况 OOM
- **修复**: 每连接写入队列 + 大小限制 + 背压信号（与 Round 2 P1-3 一致）

#### P1-3: ChatResponse.session_id 不一致填充
- **位置**: `backend/app/services/agent_grpc_service.py:210-213`
- **问题**: Python 仅在 `not response.session_id` 时回填 session_id，但 orchestrator 内部产生的 response 可能已设了错误值
  ```python
  if not response.session_id:
      response.session_id = request.session_id  # 只在为空时设
  ```
- **影响**: 极端情况下 Go 或 Flutter 收到空 session_id，无法关联会话
- **修复**: 强制覆写 `response.session_id = request.session_id`，不检查空值

#### P1-4: Proto `history` 和 `config` 字段定义但两端都未使用
- **位置**: `proto/agent_service.proto:100,103`
- **问题**:
  - `repeated ChatMessage history = 6` — Go 从不填充，Python 注释"应优先从数据库读取"
  - `ChatConfig config = 8` — 含 model/temperature/max_tokens/tools_enabled，两端都未使用
- **影响**: 增加 proto 复杂度，给新开发者造成误解；config 字段的设计意图（per-request 模型覆盖）被浪费
- **修复**: 移除无用字段，或实现 config 字段支持动态模型选择

#### P1-5: chat_mode 使用魔术字符串而非 proto enum
- **位置**: `proto/agent_service.proto:113` (string 类型) vs Python 多处硬编码
- **问题**: chat_mode 定义为 `string chat_mode = 13`，Python 侧使用 7+ 种字符串常量
  ```python
  # agent_profiles.py, unified_intent_router.py 等文件:
  "standard", "deep_analysis", "study_plan", "error_diagnosis",
  "expert_auto", "expert::<expert_id>", "team::<team_spec>"
  ```
- **影响**: 无编译时校验，拼写错误（如 "deep_anlysis"）不会被 proto 层捕获
- **修复**: 改为 proto enum + string prefix 保留扩展性

---

### P2 — 改进建议（4 项）

#### P2-1: 单 gRPC 连接无连接池
- **位置**: `backend/gateway/internal/agent/client.go:62-88`
- **问题**: `NewClient()` 创建单个 `grpc.ClientConn`，高并发下可能成为瓶颈
- **修复**: 连接池（如 2-4 个连接轮转），或依赖 gRPC 内置多路复用

#### P2-2: Python 端无 user_id 格式校验
- **位置**: `backend/app/services/agent_grpc_service.py:148`
  ```python
  user_id = request.user_id or metadata.get("user-id", "")
  # 空字符串也接受，不校验 UUID 格式
  ```
- **修复**: 添加 UUID 格式校验，空 user_id 返回 INVALID_ARGUMENT

#### P2-3: event_time 依赖 fallback 而非发送端统一设置
- **位置**: `agent_grpc_service.py:86` (normalize fallback) vs orchestrator 发送端
- **问题**: `_normalize_v2_response` 为缺失 event_time 的 response 补时间戳，但应在上游统一设置
- **修复**: orchestrator 每个 yield 点确保设置 event_time

#### P2-4: gRPC 超时最小值 300s 不可调低
- **位置**: `chat_orchestrator.go:208-216`
  ```go
  if timeoutSeconds < 300 {
      timeoutSeconds = 300  // 强制最低 5 分钟
  }
  ```
- **问题**: 开发/测试环境可能需要更短超时以快速失败
- **修复**: 仅在生产环境强制最低值，开发环境允许 30s

---

### 合规项（5 项）

1. **元数据传播完整** ✅ — Go→Python 传递 user-id、x-trace-id、authorization
2. **重连 + 熔断器** ✅ — client.go 自动重连 Unavailable/DeadlineExceeded，health_checker 实现三态熔断
3. **对象池优化** ✅ — chat_orchestrator.go 使用 sync.Pool 减少 GC 压力
4. **OTel 分布式追踪** ✅ — Go 和 Python 均接入 OpenTelemetry
5. **Proto 弃用字段规范处理** ✅ — timestamp→event_time, code→error_code 均正确 reserved

---

## 数据流图

```
Go Gateway (chat_orchestrator.go)
  │
  ├── buildChatRequest()
  │   ├── 设置: user_id, session_id, request_id, message, file_ids,
  │   │         include_references, chat_mode, user_profile, extra_context ✅
  │   ├── 未设置: active_tools ❌, history ❌, config ❌
  │   ↓
  ├── client.StreamChatWithFallback(ctx, req)
  │   ├── 熔断器检查 (AllowRequest?)
  │   ├── metadata: user-id, x-internal-api-key, x-trace-id
  │   ├── 超时: min 300s
  │   ├── gRPC 连接: 单连接, keepalive 20s, retry max 4
  │   ↓
  ↓ [gRPC HTTP/2]
Python Engine (agent_grpc_service.py)
  │
  ├── 提取 metadata: user-id, x-trace-id
  ├── user_id = request.user_id || metadata["user-id"]  (无校验 ⚠️)
  ├── chat_mode = normalize_chat_mode(request.chat_mode)
  ├── DB session: 每请求独立
  ↓
  ├── orchestrator.process_stream(request, ...)
  │   ├── 读取 active_tools = list(request.active_tools)  → 永远 [] ⚠️
  │   ├── 构建上下文, 组装 prompt
  │   ├── 调用 LLM, 工具执行
  │   └── yield ChatResponse (delta/full_text/tool_call/error/...)
  │
  ├── _normalize_v2_response()
  │   ├── event_time fallback (如缺失)
  │   └── error_code fallback (如 UNSPECIFIED → UNKNOWN)
  │
  ├── session_id 回填 (仅 when empty ⚠️)
  │
  ├── [正常完成] yield → finish_reason=STOP ✅
  ├── [异常] yield ChatResponse(error=...) → finish_reason=STOP ❌ 应为 ERROR
  │         未调用 context.set_code() ❌
  ↓
Go Gateway (接收循环)
  │
  ├── stream.Recv() → 无背压 ⚠️
  ├── 正常: io.EOF → break
  ├── 错误: SendError("aborted", "Stream interrupted") → break
  │         无 DoneEvent ⚠️ (Round 2 P1-6)
  ├── Protobuf → JSON 转换
  │         metadata 布尔值标准化 (Round 2 P1-1)
  ├── XSS sanitizer (bluemonday)
  ↓
WebSocket → Flutter
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | active_tools 永远为空 | Go 填充 active_tools 或移除 proto 字段 | 低（~15 行 Go） |
| P0-2 | finish_reason 错误场景用 STOP | 改为 `agent_service_pb2.ERROR` | 低（1 行 Python） |
| P0-3 | StreamChat 无 gRPC status code | 错误路径添加 `context.set_code()` | 低（~5 行 Python） |
| P1-1 | 流中断无恢复 | resume token 机制 | 高（~200 行） |
| P1-2 | 流接收无背压 | 每连接写入队列 | 中（~80 行 Go） |
| P1-3 | session_id 不一致填充 | 强制覆写而非条件检查 | 低（1 行 Python） |
| P1-4 | history/config 死字段 | 移除或实现 | 低（proto 改动） |
| P1-5 | chat_mode 魔术字符串 | 改为 proto enum | 中（proto + 多文件改动） |
