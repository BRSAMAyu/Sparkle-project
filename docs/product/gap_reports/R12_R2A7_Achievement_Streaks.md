# R12 / R2A7 — Achievement_Streaks 二次深度审查
**Date**: 2026-05-07
**Scope**: Achievement + Streaks
**Layers**: Flutter → Go Gateway → Python Engine → PostgreSQL / Redis
**Vision check**: The achievement system is robust but has a few gaps in quality-weighted tracking and deep narrative integration.

---

## Summary
| Category | Count |
|----------|-------|
| P0 (must-fix before launch) | 2 |
| P1 (important gap, ship with plan) | 4 |
| P2 (nice to have, post-launch) | 3 |
| Verified working | 7 |

---

## R11 P0 验证
Verified that some P0 issues from R11 still persist or need updates, though E2E testing for achievements has been added in `backend/tests/e2e/test_achievement_unlock_e2e.py`.

---

## P0 Findings (Must Fix Before Launch)

### P0-1: Binary Streak Fuels Achievement Engine; Quality Streak Is Read-Only
**File**: `backend/app/services/achievement_engine.py`
**Lines**: 1916-1948
**Problem**: The streak counter that feeds STREAK_DAYS achievements is binary. It checks if the event type is in `[DAILY_CHECKIN, DAILY_STUDY, TASK_COMPLETED, NODE_MASTERED]`. The quality score calculated via `StreakQualityService` is cached but not used as a gate for achievement progress.
**Evidence**: `if event_type not in [AchievementEvent.DAILY_CHECKIN, ...]: return`
**Expected**: The streak feeding the achievement engine should be quality-gated.
**Fix recommendation**: In `_update_streak_stats`, before incrementing, call `StreakQualityService.compute_quality()` and require `is_quality_day == True`.

### P0-2: No Daily Reflection Feature Exists
**File**: `mobile/lib/features/reflection/` (Missing)
**Lines**: N/A
**Problem**: There is no dedicated "Daily Reflection" screen or API endpoint.
**Evidence**: Glob search for `daily_reflection` or `reflection/**/*.dart` yields no results.
**Expected**: A daily reflection ritual that feeds into the growth chronicle.
**Fix recommendation**: Create a `DailyReflectionScreen` and corresponding API endpoint.

---

## P1 Findings (Important, Ship With Plan)

### P1-1: Growth Chronicle Is Redis-primary
**File**: `backend/app/signals/growth_chronicle.py`
**Lines**: 112-169
**Problem**: Chronicle entries use Redis with a TTL instead of permanent DB storage, risking data loss.
**Expected**: Chronicle should be durable.
**Fix recommendation**: Create a proper DB table.

### P1-2: Milestone Achievement Notifications Only for 3 Hardcoded IDs
**File**: `backend/app/services/achievement_event_consumer.py`
**Lines**: 39-50
**Problem**: The `MILESTONE_ACHIEVEMENT_IDS` list only supports a limited set of IDs for rich notifications (expanded slightly from R11 but still hardcoded).
**Fix recommendation**: Expand to all rare+ achievements.

### P1-3: Chronicle entries not generated for achievement unlocks
**File**: `backend/app/services/achievement_engine.py`
**Lines**: 1487-1509
**Problem**: Unlocks trigger `_record_progress_narrative_unlock` but do not directly add to `GrowthChronicleService`.
**Fix recommendation**: Call `GrowthChronicleService.add_entry()` directly.

### P1-4: Celebration triggers are invisible (no push)
**File**: `backend/app/services/streak_quality.py`
**Lines**: 177-212
**Problem**: `celebration_trigger` returns a message but it's not pushed to the user actively.
**Fix recommendation**: Add a scheduled push notification.

---

## Verified Working (Strengths)

### V-1: E2E Achievement Unlock Tests
- `backend/tests/e2e/test_achievement_unlock_e2e.py` contains comprehensive test flows for streak breaks, unlocks, idempotency, and payloads.
- **Verdict**: Verified working and resolves the previous R11 P0-3 missing E2E test issue.

### V-2: Quality-Weighted Streak Computation
- `StreakQualityService` computes detailed stats and evidence.
- **Verdict**: Excellent computation, but still needs to feed the achievement engine.

### V-3: Growth Chronicle CRUD
- `GrowthChronicleService.add_entry` is implemented and functional.
- **Verdict**: Good logic, though storage backend needs review.
