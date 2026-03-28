# Execution UI Enhancement Roadmap

## Overview

This document outlines a phased approach to elevate Sparkle's OpenClaw execution UI from MVP to commercial polish. The current implementation is functionally complete but lacks the polish of premium AI tools.

---

## Current Implementation Details

### 1. State Management Flow

```
User clicks "交给 AI 执行"
  ↓
handoffTaskToAi() called
  ├─ Sets handoffInFlight = true
  ├─ POST /executions/tasks/{taskId}/handoff
  └─ Starts 5-second polling timer
      ├─ loadTaskExecutionState() every 5s
      └─ Updates ExecutionIntentModel
  
Task execution reaches terminal state
  └─ polling stops (isTerminal = true)
```

### 2. UI State Tree

```
TaskListState
├── taskExecutions[taskId]          → ExecutionIntentModel (current execution)
├── taskExecutionRecords[taskId]    → ExecutionRecordModel (output/validation)
├── taskExecutionTemplates[taskId]  → List<ExecutionTemplateModel> (available)
├── selectedExecutionTemplateIds    → User template choice
├── handoffInFlight                 → Set of tasks being handed off
└── executionDecisionInFlight       → Set of tasks awaiting approval decision
```

### 3. Widget Hierarchy

```
TaskExecutionScreen
└── _BottomControls (ConsumerWidget)
    ├── Template Selection UI (if !executionIntent && templates.isNotEmpty)
    │   └── Wrap(ChoiceChip x 3)
    │
    ├── Execution Status Card (if executionIntent != null || handoffInFlight)
    │   ├── Status Icon + Color
    │   ├── Title + Subtitle
    │   ├── Output Preview (text)
    │   └── Meta Preview (template, strategy, node)
    │
    ├── Approval Buttons (if executionIntent?.isWaitingApproval)
    │   ├── "取回任务" (reject)
    │   └── "确认采用 AI 结果" (confirm)
    │
    ├── Handoff Button (full width)
    │   └── Adaptive text + disabled state
    │
    └── Standard Controls
        ├── "放弃" (abandon)
        └── "完成" (complete)
```

---

## Phase 1: Quick Wins (1-2 Days)

### 1.1 Execution Duration Display

**Current**: Status card shows status and output only
**Enhancement**: Add elapsed time indicator

```dart
Widget _buildExecutionDuration(ExecutionIntentModel intent) {
  if (intent.dispatchedAt == null) return SizedBox.shrink();
  
  final elapsed = DateTime.now().difference(intent.dispatchedAt!);
  final formatted = _formatDuration(elapsed);
  
  return Padding(
    padding: const EdgeInsets.only(top: DS.spacing8),
    child: Row(
      children: [
        Icon(Icons.schedule, size: 14, color: DS.neutral600),
        SizedBox(width: DS.spacing4),
        Text(
          'Running for $formatted',
          style: DS.bodySmall.copyWith(color: DS.neutral600),
        ),
      ],
    ),
  );
}
```

**Where to add**: In `_BottomControls.build()`, after status subtitle (line 1820)

### 1.2 Error Message Styling

**Current**: Plain text error messages
**Enhancement**: Styled callout boxes

```dart
if (intent.errorMessage != null && intent.errorMessage!.isNotEmpty)
  Container(
    margin: const EdgeInsets.only(top: DS.spacing8),
    padding: const EdgeInsets.all(DS.spacing12),
    decoration: BoxDecoration(
      color: DS.error.withValues(alpha: 0.1),
      border: Border.all(
        color: DS.error.withValues(alpha: 0.3),
        width: 1,
      ),
      borderRadius: BorderRadius.circular(DS.borderRadiusSM),
    ),
    child: Row(
      children: [
        Icon(
          Icons.error_outline,
          color: DS.error,
          size: 16,
        ),
        const SizedBox(width: DS.spacing8),
        Expanded(
          child: Text(
            intent.errorMessage!,
            style: DS.bodySmall.copyWith(color: DS.error),
          ),
        ),
      ],
    ),
  ),
```

### 1.3 Approval Button Enhancement

**Current**: Inline buttons, small text
**Enhancement**: Larger, bottom-sheet style

```dart
// Consider moving approval workflow to modal bottom sheet
if (executionIntent?.isWaitingApproval == true) {
  showApprovalBottomSheet(context, executionIntent, executionRecord);
}
```

### 1.4 Success Celebration

**Current**: Status change, no ceremony
**Enhancement**: Add brief animation on success

```dart
if (executionIntent?.status == ExecutionIntentStatus.succeeded) {
  // Add success animation (e.g., confetti burst, checkmark animation)
  WidgetsBinding.instance.addPostFrameCallback((_) {
    showSuccessCelebration(context);
  });
}
```

### 1.5 Status Icon Loading Skeleton

**Current**: Icon appears/disappears instantly
**Enhancement**: Add placeholder skeleton

```dart
Widget _buildStatusIcon(
  ExecutionIntentModel? intent,
  bool isLoading,
) {
  if (isLoading) {
    return Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        color: DS.neutral200,
        borderRadius: BorderRadius.circular(DS.borderRadiusSM),
      ),
      child: const Shimmer(),
    );
  }
  
  return Container(
    // ... existing code
  );
}
```

**Estimated Effort**: 4-6 hours  
**Impact**: Medium (improves polish and clarity)

---

## Phase 2: Medium Enhancements (3-5 Days)

### 2.1 Expandable Details Panel

Add a collapsible section showing full execution details:

```dart
class _ExecutionDetailsPanel extends StatefulWidget {
  final ExecutionIntentModel intent;
  final ExecutionRecordModel? record;
  
  @override
  State<_ExecutionDetailsPanel> createState() => _ExecutionDetailsPanelState();
}

// Shows:
// - Full parsed output (not just preview)
// - Validation results (if any)
// - Quality score with confidence
// - Execution metadata timeline
//   - Created at
//   - Dispatched at
//   - Completed at
//   - Duration
```

**Implementation**:
1. Create new widget `ExecutionDetailsPanel`
2. Add ExpansionTile to execution status card
3. Format full output (JSON → pretty-printed table)
4. Show metadata timeline

### 2.2 Animated State Transitions

Replace instant appearance with smooth animations:

```dart
// Current: status card appears/disappears instantly
return showExecutionStatus ? statusCard : SizedBox.shrink();

// Enhanced: animated slide in/out
AnimatedSwitcher(
  duration: Duration(milliseconds: 300),
  transitionBuilder: (child, animation) => SlideTransition(
    position: Tween<Offset>(
      begin: const Offset(0, 0.2),
      end: Offset.zero,
    ).animate(animation),
    child: child,
  ),
  child: showExecutionStatus
      ? statusCard
      : const SizedBox.shrink(),
)
```

### 2.3 Approval Dialog with Context

Currently, users blindly confirm without seeing changes. Add a modal showing:
- What will be executed
- Expected output
- Confidence/quality score
- Approval vs. rejection impact

```dart
Future<void> _confirmAiResult(BuildContext context, WidgetRef ref) async {
  // Show modal instead of inline
  final result = await showApprovalModal(
    context,
    intent: executionIntent,
    record: executionRecord,
  );
  
  if (result == true) {
    // Proceed with confirmation
  }
}
```

### 2.4 Execution History in UI

Add a collapsible "Past Executions" section:

```dart
// Show last 3-5 execution intents for this task
if (executionIntents.isNotEmpty) {
  return ExpansionTile(
    title: Text('Execution History (${executionIntents.length})'),
    children: executionIntents.take(5).map((intent) {
      return ListTile(
        leading: _statusIcon(intent),
        title: Text(intent.templateName ?? 'Unknown'),
        subtitle: Text(intent.createdAt?.formatted ?? ''),
        trailing: Text(intent.statusLabel),
      );
    }).toList(),
  );
}
```

### 2.5 Rich Output Formatting

Currently, `parsedOutput` is displayed as plain text. Add formatting:

```dart
Widget _formatParsedOutput(Map<String, dynamic>? output) {
  if (output == null) return SizedBox.shrink();
  
  return Column(
    children: output.entries.map((entry) {
      final value = entry.value;
      
      if (value is List) {
        return _formatList(entry.key, value);
      } else if (value is Map) {
        return _formatMap(entry.key, value);
      } else {
        return _formatScalar(entry.key, value);
      }
    }).toList(),
  );
}

Widget _formatList(String key, List<dynamic> items) {
  return Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text('$key:', style: DS.bodyMedium.copyWith(fontWeight: DS.fontWeightBold)),
      ...items.map((item) => Padding(
        padding: const EdgeInsets.only(left: DS.spacing16, top: DS.spacing4),
        child: Text('• $item', style: DS.bodySmall),
      )).toList(),
    ],
  );
}
```

**Estimated Effort**: 8-12 hours  
**Impact**: High (significantly improves user confidence)

---

## Phase 3: Premium Enhancements (1-2 Weeks)

### 3.1 WebSocket Integration

Replace 5-second polling with real-time updates:

```dart
// In TaskNotifier, add WebSocket stream
Future<void> _subscribeToExecutionUpdates(String taskId) async {
  _executionStream = _websocketService
      .executionStream(taskId)
      .listen((event) {
    if (event is ExecutionStatusChanged) {
      _setTaskExecution(taskId, event.intent);
      _setTaskExecutionRecord(taskId, event.record);
    }
  });
}

// Reuse websocket_chat_service_v2.dart pattern
```

### 3.2 Step-by-Step Execution Visualization

Show what OpenClaw is currently doing:

```dart
// New model: ExecutionStep
class ExecutionStep {
  final int stepNumber;
  final String description;
  final DateTime startedAt;
  final DateTime? completedAt;
  final String status; // pending | running | completed | failed
  final String? output;
  final String? error;
}

// UI: Timeline showing steps
Widget _buildExecutionTimeline(List<ExecutionStep> steps) {
  return TimelineTile(
    steps: steps.map((step) => TimelineTileStep(
      number: step.stepNumber,
      title: step.description,
      status: step.status,
      duration: step.completedAt?.difference(step.startedAt),
      output: step.output,
    )).toList(),
  );
}
```

### 3.3 Confidence/Quality Indicators

Visualize result quality:

```dart
Widget _buildQualityIndicator(ExecutionRecordModel? record) {
  if (record?.qualityScore == null) return SizedBox.shrink();
  
  final score = record!.qualityScore!;
  return Column(
    children: [
      LinearProgressIndicator(
        value: score,
        backgroundColor: DS.neutral200,
        valueColor: AlwaysStoppedAnimation<Color>(
          score > 0.8 ? DS.success : score > 0.5 ? DS.warning : DS.error
        ),
      ),
      Text(
        'Quality: ${(score * 100).toStringAsFixed(0)}%',
        style: DS.bodySmall,
      ),
    ],
  );
}
```

### 3.4 Execution Replay/Undo

Allow users to:
- Rerun with same parameters
- Adjust parameters and rerun
- Rollback to previous execution

```dart
// New button: "Modify & Re-execute"
CustomButton.secondary(
  text: 'Modify & Re-execute',
  icon: Icons.edit,
  onPressed: () => _showModifyExecutionDialog(context),
)
```

### 3.5 Confidence Indicators

Add visual confidence scores:

```dart
// In execution status card, show:
// - Trust Level badge
// - Validation score (if HYBRID)
// - Quality score with tooltip

Widget _buildTrustBadge(ExecutionTrustLevel level) {
  return Container(
    padding: const EdgeInsets.symmetric(
      horizontal: DS.spacing8,
      vertical: DS.spacing4,
    ),
    decoration: BoxDecoration(
      color: _trustColor(level).withValues(alpha: 0.1),
      border: Border.all(
        color: _trustColor(level).withValues(alpha: 0.3),
      ),
      borderRadius: BorderRadius.circular(DS.borderRadiusSM),
    ),
    child: Text(
      level.label,
      style: DS.bodySmall.copyWith(
        color: _trustColor(level),
        fontWeight: DS.fontWeightMedium,
      ),
    ),
  );
}
```

**Estimated Effort**: 3-4 weeks  
**Impact**: Very High (transformative UX)

---

## Implementation Priorities

### Must-Have (Commercial Quality):
1. Error message styling (phase 1.2)
2. Execution duration display (phase 1.1)
3. Expandable details panel (phase 2.1)
4. Animated transitions (phase 2.2)
5. Approval dialog with context (phase 2.3)

### Nice-to-Have (Premium Polish):
1. Rich output formatting (phase 2.5)
2. WebSocket integration (phase 3.1)
3. Execution history (phase 2.4)
4. Confidence indicators (phase 3.5)

### Deferred (Future Enhancements):
1. Step-by-step visualization (phase 3.2)
2. Execution replay/undo (phase 3.4)

---

## Code Organization Recommendations

### New Files to Create:

```
mobile/lib/features/task/presentation/widgets/
├── execution_status_card.dart              (refactor from _BottomControls)
├── execution_details_panel.dart            (phase 2.1)
├── execution_approval_modal.dart           (phase 2.3)
├── execution_output_formatter.dart         (phase 2.5)
├── execution_timeline.dart                 (phase 3.2)
└── execution_quality_indicator.dart        (phase 3.5)

mobile/lib/core/services/
└── execution_websocket_service.dart        (phase 3.1)
```

### Files to Modify:

1. `task_execution_screen.dart` - Refactor _BottomControls, use new widgets
2. `task_provider.dart` - Add WebSocket subscription (phase 3.1)
3. `design_system.dart` - Add execution-specific tokens (if needed)

---

## Testing Strategy

### Unit Tests:
- `execution_output_formatter_test.dart` - Output formatting logic
- `execution_status_color_test.dart` - Status → color mapping

### Widget Tests:
- `execution_status_card_test.dart` - Renders correctly for all states
- `execution_approval_modal_test.dart` - Approval flow

### Integration Tests:
- Full handoff → execution → approval workflow
- Polling behavior with different execution durations
- Error handling (network failures, malformed responses)

---

## Success Metrics

After implementing Phase 1 + Phase 2:
- ✓ 95%+ users can understand execution status at a glance
- ✓ <5% of users say "I don't know what's happening" during execution
- ✓ Approval flow completion rate improves by 20%
- ✓ Support tickets about execution UX drop by 50%

After Phase 3:
- ✓ Execution feature mentioned as "premium" in user reviews
- ✓ WebSocket integration reduces apparent latency from 5s to <500ms
- ✓ 90%+ approval completion without needing to drill into details

---

## References

- Current implementation: `/mobile/lib/features/task/presentation/screens/task_execution_screen.dart`
- State management: `/mobile/lib/features/task/presentation/providers/task_provider.dart`
- Design tokens: `/mobile/lib/core/design/design_system.dart`
- Chat streaming example: `/mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart`
- Backend alignment doc: `/docs/architecture/SPARKLE_OPENCLAW_ALIGNMENT_v1.0.md`
