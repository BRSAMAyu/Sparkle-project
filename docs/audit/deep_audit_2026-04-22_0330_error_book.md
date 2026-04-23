# 深度审计：Error Book（错题本）完整链路

> 日期：2026-04-22 03:30
> 范围：Flutter 错题创建/编辑/复习/筛选 → Go Gateway gRPC handler → Python error_book_service CRUD + SM-2 间隔复习 → 后台分析管道（9 步）→ 事件发布 → 认知碎片/知识图谱/掌握度同步/自适应重规划 → DB schema（error_records 表）

## 审计发现

### P0 — 阻断性问题（2 项）

#### P0-1: 错题分析管道以 BackgroundTask 运行，失败后无重试无通知，核心 AI 价值静默丢失
- **位置**: `backend/app/services/error_book_service.py:139-165` (create_error → BackgroundTasks) + `:167-298` (analyze_and_link 9 步管道)
- **问题**: `create_error()` 返回 201 后，将 9 步分析管道（OCR → 向量检索 → LLM 分析 → 语义记忆 → 掌握度同步 → 事件发布）作为 FastAPI BackgroundTask 执行。如果任何步骤抛出未预期的异常，整个管道终止：
  ```python
  # error_book_service.py:139-165 — 创建后立即返回
  async def create_error(self, user_id, data):
      error = ErrorRecord(...)
      db.add(error)
      await db.commit()
      background_tasks.add_task(self.analyze_and_link, error.id, user_id)
      return error  # ← 此时 latest_analysis = null
  
  # analyze_and_link() 9 步管道中，如果 LLM 超时或 DB 异常：
  # → latest_analysis 永久为 null
  # → 无自动重试
  # → 无用户通知
  # → 用户看到 "暂无分析" 但不知道为什么或可以重新触发
  ```
- **对比**: 虽然有 fallback 策略（LLM 失败 → 正则分析；向量搜索失败 → ILIKE 搜索），但 BackgroundTask 级别的进程崩溃（OOM、连接超时）不在 fallback 覆盖范围内
- **影响**: 错题本的核心价值是 AI 诊断。如果分析管道静默失败，错题退化为原始文本/图片记录，用户失去根因分析、修正步骤、知识关联等核心功能。这是产品关键路径的断裂
- **修复**: (1) 将分析管道改为 Celery 任务（支持重试 + DLQ）(2) 失败时通过 WebSocket/SystemUpdate 通知用户 (3) 前端检测 `latest_analysis == null` 且 `created_at > 5min` 时显示 "分析失败，点击重试" 提示

#### P0-2: 错题纠正闭环无成就反馈，Growth Loop "Reinforce" 阶段对错题本完全失效
- **位置**: `backend/app/services/achievement_engine.py:67-91` (AchievementEvent 枚举) + `backend/app/schemas/error_book.py:31-41` (ErrorTypeEnum)
- **问题**: AchievementEngine 的 `AchievementEvent` 枚举有 `TASK_COMPLETED`, `STUDY_MINUTES_ACCUMULATED`, `NODE_MASTERED` 等事件，但**无 `ERROR_FIX` 或 `ERROR_REVIEWED` 事件类型**：
  ```python
  # achievement_engine.py — 无错题相关事件
  class AchievementEvent:
      TASK_COMPLETED = "task_completed"
      STUDY_MINUTES_ACCUMULATED = "study_minutes_accumulated"
      NODE_MASTERED = "node_mastered"
      # ❌ 无: ERROR_FIX = "error_fix"
      # ❌ 无: ERROR_REVIEW_STREAK = "error_review_streak"
  ```
- **对比**: 任务完成 → 成就解锁（Task Service），专注完成 → 成就解锁（Focus Service），但错题复习/纠正 → 无成就
- **影响**: 错题本是 24 个路由模块之一，用户创建错题 → AI 分析 → 复习纠正 的完整闭环缺少 "Reinforce" 阶段。用户纠正错题后无任何游戏化反馈（无成就弹窗、无火焰点、无视觉元素解锁），降低了错题复习的动力
- **修复**: (1) 在 AchievementEvent 中添加 `ERROR_FIX` 和 `ERROR_REVIEW_STREAK` 事件 (2) 在 `submit_review()` 中调用 `AchievementEngine.process_event()` (3) 定义错题相关成就（"首次纠错"、"连续复习 7 天"、"消灭知识盲点"）

---

### P1 — 重要问题（5 项）

#### P1-1: linked_knowledge_node_ids 为 UUID 数组，无外键约束，知识节点删除后残留悬挂引用
- **位置**: `backend/app/models/error_book.py:57` + `backend/gateway/internal/db/schema.sql`
  ```python
  # error_book.py:57 — UUID 数组，无 FK
  linked_knowledge_node_ids = Column(ArrayUUIDCompat, default=list)
  ```
- **对比**: 其他模型的知识节点关联使用 `TaskKnowledgeLink` 中间表 + FK 约束
- **影响**: 知识节点被删除后（如用户删除 Galaxy 节点），`linked_knowledge_node_ids` 中的 UUID 引用仍存在。前端展示关联知识点时需逐个验证有效性，增加查询负担
- **修复**: (1) 添加事件消费者监听 `galaxy.node.deleted` 事件，清理 error_records 中的引用 (2) 或迁移到中间表模式

#### P1-2: ErrorReplanBridge 的 time_management 触发基于启发式关键词匹配，可能产生误触发
- **位置**: `backend/app/services/error_replan_bridge.py:243-252`
  ```python
  # error_replan_bridge.py:243-248 — 启发式匹配
  if raw_error_type == "time_management" or any(
      token in f"{root_cause} {study_suggestions}" for token in ("time", "rush", "pace", "deadline")
  ):
      return "time_management"
  ```
- **影响**: 如果 LLM 分析的 `root_cause` 包含 "at that time" 或 "pace of learning" 等非时间管理相关表述，会误分类为 `time_management` 触发类型，导致不相关的计划健康评估
- **修复**: 缩小关键词范围，或要求 `raw_error_type` 也匹配 `time_pressure` 才触发

#### P1-3: Flutter 7 个科目标签和多个屏幕硬编码中文，未走国际化
- **位置**:
  - `mobile/lib/features/error_book/presentation/widgets/subject_chips.dart:20-56` — 7 个科目名称
  - `add_error_screen.dart:264,329,344,376,398` — "移除"、"重新上传图片"、"编辑错题" 等
  - `review_screen.dart:14-17,92` — "今日复习"、"按科目"、"薄弱专攻"、"随机抽查"、"退出复习"
  - `error_book_repository.dart:266-285` — 错误提示消息（"错题不存在或已删除"、"网络超时" 等）
- **修复**: 迁移到 l10n YAML

#### P1-4: 错题本使用独立的 Go gRPC handler，与项目主流 proxy 模式架构不一致
- **位置**: `backend/gateway/internal/handler/error_book.go` (329 行) + `backend/gateway/internal/error_book/client.go` (110 行)
- **对比**: 其他 23 个路由模块使用 `proxyWithHeaders` 直接转发 REST 到 Python
- **影响**: (1) 维护两套路由架构（proxy + gRPC handler）(2) proto 定义与 Python REST API 需手动保持同步 (3) 新增字段需同时修改 proto + Go handler + Python service
- **修复**: 统一为 proxy 模式，或为所有模块采用 gRPC 模式

#### P1-5: ErrorRecord 使用 `is_deleted` 布尔字段，与项目其他模型的 `deleted_at` 时间戳模式不一致
- **位置**: `backend/app/models/error_book.py:63` vs 其他模型使用 `deleted_at`
  ```python
  # error_book.py:63 — 布尔软删除
  is_deleted = Column(Boolean, default=False)
  
  # 其他模型 — 时间戳软删除
  deleted_at = Column(DateTime)
  ```
- **缓解**: 服务层查询已正确过滤 `is_deleted == False`（error_book_service.py:565,642,817），无数据泄露风险
- **影响**: 丧失删除时间信息（无法按删除时间排序/恢复），与 BaseModel 模式不兼容，新开发者可能误用 `deleted_at` 查询
- **修复**: 迁移到 `deleted_at` 时间戳模式，添加 Alembic 迁移

---

### P2 — 改进建议（3 项）

#### P2-1: memory_lapse 错误类型不被 ErrorReplanBridge 覆盖，遗漏记忆衰退信号
- **位置**: `backend/app/services/error_replan_bridge.py:234-253` — `_classify_trigger_type_from_analysis()` 返回 None for memory_lapse
- **修复**: 添加 `memory_lapse → "knowledge_gap"` 映射

#### P2-2: ReviewSchedulerService 使用 `random.uniform()` 无固定种子，测试不确定
- **位置**: `backend/app/services/error_book_service.py:107`
  ```python
  jitter = random.uniform(0.9, 1.1)  # 非确定性
  ```
- **修复**: 测试时注入固定种子的 random 实例

#### P2-3: ErrorRecord 继承 `Base` 而非 `BaseModel`，缺失自动软删除过滤
- **位置**: `backend/app/models/error_book.py:17`
  ```python
  class ErrorRecord(Base):  # ← 非 BaseModel
  ```
- **影响**: 服务层必须手动在每条查询中添加 `is_deleted == False` 过滤。当前已正确处理，但未来新增查询时可能遗漏
- **修复**: 统一继承 BaseModel 或添加自定义 mixin

---

### 合规项（5 项）

1. **SM-2 算法正确实现** ✅ — mastery_level 在 [0.0, 1.0] 范围内正确钳位（error_book_service.py:98-102），EF 因子限制在 [1.3, 2.5]，间隔抖动 ±10% 防复习轰炸
2. **丰富的事件驱动集成** ✅ — 错题创建触发 7+ 下游系统（Galaxy、Cognitive、Memory、SignalProcessor、MasterySync、ErrorReplanBridge）
3. **ErrorReplanBridge 智能类型映射** ✅ — 将 9 种 ErrorTypeEnum 值映射到 6 种触发类型，覆盖 concept_confusion、knowledge_gap、method_wrong、reading_careless、calculation_error、logic_error
4. **多层 fallback 策略** ✅ — LLM 失败 → 正则分析；向量搜索失败 → ILIKE 搜索；JSONB 查询失败 → Python 过滤
5. **软删除正确实现** ✅ — 所有查询方法均过滤 `is_deleted == False`（lines 565, 642, 817），删除操作设置 `is_deleted = True`

---

## 数据流图

```
Flutter 错题操作 (创建/编辑/复习/删除)
  │
  ├── [创建] POST /errors → Go gRPC handler → Python
  │   ├── 创建 ErrorRecord (mastery=0.0, analysis=null) ✅
  │   ├── 返回 201 (立即响应) ✅
  │   └── BackgroundTask: analyze_and_link() 9 步管道:
  │       ├── Step 1: OCR (sparkle-file:// → presigned URL → GLM OCR)
  │       ├── Step 2: RAG 向量检索 → linked_knowledge_node_ids ✅
  │       │   └── Fallback: ILIKE keyword search ✅
  │       ├── Step 3: LLM 分析 → latest_analysis (JSONB) ✅
  │       │   └── Fallback: _build_fallback_analysis() (regex) ✅
  │       ├── Step 4: DB 更新 (analysis + links) ✅
  │       ├── Step 5: SemanticMemoryService (策略节点) ✅
  │       ├── Step 6: EpisodicMemoryService (情景记忆) ✅
  │       ├── Step 7: ErrorBookSignalProcessor (偏好更新) ✅
  │       ├── Step 8: ErrorBookMasterySyncService (掌握度 -3~-10) ✅
  │       └── Step 9: 发布 error_created 事件 ✅
  │           ├── GalaxyEventConsumer → graph evolution ✅
  │           ├── ErrorReplanBridge → 自适应重规划 ✅
  │           ├── AutoFragmentCollector → 认知碎片 ✅
  │           └── ProfileEventConsumer → 画像更新 ✅
  │       ⚠️ 管道失败 = 无重试 + 无通知 (P0-1)
  │
  ├── [复习] POST /errors/:id/review → SM-2 算法
  │   ├── Remembered: mastery +0.15, interval 增长 ✅
  │   ├── Fuzzy: mastery -0.05, interval 维持 ✅
  │   ├── Forgotten: mastery -0.20, interval 重置 ✅
  │   ├── MasterySync: 节点掌握度 +4/+1/-2 ✅
  │   ├── EpisodicMemory: practice_outcome ✅
  │   └── ❌ 无成就触发 (P0-2)
  │
  ├── [语义摘要] GET /errors/:id/semantic
  │   ├── 根因分析 (from latest_analysis) ✅
  │   ├── 关联知识节点 (linked_knowledge_node_ids) ✅
  │   ├── 学习策略 (SemanticMemoryService) ✅
  │   └── 相似错题 (same root_cause) ✅
  │
  └── [自适应触发] error_created → ErrorReplanBridge
      ├── 智能类型映射: 9 种 ErrorType → 6 种触发类型 ✅
      ├── 条件: mastery < 50 && errors >= 3 in 7d ✅
      ├── 冷却: 24h 间隔 ✅
      └── → AdaptiveReplanner.evaluate_plan_health_now() ✅
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | 分析管道无重试无通知 | 改为 Celery 任务 + 失败通知 | 中（~40 行 Python） |
| P0-2 | 无 ERROR_FIX 成就事件 | 添加成就事件 + 触发逻辑 | 中（~50 行 Python） |
| P1-1 | 知识节点 UUID 数组无 FK | 添加 node.deleted 事件清理 | 低（~20 行 Python） |
| P1-2 | time_management 启发式误触发 | 缩小关键词范围 | 低（~5 行 Python） |
| P1-3 | Flutter 硬编码中文 | 迁移到 l10n | 中（~80 行 Dart） |
| P1-4 | gRPC vs proxy 架构不一致 | 统一为 proxy 模式 | 高（~400 行 Go 重写） |
| P1-5 | is_deleted vs deleted_at 不一致 | 迁移到 deleted_at | 中（迁移 + 查询更新） |

---

## 复核笔记

> **复核日期**: 2026-04-25 05:30
> **复核轮次**: 第九次唤醒 (Round #55 并行复核)
> **复核方式**: 代码验证

### 复核结果: 0/8 已修 (2 项 N/A — ErrorReplanBridge 不存在于主项目)

| 原始编号 | 描述 | 状态 | 备注 |
|----------|------|------|------|
| P0-1 | 分析管道 BackgroundTask 无重试无通知 | ❌ 未修 | `error_book.py:54` 仍使用 `BackgroundTasks.add_task()`，无 Celery 迁移。有 `POST /{id}/analyze` 手动重触发端点但前端无失败提示 |
| P0-2 | 错题纠正无成就反馈 (Reinforce 失效) | ❌ 未修 | `AchievementEvent` 枚举无 `ERROR_FIX`/`ERROR_REVIEW` 事件。`submit_review()` 仅调 `ErrorBookSignalProcessor`，不调用 `AchievementEngine.process_event()` |
| P1-1 | linked_knowledge_node_ids 无 FK 约束 | ❌ 未修 | `error_book.py:57` 仍为 `ArrayUUIDCompat`，schema.sql 仍为 `uuid[]` 无 FK |
| P1-2 | ErrorReplanBridge time_management 误触发 | N/A | `error_replan_bridge.py` 不存在于主项目，仅存于 worktree |
| P1-3 | Flutter 硬编码中文 (7 科目 + 20+ 屏幕) | ❌ 未修 | `subject_chips.dart` 7 科目仍硬编码，`review_screen.dart` 20+ 处硬编码中文，零 l10n 引用 |
| P1-4 | 独立 Go gRPC handler vs proxy 模式 | ❌ 未修 | `error_book.go` (330 行) 仍为独立 gRPC handler，vs 项目 257 个 proxy 路由 |
| P1-5 | is_deleted vs deleted_at 不一致 | ❌ 未修 | `error_book.py:63` 仍为 `is_deleted Boolean`，`BaseModel` 用 `deleted_at DateTime` |
| P2-1 | memory_lapse 不被 ErrorReplanBridge 覆盖 | N/A | ErrorReplanBridge 不存在于主项目 |
| P2-2 | ReviewScheduler random.uniform 无种子 | ❌ 未修 | `error_book_service.py:99` 仍为 `random.uniform(0.9, 1.1)` |
| P2-3 | ErrorRecord 继承 Base 非 BaseModel | ❌ 未修 | `error_book.py:17` 仍为 `class ErrorRecord(Base)` |

### 复核附加发现

**AF-1: ErrorReplanBridge 整体缺失 (P0 级)**
审计报告 analyze_and_link() Step 9 描述"发布 error_created → ErrorReplanBridge → 重规划"。但 ErrorReplanBridge 整个文件不存在于主项目。error_created 事件消费者仅 GalaxyEventConsumer/AutoFragmentCollector/ProfileEventConsumer。**错题信号无法触发自适应重规划**。

**AF-2: error_summary/recent_errors 在 prompt 层完全不可见 (关联 Round #54 P1-1)**
context_manager.py 收集 error_summary/recent_errors 到 CognitiveContext，但 orchestrator_production.py 的 _build_user_context() 不调用 ContextOrchestrator，直接用 UserService.get_context()。prompts.py 的 _normalize_user_context() 也不提取这些字段。**错题数据在 AI prompt 中完全不可见**。

### 跨轮次因果链更新

| 本轮复核 | 关联 | 说明 |
|----------|------|------|
| P0-2 + AF-2 | Round #54 P1-1 (error data 死代码) | 错题数据双重断裂: 既不在 AI prompt 也不在成就引擎 |
| AF-1 | Memory "ErrorReplanBridge dormant" | 情况更严重: 不是 dormant 而是 absent |
| P1-3 | Round #47 i18n 盲区 + Round #52 P1-1 | 系统性 i18n 缺失 |
