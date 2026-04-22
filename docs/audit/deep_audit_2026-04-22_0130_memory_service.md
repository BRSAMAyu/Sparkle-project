# 深度审计：Memory Service 写入路径

> 日期：2026-04-22 01:30
> 范围：`memory_service.py` 写入方法 → `memory_inferred_write_lane.py` AI 推断写入 → `chat_signal_collector.py` 信号收集 → `context_pack.py` 读取 → `prompts.py` 渲染 → DB schema（12 表 + 索引）

## 审计发现

### P0 — 阻断性问题（2 项）

#### P0-1: AI 推断记忆写入默认禁用，对话过程不创建任何情景记忆
- **位置**: `backend/app/config/settings.py:543` + `backend/app/services/memory_inferred_write_lane.py:94-97, 122-125`
- **问题**: `SPARKLE_MEMORY_INFERRED_WRITE_ENABLED = False`，两个主要写入入口（`enqueue_from_chat_turn`, `enqueue_from_session`）均在此标志为 False 时直接 return
  ```python
  # settings.py:543
  SPARKLE_MEMORY_INFERRED_WRITE_ENABLED: bool = False  # ← 禁用

  # memory_inferred_write_lane.py:94-97
  if not (settings.SPARKLE_MEMORY_INFERRED_WRITE_ENABLED
          or settings.SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED):
      return  # 直接返回，不写入任何记忆
  ```
- **影响**: 用户进行 100 轮对话后，系统对用户的认知仅为：每 20 轮通过 ChatSignalCollector 推断的偏好（仅 preference 类型）。没有情景记忆（用户讨论了什么、学到了什么、经历了什么），系统是"金鱼记忆"
- **验证**: 搜索所有 memory_service 写入调用点 — `create_episodic_memory()` 仅被 `focus_service.py:178` 和 `error_book_service.py:333,799` 调用（非对话路径），对话流中零调用
- **修复**: (1) 将 `SPARKLE_MEMORY_INFERRED_WRITE_ENABLED` 设为 True（Stage 16 Rule Y 要求 Default-OFF + revocable，建议灰度开启）(2) 添加干运行模式验证推断质量后再正式开启

#### P0-2: 记忆读取路径 56-75% 数据丢失，关键元数据未到达 LLM
- **位置**: `backend/app/core/context_pack.py:561-583` (数据转换) → `prompts.py:2585-2721` (渲染)
- **问题**: ContextPackBuilder 将记忆数据转换为轻量 payload 时丢弃了关键字段
  ```python
  # context_pack.py:561-564 — Preferences: 仅保留 key/value
  preferences = {
      entry.item.pref_key: entry.item.pref_value  # 丢失: confidence, evidence_refs, evidence_score
  }
  # context_pack.py:565-573 — Goals: 仅保留 4 字段
  goal_payloads = [{
      "id": ..., "title": ..., "status": ..., "target_date": ...
      # 丢失: expires_at, metadata_payload, evidence_refs, evidence_score
  }]
  # context_pack.py:574-583 — Episodic: 仅保留 5 字段
  episodic_payloads = [{
      "id": ..., "summary": ..., "occurred_at": ..., "importance_score": ..., "tags": ...
      # 丢失: confidence, evidence_refs, evidence_snapshot, source_type, source_id
  }]
  ```
- **影响**: LLM 无法判断记忆可靠度（无 confidence）；无法追溯记忆来源（无 evidence_refs）；无法区分用户明确说过的 vs AI 推断的（无 source_type）
- **修复**: 在 payload 中至少保留 `confidence` 和 `source_type`，让 LLM 知道哪些记忆更可靠

---

### P1 — 重要问题（4 项）

#### P1-1: episodic_memories 和 scenes 有 embedding 列但无 HNSW 索引，向量搜索全表扫描
- **位置**: DB schema — `episodic_memories.embedding vector(1024)` 和 `scenes.centroid_embedding vector(1024)` 存在但无 HNSW 索引
- **对比**: `cognitive_fragments` 有 `idx_cognitive_fragments_embedding_hnsw`（HNSW + vector_cosine_ops）
- **影响**: 情景记忆的语义相似度搜索为全表扫描，O(N) 复杂度；随数据量增长查询时间线性退化
- **修复**: 为 episodic_memories 和 scenes 添加 HNSW 索引

#### P1-2: ChatSignalCollector 仅每 20 轮写入偏好，前 19 轮对话完全无记忆反馈
- **位置**: `backend/app/services/chat_signal_collector.py:34-89`
- **问题**: `WINDOW_SIZE = 20`，每 20 轮才触发一次 `ProfileWriteService.update_inferred_preference()`
- **影响**: 用户在第 1-19 轮表达的所有偏好（学习风格、难度偏好、话题兴趣）完全丢失，直到第 20 轮才被批量处理
- **修复**: (1) 降低窗口到 5 轮 (2) 或每轮增量更新

#### P1-3: ContextPackBuilder 无缓存，每条聊天请求 3 次 DB 查询获取记忆
- **位置**: `backend/app/core/context_pack.py:461-463`
  ```python
  # 每次请求都直接查 DB，无缓存
  preference_records = await self.memory_service.list_preference_records(user_id)
  goals = await self.memory_service.list_active_goals(user_id)
  episodic = await self.memory_service.list_recent_episodic(user_id, limit=20)
  ```
- **影响**: 高频对话中记忆查询成为 DB 热点
- **修复**: 添加 60s TTL Redis 缓存，记忆写入时主动失效

#### P1-4: memory_evolutions 表无分区/清理，审计日志无限增长
- **位置**: DB schema — `memory_evolutions` 表
- **问题**: 记录所有记忆变更的审计日志（10M-50M rows @ 10K users），无分区、无 TTL、无清理
- **影响**: 长期运行后表体积膨胀，查询变慢，存储成本增加
- **修复**: 按 `created_at` 月分区 + 90 天后归档到冷存储

---

### P2 — 改进建议（3 项）

#### P2-1: episodic_memories 表无分区，按时间增长的表不适合全量存储
- **位置**: DB schema
- **修复**: 考虑按 `occurred_at` 月分区

#### P2-2: 记忆生命周期查询需检查 4 个时间戳（archived_at + retracted_at + revoked_at + deleted_at）
- **位置**: memory_service.py 查询逻辑
- **问题**: 每次查询需 `WHERE archived_at IS NULL AND retracted_at IS NULL AND deleted_at IS NULL`
- **修复**: 添加 `is_active` 计算列或 partial index

#### P2-3: scenes 表仅存在于 SQLAlchemy 模型，不在 schema.sql 中
- **位置**: Python model 有 scenes 定义，Go schema.sql 中未找到对应表
- **影响**: Go Gateway 无法直接访问 scenes 数据（如需跨服务查询）
- **修复**: 如需 Go 侧访问，添加到 schema.sql + sqlc 生成

---

### 合规项（4 项）

1. **写入权限控制** ✅ — `_allow_write()` + `MemoryPolicyEvaluator` 检查用户级别记忆控制
2. **证据质量追踪** ✅ — 所有记忆类型有 `evidence_score`, `evidence_missing`, `correction_count`
3. **偏好版本链** ✅ — `version` + `replaced_by_id` 实现偏好版本化
4. **衰减与治理任务** ✅ — `memory_jobs.py` 实现了衰减、归档、健康检查、日快照 4 种定时任务

---

## 数据流图

```
用户对话 (100 轮)
  │
  ├── [写入路径 A: AI 推断] ⚠️ DISABLED (P0-1)
  │   ├── MemoryInferredWriteLaneService.enqueue_from_chat_turn()
  │   │   └── SPARKLE_MEMORY_INFERRED_WRITE_ENABLED=False → return
  │   └── MemoryInferredWriteLaneService.enqueue_from_session()
  │       └── SPARKLE_MEMORY_INFERRED_WRITE_ENABLED=False → return
  │
  ├── [写入路径 B: ChatSignalCollector] ✅ 仅偏好
  │   ├── 每 20 轮触发一次 (P1-2)
  │   └── → ProfileWriteService.update_inferred_preference()
  │       → memory_service.upsert_preference() ✅
  │
  ├── [写入路径 C: 显式操作] ✅
  │   ├── 用户设置偏好 → profile_write_service → upsert_preference
  │   └── 用户纠正记忆 → apply_correction → retract + recreate
  │
  │   ❌ 无写入: create_episodic_memory() 在对话流中零调用
  │   ❌ 无写入: create_goal() 在对话流中零调用
  │
  ↓ 结果: 100 轮后仅有 ~5 条 preference 记忆
  │
  ├── [读取路径]
  │   ├── ContextPackBuilder.build()
  │   │   ├── list_preference_records() → DB (无缓存 ⚠️ P1-3)
  │   │   ├── list_active_goals() → DB
  │   │   └── list_recent_episodic() → DB (大概率空)
  │   │
  │   ├── 数据转换: 56-75% 字段丢失 ⚠️ (P0-2)
  │   │   ├── preference → {key, value} (丢失 confidence, evidence)
  │   │   ├── goals → {id, title, status, target_date} (丢失 evidence)
  │   │   └── episodic → {id, summary, occurred_at, importance, tags}
  │   │       (丢失 confidence, source_type, evidence)
  │   │
  │   └── to_prompt_context() → build_system_prompt()
  │       ├── prompts.py:2585-2599 → 渲染偏好
  │       ├── prompts.py:2707-2712 → 渲染目标
  │       └── prompts.py:2714-2721 → 渲染情景记忆（通常空）
  │
  ↓
LLM 收到: 仅 {key:value} 偏好 + 0 条情景记忆
  └── 系统对用户的认知 ≈ 空
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | AI 推断记忆写入禁用 | 灰度开启 `INFERRED_WRITE_ENABLED` + dry-run 验证 | 配置（0 行代码） |
| P0-2 | 读取路径 56-75% 数据丢失 | ContextPackBuilder 保留 confidence + source_type | 低（~20 行 Python） |
| P1-1 | episodic/scenes 无 HNSW 索引 | 添加 HNSW 索引 | 低（2 条 DDL） |
| P1-2 | 偏好写入窗口 20 轮过大 | 降低到 5 轮或增量更新 | 低（1 行配置） |
| P1-3 | ContextPackBuilder 无缓存 | 60s Redis 缓存 + 写入时失效 | 中（~40 行 Python） |
| P1-4 | memory_evolutions 无限增长 | 月分区 + 90 天归档 | 中（迁移 + 清理任务） |
