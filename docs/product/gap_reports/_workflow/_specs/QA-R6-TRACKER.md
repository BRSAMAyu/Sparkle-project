# QA Round 6 Tracker

> **Date**: 2026-05-06 | **Report**: QA_ROUND6_2026-05-06.md
> **Status**: COMPLETE (P0+P1 done, P2 deferred)

## P0 — 用户点击没反应 / 空状态困惑（立即修）

| # | UX 问题 | 文件 | 状态 | Commit |
|---|---------|------|------|--------|
| P0-1 | Modify Criteria 按钮是 no-op → 隐藏 | minimum_criteria_card.dart | ✅ done | 6fcd549f9 |
| P0-2 | 首次使用看到空卡片森林 → onboarding | dashboard_screen.dart | ✅ done | 7b1c3b116 |
| P0-3 | 目标创建后没有庆祝 → dialog | goal_creation_wizard_screen.dart, goal_created_dialog.dart | ✅ done | 01f4aca1f |

## P1 — 用户感知但可以理解（本周修）

| # | UX 问题 | 文件 | 状态 | Commit |
|---|---------|------|------|--------|
| P1-1 | Dashboard 信息层级倒置 → 调整 slot order | dashboard_slot_config_provider.dart | ✅ done | 326b4684c |
| P1-2 | 成就解锁缺乏情感冲击 → dialog | achievement_unlocked_dialog.dart | ✅ done | 360d0e5e7 |
| P1-3 | Scenario pack "backbone" 未解释 → Tooltip | journey_progress_card.dart | ✅ done | 83e5f84dd |
| P1-4 | 连胜数据缺乏总结 → insight banner | streak_details_screen.dart | ✅ done | 83e5f84dd |

## P2 — 值得做但需要更多设计

| # | UX 问题 | 状态 |
|---|---------|------|
| P2-1 | Chat 输入区垂直拥挤 → 折叠 pills | ⏳ deferred |
| P2-2 | GoalDetail 不展示 milestone 时间线 | ⏳ deferred |
| P2-3 | GrowthChronicle 可发现性差 → Dashboard 入口 | ⏳ deferred |
| P2-4 | Chat Semantics（先 widget 提取，再标注） | ⏳ deferred |

## Deferred/WONTFIX

- ExperienceEnvelope 字段 → WONTFIX (未展示字段是内部元数据)
- 114-file batch skeleton → 缩小到定向 6 个屏幕
- P1-2 full integration (provider-level newlyUnlocked tracking) → deferred to next round
