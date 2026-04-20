# SPARKLE Aurora Stage 12 WS-MOB1 Decision Artifact (2026-04-20)

> **Status**: pre-implementation artifact for `WS-MOB1`
> **Goal**: close every mobile old-debt item from Stage 11 with an explicit `fix / isolate / delete` path.

## 1. Decision Table

| Test / file | Stage 11 symptom | Stage 12 decision | Why | Verification target |
| --- | --- | --- | --- | --- |
| `test/widget/poster_studio_regression_test.dart` | stale `SharePosterService.runWithoutDebugTextGuides` reference | `fix` | compile drift against current poster service API is cheap to close | test compiles and passes with current service contract |
| `test/widget/j3_frontend_closure_test.dart` | `AppEventStreamService` constructor drift | `fix` | fixture drift, not product ambiguity | test updated to current constructor and passes |
| `test/widget/sync_center_screen_test.dart` | `IsarCore` bootstrap failure | `isolate` | environment-sensitive dependency, not stable CI product logic | explicit skip / isolate annotation plus known-limit note |
| `test/widget/j2_frontend_closure_test.dart` | expected task text no longer rendered | `fix` | assertion drift should be reconciled with current supported UX | updated assertion or fixture passes |
| `test/widget/galaxy_node_preview_card_test.dart` | missing `onViewDetails` parameter | `fix` | compile drift against current widget contract | test updated and passes |
| `test/widget/mirofish_wiring_finish_test.dart` | expected `最近洞察` block missing | `delete` | likely stale acceptance of a no-longer-supported UI contract; if inspection disproves this, downgrade to `fix` before code lands | file removed or replaced by a narrower supported-path test |
| `test/widget/user_persona_screen_test.dart` | fake repo missing new methods / signatures | `fix` | contract drift from repo evolution | fake repo updated, test passes |
| `test/widget/openclaw_connection_panel_test.dart` | timeout-prone external gateway reachability | `isolate` | environment-coupled and unsuitable for default widget sweep | explicit skip / isolate annotation plus known-limit note |
| `pending wider-sweep residual` | unnamed residual debt bucket in Stage 11 triage | `delete` | Stage 12 cannot carry anonymous debt; the bucket must resolve into named cases or disappear | no residual bucket remains in updated artifact / handoff |

## 2. Execution Notes

1. `fix` means the test remains in the active suite and passes
2. `isolate` means the test remains in the repo but is explicitly skipped or quarantined with a stated reason
3. `delete` means the file is removed only if inspection confirms it no longer validates a supported path

## 3. Rule V Expectation

For every `fix`, Stage 12 must preserve a test that reproduces the previously broken symptom against the current supported contract.

For every `isolate`, Stage 12 must make the isolation visible in code and in handoff known limits.
