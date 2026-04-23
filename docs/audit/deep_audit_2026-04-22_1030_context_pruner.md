# 深度审计：Context Pruner 对话历史裁剪与摘要完整链路

> 日期：2026-04-22 10:30
> 范围：Python `context_pruner.py`（333 行，3 层裁剪策略）+ `summarization_worker.py`（401 行，后台摘要 Worker）+ Go `chat_history.go`（508 行，`SaveMessage`/`LTrim`/`getMessagesFromRedis`）→ `context_builder.py:834`（主调用点）→ `prompts.py:1535-1574`（摘要渲染到 prompt）→ `orchestrator.py:311-320` / `orchestrator_production.py:266-283`（初始化）→ `config_production.py:93-96`（配置定义）

## 审计发现

### P0 — 阻断性问题（2 项）

#### P0-1: Tier 3（LLM 摘要）永不可达 — Go Gateway 在写入时 `LTrim(-20, -1)` 限制为 20 条消息，但 Python `importance_threshold = max(summary_threshold, 30) = 30`，Tier 3 要求 >30 条消息才能触发
- **位置**: `backend/gateway/internal/service/chat_history.go:208` + `backend/app/orchestration/context_pruner.py:43,81`
- **问题**:

  ```go
  // chat_history.go:206-208: Go 写入时立即裁剪到 20 条
  cacheKey := "chat:history:" + sid
  pipe.RPush(ctx, cacheKey, msg)
  pipe.LTrim(ctx, cacheKey, -20, -1) // Keep last 20 messages
  ```

  ```python
  # context_pruner.py:43: Python 的 importance_threshold 计算
  self.importance_threshold = max(summary_threshold, 30)  # = max(20, 30) = 30

  # context_pruner.py:72-81: 三层策略
  if original_count <= self.max_history_messages:    # ≤ 10 → Tier 1: 全保留
      return {...}
  if not force_summary and original_count <= self.importance_threshold:  # ≤ 30 → Tier 2: 规则压缩
      messages = self._compress_with_importance(history)
  # 否则 → Tier 3: LLM 摘要（永远到不了！）
  ```

  **实际情况**:
  - Go 写入后立即 LTrim 到 20 条 → Redis 中最多 20 条消息
  - Python 读取 `lrange(0, -1)` → 最多 20 条消息
  - `importance_threshold = 30` → 20 ≤ 30 → 永远走 Tier 2（规则压缩）
  - Tier 3（`_summarize_sync`，`_get_summarized_history`）从未被触发

  **影响**: `_summarize_sync`（line 147-173）每次调用需要 LLM 请求（FAST tier），虽然不会执行，但代码维护负担和复杂度持续存在。`SummarizationWorker`（401 行）完全是僵尸代码

- **修复**: (1) 将 `importance_threshold` 降为 15-18（与 Go 的 20 条限制对齐） (2) 或增大 Go 的 LTrim 限制到 50+，让 Python 的 3 层策略真正生效

#### P0-2: `SummarizationWorker` 完全孤立 — 无任何生产者向 `queue:summarization` 入队，Worker 从未被 Docker/CI 启动
- **位置**: `backend/app/orchestration/summarization_worker.py:92` + 全项目 grep
- **问题**:

  ```python
  # summarization_worker.py:92: 仅消费端引用
  queue_key = "queue:summarization"

  # grep 结果: 全项目仅在 summarization_worker.py 中引用此 queue
  # 无任何代码执行 rpush/lpush 到 "queue:summarization"
  ```

  **Worker 启动方式**: 仅在 `__main__` 块中（line 398-400）通过 `asyncio.run(run_worker())` 启动，未集成到 Docker Compose 或任何进程管理器中

  **影响**: 401 行代码完全浪费 — 包含精心设计的重试逻辑（exponential backoff）、LLM 降级保护（`llm_fallback_utils`）、本地 fallback 摘要（line 276-306），但从未执行

- **修复**: (1) 如果不需要异步摘要，删除 SummarizationWorker (2) 如果需要，在 Tier 3 触发时入队到 `queue:summarization`，并将 Worker 集成到 Docker Compose

---

### P1 — 重要问题（5 项）

#### P1-1: Python `_load_chat_history` 不按 `user_id` 过滤 — Go `getMessagesFromRedis`（line 349）过滤 `user_id != userID`，但 Python 直接返回全部消息
- **位置**: `backend/app/orchestration/context_pruner.py:274-289` + `backend/gateway/internal/service/chat_history.go:349`
- **问题**:

  ```python
  # context_pruner.py:274-289: 不检查 user_id
  async def _load_chat_history(self, session_id: str) -> list[dict]:
      messages = await self.redis.lrange(cache_key, 0, -1)
      for msg in messages:
          parsed = json.loads(msg)
          if "role" in parsed and "content" in parsed:  # ← 只检查格式，不检查归属
              history.append(parsed)
  ```

  ```go
  // chat_history.go:349: Go 正确过滤
  if msg.UserID != "" && msg.UserID != userID {
      continue  // ← 跳过非当前用户的消息
  }
  ```

  Python `_get_summarized_history` 接收 `user_id` 参数但立即 `del user_id`（line 115）。Go 的 `ChatHistoryMessage` 包含 `user_id` 字段（line 72），Python 解析后也有此字段但从不使用

  **实际风险**: 低 — session ID 是 UUID，且 Go 在写入时已绑定 session → user。但如果出现 session ID 冲突或 Redis 数据污染，Python 会包含其他用户的消息

- **修复**: `_load_chat_history` 接收 `user_id` 参数，过滤 `msg.get("user_id") != user_id` 的消息

#### P1-2: `_summary_cache_key` 基于完整消息列表的 SHA1 — 每新增一条消息，整个消息列表变化导致缓存键变化，缓存永远不会命中
- **位置**: `backend/app/orchestration/context_pruner.py:243-247`
- **问题**:

  ```python
  def _summary_cache_key(self, session_id: str, messages: list[dict]) -> str:
      digest = hashlib.sha1(
          json.dumps(messages, ensure_ascii=False, sort_keys=True).encode("utf-8")
      ).hexdigest()[:16]
      return f"summary:{session_id}:{digest}"
  ```

  `messages` 是完整的待摘要消息列表（早期消息减去锚点消息）。每次新消息加入对话，消息列表尾部扩展，SHA1 完全变化。即使 Tier 3 可达，缓存也不会命中

  **正确做法**: 缓存键应基于消息列表的前 N-1 条（排除最新消息），或使用最后一条消息的 ID/timestamp 作为版本号

- **修复**: 使用 `f"summary:{session_id}:{messages[0].get('timestamp')}:{len(messages)}"` 作为缓存键

#### P1-3: `_summarize_sync` 和 `_build_summary_prompt` 硬编码中文 — LLM 总结提示和系统消息全部中文
- **位置**: `backend/app/orchestration/context_pruner.py:161-168` + `summarization_worker.py:211-272`
- **问题**:

  ```python
  # context_pruner.py:161-168
  prompt = (
      "用中文简洁总结以下对话的关键信息（100字以内）。\n"
      "要求：1. 用户核心目标 2. 已完成事项 3. 当前阶段 4. 关键决策。\n\n"
      f"{self._format_messages_for_summary(messages)}"
  )
  # line 168: system message
  "你是对话总结助手。只输出总结，不加前缀。"
  ```

  `summarization_worker.py:253-272` 同样全部中文。如果用户语言为英文，摘要仍会强制用中文生成

- **修复**: 从 `user_context.language` 获取语言偏好，或使用语言中性的提示

#### P1-4: 生产配置 `CONTEXT_PRUNER_*` 已定义但未接入 — 两个 Orchestrator 都硬编码 `max_history_messages=10, summary_threshold=20, cache_ttl=3600`
- **位置**: `backend/app/config_production.py:93-96` + `backend/app/orchestration/orchestrator.py:314-319` + `orchestrator_production.py:281-283`
- **问题**:

  ```python
  # config_production.py:93-96: 已定义但未被使用
  CONTEXT_PRUNER_MAX_HISTORY: int = Field(default=10, env="CONTEXT_PRUNER_MAX_HISTORY")
  CONTEXT_PRUNER_SUMMARY_THRESHOLD: int = Field(default=20, env="CONTEXT_PRUNER_SUMMARY_THRESHOLD")
  CONTEXT_PRUNER_CACHE_TTL: int = Field(default=3600, env="CONTEXT_PRUNER_CACHE_TTL")

  # orchestrator.py:314-319: 硬编码值
  self.context_pruner = ContextPruner(
      redis_client=redis_client,
      max_history_messages=10,     # ← 硬编码，不读 settings
      summary_threshold=20,        # ← 硬编码
      summary_cache_ttl=3600,      # ← 硬编码
  )
  ```

  `orchestrator_production.py:281-283` 完全相同。修改配置需要改代码而非环境变量

- **修复**: `ContextPruner(redis_client, max_history_messages=settings.CONTEXT_PRUNER_MAX_HISTORY, ...)`

#### P1-5: `_is_high_importance_message` 和 `_is_anchor_message` 基于中文关键词匹配 — 9 个高优先级关键词和 7 个锚点关键词全部中文，英文消息永远不会被标记为重要
- **位置**: `backend/app/orchestration/context_pruner.py:219-231`
- **问题**:

  ```python
  # line 223: 高优先级关键词全部中文
  high_priority_keywords = ["计划", "任务", "阶段", "里程碑", "目标", "记住", "注意", "修改", "变更"]

  # line 230: 锚点关键词全部中文
  anchor_keywords = ["计划已创建", "任务完成", "阶段", "里程碑", "目标确认", "关键决策", "修改计划"]
  ```

  **影响**: 英文对话中，Tier 2 压缩不会保留任何"重要"消息（因为关键词匹配永远失败），所有早期消息都会被压缩为 `[assistant简述] ...`。Tier 3 摘要不会保留任何锚点消息

- **修复**: 添加英文关键词映射：`["plan", "task", "milestone", "goal", "remember", "important", "change"]`

---

### P2 — 改进建议（3 项）

#### P2-1: `_dedupe_messages` 基于完整 JSON 去重 — 使用 `(role, content, timestamp)` 三元组作为去重键，如果两条消息恰好同时发送且角色+内容相同，后一条会被丢弃
- **位置**: `backend/app/orchestration/context_pruner.py:249-266`
- **问题**: 去重键 `json.dumps({"role": ..., "content": ..., "timestamp": ...})` 不包含消息 ID。Go 的 `ChatHistoryMessage` 有 `ID` 字段（line 70），应用作去重依据

- **修复**: 在去重键中加入 `message.get("id", "")`

#### P2-2: `clear_summary` 使用 `scan_iter` — 在大型 Redis 实例上可能阻塞，且无分页限制
- **位置**: `backend/app/orchestration/context_pruner.py:312`
- **问题**: `async for key in self.redis.scan_iter(match=f"summary:{session_id}:*")` — `scan_iter` 是 `SCAN` 的封装，虽然有 COUNT hint，但在大量 key 匹配时仍可能耗时

- **修复**: 可接受（每个 session 的 summary key 数量极少，通常 0-2 个）

#### P2-3: `_compress_message` 对长消息截断到 150 字符但 AI 回复通常 > 150 字 — Tier 2 压缩会截断大部分 AI 回复
- **位置**: `backend/app/orchestration/context_pruner.py:195-196`
- **问题**: `if len(content) > 150: compressed["content"] = content[:150].rstrip() + "..."` — 150 字符对中文约 75 个汉字，AI 回复通常 200-500 字。这意味着大部分 AI 回复在 Tier 2 压缩时被截断到 1/3

- **修复**: 区分 user/assistant 消息，assistant 消息截断阈值设为 300-500

---

### 合规项（5 项）

1. **Go-Redis-Python 数据流** ✅ — Go `SaveMessage` 写入 `chat:history:{sid}`（JSON），Python `_load_chat_history` 读取同一 key，格式兼容（Go `ChatHistoryMessage` 含 `role`+`content`，Python 检查 `"role" in parsed and "content" in parsed`）
2. **Tier 1/2 策略有效** ✅ — ≤10 条全保留，11-20 条进入重要性压缩（保留最近 6 条 + 高重要性早期消息），逻辑正确
3. **Redis 管道原子性** ✅ — Go `SaveMessage` 使用 `pipe.RPush + pipe.LTrim + pipe.Expire` 三操作原子执行，不会出现消息数 > 20 的中间状态
4. **Prompt 渲染** ✅ — `prompts.py:1535-1574` 正确渲染 `summary_used`、`summary`、`messages`，区分"前情提要"和"最近对话"两种展示模式
5. **降级容错** ✅ — `_get_summarized_history` 在 LLM 失败时回退到 `_compress_with_importance`（line 141），`_load_chat_history` 在 Redis 异常时返回空列表（line 288）

---

## 数据流图

```
Context Pruner 对话历史裁剪与摘要完整链路
  │
  ├── [写入] Go Gateway: ChatHistoryService.SaveMessage()
  │   ├── pipe.RPush("chat:history:{sid}", JSON) ✅
  │   ├── pipe.LTrim(-20, -1) ✅ ← 限制 20 条
  │   ├── pipe.Expire(30min TTL) ✅
  │   ├── pipe.RPush("queue:persist:history", msg) ✅
  │   │   └── Circuit Breaker: qLen < threshold 才入队 ✅
  │   ├── pipe.ZAdd("chat:sessions:user:{uid}", ...) ✅
  │   └── pipe.HSet("chat:session_meta:{sid}", ...) ✅
  │
  ├── [读取] Python: ContextPruner._load_chat_history()
  │   ├── redis.lrange("chat:history:{sid}", 0, -1) → 最多 20 条
  │   ├── 解析 JSON, 检查 role+content ✅
  │   └── ⚠️ 不过滤 user_id (P1-1)
  │
  ├── [Tier 1] ≤ 10 条消息
  │   └── 全部保留，直接返回 ✅
  │
  ├── [Tier 2] 11-20 条消息（实际可达范围）
  │   ├── 保留最近 6 条 ✅
  │   ├── 早期消息: 检查 _is_high_importance ⚠️ 仅中文关键词 (P1-5)
  │   │   ├── 高重要性 → 保留原文 ✅
  │   │   └── 低信号 → 压缩为 "[role简述] ..." ✅
  │   ├── 长消息截断到 150 字符 ⚠️ AI 回复过短 (P2-3)
  │   └── 返回: compressed + recent ✅
  │
  ├── [Tier 3] > 30 条消息 ❌ 永不可达 (P0-1)
  │   ├── _get_summarized_history()
  │   │   ├── 保留最近 4 条 ✅
  │   │   ├── 识别锚点消息 ⚠️ 仅中文关键词 (P1-5)
  │   │   ├── 剩余消息 → _summarize_sync()
  │   │   │   ├── 检查 SHA1 缓存 ⚠️ 永远 miss (P1-2)
  │   │   │   ├── LLM FAST tier 摘要 ⚠️ 中文 prompt (P1-3)
  │   │   │   └── 缓存写入 Redis (TTL 1h) ✅
  │   │   ├── 失败 → 回退到 Tier 2 压缩 ✅
  │   │   └── 去重锚点+最近消息 ✅
  │   └── 返回: anchors + recent + summary
  │
  ├── [消费] prompts.py:1535-1574
  │   ├── summary_used=True → "前情提要" + "最近对话" ✅
  │   ├── summary_used=False, summary exists → "历史摘要" ✅
  │   └── 消息截断: anchor 500字, 其他 100字 ✅
  │
  ├── [Worker] SummarizationWorker ❌ 完全孤立 (P0-2)
  │   ├── 消费 "queue:summarization" ← 无生产者！
  │   ├── 重试逻辑 (exponential backoff) ← 从未执行
  │   ├── LLM 降级保护 ← 从未执行
  │   ├── 本地 fallback 摘要 ← 从未执行
  │   └── __main__ 入口 ← 未集成 Docker
  │
  ├── [配置] config_production.py:93-96
  │   ├── CONTEXT_PRUNER_MAX_HISTORY = 10
  │   ├── CONTEXT_PRUNER_SUMMARY_THRESHOLD = 20
  │   ├── CONTEXT_PRUNER_CACHE_TTL = 3600
  │   └── ⚠️ 已定义但未接入 (P1-4)
  │
  ├── [初始化] orchestrator.py:314-319
  │   └── ContextPruner(redis, 10, 20, 3600) ← 硬编码值
  │
  ↓ 跨系统不一致

  Go Gateway LTrim:     保留 20 条消息
  Python max_history:   ≤ 10 条全保留
  Python importance:    ≤ 30 条规则压缩  ← 30 > 20, Tier 2 范围 = 11-20
  Python summarization: > 30 条 LLM 摘要 ← 永远到不了
  Redis TTL:            30 分钟 (Go) vs 1 小时 (Python summary cache)
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | Tier 3 不可达（Go LTrim 20 vs Python threshold 30） | 降低 `importance_threshold` 到 15 或增大 Go LTrim 到 50 | 低（1 行 Go 或 1 行 Python） |
| P0-2 | SummarizationWorker 无生产者且未启动 | 删除或集成：在 Tier 3 触发时入队 + Docker Compose 启动 | 中（~30 行 + Docker 配置） |
| P1-1 | Python 不过滤 user_id | `_load_chat_history` 添加 user_id 过滤 | 低（~5 行 Python） |
| P1-2 | SHA1 缓存键每条消息变化 | 使用首条消息 ID + 消息数作为缓存键 | 低（~3 行 Python） |
| P1-3 | 硬编码中文 LLM 提示 | 根据用户语言动态选择提示语言 | 中（~20 行 Python） |
| P1-4 | 配置已定义但未接入 | Orchestrator 读取 settings.* 替代硬编码 | 低（~6 行 Python） |
| P1-5 | 关键词匹配仅中文 | 添加英文关键词映射 | 低（~5 行 Python） |

---

## 复核笔记

> 复核日期: 2026-04-25
> 复核轮次: 第十三次唤醒 (Round #57 并行复核)
> 复核方式: 代码验证
> 复核人: Claude Opus 4.5 (GLM-5.1 executor)

### 文件版本快照

| 文件 | 审计时行数 | 当前行数 | 偏移 |
|------|-----------|---------|------|
| `context_pruner.py` | 333 | 332 | -1（末尾空行差异，无实质变化） |
| `summarization_worker.py` | 401 | 355 | -46（重构：删除了 `__main__` 入口和冗余代码） |
| `chat_history.go` | 508 | 692 | +184（新增断路器重试机制、DB fallback、session 元数据管理） |

---

### P0-1: Tier 3（LLM 摘要）永不可达 — **未修复，确认仍然存在**

**验证结果**:

- `chat_history.go:199`: `pipe.LTrim(ctx, cacheKey, -20, -1)` — 仍然限制 20 条
- `context_pruner.py:43`: `self.importance_threshold = max(summary_threshold, 30)` — 仍然是 30
- `context_pruner.py:81`: `if not force_summary and original_count <= self.importance_threshold:` — 逻辑不变

**行号漂移**: 原报告引用 `chat_history.go:206-208`，现在位于 `199`（因文件头部新增常量定义和 retryEntry 结构体导致偏移）。原报告引用 `context_pruner.py:43,81`，行号未变。

**结论**: Go LTrim 20 条 vs Python importance_threshold 30 的矛盾完全未修复。Tier 3 仍然不可达。`_summarize_sync`（L147-173）和 `_get_summarized_history`（L109-145）中的 LLM 调用路径仍然是死代码。

---

### P0-2: SummarizationWorker 完全孤立 — **未修复，确认仍然存在**

**验证结果**:

- `summarization_worker.py:92`: `queue_key = "queue:summarization"` — 仍然消费此队列
- 全项目 grep `rpush.*summarization\|lpush.*summarization`（排除测试和 `__pycache__`）: **零结果** — 无任何生产者入队
- `docker-compose.yml`: grep "summarization" **零匹配** — Worker 未集成到 Docker Compose
- 两个 Orchestrator 均不 import 或引用 `SummarizationWorker`

**变化**: Worker 文件从 401 行减少到 355 行（删除了 `__main__` 块中的 `asyncio.run(run_worker())` 入口和一些冗余），但核心问题不变。

**结论**: Worker 仍然是完全孤立的僵尸代码。`health_production.py` 中甚至有 `queue:summarization` 的监控代码（L150, L239, L304, L362），但这些代码监控的是一个永远不会增长的队列。

---

### P1-1: Python `_load_chat_history` 不按 `user_id` 过滤 — **未修复，确认仍然存在**

**验证结果**:

- `context_pruner.py:274-289`: `_load_chat_history(self, session_id: str)` — 签名不变，仍不接收 `user_id`
- `context_pruner.py:282`: 只检查 `"role" in parsed and "content" in parsed` — 不检查 `user_id`
- `context_pruner.py:115`: `_get_summarized_history` 仍然 `del user_id` — 删除了传入的 user_id

**对比 Go**: `chat_history.go:333-334` (`getMessagesFromRedis`): `if msg.UserID != "" && msg.UserID != userID { continue }` — Go 正确过滤

**结论**: 安全风险虽低（session UUID 隔离），但 Python 侧确实不验证消息归属，与 Go 行为不一致。

---

### P1-2: SHA1 缓存键每次消息变化 — **未修复，确认仍然存在**

**验证结果**:

- `context_pruner.py:243-247`: `_summary_cache_key` 仍然基于完整消息列表的 SHA1
- 逻辑不变：每新增一条消息，整个消息列表的 SHA1 变化，缓存永远 miss

**结论**: 缓存设计缺陷仍然存在。但由于 Tier 3 本身不可达（P0-1），此缓存逻辑从不执行，影响为零。

---

### P1-3: 硬编码中文 LLM 提示 — **未修复，确认仍然存在**

**验证结果**:

- `context_pruner.py:161-168`: 提示仍然是 `"用中文简洁总结以下对话的关键信息（100字以内）"` + `"你是对话总结助手。只输出总结，不加前缀。"`
- `summarization_worker.py:211,253-258`: `"你是一个专业的对话总结助手。请用简洁的语言总结对话核心内容。"` + `"总结（用中文，不超过200字）"` — 同样全中文

**结论**: 由于 Tier 3 不可达，`context_pruner.py` 中的中文提示从不执行。但 `summarization_worker.py` 的中文提示作为独立模块的代码债务仍然存在。

---

### P1-4: 生产配置 `CONTEXT_PRUNER_*` 未接入 — **未修复，确认仍然存在**

**验证结果**:

- `config_production.py:94-96`: 三个配置字段仍然定义但未被使用
- `orchestrator.py:306-310`: 仍然硬编码 `max_history_messages=10, summary_threshold=20, summary_cache_ttl=3600`
- `orchestrator_production.py:265-270`: 同样硬编码相同值

**行号漂移**: 原报告引用 `orchestrator.py:314-319`，现在位于 `306-310`（前面代码删减导致偏移）。原报告引用 `orchestrator_production.py:281-283`，现在位于 `265-270`。

**结论**: 环境变量配置路径仍然断开，修改配置仍需改代码。

---

### P1-5: 关键词匹配仅中文 — **未修复，确认仍然存在**

**验证结果**:

- `context_pruner.py:223`: `high_priority_keywords = ["计划", "任务", "阶段", "里程碑", "目标", "记住", "注意", "修改", "变更"]` — 9 个中文关键词
- `context_pruner.py:230`: `anchor_keywords = ["计划已创建", "任务完成", "阶段", "里程碑", "目标确认", "关键决策", "修改计划"]` — 7 个中文关键词
- `context_pruner.py:214`: `_is_low_signal_message` 的 `low_signal_values` 已包含 `"ok"`, `"okay"` — **部分英文覆盖**

**结论**: 高重要性和锚点关键词仍然是纯中文。低信号检测已包含少量英文词（ok/okay），但核心的关键词匹配对英文对话完全无效。由于 Tier 2（11-20 条消息）是实际执行的路径，此问题对英文用户有实际影响。

---

### P2-1: 去重键不含消息 ID — **未修复，确认仍然存在**

**验证结果**:

- `context_pruner.py:249-266`: `_dedupe_messages` 仍然使用 `(role, content, timestamp)` 三元组
- `chat_history.go:62`: `ChatHistoryMessage` 仍然包含 `ID string` 字段
- Python 解析后 `parsed` 中应有 `id` 字段但未被使用

**结论**: 去重逻辑不变。实际影响低（timestamp 相同的重复消息罕见）。

---

### P2-2: `clear_summary` 使用 `scan_iter` — **未修复，风险可接受**

**验证结果**:

- `context_pruner.py:312`: `async for key in self.redis.scan_iter(match=f"summary:{session_id}:*")` — 逻辑不变

**结论**: 原报告已标注"可接受"。每个 session 的 summary key 通常 0-2 个，无性能问题。

---

### P2-3: 消息截断阈值 150 字符 — **未修复，确认仍然存在**

**验证结果**:

- `context_pruner.py:195-196`: `if len(content) > 150: compressed["content"] = content[:150].rstrip() + "..."` — 阈值不变
- 无 user/assistant 区分逻辑

**结论**: AI 回复仍会被截断到 ~150 字符。由于 Tier 2 是实际执行路径（11-20 条消息），此问题有实际影响。

---

### 合规项复核

| # | 合规项 | 审计结论 | 复核结论 |
|---|--------|---------|---------|
| 1 | Go-Redis-Python 数据流 | ✅ | ✅ 仍然正确。Go 写 JSON 到 `chat:history:{sid}`，Python 读同一 key，格式兼容 |
| 2 | Tier 1/2 策略有效 | ✅ | ✅ 仍然正确。Tier 1 (<=10) 全保留，Tier 2 (11-20) 重要性压缩 |
| 3 | Redis 管道原子性 | ✅ | ✅ 仍然正确。`pipe.RPush + pipe.LTrim + pipe.Expire` 不变 |
| 4 | Prompt 渲染 | ✅ | ✅ 仍然正确。`prompts.py:1241+` 正确渲染 summary_used/summary/messages |
| 5 | 降级容错 | ✅ | ✅ 仍然正确。LLM 失败回退到 `_compress_with_importance`（L141），Redis 异常返回空列表（L288） |

---

### 总结

**10 项发现中 0 项已修复，全部确认仍然存在。**

| 优先级 | 总数 | 已修复 | 仍然存在 | 备注 |
|--------|------|--------|---------|------|
| P0 | 2 | 0 | 2 | Tier 3 不可达 + Worker 孤立 |
| P1 | 5 | 0 | 5 | user_id 过滤、缓存键、中文提示、配置未接入、中文关键词 |
| P2 | 3 | 0 | 3 | 去重键、scan_iter、截断阈值 |

**核心问题未变**: Go LTrim 限制 20 条 → Python importance_threshold 30 → Tier 3 永不可达 → 依赖于 Tier 3 的 SummarizationWorker、SHA1 缓存、LLM 中文摘要提示全部成为死代码。实际运行路径仅为 Tier 1 (<=10) 和 Tier 2 (11-20)。

**新增观察**: `chat_history.go` 新增了断路器重试机制（retryWorker + retryBuf）和 DB fallback（getMessagesFromDB），但这些改进不涉及 Python 侧的裁剪逻辑，因此不影响本审计的任何发现。
