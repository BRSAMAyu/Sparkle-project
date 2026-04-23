# 深度审计：Cognitive Prism（认知棱镜）完整链路

> 日期：2026-04-22 04:00
> 范围：Flutter 认知碎片/行为模式 UI + 胶囊系统 → Go Gateway proxy 路由 → Python cognitive_service 碎片创建 + RAG 分析 + 模式提取 → 事件消费链（CognitiveEventConsumer + CapsuleEventConsumer + ProfileEventConsumer + TaskEventConsumer）→ prompt 渲染 → DB schema（cognitive_fragments + behavior_patterns 表）

## 审计发现

### P0 — 阻断性问题（2 项）

#### P0-1: 分析双路径调度 — BackgroundTask + EventBus 消费者同时触发 analyze_behavior，导致重复分析
- **位置**: `backend/app/api/v1/cognitive.py:82-87` (BackgroundTask) + `backend/app/services/cognitive_event_consumer.py:74-84` (EventBus 消费者)
- **问题**: 创建碎片后，存在**两条独立的分析触发路径**：
  ```python
  # cognitive.py:82-87 — 第一条：API 层 BackgroundTask
  background_tasks.add_task(
      _analyze_fragment_task,
      user_id,
      fragment.id,
      AsyncSessionLocal
  )
  
  # cognitive_service.py:208-216 — 第二条：create_fragment 内发布事件
  await event_bus.publish("cognitive.fragment.created", {
      "event_type": "cognitive.fragment.created",
      "user_id": str(user_id),
      "fragment_id": str(fragment.id),
      ...
  })
  
  # cognitive_event_consumer.py:74-78 — EventBus 消费者触发分析
  cognitive_service = CognitiveService(db)
  result = await cognitive_service.analyze_behavior(user_id, fragment_id)
  ```
- **条件分析**: 两条路径**同时生效**当：
  - GLM batch 未启用 (`should_enqueue_glm_batch = False`) → BackgroundTask 触发
  - EventBus 消费者始终监听 `cognitive.fragment.created` → 也触发
  - 即：当 `GLM_BATCH_ENABLED=False` 时，每次碎片创建触发**两次** `analyze_behavior()`
  - 当 `GLM_BATCH_ENABLED=True` 时，GLM batch 路径 + EventBus 消费者触发**两次**
- **影响**: 重复分析导致 (1) LLM 调用翻倍，成本浪费 (2) `_upsert_pattern` 的 EMA confidence 计算被调用两次，影响模式准确度 (3) 事件发布重复（`PROFILE_COGNITIVE_UPDATED` 和 `behavior.pattern.updated` 可能被触发两次）
- **修复**: 移除 `cognitive.py` 中的 `background_tasks.add_task`（保留 EventBus 驱动路径），或将 API 层改为仅当 EventBus 不可用时才走 BackgroundTask

#### P0-2: evidence_ids 存储为 `list[str]` 但 schema 声明为 `list[UUID]`，GET /patterns 返回 422
- **位置**: `backend/app/services/cognitive_service.py:582-591` (存储 str) + `backend/app/schemas/cognitive.py:65` (声明 UUID)
- **问题**: `_upsert_pattern()` 将 evidence_ids 存储为**字符串数组**：
  ```python
  # cognitive_service.py:584 — 存储为 str
  ev_list.append(str(fragment_id))  # "abc-123-..."
  pattern.evidence_ids = ev_list    # ["abc-123-...", "def-456-..."]
  
  # cognitive_service.py:602 — 创建时也用 str
  evidence_ids=[str(fragment_id)]
  ```
  但响应 schema 声明为 UUID 类型：
  ```python
  # schemas/cognitive.py:65
  evidence_ids: list[UUID] | None  # ← 期望 UUID 对象
  ```
- **影响**: `GET /cognitive/patterns` 返回的 `evidence_ids` 字段包含字符串（如 `"550e8400-e29b-41d4-a716-446655440000"`）。Pydantic v2 的 `from_attributes=True` 会尝试将 `str` 转换为 `UUID` — 对于 JSON 列中的数据，这取决于 SQLAlchemy 返回的是 `str` 还是原始 `UUID`。如果 DB 返回 `str`（JSON 列的默认行为），Pydantic 的严格模式可能拒绝
- **修复**: 将 schema 中 `evidence_ids: list[UUID] | None` 改为 `evidence_ids: list[str] | None`，或在模型层添加 property 做类型转换

---

### P1 — 重要问题（5 项）

#### P1-1: get_user_patterns 不过滤 is_archived，已克服模式仍返回给前端和 AI
- **位置**: `backend/app/services/cognitive_service.py:662-674` (get_user_patterns) + `backend/app/api/v1/cognitive.py:119-124` (GET /patterns)
- **问题**: `get_user_patterns()` 仅过滤 `confidence_score >= min_confidence`，不检查 `is_archived`：
  ```python
  # cognitive_service.py:667-672 — 无 is_archived 过滤
  stmt = (
      select(BehaviorPattern)
      .where(BehaviorPattern.user_id == user_id)
      .where(BehaviorPattern.confidence_score >= min_confidence)
      # ❌ 无: .where(BehaviorPattern.is_archived == False)
  )
  ```
  同样，`GET /patterns` 端点也不过滤已归档模式：
  ```python
  # cognitive.py:119-124 — 不过滤 is_archived
  stmt = (
      select(BehaviorPattern)
      .where(BehaviorPattern.user_id == current_user.id)
      .order_by(desc(BehaviorPattern.created_at))
  )
  ```
- **影响**: (1) 用户标记为"已克服"的模式仍出现在 AI 上下文中，导致 AI 对用户做不准确的判断 (2) 前端 PatternListScreen 显示已归档模式 (3) context_builder 注入的认知洞察包含已克服模式
- **修复**: 在两个查询中添加 `.where(BehaviorPattern.is_archived == False)` 或提供 `include_archived` 参数

#### P1-2: source_type/resource_type 使用原始 str 无校验，LLM prompt 注入风险
- **位置**: `backend/app/schemas/cognitive.py:19` + `backend/app/api/v1/cognitive.py:49-50`
- **问题**: `CognitiveFragmentCreate` 的 `source_type` 和 `resource_type` 是未约束的 `str`，客户端可传入任意值：
  ```python
  # schemas/cognitive.py:19 — 任意字符串
  source_type: str = Field(..., description="capsule, interceptor, behavior")
  resource_type: str = "text"
  ```
  这些值直接写入 DB 并进入 LLM 分析 prompt（`cognitive_service.py:428-456`）：
  ```python
  # cognitive_service.py:431 — 注入 LLM prompt
  Context: {fragment.context_tags}
  Error Tags: {fragment.error_tags}
  ```
  如果客户端传入恶意 `context_tags` 或 `error_tags`，可能影响 LLM 输出
- **修复**: 将 `source_type` 和 `resource_type` 改为枚举类型，对 `context_tags` 和 `content` 做 HTML/注入清洗

#### P1-3: analyze_behavior 异常时 status 设为 FAILED 但仅返回 error dict，无重试
- **位置**: `backend/app/services/cognitive_service.py:540-545`
  ```python
  except Exception as e:
      fragment.analysis_status = AnalysisStatus.FAILED
      fragment.error_message = str(e)[:200]
      await self.db.commit()
      return {"error": str(e)}  # ← 永久失败，无重试
  ```
- **影响**: 如果 LLM 超时、DB 连接断开等瞬态故障导致分析失败，碎片永久停留在 FAILED 状态。与 Error Book P0-1 同构问题。`CognitiveEventConsumer` 的 rate limiter 不会重试已失败的分析
- **修复**: 添加重试逻辑（最多 3 次，指数退避），或创建 `/cognitive/fragments/:id/retry` 端点

#### P1-4: severity 字段无业务上限语义，LLM 提示中 severity 1-5 含义模糊
- **位置**: `backend/app/schemas/cognitive.py:26` + `backend/app/services/cognitive_service.py:433`
  ```python
  # schema: 1-5 范围
  severity: int = Field(1, ge=1, le=5)
  
  # prompt: 仅写 "Severity: X/5"，无映射表
  Severity: {fragment.severity}/5
  ```
- **影响**: LLM 收到 "Severity: 3/5" 但不知道 3 意味着什么（低？中？高？），降低分析质量
- **修复**: 在 prompt 中添加 severity 映射说明（1=轻微, 3=中等, 5=严重）

#### P1-5: GET /fragments 不过滤 analysis_status，大量 FAILED 碎片返回前端
- **位置**: `backend/app/api/v1/cognitive.py:91-108` + `backend/app/services/cognitive_service.py:650-660`
- **问题**: 碎片列表查询不过滤 `analysis_status`，返回所有状态（PENDING/PROCESSING/COMPLETED/FAILED）的碎片：
  ```python
  # cognitive_service.py:652-658 — 无 status 过滤
  stmt = (
      select(CognitiveFragment)
      .where(CognitiveFragment.user_id == user_id)
      # ❌ 无: .where(CognitiveFragment.analysis_status != AnalysisStatus.FAILED)
  )
  ```
- **影响**: 前端需要自行过滤 FAILED 碎片，增加客户端负担
- **修复**: 添加 `status` 查询参数，默认排除 FAILED

---

### P2 — 改进建议（3 项）

#### P2-1: behavior_patterns 表无 (user_id, pattern_name) 联合唯一约束，依赖应用层查重
- **位置**: `backend/gateway/internal/db/schema.sql` (behavior_patterns 表)
- **问题**: `_upsert_pattern()` 通过 `SELECT ... WHERE pattern_name = ?` 做字符串精确匹配查重（cognitive_service.py:561-566），无 DB 级唯一约束。并发创建相同 pattern_name 的碎片可能产生重复模式记录
- **修复**: 添加 `CREATE UNIQUE INDEX idx_bp_user_name ON behavior_patterns(user_id, pattern_name) WHERE deleted_at IS NULL`

#### P2-2: _upsert_pattern 使用 EMA 更新 confidence 但 EMA alpha=0.3 硬编码
- **位置**: `backend/app/services/cognitive_service.py:577`
  ```python
  alpha = 0.3  # ← 硬编码
  pattern.confidence_score = alpha * new_confidence + (1 - alpha) * pattern.confidence_score
  ```
- **修复**: 提取到配置文件或 phase5_config

#### P2-3: GET /patterns 端点按 created_at 排序而非 confidence_score，与 get_user_patterns 不一致
- **位置**: `backend/app/api/v1/cognitive.py:122` vs `backend/app/services/cognitive_service.py:671`
  ```python
  # API: 按 created_at 排序
  .order_by(desc(BehaviorPattern.created_at))
  # Service: 按 confidence 排序
  .order_by(desc(BehaviorPattern.confidence_score))
  ```
- **修复**: 统一为 confidence_score 排序

---

### 合规项（5 项）

1. **幂等性设计** ✅ — `create_fragment()` 通过 `source_event_id` 实现幂等（cognitive_service.py:152-162），相同事件不创建重复碎片
2. **pgvector 优雅降级** ✅ — 向量运行时错误检测 → 用户级别禁用 → 无 embedding 插入 fallback，5 层防御（cognitive_service.py:42-79）
3. **HyDE RAG 策略** ✅ — 短查询（<HYDE_QUERY_LENGTH_THRESHOLD）使用 HyDE 文档生成 + 向量检索，长查询直接检索，带超时保护
4. **前后端 PatternType 对齐** ✅ — Python `PatternType` (cognitive/emotional/execution) 与 Flutter `PatternType` (cognitive/emotional/execution/unknown) 兼容，Flutter 有 `unknown` 兜底
5. **多系统集成** ✅ — 认知数据流入 7+ 系统：ContextBuilder、CapsuleGeneration、ExecutionLearning、ProfileEventConsumer、Dashboard、Theater、BehaviorSignalCollector

---

## 数据流图

```
Flutter 认知操作 (碎片创建/模式查看/胶囊消费)
  │
  ├── [创建碎片] POST /cognitive/fragments → Go proxy → Python
  │   ├── 创建 CognitiveFragment (status=PENDING) ✅
  │   ├── Embedding 生成 (pgvector) ✅
  │   │   └── Fallback: 无 embedding 插入 ✅
  │   ├── 发布 cognitive.fragment.created 事件 ✅
  │   │   └── CognitiveEventConsumer → analyze_behavior() ⚠️ (P0-1 第二条路径)
  │   ├── GLM Batch 决策:
  │   │   ├── GLM Batch 可用 → enqueue GLM batch ✅
  │   │   └── GLM Batch 不可用 → BackgroundTask ⚠️ (P0-1 第一条路径)
  │   └── SystemUpdate 入队 ✅
  │
  ├── [分析] analyze_behavior() 双路径触发 ⚠️ (P0-1)
  │   ├── status → PROCESSING ✅
  │   ├── RAG 检索 (raw + HyDE) ✅
  │   │   └── pgvector HNSW 索引 ✅
  │   ├── LLM 分析 (带 fallback) ✅
  │   │   └── Fallback: {"pattern_name": "Unknown", "confidence": 0.0}
  │   ├── confidence > 0.6 → _upsert_pattern():
  │   │   ├── 字符串匹配查重 ⚠️ 无 DB 唯一约束 (P2-1)
  │   │   ├── EMA confidence 更新 ✅
  │   │   ├── evidence_ids 追加 (str 类型) ⚠️ (P0-2)
  │   │   ├── PROFILE_COGNITIVE_UPDATED 事件 ✅
  │   │   │   └── CapsuleEventConsumer → 胶囊重生成 ✅
  │   │   │   └── ExecutionLearningService → 执行策略更新 ✅
  │   │   └── behavior.pattern.updated 事件 (confidence ≥ 0.7) ✅
  │   │       └── ProfileEventConsumer → 缓存失效 ✅
  │   │       └── TaskEventConsumer → 任务策略更新 ✅
  │   ├── status → COMPLETED ✅
  │   └── ❌ 异常 → status=FAILED, 无重试 (P1-3)
  │
  ├── [查看模式] GET /cognitive/patterns
  │   ├── ⚠️ 不过滤 is_archived (P1-1)
  │   ├── ⚠️ 按 created_at 而非 confidence 排序 (P2-3)
  │   └── ⚠️ evidence_ids 类型可能不匹配 (P0-2)
  │
  ├── [查看碎片] GET /cognitive/fragments
  │   └── ⚠️ 不过滤 analysis_status (P1-5)
  │
  └── [胶囊消费] GET /capsules/today → CapsuleRepository
      ├── 胶囊详情 (depth, quality, personalization) ✅
      ├── 反馈 (5 星评分 + 分类 + 评论) ✅
      ├── 收藏 + 分享 ✅
      └── Flutter: Hive 缓存 + 离线同步 ✅
  
  ↓ 跨系统消费汇总
  
  ContextBuilder ← cognitive_insights (patterns by type, top patterns) ✅
  Prompts ← _format_cognitive_prism_section() (模式注入 LLM) ✅
  CapsuleGeneration ← get_user_patterns() for personalization ✅
  ExecutionLearning ← PROFILE_COGNITIVE_UPDATED ✅
  ProfileEventConsumer ← behavior.pattern.updated → 缓存失效 ✅
  TaskEventConsumer ← behavior.pattern.updated ✅
  DashboardService ← cognitive fragments (anxiety detection) ✅
  BehaviorSignalCollector → 隐式行为 → 碎片创建 ✅
  AchievementEventConsumer → 成就解锁 → 碎片创建 ✅
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | 分析双路径调度 | 移除 BackgroundTask，仅保留 EventBus 路径 | 低（删除 ~6 行 Python） |
| P0-2 | evidence_ids 类型不匹配 | schema 改为 `list[str]` | 低（1 行 Python） |
| P1-1 | 不过滤 is_archived | 添加过滤条件 | 低（~3 行 Python） |
| P1-2 | source_type 无枚举校验 | 改为 Literal 或 Enum 类型 | 低（~5 行 Python） |
| P1-3 | 分析失败无重试 | 添加重试逻辑或 retry 端点 | 中（~30 行 Python） |
| P1-4 | severity 含义模糊 | prompt 中添加映射说明 | 低（~3 行 Python） |
| P1-5 | 不过滤 FAILED 碎片 | 添加 status 查询参数 | 低（~5 行 Python） |

---

## 复核笔记

> **复核日期**: 2026-04-25
> **复核轮次**: 第十次唤醒 (Round #56 并行复核)
> **复核方式**: 代码验证
> **复核基准**: main project `/Users/brsama/code/GitHub/Sparkle-project/`

### 复核结果: 0/10 已修

| 原始编号 | 描述 | 状态 | 备注 |
|----------|------|------|------|
| P0-1 | 分析双路径调度 — BackgroundTask + EventBus 同时触发 | ❌ 未修 | `cognitive.py:80-86` BackgroundTask 仍在；`cognitive_event_consumer.py:78` EventBus 消费者仍在。唯一变化：`settings.ANALYSIS_SYNC_ON_EVENT=True`（默认值）使 `analyze_behavior()` 在 EventBus 路径走 `UnifiedAnalysisService` 而非直接 LLM prompt，但**双触发本身未消除**。当 `GLM_BATCH_ENABLED=False` 时 BackgroundTask 触发一次，EventBus 消费者再触发一次，两次分析仍并行执行。 |
| P0-2 | evidence_ids 存储为 `list[str]` 但 schema 声明 `list[UUID]` | ❌ 未修 | `cognitive_service.py:546-562` 仍用 `str(fragment_id)` 写入 evidence_ids。`schemas/cognitive.py:65` 仍声明 `evidence_ids: list[UUID] \| None`。类型不匹配未修。Pydantic v2 的 `from_attributes=True` 在大多数情况下会将 str 自动转为 UUID（宽松模式），但如果开启严格模式或将 evidence_ids 序列化为 JSON 再反序列化，可能导致 422。风险潜伏。 |
| P1-1 | get_user_patterns 不过滤 is_archived | ❌ 未修 | `cognitive_service.py:622-634` `get_user_patterns()` 仅过滤 `confidence_score >= min_confidence`，无 `is_archived == False` 过滤。`cognitive.py:118-124` GET /patterns 也不过滤。已归档模式仍返回给前端和 AI。 |
| P1-2 | source_type/resource_type 无枚举校验 | ❌ 未修 | `schemas/cognitive.py:18-21` 仍为未约束的 `str`。无 Literal/Enum 约束。客户端可传入任意值。 |
| P1-3 | analyze_behavior 异常无重试 | ❌ 未修 | `cognitive_service.py:505-510` 仍直接 `return {"error": str(e)}` 无重试。`cognitive_event_consumer.py:81-84` 虽有 DLQ 机制但仅对 EventBus 消费者路径有效，BackgroundTask 路径完全无重试。无 `/retry` 端点。 |
| P1-4 | severity 含义模糊 — prompt 仅 "X/5" | ❌ 未修 | `cognitive_service.py:398` 仍为 `Severity: {fragment.severity}/5`，无映射说明。LLM 无法区分 severity 1 和 5 的业务语义。 |
| P1-5 | GET /fragments 不过滤 FAILED 碎片 | ❌ 未修 | `cognitive_service.py:610-620` `get_fragments()` 无 `analysis_status` 过滤条件。`cognitive.py:91-107` 无 `status` 查询参数。所有状态碎片（含 FAILED）均返回前端。 |
| P2-1 | behavior_patterns 无 (user_id, pattern_name) 唯一约束 | ❌ 未修 | `schema.sql` 的 `behavior_patterns` 表无联合唯一索引。`_upsert_pattern()` 仍依赖应用层字符串精确匹配查重。并发写入仍可能产生重复模式。 |
| P2-2 | EMA alpha=0.3 硬编码 | ❌ 未修 | `cognitive_service.py:539` 仍为 `alpha = 0.3` 硬编码。未提取到配置。 |
| P2-3 | GET /patterns 按 created_at 而非 confidence_score 排序 | ❌ 未修 | `cognitive.py:121` 仍 `.order_by(desc(BehaviorPattern.created_at))`，与 `get_user_patterns()` 的 `.order_by(desc(BehaviorPattern.confidence_score))` 不一致。 |

### 复核附加发现

#### AF-1: ANALYSIS_SYNC_ON_EVENT 引入新的双路径语义差异
- **位置**: `cognitive_service.py:288-296`
- **发现**: 当 `ANALYSIS_SYNC_ON_EVENT=True`（当前默认值）且无 `batch_model_key` 时，`analyze_behavior()` 走 `UnifiedAnalysisService` 路径而非直接 LLM+RAG 路径。但 EventBus 消费者调用 `analyze_behavior(user_id, fragment_id)` 时不传 `batch_model_key`，会走 Unified 路径；而 BackgroundTask 也走同一路径。结果是两次完全相同的 Unified 分析，浪费更严重（Unified 分析成本 > 基础 LLM 分析成本）。
- **严重度**: P0（加剧 P0-1 的影响）

#### AF-2: EventBus 消费者无去重保护
- **位置**: `cognitive_event_consumer.py:43-84`
- **发现**: 消费者直接调用 `analyze_behavior`，不检查 fragment 的 `analysis_status`。如果 fragment 已处于 `COMPLETED` 或 `PROCESSING` 状态（因 BackgroundTask 先执行），EventBus 消费者仍会启动第二遍分析。`analyze_behavior()` 内部也无 status guard（不在 COMPLETED 时短路返回）。
- **严重度**: P1（可通过在 `analyze_behavior` 开头添加 `if fragment.analysis_status in (PROCESSING, COMPLETED): return` 缓解）

#### AF-3: Pydantic schema 缺少 updated_at 字段映射
- **位置**: `schemas/cognitive.py:57-73` (`BehaviorPatternResponse`)
- **发现**: Response schema 声明了 `updated_at: datetime`（行 70），但数据库模型 `BehaviorPattern` 继承自 `BaseModel`，其 `updated_at` 字段在模型更新时需手动维护。`_upsert_pattern()` 在更新模式时不更新 `updated_at`（仅 `commit()` 不触 `updated_at` 刷新），导致 `updated_at` 可能与实际更新时间不一致。
- **严重度**: P2（数据展示偏差）

### 跨轮次因果链更新

1. **P0-1 双触发 + AF-1 Unified 路径 + AF-2 无 status guard** = 三重叠加：每次碎片创建触发两次完整的 UnifiedAnalysisService 分析，无短路保护。这是当前 Cognitive Prism 系统中最紧迫的成本/正确性缺陷。
2. **P0-2 类型不匹配**仍为潜伏缺陷：在默认 Pydantic 配置下通常不会触发运行时错误，但如果未来启用严格模式或添加自定义验证器，将突然爆发。
3. 所有 P1/P2 项均未被触及，代码自 2026-04-22 审计以来未发生变化。
4. **合规项仍然有效**：幂等性（source_event_id）、pgvector 优雅降级、HyDE RAG 策略、PatternType 对齐、多系统集成等 5 项合规项均未退化。

---

## 复核笔记

> 复核者：Chris (Session 3) | 日期：2026-04-23
> 复核范围：对照主项目代码验证关键 P0/P1 发现

### 复核结果

| ID | 原始结论 | 复核结论 | 变化 |
|----|---------|---------|------|
| P0-1 | 双路径分析（BackgroundTask + EventBus） | **确认不变** | cognitive.py:81 仍有 background_tasks.add_task, 且 EventBus 消费者也触发分析 |
| P0-2 | evidence_ids 类型不匹配（str vs UUID） | **确认不变** | cognitive_service.py 存 str, schemas/cognitive.py:65 声明 list[UUID] |
| P1-1 | is_archived 无过滤 | **确认不变** | cognitive_service.py 中 is_archived 出现 0 次 |
| P1-2 | source_type 无枚举约束 | 未验证 | — |
| P1-3 | FAILED 无重试 | 未验证 | — |
| P1-4 | severity 含义模糊 | 未验证 | — |
| P1-5 | 不过滤 analysis_status | 未验证 | — |
| AF-1 | ANALYSIS_SYNC_ON_EVENT 双重分析 | 未验证 | — |
| AF-2 | EventBus 盲目重复分析 | 未验证 | — |

### 判定

P0-1 (双路径) 和 P0-2 (类型不匹配) 均确认存在且未修复。P1-1 (is_archived) 也确认未修复。这些是架构级问题，需按优先级排期修复。

**状态更新**: ⚠️ 已复核-有更新 → ⚠️ 已复核-二次确认（无变化）
