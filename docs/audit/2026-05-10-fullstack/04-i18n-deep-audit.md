# i18n Deep Audit Report

**Date**: 2026-05-10
**Scope**: Full-stack i18n compliance across Flutter mobile layer
**Status**: CRITICAL -- 988 violations across 204 files

---

## Executive Summary

The i18n system has a properly maintained ARB infrastructure (9,400 keys, EN/ZH parity is perfect) but suffers from massive non-compliance in the presentation layer. The `isChinese ? 'zh' : 'en'` anti-pattern bypasses the ARB system entirely in 988 locations across 204 files. An additional 82 `_t()` helper calls and hardcoded Chinese fallbacks in error widgets compound the problem.

---

## 1. ARB Key Parity (PASS)

| Metric | Count |
|--------|-------|
| EN keys (`app_en.arb`) | 9,400 |
| ZH keys (`app_zh.arb`) | 9,400 |
| EN-only keys | 0 |
| ZH-only keys | 0 |

**Result**: EN/ZH ARB files have perfect 1:1 key parity. No missing keys in either direction.

### 1.1 Parameter Mismatches (15 keys)

These keys exist in both EN and ZH but have different placeholder structures. Most are intentional (Chinese does not need plural forms for many quantities), but they may cause runtime issues depending on the ICU message parser:

| Key | EN Pattern | ZH Pattern | Severity |
|-----|-----------|------------|----------|
| `numberCount` | `{count, plural, =0{None} =1{1 item} other{{count} items}}` | `{count, plural, =0{无} =1{1项} other{{count}项}}` | Low |
| `streakDays` | `{count, plural, =1{1 day} other{{count} days}}` | `{count, plural, =1{1天} other{{count}天}}` | Low |
| `taskCount` | `{count, plural, =0{No tasks} =1{1 task} other{{count} tasks}}` | `{count, plural, =0{无任务} =1{1个任务} other{{count}个任务}}` | Low |
| `timeDaysAgo` | `{count, plural, =1{1 day ago} other{{count} days ago}}` | `{count}天前` | Medium |
| `timeHoursAgo` | `{count, plural, =1{1 hour ago} other{{count} hours ago}}` | `{count}小时前` | Medium |
| `timeInDays` | `In {count, plural, =1{1 day} other{{count} days}}` | `{count}天后` | Medium |
| `timeInHours` | `In {count, plural, =1{1 hour} other{{count} hours}}` | `{count}小时后` | Medium |
| `timeInMinutes` | `In {count, plural, =1{1 minute} other{{count} minutes}}` | `{count}分钟后` | Medium |
| `timeInMonths` | `In {count, plural, =1{1 month} other{{count} months}}` | `{count}个月后` | Medium |
| `timeInWeeks` | `In {count, plural, =1{1 week} other{{count} weeks}}` | `{count}周后` | Medium |
| `timeInYears` | `In {count, plural, =1{1 year} other{{count} years}}` | `{count}年后` | Medium |
| `timeMinutesAgo` | `{count, plural, =1{1 minute ago} other{{count} minutes ago}}` | `{count}分钟前` | Medium |
| `timeMonthsAgo` | `{count, plural, =1{1 month ago} other{{count} months ago}}` | `{count}个月前` | Medium |
| `timeWeeksAgo` | `{count, plural, =1{1 week ago} other{{count} weeks ago}}` | `{count}周前` | Medium |
| `timeYearsAgo` | `{count, plural, =1{1 year ago} other{{count} years ago}}` | `{count}年前` | Medium |

**Note**: The `timeXxxAgo` and `timeInXxx` mismatches are by design -- Chinese does not need plural forms. These are not bugs but should be verified to work with Flutter's ICU message parser.

---

## 2. `isChinese` Pattern Violations (CRITICAL)

### 2.1 Totals

| Pattern | Occurrences |
|---------|------------|
| `isChinese` references (total) | **988** |
| `isChinese ? '...' : '...'` ternaries | **473** |
| `zh ? '...' : '...'` ternaries | **690** |
| `_t('zh', 'en')` helper calls | **82** |
| Unique files affected | **204** |

### 2.2 Breakdown by Feature Area

| Area | isChinese Count | Files |
|------|----------------|-------|
| home | 227 | 35 |
| community | 219 | 28 |
| tools | 63 | 12 |
| calendar | 48 | 10 |
| memory | 40 | 6 |
| insights | 40 | 8 |
| error_book | 33 | 4 |
| core/services | 28 | 4 |
| task | 27 | 9 |
| user | 26 | 6 |
| reflection | 23 | 2 |
| auth | 23 | 5 |
| seed_library | 21 | 4 |
| statistics | 18 | 8 |
| mirofish | 18 | 2 |
| visual_elements | 13 | 4 |
| design | 12 | 8 |
| cognitive | 12 | 5 |
| theater | 11 | 3 |
| goal | 11 | 5 |
| achievement | 11 | 9 |
| notification_center | 9 | 3 |
| knowledge | 9 | 2 |
| galaxy | 7 | 2 |
| translation | 6 | 2 |
| focus | 6 | 3 |
| plan | 5 | 3 |
| experience | 5 | 3 |
| photon | 3 | 2 |
| chat | 3 | 2 |
| report | 2 | 2 |
| openclaw | 2 | 2 |

### 2.3 Top 30 Worst Offenders (by isChinese count)

| Count | File |
|-------|------|
| 32 | `features/memory/presentation/widgets/evidence_cards.dart` |
| 26 | `features/community/presentation/screens/create_group_screen.dart` |
| 26 | `core/services/universal_share_service.dart` |
| 25 | `features/home/presentation/widgets/exam_sprint_dashboard_card.dart` |
| 24 | `features/community/presentation/screens/group_tasks_screen.dart` |
| 23 | `features/reflection/presentation/screens/reflection_summary_screen.dart` |
| 23 | `features/error_book/presentation/screens/add_error_screen.dart` |
| 21 | `features/calendar/presentation/screens/calendar_stats_screen.dart` |
| 20 | `features/tools/presentation/widgets/breathing_tool.dart` |
| 18 | `features/user/data/repositories/user_repository.dart` |
| 18 | `features/mirofish/presentation/support/mirofish_milestone_service.dart` |
| 17 | `features/home/presentation/widgets/learning_heatmap_widget.dart` |
| 16 | `features/tools/presentation/widgets/vocabulary_lookup_tool.dart` |
| 16 | `features/insights/presentation/screens/learning_insights_overview_screen.dart` |
| 16 | `features/home/presentation/widgets/task_board/task_board_card.dart` |
| 16 | `features/home/presentation/widgets/openclaw_hub_card.dart` |
| 16 | `features/home/presentation/screens/dashboard_screen.dart` |
| 15 | `features/home/presentation/widgets/next_actions_card.dart` |
| 15 | `features/community/presentation/screens/accountability_screen.dart` |
| 14 | `features/community/presentation/screens/group_moderation_screen.dart` |
| 14 | `features/community/presentation/screens/favorites_screen.dart` |
| 13 | `features/home/presentation/widgets/predicted_intent_card.dart` |
| 13 | `features/home/presentation/providers/intent_prediction_provider.dart` |
| 13 | `features/community/presentation/widgets/similar_goal_pursuers_card.dart` |
| 12 | `features/community/presentation/widgets/shared_resource_card.dart` |
| 12 | `features/community/presentation/screens/group_members_screen.dart` |
| 12 | `features/community/presentation/screens/blocked_users_screen.dart` |
| 12 | `features/auth/data/repositories/auth_repository.dart` |
| 11 | `features/task/data/repositories/task_repository.dart` |
| 11 | `features/seed_library/presentation/marketplace/marketplace_screen.dart` |

### 2.4 Complete File Inventory

Below is the complete list of all 204 files with isChinese violations:

#### Core (39 occurrences, 12 files)

| Count | File |
|-------|------|
| 6 | `core/statistics/data/services/statistics_export_service_impl.dart` |
| 5 | `core/statistics/presentation/widgets/common/statistics_empty_state.dart` |
| 5 | `core/design/widgets/loading_indicator.dart` |
| 5 | `core/design/widgets/universal_share_bottom_sheet.dart` |
| 3 | `core/design/widgets/app_permission_dialog.dart` |
| 3 | `core/utils/formatters.dart` |
| 2 | `core/errors/failures.dart` |
| 2 | `core/services/sensory_feedback_service.dart` |
| 1 | `core/design/widgets/compact_error_card.dart` |
| 1 | `core/design/widgets/app_feedback.dart` |
| 1 | `core/statistics/domain/repositories/statistics_repository.dart` |
| 1 | `core/services/universal_share_service.dart` |

#### Home (227 occurrences, 35 files)

| Count | File |
|-------|------|
| 25 | `features/home/presentation/widgets/exam_sprint_dashboard_card.dart` |
| 17 | `features/home/presentation/widgets/learning_heatmap_widget.dart` |
| 16 | `features/home/presentation/screens/dashboard_screen.dart` |
| 16 | `features/home/presentation/widgets/openclaw_hub_card.dart` |
| 16 | `features/home/presentation/widgets/task_board/task_board_card.dart` |
| 15 | `features/home/presentation/widgets/next_actions_card.dart` |
| 13 | `features/home/presentation/providers/intent_prediction_provider.dart` |
| 13 | `features/home/presentation/widgets/predicted_intent_card.dart` |
| 11 | `features/home/presentation/widgets/task_board/sprint_view.dart` |
| 9 | `features/home/presentation/widgets/expanded_toolbar_section.dart` |
| 7 | `features/home/presentation/widgets/aurora_status_band.dart` |
| 6 | `features/home/presentation/widgets/calendar/task_preview_panel.dart` |
| 4 | `features/home/presentation/providers/home_growth_provider.dart` |
| 4 | `features/home/presentation/screens/notification_list_screen.dart` |
| 4 | `features/home/presentation/widgets/multi_goal_dashboard_card.dart` |
| 4 | `features/home/presentation/widgets/next_action_prompt.dart` |
| 4 | `features/home/presentation/widgets/seed_library_dashboard_card.dart` |
| 3 | `features/home/data/repositories/dashboard_repository.dart` |
| 3 | `features/home/presentation/providers/dashboard_provider.dart` |
| 3 | `features/home/presentation/widgets/today_growth_status_card.dart` |
| 3 | `features/home/presentation/widgets/long_term_plan_card.dart` |
| 3 | `features/home/presentation/widgets/dashboard_edit_sheet.dart` |
| 2 | `features/home/presentation/widgets/focus_card.dart` |
| 2 | `features/home/presentation/widgets/metrics_row.dart` |
| 2 | `features/home/presentation/widgets/sprint_card.dart` |
| 2 | `features/home/presentation/widgets/dashboard_curiosity_card.dart` |
| 2 | `features/home/presentation/widgets/compact_status_bar.dart` |
| 2 | `features/home/presentation/widgets/active_bottleneck_alert.dart` |
| 2 | `features/home/presentation/widgets/task_board/schedule_view.dart` |
| 2 | `features/home/presentation/widgets/task_board/priority_view.dart` |
| 1 | `features/home/data/repositories/notification_repository.dart` |
| 1 | `features/home/presentation/providers/spine_status_band_provider.dart` |
| 1 | `features/home/presentation/providers/exam_sprint_dashboard_provider.dart` |
| 1 | `features/home/presentation/widgets/collapsible_slot.dart` |
| 1 | `features/home/presentation/widgets/daily_context_line.dart` |
| 1 | `features/home/presentation/widgets/goal_switcher.dart` |
| 1 | `features/home/presentation/widgets/intent_prediction_bar.dart` |
| 1 | `features/home/presentation/widgets/multi_agent_bar.dart` |
| 1 | `features/home/presentation/widgets/prism_card.dart` |
| 1 | `features/home/presentation/widgets/recent_insights_card.dart` |
| 1 | `features/home/presentation/widgets/task_board/task_view_switcher.dart` |
| 1 | `features/home/presentation/widgets/task_board/plan_view.dart` |
| 1 | `features/home/presentation/widgets/calendar/compact_task_card.dart` |

#### Community (219 occurrences, 28 files)

| Count | File |
|-------|------|
| 26 | `features/community/presentation/screens/create_group_screen.dart` |
| 24 | `features/community/presentation/screens/group_tasks_screen.dart` |
| 15 | `features/community/presentation/screens/accountability_screen.dart` |
| 14 | `features/community/presentation/screens/group_moderation_screen.dart` |
| 14 | `features/community/presentation/screens/favorites_screen.dart` |
| 13 | `features/community/presentation/widgets/similar_goal_pursuers_card.dart` |
| 12 | `features/community/presentation/widgets/shared_resource_card.dart` |
| 12 | `features/community/presentation/screens/group_members_screen.dart` |
| 12 | `features/community/presentation/screens/blocked_users_screen.dart` |
| 9 | `features/community/data/repositories/accountability_repository.dart` |
| 8 | `features/community/presentation/widgets/wordbook_tool.dart` |
| 8 | `features/community/presentation/providers/community_agent_provider.dart` |
| 8 | `features/community/presentation/widgets/partners_tab.dart` |
| 7 | `features/community/data/repositories/mock_community_repository.dart` |
| 7 | `features/community/presentation/widgets/feed_tab_content.dart` |
| 6 | `features/community/presentation/screens/user_search_screen.dart` |
| 6 | `features/community/presentation/screens/group_search_screen.dart` |
| 5 | `features/community/presentation/widgets/group_recommendation_card.dart` |
| 4 | `features/community/presentation/screens/group_list_screen.dart` |
| 4 | `features/community/presentation/screens/create_post_screen.dart` |
| 3 | `features/community/presentation/widgets/group_chat_bubble.dart` |
| 3 | `features/community/presentation/widgets/achievement_badge.dart` |
| 2 | `features/community/presentation/widgets/community_strategy_card.dart` |
| 2 | `features/community/presentation/widgets/checkin_interaction.dart` |
| 2 | `features/community/presentation/screens/group_files_screen.dart` |
| 1 | `features/community/presentation/screens/community_main_screen.dart` |
| 1 | `features/community/presentation/providers/community_provider.dart` |
| 1 | `features/community/data/repositories/community_accountability_repository.dart` |
| 1 | `features/community/presentation/widgets/private_chat_bubble.dart` |
| 1 | `features/community/presentation/widgets/accountability_hub/partner_observation_settings.dart` |
| 1 | `features/community/presentation/widgets/accountability/partner_visibility_banner.dart` |
| 1 | `features/community/presentation/widgets/accountability/checkin_cadence_card.dart` |
| 1 | `features/community/presentation/widgets/share_cards/achievement_share_card.dart` |

#### Tools (63 occurrences, 12 files)

| Count | File |
|-------|------|
| 20 | `features/tools/presentation/widgets/breathing_tool.dart` |
| 16 | `features/tools/presentation/widgets/vocabulary_lookup_tool.dart` |
| 8 | `features/tools/presentation/widgets/wordbook_tool.dart` |
| 6 | `features/tools/presentation/widgets/translator_tool.dart` |
| 4 | `features/tools/presentation/widgets/notes_tool.dart` |
| 2 | `features/tools/presentation/widgets/tool_shell.dart` |
| 2 | `features/tools/presentation/widgets/speech_to_text_tool.dart` |
| 2 | `features/tools/presentation/widgets/calculator_tool.dart` |
| 2 | `features/tools/presentation/screens/tool_host_screen.dart` |
| 1 | `features/tools/presentation/widgets/focus_stats_tool.dart` |

#### Calendar (48 occurrences, 10 files)

| Count | File |
|-------|------|
| 21 | `features/calendar/presentation/screens/calendar_stats_screen.dart` |
| 7 | `features/calendar/presentation/screens/daily_detail_screen.dart` |
| 6 | `features/calendar/presentation/widgets/agent_stats_dashboard.dart` |
| 6 | `features/calendar/data/models/calendar_day_aggregate.dart` |
| 4 | `features/calendar/presentation/widgets/smart_schedule_chip.dart` |
| 2 | `features/calendar/data/services/smart_schedule_service.dart` |
| 2 | `features/calendar/data/repositories/calendar_repository.dart` |

#### Other Feature Areas

| Count | Area/File |
|-------|-----------|
| 40 | memory (evidence_cards 32, evidence_drawer 2, memory_evidence_badge 3, pending_commitments_section 2, unresolved_conflicts_section 1) |
| 40 | insights (learning_insights_overview_screen 16, learning_forecast_screen 10, directive_audit_screen 5, weekly_growth_narrative 5, weekly_growth_narrative_card 3, growth_dashboard 1) |
| 33 | error_book (add_error_screen 23, error_book_provider 8, error_book_repository 1, remediable_patterns_card 1) |
| 27 | task (execution_copy 4, task_execution_screen 3, task_provider 1, task_guidance_surface 1, paused_task_status_panel 1, source_lifecycle_badge 1, task_offline_indicator 1, task_protocol_panel 1, why_this_today_panel 1) |
| 26 | user (user_repository 18, ws6_profile_mirror_provider 2, edit_profile_screen 1, unified_settings_screen 2, learning_mode_control 1, working_memory_card 2) |
| 23 | reflection (reflection_summary_screen 23) |
| 23 | auth (auth_repository 12, legal_document_screen 4, reset_password_screen 4, register_screen 2, auth_provider 1) |
| 21 | seed_library (marketplace_screen 11, create_library_screen 6, seed_library_provider 1, seed_library_card 3) |
| 18 | mirofish (mirofish_milestone_service 18) |
| 13 | visual_elements (visual_element_preview_dialog 5, visual_recommendation_service 5, visual_element_card 2, visual_element_repository 1) |
| 12 | cognitive (strategy_migration_wizard 5, capsule_detail_screen 2, curiosity_capsule_screen 2, pattern_list_screen 1, mock_cognitive_repository 2) |
| 11 | theater (theater_provider 10, theater_repository 1) |
| 11 | goal (goal_creation_wizard_screen 8, goal_created_dialog 1, goal_intent_input 1, journey_progress_card 1) |
| 11 | achievement (achievement_map_screen 1, achievement_contract_screen 1, streak_details_screen 1, achievement_unlock_dialog 1, achievement_unlocked_dialog 1, achievement_share_bottom_sheet 1, achievement_progress_card 1, achievement_progress_banner 1, share_template_selector 1, streak_indicator 2) |
| 9 | notification_center (notification_analytics_screen 4, notification_center_repository 3, unified_notification_model 2) |
| 9 | knowledge (vocabulary_provider 9) |
| 7 | galaxy (galaxy_node_preview_card 6, node_detail_sheet 1) |
| 6 | translation (inline_translation_block 3, knowledge_integration_service 3) |
| 6 | focus (focus_repository 2, mindfulness_provider 2, reflection_dialog 2) |
| 5 | plan (plan_repository 1, plan_guide_generator 1, active_goal_provider 3) |
| 5 | experience (community_accountability_hub_card 1, goal_detail_snapshot_card 1, understanding_snapshot_card 2, growth_quality_card 1) |
| 3 | photon (photon_balance_card 3) |
| 3 | chat (aurora_receipt_chip 2, calibration_receipt_chip 2) |
| 2 | report (mastery_radar_chart 1, report_routes 1) |
| 2 | openclaw (openclaw_primitives 2) |
| 1 | simulation (simulation_chat_bubble 1) |

### 2.5 `_t()` Helper Pattern (82 additional violations)

The `_t()` helper is a wrapper around `isChinese` that centralizes the pattern but still bypasses ARB:

| Count | File |
|-------|------|
| 32 | `features/goal/presentation/screens/goal_creation_wizard_screen.dart` |
| 10 | `features/cognitive/presentation/widgets/strategy_migration_wizard.dart` |
| 9 | `features/error_book/presentation/widgets/remediable_patterns_card.dart` |
| 8 | `features/task/presentation/widgets/why_this_today_panel.dart` |
| 5 | `features/task/presentation/widgets/paused_task_status_panel.dart` |
| 4 | `features/task/presentation/widgets/task_protocol_panel.dart` |
| 4 | `features/goal/presentation/widgets/journey_progress_card.dart` |
| 4 | `features/goal/presentation/widgets/goal_intent_input.dart` |
| 4 | `features/community/presentation/widgets/accountability_hub/partner_observation_settings.dart` |
| 2 | `features/achievement/presentation/widgets/achievement_unlocked_dialog.dart` |

---

## 3. Hardcoded Strings NOT Caught by `isChinese` Pattern

### 3.1 Hardcoded Chinese Fallback Strings

These are Chinese strings used as fallbacks in code that should use ARB:

| File | Line | String |
|------|------|--------|
| `core/design/widgets/error_widget.dart` | 196 | `'哎呀，出错了'` |
| `core/design/widgets/error_widget.dart` | 198 | `'温馨提示'` |
| `core/design/widgets/error_widget.dart` | 200 | `'小提示'` |
| `core/design/widgets/error_widget.dart` | 204 | `'重试'` |
| `core/constants/app_constants.dart` | 5 | `appNameChinese = '星火'` |

### 3.2 `error_messages.dart` -- Chinese String Matching

`core/utils/error_messages.dart` contains Chinese character matching for error classification (lines 13-32, 114-130):
- `'没有找到'`, `'不存在'` -- for not-found errors
- `'登录信息已过期'`, `'令牌无效'`, `'重新登录'` -- for auth errors
- `'网络'`, `'连接'` -- for network errors
- `'服务器'`, `'打盹'` -- for server errors
- `'太频繁'`, `'休息一下'` -- for rate limiting
- `'权限'`, `'管理员'` -- for permission errors
- Hardcoded Chinese return strings: `'连接中断了...'`, `'看起来已经离线了...'`, etc. (lines 122-130)

These are particularly problematic because they match backend error messages that could change independently.

### 3.3 `design_system_linter.dart` -- Dev Tool with Chinese Output

`core/design/validation/design_system_linter.dart` contains extensive Chinese strings in its report generation (lines 310-439). This is a developer tool, so it may be acceptable, but it should be noted.

### 3.4 Comment Files with Chinese (not user-facing, informational only)

Multiple files have Chinese comments that are not user-facing:
- `core/design/color_extensions.dart` (110+ lines of Chinese doc comments)
- `core/design/motion.dart` (Chinese comments)
- `core/design/tokens_v2/typography_token.dart` (Chinese comments)
- `core/design/tokens_v2/responsive_system.dart` (Chinese comments)
- `core/design/components/organisms/expandable_section.dart` (Chinese comments)

These are developer-facing and do not need i18n.

---

## 4. l10n Code Generation Verification (PASS)

| Metric | Count |
|--------|-------|
| ARB keys (EN) | 9,400 |
| Generated getters/methods (`app_localizations_en.dart`) | 9,400 |
| Abstract class getters/methods (`app_localizations.dart`) | 9,400 |
| ARB keys not in generated | 0 |
| Generated keys not in ARB | 0 |
| Abstract class keys not in generated | 0 |

**Result**: Code generation is perfectly in sync with ARB files.

---

## 5. Severity Classification

### P0 -- Immediate Fix Required

1. **`error_widget.dart` hardcoded Chinese fallbacks** (4 strings): These are unconditional Chinese strings that appear to ALL users regardless of locale. If l10n is null, the fallback is Chinese -- should be English or locale-aware.

2. **`error_messages.dart` Chinese string matching** (lines 13-32): Backend error messages are matched using Chinese strings. This is fragile and will break if the backend changes its error message language.

### P1 -- Systematic Migration Required

3. **988 `isChinese` ternary violations** across 204 files: Every instance bypasses the ARB system and cannot be extended to additional locales without code changes.

4. **82 `_t()` helper violations** across 10 files: Same problem, different wrapping.

### P2 -- Design Decision Needed

5. **15 ARB parameter mismatches** between EN and ZH: The `timeXxx` and `timeInXxx` keys have ICU plural in EN but simple placeholders in ZH. This is linguistically correct but should be verified to not cause runtime issues.

6. **`app_constants.dart` hardcoded `appNameChinese`**: Should be in ARB.

---

## 6. Recommended Fix Approach

### Phase 1: Quick Wins (P0 fixes)
- Fix `error_widget.dart` fallbacks to use English as default
- Add bilingual matching in `error_messages.dart` or use error codes instead of string matching
- Move `appNameChinese` to ARB

### Phase 2: Systematic Migration (P1)
The recommended migration strategy for the 988+82 violations:

1. **Create ARB keys**: For each `isChinese ? 'zh' : 'en'` pattern, add a key to both `app_en.arb` and `app_zh.arb`
2. **Replace patterns**: `I18nService.instance.isChinese ? '加载中' : 'Loading'` becomes `context.l10n.loading`
3. **Handle parameterized strings**: `isChinese ? '$n项' : '$n items'` becomes `context.l10n.itemCount(n)`
4. **Remove `_t()` helpers**: Replace with `context.l10n.xxx` calls
5. **Estimated new ARB keys needed**: ~550-650 (some patterns repeat across files)

### Phase 3: Verification
- Run `flutter gen-l10n` and verify no new errors
- Full regression test across both locales
- Add CI check: `grep -rn "isChinese ? '" mobile/lib/ --include="*.dart"` should return 0

### Priority Order for Migration
1. Core widgets (`error_widget`, `loading_indicator`, `compact_error_card`) -- highest user visibility
2. Home dashboard (`dashboard_screen`, `next_actions_card`, etc.) -- most used screens
3. Community screens -- second highest traffic
4. Feature screens (tools, calendar, etc.) -- functional screens
5. Repository layer (error messages) -- lowest visibility but high correctness impact

---

## 7. Infrastructure Notes

### Exempt Files (correct usage, no migration needed)
- `core/extensions/context_l10n.dart` -- defines `isChinese` getter, correct
- `core/services/i18n_service.dart` -- defines `I18nService`, correct
- `features/home/presentation/widgets/exam_sprint_dashboard_card.dart` -- uses `isChinese` as parameter passed to sub-widgets, structural pattern (needs refactoring but not straightforward migration)

### i18n System Architecture
```
Source of Truth: mobile/lib/l10n/app_en.arb + app_zh.arb
Generated Code:  mobile/lib/l10n/app_localizations.dart (abstract)
                 mobile/lib/l10n/app_localizations_en.dart (EN impl)
                 mobile/lib/l10n/app_localizations_zh.dart (ZH impl)
Runtime Access:  context.l10n.xxx (via BuildContext)
Bypass Pattern:  I18nService.instance.isChinese ? 'zh' : 'en' (violations)
```

The ARB system is healthy and well-maintained. The problem is entirely in the presentation layer's failure to use it consistently.
