# Reviewer B — D08: 社区→个人AI体验——伙伴活动影响教练吗
Timestamp: 2026-04-26T01:30:00+08:00
Chain Index: 20 (Round 3 — D-chain audit)

## Chain Flow Summary
用户的学习伙伴完成任务/打卡时，`CommunityService._record_community_signal()` 写入 Redis，`CommunitySignalCollector` 聚合到用户偏好。`ContextManager._get_social_context_v1` 调用 `SocialSignalBridge.build_social_signals_v1` 生成 `SocialSignalsV1`（含 mention_count、relationship_count、pending_commitments_count 等）。`prompts.py:3276` 检查 `stage33_social_mode`，仅在 `"live"` 时渲染【社群信号 [L2 引导]】section。但 `settings.py:320` 默认值为 `"shadow"`，导致社交信号被计算但不注入 prompt。Dashboard 不读取社交信号（零匹配确认）。Mobile 端 `accountability_screen.dart` 展示伙伴打卡/连续天数，但为纯展示，不影响 AI 个性化。

## Critical Issues 🔴
None found.

## Major Issues 🟡
**`backend/app/config/settings.py:320` + `backend/app/orchestration/prompts.py:3276`**: `AURORA_STAGE33_SOCIAL_MODE` 默认 `"shadow"`，社交信号被计算但不注入 Aurora prompt。`prompts.py:3276` 仅在 `stage33_social_mode == "live"` 时渲染社群信号 section。Expected: 学习伙伴的活跃度（打卡、复习完成）影响我的 AI 教练的建议和行为。Actual: 伙伴数据在 `SocialSignalBridge` 中被正确计算，在 `context_manager` 中被正确收集，但最终因 kill switch 处于 shadow 模式而不进入 prompt。Aurora 完全不知道用户有活跃的学习伙伴。Evidence: `settings.py:320` → `prompts.py:3276` (`if stage33_social_mode == "live"`)。

**`backend/app/aurora/runtime_v1/dashboard.py`**: Dashboard 零社交信号引用。`SocialSignalBridge` 产生的 `SocialSignalsV1` 不影响 wake tokens、routing hints 或任何 dashboard 决策。即使 kill switch 切到 "live"，dashboard 层面的 AI 个性化也不会包含社交维度。

## Minor Issues 🟢
None found.

## Working Well ✅
- **`backend/app/services/social_signal_bridge.py:74-118`**: `build_social_signals_v1` 正确聚合多维度社交数据——mention_count、relationship_count、pending_commitments_count、community_engagement_level，数据模型完善。
- **`backend/app/core/context_manager.py:295-302`**: `_get_social_context_v1` 正确调用 bridge 并返回结果，集成路径通畅（只等 kill switch 切到 live）。
- **`backend/app/orchestration/prompts.py:2727-2750`**: `_format_stage33_social_signal_section` 渲染逻辑完善——包含边界感提示（line 2749: "不代表必须把学习社交化"），符合 Rule Z 隐私治理。
- **`mobile/lib/features/community/presentation/screens/accountability_screen.dart:312-366`**: 伙伴打卡和连续天数展示完整，UI 功能正常。
- **`backend/app/services/community_service.py`**: `_record_community_signal` 正确记录多种交互类型（join/post/comment/like/dm）。

## Files Examined
- `backend/app/services/social_signal_bridge.py` (lines 74-118, 182, 199)
- `backend/app/services/community_service.py` (lines 50-65, 778-783)
- `backend/app/core/context_manager.py` (lines 64-68, 184, 196, 295-302)
- `backend/app/orchestration/prompts.py` (lines 2657, 2666, 2727-2750, 3275-3280)
- `backend/app/aurora/runtime_v1/dashboard.py` (grep — zero social/partner/community/accountability references)
- `backend/app/config/settings.py` (line 320 — default "shadow")
- `mobile/lib/features/community/presentation/screens/accountability_screen.dart` (lines 18-84, 312-366)

## Confidence: High — shadow 模式默认值和 dashboard 零引用已通过 grep 确认。整条链路从计算到展示通畅，但最终 injection 被 kill switch 阻断。
