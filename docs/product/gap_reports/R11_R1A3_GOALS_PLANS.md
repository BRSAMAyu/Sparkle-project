# R11-R1A3: Goals + Plans Journey Audit

**Audit Date**: 2026-05-07
**Auditor**: Claude Code (Automated Pre-Launch Audit)
**Scope**: Complete Goal and Plan management journey across Flutter, Go Gateway, and Python Engine

## Summary: FAIL -- 2 P0 blockers, 5 P1 issues, 7 P2 items

The Goals + Plans journey has a well-architected **goal creation wizard** and a sophisticated **plan review card**, but the core loop is broken: goal progress never updates from task completions, goal-to-plan navigation is missing, and the GoalWorldGraph is only accessible from the Galaxy screen rather than the Goal Detail page. These break the vision of Goals being the center of the experience.

---

## Critical Issues (P0): 2 issues that block launch

### Finding 1: Goal progress is never updated from task completions

- **Severity**: P0
- **User Impact**: Users complete tasks but goal progress stays at 0% forever. The "center of everything" shows no progress, making the entire goal system feel broken.
- **File**: `backend/app/models/goal.py:47-48` (Goal.progress column exists but is never written)
- **Current Code**: `Goal.progress` and `Goal.mastery` are columns on the `goals` table, initialized at 0.0 on creation. No code path anywhere in the backend updates these fields when tasks are completed.
- **Evidence**: Exhaustive grep for `goal.progress =`, `Goal.progress`, `goal\.mastery` across the entire `backend/` directory shows:
  - `goal_decomposition_service.py` creates goals with `status="active"`, `progress=0.0` (default)
  - `spine_orchestrator.py` handles `on_task_completed` but only processes signal detection and relationship model updates -- never writes back to Goal.progress
  - `plan_service.py` updates `Plan.progress` but never propagates to the associated Goal
  - The `TaskCompleted` event exists in `event_bus.py` but no consumer updates goal progress
  - The goal detail endpoint (`experience/goal_router.py:424-434`) computes a **synthetic** `plan_health.overall` score from plan progress + mastery + task_completion_rate, but this is only at read-time -- the stored `Goal.progress` column remains 0
- **Expected**: When tasks under a goal's plan are completed, `Goal.progress` should be updated to reflect actual progress. At minimum, task completion rate should write back to goal progress.
- **Fix**: Create a `GoalProgressConsumer` that listens to `TaskCompleted` events and recalculates `Goal.progress` as `completed_tasks / total_tasks` for the associated plan. Alternatively, add goal progress update to the existing `spine_orchestrator.on_task_completed()` method. The goal detail API already computes this on read, but the stored value should also be updated for list views and notifications.

### Finding 2: Goal-to-Plan navigation link is missing in goal detail

- **Severity**: P0
- **User Impact**: Users create a goal, see "See full plan" in the creation dialog, but when they arrive at the goal detail page there is no way to navigate to the plan. The hierarchy Goal -> Plan -> Task is broken at the Goal -> Plan link.
- **File**: `mobile/lib/features/goal/presentation/pages/goal_detail_page.dart:59-118` (goal detail body)
- **Current Code**: The `GoalDetailPage` renders these sections: GoalHeader, JourneyProgressFutureCard, StrategyMigrationWizard, MinimumCriteriaCard, GoalBottleneckStrip, TodayStepCard, PlanHealthBand, AccountabilityCard, RelatedSourcesCard, SimilarGoalPursuersCard. There is NO link/tap target to navigate to the associated plan detail screen (`/plans/{planId}`).
- **Expected**: A "View Plan" or "Plan Details" button/card that navigates to `/plans/{planId}` when tapped. The `GoalDetailData` model does not expose `plan_id`, though the backend `GoalSummaryPayload` could be extended.
- **Fix**: 
  1. Add `plan_id` to `GoalSummary` in `goal_detail_provider.dart` (backend already has `goal.plan_id`)
  2. Add a "View Plan" button/card in the goal detail page that navigates to `/plans/{planId}`
  3. Consider adding a `PlanHealthBand` tap handler that navigates to plan detail

---

## High Issues (P1): 5 issues that degrade experience significantly

### Finding 3: GoalWorldGraph not shown on Goal Detail page

- **Severity**: P1
- **User Impact**: The vision describes "already mastered" vs "need to conquer" visualization linked to the goal. The `GoalWorldGraphMiniPanel` widget exists and works but is only placed on the Galaxy screen. Users viewing a goal cannot see their knowledge graph.
- **File**: `mobile/lib/features/goal/presentation/pages/goal_detail_page.dart` (missing import)
- **Current Code**: Goal detail shows `GoalBottleneckStrip` with a flat list of bottleneck nodes, but not the interactive `GoalWorldGraphMiniPanel` with mastery bars, gap analysis, and expand/collapse.
- **Expected**: The goal detail page should show the `GoalWorldGraphMiniPanel` widget or at minimum link to the Galaxy screen with the goal's graph open.
- **Fix**: Import and place `GoalWorldGraphMiniPanel(goalId: goalId)` in the goal detail page, between the JourneyProgressCard and the MinimumCriteriaCard.

### Finding 4: Goal creation does not trigger plan generation

- **Severity**: P1
- **User Impact**: Users create a goal with milestones, but no plan is automatically generated. The goal's `plan_id` remains null. The plan creation flow is entirely separate (via `/plans` API or discovery flow). This disconnects the Goal->Plan relationship the vision describes.
- **File**: `backend/app/api/v1/goals.py:118-188` (`create_goal`)
- **Current Code**: Goal creation creates a `Goal` record and a first task from the first milestone, but does NOT create a `Plan` record. The `Goal.plan_id` column is never set. The milestones are stored in `metadata_payload` but not translated into a formal Plan with phases.
- **Expected**: After goal creation, the system should auto-generate an ExecutablePlan from the milestones and link it via `goal.plan_id`. The plan should have phases derived from the milestones.
- **Fix**: After creating the goal, call the plan creation service to generate a plan from the milestones. Set `goal.plan_id` to the created plan's ID. Consider using `GoalDecompositionService` milestones as plan phases.

### Finding 5: Goal quality evaluation not wired into creation flow

- **Severity**: P1
- **User Impact**: The `GoalQualityEvaluator` exists with specificity/measurability/time-bound scoring, but it is never called during goal creation. Users can create vague goals like "get better at stuff" with no AI feedback.
- **File**: `backend/app/orchestration/goal_quality_evaluator.py` (exists but unused in creation flow)
- **File**: `backend/app/api/v1/goals.py:118-188` (creation endpoint does not call evaluator)
- **Current Code**: The `GoalQualityEvaluator.evaluate()` method is well-implemented with LLM evaluation and heuristic fallback. It evaluates specificity, measurability, and time-bound dimensions with a 0.5 threshold. However, the `create_goal` endpoint never invokes it.
- **Expected**: After the user submits the goal form (or during the wizard's confirm step), the backend should run GoalQualityEvaluator and return clarification questions if the goal is too vague.
- **Fix**: Call `goal_quality_evaluator.evaluate()` in the `create_goal` endpoint. If `passed=False`, return the `clarification_questions` to the frontend. The Flutter wizard should display these questions before final creation.

### Finding 6: No goal completion detection or celebration

- **Severity**: P1
- **User Impact**: When all acceptance criteria are met and all tasks are done, the goal silently sits at whatever status it had. No "congratulations" moment, no achievement event, no status change to "completed". The growth loop's "Reinforce" phase is missing.
- **File**: No `GoalCompleted` event or consumer exists in the codebase.
- **Current Code**: Goals have a `completed_at` timestamp column and a `status` field that supports "completed", but nothing transitions status to "completed". The `MinimumAcceptanceCriteria` on the goal detail page has thresholds with `met` booleans, but no backend code checks these and auto-completes the goal.
- **Expected**: When all minimum acceptance criteria thresholds are met (or when progress reaches 1.0), the goal should auto-transition to "completed" status. Achievement events should fire. The user should see a celebration UI.
- **Fix**: Create a periodic check (or event-driven) that evaluates goal criteria completion. When all thresholds are met, set `goal.status = "completed"`, `goal.completed_at = now()`, and fire achievement events.

### Finding 7: Goal status transitions are not exposed to the user

- **Severity**: P1
- **User Impact**: Goals have statuses (draft, active, paused, completed, archived, cancelled) but the goal detail page only displays the status as a read-only chip. Users cannot pause, archive, or cancel goals from the UI.
- **File**: `mobile/lib/features/goal/presentation/pages/goal_detail_page.dart:214-218` (status chip)
- **Current Code**: Status is displayed as an `_InfoChip` with no interaction. The Go gateway does not proxy goal status update endpoints (only GET, POST, PUT, DELETE are registered).
- **Expected**: Goal detail page should have a status management menu (e.g., AppBar overflow menu) with options to pause, resume, archive, or cancel the goal.
- **Fix**: Add status transition buttons to the goal detail page AppBar or as a bottom action bar. Add PATCH endpoint support in Go proxy routes for `/goals/:id/status`.

---

## Medium Issues (P2): 7 polish items

### Finding 8: Goal type mapping inconsistency between Flutter and Python

- **Severity**: P2
- **User Impact**: Flutter shows user-friendly labels ("academic", "skill", "habit") but Python's GoalDecompositionService normalizes "exam" to "academic" while the API uses "exam" as the canonical type. The mapping works but is fragile.
- **File**: `mobile/lib/features/goal/data/repositories/goal_repository.dart:35-47` (Flutter type map)
- **File**: `backend/app/services/goal_decomposition_service.py:179-190` (Python normalizer)
- **Current Code**: Flutter maps `academic -> exam`, `skill -> job_search`, `habit -> fitness`. Python normalizes `exam -> academic`, `job_search -> skill`. This bidirectional normalization works but if any new type is added it could break.
- **Expected**: Single canonical type mapping, ideally server-driven.
- **Fix**: Consider making the Flutter wizard fetch available goal types from the backend rather than hardcoding.

### Finding 9: Goal detail skeleton does not match all sections

- **Severity**: P2
- **User Impact**: Loading skeleton shows placeholders for header, strategy card, minimum criteria card, and metrics but not for the TodayStepCard, AccountabilityCard, SimilarGoalPursuersCard, or JourneyProgressCard.
- **File**: `mobile/lib/features/goal/presentation/pages/goal_detail_page.dart:699-755` (skeleton)
- **Current Code**: The `_GoalDetailSkeleton` has 7 placeholder blocks but the actual page renders 9+ sections.
- **Expected**: Skeleton should match the visual layout of the loaded page to avoid layout shift.
- **Fix**: Add skeleton placeholders for JourneyProgressCard, TodayStepCard, and the community/accountability section.

### Finding 10: Plan review card has hardcoded semantics label

- **Severity**: P2
- **User Impact**: Screen readers announce "Chat plan review card control 1" and "Chat plan review card control 2" instead of meaningful labels.
- **File**: `mobile/lib/features/chat/presentation/widgets/plan_review_card.dart:369,1259` (hardcoded Semantics labels)
- **Current Code**: `label: 'Chat plan review card control 1'` and `label: 'Chat plan review card control 2'`
- **Expected**: Descriptive semantics labels like "Plan review card: approved with 85% confidence"
- **Fix**: Replace hardcoded strings with contextual labels using l10n and the review result data.

### Finding 11: Goal creation wizard does not validate title uniqueness

- **Severity**: P2
- **User Impact**: Users can create multiple goals with the exact same title, leading to confusion in the GoalSwitcher and goal list.
- **File**: `backend/app/api/v1/goals.py:118-188` (no uniqueness check)
- **Current Code**: No duplicate title check in the create_goal endpoint.
- **Expected**: At minimum, warn the user if they already have an active goal with the same title.
- **Fix**: Add a soft warning (not a hard block) in the creation response if an active goal with the same title already exists for the user.

### Finding 12: Multi-goal arbitration endpoint not integrated into Flutter

- **Severity**: P2
- **User Impact**: The backend has a `/goals/arbitrate` endpoint that returns priority scores, time split recommendations, and conflict detection for multiple goals. This intelligence is never surfaced to the user.
- **File**: `backend/app/api/v1/goals.py:191-236` (arbitration endpoint)
- **File**: No Flutter code calls this endpoint.
- **Current Code**: `GoalSwitcher` widget lets users switch between goals but does not show arbitration data (conflicts, recommended time split).
- **Expected**: When a user has multiple active goals, show a "Goal Balance" card with time allocation suggestions and conflict warnings.
- **Fix**: Wire the arbitration endpoint to a Flutter provider and display recommendations in the dashboard or goal list.

### Finding 13: Goal creation milestone editor lacks drag-to-reorder

- **Severity**: P2
- **User Impact**: Users can edit milestone titles and descriptions but cannot reorder them. If the AI-generated order is suboptimal, the user's only option is "Regenerate".
- **File**: `mobile/lib/features/goal/presentation/screens/goal_creation_wizard_screen.dart:635-732` (_MilestoneEditorStep)
- **Current Code**: Milestones are displayed as a vertical list of cards with no reorder handles.
- **Expected**: ReorderableListView or drag handles for milestone reordering.
- **Fix**: Wrap milestone cards in `ReorderableListView` and add drag handles.

### Finding 14: Scenario pack journey progress fails silently

- **Severity**: P2
- **User Impact**: If the scenario pack service is unavailable or no pack is matched, the JourneyProgressCard shows "AI is personalizing your journey..." indefinitely with no fallback to raw milestone progress.
- **File**: `mobile/lib/features/goal/presentation/widgets/journey_progress_card.dart:22-45` (no-pack fallback)
- **Current Code**: When `progress.hasPack` is false, a static message is shown. No retry mechanism, no fallback to milestone-based progress.
- **Expected**: If no scenario pack is available after a few seconds, show milestone-based progress instead.
- **Fix**: Add a timeout fallback in `JourneyProgressFutureCard` that falls back to milestone-based progress if the scenario pack service fails.

---

## Verified Working

The following aspects of the Goals + Plans journey are confirmed working correctly:

1. **Goal Creation Wizard (Flutter)**: 5-step wizard with type selection, motivation/title/description input, time horizon selection, milestone editing with AI preview, and confirmation. Entry Wire (intent analysis) properly falls back to legacy chooser when kill switch is off. Proper i18n throughout.

2. **Goal Creation API (Python)**: `POST /goals` accepts goal_type, title, motivation, time_horizon, description, and milestones. Creates first task automatically. Auto-assigns scenario pack. Returns `first_task_id` for immediate task execution.

3. **Goal Detail Page (Flutter)**: Rich page showing progress circle (percentage), status/mastery/target-date/priority chips, minimum acceptance criteria with threshold checklist, knowledge bottleneck strip, today's minimal next step with start/complete buttons, plan health metrics (overall, phase health, task completion rate), accountability status, related sources, and similar goal pursuers card. Skeleton loading state and error state with retry are present.

4. **Goal Detail API (Python)**: `GET /experience/goal-detail/{goal_id}` aggregates data from Goal, Plan, Tasks, GoalWorldGraphSnapshot, AccountabilityPartnership, and StrategyBeliefSnapshot into a single rich payload.

5. **Go Gateway Routing**: Both `/goals` and `/experience` routes are properly proxied through the Go gateway with auth middleware. Plan review feedback is handled via WebSocket with gRPC forwarding to Python.

6. **GoalSwitcher Widget**: Multi-goal support with popup menu for switching active goal. Wired to `activeGoalProvider`. Shows "No focus goal" when no goals exist. Dense mode for dashboard embedding.

7. **Plan Review Card (Flutter)**: Rich card with decision badge, confidence bar, reasoning summary/details, alignment summary, comments grouped by severity, action buttons (approve/reject/modify), delegate-to-agent toggle, and rejection feedback bottom sheet with structured reasons. Sensory feedback on approve. Animated highlight for pending actions.

8. **Plan Review Service (Python)**: Two-tier review (rule-based quick check + LLM deep review) with user confirmation workflow. Circuit breaker protection. Plan quality gate with completeness/safety/alignment checks.

9. **Plan API (Python)**: Full CRUD with quota management, archive/restore with achievement events, phase management (create/reorder/activate/complete/feedback), compass review workflow, phase sketch generation and materialization, discovery workflow (start/turn/finalize), task generation, and health evaluation.

10. **GoalWorldGraphMiniPanel (Flutter)**: Interactive expandable panel with gap analysis summary (coverage %, bottleneck count, mastery average), color-coded node sections (bottleneck/learning/mastered), node detail bottom sheets with type/mastery/exam-weight/difficulty/trainability/mistakes. Toggle between Galaxy Star Map and Goal World modes.

11. **Goal Model (Python)**: Comprehensive ORM model with plan_id FK, minimum_acceptance_criteria JSON column, domain_pack_id, source tracking, lifecycle timestamps (completed_at, archived_at), is_primary flag, and metadata payload.

12. **SparkleGoalCreatedDialog (Flutter)**: Celebration dialog after goal creation showing goal name, learning path (if matched), first milestone, minimum criteria tip, and action buttons to "See full plan" or "Start first task".

13. **Goal Decomposition Service (Python)**: Template-based milestone generation for 5 goal types (academic, skill, habit, project, other) with personalized descriptions, time horizon mapping (short=21d, medium=75d, long=150d), and acceptance criteria scaffolding.

14. **Strategy Migration Wizard**: Displayed on goal detail when `strategyBelief` is present with low confidence score, allowing users to migrate away from underperforming strategies.

15. **Minimum Acceptance Criteria Card (Flutter)**: Shows criteria with met/unmet status, confirm/modify buttons, description text, and proper i18n. Confirm action calls backend PUT endpoint with undo support via snackbar.

---

## Architecture Trace Summary

```
Goal Creation Flow:
  Flutter GoalCreationWizardScreen
    -> Flutter ApiGoalRepository.createGoal()
    -> POST /goals (Go proxy_routes.go)
    -> Python create_goal() (api/v1/goals.py)
    -> GoalDecompositionService.create_goal() -> Goal ORM (models/goal.py)
    -> TaskService.create() (first task from first milestone)
    -> _auto_assign_scenario_pack() (Redis journey state)
    -> Flutter SparkleGoalCreatedDialog (see plan / start task)

Goal Detail Flow:
  Flutter GoalDetailPage
    -> Flutter GoalDetailNotifier.load()
    -> GET /experience/goal-detail/{goalId} (Go proxy)
    -> Python get_goal_detail() (api/v1/experience/goal_router.py)
    -> Aggregates: Goal + Plan + Tasks + GoalWorldGraphSnapshot +
       AccountabilityPartnership + StrategyBeliefSnapshot
    -> Renders: Header, JourneyProgress, Criteria, Bottlenecks, TodayStep,
       PlanHealth, Accountability, Sources, Pursuers

Plan Review Flow:
  Python PlanReviewService.review_plan()
    -> PlanQualityGate (rule-based) -> LLM review
    -> Streamed via gRPC to Go chat_orchestrator
    -> Go forwards plan_review_card delta via WebSocket
    -> Flutter PlanReviewCard (approve/reject/modify)
    -> Flutter sends plan_review_feedback via WebSocket
    -> Go handlePlanReviewFeedbackWithResponder()
    -> gRPC SubmitPlanReview to Python
    -> Python processes user decision

BROKEN: Goal Progress Update:
  Task completed -> TaskCompleted event -> spine_orchestrator.on_task_completed()
    -> signal detection, relationship model
    -> DOES NOT UPDATE Goal.progress or Goal.mastery
    -> Goal.progress stays at 0.0 forever
```
