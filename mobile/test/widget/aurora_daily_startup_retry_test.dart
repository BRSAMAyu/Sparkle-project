import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/aurora/data/models/aurora_comeback_context.dart';
import 'package:sparkle/features/aurora/data/models/aurora_daily_startup_message.dart';
import 'package:sparkle/features/aurora/data/repositories/aurora_daily_startup_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/chat/presentation/screens/chat_screen.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

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

class _Http500DailyStartupRepository extends AuroraDailyStartupRepository {
  _Http500DailyStartupRepository() : super(_NoopApiClient());

  int calls = 0;

  @override
  Future<AuroraDailyStartupMessage> getDailyStartup({
    required String planId,
  }) async {
    calls += 1;
    final requestOptions = RequestOptions(path: '/aurora/daily-startup');
    throw DioException(
      requestOptions: requestOptions,
      response: Response<dynamic>(
        requestOptions: requestOptions,
        statusCode: 500,
      ),
    );
  }

  @override
  Future<AuroraComebackContext> getComebackContext() async =>
      const AuroraComebackContext.empty();
}

class _SuccessfulDailyStartupRepository extends AuroraDailyStartupRepository {
  _SuccessfulDailyStartupRepository() : super(_NoopApiClient());

  int calls = 0;
  String? requestedPlanId;

  @override
  Future<AuroraDailyStartupMessage> getDailyStartup({
    required String planId,
  }) async {
    calls += 1;
    requestedPlanId = planId;
    return const AuroraDailyStartupMessage(
      message: '早上好，缓存计划已接上：今天先完成语言表达 20 分钟。',
      todayFocus: '语言表达',
      estimatedMinutes: 20,
      adjustmentReason: '来自 active plan fallback。',
    );
  }

  @override
  Future<AuroraComebackContext> getComebackContext() async =>
      const AuroraComebackContext.empty();
}

class _FakeChatRepository extends Fake implements ChatRepository {
  @override
  Stream<WsConnectionState> get connectionStateStream => const Stream.empty();

  @override
  WsConnectionState get connectionState => WsConnectionState.disconnected;

  @override
  Future<void> ensureConnected({required String userId, String? token}) async {}

  @override
  Future<List<ChatMessageModel>> getConversationHistory(
    String conversationId, {
    int? limit,
    int? offset,
  }) async =>
      const [];

  @override
  Future<void> reconnect() async {}

  @override
  void dispose() {}
}

class _StartupChatNotifier extends ChatNotifier {
  _StartupChatNotifier(super.chatRepository, super.ref);

  @override
  Future<void> warmUpConnection() async {}
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
  _QuietDashboardNotifier() : super(_QuietDashboardRepository(), _FakeRef());

  @override
  Future<void> fetchData() async {
    state = DashboardState.error('');
  }

  @override
  Future<void> refresh() async {}
}

class _FakeRef implements Ref {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

const _sprint = ExamSprintDashboardData(
  planId: 'plan-1',
  planName: '期末冲刺',
  subject: '语言表达',
  daysLeft: 5,
  targetMode: 'pass',
  todayProgress: ExamSprintTodayProgress(
    completed: 0,
    total: 1,
    completionRate: 0,
  ),
  highFreqCoverage: 0,
  highFreqCoveredCount: 0,
  highFreqTotalCount: 0,
  mistakeFixRate: 0,
  fixedMistakeCount: 0,
  totalMistakeCount: 0,
  streakDays: 0,
  taskGroups: [],
);

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('daily startup 500 shows retry banner', (tester) async {
    await tester.binding.setSurfaceSize(const Size(390, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    await ViewStorageService.ensureInitialized();
    final startupRepository = _Http500DailyStartupRepository();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(preferences),
          dashboardProvider.overrideWith((ref) => _QuietDashboardNotifier()),
          examSprintDashboardProvider.overrideWith((ref) async => _sprint),
          auroraDailyStartupRepositoryProvider.overrideWithValue(
            startupRepository,
          ),
          activePlanProvider.overrideWith(
            (ref) => ActivePlanNotifier(ref)..selectPlan('plan-1'),
          ),
          chatProvider.overrideWith(
            (ref) => _StartupChatNotifier(_FakeChatRepository(), ref),
          ),
        ],
        child: testMaterialApp(
          home: ChatScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(seconds: 6));

    expect(find.text('加载今日概览中…'), findsOneWidget);
    expect(find.byTooltip('重试今日概览'), findsOneWidget);
    expect(startupRepository.calls, 1);

    await tester.tap(find.byTooltip('重试今日概览'));
    await tester.pump();

    expect(startupRepository.calls, 2);
  });

  testWidgets('slow dashboard falls back to active plan for daily startup',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(390, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    await ViewStorageService.ensureInitialized();
    final startupRepository = _SuccessfulDailyStartupRepository();
    final dashboardCompleter = Completer<ExamSprintDashboardData?>();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(preferences),
          dashboardProvider.overrideWith((ref) => _QuietDashboardNotifier()),
          examSprintDashboardProvider.overrideWith(
            (ref) => dashboardCompleter.future,
          ),
          auroraDailyStartupRepositoryProvider.overrideWithValue(
            startupRepository,
          ),
          activePlanProvider.overrideWith(
            (ref) => ActivePlanNotifier(ref)..selectPlan('plan-1'),
          ),
          chatProvider.overrideWith(
            (ref) => _StartupChatNotifier(_FakeChatRepository(), ref),
          ),
        ],
        child: testMaterialApp(
          home: ChatScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(seconds: 6));

    expect(startupRepository.calls, 1);
    expect(startupRepository.requestedPlanId, 'plan-1');
    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChatScreen)),
    );
    expect(
      container.read(chatProvider).messages.single.content,
      contains('缓存计划已接上'),
    );
    expect(find.text('加载今日概览中…'), findsNothing);
  });
}
