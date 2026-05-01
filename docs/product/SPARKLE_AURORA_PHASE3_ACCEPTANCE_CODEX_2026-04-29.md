# Sparkle Aurora Phase 3 Codex Acceptance Review (2026-04-29)

> Auditor: Codex
> Scope: commits after `42449df2` through `f8bb193e`, plus current uncommitted Aurora / Spine / mobile draft changes observed on 2026-04-29.
> Posture: reviewer + acceptance owner + product/architecture designer.

## Verdict

Phase 3.1 through Phase 3.3 are provisionally accepted at backend-runtime level: the committed Aurora suites pass locally.

T3.4 is not accepted yet. The backend draft has useful pieces, but the user-visible and production-routing paths are not closed enough to mark "状态带 6 态统一 + 用户偏好完成" as final.

The tracker should treat T3.4 as `needs-fix / needs-reacceptance` until the findings below are closed.

## Evidence Run

| Check | Result |
|---|---|
| `pytest tests/unit/test_t311_l0_rules.py ... test_t33_predicted_reply_correction.py test_d01_notification_fatigue.py test_d02_photon_spine.py -q` | 223 passed, 11 warnings |
| `pytest tests/unit/test_t34_status_band_preferences.py -q` | 35 passed, 2 warnings |
| `pytest tests/unit/test_spine_event_bridge.py -q` | 9 passed |
| `go test ./internal/service -run TestChatHistoryServiceRequiresCanonicalOwnerAcrossReconnect -count=1` | passed |
| `ruff check app/api/v1/aurora.py app/orchestration/dual_core_router.py app/signals/spine_orchestrator.py app/aurora/runtime_v1/user_preferences.py tests/unit/test_t34_status_band_preferences.py` | failed; mostly existing `spine_orchestrator.py` debt, plus T3.4 test/import hygiene |

## Acceptance Findings

### AUR-P3-ACCEPT-01 — T3.4.4 user preferences are not wired into the production routing path

Severity: P1

`DualCoreRouter` now consumes `routing_input.aurora_preferences`, but `RoutingEngine._build_dual_core_input()` still constructs `DualCoreRoutingInput` without reading or passing those preferences. Evidence:

- `backend/app/orchestration/dual_core_router.py:422` reads `routing_input.aurora_preferences`
- `backend/app/orchestration/routing_engine.py:714` returns `DualCoreRoutingInput(...)` without `aurora_preferences=...`

Impact: the API can save preferences and router unit tests can pass with hand-built inputs, but real chat/orchestration turns will still feel like the default `guided / motivating / detailed / deep` profile. This directly violates T3.4.4's user promise: "少分析我 / 直接安排我 / 多解释原因 / 不用压力提醒".

Required fix: add a non-fatal `RoutingEngine` preference loader backed by `AuroraUserPreferencesService`, pass the normalized dict into `DualCoreRoutingInput`, and add an integration test around `_build_dual_core_input()`.

### AUR-P3-ACCEPT-02 — The 6-state status band is not actually the dashboard/user-visible status band

Severity: P1

Backend draft returns `band_status`, `band_label`, `band_summary`, `correction_options`, and cooldown fields. However Flutter dashboard still resolves the band from local dashboard sprint state and never calls `/aurora/spine/status-band`.

Evidence:

- `backend/app/api/v1/aurora.py:599` exposes `/aurora/spine/status-band`
- `mobile/lib/core/network/api_endpoints.dart:218` defines `auroraSpineStatusBand`
- `mobile/lib/features/home/presentation/screens/dashboard_screen.dart:80` derives `AuroraBandState` locally from `DashboardState`
- `mobile/lib/features/home/presentation/widgets/aurora_status_band.dart:148` lacks `sensing`, `calibrationAvailable`, and `coolingDown`

Impact: T3.4.1/T3.4.2 are only backend contract work right now. The actual first-screen status band remains decorative and heuristic, which conflicts with Roadmap v3's acceptance text: "状态带非装饰品, 用户可交互".

Required fix: add a mobile repository/provider/model for `/aurora/spine/status-band`, map all six backend states, render cooldown and correction affordances, and keep a safe fallback only when the endpoint fails.

### AUR-P3-ACCEPT-03 — T3.4.2 "current judgment + evidence + correctable options" is under-specified

Severity: P2

`SpineOrchestrator._build_correction_options()` generates options from `band_status` only, and `band_summary` is built with an empty facet list. Active state entries are not translated into per-judgment evidence or targeted correction metadata.

Evidence:

- `backend/app/signals/spine_orchestrator.py:643` calls `_band_status_summary(band_status, [])`
- `backend/app/signals/spine_orchestrator.py:662` accepts `active_entries`, but the implementation does not use them

Impact: users may see generic correction chips, but they do not see exactly what Aurora believes and why. That is weaker than the vision anchor: Aurora should be felt as calibrated context engineering, not a vague badge.

Required fix: include top active claims with evidence summaries and state keys; emit correction options that carry `target_state_key`, `target_claim`, and `telemetry_id`, then route those through the existing correction feedback pipeline.

### AUR-P3-ACCEPT-04 — Cooldown override needs clearer cost-control semantics

Severity: P2

The status band returns `cooldown_can_override=True` whenever `energy.is_cooling_down`. The label "override" risks implying that L3 can be forced during cooldown, while the cost controller design says cooldown should fall back to quick calibration.

Evidence:

- `backend/app/signals/spine_orchestrator.py:649` checks `energy.is_cooling_down`
- `backend/app/signals/spine_orchestrator.py:654` sets `cooldown_can_override = True`

Required fix: rename or split the contract into `quick_calibration_available` and `l3_wake_allowed`, and only expose an L3 wake entry when quota/cooldown policy allows it.

### AUR-P3-ACCEPT-05 — Tracker regression claims need evidence discipline

Severity: P2

The dirty tracker line claims "35 production-grade tests passed, 2053 spine tests + 287 Aurora tests no regression." I verified 35 T3.4 tests and 223 committed Phase 3 tests locally, but I did not see local evidence for the larger 2053/287 figures in this run.

Required fix: either attach the exact command/output evidence to the tracker, or downgrade the line to "targeted tests passed; full-suite evidence pending".

### AUR-P3-ACCEPT-06 — Test/lint warnings should not be hidden under "production-grade"

Severity: P2

The test suites pass, but there are unawaited coroutine warnings from async mocks. `ruff` also reports active hygiene failures, including duplicate method definitions in `spine_orchestrator.py`. Some of this predates T3.4, but it weakens the "production-grade" claim for the core Aurora/Spine file.

Required fix: clean T3.4 test imports and async mocks immediately; separately schedule a focused `spine_orchestrator.py` duplicate-method cleanup after user-in-progress changes stabilize.

## Positive Acceptance Notes

- T3.1-T3.3 backend runtime coverage is substantial and passed locally.
- T3.4 backend draft preserves the old status-band fields while adding six-state fields, which is the right compatibility direction.
- `AuroraUserPreferencesService` stores only explicit whitelisted preference keys and keeps non-Aurora explicit preferences intact.
- The uncommitted gateway identity canonicalization test passed and looks aligned with session-history ownership safety.
- The uncommitted calendar bridge enhancement passed its focused tests and moves P2-11 in the right direction.

## Next Required Execution Order

1. Close AUR-P3-ACCEPT-01 by wiring saved Aurora preferences into `RoutingEngine._build_dual_core_input()`.
2. Close AUR-P3-ACCEPT-02 by making the dashboard status band consume the real six-state backend contract.
3. Close AUR-P3-ACCEPT-03 by adding evidence-bearing correction options and targeted telemetry.
4. Clarify cooldown contract naming and L3 wake availability.
5. Only then mark T3.4 complete in the tracker and proceed to the next Phase 3/Phase 4 item.

## Workflow Note

The current worktree contains user-in-progress changes. This review intentionally avoids staging or rewriting those files. This document is the Codex audit artifact for the current acceptance pass.
