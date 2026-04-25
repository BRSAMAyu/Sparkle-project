# Reviewer B — E04: 错题本完整生命周期——录入→OCR→RAG→分析→节点关联→复习→掌握度
Timestamp: 2026-04-26T14:35:00+08:00
Chain Index: 22 (architect override to E04)

## Chain Flow Summary
用户在移动端录入错题（文字或图片），后端异步执行 OCR→RAG 向量检索→LLM 分析→节点关联→掌握度更新。复习时 SM-2 算法调度间隔，复习结果再次更新掌握度。整条链路从后端到 EventBus 消费者完整贯通，但存在一个严重的数据双写问题。

## Critical Issues 🔴

**1. 错题创建导致双倍掌握度扣减**
- **File**: `backend/app/services/error_book_service.py:350-361` + `backend/app/services/galaxy_service.py:183-248`
- **Expected**: 一道错题创建后，对应知识节点掌握度按 error_type 权重扣减一次（-2 至 -10）
- **Actual**: 掌握度被扣减两次——
  - **Path A**（同步）: `analyze_and_link()` 调用 `ErrorBookMasterySyncService.apply_error_diagnosis()`，按 `ERROR_TYPE_IMPACT` 权重扣减（-2 到 -10），并发布 `node_mastery_updated` 事件
  - **Path B**（异步 EventBus）: `analyze_and_link()` 发布 `ErrorCreated` 事件 → `GalaxyEventConsumer._handle_error_created()` → `ErrorReplanBridge.on_error_created()` → `_update_mastery_from_error()` → `GalaxyService.update_mastery_from_error()` 再次扣减（-3 到 -15）
- **Evidence**: `galaxy_event_consumer.py:83-84` 的注释明确说"节点掌握度更新已迁移到 ErrorBookMasterySyncService"，但 `error_replan_bridge.py:216-224` 仍然无条件调用 `_update_mastery_from_error()`
- **Impact**: 一道 knowledge_gap 错题会被扣减 -10（Path A）+ -8（Path B）= -18，远超设计意图。用户星图会异常变暗

## Major Issues 🟡

**2. 复习完成后 Galaxy 星图不刷新**
- **File**: `mobile/lib/features/error_book/data/providers/error_book_provider.dart:456-464`
- **Expected**: 用户完成错题复习后，Galaxy 星图颜色应立即反映掌握度变化
- **Actual**: `submitReview()` 后 invalidate 了 error/plan/task/stats 等 9 个 provider，但没有 invalidate 任何 Galaxy 相关 provider（`galaxyProvider`、`galaxyNodeStatusProvider` 等）
- **Evidence**: 已验证 invalidate 列表为 `errorDetailProvider`, `errorListProvider`, `todayReviewListProvider`, `errorStatsProvider`, `planListProvider`, `planDetailProvider`, `taskListProvider`, `systemUpdatesProvider`, `weeklyGrowthNarrativeProvider` — 无 Galaxy provider
- **Impact**: 用户复习错题后切到星图页看到的是旧数据，需手动离开再回来才能看到变化

**3. OCR 触发条件过于严格**
- **File**: `backend/app/services/error_book_service.py:266`
- **Expected**: 有图片的错题都应执行 OCR 提取文字
- **Actual**: 条件为 `error.question_image_url and (not error.question_text or len(error.question_text) < 10)`，即文字 ≥10 字符时 OCR 被完全跳过
- **Impact**: 用户输入 "请看图片"（刚好 5 字符 < 10 → OCR 会触发）但 "请看图片吧这道题"（8 字符 < 10 → 也会触发）而 "请查看照片上的题目"（9 字符 < 10 → 也会触发）。但 "请看照片中的这道数学题"（12 字符 ≥ 10 → OCR 不触发）。阈值 10 过于武断，导致部分有图片的错题不经过 OCR

## Minor Issues 🟢

**4. LLM 备用分析硬编码中文关键词**
- **File**: `backend/app/services/error_book_service.py:600-608`
- **Expected**: fallback 分析对不同语言/科目有合理分类
- **Actual**: `_build_fallback_analysis()` 仅检查中文字符如 "指针"、"计算"、"公式"。非中文科目（如英语错误）永远被分类为 "knowledge_gap"
- **Impact**: 低——仅影响 LLM 超时后的降级分析

## Working Well ✅

- **完整 API 生命周期**: `POST /errors` → 后台分析 → `GET /errors` 列表 → `POST /errors/{id}/review` → `GET /errors/stats`，全部端到端通畅（`backend/app/api/v1/error_book.py`）
- **SM-2 间隔重复**: 带抖动的 SM-2 算法，EF 有上下界保护（1.3-2.5），防止复习轰炸（`error_book_service.py:52-120`）
- **双重节点检索**: 向量搜索 + 关键词降级，确保冷启动也能匹配（`error_book_service.py:471-540`）
- **EventBus 集成**: `ErrorCreated` → `GalaxyEventConsumer` → 图演化 + 种子预热 + ErrorReplanBridge 完整触发（`galaxy_event_consumer.py:78-156`）
- **语义记忆集成**: `SemanticMemoryService.upsert_strategy_from_error()` 写入策略节点（`error_book_service.py:327-329`）
- **情景记忆写入**: 诊断阶段和复习结果都会写入 episodic memory（`error_book_service.py:337-339, 814-822`）
- **ErrorReplanBridge 专项修复**: 支持冲刺包聚类匹配和通用错误模式，创建通知+干预记录+修复任务（`error_replan_bridge.py:466-525`）
- **移动端 createError 后正确 invalidate**: 创建后刷新列表和统计（`error_book_provider.dart:338-339`）
- **Mastery sync 安全边界**: `_clamp_impact()` 限制单次最大 10 分扣减，`_clamp_mastery()` 限制 0-100 范围（`error_book_mastery_sync_service.py:547-555`）

## Files Examined
- `backend/app/services/error_book_service.py` (全文 910 行)
- `backend/app/services/error_replan_bridge.py` (全文 1906 行)
- `backend/app/services/error_book_mastery_sync_service.py` (全文 556 行)
- `backend/app/services/galaxy_event_consumer.py` (全文 381 行)
- `backend/app/services/galaxy_service.py:183-262`
- `backend/app/api/v1/error_book.py` (全文 210 行)
- `backend/app/core/event_bus.py` (Event class definitions)
- `mobile/lib/features/error_book/data/repositories/error_book_repository.dart` (全文 289 行)
- `mobile/lib/features/error_book/data/providers/error_book_provider.dart` (invalidate 列表)

## Confidence: High — 所有 finding 均通过直接读取源码验证，关键行号和代码行为已交叉确认
