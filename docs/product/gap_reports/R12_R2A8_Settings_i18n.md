# R12 / R2A8 — Settings_i18n 二次深度审查
**Date**: 2024-05-24 (Current Audit)
**Scope**: Settings + i18n
**Layers**: Flutter → Go Gateway → Python Engine → PostgreSQL / Redis
**Vision check**: Checked against accessibility, i18n, and emotional adaptive UI connection requirements.

---

## Summary
| Category | Count |
|----------|-------|
| P0 (must-fix before launch) | 2 |
| P1 (important gap, ship with plan) | 2 |
| P2 (nice to have, post-launch) | 0 |
| Verified working | 2 |

---

## R11 P0 验证
N/A - Initial deep dive.

---

## P0 Findings (Must Fix Before Launch)

### P0-1: Accessibility Settings Disconnected from Render Pipeline
**File**: `mobile/lib/features/settings/presentation/providers/accessibility_provider.dart`
**Lines**: Various
**Problem**: 9 accessibility settings are declared and saved to local/backend storage, but most are disconnected from the application's render pipeline. Specifically, `touchTargetSize`, `colorBlindFriendly`, `screenReaderOptimized`, `ttsEnabled`, and `lowLoadMode` are never read by the Flutter widget tree to alter dimensions, padding, or semantic logic. 
**Evidence**: Searching for `touchTargetSize` usage shows it is only read by `_TouchPreview` inside the settings screen itself. Searching for `colorBlindFriendly` shows it is never used anywhere in the codebase to adjust colors.
**Expected**: The entire app should react to these accessibility settings. E.g., `touchTargetSize` should influence a global padding/sizing multiplier in the Design System. E.g., `colorBlindFriendly` should swap out SemanticColors palettes.
**Fix recommendation**: Create a global `AccessibilityFeatures` InheritedWidget or expose these variables through the Design System (`DS`) or `ThemeManager` so that all interactive widgets respect the configured `touchTargetSize` and `colorBlindFriendly` palettes.

### P0-2: Dual Source of Truth for High Contrast 
**File**: `mobile/lib/features/settings/presentation/screens/accessibility_settings_screen.dart`
**Lines**: 74-75
**Problem**: The Accessibility Settings screen toggles `highContrast` via `accessibilitySettingsProvider` which saves to `settings_accessibility_central`. However, the app's theme actually relies on `ThemeManager().highContrast` which reads from a separate `high_contrast` SharedPreferences key. Toggling high contrast in the Accessibility settings screen does NOT update the app's theme.
**Evidence**: `AccessibilitySettingsNotifier.patch(highContrast: value)` only updates its internal state. `ThemeManager().toggleHighContrast` is never called.
**Expected**: Toggling high contrast in Accessibility Settings should instantly reflect in the app theme.
**Fix recommendation**: Have `AccessibilitySettingsNotifier` call `ThemeManager().toggleHighContrast(value)` when the value changes, or refactor `ThemeManager` to listen to `accessibilitySettingsProvider` as the single source of truth.

---

## P1 Findings (Important, Ship With Plan)

### P1-1: Hardcoded Chinese Strings and Manual Locale Check in SparkleAvatar
**File**: `mobile/lib/core/design/widgets/sparkle_avatar.dart`
**Lines**: 9-12
**Problem**: `SparkleAvatar` uses a hardcoded manual check for the Chinese locale instead of utilizing the generated `AppLocalizations` ARB files.
**Evidence**: 
```dart
String _avatarPendingLabel(BuildContext context) {
  final zh = Localizations.localeOf(context).languageCode == 'zh';
  return zh ? '审核中' : 'Under Review';
}
```
**Expected**: Should use standard `context.l10n.avatarUnderReview` defined in `app_en.arb` and `app_zh.arb`.
**Fix recommendation**: Add `avatarUnderReview` to the ARB files and replace the manual string logic in `SparkleAvatar`.

### P1-2: iOS Info.plist Missing i18n Localization for Permissions
**File**: `mobile/ios/Runner/Info.plist`
**Lines**: 66-77
**Problem**: iOS permission descriptions (e.g., `NSCameraUsageDescription`, `NSUserNotificationsUsageDescription`) are hardcoded in Chinese directly in `Info.plist`. There is no `InfoPlist.strings` provided for English.
**Evidence**: `<key>NSUserNotificationsUsageDescription</key><string>需要通知权限以发送任务提醒、学习计划进度和重要消息</string>`
**Expected**: iOS should prompt English users with English explanations for camera, microphone, and notification permissions.
**Fix recommendation**: Create `InfoPlist.strings` files for both `en` and `zh` inside `mobile/ios/Runner/` and map the keys appropriately.

---

## P2 Findings (Post-Launch)
None at this time.

---

## Verified Working (Strengths)

### V-1: Emotion Adaptive UI Full Chain
- **Verification**: Traced from `websocket_chat_service_v2.dart` receiving the `aurora_state_band` event, which correctly updates `EmotionStateProvider`. The `EmotionStateProvider` exposes `responsiveConfig` to `EmotionResponsiveAppWrapper`, successfully bridging the backend emotion analysis to the Flutter render pipeline and color temperature shifts.
- **Verdict**: Fully Connected and Working.

### V-2: i18n Language Switch Propagation
- **Verification**: `localeProvider` controls `MaterialApp.router(locale: ...)`. Modifying the language in settings updates the locale provider, causing the root app widget to rebuild. Nearly all widgets use `context.l10n` (which maps to `AppLocalizations.of(context)`) directly inside their `build` methods, preventing any text caching issues.
- **Verdict**: Fully Connected and Working.

---

## Cross-Route Integration Issues
None identified outside of the disconnected Accessibility settings mentioned in P0.

---

## Code Quality Observations
- The use of `context.l10n` extension is excellent and widespread, reducing boilerplate. 
- Overall separation of `UnifiedSettingsScreen` and `AccessibilitySettingsScreen` is clean, but the connection between `providers` and `ThemeManager`/`DesignSystem` needs tighter integration to enforce actual UI changes rather than just saving JSON to a backend.