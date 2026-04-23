# 深度审计 #47 — ChatOrchestrator Chatflow 核心聊天请求处理

> **日期**: 2026-04-24 11:00
> **模块**: Go Gateway ChatOrchestrator Chatflow — 用户消息 → 配额预留 → 语义缓存 → gRPC 流式聊天 → 流式转发 → 配额记录 → 历史持久化完整链路
> **范围**: `chat_orchestrator_chatflow.go`（729 行）+ `chat_orchestrator_protocol.go`（convertResponseToJSON 215 行）+ `chat_orchestrator.go`（sanitizer/stringBuilderPool/chatInput）
> **审计员**: Claude Deep Auditor (Round 47)

---

## 审计范围

`handleChatMessage` 是 Sparkle 系统的**最关键请求路径**。每一条用户聊天消息都经过此函数处理：从 WebSocket 接收用户消息，经过输入消毒、身份解析、上下文组装、语义缓存检查、配额预留、gRPC 流式调用 Python 后端、流式转发响应给客户端、配额记录、历史持久化。

### 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `gateway/internal/handler/chat_orchestrator_chatflow.go` | 729 | 核心聊天请求处理全链路 |
| `gateway/internal/handler/chat_orchestrator_protocol.go` | 602 | protobuf→JSON 转换 + getEnvInt64 |
| `gateway/internal/handler/chat_orchestrator.go` | ~120 | sanitizer + stringBuilderPool + chatInput 定义 |
| `gateway/internal/handler/ws_safe_writer.go` | 67 | WebSocket 安全写入封装 |

**总计**: 4 核心文件, ~1,518 行

---

## 数据流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Flutter → WebSocket → handleChatMessage (:198)                         │
│                                                                         │
│  处理流程:                                                              │
│    1. 输入消毒 (:219)                                                   │
│       input.Message = sanitizer.Sanitize(input.Message) ✅              │
│                                                                         │
│    2. 用户消息持久化 (:222-226)                                          │
│       saveMessage(userID, sessionID, "user", message) ✅                │
│                                                                         │
│    3. 身份解析 (:236)                                                   │
│       resolveUserIdentity → UUID / email fallback ✅                    │
│                                                                         │
│    4. 用户上下文获取 (:253-297)                                          │
│       userContext.GetUserContextData → JSON string ✅                    │
│                                                                         │
│    5. 语义缓存检查 (:307-366)                                            │
│       semanticCacheScope(userID, mode, ctxHash, files, refs)            │
│       ❌ P1-3: ctxHash 包含完整 userContextJSON → 活跃用户几乎无缓存命中 │
│                                                                         │
│    6. 配额预留 (:384-407)                                               │
│       quota.ReserveRequest(userID, reqID, 24h)                          │
│       ❌ P0-1: 流失败时永不退还 — 配额泄漏                               │
│                                                                         │
│    7. gRPC 流式调用 (:456-471)                                           │
│       agentClient.StreamChatWithFallback → server streaming             │
│                                                                         │
│    8. 流式转发 + 中流配额检查 (:491-589)                                 │
│       segmentSize = getEnvInt64("STREAM_TOKEN_SEGMENT", 200)            │
│       estimatedTokens = runes * 1.5 (:719)                              │
│       ❌ P0-2: 英文文本 token 估算偏高 ~6x → 过早配额耗尽               │
│       mid-stream quota exceeded → cancel() → return                     │
│       ❌ P0-1: cancel 后不退还配额预留                                   │
│                                                                         │
│    9. 最终使用量记录 (:592-612)                                          │
│       RecordUsage(userID, reqID, delta, 24h)                            │
│       ❌ P0-1: 中流退出时此步不执行 → 预留+分段双计                     │
│                                                                         │
│   10. 元数据 + 完成响应 (:614-689)                                       │
│       ❌ P1-1: SendMeta/SendChatResponse 错误被 _ 丢弃                  │
│                                                                         │
│   11. 历史持久化 + 异步缓存更新 (:691-710)                               │
│       saveMessage("assistant", fullText) ✅ 同步                         │
│       semantic.SetExact → goroutine ✅ 异步                             │
│                                                                         │
│  全局问题:                                                              │
│    ❌ P1-2: input.FileIds 未消毒 — 客户端数组直接传 gRPC                │
│    ❌ P1-4: buildAgentUserProfile 硬编码 timezone/language — i18n 十连   │
│    ❌ P1-5: input.Message 无长度限制 — 超大消息直接传 gRPC              │
│    ❌ P2-1: getEnvInt64 每次请求调用 — 未缓存                           │
│    ❌ P2-2: SHA-1 用于缓存 key 散列 — 使用已破解算法                    │
│    ❌ P2-3: isDevelopmentEnv() 每次请求调用 — 未缓存                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 审计发现

### P0 — 严重缺陷

#### P0-1: 配额预留永不退还 — 每次失败请求永久泄漏配额
**文件**: `chat_orchestrator_chatflow.go:384-407, 460-471, 501-511, 540-553`
**严重性**: P0 — 配额泄漏导致用户无法使用系统

```go
// :384-407 — 预留配额（从 user:quota:{uid} 扣减）
remaining, err := h.quota.ReserveRequest(quotaCtx, userID, reqID, 24*time.Hour)

// :460-471 — gRPC 调用失败
stream, err := h.agentClient.StreamChatWithFallback(grpcCtx, req)
if err != nil {
    // ← 发送错误给客户端，但永不退还 ReserveRequest
    r.SendError("unavailable", "AI Service Unavailable", true)
    return false
}

// :501-511 — 流中断
if err != nil {
    // ← 同样不退还
    r.SendError("aborted", "Stream interrupted", true)
    break
}

// :540-553 — 中流配额超限
if dailyUsageStart+segmentRecorded+segmentSize > dailyLimit {
    cancel()
    r.SendError("resource_exhausted", "Daily quota exceeded", false)
    return false  // ← 不退还，且后续 RecordUsage 不执行
}
```

**三重泄漏路径**:

| 失败场景 | ReserveRequest | RecordUsageSegment | RecordUsage | 净效果 |
|----------|---------------|-------------------|-------------|--------|
| gRPC 连接失败 | ✅ 已扣减 | ✗ 不执行 | ✗ 不执行 | 预留泄漏 |
| 流中断 (Recv err) | ✅ 已扣减 | 部分 (已记录的段) | ✗ 不执行 | 预留+部分记录泄漏 |
| 中流配额超限 | ✅ 已扣减 | ✅ 已记录多段 | ✗ 不执行 | 预留+段双计 |

**攻击场景**: 后端不稳定时，用户每次重试都永久扣减预留配额。10 次失败重试可能消耗全部日配额，即使从未成功获取 AI 回复。

**修复方向**: (1) 失败时调用 `quota.Refund(userID, reqID)` 退还预留；(2) 或改用"仅记录不预留"模式，流成功结束后才扣减。

---

#### P0-2: `estimateTokensFromRunes` 1.5 倍乘数对英文偏估约 6 倍 — 英文用户配额过早耗尽
**文件**: `chat_orchestrator_chatflow.go:715-724`
**严重性**: P0 — 英文用户配额实际可用量仅为声明的 ~17%

```go
// :715-724 — token 估算函数
func estimateTokensFromRunes(runes int) int64 {
    if runes <= 0 {
        return 0
    }
    estimated := int64(float64(runes) * 1.5)  // ← Unicode 码点数 × 1.5
    if estimated < 1 {
        return 1
    }
    return estimated
}
```

**问题**: 函数将 Unicode 码点数（rune count）乘以 1.5 作为 token 估算。但不同语言的 token 化比率差异巨大：

| 语言 | 实际比率 (rune/token) | 估算比率 (rune×1.5/token) | 偏估倍数 |
|------|----------------------|--------------------------|---------|
| 中文 | ~1 rune/token | 1.5 tokens/rune | ~1.5x 偏高 |
| 英文 | ~4 rune/token | 1.5 tokens/rune | **~6x 偏高** |
| 混合 | ~2-3 rune/token | 1.5 tokens/rune | ~3-4.5x 偏高 |

**影响链路**:

```
英文消息 "Explain quantum physics in detail" (35 runes)
  → estimateTokensFromRunes(35) = 52 tokens
  → 实际 token 数 ≈ 8-9 tokens
  → mid-stream 检查以为用户已用 52 tokens
  → 段记录 (segmentSize=200) 在 200 runes 时触发
  → 实际只消耗 ~50 tokens 但记录了 ~300 tokens (200 runes × 1.5)
  → 下次请求 GetDailyUsage 返回含水分的数值
  → 用户在消耗 ~17% 实际配额时即被截断
```

**影响范围**: 所有使用英文（及大部分非 CJK 语言）的用户。每日配额 100K tokens 实际只能使用约 16-17K tokens 的英文内容。

**修复方向**: (1) 使用 GPT tokenizer 的 cl100k_base 编码做精确计数；(2) 或按 Unicode 范围区分 CJK/非 CJK 字符使用不同系数（CJK: ×1.2, 非 CJK: ×0.3）。

---

### P1 — 重要问题

#### P1-1: 缓存命中路径和完成响应路径的发送错误被 `_` 静默丢弃 — 客户端可能收不到响应但系统认为已送达
**文件**: `chat_orchestrator_chatflow.go:342-365, 657-689`
**严重性**: P1 — 静默失败，无重试/重连

```go
// :342-365 — 缓存命中路径
case *wsSafeWriter:
    _ = writeLegacyJSON(r, convertResponseToJSON(resp))   // ← 错误丢弃
    _ = writeLegacyJSON(r, gin.H{...})                     // ← 错误丢弃
return false

// :657-689 — 完成响应路径
case *envelopeResponder:
    _ = r.SendMeta(meta)           // ← 错误丢弃
case *protobufResponder:
    _ = r.SendChatResponse(doneResp)  // ← 错误丢弃
```

主流式循环中（:567-588），发送错误**有检查**并触发重连（`return true`）。但缓存命中路径和完成元数据路径完全忽略发送错误。如果 WebSocket 已断开：
- 缓存命中路径：用户认为消息已发送但永远收不到回复
- 完成路径：用户收到流式内容但缺少 `done` 标记，UI 可能卡在"加载中"

**修复方向**: 缓存命中路径检查发送错误，失败时 `return true` 触发重连。

---

#### P1-2: `input.FileIds` 客户端数组未经任何验证直接传入 gRPC 请求
**文件**: `chat_orchestrator_chatflow.go:414`
**严重性**: P1 — 防御纵深缺失

```go
// :414 — 直接赋值，无格式/长度/内容验证
req.FileIds = input.FileIds
```

`chatInput.FileIds` 来自客户端 WebSocket JSON 消息的 `file_ids` 字段。Go Gateway 作为安全边界应在此层验证：
1. 数组长度限制（防止 DDoS — 可发送 10 万个 file ID）
2. 每个元素格式（应为 UUID 格式）
3. 每个元素长度限制

与 Round #128 P0-1 (SSRF via recordID) 同构 — 客户端输入未消毒即传入后端。

**修复方向**: `for _, fid := range input.FileIds { if _, err := uuid.Parse(fid); err != nil { return } }; if len(input.FileIds) > 10 { return }`。

---

#### P1-3: 语义缓存 scope 包含完整 userContextJSON 散列 — 活跃用户几乎无缓存命中
**文件**: `chat_orchestrator_chatflow.go:49-69, 307-315`
**严重性**: P1 — 缓存命中率趋近于零

```go
// :58 — contextHash 包含完整用户上下文 JSON
contextHash := shortHash(userContextJSON)

// :309-315 — 缓存 scope 组装
cacheScope := semanticCacheScope(
    userID,
    normalizedChatMode,
    userContextJSON,   // ← 包含 pending_tasks, active_plans, focus_stats, recent_progress
    input.FileIds,
    input.IncludeReferences,
)
```

`userContextJSON` 包含 `pending_tasks`、`active_plans`、`focus_stats`、`recent_progress` 等频繁变化的字段。用户完成一个任务、开始一次专注、更新进度记录都会改变 contextHash，导致缓存 key 变化。

**影响**: 对于活跃用户（Sparkle 的核心目标用户），语义缓存命中率趋近于零。缓存检查（Redis 查询）和异步缓存写入（goroutine）都是无用功。

**修复方向**: 从缓存 scope 中排除 volatile 字段（仅保留 user_id + chat_mode + file_ids），或使用 user context 的稳定子集（如 long-term preferences）。

---

#### P1-4: `buildAgentUserProfile` 硬编码 timezone 和 language — i18n 盲区十连
**文件**: `chat_orchestrator_chatflow.go:153-154`
**严重性**: P1 — 与 Round #48→#128 同一反模式

```go
// :153-154 — 硬编码中国时区和中文
Timezone:     "Asia/Shanghai",
Language:     "zh-CN",
```

虽然有 snapshot 覆盖逻辑（:162-167），但默认值硬编码为中国/中文。新用户或 snapshot 为空时，Python 后端收到固定的中国时区。非中国用户的所有时间计算将基于错误时区。

此为跨轮次 i18n 盲区反模式的第十次确认（Rounds #48→#128）。

---

#### P1-5: `input.Message` 无长度限制 — 超大消息直接传入 gRPC 流式调用
**文件**: `chat_orchestrator_chatflow.go:219, 432`
**严重性**: P1 — 资源滥用

```go
// :219 — 仅 HTML 消毒，无长度限制
input.Message = sanitizer.Sanitize(input.Message)

// :432 — 直接传入 gRPC
req.Input = &agentv1.ChatRequest_Message{
    Message: input.Message,  // ← 可为任意长度
}
```

客户端可发送兆字节级的消息文本。经过 HTML 消毒后仍然可能是巨大的纯文本。这将：
1. 导致 gRPC 消息超过默认 4MB 限制 → 连接断开
2. Python 后端 LLM 调用消耗大量 tokens
3. 配额系统按偏高的估算扣减

**修复方向**: 添加 `if len(input.Message) > 10000 { return }` 截断（10K 字符 ≈ 5K-10K tokens）。

---

### P2 — 改进建议

#### P2-1: `getEnvInt64("DAILY_QUOTA", 100000)` 每次请求读取环境变量 — 应缓存

```go
// :372 — 每次聊天请求都调用
dailyLimit = getEnvInt64("DAILY_QUOTA", 100000)
```

`getEnvInt64` 每次调用 `os.Getenv` + `strconv.ParseInt`。虽然 Go 的 `os.Getenv` 很快（访问进程环境块），但每天可能有数十万次调用。应在初始化时读取并缓存。

---

#### P2-2: `shortHash` 使用 SHA-1 — 非安全用途但使用已破解算法

```go
// :37-46 — SHA-1 用于缓存 key 散列
func shortHash(parts ...string) string {
    h := sha1.New()
    ...
    return hex.EncodeToString(h.Sum(nil))[:12]
}
```

虽然仅用于缓存 scope 去重（非安全上下文），但 SHA-1 已被 NIST 弃用。`sha256.New` 性能差异可忽略。取前 12 字符（48 位）用于缓存 key 碰撞风险可接受。

---

#### P2-3: `isDevelopmentEnv()` 每次请求调用 — 应缓存

```go
// :373 — 每次聊天请求调用
if dailyLimit <= 0 || isDevelopmentEnv() {
```

`isDevelopmentEnv()` 调用 `os.Getenv("ENVIRONMENT")` 并做字符串比较。环境在运行时不变，应在初始化时读取一次。

---

## 合规项

| 检查项 | 状态 |
|--------|------|
| 输入 HTML 消毒 | ✅ bluemonday.UGCPolicy 消毒用户消息 (:219) |
| Context 超时设置 | ✅ context.WithTimeout 300s 下限 (:208-216) |
| 认证 Token 传递 | ✅ userID 从已认证上下文传入 |
| OpenTelemetry 追踪 | ✅ 完整覆盖：user_context.fetch, semantic_cache.search, quota.reserve, grpc.agent_call, stream.receive, stream.process_response |
| Prometheus 指标 | ✅ AIChatTotalDuration/FirstEventDuration/FirstTokenDuration/StreamDuration 四维度 (:629-638) |
| 结构化日志 | ✅ 关键节点日志带 user_id, request_id, trace_id, session_id |
| 字符串构建池 | ✅ sync.Pool 复用 strings.Builder 减少 GC (:474-479) |
| WebSocket 写入安全 | ✅ wsSafeWriter channel mutex 防并发写 |
| 配额预留幂等 | ✅ reqID 用于幂等检查 (reserve_quota.lua) |

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

1. **P0-1** (配额不退还) — 添加 RefundReserve 方法，失败/中断时调用 — ~15 行
2. **P0-2** (token 估算偏估) — CJK/非 CJK 分别使用不同系数 — ~10 行
3. **P1-2** (FileIds 未验证) — UUID 格式检查 + 数组长度限制 — ~5 行
4. **P1-5** (Message 无长度限制) — 添加截断或拒绝 — ~1 行
5. **P1-1** (发送错误丢弃) — 缓存命中路径检查错误 — ~5 行
6. **P1-3** (缓存 scope) — 排除 volatile 字段 — ~5 行
7. P1-4/P2-1/P2-2/P2-3 — 随后续迭代修复

---

## 跨轮次因果链

| 本轮发现 | 关联轮次 | 关联模式 |
|----------|---------|---------|
| P0-1 (配额不退还) | Round #83 P0-1 (双轨计数器不同步) | 配额预留/记录使用独立 key 空间，预留失败无退还机制 |
| P0-2 (token 偏估) | Round #83 P1-2 (三套计数器混乱) | 配额系统的 token 计量准确性问题 |
| P1-2 (FileIds 未验证) | Round #128 P0-1 (SSRF via recordID) | Go Gateway 对客户端输入信任过度 — 防御纵深缺失 |
| P1-4 (i18n 十连) | Rounds #48→#128 (九连) | 硬编码中文 — 系统性反模式 |
| P1-1 (发送错误丢弃) | Round #2 (WebSocket 消息流) | WebSocket 写入错误处理不一致 |

---

## 复核笔记

> **复核日期**: 2026-04-22 (Session continuation)
> **复核方式**: 逐项代码验证
> **复核人**: GLM-5.1 executor

### 行号偏移对照

| 原始行号 | 当前行号 | 位置描述 |
|----------|---------|---------|
| 198 | 162 | Sanitize input.Message |
| 219 | 162 | Message sanitization |
| 384-407 | 310-341 | 配额预留 ReserveRequest |
| 414 | 351 | FileIds 直接赋值 |
| 432 | 349 | Message 传入 gRPC |
| 456-471 | 382-394 | gRPC StreamChatWithFallback 调用 |
| 491-589 | 398-638 | 流式转发主循环 |
| 592-612 | 505-530 | 最终使用量记录 |
| 614-689 | 548-600 | 元数据+完成响应 |
| 715-724 | 640-647 | estimateTokensFromRunes |
| 153-154 | 356-357 | UserProfile timezone/language |

### 复核结果: 0/10 已修 (全部未变)

| 原始编号 | 描述 | 状态 | 验证证据 |
|----------|------|------|---------|
| P0-1 | 配额预留永不退还 | **未修** | ReserveRequest(:320) 后三条失败路径(gRPC fail :385-394, stream interrupt :426-436, mid-stream quota :466)均无 RefundReserve 调用。全文件 grep `Refund|refund|Release` 零结果 |
| P0-2 | estimateTokensFromRunes 英文偏估6x | **未修** | :640-647 `float64(runes) * 1.5` 不变，无 CJK/非CJK 区分 |
| P1-1 | 缓存命中+完成路径发送错误被 `_` 丢弃 | **未修** | 缓存命中路径 :274-298 全部 `_ = r.SendChatResponse/SendMeta/writeLegacyJSON`，完成路径同理 |
| P1-2 | input.FileIds 未验证 | **未修** | :351 `FileIds: input.FileIds` 直接赋值，无 UUID 格式校验或长度限制 |
| P1-3 | 语义缓存 scope 含 volatile 字段 | **未修** | 缓存 scope 仍包含完整 userContextJSON（含 pending_tasks, active_plans 等频繁变化字段） |
| P1-4 | 硬编码 timezone/language | **未修** | :356-357 `"Asia/Shanghai"` 和 `"zh-CN"` 不变 |
| P1-5 | input.Message 无长度限制 | **未修** | :162 仅 `Sanitize`，无 `len(input.Message) > N` 截断 |
| P2-1 | getEnvInt64 每次请求调用 | **未修** | 未缓存 |
| P2-2 | SHA-1 用于缓存 key | **未修** | shortHash 仍用 sha1.New() |
| P2-3 | isDevelopmentEnv() 每次请求调用 | **未修** | 未缓存 |

### 判定

审计报告全部 10 项发现经代码验证**完全准确**。行号有系统性偏移（整体前移约 40-70 行），但问题位置和描述完全吻合。配额不退还(P0-1)是最高优先级修复项——后端不稳定时用户配额会被永久泄漏。

**状态更新**: ✅ 完成 → ⚠️ 已复核-无变化
