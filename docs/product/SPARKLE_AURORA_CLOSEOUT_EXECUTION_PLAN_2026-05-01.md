# Sparkle Aurora 完全体收口 — 并行执行方案

> **日期**: 2026-05-01
> **版本**: v1.0
> **目标分支**: roadmapv3
> **执行方式**: 最多 15 个 code agent 并行，每个 agent 领取一个任务号
> **基础**: 独立验证审计报告 `docs/product/SPARKLE_INDEPENDENT_VERIFICATION_REPORT_2026-05-01.md` 中确认的真实问题 + 用户完整体验收口需求
> **成功定义**: 用户在日常对话、目标推进、卡点恢复、跨会话切换中，持续感到 Aurora 真的理解我、记得我、会校准自己；生产路径不会因 WebSocket 关闭、错误泄露、状态丢失而打断信任

---

## 方案总览

本方案将 5 大 Key Changes + 审计确认的真实问题拆分为 **15 个并行任务**，分三波执行：

| 波段 | 任务数 | 聚焦领域 | 依赖 |
|------|--------|---------|------|
| **Wave 1** (Day 1) | 6 任务 | 生产信任底座 + 纠错协议统一 | 无依赖，全部并行 |
| **Wave 2** (Day 1-2) | 6 任务 | 体验连续性 + 校准回执 + 离线可见 | T07/T08 依赖 T04/T05 |
| **Wave 3** (Day 2-3) | 3 任务 | 工程质量 + 文档收敛 + CI 一致性 | 可与 Wave 2 后半段并行 |

每个任务标注了：
- **愿景目标**：这个任务完成后用户感受到什么
- **当前状态**：现在是什么情况
- **需要达到的效果**：具体可验证的完成条件
- **验收标准**：逐项 checkbox
- **具体文件**：涉及的文件范围
- **禁止事项**：明确不能碰的边界

---

## 全局约束（所有 Agent 必须遵守）

### 不改的范围
- Aurora PII redaction / LLM safety / kill switch 基础设施 — 只开不关，不修改逻辑
- Proto 定义 — 不新增字段，只在已有字段上调整使用方式
- 数据库 schema — 不新增 migration
- 已实现且 live 的 Aurora / 双核链路 — 不退回 shadow/off
- 用户 opt-out 路径 — 必须保留并确保功能正常

### 代码质量要求
- 每处文案变更必须同时更新中英文 `.arb` 文件
- 每处 UI 变更必须检查暗色模式兼容性（使用 DS token 而非硬编码颜色）
- 每处交互元素必须添加 `Semantics` 标签
- 每处 Aurora 介入必须有可追溯的 `receipt` 数据结构

### 测试要求
- 后端: 核心链路必须补充至少 1 个 pytest（路径: `backend/tests/`）
- Flutter: 交互元素必须补充至少 1 个 widget test（路径: `mobile/test/`）
- Go: 每个 handler/middleware 修改必须补充至少 1 个 table-driven test
- 如果修改了已有逻辑，必须先确保已有测试继续通过

### 并行安全
- 每个 agent 只修改自己任务列出的文件
- 如果必须修改共享文件（如 orchestrator.py），只在文件末尾或明确标记的区域添加
- 提交前运行 `git diff --check` 确保无冲突标记

---

## Wave 1：生产信任底座 + 纠错协议统一（6 个并行任务）

### 任务 T01：Go WebSocket 关闭安全性 — 消除 idleTimer 竞态和双重 Close

**并行约束**: 无依赖，可立即开始

**愿景目标**:
用户在聊天过程中不会因为 WebSocket 连接超时、网络切换或服务端 idle timeout 而遇到连接崩溃、消息丢失或 goroutine 泄露。WebSocket 的关闭路径是幂等的、序列化的、不会产生 panic。

**当前状态**:
- `chat_orchestrator.go:278-290` idleTimer goroutine 调用 `writer.WriteControl()` + `writer.Close()`
- 主 handler 的 deferred cleanup 也调用 `writer.Close()`
- `wsSafeWriter` 序列化了写入操作但 `Close()` 方法没有被 `sync.Once` 保护
- 并发 `websocket.Conn.Close()` 可导致 panic

**需要达到的效果**:

1. **wsSafeWriter.Close() 幂等化** — `Close()` 方法使用 `sync.Once` 确保底层 `websocket.Conn.Close()` 只执行一次，后续调用安全返回 nil

2. **idleTimer goroutine 安全退出** — idleTimer 触发后通过 `connDone` channel 与主 handler 协调，不在 timer goroutine 中直接调用 `writer.Close()`，而是通过信号通知主 handler 执行关闭

3. **WriteControl 超时保护** — `WriteControl()` 调用加入 context timeout，不会因为对端已断开而永久阻塞

4. **关闭路径测试** — 至少覆盖：正常关闭、idle timeout 关闭、客户端断连时关闭、并发关闭

**具体文件**:
- `backend/gateway/internal/handler/ws_safe_writer.go` — Close() 幂等化
- `backend/gateway/internal/handler/ws_safe_writer_test.go` — 幂等测试
- `backend/gateway/internal/handler/chat_orchestrator.go` — idleTimer 安全退出
- `backend/gateway/internal/handler/chat_orchestrator_connections.go` — 如果关闭逻辑在此

**验收标准**:
- [ ] `wsSafeWriter.Close()` 可被多次调用，第二次及以后返回 nil 不 panic
- [ ] idleTimer 触发时不直接关闭连接，而是通知主 handler 优雅关闭
- [ ] `WriteControl` 有 context timeout 保护
- [ ] 新增至少 3 个 Go test：幂等 Close、idle timeout 关闭路径、并发关闭不 panic
- [ ] 已有 `go test ./...` 全部继续通过

**禁止事项**:
- 不修改 WebSocket 消息协议格式
- 不修改心跳间隔参数
- 不修改 wsSafeWriter 的写入序列化逻辑（只改 Close）

---

### 任务 T02：Go 错误响应统一脱敏 — 生产环境不泄露内部错误

**并行约束**: 无依赖，可立即开始

**愿景目标**:
用户在任何操作失败时看到的都是友好的、不暴露内部实现的错误消息。内部错误细节只在服务端日志中记录，永远不离开 Go Gateway。

**当前状态**:
- 23+ 处 handler 将 `err.Error()` 直接返回给客户端（HTTP JSON 或 WebSocket 消息）
- 分布在 error_book.go(7处)、file_handler.go(8处)、health.go(2处)、auth.go(2处)、galaxy_handler.go(2处)、chaos.go(2处)、data_consistency_handler.go(1处)、intervention_push.go(1处)
- `file_handler.go` 已有 `sanitizeError()` 函数作为可复用模式

**需要达到的效果**:

1. **统一脱敏函数** — 扩展或创建通用的 `sanitizeErrorResponse(c *gin.Context, statusCode int, err error, internalMsg string)` 函数：
   - 开发模式（`isDevelopmentModeForErrors()`）: 返回 `err.Error()` 用于调试
   - 生产模式: 返回通用错误消息，内部错误写入 zap.Logger
   - 保留 error code/category 用于前端分类处理

2. **逐一替换** — 将 23+ 处 `c.JSON(500, gin.H{"error": err.Error()})` 替换为 `sanitizeErrorResponse(c, 500, err, "...")`

3. **i18n 错误消息** — 生产模式的通用错误消息通过 i18n 系统返回（如 "操作失败，请稍后重试" / "Something went wrong"）

4. **错误日志与指标** — 每次脱敏时同时：
   - 用 zap.Logger 记录完整错误（含 request_id）
   - 递增 Prometheus error counter（按 status code + handler 分类）

**具体文件**:
- `backend/gateway/internal/handler/error_sanitizer.go` — 新建或扩展统一脱敏函数
- `backend/gateway/internal/handler/error_book.go` — 7 处替换
- `backend/gateway/internal/handler/file_handler.go` — 8 处替换（已有 sanitizeError 可参考）
- `backend/gateway/internal/handler/health.go` — 2 处替换
- `backend/gateway/internal/handler/auth.go` — 2 处替换
- `backend/gateway/internal/handler/galaxy_handler.go` — 2 处替换
- `backend/gateway/internal/handler/chaos.go` — 2 处替换
- `backend/gateway/internal/handler/data_consistency_handler.go` — 1 处替换
- `backend/gateway/internal/handler/intervention_push.go` — 1 处替换
- `backend/gateway/internal/handler/chat_orchestrator_feedback.go` — 1 处 WebSocket 错误消息替换

**验收标准**:
- [ ] 23+ 处 `err.Error()` 全部替换为脱敏函数调用
- [ ] 生产模式返回通用消息，不包含任何内部路径/函数名/SQL
- [ ] 开发模式保留完整错误用于调试
- [ ] 每次脱敏同时记录 zap 日志（含 request_id）
- [ ] 新增至少 3 个 Go test：生产模式脱敏、开发模式保留、i18n 错误消息
- [ ] 已有 `go test ./...` 全部继续通过

**禁止事项**:
- 不修改错误码体系（前端可能依赖）
- 不删除 `isDevelopmentModeForErrors()` 的判断逻辑
- 不修改 zap.Logger 的配置

---

### 任务 T03：Go Handler 服务层隔离 — 消除 handler 直接访问 DB

**并行约束**: 无依赖，可立即开始

**愿景目标**:
Go Gateway 的 handler 层只负责请求解析、验证和响应序列化。所有数据库和 Redis 操作通过 service 层完成，确保未来缓存、事务、权限逻辑有统一插入点。

**当前状态**:
- `auth.go` 直接持有 `*db.Queries`，执行 6 处直接 DB 调用（GetUserByAppleID、GetUserByEmail、CreateSocialUser、LinkAppleUser、UpdateUserLastLogin、UpsertUserSession）
- `group_chat.go` 直接持有 `*db.Queries`，执行 2 处 DB 调用（IsGroupMember、GetGroupMessages）
- `data_consistency_handler.go` 直接持有 `*db.Queries` 和 `*redis.Client`

**需要达到的效果**:

1. **auth.go 服务层** — 创建 `backend/gateway/internal/service/apple_auth_service.go`（或扩展现有 auth service）：
   - 将 6 处 DB 调用封装为 service 方法
   - handler 只做：解析请求 → 调用 service → 序列化响应
   - 保持 Apple token 验证逻辑不变

2. **group_chat.go 服务层** — 创建 `backend/gateway/internal/service/group_chat_service.go`：
   - IsGroupMember → `service.CheckGroupMembership(ctx, userID, groupID)`
   - GetGroupMessages → `service.GetGroupMessages(ctx, groupID, limit, offset)`

3. **data_consistency_handler.go** — 已部分使用 `service.ChatHistoryService`，补充剩余直接 DB/Redis 调用

4. **测试更新** — 原有 handler 测试改为 mock service 接口而非 mock DB

**具体文件**:
- `backend/gateway/internal/service/apple_auth_service.go` — 新建或扩展
- `backend/gateway/internal/service/group_chat_service.go` — 新建或扩展
- `backend/gateway/internal/handler/auth.go` — 移除 `*db.Queries` 依赖
- `backend/gateway/internal/handler/group_chat.go` — 移除 `*db.Queries` 依赖
- `backend/gateway/internal/handler/data_consistency_handler.go` — 补充 service 调用
- 对应的 test 文件

**验收标准**:
- [ ] auth.go handler 不再持有 `*db.Queries`
- [ ] group_chat.go handler 不再持有 `*db.Queries`
- [ ] data_consistency_handler.go 不再直接访问 Redis/DB（通过 service）
- [ ] 所有 DB 操作通过 service 层方法
- [ ] 已有 handler 测试继续通过（改为 mock service）
- [ ] 新增至少 2 个 service 层测试

**禁止事项**:
- 不修改 SQL 查询本身
- 不修改 API 接口格式
- 不修改认证/token 逻辑

---

### 任务 T04：Aurora 纠错协议统一 — 建立单一 `AuroraCorrectionPayload` 语义

**并行约束**: 无依赖，可立即开始

**愿景目标**:
无论用户从哪个入口（dashboard freeform、chat correction chip、chat freeform、status band correction、未来多端消息）发起纠错，后端接收到的都是同一种结构化的、可追踪的、可关联到用户画像的 payload。不再有"dashboard 发一种格式、chat 发另一种格式"的分叉。

**当前状态**:
- `CorrectionFeedbackProcessor` 已接受 `freeform_text`、`is_freeform`、`semantic_value`、`is_disconfirming` 参数
- Dashboard 发送 `aurora_correction` 含 `type`/`semantic_value`/`band_status`/`freeform_text`
- Chat 发送 `aurora_correction` 含 `type`/`semantic_value`/`is_disconfirming`/`is_freeform`/`freeform_text`/`band_status`
- 但：缺少统一的 `surface`/`source` 字段标识入口来源
- 缺少 `telemetry_id`/`group_id` 的前端→后端传递
- 缺少 `conversation_id`/`message_id` 的关联

**需要达到的效果**:

1. **定义 `AuroraCorrectionPayload` 协议** — 在后端创建统一的数据结构：
   ```
   AuroraCorrectionPayload:
     surface: str          # "dashboard" | "chat" | "status_band" | "push" | "core_session"
     source: str           # "freeform_input" | "predicted_chip" | "calibration_override"
     semantic_value: str   # 内部语义 token（metadata only，不展示给用户）
     label: str            # 用户可见的自然语言标签
     freeform_text: str    # 用户输入的自由文本（空串表示非 freeform）
     is_freeform: bool
     is_disconfirming: bool
     band_status: str      # 当前 Aurora 状态
     telemetry_id: str     # 前端生成的追踪 ID
     group_id: str         # 纠错分组 ID
     conversation_id: str  # 当前对话 ID
     message_id: str       # 关联消息 ID（如有）
   ```

2. **后端 CorrectionFeedbackProcessor 扩展** — `process()` 方法接受完整的 `AuroraCorrectionPayload`，记录 `surface` 和 `source` 到 correction 记录，用于后续分析哪个入口最常被使用

3. **`aurora.py` API 端点统一** — `/api/v1/aurora/correction` 端点接受统一 payload，分发到 `CorrectionFeedbackProcessor`

4. **Go Gateway 透传** — 确保 `aurora_correction` metadata 从 Flutter 通过 Go 到达 Python 时不丢失任何字段

**具体文件**:
- `backend/app/aurora/runtime_v1/correction_feedback.py` — 扩展 process() 接受完整 payload
- `backend/app/aurora/correction_types.py` — 新建统一 payload 定义
- `backend/app/api/v1/aurora.py` — 统一 API 端点
- `backend/app/services/agent_grpc_service.py` — 确保 gRPC metadata 透传
- `backend/gateway/internal/handler/` — 确保 WS metadata 透传
- `backend/tests/unit/test_aurora_correction_payload.py` — 新建 payload 归一化测试

**验收标准**:
- [ ] `AuroraCorrectionPayload` 数据类定义完整，包含上述所有字段
- [ ] `CorrectionFeedbackProcessor.process()` 接受并记录 surface/source/conversation_id
- [ ] 至少 3 个 pytest：dashboard 格式归一化、chat 格式归一化、freeform vs chip 路径
- [ ] 已有纠错测试（test_t33 等）全部继续通过
- [ ] 内部 semantic token 不出现在任何面向用户的输出中

**禁止事项**:
- 不修改 Proto 定义
- 不修改 `CorrectionFeedbackProcessor` 的置信度调整逻辑（-0.15/+0.05）
- 不修改 Bayesian learner 的更新逻辑
- 不删除任何现有纠错入口

---

### 任务 T05：Aurora 校准回执生成 — 纠错后用户看到"我调整了什么"

**并行约束**: 可与 T04 并行开始（先定义 receipt 数据结构，后端实现不依赖 T04 的 payload 统一）

**愿景目标**:
用户完成一次纠错后，不仅看到"已收到"的确认，还看到一段自然语言的校准回执，告诉用户 Aurora 具体调整了什么判断、下次会有什么变化。这段回执是从实际的 state patch 和 confidence 变化生成的，不是固定模板。

**当前状态**:
- `CorrectionFeedbackProcessor` 已返回 `CorrectionResult` 包含 `affected_state_keys`、`new_confidence`、`user_visible_effect`
- Flutter 的 `status_awareness_bar.dart` 有 `_CorrectionEffectPill` 显示"纠正已生效"
- 但：没有详细的"我具体调整了什么"的自然语言回执
- 没有 `calibration_receipt` 数据结构进入聊天 metadata

**需要达到的效果**:

1. **校准回执生成函数** — 在后端创建 `generate_calibration_receipt(correction_result: CorrectionResult) -> dict`：
   - 从 `affected_state_keys` 和 `new_confidence` 生成自然语言描述
   - 例如："我把'你可能压力很大'的判断置信度从 0.8 降到 0.6。下次遇到类似情境，我会先确认再提醒。"
   - 包含：调整了什么（what）、为什么（why，基于用户的 freeform_text 或 chip label）、下次会怎样（next_time）
   - 所有文本同时生成中英文版本

2. **回执数据结构** — `calibration_receipt`:
   ```
   calibration_receipt:
     correction_id: str
     what_changed: str          # 自然语言
     why_changed: str           # 引用用户输入
     next_time: str             # 下次会怎样
     affected_states: list      # 内部 state keys（metadata only）
     confidence_delta: float    # 置信度变化
     surface: str               # 来自哪个入口
     timestamp: str
   ```

3. **回执进入聊天 metadata** — 校准回执作为 `calibration_receipt` 字段进入 gRPC 响应的 metadata，Go Gateway 透传到 Flutter

4. **回执对后续对话的影响** — 校准回执写入用户画像的 `recent_corrections` 和 working memory，下一轮对话的 prompt 中 Aurora 能自然引用："上次你说其实不焦虑，我记住了。"

**具体文件**:
- `backend/app/aurora/runtime_v1/correction_feedback.py` — 添加 `generate_calibration_receipt()`
- `backend/app/orchestration/prompts.py` — 在 context 组装中包含 recent corrections
- `backend/app/services/memory_service.py` 或 working_memory — 写入 correction record
- `backend/tests/unit/test_calibration_receipt.py` — 新建回执生成测试

**验收标准**:
- [ ] `generate_calibration_receipt()` 能从 CorrectionResult 生成自然语言回执
- [ ] 回执包含 what/why/next_time 三要素
- [ ] 回执通过 gRPC metadata 到达 Flutter
- [ ] 下一轮对话的 prompt context 中包含 recent correction
- [ ] 至少 3 个 pytest：不同 correction 类型 → 不同回执内容；置信度变化的自然语言描述
- [ ] 回执文本有中英文版本

**禁止事项**:
- 不修改 Confidence delta 逻辑
- 不修改 Bayesian learner
- 不修改 gRPC proto 定义（使用现有 metadata 字段）

---

### 任务 T06：Go SlidingWindow Rate Limiter 优化 — Lua Script 复用

**并行约束**: 无依赖，可立即开始

**愿景目标**:
每次请求不再创建新的 Lua script 对象，减少 GC 压力。Token Bucket 实现已正确使用包级变量，SlidingWindow 应与之一致。

**当前状态**:
- `distributed_rate_limiter.go:41` — `distributedTokenBucketScript` 正确使用包级变量
- `distributed_rate_limiter.go:236` — `SlidingWindowRateLimiter.Allow()` 每次调用创建 `redis.NewScript()`

**需要达到的效果**:

1. 将 `SlidingWindowRateLimiter` 的 Lua script 移到包级变量
2. 确保线程安全（`redis.Script` 本身是线程安全的）
3. 性能对比基准测试（可选，如果有 benchmark 基础设施）

**具体文件**:
- `backend/gateway/internal/middleware/distributed_rate_limiter.go` — 移动 Lua script
- `backend/gateway/internal/middleware/distributed_rate_limiter_test.go` — 确保测试通过

**验收标准**:
- [ ] `SlidingWindowRateLimiter` 不在 `Allow()` 内创建 `redis.NewScript()`
- [ ] Lua script 声明为包级变量
- [ ] 已有 5 个 distributed_rate_limiter 测试全部通过

**禁止事项**:
- 不修改限流算法逻辑
- 不修改限流参数（速率、突发上限）

---

## Wave 2：体验连续性与校准回执（6 个任务）

### 任务 T07：Flutter 纠错协议统一 — 所有入口发送标准 payload

**并行约束**: 依赖 T04（后端 payload 定义完成）

**愿景目标**:
Flutter 端所有纠错入口（dashboard freeform、chat correction chip、chat freeform、status band correction）发送完全一致的 `aurora_correction` payload 格式，包含 `surface` 和 `source` 字段标识来源。

**当前状态**:
- Dashboard（`dashboard_screen.dart`）发送 `aurora_correction` 含 `type: 'freeform'`/`'chip'`/`'cooldown_override'`
- Chat（`chat_screen.dart`）发送 `aurora_correction` 含 `type: 'freeform'`，有 `freeform_text`/`is_freeform`/`is_disconfirming`
- Status band 发送 correction 但字段不完全一致
- 缺少 `surface`/`source`/`telemetry_id`/`group_id`/`conversation_id`/`message_id`

**需要达到的效果**:

1. **统一 payload helper** — 创建 `AuroraCorrectionPayload` Dart 类：
   - 所有纠错入口使用同一个 factory constructor
   - 自动填充 `surface`（根据调用位置）、`conversation_id`（从 chat state 获取）、`message_id`（从当前消息获取）
   - 生成 `telemetry_id`（UUID v4）和 `group_id`（按 session 分组）

2. **Dashboard 入口改造** — `dashboard_screen.dart` 中所有 `aurora_correction` 使用统一 helper，`surface: 'dashboard'`

3. **Chat 入口改造** — `chat_screen.dart` 中的 predicted chip 和 freeform 使用统一 helper，`surface: 'chat'`

4. **Status Band 入口改造** — `status_awareness_bar.dart` 和 `contextual_correction_bar.dart` 使用统一 helper，`surface: 'status_band'`

5. **验证无内部 token 外泄** — 确保 `semantic_value` 只存在于 `aurora_correction` 的 metadata 中，不出现在用户可见的聊天消息文本中

**具体文件**:
- `mobile/lib/core/models/aurora_correction_payload.dart` — 新建统一 payload
- `mobile/lib/features/home/presentation/screens/dashboard_screen.dart` — 使用统一 helper
- `mobile/lib/features/chat/presentation/screens/chat_screen.dart` — 使用统一 helper
- `mobile/lib/features/chat/presentation/widgets/contextual_correction_bar.dart` — 使用统一 helper
- `mobile/lib/features/chat/presentation/widgets/status_awareness_bar.dart` — 使用统一 helper

**验收标准**:
- [ ] 所有纠错入口使用同一个 `AuroraCorrectionPayload` 类
- [ ] Dashboard/chip/freeform/status band 各场景的 payload 含正确的 `surface` 和 `source`
- [ ] `semantic_value` 不出现在用户可见的聊天消息文本中
- [ ] 至少 4 个 widget test：dashboard freeform、chat chip、chat freeform、status band correction 各一个
- [ ] 已有纠错相关 widget test 全部通过

**禁止事项**:
- 不修改纠错的后端处理逻辑
- 不修改 `auroraCorrectionPresentationFor()` 的自然语言映射
- 不删除任何现有纠错入口

---

### 任务 T08：校准回执 Flutter 体验 — 用户看到"Aurora 调整了什么"

**并行约束**: 依赖 T05（后端回执生成完成）

**愿景目标**:
用户完成纠错后，在聊天中看到一段安静的、可展开的校准回执卡片，告诉用户 Aurora 具体调整了什么。这段回执不是 Toast 或弹窗，而是 inline 的 receipt chip，用户可以忽略也可以点击查看详情。

**当前状态**:
- `_CorrectionEffectPill` 显示简短的"纠正已生效"
- `context_receipt_bar.dart` 已有 receipt 渲染框架
- 但：没有详细的"我调整了什么"的回执展示

**需要达到的效果**:

1. **CalibrationReceiptChip** — 在聊天消息旁（通过 context_receipt_bar）显示校准回执：
   - 一句话摘要："Aurora 调整了关于[判断]的理解"
   - 点击展开：完整回执（what/why/next_time）
   - 可关闭，关闭后不再展示此条回执

2. **回执动画** — 校准回执使用淡入动画进入，不突兀打断对话流

3. **回执与下一轮对话的一致性** — 用户看到回执后下一轮对话中 Aurora 的回复风格确实发生了变化（这是后端 T05 的职责，但 Flutter 需要确保回执被正确展示）

4. **回执 i18n** — 回执文本使用后端返回的中英文版本，不硬编码

**具体文件**:
- `mobile/lib/features/chat/presentation/widgets/calibration_receipt_chip.dart` — 新建
- `mobile/lib/features/chat/presentation/widgets/context_receipt_bar.dart` — 集成 calibration receipt
- `mobile/lib/features/chat/presentation/widgets/status_awareness_bar.dart` — 增强效果展示
- `mobile/test/features/chat/presentation/widgets/calibration_receipt_chip_test.dart` — 新建

**验收标准**:
- [ ] 校准回执在纠错完成后以 chip 形式展示在聊天中
- [ ] 点击 chip 展示完整的 what/why/next_time
- [ ] 回执有淡入动画
- [ ] 回执文本使用后端返回的中英文，不硬编码
- [ ] 暗色模式和 Semantics 完整
- [ ] 至少 2 个 widget test：chip 渲染、chip 展开
- [ ] 内部 semantic token 不出现在回执 UI 中

**禁止事项**:
- 不修改回执的后端生成逻辑
- 不使用弹窗或 Toast 展示回执
- 不在首次使用时强制引导

---

### 任务 T09：离线消息队列 UI 指示器

**并行约束**: 可与 Wave 1 并行开始（纯 Flutter，不依赖后端改动）

**愿景目标**:
用户在网络断开时发送消息，能清楚看到消息正在排队，排队数量是多少。网络恢复后，看到消息逐条发送的状态变化。不再有"消息去哪了"的困惑。

**当前状态**:
- `OfflineMessageQueueService` 有 `pendingCount(userId)` 方法
- 排队/重发逻辑完整
- 但：`pendingCount()` 从未被 UI 层调用
- 没有离线状态 badge 或 indicator

**需要达到的效果**:

1. **离线状态指示器** — 在聊天输入框上方或附近添加轻量指示器：
   - 在线状态：不显示任何东西（零噪音）
   - 离线排队中：显示小 badge "N 条消息等待发送" + 离线 icon
   - 恢复发送中：显示 "正在发送..." 的进度指示
   - 发送完成：短暂显示 "已全部发送" 后消失

2. **消息状态标记** — 排队中的消息在聊天气泡上有不同的视觉状态：
   - 正常消息：无特殊标记
   - 排队中：灰色半透明 + 小 clock icon
   - 发送中：灰色 + spinner
   - 发送失败：红色 + 重试按钮

3. **状态监听** — 使用 `OfflineMessageQueueService` 的 stream 或定时器刷新 pending count

4. **暗色模式 + Semantics** — 指示器支持暗色模式和屏幕阅读器

**具体文件**:
- `mobile/lib/features/chat/presentation/widgets/offline_queue_indicator.dart` — 新建
- `mobile/lib/features/chat/presentation/screens/chat_screen.dart` — 集成指示器
- `mobile/lib/features/chat/presentation/widgets/chat_bubble.dart` — 消息状态标记
- `mobile/lib/core/offline/offline_providers.dart` — 暴露 pendingCount 给 UI
- `mobile/test/features/chat/presentation/widgets/offline_queue_indicator_test.dart` — 新建

**验收标准**:
- [ ] 离线排队时聊天输入框旁显示排队数量 badge
- [ ] 排队中的消息有视觉区分（灰色 + icon）
- [ ] 网络恢复后 badge 更新为"发送中"→"已发送"→消失
- [ ] 暗色模式和 Semantics 完整
- [ ] 至少 3 个 widget test：离线状态显示、恢复发送状态、发送完成消失

**禁止事项**:
- 不修改离线消息的存储和重发逻辑
- 不修改 WebSocket 重连机制
- 不在每次打开聊天时弹出离线状态弹窗

---

### 任务 T10：核心 Provider 状态保持 — 避免 Tab 切换丢失上下文

**并行约束**: 可与 Wave 1 并行开始（纯 Flutter 状态管理）

**愿景目标**:
用户在 Sparkle 内切换 Tab（首页→聊天→星图→我的）后再回来，看到的是之前的状态，不是重新加载的白屏。核心状态（用户画像、Aurora 状态、聊天历史、当前计划）在 Tab 切换时保持不丢失。

**当前状态**:
- 搜索 `.keepAlive` 返回零匹配
- 所有 provider 使用 auto-dispose 模式
- Tab 切换时 provider 被销毁，回来后重新初始化

**需要达到的效果**:

1. **核心 Provider keepAlive** — 为以下核心 provider 添加 `keepAlive: true`：
   - 用户画像 provider（user profile）
   - Aurora 状态 provider（auroraStatusProvider）
   - 聊天历史 provider（核心对话记录）
   - 当前计划 provider
   - 设计系统/主题 provider
   - BGM provider

2. **非核心 Provider 保持 auto-dispose** — 页面级的数据（如某个具体的星图节点详情、某个任务的详情）保持 auto-dispose，避免内存泄漏

3. **失效机制** — keepAlive provider 需要手动失效的场景：
   - 用户登出时 invalidate 所有核心 provider
   - 用户执行了修改画像的操作后 invalidate 对应 provider
   - 长时间不活跃后可选择 refresh（不 dispose）

4. **内存监控** — 确认添加 keepAlive 后不会导致内存显著增长（核心 provider 数据量不大，风险可控）

**具体文件**:
- `mobile/lib/features/chat/presentation/providers/` — 核心聊天 provider
- `mobile/lib/features/aurora/presentation/providers/` — Aurora 状态 provider
- `mobile/lib/features/user/presentation/providers/` — 用户画像 provider
- `mobile/lib/features/plan/presentation/providers/` — 计划 provider
- `mobile/lib/core/services/bgm_service.dart` — BGM provider（如果使用 Riverpod）

**验收标准**:
- [ ] 至少 6 个核心 provider 标记为 keepAlive
- [ ] Tab 切换后核心状态保持（Aurora 状态、聊天历史、用户画像不重新加载）
- [ ] 登出时所有 keepAlive provider 正确 invalidate
- [ ] 页面级数据仍为 auto-dispose（不泄漏）
- [ ] 至少 2 个 widget test：Tab 切换后状态保持、登出后状态清理

**禁止事项**:
- 不将所有 provider 都改为 keepAlive（需要区分核心 vs 页面级）
- 不修改 provider 的数据获取逻辑
- 不修改 Tab 切换的路由逻辑

---

### 任务 T11：冷启动与回归过渡体验 — splash→chat 自然衔接

**并行约束**: 可与 Wave 1/2 并行开始

**愿景目标**:
用户冷启动 App 后，从 splash 到聊天/Aurora 状态的过渡不是生硬的页面跳转，而是自然流畅的衔接。如果用户有回归消息，过渡更温暖。这是收敛计划中 B5 唯一未完成的缺口。

**当前状态**:
- `AuroraComebackContext` 有 4 时间层级回归逻辑（<30min/30min-8h/>8h/>3d）
- `ComebackBanner` widget 存在
- 但：splash→chat 的过渡动画缺失，页面切换生硬

**需要达到的效果**:

1. **Splash→Chat 过渡动画** — 从 splash screen 到聊天首屏的过渡：
   - 不是瞬间跳转，使用 `PageRouteBuilder` 的自定义 transition
   - 如果有回归消息：splash 标志淡出的同时聊天界面淡入，回归消息以微妙的入场动画出现
   - 如果没有回归消息：简单的 cross-fade 过渡
   - 过渡时长约 400ms

2. **回归消息入场动画** — `ComebackBanner` 使用 `SparkleStaggerItem` 做渐进式内容浮现：
   - 先显示问候语（100ms delay）
   - 再显示上次主题摘要（200ms delay）
   - 最后显示未完成事项入口（300ms delay）

3. **Tab 切换时的子页面过渡** — 从首页进入聊天时，使用 hero 或 slide 动画保持视觉连续

4. **过场不阻塞交互** — 所有动画期间不阻塞用户输入（如果用户快速点击，动画立即完成）

**具体文件**:
- `mobile/lib/app/routes.dart` — 自定义 transition
- `mobile/lib/features/splash/` — splash 过渡
- `mobile/lib/features/chat/presentation/widgets/comeback_banner.dart` — 入场动画
- `mobile/lib/app/app.dart` — 冷启动过渡

**验收标准**:
- [ ] Splash→Chat 有自定义过渡动画（非默认 MaterialPageRoute）
- [ ] 回归消息有分阶段入场动画（SparkleStaggerItem 或等效）
- [ ] 过渡期间用户点击可立即跳过动画
- [ ] 暗色模式下过渡动画正常
- [ ] 至少 2 个 widget test：过渡存在、回归消息入场动画

**禁止事项**:
- 不修改 splash screen 的认证逻辑
- 不修改 WebSocket 重连机制
- 不添加超过 500ms 的延迟

---

### 任务 T12：Session ID 传播可靠性 — 消除对话连续性断裂

**并行约束**: 可与 Wave 1 并行开始

**愿景目标**:
用户的每一轮对话都通过 session_id 关联到同一个对话上下文。不会因为 orchestrator 忘记设置 session_id 而生成新 UUID，导致上下文断裂。

**当前状态**:
- `agent_grpc_service.py:234-235` — 当 response.session_id 为空且 request.session_id 也为空时自动生成新 UUID
- 这是防御性 fallback，但如果 orchestrator 持续忘记设置 session_id，每一轮都会是新对话

**需要达到的效果**:

1. **Orchestrator session_id 保证** — 确保 orchestrator 在每次响应中都设置 session_id：
   - 如果是新对话，使用生成的新 ID 并存储到 FSM context
   - 如果是延续对话，从 FSM context 中读取并返回
   - 添加 assert 或 warning：如果 orchestrator 的 response 没有 session_id 且不是首次请求，记录 warning

2. **Go Gateway session_id 透传** — 确认 Go Gateway 在 WebSocket 重连时正确传递 session_id

3. **Flutter session_id 保持** — 确认 Flutter 在 provider refresh 后不丢失 session_id（与 T10 keepAlive 联动）

4. **Fallback 改进** — 当 fallback 触发（自动生成 UUID）时：
   - 记录 warning 日志
   - 递增 Prometheus counter `sparkle_session_id_fallback_total`

**具体文件**:
- `backend/app/orchestration/orchestrator.py` — 确保 session_id 设置
- `backend/app/services/agent_grpc_service.py` — 添加 warning 和 metric
- `backend/gateway/internal/handler/chat_orchestrator.go` — 确认透传
- `mobile/lib/features/chat/presentation/providers/chat_provider.dart` — 确认保持

**验收标准**:
- [ ] Orchestrator 每次响应都包含 session_id（除非是明确的首次请求）
- [ ] Fallback 触发时有 warning 日志和 Prometheus metric
- [ ] 至少 2 个 pytest：正常 session 传播、fallback 触发时的 metric
- [ ] 已有 orchestrator 测试继续通过

**禁止事项**:
- 不修改 session 的存储格式
- 不修改 session TTL 逻辑
- 不修改 WebSocket 重连的核心机制

---

## Wave 3：工程质量 + 文档收敛（3 个任务）

### 任务 T13：Python 异常处理审计 — 减少 silent swallow

**并行约束**: 可与 Wave 2 并行开始

**愿景目标**:
生产代码中不再有大规模的 `except Exception: pass` 吞掉异常。每个异常要么被明确处理（记录日志、重试、降级），要么被显式声明为"预期的、可忽略的"并附带注释说明原因。

**当前状态**:
- 88 处 `except Exception: pass`（~75 处在生产代码）
- Top 文件：aurora.py(5)、orchestrator_production.py(5)、preference_consumption_service.py(4)
- 部分已有注释说明（如 "# Non-critical"），但大部分没有

**需要达到的效果**:

1. **优先级审计** — 将 75 处分为三类：
   - **必须修复**：安全关键路径（auth、token、PII）和用户关键路径（chat、plan execution）— 改为 `logger.error()` + 明确处理
   - **建议修复**：非关键路径但有价值的信息 — 改为 `logger.warning()`
   - **合理保持**：已注释说明原因的、测试代码中的、backup/非生产脚本中的 — 保持不变但验证注释充分

2. **优先修复前 5 文件**：
   - `app/api/v1/aurora.py` (5处)
   - `app/orchestration/orchestrator_production.py` (5处)
   - `app/services/preference_consumption_service.py` (4处)
   - `app/signals/spine_orchestrator.py` (4处)
   - `app/services/theater/prediction_theater_service.py` (4处)

3. **`aurora/runtime_v1/__init__.py` 的 11 处** — 从 `except ModuleNotFoundError: pass` 改为 `except ModuleNotFoundError as e: logger.debug(f"Optional Aurora module not loaded: {e}")`

4. **安全关键路径** — 确保 `security.py` 的 `verify_password` 和 `is_token_revoked` 的 `except Exception: return False` 有明确的注释说明这是有意为之的 fail-open 设计

**具体文件**:
- `backend/app/api/v1/aurora.py`
- `backend/app/orchestration/orchestrator_production.py`
- `backend/app/services/preference_consumption_service.py`
- `backend/app/signals/spine_orchestrator.py`
- `backend/app/services/theater/prediction_theater_service.py`
- `backend/app/aurora/runtime_v1/__init__.py`
- `backend/app/core/security.py`

**验收标准**:
- [ ] 前 5 文件的 `except Exception: pass` 全部替换为带日志的版本或明确注释
- [ ] `aurora/runtime_v1/__init__.py` 11 处添加 `logger.debug()`
- [ ] 安全关键路径有明确注释
- [ ] `grep -r "except Exception:" --include="*.py" backend/app/ | grep -v "test" | grep -v "as e" | wc -l` 减少 50% 以上
- [ ] 已有测试全部通过

**禁止事项**:
- 不改变异常处理的行为语义（fail-open 的还是 fail-open，只是不再静默）
- 不引入新的异常类型
- 不修改 `aurora/runtime_v1/__init__.py` 的模块加载逻辑

---

### 任务 T14：CI/CD 版本一致性 + 工程基建收尾

**并行约束**: 可与 Wave 2/3 并行开始

**愿景目标**:
所有 CI/CD 工作流使用统一的技术栈版本，确保 CI 测试结果与生产环境一致。Python 依赖有 lockfile 保证可复现构建。

**当前状态**:
- Flutter: CI 用 3.24.0，e2e/benchmark 用 3.16.0
- PostgreSQL: CI 用 pg16+pgvector，e2e/benchmark 用 pg15（无 pgvector）
- GitHub Actions: e2e 用 setup-python@v4/setup-go@v4/codecov@v3，CI 用 v5
- Docker: redis-stack-server 和 minio 用 latest
- Python: 所有依赖用 >= 范围，无 lockfile

**需要达到的效果**:

1. **Flutter 版本统一** — 所有工作流使用 3.24.0
2. **PostgreSQL 版本统一** — 所有工作流使用 pg16+pgvector
3. **Actions 版本同步** — e2e-tests.yml 使用与 ci.yml 相同的 action 版本
4. **Docker 版本锁定** — redis-stack-server 和 minio 锁定到具体版本号
5. **Python lockfile** — 使用 `pip-compile` 或 `uv lock` 生成 lockfile，CI 使用锁定版本

**具体文件**:
- `.github/workflows/e2e-tests.yml` — 版本更新
- `.github/workflows/benchmark.yml` — 版本更新
- `docker-compose.yml` — 锁定 redis/minio 版本
- `docker-compose.prod.yml` — 同步锁定
- `backend/requirements.txt` 或 `backend/pyproject.toml` — lockfile 集成

**验收标准**:
- [ ] 所有工作流的 Flutter 版本一致（3.24.0）
- [ ] 所有工作流的 PostgreSQL 版本一致（pg16+pgvector）
- [ ] e2e-tests.yml 的 Action 版本与 ci.yml 一致
- [ ] docker-compose.yml 中 redis/minio 不使用 latest
- [ ] Python lockfile 存在（`requirements.lock` 或 `uv.lock`）
- [ ] CI 的 lint + test job 通过

**禁止事项**:
- 不升级 Flutter 大版本（只统一到已验证的 3.24.0）
- 不修改 ci.yml 的工作流结构
- 不删除任何 CI job

---

### 任务 T15：文档收敛与验证报告追踪

**并行约束**: 依赖所有其他任务有明确进展后开始（可在 Wave 2 后半段启动）

**愿景目标**:
所有发现、修复、延迟决策都有文档追踪。验收总账、Roadmap Tracker、独立验证报告的状态保持同步。本轮收口完成后，任何新来的开发者都能通过文档了解"做了什么、为什么做、还剩什么"。

**当前状态**:
- `SPARKLE_INDEPENDENT_VERIFICATION_REPORT_2026-05-01.md` 已创建但未被 Git 追踪
- `SPARKLE_FINAL_ACCEPTANCE_LEDGER_2026-05-01.md` 最后更新到 R18
- `SPARKLE_ROADMAP_v3_TRACKER_2026-04-28.md` 最后更新到 Closeout Dispatch
- 收敛计划 `SPARKLE_AURORA_CONVERGENCE_PLAN_2026-05-01.md` 未被追踪

**需要达到的效果**:

1. **验证报告纳入追踪** — 将 `SPARKLE_INDEPENDENT_VERIFICATION_REPORT_2026-05-01.md` 提交到 Git，标注验证日期和结论

2. **验收总账更新** — 在 `SPARKLE_FINAL_ACCEPTANCE_LEDGER_2026-05-01.md` 新增 Section 20：
   - 记录本轮 T01-T15 的修复状态
   - 每个任务标记：`FIXED` / `FIXED-IN-PASS` / `DEFERRED`
   - 测试运行证据

3. **Roadmap Tracker 更新** — 更新 `SPARKLE_ROADMAP_v3_TRACKER_2026-04-28.md`：
   - 新增 "2026-05-01 Aurora Closeout Verification" section
   - 记录验证报告中确认的真实问题和修复状态
   - 记录假阳性清单（避免未来重复审计）

4. **收敛计划归档** — 将 `SPARKLE_AURORA_CONVERGENCE_PLAN_2026-05-01.md` 提交到 Git

5. **每个发现的状态** — 文档中每个问题标记为以下之一：
   - `verified fixed` — 已验证修复
   - `fixed in this pass` — 本轮修复
   - `deferred with reason` — 延迟并附原因

**具体文件**:
- `docs/product/SPARKLE_INDEPENDENT_VERIFICATION_REPORT_2026-05-01.md` — Git 追踪
- `docs/product/SPARKLE_FINAL_ACCEPTANCE_LEDGER_2026-05-01.md` — 新增 Section 20
- `docs/product/SPARKLE_ROADMAP_v3_TRACKER_2026-04-28.md` — 更新状态
- `docs/product/SPARKLE_AURORA_CONVERGENCE_PLAN_2026-05-01.md` — Git 追踪
- `docs/product/SPARKLE_AURORA_CLOSEOUT_PLAN_2026-05-01.md` — 本执行方案（Git 追踪）

**验收标准**:
- [ ] 验证报告已提交到 Git
- [ ] 收敛计划已提交到 Git
- [ ] 本执行方案已提交到 Git
- [ ] 验收总账新增 Section 20，记录 T01-T15 状态
- [ ] Roadmap Tracker 更新验证结果
- [ ] 文档中每个发现都有 `verified fixed` / `fixed in this pass` / `deferred with reason` 状态标记

**禁止事项**:
- 不修改历史 section 的内容（只添加新 section）
- 不删除任何已关闭的 issue 记录
- 不修改验证报告的事实性内容

---

## 任务依赖关系图

```
Wave 1 (全部并行，无依赖):
  T01: WebSocket 关闭安全     ← 无依赖
  T02: 错误响应脱敏           ← 无依赖
  T03: Handler 服务层隔离     ← 无依赖
  T04: 纠错协议统一(后端)     ← 无依赖
  T05: 校准回执生成(后端)     ← 无依赖（可与 T04 并行）
  T06: Rate Limiter 优化      ← 无依赖

Wave 2 (部分依赖 Wave 1):
  T07: 纠错协议统一(Flutter)  ← 依赖 T04
  T08: 校准回执 Flutter 体验  ← 依赖 T05
  T09: 离线队列 UI            ← 无依赖
  T10: Provider keepAlive     ← 无依赖
  T11: 冷启动过渡体验         ← 无依赖
  T12: Session ID 传播        ← 无依赖

Wave 3 (可与 Wave 2 后半段并行):
  T13: Python 异常审计        ← 无依赖
  T14: CI/CD 版本统一         ← 无依赖
  T15: 文档收敛               ← 依赖 T01-T14 有明确进展
```

## 并行执行建议

### 第一批（6 Agent 同时开工）
T01, T02, T03, T04, T05, T06 — Wave 1 全部任务

### 第二批（6 Agent 在第一批部分完成后开工）
T07（等 T04）, T08（等 T05）, T09, T10, T11, T12

### 第三批（3 Agent 在前两批完成后开工）
T13, T14, T15

---

## 全局成功标准

完成全部 15 个任务后，应达到以下效果：

1. **用户纠错后感到 Aurora 真的调整了**:
   - 统一 payload 从所有入口进入后端
   - 校准回执让用户看到"我调整了什么"
   - 下一轮对话体现变化

2. **用户在网络不稳定时不再困惑**:
   - 离线排队有可见状态
   - 消息发送状态清晰

3. **用户在 Tab 切换和冷启动后感到连续**:
   - 核心状态不丢失
   - 回归过渡自然温暖
   - Session 不会断裂

4. **生产路径稳定可信赖**:
   - WebSocket 关闭不 panic
   - 错误响应不泄露内部细节
   - 异常不再静默吞掉

5. **工程基础一致可维护**:
   - CI/CD 版本统一
   - 依赖可锁定复现
   - 文档状态同步

---

## 附录 A：并行安全地图

以下文件被多个任务涉及，需要序列化访问或明确分区：

| 文件 | 涉及任务 | 冲突风险 | 解决方案 |
|------|---------|---------|---------|
| `chat_orchestrator.go` | T01, T02 | 低（T01 改关闭逻辑，T02 改错误消息，不同区域） | 各自修改不同函数 |
| `agent_grpc_service.py` | T04, T12 | 中（都可能修改 metadata 处理） | T04 先完成，T12 基于 T04 的结果 |
| `chat_screen.dart` | T07, T09 | 低（T07 改纠错 payload，T09 添加离线指示器，不同区域） | 各自修改不同 widget |
| `dashboard_screen.dart` | T07 | 单任务 | 无冲突 |
| `status_awareness_bar.dart` | T07, T08 | 中（都可能修改 receipt 区域） | T07 先完成纠错 payload，T08 在其基础上添加回执 |
| `context_receipt_bar.dart` | T08 | 单任务 | 无冲突 |

---

## 附录 B：验收命令速查

```bash
# Go Gateway
cd backend/gateway && go test ./...
cd backend/gateway && go vet ./...

# Python Backend
cd backend && pytest tests/unit/test_aurora_correction_payload.py -v
cd backend && pytest tests/unit/test_calibration_receipt.py -v
cd backend && pytest tests/unit/test_t33_predicted_reply_correction.py -v
cd backend && pytest tests/golden/ -v

# Flutter
cd mobile && flutter test test/features/chat/ test/features/aurora/ test/features/home/

# Config Consistency
python3 scripts/check_aurora_config_consistency.py

# Production Secrets Check
python3 scripts/check_production_secrets.py --tracked-only

# Static Checks
grep -r "except Exception:" --include="*.py" backend/app/ | grep -v "test" | grep -v "as e" | wc -l
grep -r "err.Error()" --include="*.go" backend/gateway/internal/handler/ | wc -l
```

---

## 附录 C：与独立验证报告的对应关系

| 验证报告编号 | 问题 | 本方案任务 |
|-------------|------|-----------|
| R-01 | idleTimer 竞态条件 | T01 |
| R-02 | 23+ 处 err.Error() 泄露 | T02 |
| R-03 | Handler 直接访问 DB | T03 |
| R-04 | 88 处 except Exception: pass | T13 |
| R-05 | Session_id 自动 UUID | T12 |
| R-06 | Provider 无 keepAlive | T10 |
| R-07 | 离线队列无 UI | T09 |
| R-08 | SlidingWindow Lua script | T06 |
| R-09~R-13 | CI/CD 版本不一致 | T14 |
| R-14 | Semantics 覆盖率 | 各任务分别处理 |
| R-15 | Aurora runtime 静默导入 | T13 |
| 收敛计划 B5 缺口 | 冷启动动画 | T11 |
| 用户方案 Key Change 1 | 纠错协议统一 | T04 + T07 |
| 用户方案 Key Change 2 | "真的懂我"体感 | T05 + T08 |
| 用户方案 Key Change 3 | 核心体验连续性 | T09 + T10 + T11 + T12 |
| 用户方案 Key Change 4 | 生产信任底座 | T01 + T02 + T03 + T06 |
| 用户方案 Key Change 5 | 文档收敛 | T15 |
