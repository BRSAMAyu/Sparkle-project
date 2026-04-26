import 'package:dio/dio.dart';
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

class _NoopApiClient implements ApiClient {
  @override
  Dio get dio => Dio();

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) {
    throw UnimplementedError();
  }

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
    throw StateError('daily startup disabled for banner test');
  }
}

class _FakeChatRepository extends Fake implements ChatRepository {
  @override
  Stream<WsConnectionState> get connectionStateStream => const Stream.empty();

  @override
  WsConnectionState get connectionState => WsConnectionState.disconnected;

  @override
  Future<List<ChatMessageModel>> getConversationHistory(
    String conversationId, {
    int? limit,
    int? offset,
  }) async =>
      const [];

  @override
  void dispose() {}
}

class _BannerChatNotifier extends ChatNotifier {
  _BannerChatNotifier(super.chatRepository, super.ref);

  @override
  Future<void> warmUpConnection() async {}

  Future<void> switchPlanSession(String? planId,
      {BuildContext? context}) async {}
}

class _QuietAuroraStatusNotifier extends AuroraStatusNotifier {
  _QuietAuroraStatusNotifier() : super(_NoopApiClient());

  @override
  Future<void> refresh() async {}

  @override
  void startPeriodicRefresh() {}

  @override
  void stopPeriodicRefresh() {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('review banner renders node label and mastery', (tester) async {
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    await ViewStorageService.ensureInitialized();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(preferences),
          planRepositoryProvider.overrideWithValue(_QuietPlanRepository()),
          openClawConnectionProvider.overrideWith(
            (ref) => OpenClawConnectionService(),
          ),
          dashboardProvider.overrideWith((ref) => _QuietDashboardNotifier()),
          examSprintDashboardProvider.overrideWith((ref) async => null),
          auroraDailyStartupRepositoryProvider.overrideWithValue(
            _QuietDailyStartupRepository(),
          ),
          chatProvider.overrideWith(
            (ref) => _BannerChatNotifier(_FakeChatRepository(), ref),
          ),
          auroraStatusProvider.overrideWith(
            (ref) => _QuietAuroraStatusNotifier(),
          ),
        ],
        child: const MaterialApp(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: Locale('zh'),
          home: ChatScreen(
            initialExtraContext: {
              'review_node': 'cn.tcp_flow',
              'node_label': 'TCP 流量控制',
              'mastery': 0.35,
            },
          ),
        ),
      ),
    );

    await tester.pump();

    expect(find.text('正在复习: TCP 流量控制 · 当前掌握 35%'), findsOneWidget);
  });
}
