import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';
import 'package:sparkle/features/aurora/data/models/aurora_comeback_context.dart';
import 'package:sparkle/features/aurora/data/models/aurora_daily_startup_message.dart';
import 'package:sparkle/features/aurora/data/repositories/aurora_daily_startup_repository.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';

import '../shared/i18n_test_helper.dart';

/// V4-FIX-566：U07 遗留两缺陷的可失败钉（真实 ChatScreen + 真实滚动物理）。
///
/// ① 纯连接失败 reuse 重试路径补 force 滚动——正：中段点「重试」回最新端
///    且不追加重复用户消息；反：到达性滚动（新助手消息）仍不拉回阅读位
///    （补 force 未越权到「增量不抢滚动」语义）。
/// ② 中段阅读「跳最新」入口——贴最新端隐藏 / 上滑阅读可见 / 滑回贴底或
///    点击后回底并隐藏。
class _NoopApiClient implements ApiClient {
  @override
  Dio get dio => Dio();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// sendMessage 的 token await 在测试里不能碰真实安全存储平台通道。
class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository()
      : super(
          _NoopApiClient(),
          SecureTokenStorage(storage: const FlutterSecureStorage()),
        );

  @override
  Future<String?> getAccessToken() async => 'test-token';
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
    throw StateError('daily startup disabled for f566 test');
  }
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

/// 纯连接失败故事：connectionState 常态 failed；chatStream 由测试逐次投喂。
class _FakeChatRepository extends Fake implements ChatRepository {
  _FakeChatRepository(this._streamFactory);

  final Stream<ChatStreamEvent> Function() _streamFactory;

  @override
  Stream<WsConnectionState> get connectionStateStream => const Stream.empty();

  @override
  WsConnectionState get connectionState => WsConnectionState.failed;

  @override
  Stream<ChatStreamEvent> chatStream(
    String message,
    String? conversationId, {
    String? userId,
    String? requestId,
    String? nickname,
    Map<String, dynamic>? extraContext,
    String? token,
    List<String>? fileIds,
    bool includeReferences = false,
    String? chatMode,
    bool? useDocumentContext,
  }) =>
      _streamFactory();

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

/// 构造期零网络：AuthNotifier 构造会 unawaited(checkAuthStatus())，
/// Dart 方法虚分派使子类覆写即拦截，杜绝真实会话核验 socket。
class _QuietAuthNotifier extends AuthNotifier {
  _QuietAuthNotifier(super.ref, super.authRepository);

  @override
  Future<void> checkAuthStatus() async {}
}

class _F566ChatNotifier extends ChatNotifier {
  _F566ChatNotifier(super.chatRepository, super.ref);

  @override
  Future<void> warmUpConnection() async {}

  // 实例方法遮蔽 ChatNotifierActions extension 同名方法（banner 测试同款），
  // 计划切换监听不再触碰仓库 IO；extension 方法不可 @override。
  Future<void> switchPlanSession(
    String? planId, {
    BuildContext? context,
  }) async {}

  /// 一次性播种历史消息（单次 state 写 = 单次 messages 监听触发）。
  void seedMessages(List<ChatMessageModel> msgs) {
    state = state.copyWith(messages: msgs);
  }

  /// retryLastMessage 的 request==null 分支会 reconnect()——仓库桩下静音。
  @override
  Future<void> reconnect() async {}

  /// 直接播种「纯连接失败后的可重试错误态」（用户消息居末位为 reuse 前提）。
  /// 不经真实 send 流：错误横幅渲染路径在本机环境会等待真实事件（见
  /// run_manifest 环境注记），FIX-566 的差量在「点重试 → force 滚动」，
  /// 播种态即可钉住该差量。
  void seedRetryableFailure() {
    state = state.copyWith(
      error: '连接中断，请重试',
      errorCode: 'STREAM_TIMEOUT',
      isErrorRetryable: true,
    );
  }

  /// 追加一条助手消息（模拟到达性内容到达）。
  void appendAssistantMessage(String content) {
    state = state.copyWith(messages: [
      ...state.messages,
      ChatMessageModel(
        id: 'ai_${DateTime.now().microsecondsSinceEpoch}',
        conversationId: state.conversationId ?? 'f566',
        role: MessageRole.assistant,
        content: content,
        createdAt: DateTime.now(),
      ),
    ],);
  }
}

/// 播种历史消息（取回 notifier 播种一次，测试体内不再复用时用本助手）。
void _seedHistoryViaScreen(WidgetTester tester, int count) {
  (tester
          .state<ConsumerState>(find.byType(ChatScreen))
          .ref
          .read(chatProvider.notifier) as _F566ChatNotifier)
      .seedMessages(historyMessages(count));
}

List<ChatMessageModel> historyMessages(int count) => List.generate(
      count,
      (i) => ChatMessageModel(
        id: 'history_$i',
        conversationId: 'f566',
        role: MessageRole.assistant,
        content: '历史消息 $i',
        createdAt: DateTime.now().subtract(
          Duration(minutes: count - i),
        ),
      ),
      growable: false,
    );

Finder get _reversedListFinder => find.byWidgetPredicate(
      (widget) => widget is ListView && widget.reverse,
      description: 'reversed chat message list',
    );

void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  Future<void> settleFrames(WidgetTester tester) async {
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
  }

  testWidgets('F566① 正：中段阅读点「重试」强制回最新端（force 补齐差量钉）',
      (tester) async {
    tester.view.physicalSize = const Size(900, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    await ViewStorageService.ensureInitialized();

    final controllers = <StreamController<ChatStreamEvent>>[];
    final repository = _FakeChatRepository(() {
      final controller = StreamController<ChatStreamEvent>();
      controllers.add(controller);
      return controller.stream;
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(preferences),
          apiClientProvider.overrideWithValue(_NoopApiClient()),
          authRepositoryProvider.overrideWithValue(_FakeAuthRepository()),
          authProvider.overrideWith(
            (ref) => _QuietAuthNotifier(ref, _FakeAuthRepository()),
          ),
          chatProvider.overrideWith(
            (ref) => _F566ChatNotifier(repository, ref),
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
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    // 纯连接失败后的会话形状：历史 + 末位用户消息 + 可重试错误。
    // （reuse 前提 = 用户消息居末位，provider 侧语义由单元测
    // chat_f566_retry_reuse_path_test.dart 钉；此处钉 screen 侧差量。）
    final notifier = tester
        .state<ConsumerState>(find.byType(ChatScreen))
        .ref
        .read(chatProvider.notifier) as _F566ChatNotifier
      ..seedMessages([
        ...historyMessages(40),
        ChatMessageModel(
          id: 'user_failed',
          conversationId: 'f566',
          role: MessageRole.user,
          content: '连接测试',
          createdAt: DateTime.now(),
        ),
      ])
      ..seedRetryableFailure();
    await settleFrames(tester);

    final retryButton = find.text('重试');
    expect(retryButton, findsOneWidget, reason: '前置：可重试错误横幅在场');

    // 用户上滑阅读历史，离开 240px 跟随窗。
    await tester.drag(_reversedListFinder, const Offset(0, 600));
    await settleFrames(tester);
    final scrollable = find
        .descendant(
          of: _reversedListFinder,
          matching: find.byType(Scrollable),
        )
        .first;
    final position = tester.state<ScrollableState>(scrollable).position;
    expect(
      position.pixels,
      greaterThan(240),
      reason: '前置：已离开跟随窗，重试 force 才有区分度',
    );
    expect(find.byKey(const Key('chatJumpToLatest')), findsOneWidget);

    // 点「重试」（显式用户动作）→ 必须强制回最新端（U07 C-2 补齐差量）。
    await tester.tap(retryButton);
    await settleFrames(tester);

    expect(
      tester.state<ScrollableState>(scrollable).position.pixels,
      0.0,
      reason: '重试是显式用户动作，reuse 路径也必须 force 回最新端',
    );
    expect(
      notifier.state.messages
          .where((message) => message.role == MessageRole.user)
          .map((message) => message.content),
      ['连接测试'],
      reason: '重试不追加重复用户消息',
    );
    expect(find.byKey(const Key('chatJumpToLatest')), findsNothing);

    // 消费错误监听排定的 10s 自动清除 fake 定时器（测试不变量：零残留定时器）。
    await tester.pump(const Duration(seconds: 11));
    await settleFrames(tester);

    for (final controller in controllers) {
      await controller.close();
    }
  });

  testWidgets('F566① 反：到达性滚动不抢滚动——新助手消息到达不拉回阅读位置',
      (tester) async {
    tester.view.physicalSize = const Size(900, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    await ViewStorageService.ensureInitialized();

    final controllers = <StreamController<ChatStreamEvent>>[];
    final repository = _FakeChatRepository(() {
      final controller = StreamController<ChatStreamEvent>();
      controllers.add(controller);
      return controller.stream;
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(preferences),
          apiClientProvider.overrideWithValue(_NoopApiClient()),
          authRepositoryProvider.overrideWithValue(_FakeAuthRepository()),
          authProvider.overrideWith(
            (ref) => _QuietAuthNotifier(ref, _FakeAuthRepository()),
          ),
          chatProvider.overrideWith(
            (ref) => _F566ChatNotifier(repository, ref),
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
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    final notifier = tester
        .state<ConsumerState>(find.byType(ChatScreen))
        .ref
        .read(chatProvider.notifier) as _F566ChatNotifier
      ..seedMessages(historyMessages(40));
    await settleFrames(tester);

    await tester.drag(_reversedListFinder, const Offset(0, 600));
    await settleFrames(tester);
    final scrollable = find
        .descendant(
          of: _reversedListFinder,
          matching: find.byType(Scrollable),
        )
        .first;
    final readingOffset =
        tester.state<ScrollableState>(scrollable).position.pixels;
    expect(readingOffset, greaterThan(240));

    // 到达性内容到达（助手消息）——U07「增量不抢滚动」语义必须原样保持。
    notifier.appendAssistantMessage('新回复到达');
    await settleFrames(tester);

    expect(
      tester.state<ScrollableState>(scrollable).position.pixels,
      readingOffset,
      reason: '重试补 force 不得越权到到达路径：阅读位置不被拉回',
    );
    expect(find.byKey(const Key('chatJumpToLatest')), findsOneWidget);

    for (final controller in controllers) {
      await controller.close();
    }
  });

  testWidgets('F566② 跳最新入口：贴最新端隐藏、上滑阅读可见、滑回贴底再隐藏',
      (tester) async {
    tester.view.physicalSize = const Size(900, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    await ViewStorageService.ensureInitialized();

    final controllers = <StreamController<ChatStreamEvent>>[];
    final repository = _FakeChatRepository(() {
      final controller = StreamController<ChatStreamEvent>();
      controllers.add(controller);
      return controller.stream;
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(preferences),
          apiClientProvider.overrideWithValue(_NoopApiClient()),
          authRepositoryProvider.overrideWithValue(_FakeAuthRepository()),
          authProvider.overrideWith(
            (ref) => _QuietAuthNotifier(ref, _FakeAuthRepository()),
          ),
          chatProvider.overrideWith(
            (ref) => _F566ChatNotifier(repository, ref),
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
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    _seedHistoryViaScreen(tester, 40);
    await settleFrames(tester);

    final jumpButton = find.byKey(const Key('chatJumpToLatest'));
    expect(jumpButton, findsNothing, reason: '贴最新端（跟随态）入口零面积');

    await tester.drag(_reversedListFinder, const Offset(0, 600));
    await settleFrames(tester);
    expect(jumpButton, findsOneWidget, reason: '上滑阅读中段时入口浮现');

    // 滑回贴底（reversed 列表向下拖 = 回最新端）→ 跟随态恢复 → 入口隐藏。
    await tester.drag(_reversedListFinder, const Offset(0, -2000));
    await settleFrames(tester);
    final scrollable = find
        .descendant(
          of: _reversedListFinder,
          matching: find.byType(Scrollable),
        )
        .first;
    expect(
      tester.state<ScrollableState>(scrollable).position.pixels,
      lessThanOrEqualTo(240),
    );
    expect(jumpButton, findsNothing, reason: '回到跟随窗内入口即隐藏');

    for (final controller in controllers) {
      await controller.close();
    }
  });

  testWidgets('F566② 跳最新入口点击：显式用户动作回最新端且入口消失', (tester) async {
    tester.view.physicalSize = const Size(900, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    await ViewStorageService.ensureInitialized();

    final controllers = <StreamController<ChatStreamEvent>>[];
    final repository = _FakeChatRepository(() {
      final controller = StreamController<ChatStreamEvent>();
      controllers.add(controller);
      return controller.stream;
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(preferences),
          apiClientProvider.overrideWithValue(_NoopApiClient()),
          authRepositoryProvider.overrideWithValue(_FakeAuthRepository()),
          authProvider.overrideWith(
            (ref) => _QuietAuthNotifier(ref, _FakeAuthRepository()),
          ),
          chatProvider.overrideWith(
            (ref) => _F566ChatNotifier(repository, ref),
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
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    final notifier = tester
        .state<ConsumerState>(find.byType(ChatScreen))
        .ref
        .read(chatProvider.notifier) as _F566ChatNotifier
      ..seedMessages(historyMessages(40));
    await settleFrames(tester);

    await tester.drag(_reversedListFinder, const Offset(0, 600));
    await settleFrames(tester);

    final jumpButton = find.byKey(const Key('chatJumpToLatest'));
    expect(jumpButton, findsOneWidget);
    await tester.tap(jumpButton);
    await settleFrames(tester);

    final scrollable = find
        .descendant(
          of: _reversedListFinder,
          matching: find.byType(Scrollable),
        )
        .first;
    expect(
      tester.state<ScrollableState>(scrollable).position.pixels,
      0.0,
      reason: '点击跳最新 = 显式用户动作，滚回最新端',
    );
    expect(jumpButton, findsNothing, reason: '回底后入口隐藏');
    expect(notifier.state.messages, hasLength(40), reason: '入口点击不产生消息副作用');

    for (final controller in controllers) {
      await controller.close();
    }
  });
}
