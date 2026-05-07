# R11 / R2A7 — Achievement + Streaks + Rewards + Growth Chronicle Pre-Launch Audit

**Date**: 2026-05-07
**Scope**: Achievement engine, streak system, rewards, growth chronicle, learning dashboard, celebration triggers, daily reflection
**Layers**: Flutter → Go Gateway → Python Engine → PostgreSQL / Redis
**Vision check**: Achievements should feel meaningful (not just "unlocked badge"), streaks should be quality-weighted, growth chronicle should tell a narrative story, learning dashboard should exist

---

## Summary

| Category | Count |
|----------|-------|
| P0 (must-fix before launch) | 3 |
| P1 (important gap, ship with plan) | 4 |
| P2 (nice to have, post-launch) | 3 |
| Verified working | 6 |

---

## Architecture Overview

### End-to-End Flow

```
User action (task complete / focus / node unlock)
    → Go Gateway proxies → Python API
    → AchievementEngine.process_event()
        → _update_streak_stats()       [binary streak: 4 event types]
        → _evaluate_progress()         [23+ trigger codes]
        → _unlock_achievement()        [rewards, context snapshot, story]
    → event_bus.publish("achievement.unlocked")
    → AchievementEventConsumer.handle_event()
        → WebSocket push ("achievement_unlock" → Flutter)
        → Community broadcast (optional)
        → Cognitive fragment recorded
        → SpineOrchestrator.on_achievement_event() → GrowthChronicle
    → Flutter shell_navigation.dart catches WS event
    → AchievementUnlockDialog.showFromWsEvent() [visuals, confetti, BGM]

Parallel: StreakQualityService (READ-ONLY, analytical)
    → StreakQualityIndicator widget consumes /experience/streak-quality
    → Quality-weighted streak is computed but does NOT feed the achievement engine
```

### Event Types (AchievementEvent enum)

Defined at `backend/app/services/achievement_engine.py:92-121`:

| # | Event | Lines |
|---|-------|-------|
| 1 | TASK_COMPLETED | 95 |
| 2 | DAILY_CHECKIN | 96 |
| 3 | DAILY_STUDY | 97 |
| 4 | NODE_UNLOCKED | 98 |
| 5 | NODE_MASTERED | 99 |
| 6 | STUDY_MINUTES_ACCUMULATED | 100 |
| 7 | NIGHT_STUDY | 101 |
| 8 | EARLY_BIRD | 102 |
| 9 | WEEKEND_WARRIOR | 103 |
| 10 | STREAK_MILESTONE | 104 |
| 11 | CONTRACT_COMPLETED | 105 |
| 12 | CONTRACT_FAILED | 106 |
| 13 | MUTUAL_STUDY | 107 |
| 14 | COMMUNITY_SHARE | 108 |
| 15 | AURORA_CALIBRATION | 109 |
| 16 | HIDDEN_TRIGGER | 110 |
| 17 | SPRINT_STARTED | 112 |
| 18 | SPRINT_COMPLETED | 113 |
| 19 | SPRINT_ABANDONED | 114 |
| 20 | SPRINT_PERFECT | 115 |
| 21 | SPRINT_STREAK | 116 |
| 22 | SPRINT_AHEAD | 117 |
| 23 | ACHIEVEMENT_COMBO | 119 |
| 24 | PROGRESS_MILESTONE | 120 |
| 25 | PLAN_CREATED | 121 |

**Total: 25 event types** (exceeds the 19 stated in the brief).

### Supported Trigger Codes

`backend/app/services/achievement_engine.py:128-157`: 28 trigger codes including ALL_SECTORS_UNLOCKED, EARLY_BIRD, NIGHT_OWL_STUDY, NODES_MASTERED, NODES_UNLOCKED, PERFECTIONIST, PLANS_TOTAL, SECTOR_MASTERY, SPEED_UNLOCK, SPRINTS_*, STREAK_DAYS, STUDY_MINUTES_*, TASKS_TOTAL, WEEKEND_WARRIOR, MUTUAL_STUDY, COMMUNITY_SHARE, AURORA_CALIBRATION, HIDDEN_TRIGGER.

### Achievement Definitions

`backend/app/data/achievement_seeds.py`: 31 achievements across 8 categories (streak x4, milestone x3, node_explore x6, mastery x2, study_time x4, task_complete x3, social/hidden x5, planning x2, sprint x8).

---

## P0 Findings (Must Fix Before Launch)

### P0-1: Binary Streak Fuels Achievement Engine; Quality Streak Is Read-Only

**File**: `backend/app/services/achievement_engine.py`
**Lines**: 1924-1931 (_update_streak_stats gate)

```python
# Only 4 core event types update the streak:
if event_type not in [
    AchievementEvent.DAILY_CHECKIN,
    AchievementEvent.DAILY_STUDY,
    AchievementEvent.TASK_COMPLETED,
    AchievementEvent.NODE_MASTERED,
]:
    return
```

**Problem**: The streak counter that feeds STREAK_DAYS achievements (streak_7, streak_30, streak_100, streak_365) is binary -- any of these 4 events fires counts as a "day", regardless of quality. This means opening the app and completing a 1-minute task counts the same as a 90-minute deep work session.

Meanwhile, `StreakQualityService` (`backend/app/services/streak_quality.py`) computes a sophisticated quality score (5 dimensions, fatigue/crisis penalties, late-night caps) but its output is **never used** by the achievement engine. A user with 365 binary days (opening app daily) gets the "legendary" 365-day streak achievement with the same weight as someone doing deep work daily.

**Expected**: The streak that feeds the achievement engine should be quality-gated. At minimum, STREAK_DAYS should require `quality_score >= 0.60` (i.e., `is_quality_day == True`) rather than any binary activity.

**Fix recommendation**:
1. In `_update_streak_stats`, before incrementing, call `StreakQualityService.compute_quality()` and require `is_quality_day == True`
2. Add a `quality_streak_days` field to `UserStreakStats` for the quality-gated version
3. Change STREAK_DAYS trigger to use quality_streak_days instead of current_streak
4. Or, add new achievements like "quality_streak_30" that use the quality streak

### P0-2: No Daily Reflection Feature Exists

**Search scope**: All `*.dart`, `*.py`, `*.go` files across the monorepo.

**Finding**: There is no dedicated "Daily Reflection" screen, widget, route, or API endpoint. The only reflection-related code found:

- `mobile/lib/features/focus/presentation/widgets/reflection_dialog.dart` -- a brief post-focus reflection prompt (part of focus timer)
- `backend/app/signals/async_deep_learner.py` -- server-side deep reflection (automated)
- `backend/app/core/celery_tasks.py` -- scheduled tasks related to reflection processing

**Expected**: The vision says users should have a daily reflection ritual -- a lightweight, guided end-of-day check-in that asks questions like "What went well today?", "What was hard?", "What's one thing you'll carry forward?" and feeds into the growth chronicle.

**Fix recommendation**:
1. Create a `DailyReflectionScreen` in `mobile/lib/features/reflection/`
2. Add a `/reflections/daily` API endpoint (Go proxy route + Python router)
3. Store reflections as `ChronicleEntry` with `entry_type: "user_reflection"` in GrowthChronicleService
4. Add a home screen card that prompts reflection at a configurable time (e.g., 21:00)
5. Wire reflection completions into the dual-core router for adaptive personalization

### P0-3: Achievement Unlock Has No Comprehensive Test

**File**: `backend/tests/unit/test_achievement_event_consumer.py`

**Finding**: The achievement event consumer has unit tests, but there is no end-to-end test that:
- Creates a user
- Completes tasks and focus sessions
- Verifies streak increment
- Verifies achievement unlocks
- Verifies WebSocket message format
- Verifies Flutter receives and renders the dialog

**Expected**: An acceptance test (like `achievement_visual_acceptance.py` but runnable in CI) that fully traces the unlock flow.

**Fix recommendation**: Extend `backend/scripts/achievement_visual_acceptance.py` with test assertions and add it to the CI pipeline.

---

## P1 Findings (Important, Ship With Plan)

### P1-1: Growth Chronicle Is Ephemeral (Redis-First, 90-Day TTL)

**File**: `backend/app/signals/growth_chronicle.py`
**Lines**: 25-27

```python
_CHRONICLE_KEY = "spine:chronicle:{user_id}"
_CHRONICLE_TTL_SECONDS = 90 * 24 * 3600  # 90 days
_MAX_STORED_ENTRIES = 100
```

**Problem**: Growth chronicle entries are stored in Redis with a 90-day TTL. The durable fallback (`GrowthChronicleSnapshot`) stores ALL entries as a single JSON blob in one DB row (`backend/app/signals/growth_chronicle.py:515-543`). If Redis is flushed or the TTL expires before the next durable save, entries older than the last save are lost forever. There's no per-entry DB table.

**Impact**: A user who achieves a milestone on day 1 would lose that chronicle entry on day 91 if they haven't triggered another chronicle save event. This undermines the "user-co-owned narrative" premise.

**Fix recommendation**:
1. Create a proper `growth_chronicle_entries` DB table with per-entry rows
2. Each entry should be independently durable (written on creation)
3. Redis should be a cache layer, not the primary store
4. Reduce or eliminate TTL on the primary store

### P1-2: Milestone Achievement Notifications Only for 3 Hardcoded IDs

**File**: `backend/app/services/achievement_event_consumer.py`
**Lines**: 39-43

```python
MILESTONE_ACHIEVEMENT_IDS = {
    "30_day_learner",
    "knowledge_explorer_50",
    "sprint_veteran",
}
```

Only 3 of 31 achievements generate milestone notification cards with stats, celebration routes, and share hashtags. Other significant milestones (streak_30, nodes_100, sprint_10, study_100hours) unlock silently without the rich notification payload.

**Fix recommendation**: Expand MILESTONE_ACHIEVEMENT_IDS to include all rare+ achievements with visible effects, or make it configurable from the achievement definition.

### P1-3: GrowthChronicle Entry Generation Is Limited

**File**: `backend/app/signals/growth_chronicle.py`

The GrowthChronicleService currently generates entries only through:
1. `build_milestone_from_outcome()` -- requires `attribution == "effective"` and `attribution_confidence >= 0.8`
2. `build_turning_point_from_correction()` -- requires explicit user correction
3. `build_pattern_discovery()` -- requires 5+ outcomes with same strategy

These are called from the Signal-to-Action Spine, not from the achievement engine directly. The achievement engine's `_finalize_unlock_side_effects` calls `SpineOrchestrator.on_achievement_event()` which may or may not produce a chronicle entry depending on spine logic.

**Impact**: Most achievement unlocks do NOT generate chronicle entries. A user unlocking "streak_30" gets a dialog + photon reward but no narrative entry in their growth story.

**Fix recommendation**: In `_finalize_unlock_side_effects` (achievement_engine.py:1487), directly call `GrowthChronicleService.add_entry()` for rare+ achievement unlocks so every significant milestone becomes a chronicle entry.

### P1-4: No Push Notification for Streak Celebration Triggers

**File**: `backend/app/services/streak_quality.py`
**Lines**: 155-190

The `celebration_trigger()` method computes an evidence-backed celebration message but returns it only through the API response. There is no push notification, system update, or WebSocket push that tells the user "You have a quality streak day -- here's why."

**Impact**: The celebration trigger is invisible unless the user navigates to the streak quality indicator and taps it. This undermines the "meaningful celebration" vision.

**Fix recommendation**: Add a scheduled job (e.g., 21:00 daily) that computes quality, and if `celebration_trigger` returns non-null, push a local notification or system update with the evidence message.

---

## P2 Findings (Post-Launch)

### P2-1: Late-Night Learning Penalizes Streak Quality But Not Achievement Progress

**File**: `backend/app/services/streak_quality.py:86-102`

```python
is_late_night = any("深夜" in e for e in fatigue_state.get("evidence", []))
...
elif is_late_night:
    quality_score = min(quality_score, 0.75)
```

Night-time learning caps quality score at 0.75, which is reasonable for the quality indicator. However, this has no effect on the achievement engine's streak counter (see P0-1). The penalty only affects the analytical quality score which is read-only.

### P2-2: StreakQualityService Re-computes Everything Every Call

**File**: `backend/app/services/streak_quality.py`

Every call to `compute_quality()` runs 5+ DB queries and 2 Redis reads (fatigue + crisis state). The `build_payload()` method computes quality for the current day AND a 7-day trend. The Flutter `StreakQualityIndicator` widget fetches this on every build. No caching layer protects this.

**Fix recommendation**: Cache the `build_payload()` result for at least 5 minutes, with forced refresh on streak-relevant activity.

### P2-3: Learning Dashboard Has No Data Until User Has 7 Days of Activity

**File**: `backend/app/api/v1/experience/dashboard_router.py:40`

```python
LOOKBACK_DAYS = 7
```

The dashboard computes all metrics over a 7-day lookback window. New users (day 1-6) see empty states for everything: time distribution, efficiency metrics, weakness radar, knowledge changes. There is a `GrowthDashboard.placeholder()` factory in Flutter (`mobile/lib/features/insights/data/models/growth_dashboard.dart:42`) but it's not wired to show when the backend returns empty -- it's only used for testing.

**Fix recommendation**: Show the placeholder dashboard when backend data is empty for new users, with progressive reveal as real data accumulates.

---

## Verified Working (Strengths)

### V-1: Achievement Unlock End-to-End (Python → WebSocket → Flutter Dialog)

- `AchievementEngine._unlock_achievement()` (`achievement_engine.py:1403`): Creates UserAchievement record, checks first-unlocker status, builds context story, grants rewards
- `AchievementEngine._notify_unlocks()` (`achievement_engine.py:1826`): Formats WS message with achievement_data, rarity, visual_effect, rewards, combo_info, glory_lines, context_story
- `ws_manager.send_personal_message()`: Pushes to user's WebSocket connection
- `shell_navigation.dart:145-178`: Catches `achievement_unlock` WS type, calls `handleAchievementUnlock()`, queues dialog
- `achievement_unlock_dialog.dart`: Rarity-gated animations (common/rare/epic/legendary), confetti, BGM boost, sensory feedback, combo banner, milestone section, reward preview, visual element preview, share/view-close buttons
- **Verdict**: Full pipeline intact, production-quality visuals

### V-2: Quality-Weighted Streak Computation

- `StreakQualityService` (`streak_quality.py`): 5-dimension quality score (effective_minutes 32%, core_tasks 26%, breakthroughs 20%, plan_consistency 14%, recovery 8%)
- Fatigue/crisis penalties from spine Redis state
- Late-night capping
- `is_quality_day` threshold at 0.60 + minimum activity
- `weekly_quality_trend()` for 7-day visualization
- `celebration_trigger()` with evidence-based messaging
- Flutter `StreakQualityIndicator` widget with dual-ring visualization, breakdown grid, trend bars, evidence card
- **Verdict**: Excellent computation, but needs to feed the achievement engine (see P0-1)

### V-3: Milestone Celebration Screen

- `milestone_celebration_screen.dart`: Full-screen celebration with animated number counter, stat chips, share-to-system functionality (captures RepaintBoundary as image), glow orbs, gold gradient backdrop
- Route: `/achievements/milestone/:milestoneId?study_days=...&mastered_nodes=...`
- Deep link format: `sparkle://milestone/:milestoneId?...`
- `MilestoneCelebrationPayload` parses 3 milestone types (30_day_learner, knowledge_explorer_50, sprint_veteran) with type-specific headlines, subheadlines, badges
- **Verdict**: Production-ready, but only 3 milestone types (see P1-2)

### V-4: Learning Dashboard Page

- `learning_dashboard_page.dart`: Time distribution chart, efficiency ring metric, weakness radar (CustomPaint polar chart), knowledge change tracker, plan stability panel, model update receipt
- Route: `/learning/insights/dashboard`
- Backend: `dashboard_router.py` computes all data from live DB queries
- Flutter model: `growth_dashboard.dart` handles both story-wrapped and raw narrative formats
- **Verdict**: Exists and renders, but empty for new users (see P2-3)

### V-5: Growth Chronicle Page

- `growth_chronicle_page.dart`: Weekly story card, timeline of chronicle entries with expand/collapse, evidence refs, confirm/edit/reject actions, model update receipt
- Route: `/learning/insights/growth-chronicle`
- Backend: `growth_chronicle.py` with full CRUD (add, get, hide, edit, confirm, reject), retraction checks, ReturnCaseFile generation
- Chronicle entries are user-visible, user-editable, user-confirmable per P3-4 ruling
- **Verdict**: Well-designed UX, but storage is ephemeral (see P1-1)

### V-6: Reward System

- Photon grants: 10-5000 photons per achievement, with compensation retry (Celery + local 3-retry with exponential backoff)
- Titles: `UserTitle` model, equipped via `/achievements/titles/:titleId/equip`
- Galaxy skins: 6 skins, unlockable via achievements, equipped via `/achievements/skins/:skinId/equip`
- Freeze charges: Streak protection, granted by epic+ achievements, consumed automatically on missed days
- Visual elements: 33 elements across backgrounds/particles/effects/bundles, unlockable via achievements
- AchievementRewardObservability: Prometheus metrics + Redis audit log
- **Verdict**: Production-ready with observability

---

## Route Verification

### Go Gateway Proxy Routes

| Route Group | Path | Status |
|-------------|------|--------|
| Achievements | `/achievements/*` (15 routes) | Registered, proxy_routes.go:234-254 |
| Experience | `/experience/*` (catch-all) | Registered, proxy_routes.go:826-831 |
| Growth | `/growth/*` (catch-all) | Registered, proxy_routes.go:561-567 |
| Dashboard | `/dashboard/*` (catch-all) | Registered, proxy_routes.go:552-557 |

### Flutter Routes

| Route | Screen |
|-------|--------|
| `/learning/insights` | LearningInsightsOverviewScreen |
| `/learning/insights/growth-chronicle` | GrowthChroniclePage |
| `/learning/insights/dashboard` | LearningDashboardPage |
| `/achievements/milestone/:id` | MilestoneCelebrationScreen |

All routes are registered in `insights_routes.dart` and `achievement_routes.dart` with GoRouter, audio scoping, and motion tokens.

---

## Summary of Recommendations

| ID | Priority | Finding | Action |
|----|----------|---------|--------|
| P0-1 | P0 | Binary streak feeds achievement engine; quality streak is read-only | Gate STREAK_DAYS on quality_score >= 0.60 |
| P0-2 | P0 | No daily reflection feature exists | Build DailyReflectionScreen + API + chronicle integration |
| P0-3 | P0 | No E2E test for achievement unlock pipeline | Add CI-ready acceptance test |
| P1-1 | P1 | Growth chronicle is Redis-primary with 90-day TTL | Create proper DB table; make Redis a cache |
| P1-2 | P1 | Only 3 milestone IDs get rich notifications | Expand to all rare+ achievements with effects |
| P1-3 | P1 | Chronicle entries not generated for achievement unlocks | Call GrowthChronicleService directly in unlock flow |
| P1-4 | P1 | Celebration triggers are invisible (no push) | Add scheduled push for quality streak celebrations |
| P2-1 | P2 | Late-night penalty only affects read-only quality score | Deferred until P0-1 is resolved |
| P2-2 | P2 | StreakQualityService re-computes on every call | Add 5-min cache layer |
| P2-3 | P2 | Dashboard shows empty for users with <7 days activity | Wire GrowthDashboard.placeholder() for new users |
