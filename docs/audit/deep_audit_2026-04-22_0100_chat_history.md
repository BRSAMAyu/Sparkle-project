# 深度审计：Chat History 持久化与检索链路

> 日期：2026-04-22 01:00
> 范围：Go `chat_history.go` 服务 → `chat_history_persister.go` 后台写入 → `chat_history.go` handler → PostgreSQL `chat_messages`/`chat_sessions` → Redis 缓存 → Flutter `chat_repository.dart` → `chat_message_model.dart`

## 审计发现

### P0 — 阻断性问题（2 项）

#### P0-1: Go API 仅返回 6 个字段，Flutter 模型期望 20+ 字段，历史消息丢失关键数据
- **位置**: `backend/gateway/internal/handler/chat_history.go:59-78` (Go 响应) vs `mobile/lib/features/chat/data/models/chat_message_model.dart:8-204` (Flutter 模型)
- **问题**: Go 历史消息 API 仅返回 `id`, `conversation_id`, `role`, `content`, `created_at`, `user_id`，但 DB `chat_messages` 表存储了 `actions` (JSON), `task_id`, `tokens_used`, `model_name` 等字段，Flutter 模型定义了 `widgets`, `toolResults`, `reasoningSteps`, `meta` 等 20+ 字段
  ```go
  // chat_history.go:59-78 — 仅 6 个字段
  result = append(result, gin.H{
      "id": msgID,
      "conversation_id": msg.SessionID,
      "role": msg.Role,
      "content": msg.Content,
      "created_at": createdAt,
      "user_id": msg.UserID,
      // 缺失: actions, task_id, model_name, tokens_used
  })
  ```
  ```dart
  // chat_message_model.dart — Flutter 期望这些字段
  final List<WidgetPayload>? widgets;        // 由 actions 转换
  final List<ToolResultModel>? toolResults;  // 缺失
  final List<ReasoningStep>? reasoningSteps; // 缺失
  final MessageMeta? meta;                   // 缺失
  ```
- **影响**: 历史消息在 UI 中显示为纯文本，丢失计划评审卡片、工具调用结果、推理步骤等富内容；用户回看对话时看到的是"降级版"
- **修复**: (1) Go handler 从 DB 查询完整字段（actions, task_id, model_name）(2) 或在 persister 写入 Redis 时保存完整字段

#### P0-2: 消息持久化重试缓冲溢出静默丢弃消息，用户无感知
- **位置**: `backend/gateway/internal/service/chat_history.go:230-240`
- **问题**: 熔断器开启 + 重试缓冲满时，消息被静默丢弃
  ```go
  if len(s.retryBuf) < breakerRetryBufMax {
      s.retryBuf = append(s.retryBuf, retryEntry{msg: msg, enqueuedAt: time.Now()})
  } else {
      bufferOverflow = true
      log.Printf("[ChatHistoryService] Retry buffer full, dropping message")
      // 消息永久丢失，无用户通知，无监控指标
  }
  ```
- **影响**: 用户以为消息已发送（WebSocket 已确认），但历史记录中不存在；最长对话丢失最多消息
- **修复**: (1) 添加 `sparkle_chat_history_dropped_total` Prometheus 指标 (2) 缓冲溢出时通知客户端 (3) 考虑本地磁盘 fallback

---

### P1 — 重要问题（5 项）

#### P1-1: 缓存未命中无 thundering herd 保护，可引发 DB 风暴
- **位置**: `chat_history.go:289-319`
- **问题**: Redis miss 后直接查 DB，无 singleflight/request coalescing
  ```go
  // 多个并发请求同时 miss → 全部打到 DB
  messages, err := s.getMessagesFromRedis(ctx, userID, sessionID, limit, offset)
  if len(messages) == 0 {
      messages, err = s.getMessagesFromDB(ctx, ...)  // 无锁，无去重
      go s.backfillRedisMessages(sessionID, messages)  // 多个 goroutine 同时 backfill
  }
  ```
- **影响**: 热门会话缓存过期瞬间，N 个并发请求同时击穿到 DB
- **修复**: 使用 `golang.org/x/sync/singleflight` 对同 sessionID 的请求合并

#### P1-2: N+1 Redis 调用在 session 元数据获取中
- **位置**: `chat_history.go:554-573`
- **问题**: 获取最近会话列表时，对每个 session ID 单独调用 `HGetAll`
  ```go
  for _, sid := range ids {
      metaKey := fmt.Sprintf("chat:session_meta:%s", sid)
      meta, err := s.rdb.HGetAll(ctx, metaKey).Result()  // N+1!
  }
  ```
- **影响**: 20 个会话 = 20 次 Redis 往返，延迟累加
- **修复**: 使用 Redis Pipeline 批量获取

#### P1-3: 无数据清理机制，chat_messages 表无限增长
- **位置**: `schema.sql:1117-1132` (表定义) + 无清理任务
- **问题**: `deleted_at` 列存在但无代码使用；无定时清理；无分区策略
- **影响**: 生产环境运行数月后 chat_messages 可达数百万行，查询性能退化
- **修复**: (1) 添加 Celery 定时任务清理 >90 天的软删除数据 (2) 考虑按 `created_at` 月分区

#### P1-4: Flutter 无持久化缓存，离线无法查看历史消息
- **位置**: `mobile/lib/features/chat/presentation/providers/chat_state.dart:99`
- **问题**: 仅内存存储（max 500 messages），无 SQLite/Hive 缓存；Hive 缓存仅用于社群聊天
- **影响**: 网络断开时用户无法查看任何历史消息；每次重启 app 需重新拉取
- **修复**: 使用 Hive/Isar 缓存最近 100 条消息到本地

#### P1-5: API 响应无分页元数据（total, has_more）
- **位置**: `chat_history.go:38-80`
- **问题**: 返回消息数组但无 `total_count`, `has_more` 等元数据
  ```go
  c.JSON(http.StatusOK, result)  // 仅 []messages，无分页信息
  ```
- **影响**: Flutter 无法精确判断是否还有更多历史消息（当前用 `len(result) >= pageSize` 启发式判断）
- **修复**: 响应改为 `{messages: [...], has_more: bool, total: int}`

---

### P2 — 改进建议（3 项）

#### P2-1: chat_messages 存在重复索引
- **位置**: `schema.sql:6917` + `:8464` (session_id), `:6938` + `:8471` (user_id)
- **问题**: `idx_chat_session_id` 与 `ix_chat_messages_session_id` 重复；user_id 同理
- **修复**: 移除重复索引

#### P2-2: 缺失复合索引优化 session 列表查询
- **位置**: `chat_sessions` 表
- **问题**: `GetRecentSessionsFromDB` 按 `(user_id, is_active, last_message_at DESC)` 查询，但无对应复合索引
- **修复**: 添加 `CREATE INDEX idx_chat_sessions_user_active_recent ON chat_sessions (user_id, is_active, last_message_at DESC)`

#### P2-3: chat_messages.session_id 无外键约束
- **位置**: `schema.sql:1122`
- **问题**: `session_id` 无 FK 到 `chat_sessions.id`，允许孤立消息
- **修复**: 评估是否需要添加（当前为有意的柔性设计，暂不强制）

---

### 合规项（4 项）

1. **消息去重** ✅ — persister 使用 `ON CONFLICT (id) DO NOTHING` 防止重复写入
2. **所有权校验** ✅ — `GetMessages` 验证 session 归属 user，越权返回 403
3. **双写策略** ✅ — 消息同时写 Redis 缓存（即时可读）和持久化队列（最终落 DB）
4. **熔断器保护** ✅ — persister 实现了熔断器 + 指数退避重试 + 批量写入

---

## 数据流图

```
Flutter (chat_repository.dart)
  │  GET /chat/history/{conversation_id}?limit=20&offset=0
  ↓
Go Handler (chat_history.go)
  │  提取 user_id (auth context), conversation_id (path), limit/offset (query)
  ↓
ChatHistoryService.GetMessages()
  │
  ├── [Redis] getMessagesFromRedis()
  │   ├── Hit → 返回 (仅缓存最近 20 条 ⚠️ LTrim)
  │   ├── Miss → 继续
  │   └── Error → 继续 (降级到 DB)
  │
  ├── [PostgreSQL] getMessagesFromDB()
  │   ├── SQL: SELECT id,session_id,user_id,role,content,created_at
  │   │        WHERE user_id=$1 AND session_id=$2 AND deleted_at IS NULL
  │   │        ORDER BY created_at DESC LIMIT $3 OFFSET $4
  │   ├── ⚠️ 不查询 actions, task_id, model_name 等字段 (P0-1)
  │   └── Async: go s.backfillRedisMessages() ⚠️ 无 singleflight (P1-1)
  │
  ├── Handler 响应构造 ⚠️ 仅 6 字段 (P0-1)
  │   └── c.JSON(200, [{id, conversation_id, role, content, created_at, user_id}])
  │
  ↓
Flutter 解析
  │  chat_repository.dart → ChatMessageModel.fromJson()
  │  ⚠️ actions 字段缺失 → widgets = null (P0-1)
  │  ⚠️ task_id, meta, reasoningSteps 全部 null
  │  → 历史消息显示为纯文本，无富内容

--- 写入路径 ---

WebSocket 接收消息
  │
  ├── 即时写 Redis (chat:history:{sessionID})
  │   └── LTrim -20 → 仅保留最近 20 条 ⚠️
  │
  ├── 入持久化队列 (queue:persist:history)
  │
  ↓
ChatHistoryPersister (后台 goroutine)
  │  LPop → 批量累积 (max 100) → INSERT INTO chat_messages
  │  ON CONFLICT (id) DO NOTHING ✅
  │  熔断器: 连续失败 → 开启 → 重试缓冲
  │  ⚠️ 缓冲满 → 静默丢弃 (P0-2)
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | Go 响应缺失字段 | 从 DB 查询 actions/task_id 并返回 | 中（~40 行 Go） |
| P0-2 | 重试缓冲溢出静默丢消息 | 添加 Prometheus 指标 + 客户端通知 | 低（~20 行 Go） |
| P1-1 | 无 thundering herd 保护 | singleflight 包裹 DB 查询 | 低（~15 行 Go） |
| P1-2 | N+1 Redis session 元数据 | Pipeline 批量获取 | 低（~20 行 Go） |
| P1-3 | 无数据清理机制 | Celery 定时任务 + 软删除清理 | 中（~60 行 Python） |
| P1-4 | Flutter 无本地缓存 | Hive 缓存最近 100 条 | 中（~80 行 Dart） |
| P1-5 | 无分页元数据 | 响应添加 has_more/total | 低（~10 行 Go） |

---

## 复核笔记

> **复核日期**: 2026-04-25
> **复核员**: Claude Deep Auditor

### 复核方法

逐项验证原审计（Round #8）发现是否与当前代码一致。独立验证 agent 同步完成交叉确认。

### 逐项复核结果

| 编号 | 原发现 | 状态 | 备注 |
|------|--------|------|------|
| P0-1 | Go API 仅返回 6 个字段 | ✅ 已验证 | `chat_history.go:69-76` 仍为 6 字段：id, conversation_id, role, content, created_at, user_id。actions/task_id/model_name/tokens_used 仍未返回。ChatHistoryMessage struct (:61-68) 未变 |
| P0-2 | 重试缓冲溢出静默丢弃 | ⚠️ 部分改善 | 不再完全静默：`:223-227` 现在 log "dropping message" + 队列深度。但：(1) 无 Prometheus 指标 (2) 缓冲满时仍丢弃消息 (breakerRetryBufMax=500) (3) 无客户端通知 |
| P1-1 | 无 thundering herd 保护 | ✅ 已验证 | 无 singleflight。`:296` `go s.backfillRedisMessages(sessionID, messages)` 仍为无锁无去重的异步 backfill |
| P1-2 | N+1 Redis session 元数据 | ✅ 已验证 | `:537-543` 仍在循环中逐个调用 `s.rdb.HGetAll(ctx, metaKey)`。Pipeline 仅用于写操作 (:194)，读操作无批量化 |
| P1-3 | 无数据清理机制 | ✅ 已验证 | 无变化 |
| P1-4 | Flutter 无持久化缓存 | ✅ 已验证 | 无变化 |
| P1-5 | API 响应无分页元数据 | ✅ 已验证 | `:58-78` 仍为 `c.JSON(200, result)`，无 has_more/total_count |
| P2-1 | 重复索引 | ✅ 已验证 | 无变化 |
| P2-2 | 缺失复合索引 | ✅ 已验证 | 无变化 |
| P2-3 | 无外键约束 | ✅ 已验证 | 无变化 |

### 新发现

- 无新发现。代码变化极小，仅 P0-2 增加了日志记录。

### 总结

- **0/10 已完全修复**
- **1/10 部分改善** (P0-2: 增加丢弃日志，但无指标/通知)
- **9/10 未变化**
- P0-1（历史消息丢失富内容）是用户体验最严重的未修项——用户回看对话只能看到纯文本
