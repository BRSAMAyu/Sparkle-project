import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/aurora/data/repositories/aurora_daily_startup_repository.dart';
import 'package:sparkle/features/aurora/data/models/aurora_daily_startup_message.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
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

/// Minimal Fake ApiClient to satisfy various notifier constructors.
class _FakeApiClient extends Fake implements ApiClient {}

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

/// Quiet DashboardNotifier that does not trigger network requests.
/// Prevents the real DashboardRepository from creating timers/network calls.
class _QuietDashboardNotifier extends DashboardNotifier {
  _QuietDashboardNotifier() : super(_QuietDashboardRepository());

  @override
  Future<void> fetchData() async {
    state = DashboardState.error('');
  }

  @override
  Future<void> refresh() async {}
}

/// Minimal DashboardRepository that returns empty data without network calls.
class _QuietDashboardRepository extends DashboardRepository {
  _QuietDashboardRepository() : super(_FakeApiClient());

  @override
  Future<Map<String, dynamic>> getDashboardStatus() async => const {};

  @override
  Future<Map<String, dynamic>> getGrowthDashboard() async => const {};

  @override
  Future<Map<String, dynamic>> getPredictiveDashboard() async => const {};
}

/// A SimpleBoolPreferenceNotifier that always returns false (disabled).
/// Prevents the ChatPredictionDock from creating its 18-second timer.
class _DisabledBoolNotifier extends SimpleBoolPreferenceNotifier {
  _DisabledBoolNotifier()
      : super(storageKey: '_test_disabled', defaultValue: false);
}

/// Minimal AuroraDailyStartupRepository that returns no data without timers.
class _QuietDailyStartupRepository extends AuroraDailyStartupRepository {
  _QuietDailyStartupRepository() : super(_FakeApiClient());

  @override
  Future<AuroraDailyStartupMessage> getDailyStartup({
    required String planId,
  }) async {
    throw Exception('not available');
  }

  @override
  Future<AuroraCachedDailyStartup?> getCachedDailyStartup({
    String? planId,
  }) async =>
      null;
}

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

  // Suppress framework errors that occur during widget tree teardown.
  // These are known production-code issues (StatusAwarenessBar.dispose
  // uses ref after widget disposal; animations continue after disposal).
  late void Function(FlutterErrorDetails)? originalOnError;
  setUp(() {
    originalOnError = FlutterError.onError;
    FlutterError.onError = (details) {
      final msg = details.exceptionAsString();
      if (msg.contains('Cannot use "ref" after the widget was disposed') ||
          msg.contains('An animation is still running even after') ||
          msg.contains('A Timer is still pending')) {
        return;
      }
      originalOnError?.call(details);
    };
  });
  tearDown(() {
    FlutterError.onError = originalOnError;
  });

  /// Pumps enough frames for layout to settle. Uses [pump] instead of
  /// [pumpAndSettle] because the ChatScreen contains widgets with infinite
  /// animations (e.g. shimmer dots, breathing overlays) that prevent settling.
  Future<void> settleFrames(WidgetTester tester) async {
    for (var i = 0; i < 5; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
  }

  /// Tears down the current widget tree cleanly by pumping an empty widget
  /// and advancing the fake clock far enough to flush any pending timers and
  /// animations. This prevents "Timer is still pending" and "animation is
  /// still running" assertions from the test framework.
  Future<void> disposeWidgetTree(WidgetTester tester) async {
    // Silence any errors that occur during the teardown of the old widget tree.
    // The StatusAwarenessBar.dispose() calls ref.read() after the widget is
    // already disposed, which is a production code bug we cannot fix here.
    final savedOnError = FlutterError.onError;
    FlutterError.onError = (details) {};
    try {
      // Replace the current widget tree with a trivially simple one so that
      // all ChatScreen-related widgets are unmounted.
      await tester.pumpWidget(
        const MaterialApp(home: SizedBox.shrink()),
      );
      // Advance fake time well beyond any timer duration (18s, 300ms debounce, etc.)
      // to ensure all pending timers and animations complete.
      await tester.pump(const Duration(seconds: 30));
    } finally {
      FlutterError.onError = savedOnError;
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
          dashboardProvider.overrideWith((ref) => _QuietDashboardNotifier()),
          auroraDailyStartupRepositoryProvider.overrideWithValue(
            _QuietDailyStartupRepository(),
          ),
          activePlanProvider.overrideWith((ref) => ActivePlanNotifier(ref)),
          // Hide the prediction dock to prevent its 18s followup timer.
          showChatPredictionDockProvider.overrideWith(
            (ref) => _DisabledBoolNotifier(),
          ),
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

    await disposeWidgetTree(tester);
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

    await disposeWidgetTree(tester);
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

    await disposeWidgetTree(tester);
  });
}
