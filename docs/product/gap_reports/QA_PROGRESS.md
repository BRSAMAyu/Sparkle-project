# QA Fix Progress Tracker

> Single source of truth for QA audit fixes. Updated: 2026-05-06
> 8 source reports in docs/product/gap_reports/QA_*.md

## Legend

| Symbol | Meaning |
|--------|---------|
| ⬜ pending | Not started |
| 🔵 in-progress | Claimed and being worked on |
| ✅ done | Committed and verified |
| 🚫 blocked | Blocked with reason |
| ⏭️ skip | Verified already fixed or not applicable |

## P0: Critical (6 items)

| ID | Title | Scope | Effort | Status | Claimed-By | Commit | Note |
|----|-------|-------|--------|--------|-----------|--------|------|
| QA-P0-1 | RetrievalDirective → RAG consume 参数传递 | Python | M | ✅ done | — | 9068ef3e | QA_P0_critical: graph_rag.py retrieve() 加 retrieval_directive 参数 |
| QA-P0-2 | RAG must_load/may_load/do_not_load 过滤 | Python | L | ✅ done | — | 88bfa07c | QA_P0_critical: 检索结果按 directive 列表过滤 |
| QA-P0-3 | pollution_guard strict 阈值执行 | Python | M | 🔵 in-progress | claude-B | — | QA_P0_critical: strict 模式下过滤低质量结果 |
| QA-P0-4 | token_budget 执行限制检索量 | Python | M | ⬜ pending | — | — | QA_P0_critical: 按 budget_tokens 截断检索结果 |
| QA-P0-5 | RetrievalDirective 集成测试 | Python | M | ⬜ pending | — | — | QA_P0_critical: 端到端测试 directive 过滤逻辑 |
| QA-P0-6 | L1 fast-path 跳过 LLM decision loop | Python | S | ⬜ pending | — | — | QA_P1_arch: orchestrator.py:568 should_escalate=False 时短路 |

## P1: High (20 items)

| ID | Title | Scope | Effort | Status | Claimed-By | Commit | Note |
|----|-------|-------|--------|--------|-----------|--------|------|
| QA-P1-1 | Hardcoded 'Your Data & Privacy' → ARB | Flutter | S | ⬜ pending | — | — | data_usage_dashboard_screen.dart |
| QA-P1-2 | Hardcoded 'Growth Plans' → ARB | Flutter | S | ⬜ pending | — | — | growth_screen.dart |
| QA-P1-3 | Hardcoded 'New Plan' → ARB | Flutter | S | ⬜ pending | — | — | growth_screen.dart |
| QA-P1-4 | Hardcoded 'Send Message' → ARB | Flutter | S | ⬜ pending | — | — | user_search_screen.dart |
| QA-P1-5 | Add route: LeaderboardScreen | Flutter | S | ⬜ pending | — | — | QA_NAV P0-1: 4 orphaned screens |
| QA-P1-6 | Add route: FocusStatisticsScreen | Flutter | S | ⬜ pending | — | — | QA_NAV P0-1 |
| QA-P1-7 | Add route: ThemeSettingsScreen | Flutter | S | ⬜ pending | — | — | QA_NAV P0-1 |
| QA-P1-8 | Add route: SchedulePreferencesScreen | Flutter | S | ⬜ pending | — | — | QA_NAV P0-1 |
| QA-P1-9 | Add route: SmartPushSettingsScreen | Flutter | S | ⬜ pending | — | — | QA_NAV P0-1 |
| QA-P1-10 | Add route: ProfileTransparentScreen | Flutter | S | ⬜ pending | — | — | QA_NAV P0-1 |
| QA-P1-11 | Add route: DataUsageDashboardScreen | Flutter | S | ⬜ pending | — | — | QA_NAV P0-1 |
| QA-P1-12 | Add route: CapsuleJobsScreen | Flutter | S | ⬜ pending | — | — | QA_NAV P0-1 |
| QA-P1-13 | SprintReviewScreen loading indicator | Flutter | S | ⬜ pending | — | — | Add skeleton shimmer |
| QA-P1-14 | PausedTaskBanner error handling | Flutter | M | ⬜ pending | — | — | Show error feedback on resume fail |
| QA-P1-15 | Integrate UnderstandingSnapshotCard | Flutter | M | ⬜ pending | — | — | Import into home dashboard |
| QA-P1-16 | Register AccountabilityHubScreen route | Flutter | S | ⬜ pending | — | — | community_routes.dart |
| QA-P1-17 | Persist SprintReviewScreen notes | Flutter | M | ⬜ pending | — | — | Wire save API |
| QA-P1-18 | Replace duplicate GoalValueChip | Flutter | S | ⬜ pending | — | — | Use shared widget in notifications |
| QA-P1-19 | Unit tests: per-channel delivery | Python | M | ⬜ pending | — | — | silent/in_app/push resolution |
| QA-P1-20 | Unit tests: fatigue + streak quality | Python | M | ⬜ pending | — | — | Fatigue penalty + Redis fallback |

## P2: Medium (35 items)

| ID | Title | Scope | Effort | Status | Claimed-By | Commit | Note |
|----|-------|-------|--------|--------|-----------|--------|------|
| QA-P2-1 | Semantics: UnderstandingSnapshotCard | Flutter | S | ⬜ pending | — | — | Add root Semantics wrapper |
| QA-P2-2 | Semantics: ContextReceiptBar | Flutter | S | ⬜ pending | — | — | Add Semantics label |
| QA-P2-3 | Semantics: SimilarGoalPursuersCard | Flutter | S | ⬜ pending | — | — | Add Semantics wrapper |
| QA-P2-4 | Semantics: GoalValueChip | Flutter | S | ⬜ pending | — | — | Add semanticLabel |
| QA-P2-5 | Semantics: TaskRestoreDialog | Flutter | S | ⬜ pending | — | — | Add semantic labels |
| QA-P2-6 | Semantics: SprintReviewScreen | Flutter | M | ⬜ pending | — | — | All interactive sections |
| QA-P2-7 | Semantics: GoalCreationWizardScreen | Flutter | M | ⬜ pending | — | — | Multi-step form |
| QA-P2-8 | Hardcoded 'Retry' → ARB | Flutter | S | ⬜ pending | — | — | strategy_migration_wizard.dart |
| QA-P2-9 | Hardcoded 'Translation Demo' → ARB | Flutter | S | ⬜ pending | — | — | translatable_text.dart |
| QA-P2-10 | _should_retract() enforcement logic | Python | M | ⬜ pending | — | — | Replace stub |
| QA-P2-11 | Build TaskRestoreDialog widget | Flutter | M | ⬜ pending | — | — | Extract to reusable widget |
| QA-P2-12 | Build CommunityStrategyCard widget | Flutter | L | ⬜ pending | — | — | New widget |
| QA-P2-13 | Build ExperienceEnvelopeIndicator | Flutter | L | ⬜ pending | — | — | New widget from provider |
| QA-P2-14 | Clean orphaned vocabulary providers | Flutter | S | ⬜ pending | — | — | Remove 4 unused |
| QA-P2-15 | Clean orphaned shop providers | Flutter | S | ⬜ pending | — | — | Remove 7 unused |
| QA-P2-16 | i18n → ARB: Insights feature (36 ternaries) | Flutter | L | ⬜ pending | — | — | insights/ inline isChinese |
| QA-P2-17 | i18n → ARB: User feature (11 ternaries) | Flutter | M | ⬜ pending | — | — | user/ inline isChinese |
| QA-P2-18 | i18n → ARB: Settings feature (15 ternaries) | Flutter | M | ⬜ pending | — | — | settings/ inline isChinese |
| QA-P2-19 | i18n → ARB: Home feature (10 ternaries) | Flutter | M | ⬜ pending | — | — | home/ inline isChinese |
| QA-P2-20 | i18n → ARB: Plan feature (8 ternaries) | Flutter | M | ⬜ pending | — | — | plan/ inline isChinese |
| QA-P2-21 | i18n → ARB: Goal feature (8 ternaries) | Flutter | M | ⬜ pending | — | — | goal/ inline isChinese |
| QA-P2-22 | i18n → ARB: Chat feature (8 ternaries) | Flutter | M | ⬜ pending | — | — | chat/ inline isChinese |
| QA-P2-23 | i18n → ARB: Cognitive feature (7 ternaries) | Flutter | S | ⬜ pending | — | — | cognitive/ inline isChinese |
| QA-P2-24 | i18n → ARB: Community feature (5 ternaries) | Flutter | S | ⬜ pending | — | — | community/ inline isChinese |
| QA-P2-25 | i18n → ARB: Memory feature (9 ternaries) | Flutter | M | ⬜ pending | — | — | memory/ inline isChinese |
| QA-P2-26 | i18n → ARB: Task feature (11 ternaries) | Flutter | M | ⬜ pending | — | — | task/ inline isChinese |
| QA-P2-27 | Migrate ~110 _t() usages to ARB | Flutter | L | ⬜ pending | — | — | ~15 files |
| QA-P2-28 | DS tokens: Achievement colors (12) | Flutter | M | ⬜ pending | — | — | milestone_celebration_screen.dart |
| QA-P2-29 | DS tokens: Home colors (7) | Flutter | M | ⬜ pending | — | — | background_layer.dart |
| QA-P2-30 | DS tokens: User colors (16) | Flutter | M | ⬜ pending | — | — | profile_screen.dart |
| QA-P2-31 | DS tokens: Plan colors (20) | Flutter | M | ⬜ pending | — | — | learning_portfolio_screen.dart |
| QA-P2-32 | DS tokens: BorderRadius (1,015 instances) | Flutter | L | ⬜ pending | — | — | → DS.borderRadius* |
| QA-P2-33 | DS tokens: EdgeInsets (1,359 instances) | Flutter | L | ⬜ pending | — | — | → DS.spacing* |
| QA-P2-34 | Semantics: IconButtons (31+ files) | Flutter | M | ⬜ pending | — | — | Add tooltip/semanticLabel |
| QA-P2-35 | Semantics: InkWell (30+ files) | Flutter | M | ⬜ pending | — | — | Wrap with Semantics |
| QA-P2-36 | Semantics: GestureDetector (30+ files) | Flutter | M | ⬜ pending | — | — | Wrap with Semantics |
| QA-P2-37 | Fix generic Semantics: CausalTimeline | Flutter | S | ⬜ pending | — | — | Replace 'control 1/2/3' |
| QA-P2-38 | Fix hardcoded toggle: GoalWorldGraph | Flutter | S | ⬜ pending | — | — | Toggle strings → ARB |
| QA-P2-39 | Semantics: notification chips | Flutter | S | ⬜ pending | — | — | Goal value + next step |
| QA-P2-40 | Hardcoded 'Decision Timeline' → ARB | Flutter | S | ⬜ pending | — | — | ChatScreen |
| QA-P2-41 | State handling: CommunityMainScreen | Flutter | M | ⬜ pending | — | — | loading/error/empty |
| QA-P2-42 | State handling: GroupListScreen | Flutter | M | ⬜ pending | — | — | loading/error/empty |
| QA-P2-43 | State handling: LearningInsightsOverview | Flutter | M | ⬜ pending | — | — | loading/error states |

## P3: Low (5 items)

| ID | Title | Scope | Effort | Status | Claimed-By | Commit | Note |
|----|-------|-------|--------|--------|-----------|--------|------|
| QA-P3-1 | Hardcoded 'A'/'B' strings → ARB | Flutter | S | ⬜ pending | — | — | memory unresolved_conflicts |
| QA-P3-2 | _a11yCopy helper → ARB | Flutter | M | ⬜ pending | — | — | accessibility settings |
| QA-P3-3 | Strategy effectiveness: SprintReview | Flutter | L | ⬜ pending | — | — | Per-strategy outcome display |
| QA-P3-4 | Tap target padding for undersized icons | Flutter | M | ⬜ pending | — | — | 48px hit area for 20-36px icons |
| QA-P3-5 | Audit fontSize for text scaling | Flutter | L | ⬜ pending | — | — | 719 fontSize overrides |

## Summary

| Priority | Total | ✅ done | ⬜ pending | 🔵 in-progress |
|----------|-------|---------|-----------|----------------|
| P0 | 6 | 2 | 4 | 0 |
| P1 | 20 | 0 | 20 | 0 |
| P2 | 35 | 0 | 35 | 0 |
| P3 | 5 | 0 | 5 | 0 |
| **Total** | **66** | **2** | **64** | **0** |
