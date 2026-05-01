# Reviewer B — D02: 错题修复→Galaxy掌握度闭环——修了错题星图真的变亮吗
Timestamp: 2026-04-26T01:15:00+08:00
Chain Index: 17 (Round 3 — D-chain audit)

## Chain Flow Summary
用户在错题本复习一道错题，选择 remembered/fuzzy/forgot。`ErrorBookService.submit_review` 调用 `ErrorBookMasterySyncService.apply_review_feedback`，后者对关联的知识节点执行 mastery delta（+4/+1/-2，0-100 刻度），直接写入 `UserNodeStatus.mastery_score`，并返回 `_pending_event`。`submit_review` commit 后调用 `_flush_pending_mastery_events` 将事件发布到 Redis Stream `sparkle_events`。`GalaxyEventConsumer._handle_mastery_updated` 处理该事件触发图演化。但 mobile 端 galaxy_provider 需要 `galaxy.node.updated` 或 `galaxy.mastery_updated` WebSocket 事件才能实时更新星图。

## Critical Issues 🔴
**`backend/app/services/error_book_mastery_sync_service.py:243-246`**: `apply_review_feedback` 直接修改 `UserNodeStatus.mastery_score`，绕过了 `GalaxyService.update_node_mastery`（后者有 Outbox 写入、审计日志、WebSocket 推送）。Expected: 用户复习错题后，Galaxy 星图实时更新（节点颜色变亮）。Actual: mastery 更新写入 DB，但不会通过 Outbox 推送到 mobile。用户需要重新打开 Galaxy 页面才能看到变化（因为 galaxy_provider 重新加载时会从 API 拉取最新数据）。Redis Stream 事件只触发后端图演化，不触发前端 WebSocket 推送。Evidence: `error_book_mastery_sync_service.py:246` 直接写 `status.mastery_score = new_mastery`，对比 `galaxy_service.py:1667-1677` 的 Outbox 写入路径。

## Major Issues 🟡
**`backend/app/services/error_book_mastery_sync_service.py:170-172`**: 如果用户记录错题时 `linked_knowledge_node_ids` 为空（没关联知识节点），`apply_review_feedback` 直接返回空列表，mastery 不会更新。Expected: 即便没有关联节点，复习错题也应该通过 error_replan_bridge 等机制产生可见效果。Actual: 无节点关联时复习不产生任何 mastery 变化，但前端不提示用户关联节点。

**`mobile/lib/features/error_book/data/providers/error_book_provider.dart:454-464`**: `submitReview` 成功后 invalidate 了多个 provider（error、plan、task、weekly），但没有 invalidate `galaxyProvider` 或递增 `galaxyRefreshTriggerProvider`。Expected: 复习错题后 Galaxy 页面刷新。Actual: 即使后端 mastery 已更新，Galaxy 页面不会自动刷新（除非用户重新进入页面触发加载）。

## Minor Issues 🟢
None found.

## Working Well ✅
- **`backend/app/services/error_book_mastery_sync_service.py:36-49`**: REVIEW_PERFORMANCE_IMPACT 映射合理：remembered→+4, fuzzy→+1, forgot→-2。`_clamp_mastery` 确保值在 0-100 范围内。
- **`error_book_mastery_sync_service.py:179`**: 限制最多更新 3 个节点，防止一个错题关联过多节点导致过大变化。
- **`error_book_mastery_sync_service.py:250-254`**: 正确更新了 `bkt_mastery_prob`（0-100→0.0-1.0）、`study_count`、`next_review_at`。
- **`backend/app/services/error_book_service.py:132-143`**: `_flush_pending_mastery_events` 在 DB commit 后发布事件，确保数据一致性。
- **`error_book_mastery_sync_service.py:260-269`**: 创建 `StudyRecord` 记录每次 mastery 变化，有完整的审计追踪。

## Files Examined
- `backend/app/services/error_book_service.py` (lines 132-143, 787-839)
- `backend/app/services/error_book_mastery_sync_service.py` (lines 36-49, 153-291)
- `backend/app/services/galaxy_service.py` (lines 75-110, 165-178, 1660-1689)
- `backend/app/services/galaxy_event_consumer.py` (lines 66-74, 282-289)
- `mobile/lib/features/error_book/data/providers/error_book_provider.dart` (lines 439-467)
- `mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart` (lines 441-443, 477-526)

## Confidence: High — mastery 更新路径和 WebSocket 推送缺失已通过代码对比确认。
