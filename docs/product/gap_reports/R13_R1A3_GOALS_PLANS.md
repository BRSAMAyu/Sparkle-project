# R13 R1A3: Goals + Plans Flow -- Independent Audit

**Date**: 2026-05-07
**Auditor**: Claude (R13 fresh independent audit)
**Scope**: Goal creation, goal detail, plan generation, plan execution, goal-plan-task hierarchy, GoalWorldGraph, edge cases

---

## Summary Table

| Area | Status | Issues Found |
|------|--------|-------------|
| Goal Creation (Flutter wizard) | WORKING | 1 P1, 1 P2 |
| Goal Detail Page | WORKING | 1 P1 |
| Goal Editing | MISSING | 1 P1 |
| Goal Deletion | PARTIAL | 1 P1 |
| Goal-to-Plan Navigation | WORKING | 0 |
| Plan Generation from Goal | DISCONNECTED | 1 P0 |
| Plan Detail & Execution | WORKING | 0 |
| Plan History | WORKING | 0 |
| Plan Versioning | NOT IMPLEMENTED | 1 P2 |
| Goal-Plan-Task Hierarchy | PARTIAL | 1 P1 |
| Progress Chain (Task -> Plan -> Goal) | PARTIAL | 1 P1 |
| GoalWorldGraph | WORKING | 0 |
| Minimum Acceptance Criteria | WORKING | 0 |
| Goal Deadline / Overdue | NOT HANDLED | 1 P1 |
| Multi-Goal Arbitration | WORKING | 0 |
| Goal Conflict Dialog | WORKING | 0 |
| Empty States | WORKING | 0 |

**Totals**: 1 P0, 6 P1, 2 P2

---

## P0 Findings (Blocks Core Flow)

### P0-01: Goal and Plan are disconnected -- no plan auto-generated from goal creation

**Evidence**:
- `backend/app/api/v1/goals.py:158-168` -- `create_goal` creates a Goal with milestones but does NOT create a Plan or link `goal.plan_id`.
- `backend/app/api/v1/goals.py:179-199` -- Only creates a single "first step" task from the first milestone. No Plan is created.
- `backend/app/models/goal.py:64` -- Goal has `plan_id = Column(GUID(), ForeignKey("plans.id"), nullable=True)` but it is never set during goal creation.
- `backend/app/models/plan.py` -- Plan model has NO `goal_id` column. The Plan-to-Goal relationship is unidirectional only.
- `mobile/lib/features/goal/data/repositories/goal_repository.dart:80-93` -- `createGoal` returns `CreatedGoal` with `id` and `firstTaskId` but no `planId`.
- `mobile/lib/features/goal/presentation/screens/goal_creation_wizard_screen.dart:424-425` -- The "See full plan" button navigates to `/goals/${created.id}`, NOT to a plan detail page. There is no plan to navigate to.

**Impact**: After creating a goal with milestones, the user sees "See full plan" but pressing it goes to the goal detail page (not a plan). The goal detail page's `_PlanHealthBand` (line 416) shows plan health only if the goal has a linked plan, but no plan exists. The user never gets a real plan from goal creation.

**Root Cause**: The goal creation flow creates milestones (which are metadata) but never converts them into a Plan with Tasks. The `_auto_assign_scenario_pack` assigns a pack_id to the goal but this only writes Redis state, it does not create a Plan entity.

**Fix Required**: Either:
1. Auto-create a Plan from milestones during `create_goal`, linking `goal.plan_id = plan.id`, OR
2. Add a "Generate Plan" button on goal detail page that triggers plan generation, OR
3. Wire the scenario pack journey into Plan creation automatically.

---

## P1 Findings (Significant Gaps)

### P1-01: Goal editing UI does not exist

**Evidence**:
- `mobile/lib/features/goal/goal_routes.dart` -- Only `create` and `detail` routes exist. No `edit` route.
- Searched all of `mobile/lib/features/goal/` for "edit" -- zero results for goal editing.
- The Goal detail page (`goal_detail_page.dart`) has no edit button in the AppBar actions.
- `backend/app/api/v1/goals.py` -- No `PUT /:id` handler exists. The Go gateway has `goals.PUT("/:id", h.proxyWithHeaders)` (proxy_routes.go:355) but Python has no matching endpoint.

**Impact**: Users cannot change goal title, description, deadline, or priority after creation.

---

### P1-02: Goal deletion has no backend handler

**Evidence**:
- `backend/gateway/internal/handler/proxy_routes.go:356` -- Go registers `goals.DELETE("/:id", h.proxyWithHeaders)`.
- `backend/app/api/v1/goals.py` -- NO `@router.delete` handler exists. Only GET and POST are defined.
- The DELETE request will be proxied to Python and return 405 Method Not Allowed.
- No Flutter UI exists for goal deletion (no delete button in goal_detail_page.dart).
- `backend/app/models/goal.py` has `deleted_at` inherited from BaseModel for soft-delete, but no endpoint uses it.

**Impact**: Goal deletion is a dead route -- the Go gateway proxies to a non-existent Python handler. Even if the UI button were added, it would 405.

---

### P1-03: Plan model has no goal_id -- bidirectional Goal-Plan link is broken

**Evidence**:
- `backend/app/models/goal.py:64` -- Goal has `plan_id` FK to plans.
- `backend/app/models/plan.py` -- Plan has NO `goal_id` FK. Searching for `goal_id` returns zero matches.
- `backend/app/schemas/plan.py` -- PlanCreate schema has no `goal_id` field.
- `backend/app/api/v1/plans.py` -- No endpoint filters plans by goal_id.
- `mobile/lib/features/plan/data/repositories/plan_repository.dart` -- No method to get plans by goal.

**Impact**: The hierarchy is one-directional: Goal -> Plan works, but Plan -> Goal does not. Tasks in a plan cannot be traced back to their source goal. The plan detail screen has no way to show which goal it belongs to.

---

### P1-04: Progress chain Task -> Plan -> Goal is incomplete

**Evidence**:
- `backend/app/api/v1/experience/goal_router.py:424-434` -- `_plan_health_payload` computes goal progress as a weighted sum of plan.progress, plan.mastery, and task_completion_rate.
- However, `goal.progress` (on the Goal model) is never updated by task completion events.
- `backend/app/models/goal.py:48` -- `progress = Column(Float, default=0.0)` is set at creation but never recomputed.
- `backend/app/services/task_event_consumer.py` does not update goal progress on task completion.
- `mobile/lib/features/goal/presentation/providers/goal_detail_provider.dart:141-152` -- The provider reads from `/experience/goal-detail/:goalId` which computes progress server-side on each GET, but the base Goal.progress column stays stale.

**Impact**: If the experience endpoint is unavailable, goal progress falls back to the stale Goal.progress=0.0 from creation. The `/goals` list endpoint returns the stale progress value. Only the dedicated `/experience/goal-detail/:goalId` endpoint computes real-time progress.

---

### P1-05: Goal deadline/overdue has no warning or adjustment mechanism

**Evidence**:
- `mobile/lib/features/goal/presentation/pages/goal_detail_page.dart:229` -- The target_date chip displays the date but has no color/urgency indicator.
- No "overdue" badge, no warning color, no adaptive replan trigger when target_date has passed.
- `backend/app/api/v1/experience/goal_router.py` -- No deadline-aware logic in the goal detail response.
- `mobile/lib/features/goal/presentation/providers/goal_detail_provider.dart` -- No deadline comparison logic.
- `backend/app/orchestration/adaptive_replanner.py` exists but is not triggered by deadline expiry in the goal detail flow.

**Impact**: Users whose goal deadline has passed see no visual or functional indication. No adaptive replan or rescheduling is offered.

---

### P1-06: "View Plan" button in goal detail requires activePlanProvider, not goal.plan_id

**Evidence**:
- `mobile/lib/features/goal/presentation/pages/goal_detail_page.dart:416-430` -- The "View Plan" button uses `ref.watch(activePlanProvider)` to determine which plan to navigate to.
- This is the user's currently selected chat-context plan, NOT necessarily the plan linked to this goal.
- If the user has multiple plans, pressing "View Plan" on a goal could navigate to the wrong plan.
- The code does not check `data.goal` for a plan_id at all.

**Impact**: Goal detail page's "View Plan" button shows the wrong plan if the user's active chat plan differs from the goal's plan.

---

## P2 Findings (Improvements)

### P2-01: Plan versioning is not implemented

**Evidence**:
- `mobile/lib/features/plan/presentation/screens/plan_history_screen.dart` -- Only shows archived plans, not plan versions.
- `mobile/lib/features/plan/plan_routes.dart` -- `planHistory` route exists but shows non-active plans only.
- No plan version or revision tracking exists in the Plan model (`backend/app/models/plan.py`).
- Plan editing (`PlanEditScreen`) overwrites the plan in place with no history.

**Impact**: Users cannot see how a plan evolved or revert to a previous version.

---

### P2-02: Goal creation wizard hardcodes i18n instead of using context.l10n

**Evidence**:
- `mobile/lib/features/goal/presentation/screens/goal_creation_wizard_screen.dart:59` -- Uses `_t(String zh, String en)` helper instead of `context.l10n` throughout.
- Same pattern in `_GoalTypeStep` (line 513), `_GoalMotivationStep` (line 554), `_TimeHorizonStep` (line 605), `_MilestoneEditorStep` (line 649), `_GoalConfirmStep` (line 758).
- Other goal widgets like `goal_detail_page.dart` correctly use `context.l10n`.

**Impact**: Inconsistent i18n approach. The `_t()` pattern works but doesn't participate in the formal localization pipeline (no .arb keys). Future i18n changes may miss these strings.

---

## Verified Working

### Goal Creation Wizard
- 5-step wizard: Type -> Motivation -> Timeline -> Milestones -> Confirm
- Phase-1 Entry Wire: GoalIntentInput with AI analysis fallback to legacy chooser
- Decomposition preview: `POST /goals/decompose-preview` works deterministically
- Scenario pack auto-assignment: `_auto_assign_scenario_pack` maps goal_type to pack_id
- First task auto-created from first milestone: `goals.py:180-199`
- Success dialog with "See Plan" and "Start First Task" CTAs
- Duplicate title warning (non-blocking): `goals.py:131-145`

### Goal Detail Page
- Full data aggregation via `/experience/goal-detail/:goalId` BFF endpoint
- Goal header with circular progress indicator, status, mastery, target date, priority
- Journey progress card (scenario pack progress)
- StrategyMigrationWizard (cognitive strategy adjustment)
- MinimumCriteriaCard with confirm/undo functionality
- GoalBottleneckStrip showing knowledge gaps
- Today's minimal next step card with start/complete actions
- Plan health band with overall, phase health, task completion metrics
- Accountability card with partner/commitment info
- Related sources card
- SimilarGoalPursuersCard (community)
- Skeleton loading state, error state with retry
- Pull-to-refresh

### Plan Detail Screen
- Two-tab layout: Overview + Progress
- Rich plan overview with description codec (structured sections)
- Learning path progress bar for learning_path plans
- Last 24h sprint mode detection and banner
- Exam sprint context section with pack nodes
- Today's focus plan with task cards
- Expandable full plan by day groups
- Task add (new + existing task picker)
- Phase management: create, activate, complete, feedback dialog
- Archive/restore actions with confirmation
- Plan health indicator with color-coded score
- Sprint completion detection and navigation
- Share sheet integration
- Pie chart (completion rate), bar chart (task type distribution), line chart (daily completion)
- Rich error handling with specific error messages

### Plan Routes
- Full CRUD routes: create, detail, edit, history
- Sprint-specific routes: setup, review, completion, history
- Growth screen and learning portfolio
- Shell route for plan detail

### GoalWorldGraph
- `GoalWorldGraphMiniPanel` in Galaxy screen
- Connected to `goalGraphOverlayProvider` with real backend data
- Gap analysis summary with coverage, bottlenecks, mastery stats
- Node sections: Bottlenecks, Learning, Mastered with progress bars
- Node detail modal with type, mastery, relationship, exam weight, difficulty
- Toggle between Star Map and Goal World modes
- Proper empty/no-goal states

### Multi-Goal Arbitration
- `ActiveGoalProvider` with persistent local + remote sync
- `MultiGoalOverview` combining spine goals + plan goals
- `GoalArbitrationSuggestion` with conflict detection
- `GoalConflictDialog` for time trade-off resolution
- `multiGoalOverviewProvider` fetches arbitration from `/aurora/spine/goals`

### Minimum Acceptance Criteria
- Stored as JSON on Goal model with thresholds
- Rendered via `MinimumCriteriaCard` with confirm/undo
- `PUT /experience/goal-detail/:goalId/criteria-status` endpoint works
- Criteria auto-generated from milestones during goal creation

---

## File Index (Evidence Sources)

### Flutter
- `mobile/lib/features/goal/goal_routes.dart`
- `mobile/lib/features/goal/goal.dart`
- `mobile/lib/features/goal/presentation/screens/goal_creation_wizard_screen.dart`
- `mobile/lib/features/goal/presentation/pages/goal_detail_page.dart`
- `mobile/lib/features/goal/presentation/providers/goal_detail_provider.dart`
- `mobile/lib/features/goal/data/repositories/goal_repository.dart`
- `mobile/lib/features/goal/data/models/goal_creation_models.dart`
- `mobile/lib/features/goal/presentation/widgets/goal_created_dialog.dart`
- `mobile/lib/features/goal/presentation/widgets/goal_conflict_dialog.dart`
- `mobile/lib/features/goal/presentation/widgets/minimum_criteria_card.dart`
- `mobile/lib/features/goal/presentation/widgets/goal_bottleneck_strip.dart`
- `mobile/lib/features/goal/presentation/widgets/journey_progress_card.dart`
- `mobile/lib/features/plan/plan_routes.dart`
- `mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart`
- `mobile/lib/features/plan/presentation/screens/plan_create_screen.dart`
- `mobile/lib/features/plan/presentation/screens/plan_history_screen.dart`
- `mobile/lib/features/plan/presentation/providers/active_plan_provider.dart`
- `mobile/lib/features/plan/presentation/providers/active_goal_provider.dart`
- `mobile/lib/features/plan/presentation/providers/plan_provider.dart`
- `mobile/lib/features/plan/data/repositories/plan_repository.dart`
- `mobile/lib/features/galaxy/presentation/widgets/goal_world_graph_mini_panel.dart`

### Go Gateway
- `backend/gateway/internal/handler/proxy_routes.go` (lines 347-356 goals, 147-186 plans, 856-862 experience)

### Python Backend
- `backend/app/api/v1/goals.py`
- `backend/app/api/v1/experience/goal_router.py`
- `backend/app/models/goal.py`
- `backend/app/services/goal_decomposition_service.py`
- `backend/app/services/plan_service.py`
- `backend/app/orchestration/goal_quality_evaluator.py`
- `backend/app/signals/goal_world_graph.py`
