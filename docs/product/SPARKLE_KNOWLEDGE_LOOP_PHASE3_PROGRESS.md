# Phase 3: 护城河闭环 — 进度文档

> **Parent**: [MASTER.md](./SPARKLE_GOAL_AWARE_KNOWLEDGE_LOOP_MASTER.md)
> **Status**: COMPLETE | Completed: 2026-04-26

---

## 目标
社群、错因、时间轴、自我模型全部接入。

## Tasks

### 3.1 社群共性错因 → 知识节点标注
- [x] 错题聚合服务提取共性 pattern
- [x] 匿名写入 knowledge node community_signal
- [x] 节点详情"社群洞察"tab 展示
- [x] Celery 定时任务每 6h 自动聚合 (wired)

**Files**: `community_error_aggregation_service.py`, `celery_tasks.py`, `celery_schedule.py`, `node_detail_sheet.dart`

**Details**:
- `CommunityErrorAggregationService` with MIN_USERS_FOR_AGGREGATION=3
- `aggregate_community_error_patterns` Celery task (21600s interval)
- Also available via `POST /galaxy/community/aggregate-errors`
- Flutter `_CommunityInsightSection` in node detail sheet

### 3.2 共享资料推荐流程
- [x] Community Resource Pool 质量/适用性评分
- [x] `GET /community/recommended-resources` endpoint
- [x] 高质量 GroupFile 资源推荐（trust_level verified/high）

**Files**: `community.py`

**Details**:
- Queries GroupFile from user's groups filtered by trust_level
- Returns file metadata with recommendation reason
- StoredFile import for file metadata lookup

### 3.3 混合时间轴 ContextPlan 因果轨迹
- [x] 每次 ContextPlan 写入 routing_decision_log
- [x] `GET /galaxy/context-plan/timeline` endpoint 可查询

**Files**: `session_state_mixin.py`, `galaxy.py`

**Details**:
- `_persist_context_plan()` writes `RoutingDecisionLog` with decision_type='context_plan'
- Timeline endpoint returns chronological decisions for the user

### 3.4 Aurora 自我校准
- [x] 检测资料策略失效（连续错题 >= 3 in 7 days）
- [x] 生成校准问题
- [x] 校准结果写入 ContextPlan (calibration_needed, calibration_question)

**Files**: `aurora_calibration_service.py`, `session_state_mixin.py`

**Details**:
- `AuroraCalibrationService.check_calibration_needed()` runs per-turn when retrieval is active
- Wired in `_apply_calibration_check()` after ContextPlan build
- 3 calibration question levels based on error count

### 3.5 资料卡
- [x] SourceAsset 详情：覆盖/用途/有效性
- [x] 质量指示器 (quality_score)
- [x] Drafts pending 徽章

**Files**: `document_library_screen.dart`, `document_library_models.dart`

**Details**:
- `_QualityIndicator` widget shows feedback-driven quality status
- `_DraftsPendingPill` with deep link to GalaxyRoutes.draftReview
- `DocumentProcessingStatus.hasDraftsPending` + `qualityScore` fields

### 3.6 知识星图节点五 tab
- [x] 概览 / 资料 / 错因 / 任务 / 社群洞察

**Files**: `node_detail_sheet.dart`

**Details**:
- `_CommunityInsightSection` and `_CommunityInsightContent` widgets
- Fetches node detail and displays community error patterns

---

## Gap Closures (post-initial implementation)

### Gap 5: Wire Aurora self-calibration
- [x] `_apply_calibration_check()` added to session_state_mixin
- Runs after ContextPlan build, before persistence

### Gap 6: Wire community error aggregation
- [x] Celery task `aggregate_community_error_patterns` registered
- Beat schedule: every 6 hours

### Gap 4: Expand Source Tray scope
- [x] `DocumentContextMode` expanded: auto/userSelected/taskScope/goalScope/off
- [x] `document_context_scope` passed from Flutter → backend → ContextPlan.source_scope
- [x] Backend maps Flutter mode names to source_scope values

### Gap 1: Task card knowledge-loop fields
- [x] `source_reason` and `fallback_action` added to TaskDocument model
- [x] `_SourceContextChip` shows when task has knowledgeNodeId
- [x] Alembic migration for new columns

---

## Commits
- `d47e63ea` feat(knowledge-loop): community error pattern aggregation (Phase 3.1)
- `cd3b1f60` feat(knowledge-loop): complete shared resource recommendation endpoint (Phase 3.2)
- `35baafe3` feat(knowledge-loop): ContextPlan timeline query + Aurora self-calibration (Phase 3.3 & 3.4)
- `536d3235` feat(knowledge-loop): Source Asset detail card with quality indicator (Phase 3.5)
- `5ebad198` feat(knowledge-loop): node detail community insights section (Phase 3.6)
- `08493b48` fix(db): merge split Alembic heads into single lineage
- `c359b008` feat(knowledge-loop): wire 4 gap closures — calibration, aggregation, scope, task card

---

## Self-Review Checklist
- [x] 所有 Python 文件 syntax check pass
- [x] Flutter analyze 0 errors (only info-level lints)
- [x] Celery task registered in beat schedule
- [x] Calibration wired into actual chat flow
- [x] Source scope flows end-to-end (Flutter→Go→Python)
- [x] Migration creates new columns reversibly
