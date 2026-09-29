/// V4-G02 · 对话/卡住/Hybrid/运行台 家族——四风格 golden + 语义钉。
///
/// 规格权威：v4/02_design/SCREEN_FAMILIES.md「对话 / 卡住 / Hybrid / 运行台」
/// 行 + ACCESSIBILITY_ASSETS.md + 卡面验收 2（「四风格各有确定性 golden+
/// 语义钉且 CI 可失败」）。判例：F05（style_preview_seed 冻结 seed + 真实
/// 主题管道宿主 + 逐档截图）与 wt296（golden 基线 macOS 签发；Linux 字体
/// 渲染差异属环境签名，golden 像素断言 Linux 跳过、语义钉全平台照跑）。
///
/// 面 = 真实家族组件 + 冻结 seed（kSeedStuckCardData / OpenClaw primitives
/// 定样文案），主题一律走 F01 唯一编程入口 `ThemeManager.setPixelPreviewProfile`
/// → AppThemes → DS 管道；本文件零颜色/字号字面量（守卫面由
/// v4_g02_family_contrast_guard_test 数值钉死）。
///
/// 对话流面 = 真实 ChatScreen（chat_f566 同款安静 provider 覆写集，零
/// 网络）：content（气泡+码块+输入坞）/ empty（零消息空态）/ streaming
/// （流式增量气泡）/ model-failure（可重试错误横幅）四态 × 四档。
library;

import 'dart:async';
import 'dart:io' as io;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/style_preview/style_preview_seed.dart';
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
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_avatar_stack.dart';
import 'package:sparkle/features/chat/presentation/widgets/task_stuck_card.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/openclaw/presentation/widgets/openclaw_primitives.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/l10n/app_localizations.dart';

import '../shared/i18n_test_helper.dart';

const List<PixelPreviewProfile> _profiles = <PixelPreviewProfile>[
  PixelPreviewProfile.classic,
  PixelPreviewProfile.paperDay,
  PixelPreviewProfile.dusk,
  PixelPreviewProfile.quiet,
];

String _label(PixelPreviewProfile p) => switch (p) {
      PixelPreviewProfile.classic => 'classic',
      PixelPreviewProfile.paperDay => 'paperDay',
      PixelPreviewProfile.dusk => 'dusk',
      PixelPreviewProfile.quiet => 'quiet',
    };

/// wt296 判例：golden 基线在 macOS 签发；Linux runner 字体渲染（CJK 回退/
/// 抗锯齿）与 macOS 存在环境签名差。像素断言仅 macOS 校验，语义钉全平台。
bool get _goldenCapable => !io.Platform.isLinux;

Future<ThemeManager> _freshThemeManager() async {
  SharedPreferences.setMockInitialValues(<String, Object>{});
  final manager = ThemeManager();
  await manager.reset();
  await manager.initialize();
  return manager;
}

/// 真实主题管道宿主（F05 style_preview_test_harness 同机制）：AnimatedBuilder
/// 监听 ThemeManager 单例，AppThemes.lightTheme 每次重建重估（切档即 live
/// re-theme，非测试替身）。SparkleThemeExtension 由 AppThemes 自带（F05 判例
/// 面即在此宿主下消费 context.sparkle）。
Widget _profileHost({required Widget child}) => AnimatedBuilder(
      animation: ThemeManager(),
      builder: (context, _) => MaterialApp(
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
        home: child,
      ),
    );

/// 固定时长泵（代替 pumpAndSettle：家族面含真实 shimmer/脉动）。
Future<void> _settleFrames(WidgetTester tester, {int ticks = 16}) async {
  for (var i = 0; i < ticks; i++) {
    await tester.pump(const Duration(milliseconds: 50));
  }
}

void _setViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(900, 1400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

// ─────────────────────────────────────────────────────────────────────────────
// ChatScreen 安静 harness（chat_f566_retry_force_scroll_jump_latest_test 同款
// 覆写集：零网络、零真实会话核验；本卡新增 streaming/failure 播种通道）。
// ─────────────────────────────────────────────────────────────────────────────

class _NoopApiClient implements ApiClient {
  @override
  Dio get dio => Dio();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

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
    throw StateError('daily startup disabled for g02 golden test');
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

class _QuietAuthNotifier extends AuthNotifier {
  _QuietAuthNotifier(super.ref, super.authRepository);

  @override
  Future<void> checkAuthStatus() async {}
}

class _G02ChatNotifier extends ChatNotifier {
  _G02ChatNotifier(super.chatRepository, super.ref);

  @override
  Future<void> warmUpConnection() async {}

  // 实例方法遮蔽 ChatNotifierActions extension 同名方法（f566 同款）。
  Future<void> switchPlanSession(
    String? planId, {
    BuildContext? context,
  }) async {}

  @override
  Future<void> reconnect() async {}

  void seedMessages(List<ChatMessageModel> msgs) {
    state = state.copyWith(messages: msgs);
  }

  /// 流式增量态（shouldShowStreamingBubble = hasActiveRun && isSending）。
  void seedStreaming(String partial) {
    state = state.copyWith(
      isSending: true,
      activeRunId: 'g02-seed-run',
      runPhase: ChatRunPhase.streaming,
      streamingContent: partial,
    );
  }

  /// 模型失败态（可重试错误横幅，f566 同款播种）。
  void seedRetryableFailure() {
    state = state.copyWith(
      error: '连接中断，请重试',
      errorCode: 'STREAM_TIMEOUT',
      isErrorRetryable: true,
    );
  }
}

/// ChatScreen 泵装结果（notifier 播种通道 + 需消费的流控制器）。
class _ChatPump {
  const _ChatPump(this.notifier, this.controllers);

  final _G02ChatNotifier notifier;
  final List<StreamController<ChatStreamEvent>> controllers;

  Future<void> dispose() async {
    for (final controller in controllers) {
      await controller.close();
    }
  }
}

const String _kSeedAssistantMarkdown = '### 特征值的三条性质\n\n'
    '对实对称矩阵，谱定理保证特征值全为实数。\n\n'
    '```dart\n'
    'final eigen = A.decompose();\n'
    'print(eigen.values);\n'
    '```\n\n'
    '记住：行列式为零等价于 0 是特征值。';

List<ChatMessageModel> _seedConversation() => <ChatMessageModel>[
      ChatMessageModel(
        id: 'seed_user_1',
        conversationId: 'g02',
        role: MessageRole.user,
        content: '帮我总结线性代数里特征值的考点',
        createdAt: DateTime.now(),
      ),
      ChatMessageModel(
        id: 'seed_ai_1',
        conversationId: 'g02',
        role: MessageRole.assistant,
        content: _kSeedAssistantMarkdown,
        createdAt: DateTime.now(),
      ),
    ];

Future<_ChatPump> _pumpChatScreen(
  WidgetTester tester,
  PixelPreviewProfile profile,
) async {
  await _freshThemeManager();
  await ThemeManager().setPixelPreviewProfile(profile);

  final preferences = await SharedPreferences.getInstance();
  await ViewStorageService.ensureInitialized();

  final controllers = <StreamController<ChatStreamEvent>>[];
  final repository = _FakeChatRepository(() {
    final controller = StreamController<ChatStreamEvent>();
    controllers.add(controller);
    return controller.stream;
  });

  await tester.pumpWidget(
    _profileHost(
      child: ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(preferences),
          apiClientProvider.overrideWithValue(_NoopApiClient()),
          authRepositoryProvider.overrideWithValue(_FakeAuthRepository()),
          authProvider.overrideWith(
            (ref) => _QuietAuthNotifier(ref, _FakeAuthRepository()),
          ),
          chatProvider.overrideWith(
            (ref) => _G02ChatNotifier(repository, ref),
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
        child: const ChatScreen(),
      ),
    ),
  );
  await _settleFrames(tester);

  final notifier = tester
      .state<ConsumerState>(find.byType(ChatScreen))
      .ref
      .read(chatProvider.notifier) as _G02ChatNotifier;
  return _ChatPump(notifier, controllers);
}

void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  // ───────────────────────── 组件面：卡住 sheet + 运行台 ─────────────────────

  for (final profile in _profiles) {
    group('V4-G02 组件面 golden+语义钉 · ${_label(profile)}', () {
      testWidgets('卡住 sheet 面：真实 TaskStuckCard（G02-D3 描边语义钉）', (tester) async {
        _setViewport(tester);
        await _freshThemeManager();
        await ThemeManager().setPixelPreviewProfile(profile);

        await tester.pumpWidget(
          _profileHost(
            child: Scaffold(
              // sheet 宿主面与对比度守卫同源（sheetCard = surfaceSecondary）：
              // TaskStuckCard 本体无面（透明），golden 需真实宿主底色。
              backgroundColor: DS.surfaceSecondary,
              body: SingleChildScrollView(
                child: Padding(
                  padding: const EdgeInsets.all(DS.spacing16),
                  child: TaskStuckCard(
                    data: kSeedStuckCardData,
                    onWidgetAction: (_, __) async {},
                  ),
                ),
              ),
            ),
          ),
        );
        await _settleFrames(tester);

        // 语义钉（CI 可失败，全平台跑）：
        // ① 三段层级在场：陈述文案 → 任务胶囊 Wrap → 动作按钮。
        expect(
          find.text(kSeedStuckCardData['message'] as String),
          findsOneWidget,
          reason: '三段层级第 1 段：卡住陈述在场',
        );
        expect(
          find.byType(Wrap),
          findsNWidgets(2),
          reason: '三段层级第 2 段：任务胶囊组在场',
        );
        expect(
          find.byType(FilledButton),
          findsOneWidget,
          reason: '三段层级第 3 段：主动作（轻会话）在场',
        );
        // ② G02-D3 钉：QuietChip 描边 = neutral600 槽（borderSubtle 在
        //    classic 对胶囊面 1.22:1，不达非文字关键部件阈 3.0，已退役）。
        final chipDecorations = tester.widgetList<Container>(
          find.descendant(
            of: find.byType(TaskStuckCard),
            matching: find.byWidgetPredicate(
              (widget) =>
                  widget is Container && widget.decoration is BoxDecoration,
            ),
          ),
        );
        final chipBorders = chipDecorations
            .map((container) => (container.decoration! as BoxDecoration).border)
            .whereType<Border>()
            .toList();
        expect(chipBorders, isNotEmpty, reason: '前置：胶囊描边存在');
        final neutral600 = DS.neutral600.toARGB32();
        expect(
          chipBorders.every(
            (border) => border.top.color.toARGB32() == neutral600,
          ),
          isTrue,
          reason: 'QuietChip 描边必须走 neutral600 槽（G02-D3）；'
              '实际=${chipBorders.map((b) => b.top.color.toARGB32())} 期望=$neutral600',
        );

        if (_goldenCapable) {
          // 捕 Scaffold（其子树含 Material 底色绘制；捕卡片本体则透明区
          // 在 golden 里渲染为黑底——matchesGoldenFile 不重绘宿主祖先）。
          await expectLater(
            find.byType(Scaffold),
            matchesGoldenFile(
              'goldens/v4_g02/stuck_sheet_${_label(profile)}.png',
            ),
          );
        }
      });

      testWidgets('运行台面：真实 OpenClaw primitives（toneOnTint + 展开面钉）',
          (tester) async {
        _setViewport(tester);
        await _freshThemeManager();
        await ThemeManager().setPixelPreviewProfile(profile);

        await tester.pumpWidget(
          _profileHost(
            child: Scaffold(
              // 运行台宿主面 = scaffold 同源（对比度守卫同口径）。
              backgroundColor: DS.surfacePrimary,
              body: const SingleChildScrollView(
                child: Padding(
                  padding: EdgeInsets.all(DS.spacing16),
                  child: Column(
                    children: [
                      OpenClawStatusCapsule(
                        title: '执行链路在线',
                        subtitle: 'gateway · run-42 · 3 队列',
                        tone: OpenClawVisualTone.connected,
                        metrics: [
                          OpenClawMetricPill(
                            label: '队列 3',
                          ),
                          OpenClawMetricPill(
                            label: '成功率 98%',
                            tone: OpenClawVisualTone.connected,
                          ),
                          OpenClawMetricPill(
                            label: '延迟 812ms',
                            tone: OpenClawVisualTone.attention,
                          ),
                        ],
                        expanded: true,
                        expandedContent: Text(
                          '最近一次运行：特征值专项 · 3 步全部回执',
                        ),
                      ),
                      SizedBox(height: DS.spacing12),
                      OpenClawStatusCapsule(
                        title: '网关离线',
                        subtitle: '上次心跳 12 分钟前',
                        tone: OpenClawVisualTone.offline,
                        showToggle: false,
                      ),
                      SizedBox(height: DS.spacing12),
                      OpenClawIdentityStrip(
                        label: 'run-42 · eigen-specialist',
                        description: 'OpenClaw 路径直连，非像素版独立 Agent 中心',
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
        await _settleFrames(tester);

        // 语义钉：
        // ① G02-D2 钉：零 Colors.white 面字面量（半透白在 dusk 变「白纱」
        //    → 已退役为 surfacePrimary@0.5 主题槽）。
        final whiteFaces = find.byWidgetPredicate(
          (widget) =>
              widget is Container &&
              widget.decoration is BoxDecoration &&
              ((widget.decoration! as BoxDecoration).color == Colors.white ||
                  ((widget.decoration! as BoxDecoration)
                          .gradient
                          ?.colors
                          .contains(Colors.white) ??
                      false)),
        );
        expect(
          whiteFaces,
          findsNothing,
          reason: '运行台面禁止 Colors.white 面字面量（dusk 白纱缺陷）',
        );
        // ② 结构在场：双胶囊 + 身份条 + 展开细节文本可见。
        expect(find.byType(OpenClawStatusCapsule), findsNWidgets(2));
        expect(find.byType(OpenClawIdentityStrip), findsOneWidget);
        expect(find.text('最近一次运行：特征值专项 · 3 步全部回执'), findsOneWidget);
        // ③ toneOnTint 钉：MetricPill 文本色 = DS.toneOnTint(tone)——
        //    浅档收敛（≠ tone 原值）、深档恒等（== tone 原值），四档各有断言。
        final pillText = tester.widget<Text>(find.text('队列 3'));
        expect(
          pillText.style?.color,
          DS.toneOnTint(DS.info),
          reason: '${_label(profile)}：MetricPill 文本走 DS.toneOnTint 收敛槽',
        );

        if (_goldenCapable) {
          await expectLater(
            find.byType(Scaffold),
            matchesGoldenFile(
              'goldens/v4_g02/openclaw_runtime_${_label(profile)}.png',
            ),
          );
        }
      });
    });
  }

  // ─────────────────────── 对话流面：真实 ChatScreen 四态 ──────────────────────

  for (final profile in _profiles) {
    group('V4-G02 对话流面 golden · ${_label(profile)}', () {
      testWidgets('content 态（气泡+码块+输入坞）', (tester) async {
        _setViewport(tester);
        final pump = await _pumpChatScreen(tester, profile);
        pump.notifier.seedMessages(_seedConversation());
        await _settleFrames(tester);

        // 语义钉：seed 对话在场（用户/助手双气泡）。
        expect(find.text('帮我总结线性代数里特征值的考点'), findsOneWidget);
        expect(find.textContaining('特征值的三条性质'), findsOneWidget);

        if (_goldenCapable) {
          await expectLater(
            find.byType(ChatScreen),
            matchesGoldenFile(
              'goldens/v4_g02/chat_flow_content_${_label(profile)}.png',
            ),
          );
        }
        await pump.dispose();
      });

      testWidgets('empty 态（零消息空态）', (tester) async {
        _setViewport(tester);
        final pump = await _pumpChatScreen(tester, profile);
        await _settleFrames(tester);

        // 语义钉：无消息、无失败横幅（空态≠失败态）。
        expect(find.text('帮我总结线性代数里特征值的考点'), findsNothing);
        expect(find.text('连接中断，请重试'), findsNothing);

        if (_goldenCapable) {
          await expectLater(
            find.byType(ChatScreen),
            matchesGoldenFile(
              'goldens/v4_g02/chat_flow_empty_${_label(profile)}.png',
            ),
          );
        }
        await pump.dispose();
      });

      testWidgets('streaming 态（流式增量气泡）', (tester) async {
        _setViewport(tester);
        final pump = await _pumpChatScreen(tester, profile);
        pump.notifier.seedMessages(_seedConversation());
        pump.notifier.seedStreaming('谱定理的两个推论正在展开：');
        await _settleFrames(tester);

        // 语义钉：流式部分内容直接在场（不伪装完成态）。
        expect(find.textContaining('谱定理的两个推论'), findsOneWidget);

        if (_goldenCapable) {
          await expectLater(
            find.byType(ChatScreen),
            matchesGoldenFile(
              'goldens/v4_g02/chat_flow_streaming_${_label(profile)}.png',
            ),
          );
        }
        await pump.dispose();
      });

      testWidgets('model-failure 态（可重试错误横幅）', (tester) async {
        _setViewport(tester);
        final pump = await _pumpChatScreen(tester, profile);
        pump.notifier.seedMessages(_seedConversation());
        pump.notifier.seedRetryableFailure();
        await _settleFrames(tester);

        // 语义钉：失败态横幅 + 重试入口在场（f566 同款文案；错误文案在
        // 横幅与会话转写各渲染一次 → findsWidgets）。
        expect(find.text('连接中断，请重试'), findsWidgets);
        expect(find.text('重试'), findsOneWidget);

        if (_goldenCapable) {
          await expectLater(
            find.byType(ChatScreen),
            matchesGoldenFile(
              'goldens/v4_g02/chat_flow_failure_${_label(profile)}.png',
            ),
          );
        }

        // 消费错误监听排定的 10s 自动清除 fake 定时器（零残留定时器）。
        await tester.pump(const Duration(seconds: 11));
        await _settleFrames(tester);
        await pump.dispose();
      });
    });
  }

  // ───────────────────────────── 200% 文本缩放 ─────────────────────────────

  testWidgets('V4-G02 200% 文本：content 态 classic 不碎版（钉）', (tester) async {
    _setViewport(tester);
    // 200% 文本缩放（平台调度器层注入，MaterialApp 全树生效）。
    tester.platformDispatcher.textScaleFactorTestValue = 2.0;
    addTearDown(tester.platformDispatcher.clearAllTestValues);

    final pump = await _pumpChatScreen(tester, PixelPreviewProfile.classic);
    pump.notifier.seedMessages(_seedConversation());
    await _settleFrames(tester);

    // 语义钉：200% 下最新端助手气泡（reversed 列表 offset 0 端，视口内
    // 必建）文本完整在场（布局无异常=无异常抛出）。
    expect(find.textContaining('特征值的三条性质'), findsOneWidget);

    if (_goldenCapable) {
      await expectLater(
        find.byType(ChatScreen),
        matchesGoldenFile('goldens/v4_g02/chat_flow_content_classic_200.png'),
      );
    }
    await pump.dispose();
  });

  // ───────────────────────────── reduce-motion 等价 ────────────────────────

  testWidgets('V4-G02 reduce-motion：头像栈脉动缺席且可 pumpAndSettle（活钉）',
      (tester) async {
    await _freshThemeManager();
    await ThemeManager().setPixelPreviewProfile(PixelPreviewProfile.paperDay);

    await tester.pumpWidget(
      _profileHost(
        child: MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: Scaffold(
            body: Center(
              child: AgentAvatarStack(
                activeAgents: [
                  AgentInfo(
                    type: 'math',
                    name: 'Sparkle',
                    icon: Icons.auto_awesome,
                    color: Colors.teal,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );

    // 活钉：修前 _transitionController.repeat(reverse: true) 无条件起表，
    // pumpAndSettle 必超时；修后 reduce-motion 分支停表，立即落定。
    await tester.pumpAndSettle();
    expect(find.byIcon(Icons.auto_awesome), findsOneWidget);
  });

  testWidgets('V4-G02 reduce-motion：正常模式脉动在场（反例控制组）', (tester) async {
    await _freshThemeManager();
    await ThemeManager().setPixelPreviewProfile(PixelPreviewProfile.paperDay);

    await tester.pumpWidget(
      _profileHost(
        child: Scaffold(
          body: Center(
            child: AgentAvatarStack(
              activeAgents: [
                AgentInfo(
                  type: 'math',
                  name: 'Sparkle',
                  icon: Icons.auto_awesome,
                  color: Colors.teal,
                ),
              ],
            ),
          ),
        ),
      ),
    );

    // 控制组：reduce-motion 关 → 脉动进行中（scale 偏离 1.0 可观测），
    // 证明上一条的反例断言是活的，不是恒真。
    await tester.pump(const Duration(milliseconds: 400));
    final scales = tester
        .widgetList<Transform>(
          find.descendant(
            of: find.byType(AgentAvatarStack),
            matching: find.byWidgetPredicate((widget) => widget is Transform),
          ),
        )
        .map((transform) => transform.transform.getMaxScaleOnAxis())
        .toList();
    expect(scales, isNotEmpty, reason: '前置：头像栈 Transform 在场');
    expect(
      scales.any((scale) => (scale - 1.0).abs() > 0.001),
      isTrue,
      reason: '正常模式下脉动必须在进行中（实测 scales=$scales）',
    );
    await tester.pump(const Duration(milliseconds: 100));
  });
}
