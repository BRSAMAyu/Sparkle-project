# QA Round 4 Tracker

> **Date**: 2026-05-06 | **Report**: QA_ROUND4_2026-05-06.md
> **Status**: IN PROGRESS

## P0 — 必修 (用户可感知)

| # | 问题 | 文件 | 状态 | Commit |
|---|------|------|------|--------|
| P0-1 | SharePrivacySettings TextEditingController 内存泄漏 | share_privacy_settings.dart | ✅ done | a5e30f024 |
| P0-2 | ThoughtCapsuleDialog TextEditingController 内存泄漏 | thought_capsule_dialog.dart | ✅ done | a5e30f024 |
| P0-3 | Chat screen 9 个 inline zh/en → ARB | chat_screen.dart | ✅ done | a5e30f024 |
| P0-4 | ExperienceEnvelopeIndicator inline i18n → ARB | experience_envelope_indicator.dart | ✅ done | a5e30f024 |

## P1 — 应修 (影响体验)

| # | 问题 | 工期 | 状态 | Commit |
|---|------|------|------|--------|
| P1-1 | 5 个核心屏幕 loading state 升级为 skeleton | M-L | ✅ done (4/5) | 38dc20e90 |
| P1-2 | Task Detail + Chat Semantics 覆盖 | L | ✅ done (Task Detail added, Chat deferred) | b61fd2e28 |
| P1-3 | Reduce motion 接入 Chat/Dashboard 动画 | M | ✅ done (2 anims, Dashboard has 0) | e702c7330 |
| P1-4 | 8 处 mounted 检查缺失 | S | ✅ done (5 real, 3 FP) | 2cd2213da |
| P1-5 | Dashboard SparkleIconButton 7 处 <48px tap target | S | ✅ done (3 real, not 7) | 2cd2213da |

## P2 — 改进

| # | 问题 | 工期 | 状态 | Commit |
|---|------|------|------|--------|
| P2-1 | ExperienceEnvelope 展示 userState/profileContext | M | ⏳ pending | — |
| P2-2 | Achievement 展示 narrative/contextStory | M | ⏳ pending | — |
| P2-3 | Galaxy 展示 exam_weight/difficulty/trainability | M | ⏳ pending | — |
| P2-4 | StreakQuality 展示 recoveryScore + suggestedMessage | S | ✅ done | 5235e8094 |
| P2-5 | 33 个 bare spinner 屏幕 → skeleton (批量) | L | ✅ done (32 screens) | 238c348c3 |

## Notes

- O2 agent PlanModel "13/21 未渲染" 结论不准确，亲自 grep 纠正为仅 isPrimary 未使用
- 所有修复需 self-review → Opus audit → commit → tracker update
