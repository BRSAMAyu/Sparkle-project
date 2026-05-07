# R17-A Flutter/Mobile Final Audit Report

**Date**: 2026-05-07
**Auditor**: Deep Audit Agent (L5 Final)
**Scope**: Full Flutter mobile codebase -- 1193 Dart files, 131 screens, 45+ features

---

## Audit Scope

| Area | Files Scanned | Method |
|------|--------------|--------|
| Features (`lib/features/`) | ~1100 .dart files | Glob + Grep + Read |
| Core Design System (`lib/core/design/`) | ~40 .dart files | Full read of key widgets |
| Core Services (`lib/core/services/`) | ~30 .dart files | Key files read |
| Offline/CRDT (`lib/core/offline/`) | ~15 .dart files | Full read |
| i18n ARB files | app_en.arb (13650 lines), app_zh.arb (13671 lines) | Key-level diff |
| Special features (vocabulary, translation, ASR, BGM) | 10+ files each | Full read |

---

## P0 Findings (Critical Issues)

### P0-1: `app_permission_dialog.dart` -- 50+ lines of hardcoded Chinese with zero English fallback

- **File**: `mobile/lib/core/design/widgets/app_permission_dialog.dart:22-70`
- **Current State**: The `title()`, `description()`, and `settingsHint()` methods for `notifications`, `camera`, `photos`, and `storage` permissions contain ONLY Chinese strings with no English fallback at all. The `microphone` case correctly uses `context.l10n`, but all other 4 cases are purely Chinese.
- **Problem**: English-speaking users will see Chinese-only permission dialogs. This is a user-facing accessibility failure in core infrastructure.
- **Evidence**:
  ```dart
  case AppPermissionKind.notifications:
    return '需要通知权限';  // No English fallback
  case AppPermissionKind.camera:
    return '需要相机权限';  // No English fallback
  ```
  The `settingsHint()` method contains 10 hardcoded Chinese-only strings (5 permissions x 2 platforms).
- **Impact**: 30+ hardcoded Chinese-only strings across title/description/settingsHint.
- **Suggested Fix**: Add ARB keys for all permission strings and use `context.l10n` consistently, matching the existing `microphone` pattern.

### P0-2: `universal_share_bottom_sheet.dart` -- Entire share UI hardcoded in Chinese only

- **File**: `mobile/lib/core/design/widgets/universal_share_bottom_sheet.dart:37-947`
- **Current State**: 19 hardcoded Chinese-only strings across:
  - Template names/descriptions (lines 37-59): `'星空'`, `'简约'`, `'霓虹'`, `'典雅'`
  - Privacy toggle labels (lines 463-484): `'显示头像'`, `'显示统计'`, `'显示进度'`
  - Share button labels (line 731): `'复制分享文案'`
  - Section headers (lines 779, 788): `'分享文案'`, multi-sentence Chinese-only descriptions
  - Success feedback (line 947): `'分享文案已复制'`
- **Problem**: The entire share bottom sheet shows only Chinese text regardless of user language setting.
- **Suggested Fix**: Create ARB keys for all share template names, privacy toggles, and action labels.

### P0-3: `loading_indicator.dart` -- "加载中" hardcoded as default with no English fallback

- **File**: `mobile/lib/core/design/widgets/loading_indicator.dart:138,145,159,197,212`
- **Current State**: 5 instances of `loadingText ?? '加载中'` used as both Semantics labels and visible text.
- **Problem**: When no `loadingText` is provided, ALL loading states across the app show "加载中" (Chinese "Loading") to English users. This affects every screen that uses the standard loading indicator without explicit text.
- **Suggested Fix**: Use `I18nService.instance.isChinese ? '加载中' : 'Loading'` or an ARB key as the default fallback.

### P0-4: `app_feedback.dart` -- "重试" hardcoded as default retry button label

- **File**: `mobile/lib/core/design/widgets/app_feedback.dart:147`
- **Current State**: `String retryLabel = '重试'` as default parameter
- **Problem**: Error snackbars across the entire app show "重试" (Chinese "Retry") to English users when no explicit retry label is passed.
- **Suggested Fix**: Use a bilingual default: `I18nService.instance.isChinese ? '重试' : 'Retry'` or require the caller to always pass a localized label.

### P0-5: `agent_statistics_provider.dart` -- Error message Chinese-only, breaks English UX

- **File**: `mobile/lib/core/statistics/presentation/providers/agent_statistics_provider.dart:195`
- **Current State**: `state = state.withError('加载失败: $e');` -- pure Chinese, no English fallback.
- **Problem**: Unlike `focus_statistics_provider.dart` and `capsule_statistics_provider.dart` (which correctly use `I18nService.instance.isChinese ? '...' : '...'`), this provider only shows Chinese error messages.
- **Suggested Fix**: Match the pattern used by sibling providers: `I18nService.instance.isChinese ? '加载失败: $e' : 'Failed to load: $e'`.

---

## P1 Findings (Important Issues)

### P1-1: Massive i18n inconsistency -- 1150+ hardcoded Chinese strings using inline ternary instead of ARB

- **Files**: Across 200+ files in `lib/` (both `core/` and `features/`)
- **Current State**:
  - 5944 proper ARB references via `context.l10n.*` or `AppLocalizations.of()`
  - 665 lines using `I18nService.instance.isChinese ? '中文' : 'English'` pattern
  - 485 lines using `zh ? '中文' : 'English'` local variable pattern
  - ~50 lines of pure Chinese with NO English fallback at all (see P0 items)
- **Problem**: The inline `isChinese ? '中文' : 'English'` pattern bypasses the ARB localization system. This means:
  1. Strings cannot be extracted/verified by tooling
  2. Adding a third language requires code changes instead of adding ARB keys
  3. String consistency cannot be validated (e.g., different translators may write different English for the same concept)
- **Most affected areas**:
  - `features/experience/presentation/widgets/` -- 60+ inline i18n strings
  - `features/insights/presentation/` -- 80+ inline i18n strings
  - `features/community/presentation/` -- 100+ inline i18n strings
  - `features/home/presentation/` -- 50+ inline i18n strings
  - `core/statistics/` -- 40+ inline i18n strings
- **Suggested Fix**: Migrate inline ternary patterns to ARB keys in batches per feature. This is a known tech debt item, not a regression.

### P1-2: `compact_error_card.dart` uses inline i18n instead of ARB

- **File**: `mobile/lib/core/design/widgets/compact_error_card.dart:28-34`
- **Current State**:
  ```dart
  zh ? '加载失败' : 'Failed to load',
  zh ? '轻触重试' : 'Tap to retry',
  ```
- **Problem**: Core error widget uses inline i18n. As a core infrastructure widget, it should use ARB for consistency with the rest of the design system.
- **Suggested Fix**: Add ARB keys like `errorLoadFailed` and `errorTapToRetry`.

### P1-3: `error_widget.dart` fallback strings are Chinese-only

- **File**: `mobile/lib/core/design/widgets/error_widget.dart:196-204`
- **Current State**:
  ```dart
  return l10n?.errorTitle ?? l10n?.errorDefaultTitle ?? '哎呀，出错了';
  return l10n?.warningTitle ?? l10n?.warningDefaultTitle ?? '温馨提示';
  return l10n?.infoTitle ?? l10n?.infoDefaultTitle ?? '小提示';
  return l10n?.retry ?? l10n?.retryLabel ?? '重试';
  ```
- **Problem**: The final fallback strings are Chinese-only. If `l10n` is null (e.g., before localization initialization), English users see Chinese text. The fallback should be English (the default language).
- **Suggested Fix**: Change final fallbacks to English: `'Oops, something went wrong'`, `'Retry'`, etc.

### P1-4: `flame_indicator.dart` -- hardcoded Chinese label without English

- **File**: `mobile/lib/core/design/widgets/flame_indicator.dart:244`
- **Current State**: `'亮度 ${widget.brightness}%'` -- pure Chinese, no English.
- **Problem**: "亮度" (Brightness) label is always shown in Chinese.
- **Suggested Fix**: Use `I18nService.instance.isChinese ? '亮度 ${widget.brightness}%' : 'Brightness ${widget.brightness}%'`.

### P1-5: `share_trigger_button.dart` -- hardcoded Chinese defaults

- **File**: `mobile/lib/core/design/widgets/share_trigger_button.dart:144,331,402`
- **Current State**:
  - Line 144: `label ?? '分享'` (Share)
  - Line 331: `'进度: ${(progress! * 100).toStringAsFixed(0)}%'` (Progress)
  - Line 402: `'掌握度: ${(masteryLevel! * 100).toStringAsFixed(0)}%'` (Mastery)
- **Problem**: Default share label and two subtitle formatters are Chinese-only.
- **Suggested Fix**: Add English fallbacks for all three strings.

### P1-6: `engagement_heatmap.dart` -- hardcoded Chinese title and subtitle

- **File**: `mobile/lib/core/design/widgets/charts/engagement_heatmap.dart:50-57`
- **Current State**:
  ```dart
  const Text('学习活跃度', style: TextStyle(fontSize: 16, fontWeight: DS.fontWeightBold)),
  Text('过去 90 天的学习记录', style: TextStyle(fontSize: 12, color: DS.brandPrimary)),
  ```
- **Problem**: Chart header uses hardcoded Chinese strings without any i18n. Also uses a raw `TextStyle(fontSize: 16, fontWeight: ...)` instead of theme tokens.
- **Suggested Fix**: Add ARB keys and use theme typography.

### P1-7: `statistics_overview_cards.dart` -- hardcoded inline i18n

- **File**: `mobile/lib/core/statistics/presentation/widgets/common/statistics_overview_cards.dart:148`
- **Current State**: `I18nService.instance.isChinese ? '较上期' : 'vs last'`
- **Problem**: This is a visible comparison label using inline i18n.
- **Suggested Fix**: Add to ARB.

### P1-8: `offline_dictionary_service.dart` -- Chinese-only exception messages

- **File**: `mobile/lib/features/vocabulary/data/services/offline_dictionary_service.dart:157-166`
- **Current State**:
  ```dart
  throw Exception('下载的词典包为空');
  throw Exception('离线词典包格式无效');
  throw Exception('离线词典包缺少 entries');
  ```
- **Problem**: Exception messages are Chinese-only. While exceptions are developer-facing, these propagate to user-facing error states and will be displayed in Chinese to all users.
- **Suggested Fix**: Use English exception messages (industry standard) or bilingual format.

### P1-9: ~10 screens missing empty state handling

- **Files** (presentation screens with no empty state detected):
  - `achievement_contract_screen.dart`
  - `data_usage_dashboard_screen.dart`
  - `accessibility_settings_screen.dart`
  - `plan_edit_screen.dart`
  - `task_reminder_settings_screen.dart`
  - `tool_host_screen.dart`
  - `theme_settings_screen.dart`
  - `learning_mode_screen.dart`
  - `guest_upgrade_screen.dart`
  - `social_accounts_screen.dart`
  - `focus_statistics_screen.dart`
  - `memory_settings_screen.dart`
- **Problem**: These screens may show blank areas or no feedback when their data is empty. Settings screens and form screens are less critical, but `focus_statistics_screen.dart`, `plan_edit_screen.dart`, and `tool_host_screen.dart` could show confusing blank states.
- **Suggested Fix**: For data-display screens, add explicit empty state widgets. Settings/form screens are acceptable without empty states.

### P1-10: `statistics_report_generator.dart` -- Chinese-only date format fallback

- **File**: `mobile/lib/core/statistics/presentation/widgets/report/statistics_report_generator.dart:308`
- **Current State**: `return '${date.year}年${date.month}月${date.day}日';`
- **Problem**: When `l10n` is null, the fallback date format is Chinese-only. Note that when l10n IS available, it correctly uses `l10n.statisticsDateFormat(...)`.
- **Suggested Fix**: Use an English fallback format: `'${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}'`.

### P1-11: 38 instances of hardcoded hex colors outside design tokens

- **Files**: Across `achievement/`, `home/`, `chat/`, `memory/` features
- **Current State**: Hardcoded colors like `Color(0xFF13213C)`, `Color(0xFFFFC107)`, `Color(0xFF8BE9FD)`, etc., used directly in widget code.
- **Most affected**:
  - `achievement/presentation/screens/milestone_celebration_screen.dart`: 8 hardcoded colors (celebration theme)
  - `home/presentation/widgets/layers/background_layer.dart`: 5 hardcoded colors (sky gradient)
  - `home/presentation/widgets/exam_sprint_dashboard_card.dart`: 2 hardcoded colors
  - `home/presentation/widgets/visual_renderer.dart`: 1 hardcoded color
  - `achievement/presentation/widgets/achievement_share_bottom_sheet.dart`: 1 hardcoded WeChat green
- **Problem**: These colors do not respond to theme changes (dark mode, high contrast, color blind mode). Celebration screens and special visual effects are somewhat justified, but `achievement_contract_screen.dart`, `achievement_map_screen.dart`, and `memory_settings_screen.dart` have colors that should use tokens.
- **Suggested Fix**: For celebration/decorative screens, define named color constants. For standard UI screens, migrate to DS tokens.

---

## P2 Findings (Minor Issues)

### P2-1: `return_case_file_card.dart` uses `const TextStyle(fontSize: 13)` ignoring theme

- **File**: `mobile/lib/features/insights/presentation/widgets/return_case_file_card.dart:153,166`
- **Current State**: `const TextStyle(fontSize: 13)` hardcoded on buttons
- **Problem**: Ignores theme font scale settings (accessibility). Users who set larger font sizes in accessibility settings will not see these labels scale.
- **Suggested Fix**: Use `DefaultTextStyle.of(context).style.copyWith(fontSize: 13)` or theme text theme.

### P2-2: `speech_to_text_tool.dart` uses inline i18n for hero chips and metric captions

- **File**: `mobile/lib/features/tools/presentation/widgets/speech_to_text_tool.dart:42,68-71,85,92`
- **Current State**:
  ```dart
  I18nService.instance.isChinese ? '转写文本已复制' : 'Transcript copied'
  zh ? '实时转写' : 'Live transcription'
  zh ? '适合直接发送或整理' : 'Ready to send or organize'
  zh ? '便于快速判断长度' : 'Quick length reference'
  ```
- **Problem**: 6 inline i18n strings instead of ARB keys.
- **Suggested Fix**: Add ARB keys for STT tool strings.

### P2-3: `learning_forecast_screen.dart` -- 12+ inline Chinese strings

- **File**: `mobile/lib/features/insights/presentation/screens/learning_forecast_screen.dart:143-495`
- **Current State**: Multiple strings like `'AI 预测系统'`, `'基于学习数据的智能分析'`, `'最佳学习时间'`, weekday names `['周一'...'周日']`
- **Problem**: Entire screen uses inline i18n. Weekday names should definitely use ARB since `DateFormat` provides localized weekday names.
- **Suggested Fix**: Migrate to ARB keys.

### P2-4: `learning_insights_overview_screen.dart` -- 15+ inline Chinese strings

- **File**: `mobile/lib/features/insights/presentation/screens/learning_insights_overview_screen.dart:106-477`
- **Current State**: Many descriptive Chinese strings with English fallbacks via `zh ?` pattern.
- **Problem**: Long descriptive strings are maintained inline, making translation updates error-prone.
- **Suggested Fix**: Migrate to ARB keys.

### P2-5: Hardcoded `TextStyle` usages across multiple widget files (not using theme)

- **Files** (partial list):
  - `understanding_snapshot_card.dart`: 5 hardcoded `TextStyle(...)` instances
  - `goal_detail_snapshot_card.dart`: 7 hardcoded `TextStyle(...)` instances
  - `community_accountability_hub_card.dart`: 2 hardcoded `TextStyle(...)` instances
  - `growth_quality_card.dart`: 5 hardcoded `TextStyle(...)` instances
  - `task_monitor_screen.dart`: 8 hardcoded `TextStyle(...)` instances
  - `learning_heatmap_widget.dart`: 8 hardcoded `TextStyle(...)` instances
- **Problem**: These TextStyles specify `fontSize` and `color` directly, which means:
  1. Font scale accessibility settings are ignored
  2. Dark mode color adjustments may not apply
- **Note**: Most use DS token colors (e.g., `color: DS.textPrimary`), so dark mode is partially handled. But font scale from accessibility settings is still ignored.
- **Suggested Fix**: Use `Theme.of(context).textTheme.bodyMedium?.copyWith(...)` pattern for accessibility compliance.

### P2-6: `openclaw_connection_panel.dart` uses `'WebSocket'` as raw English label

- **File**: `mobile/lib/features/settings/presentation/widgets/openclaw_connection_panel.dart:1073`
- **Current State**: `label: Text('WebSocket')`
- **Problem**: Technical term shown directly without i18n.
- **Suggested Fix**: Minor -- this is a developer-facing technical term, but should still go through ARB for consistency.

### P2-7: `openclaw_pairing_scanner_sheet.dart` -- Chinese-only strings

- **File**: `mobile/lib/features/settings/presentation/widgets/openclaw_pairing_scanner_sheet.dart:72-77`
- **Current State**:
  ```dart
  '扫码连接 OpenClaw',
  '把桌面端显示的配对二维码放进取景框，Sparkle 会自动识别并导入连接配置。',
  ```
- **Problem**: Two user-visible strings with no English fallback.
- **Suggested Fix**: Add English fallbacks or ARB keys.

### P2-8: `context_aware_intent_classifier.dart` -- Chinese keyword matching hardcoded

- **File**: `mobile/lib/features/home/domain/services/context_aware_intent_classifier.dart:81-90`
- **Current State**:
  ```dart
  return lower.contains('冲刺') || lower.contains('突击') || lower.contains('专注');
  return lower.contains('学习') || ...
  ```
- **Problem**: Intent classification only works for Chinese input. English keywords like "sprint", "focus", "study" are not matched.
- **Suggested Fix**: Add English keyword matching alongside Chinese.

### P2-9: `weekly_growth_narrative.dart` (data model) -- Chinese content in domain layer

- **File**: `mobile/lib/features/insights/data/models/weekly_growth_narrative.dart:23-66`
- **Current State**: Multiple Chinese-only fallback strings like `'本周成长故事'`, `'这是你的第一周，先开始吧。'` with English via ternary.
- **Problem**: Domain models should not contain presentation-layer strings. These belong in presentation/widgets.
- **Suggested Fix**: Move presentation strings to the widget layer and use ARB keys.

### P2-10: `growth_dashboard.dart` (data model) -- Chinese content in domain layer

- **File**: `mobile/lib/features/insights/data/models/growth_dashboard.dart:50-119`
- **Current State**: Multiple Chinese fallback strings for growth insights, turning points, and pattern descriptions.
- **Problem**: Same as P2-9 -- domain model contains presentation text.
- **Suggested Fix**: Same as P2-9.

### P2-11: 4 screens in `features/community/` have no explicit empty/loading/error state handling

- **Files**:
  - `community_main_screen.dart` -- delegates to child widgets, acceptable
  - `group_list_screen.dart` -- delegates to `GroupsHubView`, acceptable
  - `group_files_screen.dart` -- needs verification
  - `community_screen.dart` -- delegates to `FeedTabContent`, acceptable
- **Problem**: Community screens delegate to child widgets, so the actual state handling is in the child components. This is an architectural pattern, not a missing state.
- **Suggested Fix**: Verify child components have proper state handling (likely already handled).

---

## P3 Findings (Style/Suggestions)

### P3-1: `design_validator.dart` contains Chinese-only validation messages

- **File**: `mobile/lib/core/design/validation/design_validator.dart:88-291`
- **Current State**: All validation messages and recommendations are in Chinese only.
- **Context**: This is a developer/debugging tool, not user-facing. Chinese-only is acceptable for a design validator.
- **Suggested Fix**: Consider adding English messages for international contributors, but low priority.

### P3-2: Several `ListView` (non-builder) instances in theater screen

- **Files**: `knowledge_theater_screen.dart` lines 794, 1570, 1997, 2117, 2150, 2170
- **Current State**: Uses `ListView(children: [...])` instead of `ListView.builder`.
- **Problem**: If the children list is long, it builds all children upfront. However, these lists appear to be bounded (fixed sections), so the performance impact is minimal.
- **Suggested Fix**: Low priority -- only optimize if profiling shows jank.

### P3-3: `Colors.white` / `Colors.black` usage in feature widgets

- **Files**: Multiple files in `achievement/`, `splash/`, `auth/`
- **Current State**: `Colors.white` used as icon/text color in celebration screens, splash screen, login screen.
- **Problem**: These don't respond to theme changes. However, for specific screens like splash and celebration that have fixed backgrounds, this is intentional.
- **Suggested Fix**: Only migrate if the screen needs dark mode support.

### P3-4: 77 TODO/FIXME markers in features code

- **Observation**: 77 `TODO`/`FIXME`/`HACK`/`XXX` comments exist in `lib/features/`.
- **Suggested Fix**: Review and resolve or convert to tracked issues.

---

## Verified Healthy Areas

These areas were thoroughly inspected and confirmed to be well-implemented:

1. **WebSocket Chat Service** (`websocket_chat_service_v2.dart`): 2699 lines with comprehensive dispose, reconnect scheduling, heartbeat, offline queue, and state management. Resource cleanup is thorough.

2. **Audio Recording Service** (`audio_recording_service.dart`): Proper lifecycle management with dispose, cancel, WebSocket cleanup, and I18n-aware error messages.

3. **BGM Library Screen** (`bgm_library_screen.dart`): 100% ARB-based i18n (all strings use `context.l10n.*`), proper controller disposal, good empty state handling.

4. **Accessibility Provider** (`accessibility_provider.dart`): Comprehensive settings including font scale, high contrast, screen reader, color blind mode, haptic feedback, low load mode. Proper local persistence and server sync.

5. **Translation Service** (`translation_service.dart`): Clean API integration with proper error handling and null safety.

6. **Offline Dictionary Service** (`offline_dictionary_service.dart`): Proper Isolate-based file I/O, gzip decompression, lookup caching. Exception messages are the only i18n gap (P1-8).

7. **CRDT Persistence** (`crdt_persistence.dart`): Proper Isar integration with upsert semantics, connectivity check before sync.

8. **Conflict Resolver** (`conflict_resolver.dart`): Sound 3-tier resolution strategy (revision > timestamp > mastery).

9. **Notification Center** (`notification_center_screen.dart`): Full ARB-based i18n, loading/empty/error states, proper Riverpod integration.

10. **Deep Link Router** (`app_link_router_service.dart`): Proper stream subscription management, fallback scheduling, dispose handling.

11. **Controller Disposal**: All checked widgets (`weather_guide_screen`, `cognitive_tool_hub_card`, `dashboard_card_carousel`, `openclaw_hub_screen`, `community_main_screen`) properly dispose their controllers.

12. **ARB File Synchronization**: EN and ZH ARB files have exactly 9226 matching keys each -- zero key drift.

13. **Semantics Usage**: 262 Semantics annotations in features + 12 in core design. Core infrastructure widgets (loading, error, buttons) have proper accessibility labels.

14. **Back Button Handling**: Critical screens (`sprint_completion`, `mindfulness_mode`, `task_execution`, `create_group`) use `PopScope` for controlled back navigation.

15. **Firebase Messaging** (`firebase_messaging_service.dart`): Proper foreground/background message handling with stream subscriptions.

---

## False Positive Exclusions

| Item Checked | Why Not An Issue |
|-------------|-----------------|
| Chinese comments in code | Comments are not user-facing. Allowed per i18n rules. |
| `data/models/` Chinese strings | Many are fallback defaults in data models with proper ternary patterns. Flagged domain-layer presentation strings separately (P2-9, P2-10). |
| `design_validator.dart` Chinese | Developer tool, not user-facing. |
| `learning_dashboard_page.dart` using `colors.primary` | Correctly uses `Theme.of(context).colorScheme` -- this is proper design system usage. |
| `openclaw_screen.dart` missing states | Technical/debug screen, not user-facing. |
| `splash_screen.dart` missing empty state | Splash screens inherently have no empty state. |
| `legal_document_screen.dart` missing states | Static document viewer, no dynamic data. |
| `auth/forgot_password_screen.dart` missing empty state | Form screen, empty state not applicable. |
| Settings screens missing empty states | Form/settings screens do not need empty states. |
| `DS.textPrimary` / `DS.textSecondary` colors | These ARE design tokens (correctly used). |
| `Color(0xFF6366F1)` in `DefaultShareTemplates` | Intentional fixed brand colors for share card templates. |
| `Color(0xFF07C160)` WeChat green | Platform-specific brand color, intentional. |

---

## Summary Statistics

| Severity | Count |
|----------|-------|
| P0 (Critical) | 5 |
| P1 (Important) | 11 |
| P2 (Minor) | 11 |
| P3 (Style) | 4 |
| **Total Issues** | **31** |

### Issue Distribution by Category

| Category | P0 | P1 | P2 | P3 |
|----------|----|----|----|----|
| i18n (hardcoded Chinese without English) | 5 | 6 | 4 | 1 |
| i18n (inline ternary vs ARB) | 0 | 1 | 2 | 0 |
| Design Tokens (hardcoded colors) | 0 | 1 | 0 | 1 |
| Accessibility (font scale, semantics) | 0 | 0 | 2 | 0 |
| Missing UI states (empty/loading/error) | 0 | 1 | 1 | 0 |
| Architecture (domain layer strings) | 0 | 0 | 2 | 0 |
| Other | 0 | 2 | 0 | 2 |

### Priority Action Items

1. **Immediate** (P0): Fix `app_permission_dialog.dart`, `universal_share_bottom_sheet.dart`, `loading_indicator.dart`, `app_feedback.dart`, and `agent_statistics_provider.dart` -- these show Chinese-only text to English users.
2. **Short-term** (P1): Fix fallback strings in `error_widget.dart`, `flame_indicator.dart`, `share_trigger_button.dart`, `engagement_heatmap.dart`, and `offline_dictionary_service.dart`.
3. **Medium-term** (P1-P2): Continue migrating inline `isChinese ? '...' : '...'` patterns to ARB keys, starting with core design widgets and high-traffic screens.
4. **Ongoing** (P2-P3): Migrate hardcoded `TextStyle` to theme-aware patterns for accessibility compliance.
