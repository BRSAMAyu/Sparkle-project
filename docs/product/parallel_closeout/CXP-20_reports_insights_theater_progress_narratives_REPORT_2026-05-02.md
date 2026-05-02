# CXP-20 Report — Reports, Insights, Theater, And Progress Narratives

## Goal
Make reflection surfaces use real evidence and point the user to a next action, especially when the evidence is not just task completion but plan drift, plan progress, Aurora correction, or prediction-theater data quality.

## Work Completed
- Weekly growth narratives now include plan outcome evidence: near-complete plans, drifted plans, progress samples, and action metadata.
- Weekly growth narratives now include Aurora calibration corrections from memory correction records, so user corrections can appear in report evidence instead of disappearing into backend state.
- Report payloads expose `report_actions` with deep links for plan repair, error review, prediction theater, Aurora calibration, or a minimum next task.
- Prediction Theater responses now include an `evidence_summary` and `recommended_next_action` so the UI can explain which data supported the prediction and where to act next.
- Mobile Insights parses the new weekly evidence fields and shows chips for plan outcomes and Aurora corrections.
- Mobile Theater parses the new evidence payload and shows a compact evidence banner above the prediction workbench.

## User Experience Before / After
Before: a weekly report could praise task completion and mastery while missing the user's explicit correction ("不是没时间，是完全不会做") or a plan that had drifted past its target date.

After: the same weekly report can say that Aurora recorded the correction, identify a drifted plan, expose a primary action in the payload, and show the new evidence types in the Insights card.

## Cross-System Links
- Backend narratives: `ProgressNarrativeService`
- Backend prediction theater: `PredictionTheaterService`
- Mobile insights model/card: `WeeklyGrowthNarrative`, `WeeklyGrowthNarrativeCard`
- Mobile theater model/screen: `TheaterPrediction`, `KnowledgeTheaterScreen`
- Evidence sources: tasks, errors, study records, achievements, plans, and Aurora memory corrections

## Verification
- `python3 -m py_compile backend/app/services/progress_narrative_service.py backend/app/services/theater/prediction_theater_service.py`
- `cd backend && pytest tests/unit/test_progress_narrative_service.py` — 7 passed
- `cd backend && ruff check app/services/progress_narrative_service.py app/services/theater/prediction_theater_service.py tests/unit/test_progress_narrative_service.py` — passed
- `cd mobile && flutter analyze lib/features/insights/data/models/weekly_growth_narrative.dart lib/features/insights/presentation/widgets/weekly_growth_narrative_card.dart lib/features/theater/data/models/theater_models.dart` — no issues
- `git diff --check -- <touched files>` — passed
- `cd mobile && flutter analyze <all touched mobile files including knowledge_theater_screen.dart>` — ran, but reports info-level existing style debt in the large theater screen, mostly `require_trailing_commas` and directive ordering.

## Remaining Risks
- The theater screen is a large pre-existing file with analyzer style debt; a separate design-system/accessibility cleanup should normalize it rather than mixing that churn into CXP-20.
- `MemoryCorrection` currently identifies Aurora-related corrections by known memory types. If future Aurora correction lanes use new type names, they should be added to the summary filter.
- Report actions use existing deep-link strings; final integration should verify route names against the unified mobile router after all CXP branches merge.

## Commit
Branch: `codex/CXP-20-reports-insights-theater`
Commit: pending
