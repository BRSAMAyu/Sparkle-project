# Phase 1: 闭环连通 — 进度文档

> **Parent**: [MASTER.md](./SPARKLE_GOAL_AWARE_KNOWLEDGE_LOOP_MASTER.md)
> **Status**: COMPLETE | Started: 2026-04-26 | Completed: 2026-04-26

---

## 目标

让现有管道真正跑通，用户能走完一次完整闭环。

## Tasks

### 1.1 Upload → 处理进度 → 通知 → Draft Review 路由打通
- [x] 上传后 SSE/WebSocket 实时推送处理阶段（OCR/分块/嵌入/节点生成）
- [x] 处理完成后推送通知"X 个新知识节点待确认"
- [x] 通知点击 → 深链到 galaxy_draft_review_screen
- [x] 资料库列表显示"X drafts pending"徽章

**Files**: `documents.py`, `document_library_screen.dart`, `document_library_models.dart`

**Details**:
- Backend: `DocumentStatusResponse` 新增 `drafts_pending` 字段
- Backend: 新增 `GET /documents/drafts/summary` 端点
- Flutter: `_DraftsPendingPill` 组件，点击深链到 `GalaxyRoutes.draftReview`
- Flutter: `DocumentProcessingStatus.hasDraftsPending` 属性

### 1.2 Context Receipt MVP
- [x] `format_graph_rag_document_context()` 改造：同时返回 receipt 数据
- [x] orchestrator 将 receipt 写入 metadata
- [x] Flutter 端解析 metadata.context_receipt 并渲染
- [x] 底部显示"基于：X / 未使用：Y"

**Files**: `orchestrator.py`, `response_builder.py`, `context_receipt_bar.dart`, `chat_bubble.dart`

**Details**:
- Backend: `orchestrator._hydrate_document_context()` 构建 `context_receipt`
  (used chunks with filenames/scores/evidence_strength, excluded_count, decision_reason)
- Backend: `response_builder.py` 将 receipt JSON 写入 `response_metadata`
- Flutter: `ContextReceiptBar` 组件解析 `rawMetadata['context_receipt']`
- Flutter: 集成到 chat_bubble 中 citation strip 下方

### 1.3 ContextPlan 结构升级
- [x] retrieval_intent.py 输出从 3 档改为 ContextPlan 对象
- [x] 新增 must_load / may_load / do_not_load / token_budget / pollution_guard
- [x] orchestrator 消费 ContextPlan 而非布尔 should_retrieve
- [x] ContextPlan 写入 state.context_data 供下游使用

**Files**: `retrieval_intent.py`

**Details**:
- 8-level `RetrievalMode`: no_retrieval, graph_only, targeted_source_rag,
  task_bound_rag, user_pinned_sources, deep_source_synthesis,
  community_aggregate_context, aurora_core_case_file
- `ContextPlan` dataclass: retrieval_mode, should_retrieve, budget_tokens,
  reason, source_scope, must_load/may_load/do_not_load, pollution_guard,
  citation_required, user_visible_receipt, reason_for_user
- `RetrievalDecision = ContextPlan` backward-compatible alias
- `legacy_mode` property for backward compat

### 1.4 知识节点详情页显示挂载资料
- [x] 节点详情 API 返回 attached documents + chunks (已有)
- [x] Flutter 节点详情页新增"资料"section (已有)
- [x] 显示资料片段预览 + "打开完整资料"链接 (已有)

**Files**: `galaxy.py`, `galaxy_service.py`, `node_detail_sheet.dart`, `node_source_materials_provider.dart`

**Details**:
- 完整管道已存在: `get_node_source_documents()` → `NodeSourceDocumentRef` → `_SourceMaterialsSection`
- 支持文档列表、chunk 预览、上传新文档
- `KnowledgeNodeDocument` 多对多表已建立

---

## Commits
- `c8252245` feat(knowledge-loop): upgrade RetrievalDecision to full ContextPlan with 8-level retrieval modes
- `0a0be027` feat(knowledge-loop): implement Context Receipt MVP (Phase 1.2)
- `ac692b72` feat(knowledge-loop): add draft review notification and routing (Phase 1.1)

---

## Self-Review Checklist
- [x] 所有改动不引入新 bug (Python tests pass, Flutter analyze 0 errors)
- [x] Python imports 无缺失
- [x] Flutter analyze 无 error
- [x] backward-compatible (RetrievalDecision alias, legacy_mode property)
- [x] ContextPlan.to_dict() 包含所有新字段
