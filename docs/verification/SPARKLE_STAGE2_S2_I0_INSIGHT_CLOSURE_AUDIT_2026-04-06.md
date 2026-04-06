# Sparkle Stage 2 S2-I0 Insight Closure Audit

**Date**: 2026-04-06  
**Status**: Closed for handoff  
**Scope**: `S2-I0A` source-to-consumer audit, `S2-I0B` prompt leakage repair confirmation, `S2-I0C` telemetry and regression closeout

## 1. Why This Exists

`S2-I0` was the repair pack that turned already-collected profile truth into model-visible and runtime-visible understanding.

This audit freezes the repo truth after the code changes:
- which high-value signals are now live
- where each signal is collected, stored, normalized, rendered, or consumed
- which signals remain runtime-only or not yet user-visible
- which tests protect the pack

This document is intentionally an internal engineering artifact. It is not a public contract.

## 2. S2-I0 Outcome Summary

`S2-I0` is considered complete because the repo now does all of the following:

1. Lifts `error_summary`, `recent_errors`, and `recent_mastery_changes` from `cognitive_context` into normalized prompt context.
2. Renders recent pain-point and recent progress sections into prompt-visible user context.
3. Carries the same pain/win summaries into `situation_brief` so planning layers still see them under prompt pruning.
4. Records internal `prompt_signal_telemetry` that shows collected, normalized, rendered, prompt-visible, and dropped status for the tracked high-value fields.
5. Promotes achievement unlock behavior into durable inferred profile signals through the existing preference write path.
6. Uses focus, achievement, push, density, and recurring calendar signals in deterministic schedule ranking.
7. Persists intervention cohort context so outcome learning can use `goal_type`, `knowledge_level`, and `learning_style`.

## 3. Canonical Signal Map

Status definitions:
- `live`: collected, stored, consumed by AI/runtime, and exposed on an existing transparency surface where applicable
- `partially live`: collected and consumed, but not yet exposed on a dedicated user-facing surface or not prompt-rendered by design
- `still dropped`: collected upstream but still not consumed where the architecture intends

| Signal | Source model/service | Write or storage path | Compiler/context entrypoint | Prompt/runtime consumer | Transparency surface | Status | Behavioral impact |
|---|---|---|---|---|---|---|---|
| `error_summary` | `ErrorBookService.get_review_stats()` via `ContextOrchestrator._get_error_profile()` | `CognitiveContext.error_summary` in `backend/app/core/context_manager.py` | `_normalize_user_context()` in `backend/app/orchestration/prompts.py` lifts from top-level or `cognitive_context` | `format_user_context()` renders `【近期痛点】`; `SituationBriefBuilder` merges into `recent_pain_points` and `freshest_items` | None in current profile transparency API | `partially live` | Sparkle can now name the user's recent error burden and top weak subject cluster in prompt-time reasoning and plan framing. |
| `recent_errors` | `ErrorBookService.list_errors()` via `ContextOrchestrator._get_error_profile()` | `CognitiveContext.recent_errors` in `backend/app/core/context_manager.py` | `_normalize_user_context()` in `backend/app/orchestration/prompts.py` | `format_user_context()` renders capped recent error items; `SituationBriefBuilder` carries them into briefing evidence | None in current profile transparency API | `partially live` | Sparkle can now anchor help in concrete recent mistakes instead of generic weakness language. |
| `recent_mastery_changes` | `ProfileContextService._build_knowledge_summary()` | `ProfileContext.knowledge_summary.recent_mastery_changes`, then `CognitiveContext.recent_mastery_changes` | `_normalize_user_context()` in `backend/app/orchestration/prompts.py` | `format_user_context()` renders `【近期进展】`; `SituationBriefBuilder` carries wins into summary and evidence | None in current profile transparency API | `partially live` | Sparkle can now recognize and reinforce recent growth moments while planning the next move. |
| `achievement_peak_hours` | `AchievementEventConsumer._refresh_achievement_profile_signals()` from recent `UserAchievement` rows | `UserPreferencesCenter.inferred["achievement_peak_hours"]` via `ProfileWriteService.update_inferred_preference()` | `PreferenceService.get_preferences()` -> personalization/schedule runtime | `SmartScheduleService._resolve_focus_hours()` uses it as fallback when `peak_focus_hours` is weak or absent | `profile_transparency` inferred labels and explanations | `live` | Scheduling can now bias suggestions toward hours that historically produce achievement momentum when stronger focus evidence is unavailable. |
| `achievement_motivation_response` | `AchievementEventConsumer._refresh_achievement_profile_signals()` | `UserPreferencesCenter.inferred["achievement_motivation_response"]` | `PreferenceService.get_preferences()` -> personalization runtime | `PersonalizationEngine.get_llm_profile()` tunes reinforcement framing | `profile_transparency` inferred labels and explanations | `live` | Sparkle can now choose whether to lead with progress praise, mastery framing, or milestone framing when motivating the user. |
| `achievement_pace_style` | `AchievementEventConsumer._refresh_achievement_profile_signals()` | `UserPreferencesCenter.inferred["achievement_pace_style"]` | `PreferenceService.get_preferences()` -> personalization runtime | `PersonalizationEngine.get_llm_profile()` adjusts suggestion pacing language | `profile_transparency` inferred labels and explanations | `live` | Sparkle can now frame next steps as steady accumulation or short sprint blocks based on actual unlock patterns. |
| `achievement_reward_sensitivity` | `AchievementEventConsumer._refresh_achievement_profile_signals()` | `UserPreferencesCenter.inferred["achievement_reward_sensitivity"]` | `PreferenceService.get_preferences()` -> personalization runtime | `PersonalizationEngine.get_llm_profile()` decides when to surface visible payoff and reward cues | `profile_transparency` inferred labels and explanations | `live` | Sparkle can now decide whether reward framing is likely to help or feel noisy for this user. |
| `peak_focus_hours` | `FocusSignalProcessor.process_recent_focus_sessions()` from recent focus sessions | `UserPreferencesCenter.inferred["peak_focus_hours"]` via `ProfileWriteService.update_inferred_preference()` | `PreferenceService.get_preferences()` -> schedule/runtime | `SmartScheduleService._resolve_focus_hours()` is the primary focus-hour signal; push policy logic also reads it in `PersonalizationEngine` | `profile_transparency` inferred labels and explanations | `live` | Scheduling can now prefer hours where the user actually completes focus work instead of relying on generic windows. |
| `inactive_push_hours` | `PushFeedbackService._build_inferred_updates()` from recent push interaction history | `UserPreferencesCenter.inferred["inactive_push_hours"]` via inferred preference updates | `PreferenceService.get_preferences()` -> schedule/runtime | `SmartScheduleService` penalizes these hours; push policy logic in `PersonalizationEngine` avoids them for reminders | `profile_transparency` inferred labels and explanations | `live` | Sparkle now avoids recommending or nudging into hours where the user repeatedly ignores interruption. |
| `goal_type` (intervention cohort) | `UserPreferencesCenter.goal_memory` or explicit preferences fetched by bridge helpers | Persisted as `diagnosis_payload["cohort_profile"]["goal_type"]` on intervention records | `BehaviorInterventionBridge` and `PlanHealthInterventionBridge` compute and persist cohort profile | `InterventionOutcomeVerifier._strategy_context_snapshot()` flattens it for `InterventionStrategyLearner.record_outcome()` | No dedicated cohort transparency surface | `partially live` | Outcome learning can now distinguish whether a strategy worked for exam-driven versus other goal cohorts. |
| `knowledge_level` (intervention cohort) | Explicit preferences fetched by bridge helpers | Persisted as `diagnosis_payload["cohort_profile"]["knowledge_level"]` on intervention records | `BehaviorInterventionBridge` and `PlanHealthInterventionBridge` | `InterventionOutcomeVerifier._strategy_context_snapshot()` -> learner context snapshot | General profile preferences exist, but no dedicated intervention-cohort transparency view | `partially live` | Outcome learning can now group strategy effectiveness by prior knowledge level instead of treating all users as one bucket. |
| `learning_style` (intervention cohort) | Explicit preferences fetched by bridge helpers | Persisted as `diagnosis_payload["cohort_profile"]["learning_style"]` on intervention records | `BehaviorInterventionBridge` and `PlanHealthInterventionBridge` | `InterventionOutcomeVerifier._strategy_context_snapshot()` -> learner context snapshot | General profile preferences exist, but no dedicated intervention-cohort transparency view | `partially live` | Outcome learning can now preserve whether a strategy worked better for different learning-style cohorts. |

## 4. Prompt And Telemetry Contract

`prompt_signal_telemetry` is the temporary internal `S2-I0` contract for prompt leakage visibility.

This payload is assembled in `backend/app/orchestration/prompts.py` and attached back onto `user_context` during prompt building.

### 4.1 Tracked Fields

`S2-I0` intentionally tracks only the dead-data fields that previously leaked out of the prompt pipeline:

- `error_summary`
- `recent_errors`
- `recent_mastery_changes`

Other signals in this pack, such as achievement, focus, push, and cohort signals, are runtime-consumed but are not part of this prompt telemetry contract.

### 4.2 Payload Shape

```python
{
    "tracked_fields": ["error_summary", "recent_errors", "recent_mastery_changes"],
    "collected_high_value_fields": [str, ...],
    "normalized_high_value_fields": [str, ...],
    "rendered_high_value_fields": [str, ...],
    "prompt_visible_high_value_fields": [str, ...],
    "dropped_high_value_fields": [str, ...],
    "high_value_fields": {
        "error_summary": {
            "collected": bool,
            "collected_sources": ["context" | "cognitive_context", ...],
            "normalized": bool,
            "rendered": bool,
            "prompt_visible": bool,
            "item_count": int,
        },
        "recent_errors": { ... },
        "recent_mastery_changes": { ... },
    },
    "section_sizes": {
        "recent_pain_points": {"items": int, "approx_tokens": int},
        "recent_wins": {"items": int, "approx_tokens": int},
    },
    "model_facing_section_sizes": {
        "recent_pain_points": {"items": int, "approx_tokens": int},
        "recent_wins": {"items": int, "approx_tokens": int},
    },
}
```

### 4.3 Semantic Meaning

- `collected`: the raw field existed on the incoming context or nested `cognitive_context`
- `collected_sources`: which sources supplied the field; in `S2-I0` this is currently `context` and/or `cognitive_context`
- `normalized`: `_normalize_user_context()` produced a usable normalized value
- `rendered`: the field contributed at least one line to `【近期痛点】` or `【近期进展】`
- `prompt_visible`: the rendered line survived final prompt assembly and is visible in the model-facing user context block
- `dropped_high_value_fields`: any tracked field that was collected upstream but did not survive to prompt-visible state
- `section_sizes`: pre-assembly section budgets for the new pain/win blocks
- `model_facing_section_sizes`: the model-facing section sizes after final prompt assembly

### 4.4 Render Caps

- `light` context:
  - `recent_pain_points`: at most 1 item total, with `error_summary` taking the first slot when present
  - `recent_wins`: at most 1 item
- `full` context:
  - `recent_pain_points`: at most 3 items total, with `error_summary` taking one slot when present
  - `recent_wins`: at most 3 items

### 4.5 Fields Still Not Prompt-Rendered By Design

The following signals are intentionally runtime-only in `S2-I0` and therefore absent from `prompt_signal_telemetry`:

- `achievement_peak_hours`
- `achievement_motivation_response`
- `achievement_pace_style`
- `achievement_reward_sensitivity`
- `peak_focus_hours`
- `inactive_push_hours`
- intervention cohort fields persisted into `diagnosis_payload`

These are consumed by scheduling, personalization, or intervention learning rather than rendered into the prompt text block.

## 5. What Is Now Rendered vs Still Not Rendered

### Rendered Into Prompt Context

- `error_summary`
- `recent_errors`
- `recent_mastery_changes`

These appear in:
- `【近期痛点】`
- `【近期进展】`
- `SituationBrief.evidence.freshest_items`
- `SituationBrief.summary`

### Consumed At Runtime But Not Rendered Into Prompt Text

- `achievement_peak_hours`
- `achievement_motivation_response`
- `achievement_pace_style`
- `achievement_reward_sensitivity`
- `peak_focus_hours`
- `inactive_push_hours`
- intervention cohort fields persisted on intervention records

This is intentional for `S2-I0`. These signals improve runtime behavior without adding more prompt surface area.

### Still Dropped

No tracked `S2-I0` prompt fields are still silently dropped when present and within budget. The protected fields are now either:
- normalized and rendered
- or listed in `dropped_high_value_fields` if they fail to become prompt-visible

## 6. Verification Matrix

The following suites were rerun as the `S2-I0` closeout gate on 2026-04-06.

| Signal family | Tests that protect it |
|---|---|
| Prompt pain/win closure (`error_summary`, `recent_errors`, `recent_mastery_changes`) | `backend/tests/unit/test_prompt_signal_closure.py`, `backend/tests/unit/test_situation_brief.py`, `backend/tests/unit/test_phase_b_prompt_sections.py` |
| Achievement-derived inferred signals | `backend/tests/unit/test_openclaw_phase5_10_followup.py`, `backend/tests/unit/test_achievement_transparency_meta.py` |
| Profile-aware scheduling (`peak_focus_hours`, `achievement_peak_hours`, `inactive_push_hours`) | `backend/tests/unit/test_smart_schedule_service.py` |
| Intervention cohort persistence (`goal_type`, `knowledge_level`, `learning_style`) | `backend/tests/unit/test_intervention_context_persistence.py`, `backend/tests/unit/test_intervention_strategy_learner.py` |
| Broader planning and orchestration regression around the new prompt/runtime path | `backend/tests/unit/test_plan_quality_gate.py`, `backend/tests/unit/test_planning_benchmark_evaluator.py`, `backend/tests/unit/test_planning_benchmark_service.py`, `backend/tests/orchestration/test_run_ledger.py`, `backend/tests/unit/orchestrator/mixins/test_execution_engine_mixin.py`, `backend/tests/unit/orchestrator/mixins/test_response_builder_mixin.py`, `backend/tests/integration/test_phase5_orchestrator_north_star_acceptance.py` |

### Closeout Gate

The required `S2-I0` verification set is:

- `backend/tests/unit/test_prompt_signal_closure.py`
- `backend/tests/unit/test_situation_brief.py`
- `backend/tests/unit/test_openclaw_phase5_10_followup.py`
- `backend/tests/unit/test_achievement_transparency_meta.py`
- `backend/tests/unit/test_smart_schedule_service.py`
- `backend/tests/unit/test_intervention_strategy_learner.py`
- `backend/tests/unit/test_intervention_context_persistence.py`
- `backend/tests/unit/test_phase_b_prompt_sections.py`
- `backend/tests/unit/test_plan_quality_gate.py`
- `backend/tests/unit/test_planning_benchmark_evaluator.py`
- `backend/tests/unit/test_planning_benchmark_service.py`
- `backend/tests/orchestration/test_run_ledger.py`
- `backend/tests/unit/orchestrator/mixins/test_execution_engine_mixin.py`
- `backend/tests/unit/orchestrator/mixins/test_response_builder_mixin.py`
- `backend/tests/integration/test_phase5_orchestrator_north_star_acceptance.py`

Recorded result after the `S2-I0` code changes:
- `70 passed`

## 7. Remaining S2-I0 Boundaries

These are intentionally out of scope for `S2-I0` and must not be mistaken for regressions:

1. There is no canonical `UserInsightState` yet.
2. There is no general signal registry yet.
3. There is no new end-user transparency UI beyond inferred key labels and explanations.
4. There is no broader signal-family expansion beyond the current closure pack.
5. There is no production dashboard or metrics pipeline for `prompt_signal_telemetry`; it remains in-process context data only.

## 8. Handoff Guidance For S2-I1

`S2-I1` should start from this repo truth:

1. The prompt leak for pain/win signals is closed and regression-protected.
2. Achievement, focus, push, and cohort signals already have working runtime consumers and should be reused, not rebuilt.
3. The next job is not to reopen `S2-I0`; it is to unify these signals into a canonical compiled insight state without losing the current consumer behavior.
