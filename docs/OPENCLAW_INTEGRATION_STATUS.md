# OpenClaw Integration - Current State Analysis

## Executive Summary

The Sparkle Flutter mobile app has a **sophisticated, production-ready OpenClaw integration** that enables AI-powered task execution. The implementation is complete across data models, state management, UI/UX, and API integration. The system handles a full execution lifecycle from handoff through approval/rejection with polling-based status updates.

---

## 1. UI/UX CURRENT STATE

### 1.1 Task Execution Screen (_BottomControls Widget)

**Location**: `mobile/lib/features/task/presentation/screens/task_execution_screen.dart` (lines 1338-1923)

#### What Exists Now:

1. **Execution Template Selection** (when execution intents are null/terminal):
   - Displays top 3 templates as `ChoiceChip` buttons
   - Shows template name + execution mode (AI/Human/Hybrid)
   - Template description below chip
   - Clean, minimal design

2. **Execution Status Card** (when execution is active or loading):
   - Color-coded status indicator:
     - **SUCCEEDED** → Green + check icon
     - **PARTIAL** → Yellow/warning + pending icon
     - **FAILED/TIMEOUT** → Red + error icon
     - **WAITING_APPROVAL** → Yellow/warning + approval icon
     - **RUNNING/DISPATCHED** → Blue/primary + spinner
     - **HANDED_BACK/CANCELED** → Gray + return icon
   - Status title + subtitle with contextual messages
   - Output preview (first 2 parsed output fields shown)
   - Meta preview (template name, strategy variant, node label)
   - Inline spinner during handoff loading

3. **Approval Workflow** (when status === WAITING_APPROVAL):
   - Two buttons side-by-side:
     - "取回任务" (Return Task) - takes task back
     - "确认采用 AI 结果" (Confirm AI Result) - approves result
   - Both buttons show loading state during decision
   - Appears inline above handoff button

4. **Handoff Button**:
   - Adaptive text based on execution status:
     - `null` → "交给 AI 执行" (Handoff to AI)
     - `FAILED/TIMEOUT/CANCELED/HANDED_BACK` → "重新交给 AI" (Re-handoff)
     - `SUCCEEDED/PARTIAL` → "再次交给 AI" (Handoff again)
     - `WAITING_APPROVAL` → "等待确认" (Awaiting confirmation - disabled)
     - `RUNNING/DISPATCHED` → "AI 执行中" (AI executing - disabled)
   - Secondary button style, full width
   - Disabled when task is terminal and no execution pending

5. **Standard Controls**:
   - Abandon task button (text style, left side)
   - Complete task button (primary style, right side, 2x flex)

#### Design Patterns Used:

- **Color coding**: DS.primaryBase, DS.success, DS.warning, DS.error
- **Typography**: DS.bodyMedium, DS.bodySmall, DS.fontWeightBold
- **Spacing**: DS.spacing8, DS.spacing12, DS.spacing16 (consistent 8px rhythm)
- **Icons**: Material Icons (smart_toy, check_circle, pending_actions, error, approval, keyboard_return)
- **Surface**: GraphiteCardSurface with borderColor=DS.borderSubtle
- **Containers**: Color background (statusColor.withValues(alpha: 0.08)) + border

### 1.2 Execution Status Display Quality

**Strengths**:
- ✓ Polished color semantics (success=green, warning=yellow, error=red)
- ✓ Icon + text coherence
- ✓ Contextual messaging (error messages, validation stats, trust labels)
- ✓ Loading states clearly communicated (spinner, disabled buttons)
- ✓ Approval flow UI is straightforward and intuitive
- ✓ Output preview displays structured data in a readable format

**Gaps vs Commercial Experience**:
- ✗ **No animated transitions** between states (status card appears/disappears instantly)
- ✗ **No execution timeline/progress bar** showing how long execution has been running
- ✗ **No step-by-step execution visualization** (what OpenClaw is currently doing)
- ✗ **Output preview is text-only** (no formatted tables, code blocks, or rich media)
- ✗ **No persistent execution history** visible on this screen
- ✗ **Approval UI lacks context** (what exactly are we confirming? what were the changes?)
- ✗ **No "details" expandable section** for full execution output/logs
- ✗ **Error messages are plain text** (could be styled as callouts/alerts)
- ✗ **Template descriptions aren't always visible** (truncated in small screens)
- ✗ **No execution metadata timeline** (dispatched_at, started_at, completed_at)

---

## 2. STATE MANAGEMENT (task_provider.dart)

**Location**: `mobile/lib/features/task/presentation/providers/task_provider.dart` (863 lines)

### 2.1 TaskListState

```dart
class TaskListState {
  final Map<String, ExecutionIntentModel> taskExecutions;           // Current execution per task
  final Map<String, ExecutionRecordModel> taskExecutionRecords;      // Execution output/validation
  final Map<String, List<ExecutionTemplateModel>> taskExecutionTemplates;
  final Map<String, String> selectedExecutionTemplateIds;            // User selection
  final Set<String> handoffInFlight;                                 // Loading state for handoff
  final Set<String> executionDecisionInFlight;                       // Loading state for confirm/reject
  final String? error;
}
```

### 2.2 Key Operations

| Method | Purpose |
|--------|---------|
| `loadTaskExecutionState(taskId)` | Fetch latest ExecutionIntentModel + ExecutionRecordModel |
| `loadTaskExecutionTemplates(taskId)` | Fetch available templates, auto-select first if none selected |
| `selectExecutionTemplate(taskId, templateId)` | Update template selection |
| `handoffTaskToAi(taskId, goal?)` | POST /executions/tasks/{taskId}/handoff → create intent → start polling |
| `confirmTaskExecutionResult(taskId)` | POST /executions/records/{recordId}/confirm |
| `rejectTaskExecutionResult(taskId, reason?)` | POST /executions/records/{recordId}/reject |
| `_startExecutionPolling(taskId)` | Timer.periodic(5 seconds) → reload execution state until terminal |

### 2.3 Execution Polling (task_execution_screen.dart)

```dart
void _startExecutionPolling(String taskId) {
  _executionRefreshTimer?.cancel();
  _executionRefreshTimer = Timer.periodic(const Duration(seconds: 5), (_) {
    unawaited(() async {
      final latest = await ref
          .read(taskListProvider.notifier)
          .loadTaskExecutionState(taskId);
      if (!mounted) return;
      if (latest == null || latest.isTerminal) {
        _executionRefreshTimer?.cancel();
      }
    }());
  });
}
```

**Gap**: Polling is **pull-based** (5-second intervals). For commercial polish:
- ✓ Could use WebSocket for real-time status updates (pattern exists in chat_service)
- ✓ Could optimize polling cadence (faster initially, slower when waiting)
- ✗ No exponential backoff or jitter
- ✗ No retry logic if a poll fails

---

## 3. DATA MODELS

### 3.1 ExecutionIntentModel

**Location**: `mobile/lib/features/task/data/models/execution_intent_model.dart` (242 lines)

```dart
class ExecutionIntentModel {
  final String id, taskId;
  final ExecutionMode executionMode;  // human | agent | hybrid
  final String executor;              // "openclaw"
  final ExecutionIntentStatus status; // 11 states
  final ExecutionTrustLevel trustLevel; // raw | validated | trusted
  final String goal;
  final String? templateId, templateName, strategyVariant;
  final String? targetNodeId, targetNodeLabel;
  final DateTime? dispatchedAt, completedAt, createdAt;
  final String? errorCategory, errorMessage;
  
  bool get isTerminal;   // Succeeded, Partial, Failed, Canceled, TimedOut, HandedBack
  bool get isRunning;    // Dispatched, Running, WaitingApproval
  bool get isWaitingApproval;
  String get statusLabel;  // Chinese labels: "执行中", "等待确认", etc.
  String get trustLabel;   // "原始结果", "已校验", "可信结果"
}
```

**Status States** (11 total):
- draft, ready, dispatched, running, waitingApproval
- succeeded, partial, failed, canceled, timedOut, handedBack

### 3.2 ExecutionRecordModel

**Location**: `mobile/lib/features/task/data/models/execution_record_model.dart` (63 lines)

```dart
class ExecutionRecordModel {
  final String id, executionIntentId;
  final String trustLevel;  // 'trusted', 'validated', 'raw'
  final Map<String, dynamic>? parsedOutput;  // Structured result
  final List<Map<String, dynamic>> artifacts;
  final double? qualityScore;
  final int? durationMs, validationPassed, validationTotal, approvalRequested;
  final String? errorCategory, errorMessage;
  
  bool get hasStructuredOutput;
  String get trustLabel;
}
```

### 3.3 ExecutionTemplateModel

**Location**: `mobile/lib/features/task/data/models/execution_template_model.dart` (65 lines)

```dart
class ExecutionTemplateModel {
  final String templateId, name, description;
  final ExecutionMode executionMode;  // agent | human | hybrid
  final String targetEnv;             // browser | document | shell
  final double matchScore;            // 0.0 to 1.0
  final List<String> matchReasons;    // ['keyword:搜索', etc.]
  final String? requiredNodeCommand;
  
  String get modeLabel;  // "人工" | "AI" | "协作"
}
```

**Built-in Templates** (from backend):
1. web_research_brief - Web research + summarization
2. document_digest - Document processing
3. shell_diagnostics - Terminal diagnostics
4. browser_form_prepare - Form filling (HYBRID)
5. cross_device_capture - Multi-device capture (HYBRID)

---

## 4. API INTEGRATION (task_repository.dart)

**Location**: `mobile/lib/features/task/data/repositories/task_repository.dart` (889 lines)

### 4.1 Execution Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `handoffTask(taskId, goal?, templateId?)` | `POST /executions/tasks/{taskId}/handoff` | Create ExecutionIntent |
| `listExecutionTemplates(taskId)` | `GET /executions/tasks/{taskId}/templates` | Get available templates |
| `listExecutionIntents(taskId)` | `GET /executions/tasks/{taskId}/intents` | Get execution history |
| `getExecutionRecord(intentId)` | `GET /executions/{intentId}/record` | Get execution output |
| `confirmExecutionResult(recordId)` | `POST /executions/records/{recordId}/confirm` | Approve result |
| `rejectExecutionResult(recordId, reason?)` | `POST /executions/records/{recordId}/reject` | Reject result |

### 4.2 API Payload Examples

**Handoff Request**:
```dart
POST /executions/tasks/{taskId}/handoff
{
  "goal": "Optional custom goal",
  "template_id": "web_research_brief"
}
```

**Execution Intent Response**:
```json
{
  "id": "exec_...",
  "task_id": "...",
  "status": "dispatched",
  "executor": "openclaw",
  "execution_mode": "agent",
  "trust_level": "raw",
  "goal": "...",
  "template_name": "web_research_brief",
  "created_at": "2026-03-28T...",
  "dispatched_at": "2026-03-28T..."
}
```

### 4.3 Demo Mode

When `DemoDataService.isDemoMode` is true:
- `handoffTask()` returns a mock ExecutionIntentModel with status=succeeded
- `listExecutionTemplates()` returns 1 hardcoded template
- `getExecutionRecord()` returns null (no record in demo)
- Supports full end-to-end testing without backend

---

## 5. DESIGN SYSTEM (design_system.dart)

**Location**: `mobile/lib/core/design/design_system.dart` (100+ lines)

### 5.1 Key Design Tokens Used for Execution UI

```dart
// Colors
DS.primaryBase       // Blue - for pending/running states
DS.success           // Green - for succeeded
DS.warning           // Yellow - for partial/waiting_approval
DS.error             // Red - for failed/timeout
DS.neutral500/600/700 // Grays - for disabled/secondary text

// Typography
DS.bodyMedium        // Titles
DS.bodySmall         // Descriptions
DS.fontWeightBold    // 700
DS.fontWeightMedium  // 500

// Spacing (8px rhythm)
DS.spacing8, DS.spacing12, DS.spacing16, DS.spacing24

// Components
GraphiteCardSurface  // Container for execution status
ChoiceChip           // Template selection
CustomButton         // Actions (primary, secondary, text)
```

### 5.2 Surfaces & Modals

- **GraphiteCardSurface**: Opinionated card with default padding, border, background
- **GraphiteModalSurface**: Modal dialog surface
- **GraphiteScaffold**: Screen-level scaffold

### 5.3 Gradient Support

```dart
LinearGradient _taskWarmActionGradient(BuildContext context) {
  final isDark = Theme.of(context).brightness == Brightness.dark;
  return LinearGradient(
    colors: [DS.primaryBase, Color.lerp(DS.primaryBase, ...)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}
```

Used for "Complete" and "Confirm AI Result" buttons.

---

## 6. WEBSOCKET & STREAMING PATTERNS

**Location**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart` (500+ lines)

### 6.1 Existing Streaming Infrastructure

Sparkle has a **mature WebSocket implementation** for real-time chat that could be adapted for execution updates:

```dart
// Stream-based chat messages
Stream<ChatStreamEvent> chatStream(String sessionId) {
  // Uses web_socket_channel to parse JSON events
  // Events: TextDelta, DagExecutionEvent, TransparencyStepEvent, etc.
}

// Private WebSocket connection management
Future<void> _ensureConnected()
Future<void> _closeConnection()
Future<void> _reconnectWithExponentialBackoff()
```

### 6.2 Why Polling Instead of WebSocket

Current implementation uses **5-second polling** rather than WebSocket for execution status because:

1. **Execution updates are infrequent** (every few seconds at minimum)
2. **Task execution screen has low update frequency** compared to chat (where streaming is character-by-character)
3. **Polling simplifies lifecycle** (no connection persistence after screen closes)
4. **Polling is sufficient for UX** (5s latency is acceptable for most execution workflows)

### 6.3 Commercial Polish Opportunity

For premium features, could add:
- WebSocket stream for execution status (reduces latency from 5s to <500ms)
- Progress events (step 1/10 complete, etc.)
- Live execution logs/activity feed

---

## 7. LEARNING REPORT & FEEDBACK INTEGRATION

**Location**: `mobile/lib/features/report/presentation/screens/learning_report_screen.dart`

The learning_report_screen recently added:
- Execution result metrics (quality score, validation stats)
- Trust level visualization
- Execution metadata in reports

---

## 8. WHAT'S MISSING FOR POLISHED COMMERCIAL EXPERIENCE

### 8.1 UI/UX Gaps

| Gap | Impact | Effort |
|-----|--------|--------|
| **No animated state transitions** | Feels stiff/abrupt | Low |
| **No execution timeline** | Hard to understand duration/progress | Medium |
| **No step-by-step visualization** | Can't see what OpenClaw is doing | High |
| **Output preview is text-only** | Complex results are unreadable | Medium |
| **No expanded details view** | Users can't drill into execution logs | Medium |
| **Approval UI lacks context** | Users blindly confirm without seeing what changed | Medium |
| **Error messages are plain text** | Important errors don't stand out | Low |
| **No execution history in UI** | Can't see past executions on this screen | Low |
| **Templates not searchable** | Hard to find right template | Low |
| **No success celebration** | Execution success feels anticlimactic | Low |

### 8.2 State Management Gaps

| Gap | Impact | Effort |
|-----|--------|--------|
| **Polling-only updates** | 5s latency is noticeable | High |
| **No retry/backoff logic** | Failed polls disappear silently | Medium |
| **No local caching** | Refetching same data repeatedly | Low |
| **No pagination** for intent history | Can't browse past executions | Low |

### 8.3 Mobile-Specific UX Gaps

| Gap | Impact | Effort |
|-----|--------|--------|
| **Approval buttons not large enough** | Hard to tap reliably on mobile | Low |
| **No bottom sheet for templates** | Templates could be in scrollable panel | Medium |
| **No haptic feedback on approval** | Confirmation doesn't feel tactile | Low |
| **No background sync** | If user leaves execution screen, updates stop | High |

### 8.4 Accessibility Gaps

| Gap | Impact | Effort |
|-----|--------|--------|
| **Status icons could have semantic labels** | Screen readers can't distinguish states | Low |
| **Color-only status indication** | Color-blind users can't see status | Low |
| **No loading announcement** | Screen readers don't announce polling updates | Low |

---

## 9. DESIGN QUALITY ASSESSMENT

### 9.1 Strengths

✓ **Coherent color semantics** - Status colors match Material/commercial standards
✓ **Clear information hierarchy** - Most important info (status + buttons) prominent
✓ **Consistent spacing** - 8px rhythm throughout, no arbitrary gaps
✓ **Proper iconography** - Material icons match intent semantics
✓ **Responsive layout** - Works on small phones, doesn't overflow
✓ **State clarity** - Loading states, disabled states clearly communicated
✓ **User safety** - Approval flow forces deliberate action (not auto-confirmation)
✓ **Mobile-appropriate** - Buttons are reasonably sized for touch
✓ **Dark mode support** - Surfaces adapt to theme

### 9.2 Areas for Polish

The current UI feels like a **minimum viable product** rather than a **premium feature**:

1. **Lacks visual hierarchy depth** - All elements feel equally important
2. **No micro-animations** - State changes are instant, not graceful
3. **Output is plain text** - Can't visualize structured data
4. **Missing contextual details** - When approving, user doesn't see what they're approving
5. **No success ceremony** - Execution success is just a checkmark
6. **Loading states are subtle** - Users might not notice execution is happening

**Comparison to commercial AI tools**:
- **ChatGPT**: Streaming text with thinking dots, clear task breakdown, copyable outputs
- **Claude Artifacts**: Syntax highlighting, live preview, versioning
- **Copilot**: Step-by-step progress, rollback options, confidence indicators
- **GitHub Actions**: Timeline view, log viewer, artifact viewer

Sparkle's execution UI covers the basics but lacks these premium touches.

---

## 10. RECOMMENDED IMPROVEMENTS (Prioritized)

### Phase 1: Quick Wins (Low effort, high impact)
1. Add loading skeleton to execution status card
2. Show execution duration (time elapsed since dispatch)
3. Make approval buttons larger/more prominent
4. Add success celebration for execution success
5. Style error messages as callouts/alerts

### Phase 2: Medium Effort
1. Add expandable "Details" section with full output/logs
2. Implement animated state transitions (Slide, Fade)
3. Add approval dialog showing "before/after" of execution changes
4. Implement execution history panel
5. Add template search/filter

### Phase 3: High Polish
1. Switch from polling to WebSocket for real-time updates
2. Implement step-by-step execution visualization
3. Add rich output formatting (tables, code blocks, images)
4. Implement execution replay/undo
5. Add confidence indicators to results

---

## File Structure Summary

```
mobile/lib/features/task/
├── presentation/
│   ├── screens/
│   │   └── task_execution_screen.dart          (2155 lines - main UI)
│   ├── providers/
│   │   └── task_provider.dart                  (863 lines - state mgmt)
│   └── widgets/
│       └── task_*.dart                         (supporting widgets)
├── data/
│   ├── repositories/
│   │   └── task_repository.dart                (889 lines - API calls)
│   └── models/
│       ├── execution_intent_model.dart         (242 lines)
│       ├── execution_record_model.dart         (63 lines)
│       ├── execution_template_model.dart       (65 lines)
│       └── *.dart                              (other models)
└── utils/
    └── task_identity.dart                      (taskId helpers)
```

---

## Conclusion

Sparkle's OpenClaw integration is **architecturally sound and functionally complete**. The UI clearly communicates status and supports the full execution workflow (handoff → approval → confirmation).

However, the polish level is **MVP rather than premium**. Adding animations, expanded details views, richer output formatting, and WebSocket updates would elevate it to commercial quality.

The codebase is well-structured for these improvements - the foundation is solid, just needs visual/UX refinement.
