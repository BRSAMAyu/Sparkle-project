# QA-P3-3: Strategy Effectiveness — SprintReview Per-Strategy Outcome Display

**Status**: 📋 spec-done
**Date**: 2026-05-06
**Author**: claude-B
**Effort**: L (multi-layer: Python backend + Flutter frontend)
**Type**: Feature addition

## Problem

SprintReview's `_BottleneckCard` uses purely rule-based heuristics from `progress` (0-100%) and `daysLeft` to generate generic advice. It does not display actual per-strategy effectiveness data that the backend already tracks.

## Current State

### Backend (already exists, not used by SprintReview)
- `InterventionOutcomeTracker.get_effectiveness_summary(user_id, days=30)` — returns dict of strategy_type → {effective_count, total_count, effectiveness_rate}
- `InterventionOutcome` ORM model — tracks mastery_before/after, effective flag, outcome_status
- `InterventionStrategyOutcome` — tracks trigger_type, delivery_tone, acceptance_status, outcome, time_to_action
- `StrategyBeliefSnapshot` — Bayesian belief tracking (alpha/beta/belief_score)

### Frontend (current _BottleneckCard)
- `sprint_review_screen.dart:331-385` — `_BottleneckCard` widget
- Inputs: `progress` (double), `daysLeft` (int)
- Output: List of `_Insight` widgets derived from hardcoded if/else rules
- No provider fetches strategy effectiveness data
- No connection to backend intervention tracking

### Gap
`SprintSummaryResponse` (backend/app/schemas/exam_sprint.py:214) does not include strategy effectiveness fields. The data exists but is not plumbed through the API.

## Proposed Design

### 1. Backend: Add StrategyEffectivenessSummary to SprintSummaryResponse

**New pydantic model** in `backend/app/schemas/exam_sprint.py`:
```python
class StrategyEffectivenessSummary(BaseModel):
    strategy_type: str          # e.g. "nudge", "reminder", "reframe"
    effective_count: int        # interventions that improved mastery
    total_count: int            # total interventions of this type
    effectiveness_rate: float   # 0.0-1.0
    outcome_distribution: dict  # {"success": N, "no_change": N, "regression": N}
```

**Wire into `_build_summary()`** in `exam_sprint_review_service.py`:
- Call `InterventionOutcomeTracker.get_effectiveness_summary(user_id)`
- Map results to `List[StrategyEffectivenessSummary]`
- Include in `SprintSummaryResponse`

### 2. Flutter: New Provider + Widget

**New provider**: `strategyEffectivenessProvider` in `sprint_statistics_provider.dart`
- Fetches from the SprintReview API (which now includes strategy_effectiveness)
- Returns `AsyncValue<List<StrategyEffectiveness>>`

**New widget**: `_StrategyEffectivenessCard` (replaces or augments `_BottleneckCard`)
- Shows per-strategy effectiveness rates as a list
- Each strategy type: icon + name + effectiveness bar + count (e.g., "3/5 effective")
- Green (>66%), yellow (33-66%), red (<33%) effectiveness indicators
- Falls back to existing `_BottleneckCard` heuristics when no strategy data available

### 3. ARB/i18n
- New localization keys for strategy type labels and effectiveness descriptions
- Strategy type display names in both en/zh

## Data Flow

```
InterventionOutcomeTracker.get_effectiveness_summary()
  → exam_sprint_review_service._build_summary()
    → SprintSummaryResponse.strategy_effectiveness
      → Flutter strategyEffectivenessProvider
        → _StrategyEffectivenessCard in SprintReviewScreen
```

## Key Files to Modify

| Layer | File | Change |
|-------|------|--------|
| Backend | `backend/app/schemas/exam_sprint.py` | Add `StrategyEffectivenessSummary` model, add field to `SprintSummaryResponse` |
| Backend | `backend/app/services/exam_sprint_review_service.py` | Wire `get_effectiveness_summary()` into `_build_summary()` |
| Flutter | `mobile/lib/features/plan/presentation/providers/sprint_statistics_provider.dart` | Add `strategyEffectivenessProvider` |
| Flutter | `mobile/lib/features/plan/presentation/screens/sprint_review_screen.dart` | Add `_StrategyEffectivenessCard`, integrate with _BottleneckCard |
| Flutter | `mobile/lib/l10n/app_en.arb` | New strategy effectiveness labels |
| Flutter | `mobile/lib/l10n/app_zh.arb` | New strategy effectiveness labels (Chinese) |

## Risk Assessment

- **Low risk**: Backend changes are additive (new optional field in response). Existing data already tracked.
- **Fallback**: If no strategy data exists for user, `_BottleneckCard` heuristics continue to work unchanged.
- **No proto change needed**: SprintReview is a REST endpoint, not gRPC.

## Estimated Effort

- Backend schema + service wiring: 1-2 hours
- Flutter provider + widget: 2-3 hours
- i18n strings: 30 minutes
- Testing: 1 hour
- **Total**: ~6 hours (M-L)
