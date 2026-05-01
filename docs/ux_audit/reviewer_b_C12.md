# Reviewer B — C12: 低完成率+临近截止→自适应压缩→计划页显示精简
Timestamp: 2026-04-26T01:05:00+08:00
Chain Index: 16 (Round 2 re-audit)

## Chain Flow Summary
后端 `AdaptiveReplanner.should_compress` 检查 `completion_rate < 0.5 && days_left <= 5`。满足时调用 `compress_sprint_day` → `build_compressed_sprint_day_spec` 生成 35 分钟保底任务（含 compression_reason、primary_target、minimum_output），写入计划。Mobile 端 `_compressionSummary` 检查 `guideJson['compressed']`、`dailySpec['compressed']`、`task_kind == 'compressed_recovery'` 或 `tag == 'adaptive_compressed'` 四种条件，检测到压缩任务后显示 `_AdaptiveCompressionBanner`（橙色背景+剪刀图标+精简提示文案）。

## Critical Issues 🔴
None found.

## Major Issues 🟡
None found.

## Minor Issues 🟢
None found.

## Working Well ✅
- **`backend/app/orchestration/adaptive_replanner.py:325-334`**: `should_compress` 逻辑清晰——50% 完成率 + 5 天截止，参数合理。
- **`adaptive_replanner.py:337-411`**: `build_compressed_sprint_day_spec` 生成完整的保底任务结构，含 method_steps、fail_safe_rule、compression_reason，有实际指导价值。
- **`mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart:1652-1680`**: `_compressionSummary` 四重检测逻辑覆盖所有可能的压缩标记来源。
- **`plan_detail_screen.dart:817-844`**: `_AdaptiveCompressionBanner` 视觉设计清晰——`DS.warning` 橙色 + 剪刀图标 + "已为你精简今日计划" 标题。
- **`adaptive_replanner.py:374-375`**: compression_reason 包含具体数字（完成率百分比、剩余天数），用户能理解为什么被压缩。

## Files Examined
- `backend/app/orchestration/adaptive_replanner.py` (lines 1-80, 325-435)
- `backend/app/orchestration/planning_workflow.py` (verified via grep for compress calls)
- `mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart` (lines 670-740, 815-844, 1652-1680)

## Confidence: High — 压缩触发逻辑和前端展示完整链路已确认。
