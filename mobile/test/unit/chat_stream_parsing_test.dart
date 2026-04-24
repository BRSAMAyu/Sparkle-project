import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';

void main() {
  group('parseChatEventForTest', () {
    test('parses delta events into TextEvent', () {
      final event = parseChatEventForTest(
        json.encode({
          'type': 'delta',
          'delta': 'hello',
          'response_id': 'r1',
        }),
      );

      expect(event, isA<TextEvent>());
      expect((event as TextEvent).content, 'hello');
      expect(event.responseId, 'r1');
    });

    test('parses status update envelope into StatusUpdateEvent', () {
      final event = parseChatEventForTest(
        json.encode({
          'type': 'status_update',
          'status': {
            'state': 'THINKING',
            'details': 'planning next step',
          },
        }),
      );

      expect(event, isA<StatusUpdateEvent>());
      expect((event as StatusUpdateEvent).state, 'THINKING');
      expect(event.details, 'planning next step');
    });

    test('treats CONTINUE finish_reason frames as ContinueEvent', () {
      final event = parseChatEventForTest(
        json.encode({
          'type': 'done',
          'finish_reason': 'CONTINUE',
          'metadata': {
            'aurora_surface': 'modeling',
            'aurora_runtime_enabled': true,
          },
        }),
      );

      expect(event, isA<ContinueEvent>());
      final continueEvent = event as ContinueEvent;
      expect(continueEvent.finishReason, 'CONTINUE');
      expect(continueEvent.metadata?['aurora_surface'], 'modeling');
    });

    test('treats finish_reason frames as DoneEvent', () {
      final event = parseChatEventForTest(
        json.encode({
          'type': 'done',
          'finish_reason': 'STOP',
        }),
      );

      expect(event, isA<DoneEvent>());
      expect((event as DoneEvent).finishReason, 'STOP');
    });

    test('parses nested error payloads into ErrorEvent', () {
      final event = parseChatEventForTest(
        json.encode({
          'type': 'error',
          'error': {
            'error_code': 'TIMEOUT',
            'message': 'upstream timeout',
            'retryable': true,
          },
        }),
      );

      expect(event, isA<ErrorEvent>());
      final error = event as ErrorEvent;
      expect(error.code, 'TIMEOUT');
      expect(error.message, 'upstream timeout');
      expect(error.retryable, isTrue);
    });

    test('parses tool_call frames into ToolStartEvent', () {
      final event = parseChatEventForTest(
        json.encode({
          'type': 'tool_call',
          'tool_call': {'name': 'search'},
        }),
      );

      expect(event, isA<ToolStartEvent>());
      expect((event as ToolStartEvent).toolName, 'search');
    });

    test('returns parse error event for invalid json', () {
      final event = parseChatEventForTest('{not valid}');

      expect(event, isA<ErrorEvent>());
      final error = event as ErrorEvent;
      expect(error.code, 'PARSE_ERROR');
      expect(error.retryable, isFalse);
    });

    test('parses dag execution metadata into DagExecutionEvent', () {
      final event = parseChatEventForTest(
        json.encode({
          'type': 'delta',
          'delta': '',
          'metadata': {
            'dag_execution_event': {
              'event': 'layer_start',
              'layer_number': 1,
              'total_layers': 3,
              'tool_names': ['search', 'summarize'],
            },
          },
        }),
      );

      expect(event, isA<DagExecutionEvent>());
      final dag = event as DagExecutionEvent;
      expect(dag.signal.event, 'layer_start');
      expect(dag.signal.layerNumber, 1);
      expect(dag.signal.totalLayers, 3);
    });

    test('parses review metadata into PlanReviewWidgetEvent', () {
      final event = parseChatEventForTest(
        json.encode({
          'type': 'delta',
          'delta': '',
          'metadata': {
            'requires_review': true,
            'review_data': {
              'plan_id': 'plan-1',
              'summary': 'Need confirmation',
            },
          },
        }),
      );

      expect(event, isA<PlanReviewWidgetEvent>());
      final review = event as PlanReviewWidgetEvent;
      expect(review.reviewData['plan_id'], 'plan-1');
      expect(review.reviewData['summary'], 'Need confirmation');
    });
  });
}
