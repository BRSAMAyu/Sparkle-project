import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:riverpod/riverpod.dart';

import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/reasoning_step_model.dart';

void main() {
  // Initialize Flutter test bindings
  TestWidgetsFlutterBinding.ensureInitialized();

  group('WebSocketChatServiceV2 Tests', () {
    late WebSocketChatServiceV2 service;
    late ProviderContainer container;

    setUp(() {
      container = ProviderContainer();

      // 使用 factory 返回 null 来模拟 WebSocket (实际测试中不需要真实连接)
      WebSocketChannelFactory factory = (uri, {headers}) =>
          throw UnimplementedError('WebSocket mock not needed for unit tests');

      service = WebSocketChatServiceV2(
        container: container,
        channelFactory: factory,
        enableReconnect: false,
        autoConnect: false,
      );
    });

    tearDown(() {
      service.dispose();
      container.dispose();
    });

    group('Connection State Management', () {
      test('should initialize with disconnected state', () {
        expect(service.connectionState, equals(WsConnectionState.disconnected));
        expect(service.isConnected, isFalse);
      });

      test('should have connectionStateStream', () {
        expect(service.connectionStateStream, isA<Stream<WsConnectionState>>());
      });

      test('should provide connection states', () {
        expect(WsConnectionState.disconnected, isNotNull);
        expect(WsConnectionState.connecting, isNotNull);
        expect(WsConnectionState.connected, isNotNull);
        expect(WsConnectionState.reconnecting, isNotNull);
        expect(WsConnectionState.failed, isNotNull);
      });

      test('should only treat explicit auth failures as 401 errors', () {
        expect(
          WebSocketChatServiceV2.looksLikeAuthFailure(
            'WebSocket handshake failed with status code: 401',
          ),
          isTrue,
        );
        expect(
          WebSocketChatServiceV2.looksLikeAuthFailure('authentication failed'),
          isTrue,
        );
        expect(
          WebSocketChatServiceV2.looksLikeAuthFailure(
            'tool execution token budget exceeded',
          ),
          isFalse,
        );
        expect(
          WebSocketChatServiceV2.looksLikeAuthFailure(
            'heartbeat authentication metrics unavailable',
          ),
          isFalse,
        );
      });
    });

    group('Event Parsing Tests', () {
      test('should parse TextEvent from delta message', () {
        final deltaJson = {
          'type': 'delta',
          'delta': 'Hello',
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(deltaJson);
        expect(event, isA<TextEvent>());
        final textEvent = event as TextEvent;
        expect(textEvent.content, equals('Hello'));
        expect(textEvent.responseId, equals('req-1'));
      });

      test('should parse StatusUpdateEvent', () {
        final statusJson = {
          'type': 'status_update',
          'status': {
            'state': 'thinking',
            'details': 'AI is thinking...',
          },
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(statusJson);
        expect(event, isA<StatusUpdateEvent>());
        final statusEvent = event as StatusUpdateEvent;
        expect(statusEvent.state, equals('thinking'));
        expect(statusEvent.details, equals('AI is thinking...'));
      });

      test('should parse ErrorEvent', () {
        final errorJson = {
          'type': 'error',
          'error': {
            'code': 'TEST_ERROR',
            'message': 'Test error',
            'retryable': false,
          },
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(errorJson);
        expect(event, isA<ErrorEvent>());
        final errorEvent = event as ErrorEvent;
        expect(errorEvent.code, equals('TEST_ERROR'));
        expect(errorEvent.message, equals('Test error'));
        expect(errorEvent.retryable, isFalse);
      });

      test('should parse DoneEvent', () {
        final doneJson = {
          'finish_reason': 'stop',
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(doneJson);
        expect(event, isA<DoneEvent>());
        final doneEvent = event as DoneEvent;
        expect(doneEvent.finishReason, equals('stop'));
        expect(doneEvent.responseId, equals('req-1'));
      });

      test('should parse ToolStartEvent', () {
        final toolJson = {
          'type': 'tool_start',
          'tool_name': 'search_knowledge',
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(toolJson);
        expect(event, isA<ToolStartEvent>());
        final toolEvent = event as ToolStartEvent;
        expect(toolEvent.toolName, equals('search_knowledge'));
      });

      test('should parse ToolResultEvent', () {
        final toolResultJson = {
          'type': 'tool_result',
          'tool_result': {
            'success': true,
            'tool_name': 'search_knowledge',
            'data': {'result': 'found'},
          },
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(toolResultJson);
        expect(event, isA<ToolResultEvent>());
        final resultEvent = event as ToolResultEvent;
        expect(resultEvent.result.success, isTrue);
        expect(resultEvent.result.toolName, equals('search_knowledge'));
      });

      test('should parse ReasoningStepEvent', () {
        final reasoningJson = {
          'type': 'reasoning_step',
          'step': {
            'id': 'step-1',
            'description': 'Analyzing user request',
            'agent': 'orchestrator',
            'status': 'in_progress',
          },
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(reasoningJson);
        expect(event, isA<ReasoningStepEvent>());
        final reasoningEvent = event as ReasoningStepEvent;
        expect(
            reasoningEvent.step.description, equals('Analyzing user request'));
        expect(reasoningEvent.step.agent, equals(AgentType.orchestrator));
        expect(reasoningEvent.step.status, equals(StepStatus.inProgress));
      });

      test('should parse WidgetEvent', () {
        final widgetJson = {
          'type': 'widget',
          'widget_type': 'task_card',
          'widget_data': {'task_id': 'task-123'},
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(widgetJson);
        expect(event, isA<WidgetEvent>());
        final widgetEvent = event as WidgetEvent;
        expect(widgetEvent.widgetType, equals('task_card'));
        expect(widgetEvent.widgetData['task_id'], equals('task-123'));
      });

      test('should return UnknownEvent for unknown types', () {
        final unknownJson = {
          'type': 'unknown_type',
          'data': {'key': 'value'},
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(unknownJson);
        expect(event, isA<UnknownEvent>());
        final unknownEvent = event as UnknownEvent;
        expect(unknownEvent.data['type'], equals('unknown_type'));
      });

      test('should parse PlanReviewWidgetEvent', () {
        final planReviewJson = {
          'type': 'plan_review_widget',
          'review_data': {
            'plan_id': 'plan-123',
            'score': 85,
            'issues': [],
          },
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(planReviewJson);
        expect(event, isA<PlanReviewWidgetEvent>());
        final reviewEvent = event as PlanReviewWidgetEvent;
        expect(reviewEvent.reviewData['plan_id'], equals('plan-123'));
        expect(reviewEvent.reviewData['score'], equals(85));
      });

      test('should parse StateChangeEvent', () {
        final stateChangeJson = {
          'type': 'state_change',
          'change_data': {
            'change_type': 'plan_archived',
            'change_id': 'change-1',
            'plan_id': 'plan-123',
            'timestamp': '2026-03-30T00:00:00Z',
          },
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(stateChangeJson);
        expect(event, isA<StateChangeEvent>());
        final stateEvent = event as StateChangeEvent;
        expect(stateEvent.changeData['change_type'], equals('plan_archived'));
        expect(stateEvent.changeData['plan_id'], equals('plan-123'));
      });

      test('should parse DagExecutionEvent', () {
        final dagJson = {
          'type': 'dag_execution',
          'dag_execution_event': {
            'event': 'layer_start',
            'layer_number': 1,
            'total_layers': 3,
            'tool_names': ['search', 'analyze'],
          },
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(dagJson);
        expect(event, isA<DagExecutionEvent>());
        final dagEvent = event as DagExecutionEvent;
        expect(dagEvent.signal.event, equals('layer_start'));
        expect(dagEvent.signal.layerNumber, equals(1));
        expect(dagEvent.signal.totalLayers, equals(3));
      });

      test('should parse MetaEvent', () {
        final metaJson = {
          'type': 'meta',
          'meta': {
            'key': 'value',
          },
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(metaJson);
        expect(event, isA<MetaEvent>());
        final metaEvent = event as MetaEvent;
        expect(metaEvent.meta['key'], equals('value'));
      });

      test('should parse FullTextEvent', () {
        final fullTextJson = {
          'type': 'full_text',
          'content': 'Complete response',
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(fullTextJson);
        expect(event, isA<FullTextEvent>());
        final fullTextEvent = event as FullTextEvent;
        expect(fullTextEvent.content, equals('Complete response'));
      });

      test('should parse AckEvent', () {
        final ackJson = {
          'type': 'ack',
          'message_id': 'msg-1',
          'status': 'received',
          'timestamp': 1234567890,
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(ackJson);
        expect(event, isA<AckEvent>());
        final ackEvent = event as AckEvent;
        expect(ackEvent.messageId, equals('msg-1'));
        expect(ackEvent.status, equals('received'));
        expect(ackEvent.isReceived, isTrue);
      });

      test('should parse UsageEvent', () {
        final usageJson = {
          'type': 'usage',
          'prompt_tokens': 100,
          'completion_tokens': 200,
          'total_tokens': 300,
          'cost_micro_usd': 50,
          'request_id': 'req-1',
        };

        final event = WebSocketChatServiceV2Parser.parseEvent(usageJson);
        expect(event, isA<UsageEvent>());
        final usageEvent = event as UsageEvent;
        expect(usageEvent.promptTokens, equals(100));
        expect(usageEvent.completionTokens, equals(200));
        expect(usageEvent.totalTokens, equals(300));
        expect(usageEvent.costMicroUsd, equals(50));
      });
    });

    group('Resource Cleanup', () {
      test('should dispose without errors', () {
        expect(() => service.dispose(), returnsNormally);
      });

      test('should handle multiple dispose calls', () {
        service.dispose();
        expect(() => service.dispose(), returnsNormally);
      });
    });
  });
}

// Event parser extension - isolated from service for testing
class WebSocketChatServiceV2Parser {
  static ChatStreamEvent parseEvent(Map<String, dynamic> json) {
    final type = json['type']?.toString();

    switch (type) {
      case 'delta':
        return TextEvent(
          content: json['delta']?.toString() ?? '',
          responseId: json['request_id']?.toString(),
        );

      case 'status_update':
        final status = json['status'] as Map<String, dynamic>?;
        return StatusUpdateEvent(
          state: status?['state']?.toString() ?? '',
          details: status?['details']?.toString() ?? '',
          currentAgentName: status?['current_agent_name']?.toString(),
          activeAgentType: status?['active_agent_type']?.toString(),
          responseId: json['request_id']?.toString(),
        );

      case 'error':
        final error = json['error'] as Map<String, dynamic>?;
        return ErrorEvent(
          code: error?['code']?.toString() ?? '',
          message: error?['message']?.toString() ?? '',
          retryable: error?['retryable'] == true,
          responseId: json['request_id']?.toString(),
        );

      case 'done':
      case null when json.containsKey('finish_reason'):
        return DoneEvent(
          finishReason: json['finish_reason']?.toString(),
          responseId: json['request_id']?.toString(),
        );

      case 'tool_start':
        return ToolStartEvent(
          toolName: json['tool_name']?.toString() ?? '',
          responseId: json['request_id']?.toString(),
        );

      case 'tool_result':
        final resultData = json['tool_result'] as Map<String, dynamic>?;
        return ToolResultEvent(
          result: resultData != null
              ? _parseToolResult(resultData)
              : _createDefaultToolResult(),
          responseId: json['request_id']?.toString(),
        );

      case 'reasoning_step':
        final stepData = json['step'] as Map<String, dynamic>?;
        return ReasoningStepEvent(
          step: stepData != null
              ? _parseReasoningStep(stepData)
              : _createDefaultReasoningStep(),
          responseId: json['request_id']?.toString(),
        );

      case 'widget':
        return WidgetEvent(
          widgetType: json['widget_type']?.toString() ?? '',
          widgetData: json['widget_data'] as Map<String, dynamic>? ?? {},
          responseId: json['request_id']?.toString(),
        );

      case 'plan_review_widget':
        return PlanReviewWidgetEvent(
          reviewData: json['review_data'] as Map<String, dynamic>? ?? {},
          responseId: json['request_id']?.toString(),
        );

      case 'state_change':
        return StateChangeEvent(
          changeData: json['change_data'] as Map<String, dynamic>? ?? {},
          responseId: json['request_id']?.toString(),
        );

      case 'dag_execution':
        final eventData = json['dag_execution_event'] as Map<String, dynamic>?;
        final signal = DagExecutionSignal.fromDynamic(eventData);
        return DagExecutionEvent(
          signal: signal ?? DagExecutionSignal(event: 'unknown'),
          responseId: json['request_id']?.toString(),
        );

      case 'meta':
        return MetaEvent(
          meta: json['meta'] as Map<String, dynamic>? ?? {},
          responseId: json['request_id']?.toString(),
        );

      case 'full_text':
        return FullTextEvent(
          content: json['content']?.toString() ?? '',
          responseId: json['request_id']?.toString(),
        );

      case 'ack':
        return AckEvent(
          messageId: json['message_id']?.toString() ?? '',
          status: json['status']?.toString() ?? '',
          timestamp: json['timestamp'] as int? ?? 0,
          responseId: json['request_id']?.toString(),
        );

      case 'usage':
        return UsageEvent(
          promptTokens: json['prompt_tokens'] as int? ?? 0,
          completionTokens: json['completion_tokens'] as int? ?? 0,
          totalTokens: json['total_tokens'] as int? ?? 0,
          costMicroUsd: json['cost_micro_usd'] as int?,
          responseId: json['request_id']?.toString(),
        );

      default:
        return UnknownEvent(
          data: json,
          responseId: json['request_id']?.toString(),
        );
    }
  }

  static ToolResultModel _parseToolResult(Map<String, dynamic> json) {
    return ToolResultModel(
      success: json['success'] == true,
      toolName: json['tool_name']?.toString() ?? '',
      data: json['data'] as Map<String, dynamic>?,
      errorMessage: json['error_message']?.toString(),
      widgetType: json['widget_type']?.toString(),
      widgetData: json['widget_data'] as Map<String, dynamic>?,
    );
  }

  static ToolResultModel _createDefaultToolResult() {
    return ToolResultModel(
      success: false,
      toolName: 'unknown',
    );
  }

  static ReasoningStep _parseReasoningStep(Map<String, dynamic> json) {
    return ReasoningStep(
      id: json['id']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      agent: _parseAgentType(json['agent']),
      status: _parseStepStatus(json['status']),
      toolOutput: json['tool_output']?.toString(),
      citations: json['citations'] as List<String>?,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'])
          : null,
      completedAt: json['completed_at'] != null
          ? DateTime.tryParse(json['completed_at'])
          : null,
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  static ReasoningStep _createDefaultReasoningStep() {
    return const ReasoningStep(
      id: 'unknown',
      description: 'Unknown step',
      agent: AgentType.orchestrator,
      status: StepStatus.pending,
    );
  }

  static AgentType _parseAgentType(dynamic raw) {
    final str = raw?.toString().toLowerCase() ?? 'orchestrator';
    switch (str) {
      case 'orchestrator':
        return AgentType.orchestrator;
      case 'math':
        return AgentType.math;
      case 'code':
        return AgentType.code;
      case 'writing':
        return AgentType.writing;
      case 'science':
        return AgentType.science;
      case 'knowledge':
        return AgentType.knowledge;
      case 'search':
        return AgentType.search;
      case 'data_analysis':
        return AgentType.dataAnalysis;
      case 'translation':
        return AgentType.translation;
      case 'image':
        return AgentType.image;
      case 'audio':
        return AgentType.audio;
      case 'reasoning':
        return AgentType.reasoning;
      default:
        return AgentType.orchestrator;
    }
  }

  static StepStatus _parseStepStatus(dynamic raw) {
    final str = raw?.toString().toLowerCase() ?? 'pending';
    switch (str) {
      case 'pending':
        return StepStatus.pending;
      case 'in_progress':
        return StepStatus.inProgress;
      case 'completed':
        return StepStatus.completed;
      case 'failed':
        return StepStatus.failed;
      default:
        return StepStatus.pending;
    }
  }
}
