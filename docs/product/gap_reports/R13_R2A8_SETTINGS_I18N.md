# R13 Settings + i18n Independent Audit Report

> **Date**: 2026-05-07 | **Auditor**: Independent (Claude Opus) | **Scope**: Settings + i18n

---

## Summary Table

| Area | Status | P0 | P1 | P2 | Verified Working |
|------|--------|----|----|----|-----------------|
| Settings Structure | GOOD | 0 | 1 | 1 | 10 settings categories with collapsible sections |
| Accessibility Rendering | GOOD | 1 | 1 | 1 | 6/9 settings confirmed wired to rendering |
| i18n Completeness | FAIR | 1 | 2 | 0 | ARB key parity 100%; 673 hardcoded Chinese strings |
| Emotion Adaptive UI | GOOD | 0 | 1 | 0 | Full chain: emotion state -> config -> wrapper -> theme |
| Theme System | GOOD | 0 | 1 | 0 | Light/dark/system + brand presets + skins + persistence |
| Notifications | GOOD | 0 | 0 | 2 | Levels + daily cap + task reminders + push prefs |
| Profile Settings | FAIR | 0 | 1 | 1 | Avatar + nickname + email; no bio/privacy controls |
| Edge Cases | FAIR | 0 | 1 | 1 | Reset all exists; no cross-device sync |

**Total: 1 P0, 8 P1, 6 P2**

---

## P0 Findings

### P0-01: Accessibility hapticFeedback setting NOT wired to SensoryFeedbackService

**File**: `mobile/lib/features/settings/presentation/providers/accessibility_provider.dart:93`
**File**: `mobile/lib/core/services/sensory_feedback_service.dart:174`

The accessibility `hapticFeedback` toggle in AccessibilitySettingsScreen writes to `settings_accessibility_central` in SharedPreferences and syncs to server, but **SensoryFeedbackService reads from a separate key** `sensory_feedback.haptic_enabled`. These are two completely independent storage paths.

- Accessibility toggle writes: `haptic_feedback` key inside the `settings_accessibility_central` JSON blob
- SensoryFeedbackService reads: `sensory_feedback.haptic_enabled` as a standalone boolean in SharedPreferences
- **Result**: Toggling hapticFeedback in accessibility settings does NOT change whether haptic feedback fires through SensoryFeedbackService. The Unified Settings screen's "Sensory Feedback > Haptic" toggle (which calls `SensoryFeedbackService.setHapticEnabled`) controls the actual behavior, but the Accessibility Settings screen's haptic toggle is disconnected.

**Impact**: User disables haptic in Accessibility Settings, haptic still fires everywhere.

---

## P1 Findings

### P1-01: TtsService provider is unused -- TTS enabled setting has no effect

**File**: `mobile/lib/core/services/tts_service.dart:40-44`
**File**: `mobile/lib/features/tools/presentation/widgets/breathing_tool.dart:171`

The `ttsServiceProvider` correctly watches `accessibilitySettingsProvider.ttsEnabled` and creates a `TtsService(enabled: false/true)`, but **no consumer in the app calls `ttsServiceProvider`**. The only code that uses TTS is `breathing_tool.dart`, which creates its own `FlutterTts()` instance directly, completely bypassing the accessibility setting.

**Impact**: Toggling ttsEnabled in accessibility settings has no observable effect.

### P1-02: colorBlindFriendly mode uses high-contrast colors, not color-blind specific palette

**File**: `mobile/lib/core/design/tokens_v2/theme_manager.dart:47`

```dart
final useHighContrast = _highContrast || _colorBlindFriendly;
```

`colorBlindFriendly` routes directly into the `highContrast` rendering path. There is no deuteranopia/protanopia/tritanopia-specific color mapping. The setting name suggests color-blind accommodation, but the implementation is just high-contrast mode by another name.

**Impact**: Color-blind users may not get meaningful accommodation beyond contrast boost.

### P1-03: 673 hardcoded Chinese strings in presentation layer not using ARB l10n

**Files**: Multiple files across features/*/presentation/

While many strings use the `_copy(zh:, en:)` or `_t(zh:, en:)` pattern for bilingual support (which works correctly via `I18nService.instance.isChinese`), these strings bypass the ARB localization system entirely. This means:
- They cannot be found/grepped by the standard l10n tooling
- They cannot be managed by translators via ARB files
- Any future third-language support requires touching source code

Major contributors:
- `chat_bubble.dart`: ~30+ Chinese strings for intent detection keywords, UI labels
- `aurora_receipt_chip.dart`: ~25+ strings via `_copy()` pattern
- `calendar_stats_screen.dart`: ~15+ inline `zh ? '...' : '...'`
- `legal_document_screen.dart`: Full legal text inline

**Impact**: i18n maintenance burden; ARB-based tooling cannot manage these strings.

### P1-04: AmbientScene labels hardcoded in Chinese only

**File**: `mobile/lib/core/services/sensory_feedback_service.dart` (AmbientSceneLabel extension)

```dart
String get label => switch (this) {
    AmbientScene.none => '无背景音',
    AmbientScene.rain => '雨声',
    AmbientScene.ocean => '海浪',
    AmbientScene.whiteNoise => '白噪音',
    AmbientScene.cafe => '咖啡馆',
    AmbientScene.piano => '轻钢琴',
};
```

These labels appear in the Settings screen's ambient scene selector. When language is English, these still show Chinese characters.

**Impact**: English-language users see Chinese text in ambient scene selector.

### P1-05: Emotion Adaptive UI has no user-visible indicator or explanation

**File**: `mobile/lib/features/aurora/presentation/providers/emotion_state_provider.dart`
**File**: `mobile/lib/core/design/adaptive/emotion_responsive_theme.dart`

The Emotion Adaptive UI system works well technically: when fatigue >= 0.62 or cognitive load >= 0.72, the entire app switches to low-stimulus mode (dimmer colors, +1px font size boost, no animations, simplified cards). However:
- The user has no visible indicator that this mode is active
- The settings screen only exposes the mode toggle (auto/alwaysLow/alwaysNormal) without explaining what changes
- There is no way for the user to preview the difference

**Impact**: User experience changes silently without explanation.

### P1-06: Reset All Settings dialog strings not in ARB

**File**: `mobile/lib/features/user/presentation/screens/unified_settings_screen.dart:1971,2084-2109`

The "Reset All Settings" button and confirmation dialog use inline `zh ? '...' : '...'` pattern instead of ARB keys. The button label at line 1971 is a raw Chinese string `'重置所有设置'` with no English fallback visible in the ternary pattern.

### P1-07: No privacy/visibility settings for user profile

No privacy settings found in the user feature. Users cannot control:
- Whether their profile is visible to other users
- What information is shared in the community
- Whether achievements are publicly visible

The `share_privacy_settings.dart` widget exists for achievement sharing, but there is no general profile privacy control.

### P1-08: Bio/description field not editable in EditProfileScreen

**File**: `mobile/lib/features/user/presentation/screens/edit_profile_screen.dart`

The edit profile screen only supports:
- Nickname (with empty-check validation)
- Email (with regex validation)
- Avatar (from presets, camera, or gallery)

There is no bio/description field. No `bio` or `description` field in the save payload.

---

## P2 Findings

### P2-01: ThemeManager has fragile custom JSON parser instead of dart:convert

**File**: `mobile/lib/core/design/tokens_v2/theme_manager.dart:283-309`

The `_parseSimpleJson` method is a hand-rolled JSON parser that splits on commas and colons. It has known limitations:
- Cannot handle nested objects
- Cannot handle values containing commas or colons
- The comment says "should use dart:convert" but doesn't
- `dart:convert` is not even imported

The `_stringifySimpleJson` method works correctly for simple key-value and array configs, so this is not currently broken, but it is fragile for future skin configurations.

### P2-02: Notification settings lack quiet hours UI in unified settings

**File**: `mobile/lib/features/memory/presentation/screens/memory_settings_screen.dart:83-84`

Quiet hours data model exists (`quietHoursStart`/`quietHoursEnd` with defaults "22:00"/"08:00") and is configurable in the memory settings screen, but the unified settings screen's notification section does not expose quiet hours configuration.

### P2-03: screenReaderOptimized only sets accessibleNavigation flag -- limited Semantics coverage

**File**: `mobile/lib/app/app.dart:114`

The `screenReaderOptimized` accessibility setting sets `MediaQuery.accessibleNavigation`, but does not:
- Add Semantics labels to widgets that lack them
- Enable/disable semantic debugging
- Adjust any widget behavior based on screen reader state

Only `GalaxyAccessibilityService` checks this flag for galaxy-specific node descriptions.

### P2-04: Settings sync across devices only via server -- no real-time sync

Accessibility settings sync to server via `userRepository.updateUserSettings()`, but there is no real-time push notification to update settings on other devices when they change. If user changes settings on device A, device B keeps old settings until next `_syncFromServer()` on provider initialization.

### P2-05: TTS language hardcoded to 'en-US' in TtsService

**File**: `mobile/lib/core/services/tts_service.dart:14`

```dart
unawaited(_tts!.setLanguage('en-US'));
```

TtsService hardcodes English, while breathing_tool.dart uses `zh-CN`. Neither respects the current locale setting.

### P2-06: touchTargetSize only applied to SparkleButtonV2, not globally

**File**: `mobile/lib/core/design/components/atoms/sparkle_button_v2.dart:398-400`

The `minimumTouchTargetSize` from accessibility settings is only consumed in `SparkleButtonV2`. Other interactive elements (ListTiles, SwitchListTiles, ChoiceChips, IconButtons, etc.) throughout the app do not respect this setting.

---

## Verified Working

### Settings Structure (10 categories in UnifiedSettingsScreen)
1. **Sensory Feedback**: Sound, haptic, Aurora link, ambient scene + volume -- all functional, persisted via SensoryFeedbackService
2. **Accessibility**: Sub-screen with Reading (fontScale, highContrast, colorBlindFriendly), Interaction (touchTargetSize, reduceMotion, hapticFeedback), Assistive Tech (screenReaderOptimized, ttsEnabled), Low Load mode
3. **Learning Mode**: Depth + curiosity sliders, capsule generation preview, weekly agenda
4. **BGM**: Enabled, volume, palette (5 options), mode (4 options), intensity, variety, reading protection, focus priority, style lock -- all persisted via BgmService
5. **Theme & AI**: Theme mode (system/light/dark), enter-to-send, AI reasoning mode, chat context/prediction/transparency toggles, chat pure mode, motion intensity, AI usage dashboard
6. **Aurora Preferences**: Analysis depth, signal routing -- persisted via auroraPreferencesProvider
7. **Notifications**: Level (minimal/standard/verbose), behavior explanation card, task reminders
8. **Visual Elements**: Links to visual elements route
9. **Study Materials**: Links to document library
10. **Data Controls**: Growth chronicle visibility, memory panel visibility

### Accessibility Rendering (verified wired)
- **fontScale**: `app.dart:105-106` -> `MediaQuery.textScaler = TextScaler.linear(fontScale)` -- CONFIRMED
- **reduceMotion**: `app.dart:111-112` -> `MediaQuery.disableAnimations = reduceMotion` -- CONFIRMED
- **colorBlindFriendly**: `app.dart:235-236` -> `ThemeManager.setColorBlindMode()` -> affects `SparkleColors.light/dark(highContrast:)` -- CONFIRMED (but same as high contrast)
- **highContrast**: `app.dart:232-233` -> `ThemeManager.toggleHighContrast()` -> affects `SparkleColors` -- CONFIRMED
- **screenReaderOptimized**: `app.dart:114` -> `MediaQuery.accessibleNavigation` -- CONFIRMED
- **touchTargetSize**: `sparkle_button_v2.dart:398-400` -> minimumSize constraint -- CONFIRMED (limited scope)

### ARB Completeness
- EN ARB: 9,194 keys
- ZH ARB: 9,194 keys
- **100% key parity** between EN and ZH files
- Both files ~13,600 lines each

### Theme System
- Light/dark/system toggle: Works via `ThemeManager.setAppThemeMode()` -> `MaterialApp.themeMode`
- System theme following: `ThemeManager.didChangePlatformBrightness()` triggers `notifyListeners()`
- Theme persistence: SharedPreferences via `_saveToPrefs()` on every change
- Brand presets: sparkle/ocean/forest with distinct color palettes
- Shop skins: equip/unequip with color customization
- ThemeManager is a singleton that survives app lifecycle

### Emotion Adaptive UI Chain
- Backend Aurora -> `EmotionStateNotifier.updateFromAuroraStateBand()` -> `EmotionState` model
- Thresholds: fatigue >= 0.62, cognitiveLoad >= 0.72, stressSignal >= 0.58
- Low-stimulus mode: `EmotionResponsiveAppWrapper` applies:
  - +1px font size boost across all TextStyles
  - Color temperature dimming via ColorFiltered matrix (warm dim light, cool dim dark)
  - No page transitions (NoTransitionsBuilder)
  - No splash effects
  - Reduced card elevation
  - Challenge badges hidden
- User can override: auto/alwaysLow/alwaysNormal modes
- Settings exposed in unified settings screen

### Notification System
- Push notification toggle: Controlled via `UnifiedPushService`
- Notification categories: 4 type groups (reminder, spaced_repetition, weekly_report, milestone) with aliases
- Daily cap: Configurable in smart push settings
- Task reminders: Configurable time slots via TaskReminderConfig
- Quiet hours: Data model exists in memory settings (22:00-08:00 default)

### Profile Settings
- Avatar change: 3 sources (presets, camera, gallery) with permission handling
- Username/nickname change: Editable with empty-string validation
- Email change: Editable with regex validation
- Email verification: Send code + verify flow

### Settings Persistence
- All settings persisted locally via SharedPreferences
- Accessibility settings also synced to server via `userRepository.updateUserSettings()`
- Theme mode persisted separately in SharedPreferences
- Reset all settings: Exists in unified settings with confirmation dialog
