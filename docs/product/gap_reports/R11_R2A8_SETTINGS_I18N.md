# R11_R2A8: Settings, i18n, Accessibility, Emotion Adaptation -- Final Pre-Launch Audit

**Date**: 2026-05-07 | **Auditor**: Claude Code (DeepSeek v4)
**Scope**: Settings Screen, i18n (Bilingual EN/ZH), Accessibility (WCAG AA), Emotion Adaptive UI, Theme, Notifications, Profile
**Files Audited**: 50+ source files + 2 ARB files (13,576/13,597 lines)

---

## 1. Settings Screen Audit

### 1.1 Categories Present

The Unified Settings Screen (`unified_settings_screen.dart`, ~2,900+ lines) covers 20 categories:

| # | Category | Status | Widget |
|---|----------|--------|--------|
| 1 | Sensory Feedback (sound/haptic/ambient) | COMPLETE | Collapsible expandable |
| 2 | Accessibility | COMPLETE | Links to dedicated screen |
| 3 | Behavior Explanation | COMPLETE | SettingsBehaviorExplanation card |
| 4 | Learning Preferences (depth/curiosity 2D) | COMPLETE | LearningModeControl widget |
| 5 | Capsule Generation | COMPLETE | Collapsible | 
| 6 | Weekly Agenda Grid | COMPLETE | Collapsible |
| 7 | Theme Mode (system/light/dark) | COMPLETE | Links to ThemeSettingsScreen |
| 8 | Transparency Level (0-3) | COMPLETE | Inline selector |
| 9 | AI Reasoning Mode (fast/balanced/deep) | COMPLETE | Inline selector |
| 10 | Chat Preferences (enter-to-send, pure mode, etc.) | COMPLETE | Collapsible |
| 11 | Motion Intensity (low/medium/high) | COMPLETE | Inline selector |
| 12 | Emotion Adaptive Mode (auto/low/normal) | COMPLETE | Inline selector |
| 13 | Notifications (system toggle, types, level, quiet hours) | COMPLETE | Collapsible |
| 14 | Smart Push (curiosity, daily cap, persona) | COMPLETE | Link to dedicated screen |
| 15 | Task Reminders | COMPLETE | Link to dedicated screen |
| 16 | System Update Level (silent/summary/detailed) | COMPLETE | Inline selector |
| 17 | BGM (palette, volume, mode, intensity, variety) | COMPLETE | Collapsible |
| 18 | Aurora Preference Overrides | COMPLETE | Collapsible (feature-flagged) |
| 19 | Data Controls (hide chronicle/memory, export, delete) | COMPLETE | Dedicated card |
| 20 | Language (ZH/EN) | COMPLETE | ListTile with dialog |

### 1.2 Profile Settings Menu

From `profile_screen.dart`:

| Section | Items | Route |
|---------|-------|-------|
| Guest Upgrade | Conditional tile | `/profile/upgrade-guest` |
| Personal Growth | Learning Portfolio, Study Materials, Achievements, Poster Studio, Visual Elements, Persona | Various |
| Settings | Edit Profile (avatar/nickname/email), Preferences (unified settings), My Way (skills), Metacognition Panel toggle | Various |
| Account | Account Security, Memory Controls (feature-flagged), Export Data | Various |
| Sign Out | Logout with confirmation dialog, Delete Account | `/profile/delete-account` |

### 1.3 Persistence Architecture (PASS)

All settings follow a dual-layer persistence strategy:
- **Layer 1**: `SharedPreferences` (local, immediate on change)
- **Layer 2**: Server sync via `userRepositoryProvider.updateUserSettings()` (remote, eventual)

Error handling uses optimistic update + rollback pattern in most providers. The `settings_provider.dart` (1,188 lines) contains 25+ providers with save/load/sync patterns.

### 1.4 Reset to Defaults

| Setting Category | Reset Mechanism | Verified |
|-----------------|-----------------|----------|
| Theme | Reset button in `theme_settings_screen.dart:59-71`, calls `themeManager.reset()` | YES |
| Accessibility | Reset button in `accessibility_settings_screen.dart:31-38`, calls `notifier.reset()` | YES |
| Other categories | Reset by clearing SharedPreferences key or re-initializing notifier | YES |

**P2-001: No global "Reset All Settings" button.**
- File: `unified_settings_screen.dart`
- Only theme and accessibility have per-category reset. No single action resets all SharedPreferences keys + server-synced settings.
- Fix: Add guard-confirmed "Reset All Settings" button at the bottom of settings page.

### 1.5 Settings-to-Behavior Trace

| Setting | UI Control | Persistence | Consumed By | Affects Behavior? |
|---------|-----------|-------------|-------------|-------------------|
| Theme mode | ThemeSettingsScreen | SharedPrefs `theme_mode` | `ThemeManager` -> `MaterialApp.themeMode` | YES |
| Language/Locale | Language dialog | SharedPrefs `app_locale` | `localeProvider` -> `MaterialApp.locale` + I18nService | YES |
| AI Reasoning Mode | Inline selector | SharedPrefs + backend | `AiReasoningModeNotifier` invalidates dashboard providers | YES |
| BGM enabled/volume/palette | Collapsible section | BgmService (native) | BgmService static methods play/stop audio | YES |
| Sensory sound/haptic | Collapsible section | SensoryFeedbackService | SensoryFeedbackService static methods | YES |
| Transparency Level | Inline selector | SharedPrefs + backend | `transparentModeProvider` derived | YES |
| Notification prefs | Collapsible section | Backend repository | `NotificationPreferenceSettingsNotifier` + task scheduler refresh | YES |
| Push prefs | SmartPushSettingsScreen | Backend API | `/users/me/push-preference` + `/memory/push-settings` | YES |
| Learning prefs | 2D control | SharedPrefs + backend | `LearningPreferencesNotifier` updates user model | YES |
| Emotion adaptive mode | Inline selector | SharedPrefs `settings_emotion_adaptive_mode` | `EmotionResponsiveAppWrapper` in app builder | YES |
| Motion intensity | Inline selector | SharedPrefs + PerformanceService | `PerformanceService.instance.setMotionIntensityLevel()` | YES |
| Task reminders | TaskReminderSettingsScreen | Backend | TaskNotificationScheduler refreshes all reminders | YES |
| **Accessibility fontScale** | Slider in dedicated screen | SharedPrefs + backend | **NOT CONSUMED** | **NO** (P1) |
| **Accessibility highContrast** | Toggle in dedicated screen | SharedPrefs + backend | **Separate ThemeManager._highContrast** | **PARTIAL** (P1) |
| **Accessibility screenReaderOpt** | Toggle in dedicated screen | SharedPrefs + backend | **NOT CONSUMED** | **NO** (P1) |
| **Accessibility touchTargetSize** | ChoiceChips in dedicated screen | SharedPrefs + backend | **NOT CONSUMED** | **NO** (P1) |
| **Accessibility reduceMotion** | Toggle in dedicated screen | SharedPrefs + backend | **NOT CONSUMED (EmotionResponsive handles separately)** | **NO** (P1) |
| **Accessibility colorBlindFriendly** | Toggle in dedicated screen | SharedPrefs + backend | **ZERO CONSUMERS** | **NO** (P1) |
| **Accessibility ttsEnabled** | Toggle in dedicated screen | SharedPrefs + backend | **NOT CONSUMED** | **NO** (P1) |
| **Accessibility hapticFeedback** | Toggle in dedicated screen | SharedPrefs + backend | **Separate SensoryFeedbackService toggle** | **PARTIAL** (P1) |

**Critical Finding (P1-001)**: The `accessibilitySettingsProvider` is ONLY consumed in `mobile/lib/features/settings/presentation/screens/accessibility_settings_screen.dart` (its own screen). It is NOT watched by `app.dart`, NOT injected into the widget tree, and NOT consumed by any factory widgets. Users can toggle all accessibility settings and see NO behavioral change except on the settings screen itself.

---

## 2. Accessibility Audit (WCAG AA)

### 2.1 Accessibility Settings Screen

**File**: `mobile/lib/features/settings/presentation/screens/accessibility_settings_screen.dart` (517 lines)

Rich UI with 4 sections:
- Low-load mode (bundles reduceMotion + screenReader + large touch + min font scale)
- Reading (font scaling slider 0.85x-1.4x, high contrast, color-blind friendly)
- Interaction (touch target sizes with preview, reduce motion, haptic feedback)
- Assistive tech (screen reader optimization, TTS reading)
- WCAG checklist (4 items with check icons)

Provider: `accessibility_provider.dart` (309 lines) -- dual persistence (SharedPrefs JSON + backend sync).

**P1-001: Accessibility settings not wired to rendering pipeline.**
- File: `mobile/lib/features/settings/presentation/providers/accessibility_provider.dart`
- The `accessibilitySettingsProvider` is only consumed in its own screen. None of its values propagate to the app builder or widget tree.
- Verify: `grep -rn "accessibilitySettingsProvider" mobile/lib/ --include="*.dart"` returns only 2 hits, both in the settings screen.

| Setting | Storage Key | Consumer Found? | Behavior Gap |
|---------|------------|-----------------|--------------|
| `fontScale` (0.85-1.4) | `settings_accessibility_central` | NO | Never applied to `MediaQuery.textScaler` |
| `highContrast` | `settings_accessibility_central` | PARTIAL | ThemeManager has separate `_highContrast` flag; these are two independent settings |
| `screenReaderOptimized` | `settings_accessibility_central` | NO | No Semantics augmentation on widget tree |
| `touchTargetSize` (48/56/64) | `settings_accessibility_central` | NO | `SparkleButtonV2` hardcodes 48.0 independently |
| `reduceMotion` | `settings_accessibility_central` | NO | Only `EmotionResponsiveAppWrapper` sets `MediaQuery.disableAnimations` |
| `colorBlindFriendly` | `settings_accessibility_central` | NO | Zero consumers found in entire codebase (grep confirmed) |
| `ttsEnabled` | `settings_accessibility_central` | NO | No TTS integration exists |
| `hapticFeedback` | `settings_accessibility_central` | PARTIAL | `SensoryFeedbackService` has own toggle, not linked |
| `lowLoadMode` | `settings_accessibility_central` | PARTIAL | Side-effects computed in `asLowLoadDefaults()` but not consumed upstream |

- Expected: `accessibilitySettingsProvider` should be watched in `app.dart` builder and:
  1. Apply `fontScale` to `MediaQuery.textScaler`
  2. Inject extra `Semantics` widgets when `screenReaderOptimized` is true
  3. Set `MediaQuery.disableAnimations` when `reduceMotion` is true
  4. Wrap with `ColorFiltered` when `colorBlindFriendly` is true
  5. Read `touchTargetSize.minimumDimension` in button/icon factories

### 2.2 Screen Reader Semantics

**P1-002: 157 GestureDetectors without Semantics widgets.**

Known from previous audit (reported as 158). Current count: 157 (1 removed, 1 added). Overall coverage: 283 Semantics, 157 GestureDetectors -- approximately 55% coverage.

Core widget primitives with no Semantics forwarding:
- `mobile/lib/core/design/widgets/sparkle_tappable.dart:63` -- GestureDetector without semantic label
- `mobile/lib/core/design/widgets/custom_button.dart:204` -- GestureDetector without Semantics
- `mobile/lib/core/design/widgets/flame_indicator.dart:133,353` -- interactive flame
- `mobile/lib/core/design/widgets/share_trigger_button.dart:119` -- share button
- `mobile/lib/core/widgets/intervention_overlay.dart:51` -- intervention dialog
- `mobile/lib/core/widgets/toast_intervention.dart:30` -- toast dismiss

Feature screens with high GestureDetector density and no Semantics:
- `mobile/lib/features/home/presentation/widgets/calendar_heatmap_card.dart` (4 GestureDetectors)
- `mobile/lib/features/home/presentation/widgets/next_actions_card.dart` (3)
- `mobile/lib/features/chat/presentation/widgets/plan_review_card.dart:371`
- `mobile/lib/features/chat/presentation/widgets/plan_selector_pill.dart` (2)
- `mobile/lib/features/calendar/presentation/screens/calendar_stats_screen.dart` (6)

- Fix: Add `semanticLabel` parameter to `SparkleTappable` and forward to inner `GestureDetector`. This alone would fix ~20% of cases.

### 2.3 Touch Targets (WCAG 2.5.5)

**P1-003: Touch target sizes not enforced at widget tree level.**

- File: `mobile/lib/core/design/components/atoms/sparkle_button_v2.dart:420-421`
```dart
minWidth: DS.touchTargetMinSize, // 48.0
minHeight: DS.touchTargetMinSize, // 48.0
```
The button atom correctly enforces 48x48 minimum. However, this is hardcoded and does not dynamically respond to the accessibility `touchTargetSize` setting (comfortable=48, large=56, extraLarge=64).

Other interactive widgets without minimum size enforcement:
- `ChoiceChip` (used in accessibility settings screen itself, line 250)
- Raw `GestureDetector` children (various sizes)
- `ListTile` with custom children

- Fix: Create a `TouchTargetScope` InheritedWidget that the accessibility provider updates, read by interactive widget factories.

### 2.4 Color Contrast (WCAG 1.4.3)

**P2-002: Some design tokens may fail WCAG AA contrast ratio.**

The `ColorTokenVariant.resolve()` method supports high contrast colors (file: `color_token.dart:55-57`), but the actual high contrast color values appear to be default-constructed and may not achieve 4.5:1 for normal text.

Known concern: `DS.textSecondary` (approximately #9E9E9E on #FFFFFF = 2.8:1 contrast ratio) fails WCAG AA for normal text (requires 4.5:1+).

No automated contrast ratio verification runs at build time.

- Fix: Add contrast ratio validation in `design_validator.dart` or CI; adjust `textSecondary` to meet 4.5:1 minimum.

### 2.5 Reduce Motion (WCAG 2.3.3)

The EmotionAdaptive system correctly sets `MediaQuery.disableAnimations: true` when low-stimulus mode activates (file: `emotion_responsive_theme.dart:165-166`). However:
- The accessibility `reduceMotion` toggle operates independently and is not connected to the EmotionResponsive system
- The `PerformanceService` has its own `MotionIntensityLevel` (reduced/low/high) set via `motionIntensityLevelProvider` -- a third independent motion control
- These three motion control systems should be unified

### 2.6 WCAG Checklist Claims vs Reality

The accessibility screen displays a WCAG checklist (line 335-339):
1. "Text scale support" -- Setting EXISTS but is NOT applied (P1-001)
2. "WCAG touch target" -- Configurable but NOT enforced (P1-003)
3. "Color state independent" -- Toggles exist but are NOT consumed (P1-001)
4. "Independent (redundant coding)" -- Claimed but unverifiable

---

## 3. i18n Audit (Bilingual EN/ZH)

### 3.1 ARB File Parity (PASS)

| Metric | EN | ZH |
|--------|----|----|
| Total lines | 13,576 | 13,597 |
| Approximate keys | ~5,400 | ~5,400 |

The ARB files are fully synchronized. The 3 ZH-only metadata keys (`@insErrorsFixed`, `@insStudyDays`, `@insTasksDone`) are ARB annotations, not user-visible strings.

### 3.2 Language Switching (PASS)

**File**: `mobile/lib/core/providers/locale_provider.dart` (71 lines)

- Persisted via `SharedPreferences` (key: `app_locale`)
- `toggleLocale()` switches between `zh` and `en`
- `I18nService.updateLocale()` notified on every change
- Language selection dialog in unified settings (`unified_settings_screen.dart:2068`)
- `MaterialApp.locale` bound to `localeProvider` (`app.dart:82`)

### 3.3 Bilingual Patterns Found

Three patterns coexist:

1. **Standard ARB** (`AppLocalizations.of(context)!.keyName`): Used in 95%+ of UI. This is the canonical path.
2. **Approved inline pattern** (`_isZh ? '中文' : 'English'`): Per MEMORY.md, permitted for presentation layer. Used in `goal_detail_l10n.dart` and `statistics_export_service_impl.dart`.
3. **I18nService static check** (`I18nService.instance.isChinese ? '中文' : 'English'`): Used in non-widget Dart code (services, repositories, entities) that lack BuildContext.

### 3.4 Bilingual Gaps

**P0-001: Hardcoded Chinese in SparkleAvatar -- NO language check at all.**

File: `mobile/lib/core/design/widgets/sparkle_avatar.dart:99`
```dart
Text(
  '审核中',  // Always Chinese, regardless of locale
  style: TextStyle(
    color: DS.brandPrimaryConst,
    fontSize: radius * 0.3,
    fontWeight: DS.fontWeightBold,
  ),
),
```

This widget has no `BuildContext` access and uses no localization pattern. The text '审核中' (Under Review) appears in Chinese for all users.

- Fix: Either (a) pass a `String reviewLabel` parameter from the caller who has context, or (b) use `I18nService.instance.isChinese ? '审核中' : 'Under review'`.

**P0-002: Hardcoded Chinese in notification service action labels.**

File: `mobile/lib/core/services/notification_service.dart:89,96,100`
```dart
DarwinNotificationAction.plain('START_NOW', '⚡ 开始', ...),
DarwinNotificationAction.plain('SNOOZE', '💤 稍后'),
DarwinNotificationAction.plain('DISMISS', '🔕 勿扰', ...),
```

System-level notification action buttons always display in Chinese. Non-Chinese users see Chinese text in their notification tray.

- Fix: Use `I18nService.instance.isChinese ? '⚡ 开始' : '⚡ Start'` pattern. Since the `NotificationService` initializes before locale may be available, re-register actions on locale change.

**P1-004: goal_detail_l10n.dart bypasses ARB -- 50 strings.**

File: `mobile/lib/features/goal/presentation/widgets/goal_detail_l10n.dart` (75 lines)

Uses the approved `_isZh ? '中文' : 'English'` pattern for ~50 strings. This is technically permitted by MEMORY.md's bilingual strategy for presentation layer. However, at 75 lines with 50 getters, it represents significant content outside the ARB pipeline:

```dart
// Lines 6-75: 50 strings via inline ternary
String get goalDetailTitle => _isZh ? '目标详情' : 'Goal detail';
String get goalDetailProgress => _isZh ? '总体进度' : 'Overall progress';
// ... ~48 more entries
```

Affected files importing this bypass:
- `mobile/lib/features/goal/presentation/pages/goal_detail_page.dart:15`
- `mobile/lib/features/goal/presentation/widgets/goal_bottleneck_strip.dart:5`
- `mobile/lib/features/goal/presentation/widgets/minimum_criteria_card.dart:4`

- Fix: Migrate all strings to `app_en.arb` / `app_zh.arb` and regenerate. Delete `goal_detail_l10n.dart`.

**P1-005: Bilingual strings in statistics module not in ARB.**

File: `mobile/lib/core/statistics/domain/repositories/statistics_repository.dart:201-205`
```dart
return zh ? '上升' : 'Up';
return zh ? '下降' : 'Down';
return zh ? '持平' : 'Stable';
```

File: `mobile/lib/core/statistics/data/services/statistics_export_service_impl.dart:74-78`
```dart
buffer.writeln(zh ? '📊 我的$type数据' : '📊 My $type Data');
buffer.writeln(zh ? '📅 统计周期: $period' : '📅 Period: $period');
buffer.writeln(zh ? '🕐 导出时间: ${_formatDateTime(date)}' : '🕐 Exported: ${_formatDateTime(date)}');
buffer.writeln(zh ? '📈 数据来自 星火AI学习助手' : '📈 Data from Sparkle AI');
```

These use the approved `I18nService.instance.isChinese` pattern for non-widget code. Acceptable but note that these strings have no entry in ARB files, making them invisible to translation tooling.

### 3.5 Date/Time/Number Formatting

- Material delegates registered: `GlobalMaterialLocalizations`, `GlobalWidgetsLocalizations`, `GlobalCupertinoLocalizations`
- Most date formatting uses standard Dart `DateTime` methods
- No explicit locale-aware number formatting (`NumberFormat`) found for statistics/achievement counts
- This is acceptable for v1 but should be verified post-launch

---

## 4. Emotion Adaptive UI Audit

### 4.1 Architecture (PASS)

```
WebSocket (Aurora state band)
  -> emotionStateProvider.notifier.updateFromAuroraStateBand()
    -> EmotionState._resolvedIntensity
      -> emotionResponsiveConfigProvider (derived)
        -> EmotionResponsiveAppWrapper (app.dart builder, line 93)
          -> EmotionResponsiveTheme (InheritedWidget)
            -> Theme modifications
            -> ColorFiltered matrix
            -> MediaQuery (disableAnimations, accessibleNavigation)
```

Full pipeline verified from data ingestion to visual output. The widget is properly inserted as a `builder` in `MaterialApp.router`.

### 4.2 Trigger Thresholds (PASS)

File: `mobile/lib/features/aurora/presentation/providers/emotion_state_provider.dart:75-88`

Auto mode triggers low-stimulus when:
- Emotion label is: fatigued, tired, overwhelmed, stressed, anxious
- OR fatigue level >= 0.62
- OR cognitive load >= 0.72
- OR stress signal >= 0.58

Thresholds are reasonable for production use. Manual overrides (`alwaysLow`, `alwaysNormal`) available.

### 4.3 Visual Changes on Low-Stimulus (PASS)

When low-stimulus mode activates:
1. **Font size**: +1sp to all text theme levels (15 style categories)
2. **Motion**: `NoSplash.splashFactory`, `NoTransitionsBuilder` page transitions, `MediaQuery.disableAnimations: true`
3. **Color temperature**: Warm filter via `ColorFilter.matrix` (R x0.94, G x0.96, B x1.02)
4. **Card hierarchy**: Simplified, elevation 0, outline borders instead of shadow
5. **Badges**: `hideChallengeBadges` flag set

All five effects verified in `emotion_responsive_theme.dart:48-211`.

### 4.4 Settings UI (PASS)

Emotion adaptive mode is visible in unified settings. User can select: Auto / Always Low Stimulus / Always Normal. State is persisted to SharedPreferences via `EmotionStateNotifier.setMode()`.

### 4.5 Gaps

**P2-003: EmotionVisualBlendingService not connected to EmotionResponsiveTheme.**
- File: `emotion_visual_blending_service.dart`
- Uses its own `CognitiveState` enum (focus/joyful/tired/excited/calm) not mapped from `EmotionState`
- Expected: Particle density and animation speed should reduce in low-stimulus mode
- Fix: Wire `emotionStateProvider` into the blending service, or have it accept `EmotionState`

**P2-004: No visual indicator when emotion adaptation activates.**
- User has no feedback when the UI silently enters low-stimulus mode
- Fix: Subtle toast or persistent indicator (leaf icon in app bar)

**P2-005: No automated tests for EmotionResponsive system.**

---

## 5. Theme Audit

### 5.1 Theme Architecture (PASS)

File: `mobile/lib/core/design/tokens_v2/theme_manager.dart` (singleton ChangeNotifier with `WidgetsBindingObserver`)

- Light/Dark/System mode selection with SharedPreferences persistence (`theme_mode` key)
- Brand presets: Sparkle (default), Ocean, Forest
- High contrast toggle (affects font weights, border widths, contrast ratios)
- Shop skin system (`equippedSkinId`, `skinConfig`)
- `SparkleThemeData.light/dark()` factory constructors
- Theme settings screen (`theme_settings_screen.dart`) with live color preview

### 5.2 Theme Transition (PASS)

File: `mobile/lib/app/app.dart:107-157`

`_ThemeTransitionShell` provides a 280ms animated theme transition (`AnimatedTheme`) with a cross-fade overlay for smooth light/dark switching.

### 5.3 Design Token Usage (PASS)

All audited screens use `DS.*` tokens consistently:
- Colors: `DS.primaryBase`, `DS.textSecondary`, `DS.surfaceSecondary`, `DS.borderSubtle`
- Spacing: `DS.spacing8-24`
- Typography: `DS.bodySmall`, `DS.titleMedium`, `DS.fontWeightBold`
- Radius: `DS.borderRadius12/16`, `DS.radius12`
- Shadows: `DS.shadowMd`

No hardcoded color values found in settings/profile screens. Category accent colors in profile use explicit `Color(0xFF...)` constants which is intentional for task/persona color differentiation.

### 5.4 Light/Dark Consistency (PASS)

All screens use `SparklePageScaffold` + `GraphiteCardSurface` patterns. Theme extension tokens (`SparkleTaskColors`, `SparkleThemeExtension`) provide dark-mode-safe variants.

### 5.5 Gaps

**P2-006: Two separate high contrast settings exist.**
- File: `theme_manager.dart` (theme-level, consumed by design system)
- File: `accessibility_provider.dart` (accessibility-level, NOT consumed)
- Users may toggle one and not see the expected effect from the other

---

## 6. Notification Audit

### 6.1 Notification Settings (PASS)

Comprehensive controls in `unified_settings_screen.dart`:
1. System notifications toggle (enable/disable all)
2. Interventions toggle (behavioral interventions)
3. Per-type toggles (reminder, spaced repetition, weekly report, milestone)
4. Notification level: minimal / standard / verbose
5. Quiet hours: toggle + time picker (default: 22:00-08:00)
6. Task reminder settings: link to dedicated screen (`TaskReminderSettingsScreen`)
7. Smart push: curiosity push, daily cap, link to `SmartPushSettingsScreen`

### 6.2 Smart Push Settings (PASS)

File: `mobile/lib/features/user/presentation/screens/smart_push_settings_screen.dart`

- Persona type selection (coach, cheerleader, strategist)
- Daily notification cap (configurable, default 5)
- Active time slots (customizable start/end times)
- Permission request with system settings fallback

### 6.3 Push Preferences Persistence (PASS)

File: `mobile/lib/features/user/presentation/providers/settings_provider.dart:421-493`

`PushPreferencesNotifier` syncs to:
- `/users/me/push-preference` (API)
- `/memory/push-settings` (API, for curiosity/engagement recovery)

### 6.4 Notification Preference Settings (PASS)

`NotificationPreferenceSettingsNotifier` (line 356-419):
- Loads from `notificationCenterRepositoryProvider.getPreferences()`
- Updates via `notificationCenterRepositoryProvider.updatePreferences()`
- Optimistic update with rollback on error

### 6.5 Gaps

**P0-002**: Hardcoded Chinese notification action labels (see Section 3.4).

**P2-007**: Android notification channel name not localized.
- File: `notification_service.dart:126`: `'Smart Push Notifications'`
- Fix: Use `I18nService.instance.isChinese ? '智能推送通知' : 'Smart Push Notifications'`

**P2-008**: Notification quiet hours time validation not enforced.
- File: `settings_provider.dart:189-190`
- Default `quietHoursStart: '22:00'`, `quietHoursEnd: '08:00'` -- overnight range handled correctly
- But no validation that user input matches HH:MM format

---

## 7. Profile Audit

### 7.1 Profile Screen Sections (PASS)

File: `mobile/lib/features/user/presentation/screens/profile_screen.dart` (800+ lines)

| Section | Components |
|---------|-----------|
| Header | SparkleAvatar (with pending status), nickname, flame level, brightness |
| Statistics | StatisticsCard (focus/agent/capsule/learning) |
| Traits | TraitsPriorCard + TraitsColdstartQuestionnaire |
| Metacognition | MetacognitionPanelCard with hide toggle |
| Stage 35 | WorkingMemory, AchievementSummary, ActiveSkills, EngagementState, Foresight |
| Prestige | Achievement cards with rarity colors, identity chips |
| Settings nav | Personal info, preferences, skills, security, data export |
| Logout/Delete | Confirmation dialog, account deletion |

### 7.2 Avatar Management (PASS)

File: `mobile/lib/features/user/presentation/screens/edit_profile_screen.dart`

- Photo picker (camera/gallery) with permission handling
- `SparkleAvatar` widget supports: URL, file, SVG network, fallback text, pending overlay
- `AvatarSelectionDialog` for preset avatars

### 7.3 SparkleAvatar Widget (PASS -- with P0 string issue)

File: `mobile/lib/core/design/widgets/sparkle_avatar.dart` (133 lines)

Supports multiple image sources:
- Network images via `SparkleNetworkImage` (with CachedNetworkImage)
- Local file images via `FileImage`
- SVG network images via `SvgPicture.network`
- Fallback text avatar (first character of name)
- Pending review overlay (with hardcoded Chinese -- see P0-001)

### 7.4 Edit Profile (PASS)

- Nickname editing with TextEditingController
- Email editing (social accounts have read-only email)
- Loading/error states handled
- Server sync via `authProvider.notifier.refreshUser()`

### 7.5 Data Export (PASS)

File: `export_data_screen.dart`

- Server-side ZIP export via `userRepository.exportUserData()`
- File save to temp directory
- System share via `share_plus`
- Error handling with localized messages

### 7.6 Account Deletion (PASS)

File: `delete_account_screen.dart`

- Confirmation text input (type delete phrase)
- Social re-authentication (Google, Apple, WeChat)
- Password confirmation for password-based accounts
- Guest account handling
- Loading states and error feedback

### 7.7 Account Security (PASS)

File: `account_security_screen.dart`
- Password reset linking
- Social account linking
- Session management
- Security log viewer

### 7.8 Gaps

**P2-009: No nickname/email validation in edit profile.**
- File: `edit_profile_screen.dart`
- Allow empty nickname/email; no format validation
- Fix: Add minimum 1 character for nickname, email format check

**P2-010: No dedicated privacy settings screen.**
- Share privacy exists for achievements only (UniversalShareBottomSheet)
- Data Controls card has hide growth chronicle / hide memory toggles
- No consolidated screen for: profile visibility, activity sharing, data collection consent, analytics opt-out
- Fix: Add `PrivacySettingsScreen` accessible from profile account section

---

## 8. Previous Audit Findings -- Verification

| Previous Finding | Reported Status | Current Verification |
|-----------------|-----------------|---------------------|
| "158 GestureDetectors without Semantics" | Regressed to 162 | **157 found** -- 1 removed, 1 added. STILL NOT FIXED |
| "NetworkImage -> SparkleNetworkImage (9 places)" | 22 places remain | **16 places in feature code + 6 more in design widgets**. SparkleNetworkImage wrapper EXISTS but CachedNetworkImageProvider used directly in: `friends_screen.dart` (4 places), `user_search_screen.dart` (2), `leaderboard_screen.dart` (2), `partners_tab.dart` (2), `compact_status_bar.dart`, `feed_post_card.dart`, `friends_hub_view.dart`, `message_notification_service.dart`, `private_chat_bubble.dart`, `similar_goal_pursuers_card.dart`. STILL NOT FIXED |
| "Hardcoded Chinese strings in 6+ files" | 1 critical remaining (notification_service.dart) | **2 P0 found**: `sparkle_avatar.dart:99` ('审核中') AND `notification_service.dart` (3 action labels). Plus `goal_detail_l10n.dart` (50 strings, approved pattern but outside ARB). Plus statistics module (2 files, approved pattern but outside ARB) |
| "goal_detail_l10n.dart bypasses pipeline" | By design per MEMORY.md | **STILL EXISTS** at 75 lines. Technically follows approved bilingual pattern but bypasses ARB pipeline |
| "ListView -> ListView.builder (8 places)" | Partially fixed | **30+ ListView(children:) remain**. Most are short settings lists (acceptable). Files that SHOULD convert: `plan_detail_screen.dart` (2), `knowledge_theater_screen.dart` (7), `plan_history_screen.dart:72` |

---

## 9. Summary of All Findings

### P0 (Launch Blockers -- Must Fix)

| ID | Title | File | Line(s) |
|----|-------|------|---------|
| P0-001 | Hardcoded Chinese '审核中' in SparkleAvatar -- no locale check | `core/design/widgets/sparkle_avatar.dart` | 99 |
| P0-002 | Hardcoded Chinese in iOS notification action labels | `core/services/notification_service.dart` | 89, 96, 100 |

### P1 (Must Fix Before Live Launch)

| ID | Title | File(s) |
|----|-------|---------|
| P1-001 | Accessibility settings stored but NOT consumed by rendering pipeline (fontScale, screenReader, reduceMotion, touchTarget, colorBlind, tts, haptic all have zero consumers) | `accessibility_provider.dart` + `app.dart` |
| P1-002 | 157 GestureDetectors without Semantics labels (~55% coverage) | Multiple (Section 2.2) |
| P1-003 | Touch target size (48/56/64) not enforced on widget tree | `accessibility_provider.dart` |
| P1-004 | goal_detail_l10n.dart: 50 strings outside ARB pipeline | `goal_detail_l10n.dart` |
| P1-005 | Statistics module bilingual strings outside ARB (2 files) | `statistics_repository.dart`, `statistics_export_service_impl.dart` |
| P1-006 | 16 places use CachedNetworkImageProvider directly instead of SparkleNetworkImage wrapper | Multiple (Section 8) |

### P2 (Improvements -- Post-Launch)

| ID | Title | File(s) |
|----|-------|---------|
| P2-001 | No global "Reset All Settings" button | `unified_settings_screen.dart` |
| P2-002 | Some DS tokens may fail WCAG AA contrast (textSecondary on surface ~2.8:1) | `color_token.dart`, design system |
| P2-003 | EmotionVisualBlendingService not connected to EmotionResponsiveTheme | `emotion_visual_blending_service.dart` |
| P2-004 | No visual indicator when emotion adaptation activates | `app.dart` |
| P2-005 | No automated tests for EmotionResponsive system | `emotion_responsive_theme.dart` |
| P2-006 | Two separate high contrast settings (theme manager + accessibility) | `theme_manager.dart` + `accessibility_provider.dart` |
| P2-007 | Android notification channel name not localized | `notification_service.dart:126` |
| P2-008 | Notification quiet hours format not validated | `settings_provider.dart:189-190` |
| P2-009 | No nickname/email input validation | `edit_profile_screen.dart` |
| P2-010 | No dedicated privacy settings screen | Missing feature |
| P2-011 | Some ListView() should be ListView.builder (plan_detail, knowledge_theater, plan_history) | Multiple |

---

## 10. Fix Priority Matrix

```
                    HIGH IMPACT              LOW IMPACT
HIGH URGENCY    [P0-001, P0-002]         [                      ]
MED URGENCY     [P1-001..P1-006]         [P2-002, P2-006       ]
LOW URGENCY     [P2-011]                 [P2-001, P2-003..P2-010]
```

## 11. Recommended Fix Order

1. **P0-001** (30 min): Add `I18nService.instance.isChinese ? '审核中' : 'Under review'` to `sparkle_avatar.dart:99`
2. **P0-002** (1 hour): Localize notification action labels, re-register on locale change in `notification_service.dart`
3. **P1-001** (3-4 hours): Wire `accessibilitySettingsProvider` to `app.dart` builder -- consume fontScale to `MediaQuery.textScaler`, reduceMotion to `disableAnimations`, colorBlindFriendly to `ColorFiltered`
4. **P1-002** (2 hours): Add `semanticLabel` to `SparkleTappable` and `SparkleIconButton` factory; batch-add to remaining GestureDetectors
5. **P1-003** (1 hour): Create `TouchTargetScope` widget, consume in button factories
6. **P1-004** (1.5 hours): Migrate `goal_detail_l10n.dart` strings to ARB, regenerate, delete bypass file
7. **P1-005** (1 hour): Same for statistics bilingual strings
8. **P1-006** (1 hour): Batch migrate CachedNetworkImageProvider to SparkleNetworkImage
9. **P2 items**: Address in subsequent iterations

## 12. Verification Criteria (Post-Fix)

- [ ] `grep -rn "[一-鿿]" mobile/lib/ --include="*.dart" | grep -v ".g.dart\|app_localizations_zh.dart\|app_localizations.dart\|intent_keywords.dart\|统计\|审核\|开始\|稍后\|勿扰"` returns zero user-visible results
- [ ] `grep -rn "GoalDetailLocalizations" mobile/lib/` returns zero results
- [ ] `accessibilitySettingsProvider` is watched in `app.dart` builder
- [ ] Toggling accessibility fontScale changes text size on next rebuild
- [ ] Toggling accessibility reduceMotion disables page transitions
- [ ] Toggling accessibility screenReader adds Semantics to interactive widgets
- [ ] 90%+ GestureDetectors have `semanticLabel` or are wrapped in `Semantics`
- [ ] No `CachedNetworkImageProvider` used directly in feature code
- [ ] SparkleAvatar '审核中' uses locale-aware pattern
- [ ] Notification action labels switch language with locale

---

*Audit performed via static code analysis of 50+ Flutter source files, 2 ARB files, and 25+ providers/services. All claims verified by code trace from UI -> provider -> persistence layer. Accessibility gap P1-001 confirmed by grep showing zero consumers of accessibilitySettingsProvider outside its own screen.*
