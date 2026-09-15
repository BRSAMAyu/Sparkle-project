import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/aurora/data/models/aurora_comeback_context.dart';
import 'package:sparkle/features/aurora/data/models/aurora_daily_startup_message.dart';
import 'package:sparkle/features/aurora/data/repositories/aurora_daily_startup_repository.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/chat/presentation/screens/chat_screen.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _QuietDashboardRepository extends DashboardRepository {
  _QuietDashboardRepository() : super(_NoopApiClient());

  @override
  Future<Map<String, dynamic>> getDashboardStatus() async => const {};

  @override
  Future<Map<String, dynamic>> getGrowthDashboard() async => const {};

  @override
  Future<Map<String, dynamic>> getPredictiveDashboard() async => const {};
}

class _QuietDashboardNotifier extends DashboardNotifier {
  _QuietDashboardNotifier() : super(_QuietDashboardRepository());

  @override
  Future<void> refresh() async {}
}

class _QuietPlanRepository extends PlanRepository {
  _QuietPlanRepository() : super(_NoopApiClient());

  @override
  Future<List<PlanModel>> getPlans({PlanType? type, bool? isActive}) async =>
      const [];

  @override
  Future<List<PlanModel>> getActivePlans() async => const [];
}

class _QuietDailyStartupRepository extends AuroraDailyStartupRepository {
  _QuietDailyStartupRepository() : super(_NoopApiClient());

  @override
  Future<AuroraComebackContext> getComebackContext() async =>
      const AuroraComebackContext.empty();

  @override
  Future<AuroraDailyStartupMessage> getDailyStartup({
    required String planId,
  }) async {
    throw StateError('daily startup disabled for scroll test');
  }
}

// Mock needed dependencies
class _ScrollChatNotifier extends ChatNotifier {
  _ScrollChatNotifier(super.chatRepository, super.ref);

  @override
  Future<void> warmUpConnection() async {}

  void addMessage(ChatMessageModel msg) {
    state = state.copyWith(
      messages: [msg, ...state.messages],
    );
  }
}

class _FakeChatRepository extends Fake implements ChatRepository {
  @override
  Stream<WsConnectionState> get connectionStateStream => const Stream.empty();
  @override
  WsConnectionState get connectionState => WsConnectionState.disconnected;
  @override
  void dispose() {}
  @override
  Future<List<Map<String, dynamic>>> getRecentConversations() async => [];
}

class _QuietAuroraStatusNotifier extends AuroraStatusNotifier {
  _QuietAuroraStatusNotifier() : super(_NoopApiClient());

  @override
  Future<void> refresh({String? conversationId}) async {}

  @override
  void startPeriodicRefresh({String? conversationId}) {}

  @override
  void stopPeriodicRefresh() {}
}

void main() {
  setUp(setUpI18nForTesting);

  testWidgets('ChatScreen scrolls to bottom (0.0) when new message arrives',
      (WidgetTester tester) async {
    // Initialize SharedPreferences and ViewStorageService
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    await ViewStorageService.ensureInitialized();

    final fakeChatRepo = _FakeChatRepository();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(preferences),
          chatProvider.overrideWith(
            (ref) => _ScrollChatNotifier(fakeChatRepo, ref),
          ),
          planRepositoryProvider.overrideWithValue(_QuietPlanRepository()),
          openClawConnectionProvider.overrideWith(
            (ref) => OpenClawConnectionService(),
          ),
          dashboardProvider.overrideWith((ref) => _QuietDashboardNotifier()),
          examSprintDashboardProvider.overrideWith((ref) async => null),
          auroraDailyStartupRepositoryProvider.overrideWithValue(
            _QuietDailyStartupRepository(),
          ),
          auroraStatusProvider.overrideWith(
            (ref) => _QuietAuroraStatusNotifier(),
          ),
        ],
        child: testMaterialApp(home: const ChatScreen()),
      ),
    );

    // Pump several frames to let async initialization settle without using
    // pumpAndSettle, which times out due to periodic timers.
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }

    final chatNotifier = tester.state<ConsumerState>(find.byType(ChatScreen))
        .ref.read(chatProvider.notifier) as _ScrollChatNotifier;

    // Seed one message so the ListView is rendered (not the quick action panel).
    chatNotifier.addMessage(
      ChatMessageModel(
        id: 'seed',
        conversationId: 'test-session',
        content: 'Seed Message',
        role: MessageRole.user,
        createdAt: DateTime.now(),
      ),
    );
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    // Initial check - find ListView
    final listFinder = find.byWidgetPredicate(
      (widget) => widget is ListView && widget.reverse,
      description: 'reversed chat message list',
    );
    expect(listFinder, findsOneWidget);
    final scrollFinder = find.descendant(
      of: listFinder,
      matching: find.byType(Scrollable),
    );
    expect(scrollFinder, findsOneWidget);

    // Add many messages to ensure scrolling is possible
    for (var i = 0; i < 20; i++) {
      chatNotifier.addMessage(
        ChatMessageModel(
          id: 'msg_$i',
          conversationId: 'test-session',
          content: 'Message $i',
          role: MessageRole.assistant,
          createdAt: DateTime.now(),
        ),
      );
    }
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    // Scroll up (visually) -> offset increases
    await tester.drag(listFinder, const Offset(0, 300));
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    // Add new message
    chatNotifier.addMessage(
      ChatMessageModel(
        id: 'new_msg',
        conversationId: 'test-session',
        content: 'New Message',
        role: MessageRole.assistant,
        createdAt: DateTime.now(),
      ),
    );

    // Trigger the listener
    await tester.pump();
    // Wait for animation
    await tester.pump(const Duration(milliseconds: 300));
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    // We expect the scroll position to be back at 0.0
    final scrollableState = tester.state<ScrollableState>(scrollFinder);
    expect(scrollableState.position.pixels, 0.0);
  });
}
