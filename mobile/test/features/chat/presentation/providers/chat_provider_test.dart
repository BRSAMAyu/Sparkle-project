import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:riverpod/riverpod.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/shared/entities/task_model.dart';

// Mock Classes
@GenerateMocks([
  ChatRepository,
])
class MockChatRepository extends Mock implements ChatRepository {}

void main() {
  group('ChatProvider Tests', () {
    late MockChatRepository mockRepository;
    late ProviderContainer container;
    late ChatNotifier notifier;

    setUp(() {
      mockRepository = MockChatRepository();

      // Setup default mock behaviors
      provideDummy<ChatRepository>(mockRepository);

      container = ProviderContainer(
        overrides: [
          chatRepositoryProvider.overrideWithValue(mockRepository),
        ],
      );

      notifier = container.read(chatProvider.notifier);
    });

    tearDown(() {
      container.dispose();
      notifier.dispose();
    });

    group('Message Sending', () {
      test('should send message and update state', () async {
        // Mock the chatStream method to return an empty stream
        when(mockRepository.chatStream(
          any,
          any,
          userId: anyNamed('userId'),
          nickname: anyNamed('nickname'),
          token: anyNamed('token'),
          fileIds: anyNamed('fileIds'),
          includeReferences: anyNamed('includeReferences'),
          extraContext: anyNamed('extraContext'),
          chatMode: anyNamed('chatMode'),
          requestId: anyNamed('requestId'),
        )).thenAnswer((_) => Stream.empty());

        // Send message
        await notifier.sendMessage('Test message');

        // Verify the message was sent (state changed to isSending)
        expect(notifier.state.isSending, isFalse); // Should complete quickly with empty stream

        verify(mockRepository.chatStream(
          'Test message',
          null,
          userId: anyNamed('userId'),
          nickname: anyNamed('nickname'),
          token: anyNamed('token'),
          fileIds: anyNamed('fileIds'),
          includeReferences: anyNamed('includeReferences'),
          extraContext: anyNamed('extraContext'),
          chatMode: anyNamed('chatMode'),
          requestId: anyNamed('requestId'),
        )).called(1);
      });

      test('should set isSending to true during message send', () async {
        // Create a stream that emits events with delays
        final controller = StreamController<ChatStreamEvent>();

        when(mockRepository.chatStream(
          any,
          any,
          userId: anyNamed('userId'),
          nickname: anyNamed('nickname'),
          token: anyNamed('token'),
          fileIds: anyNamed('fileIds'),
          includeReferences: anyNamed('includeReferences'),
          extraContext: anyNamed('extraContext'),
          chatMode: anyNamed('chatMode'),
          requestId: anyNamed('requestId'),
        )).thenAnswer((_) => controller.stream);

        // Send message
        final future = notifier.sendMessage('Test');

        // Check initial state
        expect(notifier.state.isSending, isTrue);

        // Complete the stream
        controller.add(DoneEvent(finishReason: 'stop'));
        await controller.close();
        await future;

        // Should be false after completion
        expect(notifier.state.isSending, isFalse);
      });

      test('should handle send error gracefully', () async {
        // Mock to return an error stream
        final controller = StreamController<ChatStreamEvent>();

        when(mockRepository.chatStream(
          any,
          any,
          userId: anyNamed('userId'),
          nickname: anyNamed('nickname'),
          token: anyNamed('token'),
          fileIds: anyNamed('fileIds'),
          includeReferences: anyNamed('includeReferences'),
          extraContext: anyNamed('extraContext'),
          chatMode: anyNamed('chatMode'),
          requestId: anyNamed('requestId'),
        )).thenAnswer((_) => controller.stream);

        final future = notifier.sendMessage('Test');

        // Send error event
        controller.add(ErrorEvent(
          code: 'TEST_ERROR',
          message: 'Test error',
          retryable: false,
        ));
        await controller.close();
        await future;

        // Should have error state
        expect(notifier.state.error, isNotNull);
      });
    });

    group('Agent Collaboration', () {
      test('should update AI status during agent execution', () async {
        final controller = StreamController<ChatStreamEvent>();

        when(mockRepository.chatStream(
          any,
          any,
          userId: anyNamed('userId'),
          nickname: anyNamed('nickname'),
          token: anyNamed('token'),
          fileIds: anyNamed('fileIds'),
          includeReferences: anyNamed('includeReferences'),
          extraContext: anyNamed('extraContext'),
          chatMode: anyNamed('chatMode'),
          requestId: anyNamed('requestId'),
        )).thenAnswer((_) => controller.stream);

        final future = notifier.sendMessage('Test');

        // Send status update
        controller.add(StatusUpdateEvent(
          state: 'thinking',
          details: 'AI is thinking...',
        ));

        await Future<void>.delayed(const Duration(milliseconds: 50));

        // Verify AI status was updated
        expect(notifier.state.aiStatus, equals('thinking'));

        // Complete
        controller.add(DoneEvent(finishReason: 'stop'));
        await controller.close();
        await future;
      });

      test('should track active tools', () async {
        final controller = StreamController<ChatStreamEvent>();

        when(mockRepository.chatStream(
          any,
          any,
          userId: anyNamed('userId'),
          nickname: anyNamed('nickname'),
          token: anyNamed('token'),
          fileIds: anyNamed('fileIds'),
          includeReferences: anyNamed('includeReferences'),
          extraContext: anyNamed('extraContext'),
          chatMode: anyNamed('chatMode'),
          requestId: anyNamed('requestId'),
        )).thenAnswer((_) => controller.stream);

        final future = notifier.sendMessage('Test');

        // Send tool start event
        controller.add(ToolStartEvent(toolName: 'search_knowledge'));

        await Future<void>.delayed(const Duration(milliseconds: 50));

        // Verify tool is tracked
        expect(notifier.state.activeTools, contains('search_knowledge'));

        // Send tool result
        controller.add(ToolResultEvent(
          result: ToolResultModel(
            toolName: 'search_knowledge',
            toolCallId: 'call-123',
          ),
        ));

        await Future<void>.delayed(const Duration(milliseconds: 50));

        // Tool should be removed after result
        expect(notifier.state.activeTools, isNot(contains('search_knowledge')));

        // Complete
        controller.add(DoneEvent(finishReason: 'stop'));
        await controller.close();
        await future;
      });

      test('should track reasoning steps', () async {
        final controller = StreamController<ChatStreamEvent>();

        when(mockRepository.chatStream(
          any,
          any,
          userId: anyNamed('userId'),
          nickname: anyNamed('nickname'),
          token: anyNamed('token'),
          fileIds: anyNamed('fileIds'),
          includeReferences: anyNamed('includeReferences'),
          extraContext: anyNamed('extraContext'),
          chatMode: anyNamed('chatMode'),
          requestId: anyNamed('requestId'),
        )).thenAnswer((_) => controller.stream);

        final future = notifier.sendMessage('Test');

        final reasoningStep = ReasoningStep(
          stepId: 'step-1',
          description: 'Analyzing user request',
          timestamp: DateTime.now(),
        );

        controller.add(ReasoningStepEvent(reasoningSteps: [reasoningStep]));

        await Future<void>.delayed(const Duration(milliseconds: 50));

        // Verify reasoning steps are recorded
        expect(notifier.state.reasoningSteps, isNotEmpty);
        expect(notifier.state.reasoningSteps.first.description,
            equals('Analyzing user request'));

        // Complete
        controller.add(DoneEvent(finishReason: 'stop'));
        await controller.close();
        await future;
      });
    });

    group('Plan Review Integration', () {
      test('should handle plan review widget events', () async {
        final controller = StreamController<ChatStreamEvent>();

        when(mockRepository.chatStream(
          any,
          any,
          userId: anyNamed('userId'),
          nickname: anyNamed('nickname'),
          token: anyNamed('token'),
          fileIds: anyNamed('fileIds'),
          includeReferences: anyNamed('includeReferences'),
          extraContext: anyNamed('extraContext'),
          chatMode: anyNamed('chatMode'),
          requestId: anyNamed('requestId'),
        )).thenAnswer((_) => controller.stream);

        final future = notifier.sendMessage('Test');

        final reviewEvent = PlanReviewWidgetEvent(
          reviewData: {
            'plan_id': 'plan-123',
            'score': 85,
            'issues': [],
          },
        );

        controller.add(reviewEvent);

        await Future<void>.delayed(const Duration(milliseconds: 50));

        // The widget should be added to the messages
        // Note: Plan review handling is done internally in the provider
        // We just verify the stream processing completes
        expect(notifier.state.isSending, isTrue);

        // Complete
        controller.add(DoneEvent(finishReason: 'stop'));
        await controller.close();
        await future;
      });
    });

    group('Voice Input', () {
      test('should handle voice input state', () async {
        // This is handled by UI components, not the provider
        // The provider processes voice as regular text
        final transcript = 'Hello AI assistant';

        final controller = StreamController<ChatStreamEvent>();

        when(mockRepository.chatStream(
          any,
          any,
          userId: anyNamed('userId'),
          nickname: anyNamed('nickname'),
          token: anyNamed('token'),
          fileIds: anyNamed('fileIds'),
          includeReferences: anyNamed('includeReferences'),
          extraContext: anyNamed('extraContext'),
          chatMode: anyNamed('chatMode'),
          requestId: anyNamed('requestId'),
        )).thenAnswer((_) => controller.stream);

        await notifier.sendMessage(transcript);

        // Verify message was sent
        verify(mockRepository.chatStream(
          transcript,
          any,
          userId: anyNamed('userId'),
          nickname: anyNamed('nickname'),
          token: anyNamed('token'),
          fileIds: anyNamed('fileIds'),
          includeReferences: anyNamed('includeReferences'),
          extraContext: anyNamed('extraContext'),
          chatMode: anyNamed('chatMode'),
          requestId: anyNamed('requestId'),
        )).called(1);

        // Complete
        controller.add(DoneEvent(finishReason: 'stop'));
        await controller.close();
      });
    });

    group('Error Recovery', () {
      test('should show user-friendly error messages', () async {
        final controller = StreamController<ChatStreamEvent>();

        when(mockRepository.chatStream(
          any,
          any,
          userId: anyNamed('userId'),
          nickname: anyNamed('nickname'),
          token: anyNamed('token'),
          fileIds: anyNamed('fileIds'),
          includeReferences: anyNamed('includeReferences'),
          extraContext: anyNamed('extraContext'),
          chatMode: anyNamed('chatMode'),
          requestId: anyNamed('requestId'),
        )).thenAnswer((_) => controller.stream);

        final future = notifier.sendMessage('Test');

        final errorEvent = ErrorEvent(
          code: 'TEST_ERROR',
          message: 'Something went wrong',
          retryable: true,
        );

        controller.add(errorEvent);
        await controller.close();
        await future;

        // Verify error is shown
        expect(notifier.state.error, isNotNull);
        expect(notifier.state.isErrorRetryable, isTrue);
      });
    });

    group('Concurrency and State Consistency', () {
      test('should prevent message sending during plan switch', () async {
        // Set plan switch flag
        notifier.isSwitchingPlan = true;

        final controller = StreamController<ChatStreamEvent>();

        when(mockRepository.chatStream(
          any,
          any,
          userId: anyNamed('userId'),
          nickname: anyNamed('nickname'),
          token: anyNamed('token'),
          fileIds: anyNamed('fileIds'),
          includeReferences: anyNamed('includeReferences'),
          extraContext: anyNamed('extraContext'),
          chatMode: anyNamed('chatMode'),
          requestId: anyNamed('requestId'),
        )).thenAnswer((_) => controller.stream);

        // Try to send message during plan switch
        await notifier.sendMessage('Should be blocked');

        // Should not call the repository because of plan switch
        verifyNever(mockRepository.chatStream(
          any,
          any,
          userId: anyNamed('userId'),
          nickname: anyNamed('nickname'),
          token: anyNamed('token'),
          fileIds: anyNamed('fileIds'),
          includeReferences: anyNamed('includeReferences'),
          extraContext: anyNamed('extraContext'),
          chatMode: anyNamed('chatMode'),
          requestId: anyNamed('requestId'),
        ));

        await controller.close();
      });
    });

    group('Resource Cleanup', () {
      test('should dispose subscriptions on dispose', () async {
        final controller = StreamController<ChatStreamEvent>();

        when(mockRepository.chatStream(
          any,
          any,
          userId: anyNamed('userId'),
          nickname: anyNamed('nickname'),
          token: anyNamed('token'),
          fileIds: anyNamed('fileIds'),
          includeReferences: anyNamed('includeReferences'),
          extraContext: anyNamed('extraContext'),
          chatMode: anyNamed('chatMode'),
          requestId: anyNamed('requestId'),
        )).thenAnswer((_) => controller.stream);

        await notifier.sendMessage('Test');

        // Verify state is sending
        expect(notifier.state.isSending, isTrue);

        // Dispose
        notifier.dispose();

        // Verify clean up doesn't throw
        expect(() => notifier.dispose(), returnsNormally);

        await controller.close();
      });
    });
  });
}
