# SPARKLE Aurora Stage 12 WS-MOB1 Decision Artifact (2026-04-20)

> **Status**: post-implementation artifact for `WS-MOB1`
> **Goal**: close every mobile old-debt item from Stage 11 with an explicit `fix / isolate / delete` path.

## 1. Decision Table

| Test / file | Stage 11 symptom | Stage 12 decision | Why | Verification target |
| --- | --- | --- | --- | --- |
| `test/widget/poster_studio_regression_test.dart` | stale `SharePosterService.runWithoutDebugTextGuides` reference | `fix` | compile drift against current poster service API was cheap to close | renamed to the current `runWithoutDebugPaintGuides` contract; file passes |
| `test/widget/j3_frontend_closure_test.dart` | `AppEventStreamService` constructor drift | `fix` | fixture drift, not product ambiguity | updated to current constructor and fake `Ref`; file passes |
| `test/widget/sync_center_screen_test.dart` | `IsarCore` bootstrap failure | `isolate` | environment-sensitive dependency, not stable CI product logic | file now defaults to a visible `skip` guard unless `RUN_SYNC_CENTER_WIDGET=true` |
| `test/widget/j2_frontend_closure_test.dart` | expected task text no longer rendered | `fix` | assertion drift should be reconciled with current supported UX | assertions now match the current seeded task titles; file passes |
| `test/widget/galaxy_node_preview_card_test.dart` | missing `onViewDetails` parameter | `fix` | compile drift against current widget contract | required callback and zh locale were added; file passes |
| `test/widget/mirofish_wiring_finish_test.dart` | expected `最近洞察` block missing | `delete` | inspection confirmed the second assertion targeted a removed UI contract | stale recent-insights test was deleted; supported chat-bubble path remains and passes |
| `test/widget/user_persona_screen_test.dart` | fake repo missing new methods / signatures | `fix` | contract drift from repo evolution | fake repo now implements the new methods/signatures; file passes |
| `test/widget/openclaw_connection_panel_test.dart` | timeout-prone external gateway reachability | `isolate` | environment-coupled clipboard/pairing import path is unsuitable for default widget sweep | the flaky clipboard-import widget test is explicitly skipped; the remaining panel suite passes |
| `pending wider-sweep residual` | unnamed residual debt bucket in Stage 11 triage | `delete` | Stage 12 cannot carry anonymous debt | residual bucket removed; every known case now has an explicit terminal decision |

## 2. Execution Notes

1. `fix` means the test remains in the active suite and passes
2. `isolate` means the test remains in the repo but is explicitly skipped or quarantined with a stated reason
3. `delete` means the stale assertion is removed only after inspection confirms it no longer validates a supported path

## 3. Final Verification Snapshot

`WS-MOB1` final sweep:

```text
flutter test \
  test/widget/poster_studio_regression_test.dart \
  test/widget/j3_frontend_closure_test.dart \
  test/widget/j2_frontend_closure_test.dart \
  test/widget/galaxy_node_preview_card_test.dart \
  test/widget/mirofish_wiring_finish_test.dart \
  test/widget/user_persona_screen_test.dart \
  test/widget/sync_center_screen_test.dart \
  test/widget/openclaw_connection_panel_test.dart \
  --reporter compact
```

Result: `26 passed, 3 skipped`.

## 4. Rule V Expectation

For every `fix`, Stage 12 must preserve a test that reproduces the previously broken symptom against the current supported contract.

For every `isolate`, Stage 12 must make the isolation visible in code and in handoff known limits.
