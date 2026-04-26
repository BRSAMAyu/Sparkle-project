# Phase 2: Aurora Context Engineering — 进度文档

> **Parent**: [MASTER.md](./SPARKLE_GOAL_AWARE_KNOWLEDGE_LOOP_MASTER.md)
> **Status**: COMPLETE | Completed: 2026-04-26

---

## 目标
让 Aurora 每轮生成完整 ContextPlan，前端可感知。

## Tasks

### 2.1 ContextPlan 一等对象
- [x] ContextPlan dataclass 写入 routing_decision_log
- [x] 每轮结束后持久化，可用于时间轴回溯
- [x] 与 retrieval_decision_log 合并（通过 context_plan key）

**Files**: `session_state_mixin.py`

**Details**:
- `_persist_context_plan()` writes to `RoutingDecisionLog` with `decision_type='context_plan'`
- `state.context_data['context_plan']` + `context_plan_timestamp` stored per turn
- Async persistence with graceful failure handling

### 2.2 Aurora 状态带显示上下文决策
- [x] 新增 context_decision 状态
- [x] 收拢态："Aurora · 已参考相关资料"
- [x] 展开态：via context_receipt (existing ContextReceiptBar)

**Files**: `context_decision_provider.dart`, `status_awareness_bar.dart`

**Details**:
- `lastContextDecisionProvider` reads `context_receipt` from latest assistant message
- `StatusAwarenessBar` shows `reason_for_user` as secondary line below collapsed label

### 2.3 Source Tray 升级
- [x] 替代现有 studyMaterialsEnabled toggle
- [x] 三模式：auto / userSelected / off
- [x] Cycle through modes on tap

**Files**: `chat_state.dart`, `chat_input.dart`, `chat_screen.dart`, `chat_notifier_actions.dart`

**Details**:
- `DocumentContextMode` enum: auto / userSelected / off
- `_SourceTrayPill` cycles: auto → userSelected → off → auto
- Backward compatible: `documentRetrievalEnabled` stays in sync

### 2.4 LLM-powered 节点建议
- [x] 用 LLM 提取概念/考点 (已有: OntologyGenerator)
- [x] 生成有意义的节点名、描述、关键词
- [x] 新增 exam_weight 和 recommended_action 字段

**Files**: `ontology_generator.py`

**Details**:
- `KnowledgeNodeCandidate` now has `exam_weight` (0.0-1.0) and `recommended_action`
- Ontology prompt instructs LLM to include per-node exam weightings
- `_repair_payload` extracts and clamps new fields

### 2.5 资料质量反馈影响检索
- [x] citation feedback → quality_score 更新 (已有)
- [x] quality_score 作为检索排序因子 (已有)
- [x] 低质量资料降权 (已有)

**Files**: `document_service.py`, `graph_rag.py`

**Details**:
- Full loop already implemented: `publish_citation_feedback()` →
  `recalculate_document_quality_score()` → `get_document_quality_multiplier()` →
  applied in GraphRAG ranking with `feedback_loop_enabled` flag

---

## Commits
- `bf0fa39a` feat(knowledge-loop): persist ContextPlan to routing_decision_log
- `08c94567` feat(knowledge-loop): Aurora status bar shows context decision
- `e33d11f1` feat(knowledge-loop): Source Tray three-mode selector
- `0ad0af3c` fix(test): update stale mock overrides + enhance ontology node candidates

---

## Self-Review Checklist
- [x] 所有改动不引入新 bug
- [x] Python imports 无缺失
- [x] Flutter analyze 无 error (only info-level lints)
- [x] Backward compatible (documentRetrievalEnabled stays in sync)
