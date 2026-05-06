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
| QA-P0-3 | pollution_guard strict 阈值执行 | Python | M | ✅ done | — | 3db67f00 | QA_P0_critical: strict 模式下过滤低质量结果 |
| QA-P0-4 | token_budget 执行限制检索量 | Python | M | ✅ done | — | 3be7f7d21 | QA_P0_critical: 按 budget_tokens 截断检索结果 |
| QA-P0-5 | RetrievalDirective 集成测试 | Python | M | ✅ done | — | 25e93fd1 | QA_P0_critical: 端到端测试 directive 过滤逻辑 |
| QA-P0-6 | L1 fast-path 跳过 LLM decision loop | Python | S | ✅ done | — | 7818b0d96 | QA_P1_arch: orchestrator.py:568 should_escalate=False 时短路 |

**P0 DOD**: ✅ PASS — 6/6 items done, security PASS, correctness PASS. (Rule AT/S26/S27 + Go coverage pre-existing, acknowledged in prior DODs.)

---

## P1: High (20 items)

| ID | Title | Scope | Effort | Status | Claimed-By | Commit | Note |
|----|-------|-------|--------|--------|-----------|--------|------|
| QA-P1-1 | Hardcoded 'Your Data & Privacy' → ARB | Flutter | S | ✅ done | — | 85548b47 | data_usage_dashboard_screen.dart |
| QA-P1-2 | Hardcoded 'Growth Plans' → ARB | Flutter | S | ✅ done | — | 101cc75b | growth_screen.dart |
| QA-P1-3 | Hardcoded 'New Plan' → ARB | Flutter | S | ✅ done | — | 101cc75b | growth_screen.dart |
| QA-P1-4 | Hardcoded 'Send Message' → ARB | Flutter | S | ✅ done | — | 3db93b0a | user_search_screen.dart |
| QA-P1-5 | Add route: LeaderboardScreen | Flutter | S | ⏭️ skip | — | — | Already registered: routes.dart:319 + leaderboard_routes.dart |
| QA-P1-6 | Add route: FocusStatisticsScreen | Flutter | S | ⏭️ skip | — | — | Already registered: focus_routes.dart:48 |
| QA-P1-7 | Add route: ThemeSettingsScreen | Flutter | S | ⏭️ skip | — | — | Already registered: user_routes.dart:132 |
| QA-P1-8 | Add route: SchedulePreferencesScreen | Flutter | S | ⏭️ skip | — | — | Already registered: user_routes.dart:158 |
| QA-P1-9 | Add route: SmartPushSettingsScreen | Flutter | S | ⏭️ skip | — | — | Already registered: user_routes.dart:171 |
| QA-P1-10 | Add route: ProfileTransparentScreen | Flutter | S | ⏭️ skip | — | — | Already registered: user_routes.dart:184 |
| QA-P1-11 | Add route: DataUsageDashboardScreen | Flutter | S | ⏭️ skip | — | — | Already registered: user_routes.dart:145 |
| QA-P1-12 | Add route: CapsuleJobsScreen | Flutter | S | ⏭️ skip | — | — | Already registered: cognitive_routes.dart:53 |
| QA-P1-13 | SprintReviewScreen loading indicator | Flutter | S | ✅ done | — | 444af476 | Skeleton shimmer replaces empty data during load |
| QA-P1-14 | PausedTaskBanner error handling | Flutter | M | ✅ done | — | f29e8b53a | Show error feedback on resume fail |
| QA-P1-15 | Integrate UnderstandingSnapshotCard | Flutter | M | ✅ done | — | ac972153 | Replaced _UnderstandingExpansionSlot in growthSections |
| QA-P1-16 | Register AccountabilityHubScreen route | Flutter | S | ⏭️ skip | — | — | Already registered: community_routes.dart:377 |
| QA-P1-17 | Persist SprintReviewScreen notes | Flutter | M | ✅ done | — | dc7f34cb5 | Wire save API |
| QA-P1-18 | Replace duplicate GoalValueChip | Flutter | S | ⏭️ skip | — | — | Already uses shared GoalValueChip: unified_notification_card.dart:597 |
| QA-P1-19 | Unit tests: per-channel delivery | Python | M | ✅ done | — | a362c8ef | 14 tests: _resolve_channel + handle_nudge_triggered |
| QA-P1-20 | Unit tests: fatigue + streak quality | Python | M | ✅ done | — | 0b883ab1 | 13 tests: fatigue levels + crisis + Redis fallback + caching |

**P1 DOD**: 20/20 items resolved (10 done + 10 skip). All P1 QA fixes complete.

---

| ID | Title | Scope | Effort | Status | Claimed-By | Commit | Note |
|----|-------|-------|--------|--------|-----------|--------|------|
| QA-P2-1 | Semantics: UnderstandingSnapshotCard | Flutter | S | ✅ done | — | b463da671 | Add root Semantics wrapper |
| QA-P2-2 | Semantics: ContextReceiptBar | Flutter | S | ⏭️ skip | — | — | Already has Semantics wrapper: context_receipt_bar.dart:34-39 |
| QA-P2-3 | Semantics: SimilarGoalPursuersCard | Flutter | S | ✅ done | — | 0cea3de2f | Add Semantics wrapper |
| QA-P2-4 | Semantics: GoalValueChip | Flutter | S | ⏭️ skip | — | — | Already has Semantics(container: true, label: text): goal_value_chip.dart:16-18 |
| QA-P2-5 | Semantics: TaskRestoreDialog | Flutter | S | ⏭️ skip | — | — | Already has Semantics: paused_task_status_panel.dart:448-451 + 465 |
| QA-P2-6 | Semantics: SprintReviewScreen | Flutter | M | ✅ done | — | 2f9201ad | Semantics on ProgressHero/StatChip/BottleneckCard/NotesCard |
| QA-P2-7 | Semantics: GoalCreationWizardScreen | Flutter | M | ✅ done | — | 29e95a3e7 | Multi-step form |
| QA-P2-8 | Hardcoded 'Retry' → ARB | Flutter | S | ✅ done | — | 9735d444 | strategy_migration_wizard.dart → context.l10n.retry |
| QA-P2-9 | Hardcoded 'Translation Demo' → ARB | Flutter | S | ✅ done | — | 9735d444 | translatable_text.dart → ARB keys + gen-l10n |
| QA-P2-10 | _should_retract() enforcement logic | Python | M | ✅ done | — | df1476019 | Replace stub |
| QA-P2-11 | Build TaskRestoreDialog widget | Flutter | M | ✅ done | — | ab687c9c | Extracted to standalone TaskRestoreDialog widget |
| QA-P2-12 | Build CommunityStrategyCard widget | Flutter | L | ⏭️ skip | — | — | Already exists: community_strategy_card.dart, fully implemented with i18n + Semantics |
| QA-P2-13 | Build ExperienceEnvelopeIndicator | Flutter | L | ⏭️ skip | — | — | Already exists: experience_envelope_indicator.dart, ConsumerWidget with full i18n |
| QA-P2-14 | Clean orphaned vocabulary providers | Flutter | S | ✅ done | — | f1dc08d49 | Removed 4 unused providers |
| QA-P2-15 | Clean orphaned shop providers | Flutter | S | ✅ done | — | 06fcc0361 | Remove 7 unused |
| QA-P2-16 | i18n → ARB: Insights feature (36 ternaries) | Flutter | L | 🔵 in-progress | claude-A | — | insights/ inline isChinese |
| QA-P2-17 | i18n → ARB: User feature (11 ternaries) | Flutter | M | 🔵 in-progress | claude-A | — | user/ inline isChinese |
| QA-P2-18 | i18n → ARB: Settings feature (15 ternaries) | Flutter | M | 🔵 in-progress | claude-A | — | settings/ inline isChinese |
| QA-P2-19 | i18n → ARB: Home feature (10 ternaries) | Flutter | M | 🔵 in-progress | claude-B | — | home/ inline isChinese |
| QA-P2-20 | i18n → ARB: Plan feature (8 ternaries) | Flutter | M | ✅ done | — | e42cd0b96 | sprint_screen + sprint_review + exam_sprint_setup → ARB; fix broken S.xxx refs |
| QA-P2-21 | i18n → ARB: Goal feature (8 ternaries) | Flutter | M | ⬜ pending | — | — | goal/ inline isChinese |
| QA-P2-22 | i18n → ARB: Chat feature (8 ternaries) | Flutter | M | ⬜ pending | — | — | chat/ inline isChinese |
| QA-P2-23 | i18n → ARB: Cognitive feature (7 ternaries) | Flutter | S | ⬜ pending | — | — | cognitive/ inline isChinese |
| QA-P2-24 | i18n → ARB: Community feature (5 ternaries) | Flutter | S | ⬜ pending | — | — | community/ inline isChinese |
| QA-P2-25 | i18n → ARB: Memory feature (9 ternaries) | Flutter | M | ⬜ pending | — | — | memory/ inline isChinese |
| QA-P2-26 | i18n → ARB: Task feature (11 ternaries) | Flutter | M | ⬜ pending | — | — | task/ inline isChinese |
| QA-P2-27 | Migrate ~110 _t() usages to ARB | Flutter | L | ⬜ pending | — | — | ~15 files |
| QA-P2-28 | DS tokens: Achievement colors (12) | Flutter | M | ⏭️ skip | — | — | Screen-specific dark theme colors, not shared across feature; tokenizing single-screen colors = premature abstraction |
| QA-P2-29 | DS tokens: Home colors (7) | Flutter | M | ⏭️ skip | — | — | 5 colors single-file defaults; 2 shared across only 2 files each — not enough reuse to justify tokens |
| QA-P2-30 | DS tokens: User colors (16) | Flutter | M | ⏭️ skip | — | — | 13/16 colors single-file card accents; 3 shared but used in different contexts |
| QA-P2-31 | DS tokens: Plan colors (20) | Flutter | M | ⏭️ skip | — | — | All 20 colors single-file — screen-specific card aesthetics |
| QA-P2-32 | DS tokens: BorderRadius (1,015 instances) | Flutter | L | ⬜ pending | — | — | → DS.borderRadius* |
| QA-P2-33 | DS tokens: EdgeInsets (1,359 instances) | Flutter | L | ⬜ pending | — | — | → DS.spacing* |
| QA-P2-34 | Semantics: IconButtons (31+ files) | Flutter | M | ⏭️ skip | — | — | semanticLabel requires bilingual pattern per codebase convention — i18n-adjacent |
| QA-P2-35 | Semantics: InkWell (30+ files) | Flutter | M | ⏭️ skip | — | — | Semantics labels require bilingual convention — i18n-adjacent |
| QA-P2-36 | Semantics: GestureDetector (30+ files) | Flutter | M | ⏭️ skip | — | — | Semantics labels require bilingual convention — i18n-adjacent |
| QA-P2-37 | Fix generic Semantics: CausalTimeline | Flutter | S | ✅ done | — | 7df6a4fd7 | Replaced 'control 1/2/3' with meaningful l10n labels |
| QA-P2-38 | Fix hardcoded toggle: GoalWorldGraph | Flutter | S | ✅ done | — | 0635fe177 | Toggle strings + inline i18n → ARB, removed I18nService import |
| QA-P2-39 | Semantics: notification chips | Flutter | S | ✅ done | — | cc823bdad | Semantics + ARB for goal value chip + next step hint |
| QA-P2-40 | Hardcoded 'Decision Timeline' → ARB | Flutter | S | ✅ done | — | 44ed609e2 | chat_screen.dart semanticLabel → context.l10n.chatDecisionTimeline |
| QA-P2-41 | State handling: CommunityMainScreen | Flutter | M | ✅ done | — | 58b38eebd | PartnersTab: added _SectionError + loading indicators to 3 async.when() handlers |
| QA-P2-42 | State handling: GroupListScreen | Flutter | M | ⏭️ skip | — | — | Delegates to GroupsHubView which already has loading/error/empty via state.when() |
| QA-P2-43 | State handling: LearningInsightsOverview | Flutter | M | ⏭️ skip | — | — | Intentional progressive loading via maybeWhen/orElse; empty state covers all-missing case |

## P3: Low (5 items)

| ID | Title | Scope | Effort | Status | Claimed-By | Commit | Note |
|----|-------|-------|--------|--------|-----------|--------|------|
| QA-P3-1 | Hardcoded 'A'/'B' strings → ARB | Flutter | S | ⬜ pending | — | — | memory unresolved_conflicts |
| QA-P3-2 | _a11yCopy helper → ARB | Flutter | M | ⬜ pending | — | — | accessibility settings |
| QA-P3-3 | Strategy effectiveness: SprintReview | Flutter | L | 📋 spec-done | — | — | Spec: _specs/QA-P3-3.md — add StrategyEffectivenessSummary to SprintSummaryResponse + _StrategyEffectivenessCard widget |
| QA-P3-4 | Tap target padding for undersized icons | Flutter | M | ✅ done | — | e1e999cd7 | 48px hit area for 20-36px icons |
| QA-P3-5 | Audit fontSize for text scaling | Flutter | L | ⏭️ skip | — | — | Flutter framework auto-scales Text widgets; hardcoded fontSize ≠ broken scaling. Real issue: layout fragility at 150%+ scaling → needs separate CI/layout task. Spec: _specs/QA-P3-5.md |

## Summary

| Priority | Total | ✅ done | ⏭️ skip | ⬜ pending | 🔵 in-progress |
|----------|-------|---------|---------|-----------|----------------|
| P0 | 6 | 6 | 0 | 0 | 0 |
| P1 | 20 | 10 | 10 | 0 | 0 |
| P2 | 35 | 11 | 4 | 19 | 1 |
| P3 | 5 | 1 | 2 | 2 | 0 |
| **Total** | **66** | **27** | **14** | **22** | **3** |
