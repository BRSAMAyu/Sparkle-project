# R4-O2: Backend-to-Frontend Data Flow Audit

> **Date**: 2026-05-06
> **Auditor**: Automated deep audit
> **Scope**: 7 major providers -- model fields vs. UI-rendered fields
> **Core Question**: "Backend is powerful but frontend doesn't surface it"

---

## Executive Summary

| Provider | Model Fields | Rendered | Gap | Severity |
|----------|:---:|:---:|:---:|:---:|
| understandingSnapshot | 10 | 8 | 2 | LOW |
| experienceEnvelope | 7 | 3 | 4 | **HIGH** |
| streakQuality | 13 (nested) | 11 | 2 | MEDIUM |
| goalDetail | 25+ (nested) | 23+ | 2 | LOW |
| planList / activePlan | 21 | 8 | 13 | **HIGH** |
| galaxy | 24 (node model) | 18 | 6 | MEDIUM |
| achievement | 21 (main model) | 15 | 6 | MEDIUM |

**Verdict**: Two HIGH-severity gaps where rich backend data is structurally ignored. The plan model has 13 fields that never reach the screen. The experience envelope's profileContext and userState maps are received but never surfaced to the user. These represent meaningful product opportunities.

---

## 1. understandingSnapshotProvider

**Model**: `UnderstandingSnapshot` (`experience_models.dart`)
**Consumer**: `understanding_snapshot_card.dart`

### Model Fields (10)

| # | Field | Type | Rendered? | Notes |
|---|-------|------|:---------:|-------|
| 1 | `active` | `bool` | Indirect | Controls whether card appears |
| 2 | `status` | `String` | YES | Drives accent color (risk_found/needs_confirm vs default) |
| 3 | `summary` | `String` | YES | Main body text (lines 110-123) |
| 4 | `confidence` | `double` | YES | ConfidencePill percentage badge |
| 5 | `energyLevel` | `String?` | **NO** | Never read in the card |
| 6 | `evidence` | `List<String>` | YES | Rendered as TinyEvidenceChips (first 3) |
| 7 | `memoryClaims` | `List<String>` | PARTIAL | Fallback if evidence is empty |
| 8 | `openQuestions` | `List<String>` | PARTIAL | Only first question shown |
| 9 | `nextStepLabel` | `String?` | YES | Shown as success-colored chip |
| 10 | `updatedAt` | `DateTime?` | **NO** | Never displayed |

**Gap count**: 2 fields never rendered (`energyLevel`, `updatedAt`). 2 fields partially rendered (`memoryClaims` as fallback, `openQuestions` only first).

**Severity**: **LOW**
- `energyLevel` is a low-impact UX field. Could power a color/icon hint.
- `updatedAt` is useful for freshness indication but not critical.

---

## 2. experienceEnvelopeProvider

**Model**: `ExperienceEnvelope` (`experience_envelope.dart`)
**Consumer**: `experience_envelope_indicator.dart`
**Integration**: Confirmed rendered in `chat_screen.dart` (line 1945)

### Model Fields (7)

| # | Field | Type | Rendered? | Notes |
|---|-------|------|:---------:|-------|
| 1 | `traceId` | `String?` | **NO** | Debug/observability only, not user-visible |
| 2 | `turnId` | `String?` | **NO** | Debug/observability only |
| 3 | `userState` | `Map<String, dynamic>` | **NO** | Rich state data (cognitive_phase, srl_stage, etc.) -- never shown |
| 4 | `profileContext` | `Map<String, dynamic>` | **NO** | Profile adjustments, learning style -- never shown |
| 5 | `structuredCognitiveAdjustments` | `List<Map>` | YES | Dimension/value/reason chips |
| 6 | `raw` | `Map<String, dynamic>` | **NO** | Passthrough metadata |
| 7 | `updatedAt` | `DateTime?` | **NO** | Never displayed |

**Gap count**: 4 fields never rendered. Critically, `userState` and `profileContext` are dense maps of cognitive data that the backend computes but the frontend never surfaces.

**Severity**: **HIGH**

The indicator only shows `structuredCognitiveAdjustments` as dimension chips. The real gold is in `userState` and `profileContext` which contain:
- Cognitive phase / SRL stage
- Learning style preferences
- Adjusted tone/verbosity/challenge parameters
- Motivation and emotion state

None of this reaches the user. The backend is doing rich cognitive modeling but the UI shows only "Aurora adapting" with adjustment chips.

---

## 3. streakQualityProvider

**Model**: `StreakQualitySnapshot` + nested `StreakQuality`, `StreakQualityTrendPoint`, `StreakCelebrationTrigger`
**Consumer**: `streak_quality_indicator.dart`

### StreakQualitySnapshot (5 fields)

| # | Field | Type | Rendered? | Notes |
|---|-------|------|:---------:|-------|
| 1 | `currentStreak` | `int` | YES | Inner ring in quality ring painter |
| 2 | `qualityStreak` | `int` | YES | Outer ring + center number |
| 3 | `todayQuality` | `StreakQuality` | YES | Full breakdown grid |
| 4 | `weeklyQualityTrend` | `List<StreakQualityTrendPoint>` | PARTIAL | Bar chart shows qualityScore only, not full breakdown |
| 5 | `celebrationTrigger` | `StreakCelebrationTrigger?` | PARTIAL | Evidence shown, reason and suggestedMessage not surfaced |

### StreakQuality (7 fields)

| # | Field | Type | Rendered? | Notes |
|---|-------|------|:---------:|-------|
| 1 | `effectiveMinutes` | `int` | YES | Breakdown grid tile |
| 2 | `coreTasksCompleted` | `int` | YES | Breakdown grid tile |
| 3 | `difficultBreakthroughs` | `int` | YES | Breakdown grid tile |
| 4 | `planConsistency` | `double` | YES | Breakdown grid tile |
| 5 | `recoveryScore` | `double` | **NO** | Never rendered in breakdown grid or anywhere |
| 6 | `qualityScore` | `double` | YES | Overall score display |
| 7 | `isQualityDay` | `bool` | YES | Drives accent color |

### StreakCelebrationTrigger (3 fields)

| # | Field | Type | Rendered? | Notes |
|---|-------|------|:---------:|-------|
| 1 | `reason` | `String` | **NO** | Not shown |
| 2 | `evidence` | `String` | YES | Shown in EvidenceCard |
| 3 | `suggestedMessage` | `String` | **NO** | Not shown (could be a CTA message) |

**Gap count**: 3 fields never rendered (`recoveryScore`, `celebrationTrigger.reason`, `celebrationTrigger.suggestedMessage`). Weekly trend breakdown is partially used (only qualityScore of each point, not the full breakdown sub-object).

**Severity**: **MEDIUM**
- `recoveryScore` is a meaningful metric -- it measures how well the user recovers from low-quality days. Not showing it loses a motivational dimension.
- `suggestedMessage` from celebration triggers is a wasted engagement opportunity. The backend generates a personalized congratulatory message that never reaches the user.

---

## 4. goalDetailProvider

**Model**: `GoalDetailData` with nested models (`goal_detail_provider.dart`)
**Consumer**: `goal_detail_page.dart`

### GoalSummary (8 fields)

| # | Field | Type | Rendered? | Notes |
|---|-------|------|:---------:|-------|
| 1 | `id` | `String` | Indirect | Used for navigation |
| 2 | `title` | `String` | YES | Header title |
| 3 | `goalType` | `String` | **NO** | Never shown in the UI |
| 4 | `status` | `String` | YES | Status chip |
| 5 | `targetDate` | `String?` | YES | Date chip |
| 6 | `mastery` | `double` | YES | Mastery chip percentage |
| 7 | `progress` | `double` | YES | Circular progress indicator |
| 8 | `priority` | `String` | YES | Priority chip |

### GoalDetailData composite (9 fields)

| # | Field | Type | Rendered? | Notes |
|---|-------|------|:---------:|-------|
| 1 | `goal` | `GoalSummary` | YES | Full header rendering |
| 2 | `minimumAcceptanceCriteria` | `MinimumAcceptanceCriteria` | YES | MinimumCriteriaCard with thresholds |
| 3 | `planHealth` | `PlanHealth` | YES | Plan health band with 3 metrics |
| 4 | `currentPhase` | `CurrentPhase` | YES | Phase name chip |
| 5 | `todaysMinimalNextStep` | `TodaysMinimalNextStep` | YES | Full today step card |
| 6 | `knowledgeBottlenecks` | `List<KnowledgeBottleneck>` | YES | GoalBottleneckStrip |
| 7 | `accountabilityStatus` | `AccountabilityStatusSummary` | YES | Accountability card |
| 8 | `relatedSources` | `List<RelatedSource>` | YES | Related sources card |
| 9 | `strategyBelief` | `StrategyBeliefView?` | YES | StrategyMigrationWizard |

**Gap count**: 1 field never rendered (`goalType`). All other data flows are complete.

**Severity**: **LOW**
- `goalType` (e.g., "exam_prep", "skill_building") could help the user understand their goal category, but it's not a significant data loss. The page is one of the most complete in the codebase.

---

## 5. planListProvider / activePlanProvider

**Model**: `PlanModel` (`plan_model.dart`)
**Consumers**: `sprint_screen.dart`, `sprint_review_screen.dart`

### PlanModel Fields (21)

| # | Field | Type | Rendered? | Notes |
|---|-------|------|:---------:|-------|
| 1 | `id` | `String` | Indirect | Navigation, data key |
| 2 | `userId` | `String` | **NO** | Internal only |
| 3 | `name` | `String` | YES | Sprint header title, review hero |
| 4 | `type` | `PlanType` | YES | Filters sprint type in sprint_screen |
| 5 | `description` | `String?` | YES | Parsed via PlanDescriptionCodec, overview + schedule shown |
| 6 | `targetDate` | `DateTime?` | YES | Days-left calculation |
| 7 | `subject` | `String?` | **NO** | Subject/domain never displayed |
| 8 | `dailyAvailableMinutes` | `int` | **NO** | Available study time budget not shown |
| 9 | `totalEstimatedHours` | `double?` | **NO** | Total effort estimate not shown |
| 10 | `masteryLevel` | `double` | **NO** | Mastery level never shown |
| 11 | `progress` | `double` | YES | Progress bar, hero percentage |
| 12 | `healthScore` | `double?` | **NO** | Plan health score not surfaced |
| 13 | `healthStatus` | `String?` | **NO** | Plan health status not surfaced |
| 14 | `healthReasons` | `List<String>` | **NO** | Health issue reasons not shown |
| 15 | `isActive` | `bool` | Indirect | Filters active plans |
| 16 | `createdAt` | `DateTime` | **NO** | Not displayed |
| 17 | `updatedAt` | `DateTime` | **NO** | Not displayed |
| 18 | `tasks` | `List<TaskModel>?` | YES | Rendered as TaskCards |
| 19 | `source` | `String?` | **NO** | Plan origin (wizard/chat/etc) not shown |
| 20 | `sourceMetadata` | `Map?` | PARTIAL | Only `sprint_review_notes` read in review screen |
| 21 | `dayHighlights` | `PlanDayHighlights?` | **NO** | Day-specific recommendations never shown |
| 22 | `planStage` | `PlanStage` | **NO** | Sprint/daily/review/paused stage not shown |
| 23 | `priority` | `PlanPriority` | **NO** | critical/high/normal/low not shown |
| 24 | `isPrimary` | `bool` | **NO** | Primary plan indicator not shown |

**Gap count**: 13 fields never rendered. This is the worst data flow gap in the codebase.

**Severity**: **HIGH**

The backend computes rich plan diagnostics that are completely invisible:
- **healthScore/healthStatus/healthReasons**: A 3-part health assessment that could show plan viability. The sprint review screen derives its own ad-hoc bottleneck analysis from progress/daysLeft instead of using the structured backend data.
- **masteryLevel**: Current mastery against the goal -- a core metric.
- **dailyAvailableMinutes / totalEstimatedHours**: Time budget information that would help users plan.
- **planStage**: Whether the plan is in sprint, daily, review, or paused phase.
- **priority**: Whether the plan is critical/high/normal/low.
- **dayHighlights**: Per-day recommendations with tasks -- the backend curates the optimal day plan, but the frontend ignores it.
- **subject**: The exam or subject area the plan covers.

---

## 6. galaxyProvider

**Model**: `GalaxyNodeModel` (`galaxy_model.dart`)
**Consumers**: `galaxy_screen.dart`, `galaxy_node_preview_card.dart`, `star_map_painter.dart`

### GalaxyNodeModel Fields (24)

| # | Field | Type | Rendered? | Notes |
|---|-------|------|:---------:|-------|
| 1 | `id` | `String` | Indirect | Data key, navigation |
| 2 | `parentId` | `String?` | **NO** | Hierarchical grouping not shown |
| 3 | `name` | `String` | YES | Node label, preview card |
| 4 | `importance` | `int` (1-5) | YES | Drives node radius |
| 5 | `sector` | `SectorEnum` | YES | Color coding, sector name |
| 6 | `baseColor` | `String?` | YES | Star map rendering |
| 7 | `glowColor` | `String?` | YES | Preview card styling |
| 8 | `sectorWeights` | `Map<SectorEnum, double>` | **NO** | Cross-sector relevance never displayed |
| 9 | `isUnlocked` | `bool` | YES | Unlocked vs locked visual state |
| 10 | `masteryScore` | `int` | YES | Preview card, progress bar |
| 11 | `studyCount` | `int` | **NO** | Study frequency not shown in preview or map |
| 12 | `recentErrorCount` | `int` | YES | Error cluster tint in star_map_painter |
| 13 | `reviewUrgencyScore` | `double` | YES | Review urgency indicator |
| 14 | `isReviewRecommended` | `bool` | YES | Pulse animation trigger |
| 15 | `reviewUrgencyReason` | `String?` | YES | Review prompt text |
| 16 | `masteryLastUpdatedAt` | `DateTime?` | **NO** | Not displayed (daysSinceMasteryUpdate is used instead) |
| 17 | `daysSinceMasteryUpdate` | `double` | YES | "Days since mastery" text |
| 18 | `firstUnlockAt` | `DateTime?` | **NO** | Discovery date not shown |
| 19 | `tags` | `List<String>?` | PARTIAL | Only first tag passed to CompactKnowledgeNode |
| 20 | `description` | `String?` | YES | Preview card description section |
| 21 | `positionHint` | `NodePositionHint?` | YES (internal) | Used by layout engine |
| 22 | `outgoingEdgeIds` | `List<String>?` | YES (internal) | Edge rendering |
| 23 | `incomingEdgeIds` | `List<String>?` | YES (internal) | Edge rendering |
| 24 | `positionX/positionY` | `double?` | YES | Canvas positioning |

**Gap count**: 5 fields never rendered, 1 partially.

**Severity**: **MEDIUM**
- `studyCount` is a useful engagement metric -- "you've studied this topic X times" -- that would add depth to the preview card.
- `sectorWeights` showing cross-domain connections (e.g., "30% physics, 70% math") would enrich understanding.
- `firstUnlockAt` could show "discovered 3 weeks ago" for engagement.
- `parentId` hierarchy is structural but could power a breadcrumb trail.
- `tags` are truncated to only the first tag.

---

## 7. achievementProvider

**Model**: `AchievementModel` (`achievement_model.dart`)
**Consumers**: `achievement_list_screen.dart`, `achievement_map_screen.dart`, `achievement_detail_screen.dart`

### AchievementModel Fields (21)

| # | Field | Type | Rendered? | Notes |
|---|-------|------|:---------:|-------|
| 1 | `id` | `String` | Indirect | Navigation key |
| 2 | `name` | `String` | YES | Card, map node, detail title |
| 3 | `description` | `String?` | YES | Card subtitle, detail body |
| 4 | `iconUrl` | `String?` | **NO** | Never used -- cards use category-based icons |
| 5 | `type` | `AchievementType` | YES | Category icon mapping in map |
| 6 | `rarity` | `AchievementRarity` | YES | Color coding everywhere |
| 7 | `category` | `String?` | YES | Filter tabs |
| 8 | `isHidden` | `bool` | YES | Hidden achievement handling |
| 9 | `hint` | `String?` | PARTIAL | Used in detail screen only |
| 10 | `sortOrder` | `int` | **NO** | Sort order from backend not used (frontend sorts by progress) |
| 11 | `parentId` | `String?` | **NO** | Achievement hierarchy not shown |
| 12 | `triggerCode` | `String?` | **NO** | Internal trigger logic |
| 13 | `triggerConfig` | `Map?` | **NO** | Internal trigger config |
| 14 | `prerequisites` | `List<String>?` | YES | Detail screen prerequisite section |
| 15 | `visualEffectType` | `VisualEffectType` | PARTIAL | Used in unlock event, not in list/map cards |
| 16 | `visualConfig` | `Map?` | **NO** | Visual effect configuration |
| 17 | `rewardConfig` | `List<Map>?` | YES | Detail screen rewards section |
| 18 | `activeFrom` | `DateTime?` | YES | Limited-time section filtering |
| 19 | `activeTo` | `DateTime?` | YES | Countdown display |
| 20 | `isLimited` | `bool` | YES | Limited-time section filtering |
| 21 | `eventTag` | `String?` | YES | Event tag badge on limited cards |
| 22 | `totalUnlocked` | `int` | **NO** | Global unlock count (rarity indicator) not shown |
| 23 | `createdAt` | `DateTime` | **NO** | Not displayed |
| 24 | `updatedAt` | `DateTime` | **NO** | Not displayed |

### UserAchievementProgress Fields (10)

| # | Field | Type | Rendered? | Notes |
|---|-------|------|:---------:|-------|
| 1 | `achievementId` | `String` | Indirect | Link key |
| 2 | `progress` | `double` | YES | Progress bar |
| 3 | `progressValue` | `int` | YES | Remaining calculation |
| 4 | `progressTarget` | `int` | YES | Remaining calculation |
| 5 | `isPinned` | `bool` | **NO** | Pin status not surfaced |
| 6 | `shareCount` | `int` | **NO** | Share history not shown |
| 7 | `isFirstUnlocker` | `bool` | PARTIAL | Used in share card, not in main list |
| 8 | `unlockedAt` | `DateTime?` | **NO** | Unlock date not shown in list or map |
| 9 | `lastProgressUpdate` | `DateTime?` | **NO** | Recency indicator not shown |
| 10 | `contextSnapshot` | `Map?` | **NO** | Context of unlock not shown |
| 11 | `contextStory` | `String?` | **NO** | Narrative of unlock not shown |

**Gap count**: 6 model fields + 5 progress fields never rendered.

**Severity**: **MEDIUM**
- `iconUrl` is a missed visual richness opportunity -- the backend provides custom achievement art but the frontend uses generic category icons.
- `totalUnlocked` (how many users globally unlocked this) would add social proof.
- `unlockedAt` / `contextStory` from progress are rich narrative data points that could power "Your achievement journey" storytelling.
- `isPinned` and `shareCount` are user preferences that should be actionable.

---

## Summary of Findings

### HIGH Severity (2)

1. **planListProvider** -- 13 of 21 fields never rendered. Backend computes `healthScore`, `healthStatus`, `healthReasons`, `masteryLevel`, `dailyAvailableMinutes`, `totalEstimatedHours`, `planStage`, `priority`, `dayHighlights`, `subject` -- all invisible. The sprint review screen does its own ad-hoc analysis instead of using the structured backend data.

2. **experienceEnvelopeProvider** -- 4 of 7 fields never rendered. The `userState` and `profileContext` maps contain cognitive state, learning style, and adjusted parameters that could power a rich "How Sparkle sees you" experience. Only the structured cognitive adjustments are surfaced as small chips.

### MEDIUM Severity (3)

3. **streakQualityProvider** -- `recoveryScore` (resilience metric) and `suggestedMessage` (personalized celebration text) are computed but never shown.

4. **galaxyProvider** -- `studyCount`, `sectorWeights`, `firstUnlockAt`, `parentId`, `tags` (truncated) are available but not surfaced in the preview card or map.

5. **achievementProvider** -- `iconUrl` (custom art), `totalUnlocked` (social proof), `unlockedAt`/`contextStory` (narrative), `isPinned`/`shareCount` (user preferences) are all ignored.

### LOW Severity (2)

6. **goalDetailProvider** -- Nearly complete. Only `goalType` is not displayed.

7. **understandingSnapshotProvider** -- `energyLevel` and `updatedAt` are the only gaps.

---

## Recommendations (Priority Order)

| Priority | Action | Impact |
|----------|--------|--------|
| P0 | **Sprint screen**: Render `healthScore`/`healthStatus`/`healthReasons` as a health banner. Replace ad-hoc bottleneck derivation with structured backend data. | Users see real plan diagnostics instead of guesswork |
| P0 | **Sprint screen**: Show `masteryLevel`, `planStage`, `priority`, `subject` as info chips in the sprint header. | Users understand their plan context |
| P1 | **Experience envelope**: Surface `userState` summary in the understanding panel (e.g., "Cognitive phase: Planning | SRL stage: Execution | Learning style: Visual") | Users see the AI's model of them |
| P1 | **Streak quality**: Add `recoveryScore` as a 5th breakdown tile. Show `suggestedMessage` in celebration bottom sheet. | Recovery resilience becomes visible |
| P2 | **Galaxy preview**: Add `studyCount` ("Studied X times") and full `tags` list to the node preview card. | Richer node context |
| P2 | **Achievement cards**: Use `iconUrl` when available. Show `totalUnlocked` as "X% of users". Display `unlockedAt` date. | Visual richness + social proof |
| P3 | **Plan day highlights**: Render `dayHighlights` as a "Today's Recommendation" section in the sprint screen. | Per-day guidance reaches users |
