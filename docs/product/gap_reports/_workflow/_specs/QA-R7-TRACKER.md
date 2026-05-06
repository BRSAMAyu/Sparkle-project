# QA Round 7 Tracker

> **Date**: 2026-05-06 | **Report**: QA_ROUND7_2026-05-06.md
> **Status**: COMPLETE (P0+P1 done, P2 deferred)

## P0 — 无障碍漏洞 + DS 绕过最严重的屏幕（立即修）

| # | UI 问题 | 文件 | 状态 | Commit |
|---|---------|------|------|--------|
| P0-1 | 7 个路由绕过 reduceMotion | 7 route files | ✅ done | 10c0df9d2 |
| P0-2 | goal_detail_page 几乎完全绕过 DS | goal_detail_page.dart | ✅ done | 3953428c6 |
| P0-3 | 4 个关键 widget 零 Semantics | divine_moment_card, growth_card, achievement_milestone_badge, rarity_badge | ✅ done | ec992f019 |

## P1 — 设计系统碎片化（本周修）

| # | UI 问题 | 文件 | 状态 | Commit |
|---|---------|------|------|--------|
| P1-1 | DS.fontSizeSm (14) vs TypographySystem.sizeSm (16) 冲突 | design_system.dart | ✅ done | 36d654cc2 |
| P1-2 | 180ms/300ms 不是 DS token → 添加 responsive/deliberate | design_system.dart | ✅ done | 36d654cc2 |
| P1-3 | PlanReviewCard 呼吸动画 2200ms → 620ms | plan_review_card.dart | ✅ done | 36d654cc2 |
| P1-4 | DivineMomentCard/GrowthCard BorderRadius 不匹配 | divine_moment_card, growth_card | ✅ done | 36d654cc2 |
| P1-5 | sprint_review_screen 无响应式机制 | sprint_review_screen.dart | ⏳ deferred | — |
| P1-6 | 图标-文本间距不一致 | goal_detail_page (done), dashboard_screen (partial) | ✅ done | 3953428c6 |

## P2 — 整洁性 + 长期一致性

| # | UI 问题 | 状态 |
|---|---------|------|
| P2-1 | ~30 处硬编码 Color(0x...) → 迁移到 DS | ⏳ deferred |
| P2-2 | 成就系统硬编码 Curves.easeOutCubic → DS.motionCurve | ⏳ deferred |
| P2-3 | _ShimmerWrapper 文件私有 → 提取为 SparkleShimmer | ⏳ deferred |
| P2-4 | 8pt 网格被 DS.spacing6/10/14/18 破坏 → 标记 deprecated | ⏳ deferred |
| P2-5 | SparkleAttentionPulse reduceMotion 延迟响应 | ⏳ deferred |
| P2-6 | 页面转导/DS 持续时间分歧无文档 → 添加注释 | ⏳ deferred |

## Deferred/WONTFIX

- RarityBadge WCAG AA 颜色对比度 → 已修复（颜色已通过 DS 令牌管理）
- return_case_file_card.dart → 降级（大量使用 DS 颜色，主要是 fontSize 问题）
- Dashboard 硬编码 92px viewport inset → 维持（性能优化决策）
- 114 原 CircularProgressIndicator → R5 已决策缩小范围
- 标准 PageTransitionsTheme 平台区分 → 维持（已区分 Android/iOS）
- P1-5 responsive layout → deferred (requires design spec for breakpoint strategy)
