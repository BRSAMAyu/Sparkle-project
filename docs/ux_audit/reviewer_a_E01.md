# Reviewer A — E01: Proto/gRPC契约完整性——Go与Python接口是否对齐
Timestamp: 2026-04-26T03:00:00+08:00
Chain Index: 15

## 自我审查声明

本报告所有发现已通过亲自阅读源代码确认。关键验证：(1) `agent_service.proto` 定义 17 个 RPC 方法；(2) `agent_grpc_service.py` 实现全部 17 个（line 148-1651）；(3) `client.go` 仅封装 4 个方法（StreamChat, StreamChatWithFallback, SubmitResponseFeedback, SubmitPlanReview）；(4) grep `RetrieveMemory|GetWeeklyReport|...ArbitrationQueue` 在 `backend/gateway/internal/` 目录零匹配 — 确认 Go 端不调用这 13 个 RPC。

## Chain Flow Summary

Proto 定义 17 个 RPC，Python 全部实现，Go Gateway 只封装并调用 4 个。剩余 13 个 RPC 的 Go client 方法不存在，也没有 handler 路由到它们。

## Critical Issues 🔴

None found.

## Major Issues 🟡

**1. `client.go` 只封装 4/17 RPC 方法——13 个 Python 端实现的 RPC 无 Go client 调用**

Proto 定义 17 个 RPC，Python `agent_grpc_service.py` 全部实现（lines 148-1651）。Go `client.go` 只封装 4 个：

| # | RPC | Go Client | Go Handler Route |
|---|-----|-----------|-----------------|
| 1 | StreamChat | ✅ (line 279) | ✅ via websocket_proxy |
| 2 | SubmitResponseFeedback | ✅ (line 305) | ✅ via REST handler |
| 3 | SubmitPlanReview | ✅ (line 326) | ✅ via REST handler |
| 4 | RetrieveMemory | ❌ | ❌ |
| 5 | GetUserProfile | ❌ | ❌ |
| 6 | GetWeeklyReport | ❌ | ❌ |
| 7 | SubmitContentReviewFeedback | ❌ | ❌ |
| 8 | SubmitReviewOverride | ❌ | ❌ |
| 9 | SubmitReviewAppeal | ❌ | ❌ |
| 10 | GetAppealStatus | ❌ | ❌ |
| 11 | SubmitReviewFeedback | ❌ | ❌ |
| 12 | RequestRegeneration | ❌ | ❌ |
| 13 | GetFeedbackStatistics | ❌ | ❌ |
| 14-17 | Arbitration (4 RPCs) | ❌ | ❌ |

grep 在 `backend/gateway/internal/` 目录搜索所有 13 个未封装 RPC 方法名，结果为零匹配。这意味着：
- RetrieveMemory、GetUserProfile、GetWeeklyReport 等 RPC **只能通过直接连接 Python gRPC 端口调用**，不经过 Go Gateway
- Flutter 客户端若需调用这些功能，必须走 REST API（如果存在）或直连 gRPC

Expected: 每个有业务需求的 proto RPC 都应有 Go client 封装 + REST/WebSocket handler 暴露给客户端。Actual: 13 个 RPC 有完整 Python 实现但 Go 端完全未集成。

**Note**: 这不一定是 bug — 如果这些 RPC 仅用于内部服务间调用（不面向移动客户端），则不需要 Go Gateway 封装。但如果 Flutter 客户端需要调用（如 RetrieveMemory for RAG, GetWeeklyReport for insights），则缺少 REST 等价端点是集成缺口。

## Minor Issues 🟢

None found.

## Working Well ✅

**Proto 定义质量** (`agent_service.proto`):
- 17 个 RPC 分组清晰（Chat / Memory / Profile / Report / Feedback / Review / Arbitration）
- 每个消息类型有详细注释说明用途
- `go_package` 正确设置（line 5）
- 使用 `google.protobuf.Timestamp` 和 `Struct` 标准类型

**Python 实现完整** (`agent_grpc_service.py`):
- 全部 17 个 RPC 有 async 方法实现
- StreamChat 使用 async generator 正确处理流式响应（line 148-257）
- 每个 RPC 有 error handling + logger.error（如 line 365, 478, 534）
- 安全检查：StreamChat 验证 user_id 和 auth metadata（line 169）
- Arbitration RPC 有 admin 权限检查（`_require_admin`, line 113）

**Go Client StreamChat** (`client.go`):
- `StreamChatWithFallback` 提供降级策略（line 263）
- 正确处理 context cancellation 和 deadline（line 279-303）
- 错误映射：gRPC status → Go error（line 295-300）

## Files Examined

1. `proto/agent_service.proto` (lines 1-68, 17 RPC definitions)
2. `backend/gateway/internal/agent/client.go` (lines 263-350, 4 method wrappers)
3. `backend/app/services/agent_grpc_service.py` (lines 148-1651, 17 RPC implementations)
4. `backend/gateway/internal/` directory (grep for 13 unimplemented RPC names — zero matches)

## Confidence: High — 逐一对比 proto RPC 定义、Python 实现和 Go client 封装。核心发现明确：13/17 RPC 有 Python 实现但无 Go client。是否为实际问题取决于这些 RPC 是否需要面向移动客户端暴露。
