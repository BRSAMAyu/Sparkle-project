# Phase 1: 闭环连通 — 进度文档

> **Parent**: [MASTER.md](./SPARKLE_GOAL_AWARE_KNOWLEDGE_LOOP_MASTER.md)
> **Status**: IN PROGRESS | Started: 2026-04-26

---

## 目标

让现有管道真正跑通，用户能走完一次完整闭环。

## Tasks

### 1.1 Upload → 处理进度 → 通知 → Draft Review 路由打通
- [ ] 上传后 SSE/WebSocket 实时推送处理阶段（OCR/分块/嵌入/节点生成）
- [ ] 处理完成后推送通知"X 个新知识节点待确认"
- [ ] 通知点击 → 深链到 galaxy_draft_review_screen
- [ ] 资料库列表显示"X drafts pending"徽章

**Files**: `documents.py`, `ingestion_service.py`, galaxy upload overlay, document library screen

### 1.2 Context Receipt MVP
- [ ] `format_graph_rag_document_context()` 改造：同时返回 receipt 数据
- [ ] orchestrator 将 receipt 写入 metadata
- [ ] Flutter 端解析 metadata.context_receipt 并渲染
- [ ] 底部显示"基于：X / 未使用：Y"

**Files**: `graph_rag.py`, `orchestrator.py`, chat bubble widget, new context_receipt_widget.dart

### 1.3 ContextPlan 结构升级
- [ ] retrieval_intent.py 输出从 3 档改为 ContextPlan 对象
- [ ] 新增 must_load / may_load / do_not_load / token_budget / pollution_guard
- [ ] orchestrator 消费 ContextPlan 而非布尔 should_retrieve
- [ ] ContextPlan 写入 state.context_data 供下游使用

**Files**: `retrieval_intent.py`, `orchestrator.py`, `graph_rag.py`

### 1.4 知识节点详情页显示挂载资料
- [ ] 节点详情 API 返回 attached documents + chunks
- [ ] Flutter 节点详情页新增"资料"section
- [ ] 显示资料片段预览 + "打开完整资料"链接

**Files**: `galaxy.py`, node detail screen, node_source_materials_provider.dart

---

## Commits
*(to be filled as work progresses)*

---

## Self-Review Checklist
- [ ] 所有改动不引入新 bug
- [ ] Python imports 无缺失
- [ ] Go build 通过
- [ ] Flutter analyze 无 error
- [ ] smoke test 通过
