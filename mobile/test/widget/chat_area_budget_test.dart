import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/aurora/data/models/aurora_daily_startup_message.dart';
import 'package:sparkle/features/aurora/data/repositories/aurora_daily_startup_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_design_language_widgets.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_inline_signals.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_prediction_dock.dart';
import 'package:sparkle/features/chat/presentation/widgets/status_awareness_bar.dart';
import 'package:sparkle/features/chat/presentation/widgets/working_memory_drawer.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';

import '../shared/i18n_test_helper.dart';

/// B3-CHAT §5.1 面积预算断言（P2-4 裁决：widget test 断言为主）。
///
/// 断言 chat 屏在手机级表面（390×844）下：
/// 1. 会话本体（气泡流视口）≥ 70% 屏高（SPEC §5.1 chat 预算条款）；
/// 2. 常驻系统面板为零——「AI 当前记住」面板与 Aurora 六态条不再
///    挂载于常驻区（S8：记忆/确认撤出）。
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
  timeContext: AuroraTimeContext.fromJson(null),
  surface: null,
  updatedAt: null,
  facets: const [],
  wakeEligibility: const AuroraWakeEligibility(
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

class _FakeRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeApiClient extends Fake implements ApiClient {}

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

}

class _QuietDashboardNotifier extends DashboardNotifier {
  _QuietDashboardNotifier() : super(_QuietDashboardRepository());

  @override
  Future<void> fetchData() async {
    state = DashboardState.error('');
  }

  @override
  Future<void> refresh() async {}
}

class _QuietDashboardRepository extends DashboardRepository {
  _QuietDashboardRepository() : super(_FakeApiClient());

  @override
  Future<Map<String, dynamic>> getDashboardStatus() async => const {};

  @override
  Future<Map<String, dynamic>> getGrowthDashboard() async => const {};

  @override
  Future<Map<String, dynamic>> getPredictiveDashboard() async => const {};
}

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

/// 会话历史桩：返回与预置消息同源的 two-turn 会话。
/// （initState 的 switchPlanSession 会经 loadConversationHistory 用
///  仓库数据重建消息列表——桩与预置同源才能保住会话本体。）
class _AreaChatRepository extends Fake implements ChatRepository {

  _AreaChatRepository({required this.historyBySession});
  final List<ChatMessageModel> historyBySession;

  @override
  Stream<WsConnectionState> get connectionStateStream => const Stream.empty();

  @override
  WsConnectionState get connectionState => WsConnectionState.disconnected;

  @override
  Future<List<Map<String, dynamic>>> getRecentConversations() async =>
      const [];

  @override
  Future<List<ChatMessageModel>> getConversationHistory(
    String conversationId, {
    int? limit,
    int? offset,
  }) async =>
      historyBySession;

  @override
  void dispose() {}
}

List<ChatMessageModel> _seedMessages() => [
      ChatMessageModel(
        id: 'm-user-1',
        conversationId: 'session-area',
        content: '欧拉回路和哈密顿回路的区别是什么？',
        role: MessageRole.user,
        createdAt: DateTime(2026, 9, 22, 10),
      ),
      ChatMessageModel(
        id: 'm-ai-1',
        conversationId: 'session-area',
        content:
            '欧拉回路要求每条边恰好经过一次，哈密顿回路要求每个顶点恰好经过一次。前者有多项式判定，后者是 NP 完全的。',
        role: MessageRole.assistant,
        createdAt: DateTime(2026, 9, 22, 10, 0, 5),
      ),
    ];

class _AreaChatNotifier extends ChatNotifier {
  _AreaChatNotifier(super.chatRepository, super.ref);

  @override
  Future<void> warmUpConnection() async {}
}

void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  SharedPreferences? prefs;

  setUpAll(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
    await ViewStorageService.ensureInitialized();
  });

  /// 泵真实 ChatScreen 并断言面积预算。
  ///
  /// [minRatio]：canonical 表面为 §5.1 的 0.70 硬预算；375×667 级小屏
  /// 经 OVERLAY-SMALL overlay 化（预测 dock 悬浮于列表底部留白区 +
  /// 模式条折叠行收进「更多」菜单）后，视口实测 76.9%，断言下限
  /// 收紧至 0.70 与 canonical 同档（原 0.62 下限随结构卡作废）。
  Future<void> pumpChatScreen(
    WidgetTester tester, {
    required Size surface,
    double minRatio = 0.70,
  }) async {
    tester.view.physicalSize = surface;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final messages = _seedMessages();
    final notifier = _AreaChatNotifier(
      _AreaChatRepository(historyBySession: messages),
      _FakeRef(),
    );
    notifier.state = notifier.state.copyWith(
      conversationId: 'session-area',
      messages: messages,
    );

    // 静音框架错误（既有 known issue：动画/Timer 在拆卸窗口期残留）。
    final originalOnError = FlutterError.onError;
    FlutterError.onError = (details) {
      final msg = details.exceptionAsString();
      if (msg.contains('A Timer is still pending') ||
          msg.contains('An animation is still running even after')) {
        return;
      }
      originalOnError?.call(details);
    };
    addTearDown(() {
      FlutterError.onError = originalOnError;
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          chatProvider.overrideWith((ref) => notifier),
          auroraStatusProvider.overrideWith((ref) => _FakeAuroraNotifier()),
          dashboardProvider.overrideWith((ref) => _QuietDashboardNotifier()),
          auroraDailyStartupRepositoryProvider.overrideWithValue(
            _QuietDailyStartupRepository(),
          ),
          activePlanProvider.overrideWith(ActivePlanNotifier.new),
          // wt296：ChatScreen 草稿恢复读 sharedPreferencesProvider，
          // 不 override 直接 UnimplementedError（CI 68 败同族修法）。
          sharedPreferencesProvider.overrideWithValue(prefs!),
        ],
        child: testMaterialApp(home: const ChatScreen()),
      ),
    );
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }

    // ① 常驻系统面板为零（S8 撤出断言）；收件箱唯一入口常驻可达。
    expect(find.byType(ChatWorkingMemoryPanel), findsNothing);
    expect(find.byType(StatusAwarenessBar), findsNothing);
    expect(find.byType(ChatInboxEntryIcon), findsOneWidget);

    // ② 面积预算：气泡流视口 ≥70% 屏高（§5.1 chat 条款）。
    final viewportFinder = find.byKey(const Key('chatMessagesViewport'));
    expect(viewportFinder, findsOneWidget);
    final viewportHeight = tester.getSize(viewportFinder).height;
    final screenHeight = tester.view.physicalSize.height /
        tester.view.devicePixelRatio;
    final ratio = viewportHeight / screenHeight;
    // ignore: avoid_print
    print('AREA_BUDGET surface=$surface viewport=$viewportHeight screen=$screenHeight ratio=${(ratio * 100).toStringAsFixed(1)}%');
    expect(
      ratio,
      greaterThanOrEqualTo(minRatio),
      reason: '会话本体面积占比 $ratio 低于预算下限 $minRatio',
    );

    // ③ OVERLAY-SMALL 小屏形态：折叠行收进「更多」菜单、dock 悬浮于
    // 视口底部（仍在树内=功能可达），canonical 面不受此断言约束。
    if (surface.height < 700) {
      expect(
        find.byType(ChatContextToggle),
        findsNothing,
        reason: '小屏折叠态模式条应收进溢出菜单',
      );
      expect(
        find.byType(ChatPredictionDock),
        findsOneWidget,
        reason: '悬浮化不等于移除：dock 胶囊必须仍在可达树内',
      );
    }

    await tester.pumpWidget(const MaterialApp(home: SizedBox.shrink()));
    await tester.pump(const Duration(seconds: 30));
  }

  testWidgets('会话本体 ≥70% 屏高且常驻系统面板为零（390×844）', (tester) async {
    await pumpChatScreen(tester, surface: const Size(390, 844));
  });

  testWidgets('小屏（375×667）overlay 化后 ≥70% 且常驻系统面板为零', (tester) async {
    await pumpChatScreen(tester, surface: const Size(375, 667));
  });
}
