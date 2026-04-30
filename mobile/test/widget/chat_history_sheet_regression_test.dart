import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

/// Inactive Aurora snapshot that prevents the StatusAwarenessBar from
/// rendering its shimmer dots (which have an infinite animation and cause
/// pumpAndSettle to time out).
final _inactiveAuroraSnapshot = AuroraControlSurfaceSnapshot(
  auroraActive: false,
  runtimeEnabled: false,
  overallStatus: 'sensing',
  energyLevel: 'L0',
  summary: '',
  readyCount: 0,
  activeCount: 0,
  totalCount: 4,
  conversationId: null,
  requestedConversationId: null,
  sceneAlignment: 'matched',
  surface: null,
  updatedAt: null,
  facets: const [],
  wakeEligibility: AuroraWakeEligibility(
    canUserWake: false,
    userQuotaRemaining: 0,
    cooldownStatus: 'available',
    cooldownRemainingMin: 0,
    wakeReasons: [],
    recommendedSessionType: 'strategy_recalibration',
    estimatedDurationSec: 240,
    suggestedScope: '',
    fallbackIfUnavailable: 'quick_calibration',
  ),
  predictedReplyOptions: const [],
  fetchedAt: DateTime(2026),
);

class _HistoryFakeRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// Fake AuroraStatusNotifier that immediately provides an inactive snapshot.
/// This avoids the shimmer loading animation that causes pumpAndSettle timeouts.
class _FakeAuroraNotifier extends AuroraStatusNotifier {
  _FakeAuroraNotifier() : super(_FakeApiClient()) {
    state = _inactiveAuroraSnapshot;
  }

  @override
  Future<void> refresh({String? conversationId}) async {}

  @override
  void startPeriodicRefresh({String? conversationId}) {}

  @override
  void stopPeriodicRefresh() {}

  @override
  void dispose() {}
}

/// Minimal Fake ApiClient to satisfy the AuroraStatusNotifier constructor.
class _FakeApiClient extends Fake implements ApiClient {}

class _HistoryChatRepository extends Fake implements ChatRepository {
  _HistoryChatRepository({
    this.recentConversations = const <Map<String, dynamic>>[],
    this.historyBySession = const <String, List<ChatMessageModel>>{},
    this.recentError,
    this.historyErrorBySession = const <String, Object>{},
  });

  final List<Map<String, dynamic>> recentConversations;
  final Map<String, List<ChatMessageModel>> historyBySession;
  final Object? recentError;
  final Map<String, Object> historyErrorBySession;
  final List<String> requestedSessions = <String>[];

  @override
  Stream<WsConnectionState> get connectionStateStream => const Stream.empty();

  @override
  WsConnectionState get connectionState => WsConnectionState.disconnected;

  @override
  Future<List<Map<String, dynamic>>> getRecentConversations() async {
    if (recentError != null) {
      throw recentError!;
    }
    return recentConversations;
  }

  @override
  Future<List<ChatMessageModel>> getConversationHistory(
    String conversationId, {
    int? limit,
    int? offset,
  }) async {
    requestedSessions.add(conversationId);
    final error = historyErrorBySession[conversationId];
    if (error != null) {
      throw error;
    }
    return historyBySession[conversationId] ?? const <ChatMessageModel>[];
  }

  @override
  void dispose() {}
}

class _HistoryChatNotifier extends ChatNotifier {
  _HistoryChatNotifier(super.chatRepository, super.ref);

  @override
  Future<void> warmUpConnection() async {}

  @override
  Future<void> switchPlanSession(String? planId,
      {BuildContext? context}) async {}
}

void main() {

  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
  });

  /// Pumps enough frames for layout to settle. Uses [pump] instead of
  /// [pumpAndSettle] because the ChatScreen contains widgets with infinite
  /// animations (e.g. shimmer dots, breathing overlays) that prevent settling.
  Future<void> settleFrames(WidgetTester tester) async {
    for (var i = 0; i < 5; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
  }

  Future<_HistoryChatNotifier> pumpChat(
    WidgetTester tester, {
    required _HistoryChatRepository repository,
    String? conversationId,
  }) async {
    final notifier = _HistoryChatNotifier(repository, _HistoryFakeRef());
    if (conversationId != null) {
      notifier.state = notifier.state.copyWith(conversationId: conversationId);
    }

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          chatProvider.overrideWith((ref) => notifier),
          auroraStatusProvider.overrideWith((ref) => _FakeAuroraNotifier()),
        ],
        child: testMaterialApp(
          home: const ChatScreen(),
        ),
      ),
    );

    await settleFrames(tester);

    return notifier;
  }

  testWidgets('history sheet shows empty state without freezing',
      (tester) async {
    await pumpChat(
      tester,
      repository: _HistoryChatRepository(recentConversations: const []),
    );

    await tester.tap(find.byIcon(Icons.history));
    await settleFrames(tester);

    expect(find.text('历史对话'), findsOneWidget);
    expect(find.text('暂无历史记录'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('history sheet shows inline error and can refresh',
      (tester) async {
    final repository = _HistoryChatRepository(
      recentError: Exception('network down'),
    );

    await pumpChat(tester, repository: repository);

    await tester.tap(find.byIcon(Icons.history));
    await settleFrames(tester);

    expect(find.textContaining('加载失败'), findsOneWidget);
    expect(find.text('重试'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('history sheet opens another session and closes itself',
      (tester) async {
    final repository = _HistoryChatRepository(
      recentConversations: const <Map<String, dynamic>>[
        {
          'id': 'session-2',
          'title': '上一轮计划讨论',
          'updated_at': '2026-03-29T21:15:00',
        },
      ],
      historyBySession: <String, List<ChatMessageModel>>{
        'session-2': <ChatMessageModel>[
          ChatMessageModel(
            id: 'm-1',
            conversationId: 'session-2',
            content: '历史消息',
            role: MessageRole.assistant,
            createdAt: DateTime(2026, 3, 29, 21, 15),
          ),
        ],
      },
    );

    final notifier = await pumpChat(
      tester,
      repository: repository,
      conversationId: 'session-1',
    );

    await tester.tap(find.byIcon(Icons.history));
    await settleFrames(tester);
    await tester.tap(find.text('上一轮计划讨论'));
    await settleFrames(tester);

    expect(repository.requestedSessions, contains('session-2'));
    expect(repository.requestedSessions.last, 'session-2');
    expect(find.text('历史对话'), findsNothing);
    expect(notifier.state.conversationId, 'session-2');
    expect(notifier.state.messages.map((message) => message.content),
        contains('历史消息'));
    expect(tester.takeException(), isNull);
  });
}
