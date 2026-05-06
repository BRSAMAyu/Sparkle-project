# QA-P3-5: Audit fontSize for Text Scaling

**Status**: ⏭️ skip — not applicable (Flutter framework handles text scaling automatically)
**Date**: 2026-05-06
**Investigated by**: claude-B

## Finding

The QA item was based on the premise that 719 (actually ~1,457) hardcoded `fontSize:` values prevent system text scaling from working. Investigation revealed this premise is incorrect:

- Flutter's `Text` widget **automatically applies** `MediaQuery.textScalerOf(context).scale(fontSize)` to every rendered glyph, regardless of whether fontSize is hardcoded or theme-derived.
- The `MaterialApp.router` in `sparkle_app.dart` does NOT configure a custom `textScaler` (which is correct — the default behavior scales text).
- No `MediaQuery.withNoTextScaling()` wrappers exist that would explicitly disable scaling.

## Real Defect (Separate Concern)

Text does scale, but **layouts were not tested with enlarged text**. The real accessibility issue is layout fragility:

- Fixed-height containers overflow when text scales up
- 1,029 instances of `maxLines`/`ellipsis` truncate scaled text aggressively
- Tight `BoxConstraints` cause clipping

This is a layout testing/robustness issue, not a fontSize configuration issue.

## Recommendation

1. Add CI golden tests at 85%/150%/200% text scale to catch overflow regressions
2. Triage high-traffic screens (dashboard, chat, community feeds) for layout robustness
3. These should be tracked as separate QA items, not as a fontSize audit

## Key Files

- `mobile/lib/core/design/tokens_v2/typography_token.dart` — typography system
- `mobile/lib/core/design/tokens_v2/responsive_system.dart:91` — textScaleFactor helper (used for layout, not font)
- `mobile/lib/sparkle_app.dart` — MaterialApp.router, no custom textScaler (good)
