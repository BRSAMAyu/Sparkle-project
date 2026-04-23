# 深度审计：WebSocket 消息流完整链路

> 日期：2026-04-21 23:30
> 范围：Flutter 发送消息 → Go Gateway WebSocket 接收 → gRPC 转发 → Python FSM 处理 → 流式响应 → Go 转发回 Flutter

## 审计发现

### P0 — 阻断性问题（3 项）

#### P0-1: Flutter 消息队列无持久化，三个场景下永久丢失
- **位置**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart`
- **问题**: 消息仅存在于内存队列 `_pendingMessages`（上限 50 条），三个场景永久丢失：
  1. **队列溢出**（`:1555-1568`）：超过 50 条时丢弃最早的，无用户感知
     ```dart
     if (_pendingMessages.length >= _pendingMessageLimit) {
         final droppedPayload = _pendingMessages.removeAt(0); // 静默丢弃
     }
     ```
  2. **401 认证失败**（`:1705-1716`）：token 过期时清空全部未发送消息
  3. **最大重连耗尽**（`:1877`）：`_pendingMessages.clear()` 永久清空
- **影响**: 用户以为消息已发送但实际丢失，且无任何 UI 提示
- **修复**: (1) 消息落盘到 SQLite (2) 401 时仅暂停发送不清空队列 (3) 重连耗尽时提示用户手动重试

#### P0-2: FSM context_data 无限增长可能突破 gRPC 消息限制
- **位置**: `backend/app/orchestration/orchestrator.py:1094-1204`
- **问题**: `WorkflowState.context_data` 累积 20+ 字段无大小限制
  ```python
  state.context_data["session_feedback_signal"] = ...
  state.context_data["adaptation_records"] = ...
  state.context_data["preference_learnings"] = ...
  state.context_data["evolution_highlights"] = ...
  # 15+ more fields
  ```
- **估算**: 100 条消息会话可达 500KB-5MB，超过 gRPC 默认 4MB 限制后流中断
- **影响**: 长会话突然崩溃，用户看到 "Stream interrupted"，无解释
- **修复**: (1) ContextPruner 在 FSM 入口强制调用 (2) context_data 超过 1MB 告警、3MB 拒绝 (3) 大对象移至 Redis 仅保留引用

#### P1-7: Flutter 并发请求路由存在竞态条件（自审降级：多请求并发为少数场景，不等于数据丢失）
- **位置**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:1515-1543`
- **问题**: 无 request_id 的响应消息在多请求并发时路由到错误控制器
  ```dart
  if ((targetRequestId == null || targetRequestId.isEmpty) &&
      _requestControllers.length == 1) {
      targetRequestId = _requestControllers.keys.first; // 竞态！
  }
  ```
- **影响**: 响应消息被错误分配到另一个请求的 UI，导致内容串流
- **修复**: 当 `_requestControllers.length > 1` 时，拒绝无 request_id 的消息而非猜测路由

---

### P1 — 重要问题（6 项）

#### P1-1: Python metadata 布尔值类型不稳定
- **位置**: `backend/app/orchestration/orchestrator.py:428-439`
- **问题**: `early_ack` 用字符串 `"true"` 而非布尔值 `True`；`ux_progress` 用 `json.dumps()` 二次编码
  ```python
  metadata={
      "ux_progress": json.dumps({...}, ensure_ascii=False),  # double-encoded
      "early_ack": "true",  # string, not bool
  }
  ```
- **影响**: Go→Flutter 链路中类型不确定（有时 bool 有时 string），Flutter 必须用 `_isTrue()` 兼容
- **修复**: 统一所有 metadata 布尔字段为 Python 原生 bool，`ux_progress` 用 dict 而非 json.dumps

#### P1-2: gRPC 超时无 Flutter 端感知
- **位置**: `backend/gateway/internal/handler/chat_orchestrator_chatflow.go:208-216`
- **问题**: gRPC 默认 300s 超时，但 Flutter 端无倒计时提示，超时后仅收到通用 "Stream interrupted"
  ```go
  timeoutSeconds := 300
  ctx, cancel := context.WithTimeout(ctx, time.Duration(timeoutSeconds)*time.Second)
  ```
- **影响**: 用户在 AI 长时间思考时无法区分"正在处理"和"已超时断连"
- **修复**: (1) Go 侧在超时前 30s 发送 warning delta (2) Flutter 端显示超时倒计时

#### P1-3: Go Gateway WebSocket 写入无背压控制
- **位置**: `backend/gateway/internal/handler/chat_orchestrator_chatflow.go:~100-150`
- **问题**: Python 产出快于 Flutter 消费时，Go 直接写 WebSocket 无缓冲区检查
  ```go
  _ = r.SendChatResponse(resp) // 无背压检查
  ```
- **影响**: 高负载下 Go 写入阻塞或连接断开，内存可能溢出
- **修复**: 实现每连接写入队列 + 大小限制 + 背压信号

#### P1-4: 消息长度限制前后端不一致
- **位置**: Go `chat_orchestrator.go:115` 定义 `maxMessageLength = 4000`，Flutter 无前端校验
- **影响**: 用户输入超 4000 字符后发送，消息已在本地乐观显示但被 Go 拒绝
- **修复**: Flutter 端 `sendMessage` 前检查 `message.length <= 4000`

#### P1-5: Python 异常信息在错误传播中大量丢失
- **位置**: `backend/app/orchestration/orchestrator.py:1907-1931`
- **问题**: `build_safe_chat_error()` 仅处理 3 种异常类型，其余全返回 "系统暂时不可用"
- **影响**: LLM API 错误、工具执行失败等无法区分，调试困难
- **修复**: (1) 记录完整异常栈到日志 (2) 在响应 metadata 中附带 correlation_id (3) 扩展安全错误映射

#### P1-6: Go 侧流错误后未发送 DoneEvent
- **位置**: `backend/gateway/internal/handler/chat_orchestrator_chatflow.go:~130`
- **问题**: 流错误时发送 Error 消息但未发送 DoneEvent，Flutter 可能无限等待
  ```go
  if err != nil {
      r.SendError("aborted", "Stream interrupted", true)
      break // 但未发送 DoneEvent
  }
  ```
- **修复**: Error 之后必须发送 DoneEvent 以关闭 Flutter 端 StreamController

---

### P2 — 改进建议（4 项）

#### P2-1: Python finish_reason 对错误使用 STOP 而非 ERROR
- **位置**: `backend/app/services/agent_grpc_service.py:257`
- **修复**: 错误场景使用 `agent_service_pb2.ERROR`

#### P2-2: 流队列压力下 droppable 消息无指标
- **位置**: `backend/app/orchestration/orchestrator.py:497-538`
- **问题**: `early_ack` 等可丢弃消息在队列压力 >75% 时被静默丢弃，无 Prometheus 计数
- **修复**: 添加 `sparkle_stream_dropped_messages_total` counter

#### P2-3: Flutter Delta 无去重机制
- **位置**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:360-367`
- **问题**: 网络重试可能导致重复 delta 显示
- **修复**: 追踪 last-seen delta index 或 timestamp

#### P2-4: DoneEvent 清理顺序可能导致孤立 Timer
- **位置**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:1538-1542`
- **问题**: Timer 清理发生在 Controller 关闭之后，可能向已关闭的 controller 添加事件
- **修复**: 先取消 Timer 再关闭 Controller

---

### ✅ 合规项（4 项）

1. **Flutter↔Go 消息 JSON 结构完全一致** ✅ — `message`/`session_id`/`request_id`/`file_ids`/`extra_context`/`chat_mode` 字段一一对应
2. **Proto→Go→Python 字段映射完整** ✅ — `StreamChatRequest` 所有字段在两端都被使用
3. **Python 流式队列有优先级和背压** ✅ — 512 条容量 + 75% 压力阈值 + droppable 分类
4. **Flutter 处理 20+ 事件类型** ✅ — text/delta/tool_call/review/transparency/metadata 等全覆盖

---

## 数据流图

```
Flutter (sendMessage)
  │  JSON: {message, session_id, request_id, file_ids?, extra_context?}
  ↓
WebSocket Client (_enqueuePendingMessage → _channel.sink.add)
  │
  ↓ [WebSocket 帧]
Go Gateway (websocket_proxy.go → chat_orchestrator.go)
  │  解析 JSON → chatInput struct
  │  校验: session归属 + 消息长度≤4000 + 速率限制
  ↓
gRPC Client (agent/client.go → StreamChat RPC)
  │  metadata: user-id, x-trace-id, authorization
  │  超时: 300s (可配置)
  ↓
Python gRPC Server (agent_grpc_service.py)
  │  提取 user_id, session_id
  │  构造 OrchestratorRequest
  ↓
FSM (orchestrator.py)
  │  INIT → THINKING → GENERATING → [TOOL_CALLING → ...] → DONE
  │  context_data 累积 (⚠️ 无大小限制)
  │  yield StreamResponse(delta + metadata)
  ↓
gRPC Server → 流式响应
  │  ChatResponse { delta, full_text, finish_reason, metadata }
  ↓
Go Gateway (chat_orchestrator_chatflow.go)
  │  Protobuf → JSON 转换
  │  metadata 布尔值标准化 (⚠️ 不完整)
  │  XSS sanitizer 处理 delta
  │  写入 WebSocket (⚠️ 无背压)
  ↓
Flutter (websocket_chat_service_v2.dart)
  │  JSON 解析 → Event 对象
  │  request_id 路由到对应 StreamController
  │  TextEvent → UI 拼接显示
  │  DoneEvent → 关闭 Controller
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | 消息队列无持久化 | SQLite 落盘 + 401 保留队列 | 中（~200 行 Dart） |
| P0-2 | context_data 无限增长 | ContextPruner 强制入口 + 大小监控 | 中（~100 行 Python） |
| P0-3 | 并发请求路由竞态 | 拒绝无 request_id 消息 | 低（~10 行 Dart） |
| P1-1 | 布尔值类型不稳定 | 统一 Python metadata 为原生类型 | 低（~30 行 Python） |
| P1-2 | 超时无 Flutter 感知 | Go 超时前 30s 发 warning delta | 低（~20 行 Go） |
| P1-3 | WebSocket 写入无背压 | 每连接写入队列 + 大小限制 | 中（~80 行 Go） |
| P1-4 | 消息长度不一致 | Flutter 前端校验 ≤4000 | 低（~5 行 Dart） |
| P1-5 | 异常信息丢失 | 扩展 safe error 映射 + correlation_id | 中（~60 行 Python） |
| P1-6 | 错误后无 DoneEvent | Error 后强制发送 DoneEvent | 低（~5 行 Go） |

---

## 复核笔记

> **复核日期**: 2026-04-25
> **复核员**: Claude Deep Auditor

### 复核方法

逐项验证原审计（Round #2）发现是否与当前代码一致。重点验证 P0 级发现的行号准确性和修复进展。

### 逐项复核结果

| 编号 | 原发现 | 状态 | 备注 |
|------|--------|------|------|
| P0-1 | Flutter 消息队列无持久化 | ✅ 已验证 | 仍为 50 条上限 (`_pendingMessageLimit = 50`, :1089)，溢出 `removeAt(0)` (:1538)，多处 `.clear()` (:1571, 1676, 1742, 1847, 2020, 2187)。无 SQLite/Hive 持久化 |
| P0-2 | FSM context_data 无限增长 | ✅ 已验证 | `context_data[` 赋值超过 20 处 (:936-1189)，包含 `session_feedback_signal`, `adaptation_records`, `preference_learnings`, `evolution_highlights`, `progress_snapshot` 等。无大小限制或入口裁剪 |
| P1-7→原P0-3 | 并发请求路由竞态 | ✅ 已验证 | 无变化，自审降级合理 |
| P1-1 | Python metadata 布尔值类型不稳定 | ✅ 已验证 | `orchestrator.py:426` 仍为 `"early_ack": "true"` (字符串)，`:417` `json.dumps({...})` 二次编码 ux_progress |
| P1-2 | gRPC 超时无 Flutter 感知 | ✅ 已验证 | 无变化 |
| P1-3 | WebSocket 写入无背压控制 | ✅ 已验证 | 无变化，主流式循环 SendChatResponse 无背压检查 |
| P1-4 | 消息长度限制前后端不一致 | ✅ 已验证 | Go 侧 `maxMessageLength = 4000` (chat_orchestrator.go:102)，Flutter 端仍无前端校验 |
| P1-5 | Python 异常信息丢失 | ✅ 已验证 | 无变化 |
| P1-6 | Go 侧流错误后未发送 DoneEvent | ⚠️ 部分修复 | `break` 路径（stream interrupted, :436）现在到达 :595-614 发送 DoneEvent (FinishReason_STOP)。但 `return false` 路径（daily quota exceeded, :477）仍然**直接返回不发送 DoneEvent**，Flutter 端可能卡在"加载中" |
| P2-1 | finish_reason 对错误用 STOP | ✅ 已验证 | 无变化 |
| P2-2 | droppable 消息无指标 | ✅ 已验证 | 无变化 |
| P2-3 | Flutter Delta 无去重 | ✅ 已验证 | 无变化 |
| P2-4 | DoneEvent 清理顺序 | ✅ 已验证 | 无变化 |

### 新发现

- **P1-6 残留路径**: 配额超限 (`return false` at :477) 跳过了 :530-614 的 RecordUsage + SendMeta + SendChatResponse(DoneEvent)。这意味着：配额超限时 Flutter 端收不到 DoneEvent，StreamController 不关闭，UI 卡死。与 Round #47 P0-1 (配额不退还) 是同一代码路径的不同症状。

### 总结

- **0/13 已完全修复**
- **1/13 部分修复** (P1-6: break 路径现在发送 DoneEvent，但 return false 路径仍不发送)
- **12/13 未变化**
- 行号偏移：主要引用的文件行号基本匹配，`_pendingMessageLimit` 从报告中的 :1555 移至 :1089（Flutter 文件重构），`context_data` 赋值从 :1094 移至 :936（orchestrator 重构）
