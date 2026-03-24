import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';

void main() {
  test('ChatState copyWith clear flags reset fields', () {
    final state = ChatState(
      isSending: true,
      error: 'oops',
      errorCode: 'E1',
      isErrorRetryable: true,
      streamingContent: 'hello',
      aiStatus: 'thinking',
      aiStatusDetails: 'details',
    );

    final cleared = state.copyWith(
      clearError: true,
      clearAiStatus: true,
      streamingContent: '',
    );

    expect(cleared.error, isNull);
    expect(cleared.errorCode, isNull);
    expect(cleared.isErrorRetryable, isFalse);
    expect(cleared.aiStatus, isNull);
    expect(cleared.aiStatusDetails, isNull);
    expect(cleared.streamingContent, isEmpty);
  });

  test('ChatState listItemCount reflects status flags', () {
    final state = ChatState(
      isSending: true,
      aiStatus: 'status',
      isReasoningActive: true,
      activeRunId: 'run-1',
      runPhase: ChatRunPhase.streaming,
    );

    expect(state.listItemCount, 3);
  });

  test('ChatState copyWith clearDagExecution resets dag signal', () {
    final state = ChatState(
      dagExecutionSignal:
          DagExecutionSignal(event: 'layer_start', layerNumber: 1),
    );

    final cleared = state.copyWith(clearDagExecution: true);
    expect(cleared.dagExecutionSignal, isNull);
  });

  test('ChatState clearTransparency resets transparency payload and step state',
      () {
    final state = ChatState(
      transparencyData: const TransparencyData(
        steps: [],
        totalDurationMs: 0,
        requestId: 'req-1',
      ),
      runLedgerSummary: const RunLedgerSummary(
        traceId: 'trace-1',
        status: 'running',
        route: {},
        models: [],
        agents: [],
        quality: {},
        evidence: {},
        response: {},
        feedback: {},
        timeline: [],
        eventCount: 1,
      ),
      currentStepId: 2,
      currentStepIndex: 1,
    );

    final cleared = state.copyWith(clearTransparency: true);
    expect(cleared.transparencyData, isNull);
    expect(cleared.runLedgerSummary, isNull);
    expect(cleared.currentStepId, isNull);
    expect(cleared.currentStepIndex, isNull);
  });

  test('ChatState stores active run metadata', () {
    final state = ChatState(
      activeRunId: 'run-1',
      runPhase: ChatRunPhase.streaming,
      activeRunSummary: const ActiveRunSummary(
        status: 'GENERATING',
        details: '正在组织答案',
        agentName: 'planner',
        toolCount: 2,
      ),
      transparencyPresentationState:
          const TransparencyPresentationState(isDismissed: true),
    );

    expect(state.activeRunId, 'run-1');
    expect(state.runPhase, ChatRunPhase.streaming);
    expect(state.activeRunSummary?.toolCount, 2);
    expect(state.transparencyPresentationState.isDismissed, isTrue);
  });
}
