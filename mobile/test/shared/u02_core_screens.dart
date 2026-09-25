import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show MethodChannel;
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/adaptive/emotion_responsive_theme.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';
import 'package:sparkle/core/utils/text_rendering.dart';
import 'package:sparkle/features/aurora/data/models/aurora_comeback_context.dart';
import 'package:sparkle/features/aurora/data/models/aurora_daily_startup_message.dart';
import 'package:sparkle/features/aurora/data/repositories/aurora_daily_startup_repository.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/journey/presentation/widgets/first_action_card.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/user/presentation/screens/unified_settings_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

import '../features/home/dashboard_test_harness.dart';
import '../features/journey/u02_first_action_fixture.dart';

/// U-02 验收双档截图/rubric 共享装配：四个核心屏 × 两档刺激水平的
/// 真实渲染宿主。屏代码零改动，数据面经 provider 覆写钉为确定性
/// 状态（与存量 harness 同口径，渲染/主题层全部真实）。
///
/// 截图范围按 wt390 U-09 45 行矩阵圈定 android 列（1080x2400@3.0）：
/// home(6) / chat(11) / journey-first-action（矩阵中宿主于 home，
/// 本卡单独成图）/ settings(41)。
enum U02Surface { home, chat, journeyFirstAction, settings }

/// wt390 矩阵 android 列 viewport（1080x2400@3.0 → 逻辑 360x800）。
const Size u02ViewportLogicalSize = Size(360, 800);
const double u02ViewportDpr = 3.0;

/// U-02 rubric 已登记发现（棘轮真源，rubric/capture 两侧共用）。
///
/// 修复任一项后应同步清空对应键。编号与详情见
/// v3/09_evidence/u02_rubric/RUBRIC_VERDICT.md。
const Map<U02Surface, Set<String>> registeredU02Findings =
    <U02Surface, Set<String>>{
  U02Surface.home: {},
  // F1 消息时间戳 neutral500(#958A80) 10px w400 最优背景 3.91:1 < AA 4.5:1；
  // F4 chat_accessory_pill.dart:63 Row 在 360 逻辑宽溢出（实测 48-118px）；
  // F5 低刺激档 disableAnimations × AnimatedSize 触发框架断言
  //   （RenderAnimatedSize mutated in its own performLayout）。
  U02Surface.chat: {
    'contrast:958a80',
    'layout:features/chat/presentation/widgets/chat_accessory_pill.dart:63',
    'flutteranim:RenderAnimatedSize',
  },
  // F2 卡内无标题层（全部渲染文本为正文/辅助级）；
  // F3 first_action_card.dart:367 Row 同视口溢出 21px。
  U02Surface.journeyFirstAction: {
    'hierarchy:no-heading',
    'layout:features/journey/presentation/widgets/first_action_card.dart:367',
  },
  U02Surface.settings: {},
};

bool _u02EnvReady = false;

/// 环境初始化（i18n zh / BGM 复位 / Hive 视图存储）。幂等。
///
/// 必须在 setUpAll（真异步区）调用：BGM 复位走真实平台通道，在
/// testWidgets 假异步 zone 内 await 永不完成（会挂死整测）。
Future<void> initializeU02SurfaceEnvironment() async {
  if (_u02EnvReady) return;
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues(<String, Object>{
    'bgm.enabled': false,
    'bgm.palette': 'adaptive',
    'bgm.mode': 'adaptive',
    'bgm.intensity': 'gentle',
    'bgm.variety': 'balanced',
    'bgm.reading_protection': true,
    'bgm.focus_priority': true,
    'bgm.lock_current_style': false,
    'sensory_feedback.aurora_linkage_enabled': true,
  });
  I18nService.instance.updateLocale(const Locale('zh'), AppLocalizationsZh());
  // 平台插件桩（测试宿主无原生通道；环境隔离，非设计行为替换）：
  // 通知插件 initialize 返回 false、path_provider 返回临时目录，
  // 供 NotificationService/BgmService 的异步初始化 fail-soft 落定。
  final messenger = TestDefaultBinaryMessengerBinding
      .instance.defaultBinaryMessenger;
  messenger
    ..setMockMethodCallHandler(
      const MethodChannel('dexterous.com/flutter/local_notifications'),
      (call) async => call.method == 'initialize' ? false : null,
    )
    ..setMockMethodCallHandler(
      const MethodChannel('plugins.flutter.io/path_provider'),
      (call) async => Directory.systemTemp.createTempSync('u02_evidence_').path,
    );
  await BgmService.debugResetState();
  await ViewStorageService.ensureInitialized();
  _u02EnvReady = true;
}

/// 每屏确定性数据钉注 + 真实渲染宿主。
///
/// [chatNotifierOut] 非空时回传 chat notifier，供 pump 后注入真实消息
/// （矩阵 chat__history_citations 状态：含用户/助手往复与引用块）。
Future<Widget> u02SurfaceHost(
  U02Surface surface,
  EmotionResponsiveConfig config, {
  List<ChatNotifier>? chatNotifierOut,
}) async {
  assert(
    _u02EnvReady,
    'u02SurfaceHost: 先在 setUpAll 调 initializeU02SurfaceEnvironment()',
  );
  SharedPreferences.setMockInitialValues(<String, Object>{});
  final preferences = await SharedPreferences.getInstance();

  if (surface == U02Surface.home) {
    // 真实 DashboardScreen + 全量 provider 夹具（存量 harness），外加
    // 双档刺激装配与 CJK fallback 合并。tickerEnabled=true：截图需要
    // 入场动画落定（冻结在初帧=空白图）。
    await initializeDashboardTestEnvironment();
    return buildDashboardTestHarness(
      theme: AppThemes.lightTheme,
      locale: const Locale('zh'),
      size: u02ViewportLogicalSize,
      emotionConfig: config,
      tickerEnabled: true,
    );
  }

  final screen = switch (surface) {
    U02Surface.chat => const ChatScreen(),
    U02Surface.journeyFirstAction => const Scaffold(
        body: SingleChildScrollView(
          child: Padding(
            padding: EdgeInsets.all(16),
            child: FirstActionCard(),
          ),
        ),
      ),
    _ => const UnifiedSettingsScreen(),
  };

  final overrides = <Override>[
    // 环境隔离：测试宿主无 secure-storage 平台通道；钉内存假体阻断
    // AuthRepository 异步 token 读的 MissingPluginException（非设计缺陷）。
    flutterSecureStorageProvider.overrideWithValue(_U02MemorySecureStorage()),
    tokenStorageProvider.overrideWithValue(
      SecureTokenStorage(storage: _U02MemorySecureStorage()),
    ),
    sharedPreferencesProvider.overrideWithValue(preferences),
    ...switch (surface) {
      U02Surface.chat => _chatOverrides(preferences, chatNotifierOut),
      U02Surface.journeyFirstAction => firstActionFixtureOverrides(),
      _ => const <Override>[],
    },
  ];

  return ProviderScope(
    overrides: overrides,
    child: _U02App(config: config, screen: screen),
  );
}

/// U-02 宿主：AppThemes 真实主题管道 + 双档 wrapper + app.dart 根部同款
/// CJK fallback 合并。
class _U02App extends StatelessWidget {
  const _U02App({required this.config, required this.screen});

  final EmotionResponsiveConfig config;
  final Widget screen;

  @override
  Widget build(BuildContext context) => MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: AppThemes.lightTheme,
        locale: const Locale('zh'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: EmotionResponsiveAppWrapper(
          config: config,
          child: DefaultTextStyle.merge(
            style: const TextStyle(fontFamilyFallback: sparkleFontFallback),
            child: screen,
          ),
        ),
      );
}

// ---- chat：chat_scroll_test 同款安静依赖 + 可注入消息的 notifier ----

List<Override> _chatOverrides(
  SharedPreferences preferences,
  List<ChatNotifier>? chatNotifierOut,
) {
  final fakeChatRepo = _U02FakeChatRepository();
  return [
    sharedPreferencesProvider.overrideWithValue(preferences),
    chatProvider.overrideWith((ref) {
      final notifier = _U02ChatNotifier(fakeChatRepo, ref);
      chatNotifierOut?.add(notifier);
      return notifier;
    }),
    planRepositoryProvider.overrideWithValue(_U02QuietPlanRepository()),
    openClawConnectionProvider.overrideWith(
      (ref) => OpenClawConnectionService(),
    ),
    dashboardProvider.overrideWith((ref) => _U02QuietDashboardNotifier()),
    examSprintDashboardProvider.overrideWith((ref) async => null),
    auroraDailyStartupRepositoryProvider.overrideWithValue(
      _U02QuietDailyStartupRepository(),
    ),
    auroraStatusProvider.overrideWith((ref) => _U02QuietAuroraStatusNotifier()),
  ];
}

/// 矩阵 chat__history_citations 状态钉注：往复对话 + 引用块内容
/// （引用经 rawMetadata.citations 真实解析链路）。
List<ChatMessageModel> u02SeedChatMessages() {
  final base = DateTime(2026, 9, 25, 10);
  return [
    ChatMessageModel(
      id: 'u-1',
      conversationId: 'u02-capture',
      content: '我在准备《线性代数》第三章的测验，特征值这部分还不稳。',
      role: MessageRole.user,
      createdAt: base,
    ),
    ChatMessageModel(
      id: 'a-1',
      conversationId: 'u02-capture',
      content: '先做一道 3x3 对角化：求 A=[[2,0,0],[0,3,4],[0,0,3]] 的特征值，'
          '然后写出对应特征向量。完成后告诉我卡在哪一步。',
      role: MessageRole.assistant,
      createdAt: base.add(const Duration(seconds: 20)),
    ),
    ChatMessageModel(
      id: 'u-2',
      conversationId: 'u02-capture',
      content: '特征值 2 和 3（3 是重根）算出来了，特征向量第二组不确定。',
      role: MessageRole.user,
      createdAt: base.add(const Duration(minutes: 6)),
    ),
    ChatMessageModel(
      id: 'a-2',
      conversationId: 'u02-capture',
      content: '方向对了。重根 λ=3 对应广义特征向量要解 (A-3I)x=v，'
          '参考教材例 2[1]，把 v 取 λ=3 的已有特征向量即可。',
      role: MessageRole.assistant,
      createdAt: base.add(const Duration(minutes: 9)),
      rawMetadata: const {
        'citations': [
          {
            'title': '线性代数教材 · 第三章 例2',
            'source_name': 'local://linear_algebra/ch3',
            'page_number': 132,
          },
        ],
      },
    ),
  ];
}

class _U02ChatNotifier extends ChatNotifier {
  _U02ChatNotifier(super.chatRepository, super.ref);

  @override
  Future<void> warmUpConnection() async {}

  void seedMessages(List<ChatMessageModel> messages) {
    state = state.copyWith(messages: messages);
  }
}

/// pump 后注入矩阵 chat__history_citations 确定性消息（幂等入口）。
/// 内存 secure storage（测试环境隔离，无平台通道；dashboard_test_harness
/// 的 _MemorySecureStorage 同款口径）。
class _U02MemorySecureStorage implements FlutterSecureStorage {
  final Map<String, String> _values = <String, String>{};

  @override
  Future<bool> containsKey({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      _values.containsKey(key);

  @override
  Future<void> delete({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    _values.remove(key);
  }

  @override
  Future<void> deleteAll({
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    _values.clear();
  }

  @override
  Future<String?> read({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      _values[key];

  @override
  Future<Map<String, String>> readAll({
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      Map<String, String>.from(_values);

  @override
  Future<void> write({
    required String key,
    String? value,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (value == null) {
      _values.remove(key);
    } else {
      _values[key] = value;
    }
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}


/// 注入矩阵 chat__history_citations 确定性消息。调用时机：pump 至
/// notifier 初始化落定之后（初始化会重置消息，先种会被覆盖）。
void seedU02ChatMessages(ChatNotifier notifier) {
  if (notifier is _U02ChatNotifier) {
    notifier.seedMessages(u02SeedChatMessages());
  }
}

class _U02FakeChatRepository extends Fake implements ChatRepository {
  @override
  Stream<WsConnectionState> get connectionStateStream => const Stream.empty();
  @override
  WsConnectionState get connectionState => WsConnectionState.disconnected;
  @override
  void dispose() {}
  @override
  Future<List<Map<String, dynamic>>> getRecentConversations() async => [];
}

class _U02QuietDashboardNotifier extends DashboardNotifier {
  _U02QuietDashboardNotifier() : super(_U02QuietDashboardRepository());

  @override
  Future<void> refresh() async {}
}

class _U02QuietDashboardRepository extends DashboardRepository {
  _U02QuietDashboardRepository() : super(_U02FakeApiClient());

  @override
  Future<Map<String, dynamic>> getDashboardStatus() async => const {};

  @override
  Future<Map<String, dynamic>> getGrowthDashboard() async => const {};

  @override
  Future<Map<String, dynamic>> getPredictiveDashboard() async => const {};
}

class _U02QuietPlanRepository extends PlanRepository {
  _U02QuietPlanRepository() : super(_U02FakeApiClient());

  @override
  Future<List<PlanModel>> getPlans({PlanType? type, bool? isActive}) async =>
      const [];

  @override
  Future<List<PlanModel>> getActivePlans() async => const [];
}

class _U02QuietDailyStartupRepository extends AuroraDailyStartupRepository {
  _U02QuietDailyStartupRepository() : super(_U02FakeApiClient());

  @override
  Future<AuroraComebackContext> getComebackContext() async =>
      const AuroraComebackContext.empty();

  @override
  Future<AuroraDailyStartupMessage> getDailyStartup({
    required String planId,
  }) async {
    throw StateError('daily startup disabled for u02 capture');
  }
}

class _U02QuietAuroraStatusNotifier extends AuroraStatusNotifier {
  _U02QuietAuroraStatusNotifier() : super(_U02FakeApiClient());

  @override
  Future<void> refresh({String? conversationId}) async {}

  @override
  void startPeriodicRefresh({String? conversationId}) {}

  @override
  void stopPeriodicRefresh() {}
}

class _U02FakeApiClient extends Fake implements ApiClient {}
