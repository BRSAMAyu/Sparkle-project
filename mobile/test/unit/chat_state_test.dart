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
      messages: const [],
      isSending: true,
      aiStatus: 'status',
      isReasoningActive: true,
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
}
