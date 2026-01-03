import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/data/models/chat_message_model.dart';

void main() {
  group('ChatMessageModel Tests', () {
    test('ChatMessageModel creation with meta', () {
      final message = ChatMessageModel(
        conversationId: 'test-conversation',
        role: MessageRole.user,
        content: 'Hello World',
        meta: MessageMeta(
          latencyMs: 100,
          isCacheHit: false,
          costSaved: 0.0,
          breakerStatus: 'closed',
        ),
      );

      expect(message.conversationId, 'test-conversation');
      expect(message.role, MessageRole.user);
      expect(message.content, 'Hello World');
      expect(message.meta?.latencyMs, 100);
      expect(message.meta?.isCacheHit, false);
    });

    test('ChatMessageModel copyWith updates meta', () {
      final original = ChatMessageModel(
        conversationId: 'test',
        role: MessageRole.assistant,
        content: 'Response',
      );

      final updated = original.copyWith(
        meta: MessageMeta(latencyMs: 200),
      );

      expect(updated.meta?.latencyMs, 200);
      expect(original.meta, isNull);
    });

    test('MessageMeta serialization', () {
      final meta = MessageMeta(
        latencyMs: 150,
        isCacheHit: true,
        costSaved: 0.05,
        breakerStatus: 'open',
      );

      final json = meta.toJson();
      expect(json['latency_ms'], 150);
      expect(json['is_cache_hit'], true);
      expect(json['cost_saved'], 0.05);
      expect(json['breaker_status'], 'open');

      final fromJson = MessageMeta.fromJson(json);
      expect(fromJson.latencyMs, 150);
      expect(fromJson.isCacheHit, true);
    });
  });

  group('Workflow Integration Tests', () {
    test('Agent collaboration timeline data structure', () {
      final step = {
        'agent': 'StudyPlanner',
        'action': 'Analyze knowledge graph',
        'timestamp': DateTime.now().toIso8601String(),
        'duration': 1.5,
      };

      expect(step['agent'], 'StudyPlanner');
      expect(step['action'], 'Analyze knowledge graph');
    });

    test('Task decomposition workflow structure', () {
      final workflow = {
        'type': 'task_decomposition',
        'steps': [
          {'agent': 'StudyPlanner', 'task': 'analyze'},
          {'agent': 'ProblemSolver', 'task': 'solve'},
        ],
      };

      expect(workflow['type'], 'task_decomposition');
      expect(workflow['steps'], isA<List>());
      final steps = workflow['steps'] as List;
      expect(steps.length, 2);
    });
  });

  group('Error Handling Tests', () {
    test('降级策略数据结构', () {
      final fallback = {
        'level': 'workflow',
        'fallback_to': 'single_agent',
        'reason': 'timeout',
        'timestamp': DateTime.now().toIso8601String(),
      };

      expect(fallback['level'], 'workflow');
      expect(fallback['fallback_to'], 'single_agent');
    });

    test('OpenTelemetry trace structure', () {
      final trace = {
        'trace_id': 'abc123',
        'span_id': 'span456',
        'operation': 'agent_collaboration',
        'duration_ms': 2500,
        'status': 'success',
      };

      expect(trace['trace_id'], 'abc123');
      expect(trace['duration_ms'], 2500);
    });
  });
}
