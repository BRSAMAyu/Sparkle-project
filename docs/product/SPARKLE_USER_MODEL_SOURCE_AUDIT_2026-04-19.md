# SPARKLE User Model Source Audit (2026-04-19)

> **Status**: Stage 6 `WS-M1a` source inventory baseline
> **Purpose**: record the current code reality of the user-model pipeline in terms of `M1-M5`, the layered architecture lanes, the render-leak choke point, and the concrete Stage 6 boundaries that follow from those facts.
> **Scope**: inventory only. No refactor plan is implicit beyond the Stage 6 boundary calls listed below.

---

## 1. Executive Summary

Sparkle's user-model pipeline is already real, not theoretical.

The repository already contains a canonical path:

- `ProfileContextService`
- `UserInsightCompiler`
- `UserInsightState`
- `UserInsightCalibrationService`
- `UserInsightTransparencyService`

Together these form a substantial `L1` profile/fact pipeline with typed state, calibration, and a transparency surface. The main structural weakness is not "missing architecture" but "last-mile leakage":

- `format_user_context()` / `_normalize_user_context()` still normalize from raw context dictionaries
- the prompt render path does not consume `UserInsightState` as the primary source
- the `SituationBrief` path compiles a separate `CompiledInsightState`, which creates a dual-path reality

The inline-tier concept is also not yet real:

- no bounded inline snapshot
- no dedicated inline cache
- no hot-signal refresh boundary
- no strict token budget discipline

User correction on the backend is materially implemented, but the UI-side closure is still only partially verified.

The Stage 6 implication is direct:

- `WS-M1b` should strengthen projection quality and source discipline
- `WS-RP1` must fix render leakage first
- `WS-V1` should harden the transparency/correction loop
- `WS-E1` should turn calibration/prediction into evaluable surfaces
- `WS-VR1` should close the intervention verification loop

---

## 2. M1-M5 Inventory

| Module | Current code reality | Completeness estimate | Key anchors | Main gap | Recommended Stage 6 home |
| --- | --- | --- | --- | --- | --- |
| `M1` source inventory / raw evidence | `UserInsightCompiler` reads 7+ evidence families: error, mastery, achievement, calendar, workflow, content/capsule, accountability. `ProfileContextService` aggregates preferences, knowledge, cognitive, and error payloads into `ProfileContext`. | ~70% | [user_insight_compiler.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_insight_compiler.py), [profile_context_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/profile_context_service.py) | No structured source-coverage registry. Motivation patterns / anti-patterns / cognitive tendencies are undercompiled. No explicit data-quality checks on freshness/completeness. | `WS-M1b` |
| `M2` typed canonical snapshot | `UserInsightState` is already a large typed state with goals, constraints, readiness, pain points, wins, stable preferences, current state, bottlenecks, contradictions, hypotheses, temporal patterns, predictions, calibration, uncertainty, freshness, confidence, and signal evidence. | ~85% | [user_insight_state.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/core/user_insight_state.py) | `to_prompt_context()` is too raw; prompt/render does not consume the canonical state directly; no bounded inline projection existed before `WS-RP1`. | `WS-RP1` |
| `M3` multi-span analysis / predictions | `UserInsightAnalysisService` and `InsightPredictionService` already provide multi-span analysis, contradiction handling, and seven prediction vectors. | ~75% | [user_insight_analysis_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_insight_analysis_service.py), [insight_prediction_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/insight_prediction_service.py) | No explicit inference-layer governance boundary, no evaluation skeleton, and no clean outcome-based validation of prediction quality. | `WS-E1` |
| `M4` calibration / aging | `UserInsightCalibrationService` already performs signal demotion, hypothesis promotion/demotion, evidence aging, effective-signal pruning, and prediction calibration using `MemoryCorrection` and `InterventionStrategyOutcome`. | ~80% | [user_insight_calibration_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_insight_calibration_service.py) | Aging is still coarse-grained; calibration posture is not yet wired into Aurora parameter control; quality and evaluation are not yet formalized. | `WS-M1b` quality review + `WS-E1` |
| `M5` transparency / user correction | `UserInsightTransparencyService` exposes claims, predictions, unknowns, calibration, and correction controls. Backend transparency endpoints already exist and correction records are consumed in calibration. | ~60% | [user_insight_transparency_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_insight_transparency_service.py), [profile_transparency.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/api/v1/profile_transparency.py) | Flutter/UI consumption path is not yet confirmed end-to-end; correction path must be verified as a real user-facing loop, not only a backend capability. | `WS-V1` |

---

## 3. Layered Architecture Crosswalk

### `L0 Infrastructure`

Evidence already comes from multiple raw-evidence families:

- `CalendarEvent`
- `UserToolHistory`
- `CapsuleFavorite` / `CuriosityCapsule`
- `AccountabilityPartnership` / `AccountabilityCheckin`
- error/mastery records via `ErrorBookService` and `KnowledgeSummary`
- `MemoryCorrection`
- `InterventionStrategyOutcome`

Main gap:

- no structured source-coverage registry
- no explicit gap-discovery mechanism as a first-class infrastructure output

### `L1 Profile System / Fact Layer`

Current canonical path:

- [profile_context_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/profile_context_service.py)
- [user_insight_compiler.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_insight_compiler.py)
- [user_insight_state.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/core/user_insight_state.py)
- [user_insight_calibration_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_insight_calibration_service.py)
- [user_insight_transparency_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_insight_transparency_service.py)

ProfileContext is already cached in Redis, but that does not yet make it a real inline tier. The profile layer is strong enough to harden, not rebuild.

Main gap:

- no strict inline snapshot discipline
- no content-hash or hot-signal cache policy
- prompt path did not consume canonical state directly before `WS-RP1`

### `L2 AI System / Inference Layer`

Current evidence:

- [user_insight_analysis_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_insight_analysis_service.py)
- [insight_prediction_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/insight_prediction_service.py)

The layer exists as code reality, but not yet as a named governance layer.

Main gap:

- inference is still stored back into canonical state instead of governed as an explicit layer
- no profile-aware evaluation framework exists yet

### `L3 Aurora / Control Layer`

Current evidence:

- `SituationBrief` consumes `ProfileTruthCompiler`
- `ProfileTruthCompiler` can coerce `UserInsightState` and project it through `to_legacy_projection()`

But Aurora does not yet maintain a true independent shadow state.

Main gap:

- no explicit control-side shadow model
- no drift protocol between Aurora control state and profile projection
- no white-listed parameter steering surface in code

### `User Correction`

Current evidence:

- backend transparency payloads already exist
- correction records are loaded and applied during calibration
- correction endpoints exist in [profile_transparency.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/api/v1/profile_transparency.py)

Main gap:

- frontend consumption / submission path still needs end-to-end confirmation
- correction impact does not fully reach prompt behavior unless the prompt consumes canonical state

---

## 4. Render-Leak Diagnosis

The main Stage 6 choke point is the render path.

Two compile paths already exist:

1. canonical path  
   `ProfileContextService -> UserInsightCompiler -> UserInsightState`
2. situation-brief path  
   `ProfileTruthCompiler -> CompiledInsightState -> SituationBrief.insight_state`

But the prompt path historically consumed neither as a first-class source.

In [prompts.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/prompts.py):

- `_normalize_user_context()` extracted `error_summary`, `recent_errors`, and `recent_mastery_changes` from raw dict cascades
- there was no canonical-state branch
- `to_legacy_projection()` was not used there

So Sparkle had a real compiled user-model pipeline, but the prompt text often still saw only the weaker pre-compilation view.

This is why `WS-RP1` is the highest-ROI repair item.

---

## 5. Inline-Tier Readiness

Current cache reality:

- `ProfileContextService` caches the full `ProfileContext` in Redis
- the cache TTL is short (`300s`)
- cache validity is preference-version based

Why this is not yet a true inline tier:

- no bounded inline snapshot object
- no dedicated inline snapshot cache key
- no hot-signal refresh boundary
- compile cost still includes multiple DB reads, analysis, prediction, and calibration

Inline-tier readiness therefore remains incomplete until:

1. a bounded inline projection exists
2. a dedicated cache path exists
3. refresh triggers are made explicit
4. render path prefers that bounded projection

`WS-RP1` should solve only the render-side and inline snapshot foundation, not the entire nearline refresh system.

---

## 6. User-Correction Loop Status

### Already real on the backend

- correction records (`MemoryCorrection`)
- correction ingestion into calibration
- hypothesis demotion/promotion via calibration
- transparency payload rendering
- transparency endpoints in [profile_transparency.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/api/v1/profile_transparency.py)

### Not yet fully proven end-to-end

- Flutter reads and renders transparency payload
- Flutter submits correction actions through the intended endpoint path
- next-turn prompt behavior clearly reflects corrected calibration through the canonical prompt path

The backend loop is therefore materially implemented, but the product loop is still not fully verified.

---

## 7. Stage 6 Boundaries

### `WS-M1b` — projection/source-quality hardening

Should own:

- source-coverage registry
- stable-preference population review
- pattern-name quality audit
- anti-pattern / motivation / cognitive tendency data-quality review
- projection-quality improvements that remain inside the profile/fact layer

Should not own:

- prompt render fixes
- UI correction flow
- evaluation harness

### `WS-RP1` — render-pipeline leakage fix

Should own:

- prompt-side canonical-state consumption
- fallback preservation
- inline snapshot foundation
- bounded render discipline

Should not own:

- profile-layer algorithm redesign
- shadow-model design
- intervention-language rewrite

### `WS-V1` — transparency/correction UI hardening

Should own:

- verify existing backend transparency/correction endpoints
- confirm or implement frontend consumption and submission path
- end-to-end correction proof

Should not own:

- profile-layer recompilation logic
- inference evaluation

### `WS-E1` — profile-aware evaluation skeleton

Should own:

- evaluation harness shape
- fixtures
- prediction/calibration validation criteria

Should not own:

- live inference optimization
- production write-path changes

### `WS-VR1` — intervention verification loop

Should own:

- intervention outcome signal closure
- verification field usage
- smallest real demo of `intervention -> outcome -> verification`

Should not own:

- cohort-wide analytics
- full growth-platform redesign

---

## 8. Risks and Unknowns

1. dual compilation path confusion remains real until ownership is made explicit
2. `ProfileTruthCompiler` fallback frequency is still unknown
3. correction UI path is not yet end-to-end verified
4. cognitive pattern-name normalization needs real data-quality inspection
5. cold-start behavior is still thin
6. post-calibration refresh cost may be higher than expected for correction-heavy users
7. some achievement-derived preference signals still need reliability checks

These are not blockers for Stage 6 entry, but they should guide `M1b`, `V1`, and `E1`.

---

## 9. Final M1a Call

The correct Stage 6 interpretation is:

- do **not** build a new user-model subsystem
- do **not** treat the current stack as unfinished theory
- do harden the canonical pipeline that already exists
- do fix the render choke point immediately
- do convert calibration/transparency from backend capability into a verified user-facing loop
