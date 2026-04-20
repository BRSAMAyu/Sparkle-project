# SPARKLE Aurora Stage 11 Mobile Old-Debt Triage (2026-04-20)

> **Status**: Gate S11-0 triage artifact
> **Purpose**: make existing mobile failures explicit before Stage 11 implementation starts.

## 1. Audit Command

```bash
cd mobile && flutter test test/widget/ test/features/user/ --reporter compact
```

Observed broad sweep baseline from prior verification thread:

- `207 passed / 2 skipped / 9 failed`

This artifact records the failures that are already visible and classifies them so Stage 11 does not carry unknown debt into Wave 1.

## 2. Triage Table

| Test / file | Failure type | Cause summary | Classification | Notes |
| --- | --- | --- | --- | --- |
| `test/widget/poster_studio_regression_test.dart` | compile break | stale reference to `SharePosterService.runWithoutDebugTextGuides` | `defer` | pre-existing API drift; not touched by Stage 11 scope |
| `test/widget/j3_frontend_closure_test.dart` | compile break | `AppEventStreamService` constructor signature drift | `defer` | unrelated frontend-closure debt |
| `test/widget/sync_center_screen_test.dart` | environment bootstrap | `IsarError: Could not download IsarCore library` in `setUpAll` | `isolate` | environment-sensitive; keep visible in known limits if skipped |
| `test/widget/j2_frontend_closure_test.dart` | runtime assertion | expected task text not rendered under existing fixture assumptions | `defer` | unrelated task-board regression debt |
| `test/widget/galaxy_node_preview_card_test.dart` | compile break | widget now requires `onViewDetails` named arg | `defer` | existing test fixture drift |
| `test/widget/mirofish_wiring_finish_test.dart` | runtime assertion | expected `最近洞察` card no longer present under old fixture | `defer` | unrelated MiroFish UI debt |
| `test/widget/user_persona_screen_test.dart` | compile break | fake repo missing new `UserRepository` methods and return signatures | `defer` | pre-existing contract drift after Stage 9/10 user repo growth |
| `test/widget/openclaw_connection_panel_test.dart` | long-running / timeout-prone | real local gateway reachability path stalls in widget sweep | `isolate` | external-environment dependent; not touched by Stage 11 scope |
| `pending wider-sweep residual` | residual legacy debt | broad sweep summary reported 9 failures, but two wide-sweep residues are outside Stage 11 touched files and remain in old mobile debt bucket | `defer` | keep explicit until dedicated debt stage or focused repair |

## 3. Operational Interpretation

1. none of the observed failures are caused by Stage 11 entry work
2. none of them block `WS-EVD2 / WS-EV4 / WS-MET2 / WS-CL0`
3. any test moved to `@skip` later must be surfaced in Stage 11 handoff known limits per Rule U and the Stage 11 mobile transparency constraint

## 4. Gate Verdict

Mobile old-debt audit is **known but not yet repaired**.

Stage 11 may proceed because the failures are now classified instead of hidden, but these debts remain outside Stage 11 acceptance unless one is directly touched by a Stage 11 code change.
