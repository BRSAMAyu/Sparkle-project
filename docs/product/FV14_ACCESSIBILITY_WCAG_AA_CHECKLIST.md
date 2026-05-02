# FV14 Accessibility WCAG AA Checklist

Scope: `AccessibilitySettingsScreen` and the central accessibility payload stored in `user_settings.accessibility_settings`.

## Operable

- Minimum touch target starts at 48dp and can be raised to 56dp or 64dp.
- All settings are reachable with standard Flutter focus traversal through `ListTile`, `SwitchListTile`, `Slider`, and `ChoiceChip` controls.
- Motion can be reduced globally through the central `reduce_motion` setting.
- Haptic feedback can be disabled independently from visual or audio feedback.

## Perceivable

- Font scale is centrally configurable from 85% to 140%, with the model clamped to prevent broken layouts.
- High contrast and color-blind-friendly defaults are stored separately so color is not the only state cue.
- Screen reader optimization and TTS are independent controls for spoken access.
- Galaxy accessibility defaults read the central screen reader, motion, contrast, and haptic settings while retaining per-feature overrides.

## Understandable

- The panel groups settings by user task: low-load mode, reading and color, touch and motion, assistive technology, and WCAG checks.
- Low-load mode applies a predictable bundle: reduced motion, screen-reader optimization, larger touch targets, and at least 110% font scale.
- Settings use stable JSON keys under `accessibility_settings` for backend sync and cross-device behavior.

## Robust

- The mobile provider persists locally first, then syncs to `/user/settings`.
- The backend response model returns the same `accessibility_settings` payload it accepts.
- The database migration adds a non-null JSON settings object with an empty-object default for existing users.
- Unit and widget golden coverage exercise normalization, serialization, semantics, and the settings screen render.
