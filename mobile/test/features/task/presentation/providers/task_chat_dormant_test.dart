import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_chat_provider.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('TaskChatState', () {
    test('should start with default values', () {
      final state = TaskChatState();

      expect(state.isLoading, isFalse);
      expect(state.messages, isEmpty);
      expect(state.error, isNull);
      expect(state.dormantInjection, isNull);
      expect(state.turnCount, equals(0));
    });

    test('should copy with loading state', () {
      final state = TaskChatState().copyWith(isLoading: true);

      expect(state.isLoading, isTrue);
      expect(state.messages, isEmpty);
    });

    test('should copy with error and clear error', () {
      var state = TaskChatState().copyWith(error: 'network error');
      expect(state.error, equals('network error'));

      state = state.copyWith(clearError: true);
      expect(state.error, isNull);
    });

    test('should increment turn count', () {
      final state = TaskChatState().copyWith(turnCount: 3);

      expect(state.turnCount, equals(3));
    });
  });

  group('DormantInjectionState', () {
    test('should start with default cold-start values', () {
      final state = DormantInjectionState();

      expect(state.hasInjection, isFalse);
      expect(state.injectionItems, isEmpty);
      expect(state.uxIntent, equals('routine'));
      expect(state.auroraPresence, equals('ambient'));
    });

    test('should copy with injection data', () {
      final items = [
        DormantInjectionItem(
          kind: 'focus_contract_summary',
          available: true,
          payload: {'focus_description': 'Study math'},
        ),
      ];

      final state = DormantInjectionState().copyWith(
        hasInjection: true,
        injectionItems: items,
      );

      expect(state.hasInjection, isTrue);
      expect(state.injectionItems, hasLength(1));
      expect(state.injectionItems.first.kind, equals('focus_contract_summary'));
      expect(state.injectionItems.first.available, isTrue);
    });

    test('cold-start items are unavailable by default', () {
      final item = DormantInjectionItem(
        kind: 'task_guidance_ai_or_fallback',
        available: false,
      );

      expect(item.available, isFalse);
      expect(item.payload, isNull);
    });
  });

  group('TaskChatState with dormant injection', () {
    test('should preserve dormant injection across state updates', () {
      final injection = DormantInjectionState(
        hasInjection: true,
        injectionItems: [
          DormantInjectionItem(
            kind: 'focus_contract_summary',
            available: true,
            payload: {'focus_description': 'test'},
          ),
        ],
      );

      var state = TaskChatState(dormantInjection: injection);
      state = state.copyWith(isLoading: true);

      expect(state.dormantInjection, isNotNull);
      expect(state.dormantInjection!.hasInjection, isTrue);
      expect(state.isLoading, isTrue);
    });

    test('should preserve turn count with dormant injection', () {
      final injection = DormantInjectionState(hasInjection: true);
      final state = TaskChatState(
        dormantInjection: injection,
        turnCount: 5,
      );

      expect(state.turnCount, equals(5));
      expect(state.dormantInjection!.hasInjection, isTrue);
    });
  });

  // -------------------------------------------------------------------
  // E2E parsing test: proves chip lights up from real backend response
  // -------------------------------------------------------------------

  group('parseDormantMeta — end-to-end metadata parsing', () {
    late TaskChatNotifier notifier;

    setUp(() {
      // Create a notifier with a no-op repository (not used in parse tests)
      // We only test the public parseDormantMeta method directly.
    });

    test('returns null when metadata is null', () {
      final notifier = _FakeTaskChatNotifier();
      final result = notifier.parseDormantMeta(null);
      expect(result, isNull);
    });

    test('returns null when metadata has no injection items or ux_intent', () {
      final notifier = _FakeTaskChatNotifier();
      final result = notifier.parseDormantMeta({'foo': 'bar'});
      expect(result, isNull);
    });

    test('parses a real backend dormant_injection payload', () {
      final notifier = _FakeTaskChatNotifier();

      // This is the exact shape the backend returns in the
      // dormant_injection field of ChatResponse
      final backendPayload = <String, dynamic>{
        'task_id': 'a1b2c3d4-0000-0000-0000-000000000001',
        'user_id': 'a1b2c3d4-0000-0000-0000-000000000002',
        'items': [
          {
            'kind': 'focus_contract_summary',
            'available': true,
            'payload': {
              'focus_description': 'Pass calculus exam',
              'active_node': 'derivatives',
            },
            'source_ref': 'FocusContract:abc-123',
          },
          {
            'kind': 'task_guidance_ai_or_fallback',
            'available': false,
            'payload': null,
            'source_ref': null,
          },
          {
            'kind': 'latest_tdr_intent_presence',
            'available': true,
            'payload': {
              'ux_intent': 'routine',
              'aurora_presence': 'ambient',
            },
            'source_ref': 'TDR:def-456',
          },
          {
            'kind': 'projection_allowed_insight_claim',
            'available': false,
            'payload': null,
            'source_ref': null,
          },
          {
            'kind': 'recent_probe_outcome',
            'available': false,
            'payload': null,
            'source_ref': null,
          },
        ],
        'ux_intent': 'routine',
        'aurora_presence': 'ambient',
        'generated_by': 'dormant_injector_v1',
      };

      final result = notifier.parseDormantMeta(backendPayload);

      // Verify the chip would light up
      expect(result, isNotNull);
      expect(result!.hasInjection, isTrue);
      expect(result.uxIntent, equals('routine'));
      expect(result.auroraPresence, equals('ambient'));

      // Verify 5 items parsed
      expect(result.injectionItems, hasLength(5));

      // Verify specific items
      final fcItem = result.injectionItems.firstWhere(
        (i) => i.kind == 'focus_contract_summary',
      );
      expect(fcItem.available, isTrue);
      expect(fcItem.payload?['focus_description'], equals('Pass calculus exam'));

      final tgItem = result.injectionItems.firstWhere(
        (i) => i.kind == 'task_guidance_ai_or_fallback',
      );
      expect(tgItem.available, isFalse);

      final tdrItem = result.injectionItems.firstWhere(
        (i) => i.kind == 'latest_tdr_intent_presence',
      );
      expect(tdrItem.available, isTrue);
      expect(tdrItem.payload?['ux_intent'], equals('routine'));
    });

    test('cold-start (no items, only ux_intent) still produces injection', () {
      final notifier = _FakeTaskChatNotifier();
      final backendPayload = <String, dynamic>{
        'ux_intent': 'routine',
        'aurora_presence': 'ambient',
      };

      final result = notifier.parseDormantMeta(backendPayload);
      expect(result, isNotNull);
      expect(result!.hasInjection, isTrue);
      expect(result.uxIntent, equals('routine'));
      expect(result.auroraPresence, equals('ambient'));
      expect(result.injectionItems, isEmpty);
    });

    test('state.copyWith with parsed injection preserves it', () {
      final notifier = _FakeTaskChatNotifier();
      final backendPayload = <String, dynamic>{
        'items': [
          {
            'kind': 'focus_contract_summary',
            'available': true,
            'payload': {'focus_description': 'Study'},
          },
        ],
        'ux_intent': 'routine',
        'aurora_presence': 'ambient',
      };

      final dormantState = notifier.parseDormantMeta(backendPayload);
      expect(dormantState, isNotNull);

      // Simulate what sendMessage does after parsing
      final state = TaskChatState(
        isLoading: false,
        dormantInjection: dormantState,
        turnCount: 1,
      );

      // Verify the state has injection — chip would light up
      expect(state.dormantInjection, isNotNull);
      expect(state.dormantInjection!.hasInjection, isTrue);
      expect(state.dormantInjection!.injectionItems, hasLength(1));
    });
  });
}

/// A test-only notifier subclass that doesn't require a real repository.
class _FakeTaskChatNotifier extends TaskChatNotifier {
  _FakeTaskChatNotifier()
      : super(_FakeChatRepository(), 'test-task-id');
}

class _FakeChatRepository implements ChatRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}
