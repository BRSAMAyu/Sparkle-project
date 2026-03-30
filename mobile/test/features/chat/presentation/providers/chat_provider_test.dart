import 'package:flutter_test/flutter_test.dart';
import 'package:riverpod/riverpod.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/chat/data/models/reasoning_step_model.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';

void main() {
  // Initialize Flutter test bindings
  TestWidgetsFlutterBinding.ensureInitialized();

  group('ChatProvider Tests', () {
    late ProviderContainer container;
    late ChatNotifier notifier;

    setUp(() {
      container = ProviderContainer();
      notifier = container.read(chatProvider.notifier);
    });

    tearDown(() {
      // Don't dispose notifier separately - container.dispose will handle it
      container.dispose();
    });

    group('Initial State', () {
      test('should start with default state', () {
        expect(notifier.state.isLoading, isFalse);
        expect(notifier.state.isSending, isFalse);
        expect(notifier.state.messages, isEmpty);
        expect(notifier.state.error, isNull);
      });

      test('should have idle run phase initially', () {
        expect(notifier.state.runPhase, equals(ChatRunPhase.idle));
      });

      test('should have correct initial connection state', () {
        expect(notifier.state.wsConnectionState,
            equals(WsConnectionState.disconnected));
      });
    });

    group('State Updates', () {
      test('should update error state', () {
        notifier.state = notifier.state.copyWith(
          error: 'Test error',
          isErrorRetryable: true,
        );

        expect(notifier.state.error, equals('Test error'));
        expect(notifier.state.isErrorRetryable, isTrue);
      });

      test('should update AI status', () {
        notifier.state = notifier.state.copyWith(
          aiStatus: 'thinking',
          aiStatusDetails: 'AI is processing...',
        );

        expect(notifier.state.aiStatus, equals('thinking'));
        expect(notifier.state.aiStatusDetails, equals('AI is processing...'));
      });

      test('should update active tools', () {
        notifier.state = notifier.state.copyWith(
          activeTools: ['search_knowledge', 'analyze'],
        );

        expect(notifier.state.activeTools.length, equals(2));
        expect(notifier.state.activeTools, contains('search_knowledge'));
      });

      test('should clear active tools via empty list', () {
        notifier.state = notifier.state.copyWith(
          activeTools: ['search_knowledge'],
        );

        expect(notifier.state.activeTools.length, equals(1));

        notifier.state = notifier.state.copyWith(
          activeTools: [],
        );

        expect(notifier.state.activeTools, isEmpty);
      });
    });

    group('Reasoning Steps', () {
      test('should update reasoning steps', () {
        final step = ReasoningStep(
          id: 'step-1',
          description: 'Analyzing user request',
          agent: AgentType.orchestrator,
          status: StepStatus.inProgress,
        );

        notifier.state = notifier.state.copyWith(
          reasoningSteps: [step],
        );

        expect(notifier.state.reasoningSteps.length, equals(1));
        expect(notifier.state.reasoningSteps.first.description,
            equals('Analyzing user request'));
      });

      test('should update reasoning active state', () {
        expect(notifier.state.isReasoningActive, isFalse);

        notifier.state = notifier.state.copyWith(isReasoningActive: true);

        expect(notifier.state.isReasoningActive, isTrue);
      });

      test('should clear reasoning steps', () {
        final step = ReasoningStep(
          id: 'step-1',
          description: 'Test',
          agent: AgentType.orchestrator,
          status: StepStatus.completed,
        );

        notifier.state = notifier.state.copyWith(
          reasoningSteps: [step],
        );

        expect(notifier.state.reasoningSteps.length, equals(1));

        // Clear reasoning
        notifier.state = notifier.state.copyWith(clearReasoning: true);

        expect(notifier.state.reasoningSteps, isEmpty);
      });
    });

    group('Run Phase Management', () {
      test('should update run phase', () {
        notifier.state = notifier.state.copyWith(
          runPhase: ChatRunPhase.streaming,
        );

        expect(notifier.state.runPhase, equals(ChatRunPhase.streaming));
        expect(notifier.state.runPhase.isActive, isTrue);
      });

      test('should track active run summary', () {
        final summary = ActiveRunSummary(
          status: 'running',
          details: 'Processing request',
          agentName: 'Orchestrator',
          toolCount: 2,
        );

        notifier.state = notifier.state.copyWith(
          activeRunSummary: summary,
        );

        expect(notifier.state.activeRunSummary?.status, equals('running'));
        expect(notifier.state.activeRunSummary?.toolCount, equals(2));
      });

      test('should clear active run summary', () {
        final summary = ActiveRunSummary(
          status: 'running',
          details: 'Test',
        );

        notifier.state = notifier.state.copyWith(
          activeRunSummary: summary,
        );

        expect(notifier.state.activeRunSummary, isNotNull);

        notifier.state = notifier.state.copyWith(clearActiveRunSummary: true);

        expect(notifier.state.activeRunSummary, isNull);
      });

      test('should correctly identify active phases', () {
        expect(ChatRunPhase.sending.isActive, isTrue);
        expect(ChatRunPhase.streaming.isActive, isTrue);
        expect(ChatRunPhase.finalizing.isActive, isTrue);
        expect(ChatRunPhase.idle.isActive, isFalse);
        expect(ChatRunPhase.completed.isActive, isFalse);
      });

      test('should correctly identify terminal phases', () {
        expect(ChatRunPhase.completed.isTerminal, isTrue);
        expect(ChatRunPhase.failed.isTerminal, isTrue);
        expect(ChatRunPhase.cancelled.isTerminal, isTrue);
        expect(ChatRunPhase.streaming.isTerminal, isFalse);
      });
    });

    group('Message Management', () {
      test('should add user message to state', () {
        final userMessage = ChatMessageModel(
          conversationId: 'conv-1',
          role: MessageRole.user,
          content: 'Hello AI',
        );

        notifier.state = notifier.state.copyWith(
          messages: [userMessage],
        );

        expect(notifier.state.messages.length, equals(1));
        expect(notifier.state.messages.first.role, equals(MessageRole.user));
        expect(notifier.state.messages.first.content, equals('Hello AI'));
      });

      test('should add assistant message to state', () {
        final assistantMessage = ChatMessageModel(
          conversationId: 'conv-1',
          role: MessageRole.assistant,
          content: 'Hello user',
        );

        notifier.state = notifier.state.copyWith(
          messages: [assistantMessage],
        );

        expect(notifier.state.messages.length, equals(1));
        expect(
            notifier.state.messages.first.role, equals(MessageRole.assistant));
      });

      test('should have multiple messages in correct order', () {
        final messages = [
          ChatMessageModel(
            conversationId: 'conv-1',
            role: MessageRole.user,
            content: 'First message',
          ),
          ChatMessageModel(
            conversationId: 'conv-1',
            role: MessageRole.assistant,
            content: 'First response',
          ),
          ChatMessageModel(
            conversationId: 'conv-1',
            role: MessageRole.user,
            content: 'Second message',
          ),
        ];

        notifier.state = notifier.state.copyWith(
          messages: messages,
        );

        expect(notifier.state.messages.length, equals(3));
        expect(notifier.state.messages[0].role, equals(MessageRole.user));
        expect(notifier.state.messages[1].role, equals(MessageRole.assistant));
        expect(notifier.state.messages[2].role, equals(MessageRole.user));
      });

      test('should retain only the most recent bounded message window', () {
        final messages = List<ChatMessageModel>.generate(
          ChatState.maxRetainedMessages + 25,
          (index) => ChatMessageModel(
            conversationId: 'conv-1',
            role: index.isEven ? MessageRole.user : MessageRole.assistant,
            content: 'message-$index',
          ),
        );

        notifier.state = notifier.state.copyWith(messages: messages);

        expect(
          notifier.state.messages.length,
          equals(ChatState.maxRetainedMessages),
        );
        expect(notifier.state.messages.first.content, equals('message-25'));
        expect(
          notifier.state.messages.last.content,
          equals('message-${messages.length - 1}'),
        );
      });
    });

    group('Connection State', () {
      test('should track WebSocket connection state', () {
        notifier.state = notifier.state.copyWith(
          wsConnectionState: WsConnectionState.connecting,
        );

        expect(notifier.state.wsConnectionState,
            equals(WsConnectionState.connecting));
      });

      test('should update to connected state', () {
        notifier.state = notifier.state.copyWith(
          wsConnectionState: WsConnectionState.connected,
        );

        expect(notifier.state.wsConnectionState,
            equals(WsConnectionState.connected));
      });

      test('should update to disconnected state', () {
        notifier.state = notifier.state.copyWith(
          wsConnectionState: WsConnectionState.disconnected,
        );

        expect(notifier.state.wsConnectionState,
            equals(WsConnectionState.disconnected));
      });

      test('should update to reconnecting state', () {
        notifier.state = notifier.state.copyWith(
          wsConnectionState: WsConnectionState.reconnecting,
        );

        expect(notifier.state.wsConnectionState,
            equals(WsConnectionState.reconnecting));
      });

      test('should update to failed state', () {
        notifier.state = notifier.state.copyWith(
          wsConnectionState: WsConnectionState.failed,
        );

        expect(
            notifier.state.wsConnectionState, equals(WsConnectionState.failed));
      });
    });

    group('Loading States', () {
      test('should update isLoading state', () {
        notifier.state = notifier.state.copyWith(
          isLoading: true,
        );

        expect(notifier.state.isLoading, isTrue);
      });

      test('should update isLoadingMore state', () {
        notifier.state = notifier.state.copyWith(
          isLoadingMore: true,
        );

        expect(notifier.state.isLoadingMore, isTrue);
      });

      test('should update hasMoreMessages state', () {
        notifier.state = notifier.state.copyWith(
          hasMoreMessages: true,
        );

        expect(notifier.state.hasMoreMessages, isTrue);
      });
    });

    group('Agent Activities', () {
      test('should create agent activity event', () {
        final activity = AgentActivityEvent(
          agentId: 'agent-1',
          status: 'running',
          displayName: 'Knowledge Agent',
          icon: 'brain',
          color: '#FF5722',
          description: 'Searching knowledge base',
        );

        expect(activity.agentId, equals('agent-1'));
        expect(activity.displayName, equals('Knowledge Agent'));
      });

      test('should track agent activities', () {
        final activities = [
          AgentActivityEvent(
            agentId: 'agent-1',
            status: 'completed',
            displayName: 'Orchestrator',
            icon: 'orchestrator',
            color: '#2196F3',
            description: 'Started workflow',
          ),
        ];

        notifier.state = notifier.state.copyWith(
          agentActivities: activities,
        );

        expect(notifier.state.agentActivities.length, equals(1));
        expect(notifier.state.agentActivities.first.agentId, equals('agent-1'));
      });

      test('should track current agent name', () {
        notifier.state = notifier.state.copyWith(
          currentAgentName: 'Knowledge Agent',
        );

        expect(notifier.state.currentAgentName, equals('Knowledge Agent'));
      });
    });

    group('DAG Execution', () {
      test('should track DAG execution signal', () {
        final signal = DagExecutionSignal(
          event: 'layer_start',
          layerNumber: 1,
          totalLayers: 3,
        );

        notifier.state = notifier.state.copyWith(
          dagExecutionSignal: signal,
        );

        expect(notifier.state.dagExecutionSignal?.event, equals('layer_start'));
        expect(notifier.state.dagExecutionSignal?.layerNumber, equals(1));
      });

      test('should clear DAG execution', () {
        final signal = DagExecutionSignal(
          event: 'layer_end',
          layerNumber: 1,
          totalLayers: 3,
        );

        notifier.state = notifier.state.copyWith(
          dagExecutionSignal: signal,
        );

        expect(notifier.state.dagExecutionSignal, isNotNull);

        notifier.state = notifier.state.copyWith(clearDagExecution: true);

        expect(notifier.state.dagExecutionSignal, isNull);
      });
    });

    group('Transparency Presentation', () {
      test('should track transparency presentation state', () {
        final presentationState = TransparencyPresentationState(
          isExpanded: true,
          isDismissed: false,
          lastCompletedLabel: 'Test completed',
        );

        notifier.state = notifier.state.copyWith(
          transparencyPresentationState: presentationState,
        );

        expect(notifier.state.transparencyPresentationState.isExpanded, isTrue);
        expect(notifier.state.transparencyPresentationState.lastCompletedLabel,
            equals('Test completed'));
      });

      test('should update transparency data', () {
        final transparencyData = TransparencyData(
          steps: const [],
          totalDurationMs: 1500,
          requestId: 'req-1',
        );

        notifier.state = notifier.state.copyWith(
          transparencyData: transparencyData,
        );

        expect(notifier.state.transparencyData, isNotNull);
        expect(notifier.state.transparencyData?.requestId, equals('req-1'));
      });

      test('should clear transparency data', () {
        final transparencyData = TransparencyData(
          steps: const [],
          totalDurationMs: 1000,
          requestId: 'req-2',
        );

        notifier.state = notifier.state.copyWith(
          transparencyData: transparencyData,
        );

        expect(notifier.state.transparencyData, isNotNull);

        notifier.state = notifier.state.copyWith(clearTransparency: true);

        expect(notifier.state.transparencyData, isNull);
      });
    });

    group('Resource Cleanup', () {
      test('should have dispose method', () {
        // Just verify the method exists - tearDown handles actual cleanup
        expect(() => notifier.dispose, isNotNull);
      });
    });

    group('Conversation Management', () {
      test('should update conversation ID', () {
        notifier.state = notifier.state.copyWith(
          conversationId: 'conv-123',
        );

        expect(notifier.state.conversationId, equals('conv-123'));
      });

      test('should clear conversation ID', () {
        notifier.state = notifier.state.copyWith(
          conversationId: 'conv-123',
        );

        expect(notifier.state.conversationId, equals('conv-123'));

        // Clear conversation
        notifier.state = notifier.state.copyWith(
          clearConversation: true,
        );

        expect(notifier.state.conversationId, isNull);
      });
    });

    group('Token Usage Tracking', () {
      test('should track token usage', () {
        notifier.state = notifier.state.copyWith(
          lastPromptTokens: 100,
          lastCompletionTokens: 200,
          lastTotalTokens: 300,
        );

        expect(notifier.state.lastPromptTokens, equals(100));
        expect(notifier.state.lastCompletionTokens, equals(200));
        expect(notifier.state.lastTotalTokens, equals(300));
      });

      test('should track daily token limits', () {
        notifier.state = notifier.state.copyWith(
          dailyTokens: 10000,
          dailyTokenLimit: 50000,
          dailyCostMicroUsd: 500,
        );

        expect(notifier.state.dailyTokens, equals(10000));
        expect(notifier.state.dailyTokenLimit, equals(50000));
        expect(notifier.state.dailyCostMicroUsd, equals(500));
      });
    });

    group('Error Handling', () {
      test('should set error with retryable flag', () {
        notifier.state = notifier.state.copyWith(
          error: 'Network timeout',
          errorCode: 'TIMEOUT',
          isErrorRetryable: true,
        );

        expect(notifier.state.error, equals('Network timeout'));
        expect(notifier.state.errorCode, equals('TIMEOUT'));
        expect(notifier.state.isErrorRetryable, isTrue);
      });

      test('should clear error state', () {
        notifier.state = notifier.state.copyWith(
          error: 'Some error',
        );

        expect(notifier.state.error, isNotNull);

        // Clear error
        notifier.state = notifier.state.copyWith(clearError: true);

        expect(notifier.state.error, isNull);
      });
    });

    group('Reconnection', () {
      test('should have reconnect method', () {
        // Verify method exists - don't call it as it has side effects
        expect(() => notifier.reconnect, isNotNull);
      });

      test('should have warmUpConnection method', () {
        // Verify method exists - don't call it as it has side effects
        expect(() => notifier.warmUpConnection, isNotNull);
      });
    });

    group('Streaming Content', () {
      test('should update streaming content', () {
        notifier.state = notifier.state.copyWith(
          streamingContent: 'Partial response...',
        );

        expect(notifier.state.streamingContent, equals('Partial response...'));
      });

      test('should clear streaming content', () {
        notifier.state = notifier.state.copyWith(
          streamingContent: 'Some content',
        );

        expect(notifier.state.streamingContent, isNotEmpty);

        notifier.state = notifier.state.copyWith(
          streamingContent: '',
        );

        expect(notifier.state.streamingContent, isEmpty);
      });
    });

    group('Active Run ID', () {
      test('should track active run ID', () {
        notifier.state = notifier.state.copyWith(
          activeRunId: 'run-123',
        );

        expect(notifier.state.activeRunId, equals('run-123'));
      });

      test('should clear active run ID', () {
        notifier.state = notifier.state.copyWith(
          activeRunId: 'run-123',
        );

        expect(notifier.state.activeRunId, isNotNull);

        notifier.state = notifier.state.copyWith(clearActiveRunId: true);

        expect(notifier.state.activeRunId, isNull);
      });
    });

    group('Step Tracking', () {
      test('should track current step ID', () {
        notifier.state = notifier.state.copyWith(
          currentStepId: 5,
        );

        expect(notifier.state.currentStepId, equals(5));
      });

      test('should track current step index', () {
        notifier.state = notifier.state.copyWith(
          currentStepIndex: 2,
        );

        expect(notifier.state.currentStepIndex, equals(2));
      });
    });

    group('Provider Methods Exist', () {
      test('should have sendMessage method', () {
        // Verify method exists
        expect(() => notifier.sendMessage, isNotNull);
      });

      test('should have cancelActiveRun method', () {
        // Verify method exists
        expect(() => notifier.cancelActiveRun, isNotNull);
      });
    });
  });
}
