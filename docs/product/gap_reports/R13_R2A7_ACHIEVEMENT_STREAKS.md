# R13-R2A7: Achievement + Streaks + Growth Chronicle Audit

> **Date**: 2026-05-07 | **Auditor**: Independent R13 Audit | **Scope**: Full-stack Achievement/Streak/Chronicle system

---

## Summary Table

| Area | Status | P0 | P1 | P2 | Verdict |
|------|--------|----|----|-----|---------|
| 1. Achievement Unlock Pipeline | WORKING | 0 | 1 | 2 | Full pipeline traced and functional |
| 2. Achievement Unlock Dialog | WORKING | 0 | 0 | 1 | Rarity animations, combo, share all wired |
| 3. Streak System | WORKING | 0 | 1 | 1 | Quality-gated sync confirmed, minor edge |
| 4. Growth Chronicle | WORKING | 0 | 1 | 2 | Page + routes exist, entry types complete |
| 5. Learning Dashboard | WORKING | 0 | 0 | 2 | Route registered, progressive lookback |
| 6. Daily Reflection | WORKING | 0 | 0 | 1 | Route + screen exist, focus dialog wired |
| 7. Reward System | WORKING | 0 | 0 | 2 | Photons, titles, skins, visual elements all grant |
| 8. Milestone Celebration | WORKING | 0 | 1 | 1 | Screen works, but only 3 milestone types have custom copy |
| **TOTAL** | | **0** | **4** | **12** | |

---

## 1. Achievement Unlock Pipeline

### Traced Full Path
```
Task Completed / Focus Session / Node Updated
  -> event_bus.publish("task.completed" / "galaxy.node.updated" / ...)
    -> AchievementEventConsumer.handle_event()  [backend/app/services/achievement_event_consumer.py]
      -> AchievementEngine.process_event()  [backend/app/services/achievement_engine.py]
        -> _update_streak_stats() (if core event)
        -> _get_relevant_achievements() (trigger_code matching)
        -> _evaluate_progress() (22 trigger code evaluators)
        -> _unlock_achievement() if progress >= 1.0
          -> _grant_rewards() (photon/title/skin/freeze_charge/visual_element)
          -> _build_context_snapshot() + _build_context_story()
          -> after-commit: _notify_unlocks() via WebSocket
          -> after-commit: _record_chronicle_unlock() -> GrowthChronicleService
          -> after-commit: _broadcast_unlock_signals() -> event_bus
```

### Achievement Definitions
- **39 achievements** in `INITIAL_ACHIEVEMENTS` seed data
- **Categories**: streak (4), milestone (3), exploration (5), mastery (2), study_time (4), tasks (3), sprint (8), community (1), aurora (1), hidden (5), planning (2)
- **Rarities**: common (14), rare (10), epic (8), legendary (7)
- **Visual effects**: none, gravity_wave, supernova, nebula_transform, black_hole, galaxy_skin
- **Reward types**: photon, title, freeze_charge, galaxy_skin, visual_element

### Verified Working
- 22 trigger code evaluators in `_evaluate_progress` cover STREAK_DAYS, TASKS_TOTAL, NODES_UNLOCKED, STUDY_MINUTES, SECTOR_MASTERY, SPEED_UNLOCK, PERFECTIONIST, WEEKEND_WARRIOR, SPRINTS_TOTAL, SPRINTS_STREAK, SPRINT_AHEAD, COMMUNITY_SHARE, AURORA_CALIBRATION, PLANS_TOTAL, CONTRACT_COMPLETED, etc.
- Context story generated on every unlock with plan/task/node snapshots
- Achievement combo system via `_handle_achievement_combo` (5-min Redis window)
- Progress milestones at 25%/50%/75% with WS notifications
- Session deduplication via `SessionCompletion` table prevents double-counting

### P1 Findings

**P1-A1: Combo bonus photons never actually granted**
- File: `backend/app/services/achievement_engine.py:2627-2634`
- `_handle_achievement_combo` computes `bonus_photons = combo * 10` for combo >= 3 and returns it in the combo info dict, but the `_grant_rewards` method is never called with this bonus. The bonus_photons value is stored in the unlock payload and sent to the frontend as display-only data. No PhotonService.grant_photons call exists for combo bonuses.
- Impact: Users see "combo bonus" in the unlock dialog but never receive the bonus photons.

### P2 Findings

**P2-A1: `_get_relevant_achievements` missing event→trigger mapping for some sprint events**
- File: `backend/app/services/achievement_engine.py:522-543`
- `SPRINT_STARTED` maps to `["SPRINT_STARTED", "SPRINTS_STARTED"]` but the trigger code `"SPRINT_STARTED"` in seeds uses `"SPRINTS_TOTAL"` with `trigger_config: {"count": 1}` which requires counting completed sprints, not started ones. The sprint_first achievement has `trigger_code: "SPRINTS_TOTAL"` but the event `SPRINT_STARTED` only maps to `SPRINT_STARTED`/`SPRINTS_STARTED` trigger codes, not `SPRINTS_TOTAL`. So a sprint start event will never increment progress for `sprint_first`.

**P2-A2: `_upsert_streak_day` called twice on same day when quality streak code runs**
- File: `backend/app/services/achievement_engine.py:1987-1992` and `2079-2084`
- The first `_upsert_streak_day` call at line 1987 sets the status to `ACTIVE`. Then the quality streak code at line 2079 may overwrite it to `WEAK` (if quality < 0.4). This means a single `process_event` call writes the same row twice, which is functionally correct but generates an extra DB flush.

---

## 2. Achievement Unlock Dialog

### Verified Working
- `AchievementUnlockDialog` at `mobile/lib/features/achievement/presentation/widgets/achievement_unlock_dialog.dart` (1569 lines)
- Four rarity levels with distinct animations:
  - Common: fade+scale, no particles
  - Rare: elastic scale, glow rings, 25 confetti particles
  - Epic: rotation + elastic scale, pulsing waves, 60 confetti, particle overlay
  - Legendary: small-scale elastic, rainbow explosion, 120 confetti, 50 particle overlay, rotating icon, legendary aura (3s)
- Combo banner shows when `comboCount >= 2` with gradient badge
- First unlocker badge displayed when `event.isFirst == true`
- Context story section shows `_buildEvidenceSection`
- Reward preview section shows all reward types
- Glory lines section shows percentile-based brag lines
- Surface preview section shows where rewards will be displayed
- Visual element preview section with glow animation
- Share button wired to `onShare` callback
- "View Rewards" button wired to `onViewRewards` callback
- `showFromWsEvent` factory method converts `chat.AchievementUnlockEvent` to model
- `pendingAchievementUnlockProvider` in achievement_provider.dart queues and manages combo dialog display
- `BgmService.boostTemporarily()` and `SensoryFeedbackService` emit tactile feedback per rarity
- ReduceMotion respected (stops glow/particle controllers)

### P2 Findings

**P2-B1: Milestone info `fromProgress` factory references `S.achievementUnlockMilestoneProgress` which is a static accessor**
- File: `mobile/lib/features/achievement/presentation/widgets/achievement_unlock_dialog.dart:1541-1543`
- The `MilestoneInfo.fromProgress` factory uses `S.achievementUnlockMilestoneProgress` (a static localization accessor) and `S.achievementUnlockPhotonReward10/25/50/100`. These static `S.` references bypass `AppLocalizations.of(context)`, which may return Chinese strings regardless of user locale setting if the static `S` class is not locale-aware. However, since milestone progress rewards are currently display-only (not granted), this is low severity.

---

## 3. Streak System

### Verified Working
- Quality-gated streak system fully implemented:
  - `StreakQualityService` at `backend/app/services/streak_quality.py` computes quality from 5 dimensions:
    - Effective minutes (32%), Core tasks completed (26%), Difficult breakthroughs (20%), Plan consistency (14%), Recovery score (8%)
  - Quality threshold: `quality_score >= 0.60` AND (`effective_minutes >= 25` OR `core_tasks_completed > 0` OR `difficult_breakthroughs > 0`)
  - `is_quality_day` flag determines ACTIVE vs WEAK status
- `StreakDayStatus` enum: `ACTIVE`, `WEAK`, `FROZEN`, `MISSED`
- `current_streak` synced to quality-gated value in `_update_streak_stats` (line 2086-2096)
- Streak protection (freeze charges): consumed when days missed, capped at `max_freeze_charges`
- Streak break: resets `current_streak = 1`, marks missed days as `MISSED`
- `StreakQualityIndicator` widget at `mobile/lib/features/achievement/presentation/widgets/streak_quality_indicator.dart`
  - Double-ring visualization (outer = quality streak, inner = raw streak)
  - Bottom sheet with 5-tile breakdown grid, 7-day quality trend bars, evidence card
  - Fallback to raw streak when quality service unavailable
- `StreakDetailsScreen` exists for detailed streak calendar
- Fatigue/crisis integration: reduces quality score for critical fatigue and active crisis states
- Late-night penalty: caps quality at 0.75 for sessions after 23:00

### P1 Findings

**P1-C1: `quality_streak` method iterates up to 90 days with individual `compute_quality` calls**
- File: `backend/app/services/streak_quality.py:148-156`
- Each `compute_quality` call does 5+ DB queries (effective_minutes, core_tasks, breakthroughs, plan_consistency, recovery_score). For a 30-day quality streak, that's 150+ DB queries in a single request. No batch optimization.
- Impact: High latency on the streak quality API endpoint for users with long streaks. Should cache computed values or batch the lookback.

### P2 Findings

**P2-C1: No visual feedback in Flutter when streak breaks**
- The streak break logic exists in Python (`achievement_engine.py:2032-2036` sets `current_streak = 1` and logs it), but there is no corresponding Flutter widget or WS event that shows "your streak broke" to the user. The user would only discover the break by noticing the streak counter decreased on the home screen.
- This is a UX gap, not a data integrity issue.

---

## 4. Growth Chronicle

### Verified Working
- `GrowthChroniclePage` at `mobile/lib/features/insights/presentation/pages/growth_chronicle_page.dart`
  - Route registered at `/learning/insights/growth-chronicle` in `insights_routes.dart:14`
  - Weekly story card with narrative, key insights, next-week suggestion
  - Timeline items with entry type icons and status pills
  - User actions: confirm, edit, reject with undo snackbars
  - Empty state with descriptive messaging
  - Pull-to-refresh
- `GrowthChronicleService` at `backend/app/signals/growth_chronicle.py`
  - Entry types: `milestone`, `turning_point`, `pattern_discovered`, `user_reflection`
  - Valid user statuses: `pending`, `confirmed`, `edited`, `rejected`, `hidden`
  - Redis-backed with 2-year TTL + PostgreSQL persistence via `GrowthChronicleSnapshot` model
  - Achievement unlocks generate chronicle entries via `_record_chronicle_unlock` in achievement_engine.py
  - `AchievementEventConsumer._persist_chronicle_event` also persists to PostgreSQL
- `_GrowthExperienceDashboardBuilder` at `backend/app/api/v1/experience/dashboard_router.py:91-100` fetches chronicle entries for the dashboard

### P1 Findings

**P1-D1: Chronicle `updateEntryStatus` on Flutter side calls provider but no backend API endpoint exists for status update**
- File: `mobile/lib/features/insights/presentation/pages/growth_chronicle_page.dart:96-118`
- The `_updateStatus` method calls `ref.read(growthDashboardProvider.notifier).updateEntryStatus(entry.id, status)`. This updates local Riverpod state, but there is no corresponding REST API endpoint to persist the status change to Redis or PostgreSQL. The status change is lost on refresh.
- Impact: Users can confirm/edit/reject chronicle entries but their choices are not persisted server-side.

### P2 Findings

**P2-D1: Chronicle entries from achievement unlocks always use `entry_type="milestone"`**
- File: `backend/app/services/achievement_engine.py:1524`
- All achievement-triggered chronicle entries use `entry_type="milestone"` regardless of achievement type. Hidden achievements, streak achievements, or sprint achievements could have more specific entry types (e.g., `pattern_discovered` for hidden achievements).

**P2-D2: No dedicated chronicle REST API for CRUD operations**
- Chronicle entries are created internally (via achievement engine, event consumer) and read via the dashboard aggregate endpoint, but there is no standalone endpoint for listing, updating, or deleting chronicle entries. The `growth.py` router only has a `return-case-file` endpoint.

---

## 5. Learning Dashboard

### Verified Working
- `LearningDashboardPage` at `mobile/lib/features/insights/presentation/pages/learning_dashboard_page.dart`
  - Route registered at `/learning/insights/dashboard` in `insights_routes.dart:15`
  - Metrics displayed: time distribution, efficiency metrics, weakness radar, knowledge changes, plan stability
  - Data calculated from real DB queries in `_GrowthExperienceDashboardBuilder`
  - Progressive lookback: new users (<7 days) get lookback since registration date
  - Empty state for users with no data
  - Model update receipts section
- Backend: `_GrowthExperienceDashboardBuilder` at `dashboard_router.py` queries FocusSession, Task, StudyRecord, UserNodeStatus, KnowledgeNode for real metrics

### P2 Findings

**P2-E1: No dedicated "placeholder for <7 days" new user experience on dashboard**
- The progressive lookback computes correct days_active for new users, but there is no special onboarding or guidance content on the dashboard for users in their first week. The empty state shows a generic message.

**P2-E2: Dashboard data is computed synchronously on every request**
- File: `backend/app/api/v1/experience/dashboard_router.py:56-81`
- Each dashboard request triggers 6+ async queries (time_distribution, efficiency_metrics, weakness_radar, knowledge_changes, plan_stability, chronicle_entries, weekly_narrative). No caching layer for the aggregate. The `rebuild` query parameter on the growth endpoint suggests cache awareness, but the dashboard endpoint itself has no caching.

---

## 6. Daily Reflection

### Verified Working
- `ReflectionSummaryScreen` at `mobile/lib/features/reflection/presentation/screens/reflection_summary_screen.dart`
  - Route registered at `/reflection/summary` in `reflection_routes.dart`
- `ReflectionDialog` at `mobile/lib/features/focus/presentation/widgets/reflection_dialog.dart`
  - Triggered after focus sessions for post-session reflection
- Reflection data flows to chronicle via the event consumer pipeline
- Home screen prompt: integration exists through the experience/envelope system

### P2 Findings

**P2-F1: Reflection route is only `/reflection/summary` -- no dedicated daily reflection trigger from home screen**
- The reflection screen exists but there is no home screen widget or daily prompt card that navigates directly to a "today's reflection" experience. The reflection is only triggered after focus sessions. Users who do not use focus mode have no obvious path to daily reflection from the home screen.

---

## 7. Reward System

### Verified Working
- **Photon grants**: `PhotonService.grant_photons` called with `PhotonTransactionType.GRANT_ACHIEVEMENT`, amounts from seed data (10-5000 photons per achievement). Retry mechanism via Celery + local 3-attempt fallback.
- **Titles**: `UserTitle` model with `title_id`, `title_name`, `source_achievement_id`. Equipment service supports equip/unequip.
- **Galaxy skins**: `UserGalaxySkin` model with `skin_id`, `unlock_source`. 6 skins defined. Equipment service supports equip/unequip.
- **Visual elements**: `VisualElementService.unlock_element` called for `visual_element` reward type. 28 visual elements defined in seeds across 8 categories (default, streak, sprint, exploration, hidden, mastery, prestige, persona).
- **Go Gateway**: Full proxy routes for `/achievements/skins`, `/achievements/skins/:skinId/equip`, `/achievements/titles`, `/achievements/titles/:titleId/equip` (proxy_routes.go:265-268).
- **Equipment service**: Separate `equip_achievement_skin`, `equip_achievement_title`, `unequip_skin`, `unequip_title` methods. Validates ownership before equip.
- **Photon amounts** in seeds: range from 10 (first_light) to 5000 (nodes_500, study_1000hours, all_sectors)

### P2 Findings

**P2-G1: Photon reward retry only covers `photon` reward type**
- File: `backend/app/services/achievement_engine.py:1612-1735`
- The `_schedule_photon_reward_retry` and `_retry_photon_reward_locally` methods handle photon grant failures with Celery + local retry. But `title`, `galaxy_skin`, and `freeze_charge` reward types have no retry mechanism. If `_unlock_title` or `_unlock_galaxy_skin` fails due to a transient DB error, the reward is silently lost.

**P2-G2: `AchievementRewardObservability` records events but no alerting or dashboard exists**
- File: `backend/app/services/achievement_reward_observability.py`
- The observability service records photon reward lifecycle events (scheduled, enqueued, retry_succeeded, retry_failed, exhausted) but there is no monitoring dashboard or alert configured for the "exhausted" state. Failed rewards could go unnoticed.

---

## 8. Milestone Celebration

### Verified Working
- `MilestoneCelebrationScreen` at `mobile/lib/features/achievement/presentation/screens/milestone_celebration_screen.dart` (593 lines)
  - Route: `/achievements/milestone/:milestoneId` in `achievement_routes.dart:23`
  - Accepts `MilestoneCelebrationPayload` with query parameters or map
  - Hero card with animated number counter (1.4s animation)
  - Background gradient with glow orbs
  - Stats chips for study_days, mastered_nodes, completed_sprints, error_count
  - Share button: captures `RepaintBoundary` as PNG and shares via `UniversalShareService`
  - "Continue Learning" button navigates to home
  - ReduceMotion respected (instantly completes number animation)
- `AchievementEventConsumer._maybe_create_milestone_notification` creates rich notifications for rarity >= rare
- Deep links generated: `sparkle://milestone/{achievementId}?query_params`

### P1 Findings

**P1-H1: Milestone celebration screen only has custom copy for 3 milestone IDs**
- File: `mobile/lib/features/achievement/presentation/screens/milestone_celebration_screen.dart:96-128`
- The `MilestoneCelebrationPayload` has custom `unitLabel`, `headline`, `subheadline`, `badgeLabel`, and `_defaultCelebrationValue` only for 3 IDs: `30_day_learner`, `knowledge_explorer_50`, `sprint_veteran`. All other milestone achievements fall through to generic defaults ("30" celebration value, "days" unit, "Core Sparkle User" badge).
- In `achievement_event_consumer.py:585-639`, `_build_milestone_copy` has custom copy for 10 IDs: `30_day_learner`, `knowledge_explorer_50`, `sprint_veteran`, `first_task`, `week_streak_7`, `galaxy_explorer`, `focus_master`, `reflection_starter`, `plan_creator`, `community_joined`. But only 3 of these (`30_day_learner`, `knowledge_explorer_50`, `sprint_veteran`) match actual achievement seed IDs. The other 7 (`first_task`, `week_streak_7`, `galaxy_explorer`, `focus_master`, `reflection_starter`, `plan_creator`, `community_joined`) do not correspond to any achievement ID in the seed data, making their custom copy unreachable.
- Impact: 36 out of 39 achievements get generic milestone celebration copy instead of personalized messaging.

### P2 Findings

**P2-H1: Share hashtag always uses default `#Sparkle里程碑` except for `30_day_learner`**
- File: `backend/app/services/achievement_event_consumer.py:474` and `mobile milestone_celebration_screen.dart:128`
- Only the 30-day milestone gets `#30天打卡`; all others share the same generic hashtag.

---

## Verified Working (Cross-Cutting)

### Full Pipeline: Achievement Engine → Event Bus → WebSocket → Flutter
1. `AchievementEngine.process_event()` evaluates progress and unlocks achievements
2. After DB commit, `_notify_unlocks()` sends `{"type": "achievement_unlock", "achievement_data": {...}}` via `ws_manager.send_personal_message()`
3. `AchievementEventConsumer` on Redis Streams consumes events for secondary effects (cognitive fragments, community broadcast, milestone notifications, chronicle persistence, profile signals)
4. Flutter `pendingAchievementUnlockProvider` queues WS events and shows `AchievementUnlockDialog` with combo counting

### Achievement Map
- `get_achievement_map()` generates a node graph with 5 prestige lanes (streak, sprint, conquest, hidden, prestige)
- Nodes have display_state: `unlocked`, `close_to_unlock`, `ready_to_pursue`, `blocked`, `hidden_unrevealed`
- Connections: prerequisite and parent relationships
- Recommended target node computed based on proximity and rarity

### Achievement Stats API
- `get_achievement_stats()` returns total counts, per-rarity breakdown, streak, total photons
- Close-to-unlock API (`get_close_to_unlock_achievements`) returns achievements at >= 80% progress

### Data Models
- `Achievement` model with i18n support (`get_localized_name`, `get_localized_description`)
- `UserAchievement` with progress tracking, context snapshot, share count
- `UserStreakStats` with current_streak, max_streak, freeze_charges, max_freeze_charges
- `UserStreakDay` with day-level status tracking (ACTIVE, WEAK, FROZEN, MISSED)
- `SessionCompletion` for idempotency
- `SparkContract` for learning contracts with photon staking

---

## Priority Summary

| ID | Severity | Area | Finding |
|----|----------|------|---------|
| P1-A1 | P1 | Achievement Pipeline | Combo bonus photons computed but never granted |
| P1-C1 | P1 | Streak System | `quality_streak` does 150+ DB queries for 30-day streaks |
| P1-D1 | P1 | Growth Chronicle | `updateEntryStatus` not persisted to backend |
| P1-H1 | P1 | Milestone Celebration | Only 3/39 achievements have custom celebration copy |
| P2-A1 | P2 | Achievement Pipeline | Sprint start events never trigger sprint count achievements |
| P2-A2 | P2 | Achievement Pipeline | Double streak day write on quality evaluation |
| P2-B1 | P2 | Unlock Dialog | MilestoneInfo uses static `S.` accessor, may ignore locale |
| P2-C1 | P2 | Streak System | No visual feedback when streak breaks |
| P2-D1 | P2 | Growth Chronicle | All achievement chronicle entries use generic "milestone" type |
| P2-D2 | P2 | Growth Chronicle | No standalone CRUD API for chronicle entries |
| P2-E1 | P2 | Learning Dashboard | No special new-user onboarding guidance on dashboard |
| P2-E2 | P2 | Learning Dashboard | No caching on dashboard aggregate endpoint |
| P2-F1 | P2 | Daily Reflection | No home screen prompt for non-focus users |
| P2-G1 | P2 | Reward System | No retry for title/skin/freeze_charge rewards |
| P2-G2 | P2 | Reward System | No alerting for exhausted photon reward retries |
| P2-H1 | P2 | Milestone Celebration | Generic share hashtag for most milestones |
