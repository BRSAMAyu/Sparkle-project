/// Q-03 Autonomous Visual QA — 共享截图/探针 harness（wt401）。
///
/// 真实渲染证据链：
/// - 泵真实 `routerProvider`（demo mode + 真 auth harness，配方同
///   `test/app/router_smoke_test.dart`），不 mock 屏语义；
/// - 截图经 `matchesGoldenFile` 落 PNG 到
///   `v3-output/WT401-Q03-VISUAL/evidence/`（仅 Q03_VISUAL_CAPTURE=true 时写）；
/// - 每屏同步跑程序化布局探针（RenderFlex 溢出异常 / RenderParagraph
///   截断候选），结果写 `layout_probe.json` 供 12 维 rubric 取计算值。
library;

import 'dart:convert';
import 'dart:ffi' as ffi;
import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data' show ByteData, Uint8List;

import 'package:audioplayers_platform_interface/audioplayers_platform_interface.dart'
    show
        AudioEvent,
        AudioplayersPlatformInterface,
        GlobalAudioEvent,
        GlobalAudioplayersPlatformInterface;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart' show MatrixUtils, RenderParagraph;
import 'package:flutter/services.dart'
    show FontLoader, MethodChannel;
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:isar/isar.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/app/routes.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/focus_session_record.dart';
import 'package:sparkle/core/offline/models/offline_chat_message.dart';
import 'package:sparkle/core/offline/models/translation_record.dart';
import 'package:sparkle/core/offline/models/vocab_word.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart'
    show sharedPreferencesProvider;
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart'
    show auroraStatusProvider, AuroraStatusNotifier;
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_brief.dart'
    show UserStatus;
import 'package:sparkle/shared/entities/user_model.dart';

/// 标准档设备 profile：390×844 logical @ 2x。
const Size q03PhysicalSize = Size(780, 1688);
const double q03DevicePixelRatio = 2.0;
const Size q03LogicalSize = Size(390, 844);

/// 证据输出根目录（相对本测试文件 test/goldens/q03_visual_qa/，供
/// matchesGoldenFile 用）。
const String _evidenceRel = '../../../../v3-output/WT401-Q03-VISUAL';

/// 证据输出目录（相对 flutter test 的 CWD=mobile/，供 dart:io 落 JSON 用）。
final Directory _evidenceDir =
    Directory('../v3-output/WT401-Q03-VISUAL');

bool get q03CaptureEnabled =>
    Platform.environment['Q03_VISUAL_CAPTURE'] == 'true';

/// 逐屏布局探针结果（全局累积，tearDownAll 落盘）。
final List<Map<String, Object?>> q03ProbeResults = <Map<String, Object?>>[];

/// 12 维 rubric 对比度采样结果。
final List<Map<String, Object?>> q03ContrastResults = <Map<String, Object?>>[];

Future<void> q03FlushProbeReports(String suiteName) async {
    final dir = _evidenceDir;
    if (!dir.existsSync()) {
      dir.createSync(recursive: true);
    }
    File('${dir.path}/layout_probe_$suiteName.json').writeAsStringSync(
      const JsonEncoder.withIndent('  ').convert(q03ProbeResults),
    );
    File('${dir.path}/contrast_probe_$suiteName.json').writeAsStringSync(
      const JsonEncoder.withIndent('  ').convert(q03ContrastResults),
    );
}

class Q03Harness {
  Q03Harness({required this.router, required this.container});

  final GoRouter router;
  final ProviderContainer container;
  bool _disposed = false;

  /// 导航到 [location]（可带 query/extra），泵帧稳定后返回。
  /// [settlePumps] 控制泵帧数：小值（1–2）可在异步数据未决时捕获真实
  /// loading 态，默认 8 帧稳定。
  Future<void> go(
    WidgetTester tester,
    String location, {
    Object? extra,
    int settlePumps = 8,
  }) async {
    router.go(location, extra: extra);
    await pumpFrames(tester, settlePumps);
  }

  Future<void> pumpFrames(WidgetTester tester, [int frames = 8]) async {
    for (var i = 0; i < frames; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
  }

  /// 截图 + 布局探针。探针永远跑；golden 仅在 Q03_VISUAL_CAPTURE=true 落盘。
  Future<void> capture(
    WidgetTester tester,
    String screenId,
    String stateName,
  ) async {
    final exception = tester.takeException();
    final probe = probeLayout(tester);
    q03ProbeResults.add(<String, Object?>{
      'screen': screenId,
      'state': stateName,
      'pump_exception': exception?.toString(),
      'logical_size': '${q03LogicalSize.width}x${q03LogicalSize.height}',
      'text_widget_count': probe.textCount,
      'truncation_candidates': probe.truncationCandidates,
      'overflow_bounds_widgets': probe.offBoundsCount,
    });
    collectContrastSamples(tester, screenId, stateName);

    if (q03CaptureEnabled) {
      final name = '${screenId}_$stateName';
      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('$_evidenceRel/evidence/$name.png'),
      );
    }
  }

  /// 采样核心屏的文本对比度（前景色 vs 最近不透明背景近似）。
  void collectContrastSamples(
    WidgetTester tester,
    String screenId,
    String stateName,
  ) {
    final context = tester.element(find.byType(MaterialApp).first);
    final scaffoldBg = Theme.of(context).scaffoldBackgroundColor;
    final samples = <Map<String, Object?>>[];
    for (final element in tester.allElements) {
      if (element.widget is! Text) {
        continue;
      }
      final text = element.widget as Text;
      final defaultStyle = DefaultTextStyle.of(element).style;
      final effective = defaultStyle.merge(text.style);
      final fg = effective.color;
      if (fg == null) {
        continue;
      }
      final bg = _nearestOpaqueBackground(element, fallback: scaffoldBg);
      final ratio = _contrastRatio(fg, bg);
      samples.add(<String, Object?>{
        'text': (text.data ?? text.textSpan?.toPlainText() ?? '').trim(),
        'fg': fg.toARGB32().toRadixString(16),
        'bg': bg.toARGB32().toRadixString(16),
        'ratio': ratio.toStringAsFixed(2),
        'font_size': effective.fontSize,
      });
    }
    if (samples.isNotEmpty) {
      q03ContrastResults.add(<String, Object?>{
        'screen': screenId,
        'state': stateName,
        'scaffold_bg': scaffoldBg.toARGB32().toRadixString(16),
        'min_ratio': samples
            .map((s) => double.parse(s['ratio'] as String))
            .reduce(math.min)
            .toStringAsFixed(2),
        'samples': samples,
      });
    }
  }

  Color _nearestOpaqueBackground(Element element, {required Color fallback}) {
    Color? found;
    element.visitAncestorElements((current) {
      final widget = current.widget;
      if (widget is Container) {
        final decoration = widget.decoration;
        if (decoration is BoxDecoration) {
          final color = decoration.color;
          if (color != null && color.a == 1.0) {
            found = color;
            return false;
          }
        }
        final containerColor = widget.color;
        if (containerColor != null && containerColor.a == 1.0) {
          found = containerColor;
          return false;
        }
      }
      if (widget is Material) {
        final color = widget.color;
        if (color != null && color.a == 1.0) {
          found = color;
          return false;
        }
      }
      if (widget is ColoredBox && widget.color.a == 1.0) {
        found = widget.color;
        return false;
      }
      return true;
    });
    return found ?? fallback;
  }

  double _contrastRatio(Color a, Color b) {
    final la = _relativeLuminance(a);
    final lb = _relativeLuminance(b);
    final lighter = math.max(la, lb);
    final darker = math.min(la, lb);
    return (lighter + 0.05) / (darker + 0.05);
  }

  double _relativeLuminance(Color c) {
    final r = _linearize(c.r);
    final g = _linearize(c.g);
    final b = _linearize(c.b);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  double _linearize(double channel) {
    if (channel <= 0.03928) {
      return channel / 12.92;
    }
    return math.pow((channel + 0.055) / 1.055, 2.4).toDouble();
  }

  Future<void> dispose(WidgetTester tester) async {
    if (_disposed) {
      return;
    }
    _disposed = true;
    PerformanceService.instance.stopMonitoring();
    // 静音既有 known issue：chat 动画/Timer 在拆卸窗口期残留
    // （配方同 chat_area_budget_test——不吞其余框架错误）。
    final originalOnError = FlutterError.onError;
    FlutterError.onError = (details) {
      final msg = details.exceptionAsString();
      if (msg.contains('A Timer is still pending') ||
          msg.contains('An animation is still running even after')) {
        return;
      }
      originalOnError?.call(details);
    };
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
    // 冲走 chat WS 连接链的一次性 timer（6 档退避+每档 10s ready 超时
    // ≈ 90s；泵 300s 让重连预算自然耗尽，pending timer 归零）。
    await tester.pump(const Duration(seconds: 300));
    container.dispose();
    FlutterError.onError = originalOnError;
  }
}

class Q03ProbeResult {
  Q03ProbeResult({
    required this.textCount,
    required this.truncationCandidates,
    required this.offBoundsCount,
  });

  final int textCount;
  final List<Map<String, Object?>> truncationCandidates;
  final int offBoundsCount;
}

Q03ProbeResult probeLayout(WidgetTester tester) {
  var textCount = 0;
  var offBoundsCount = 0;
  final truncationCandidates = <Map<String, Object?>>[];

  void visit(RenderObject? renderObject) {
    if (renderObject == null) {
      return;
    }
    if (renderObject is RenderParagraph) {
      textCount++;
      final plain = renderObject.text.toPlainText().trim();
      if (plain.isEmpty) {
        return;
      }
      final textSize = renderObject.textSize;
      final boxSize = renderObject.size;
      final clippedHorizontally = boxSize.width < textSize.width - 1.0;
      final clippedVertically = boxSize.height < textSize.height - 1.0;
      if (clippedHorizontally || clippedVertically) {
        truncationCandidates.add(<String, Object?>{
          'text': plain.length > 60 ? plain.substring(0, 60) : plain,
          'box': '${boxSize.width.toStringAsFixed(0)}x'
              '${boxSize.height.toStringAsFixed(0)}',
          'text_extent': '${textSize.width.toStringAsFixed(0)}x'
              '${textSize.height.toStringAsFixed(0)}',
          'axis': clippedHorizontally && clippedVertically
              ? 'both'
              : clippedHorizontally
                  ? 'width'
                  : 'height',
        });
      }
    }
    final transform = renderObject.getTransformTo(null);
    final paintBounds = MatrixUtils.transformRect(
      transform,
      renderObject.paintBounds,
    );
    if (paintBounds.width > q03LogicalSize.width + 2.0 ||
        paintBounds.height > q03LogicalSize.height + 2.0) {
      offBoundsCount++;
    }
    renderObject.visitChildren(visit);
  }

  visit(tester.binding.rootElement?.renderObject);
  return Q03ProbeResult(
    textCount: textCount,
    truncationCandidates: truncationCandidates,
    offBoundsCount: offBoundsCount,
  );
}

/// 泵真实路由 app（配方与 router_smoke_test 一致，standard 档主题）。
Future<Q03Harness> pumpQ03App(
  WidgetTester tester, {
  AuthState? authState,
  bool onboardingCompleted = true,
  List<Override> extraOverrides = const <Override>[],
}) async {
  tester.view.devicePixelRatio = q03DevicePixelRatio;
  tester.view.physicalSize = q03PhysicalSize;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });

  SharedPreferences.setMockInitialValues(<String, Object>{
    kOnboardingCompletedKey: onboardingCompleted,
  });
  await ViewStorageService.ensureInitialized();

  final container = ProviderContainer(
    overrides: <Override>[
      // aurora 周期刷新起 Timer.periodic，widget test 收尾必挂 pending
      // timer——用自家静音 notifier（配方同 chat_scroll_test）。
      auroraStatusProvider.overrideWith(
        (ref) => _Q03QuietAuroraStatusNotifier(),
      ),
      authProvider.overrideWith(
        (ref) => _Q03FakeAuthNotifier(
          authState ??
              AuthState(
                isAuthenticated: true,
                user: q03BuildUser(),
              ),
        ),
      ),
      sharedPreferencesProvider.overrideWithValue(
        await SharedPreferences.getInstance(),
      ),
      onboardingCompletedProvider.overrideWith(
        (ref) => _Q03OnboardingCompletedNotifier(onboardingCompleted, ref),
      ),
      enhancedGalaxyRepositoryProvider.overrideWithValue(
        _Q03GalaxyRepository(),
      ),
      ...extraOverrides,
    ],
  );
  var disposed = false;
  addTearDown(() {
    if (!disposed) {
      disposed = true;
      container.dispose();
    }
  });

  final router = container.read(routerProvider);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: MaterialApp.router(
        routerConfig: router,
        // 视觉证据不留 debug 斜纹（遮挡右上角内容）。
        debugShowCheckedModeBanner: false,
        theme: AppThemes.lightTheme.copyWith(
          splashFactory: NoSplash.splashFactory,
        ),
        darkTheme: AppThemes.darkTheme.copyWith(
          splashFactory: NoSplash.splashFactory,
        ),
        locale: const Locale('zh'),
        localizationsDelegates: const [
          ...AppLocalizations.localizationsDelegates,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
      ),
    ),
  );
  final harness = Q03Harness(router: router, container: container);
  await harness.pumpFrames(tester);
  tester.takeException();
  return harness;
}

/// flutter_tester 不带平台字体，中文一律渲染成 tofu——把系统 CJK 字体
/// （Arial Unicode）注册到默认字体族与 sparkleFontFallback 各族名下，
/// 让截图文字真实可读。同时注册 MaterialIcons/CupertinoIcons 图标字体
/// （取 flutter SDK 缓存，路径按平台解释器推导）。字体缺失时静默跳过。
Future<void> q03LoadRealFont() async {
  final flutterRoot = _guessFlutterRoot();
  final fontSources = <String, List<String>>{
    '/System/Library/Fonts/Supplemental/Arial Unicode.ttf': const <String>[
      'Roboto',
      '.SF Pro Text',
      '.SF UI Text',
      'PingFang SC',
      'Hiragino Sans GB',
      'Heiti SC',
      'Noto Sans SC',
      'Noto Sans CJK SC',
      'Arial Unicode MS',
      'Segoe UI',
    ],
    '$flutterRoot/bin/cache/artifacts/material_fonts/'
            'MaterialIcons-Regular.otf':
        const <String>['MaterialIcons'],
    '$flutterRoot/bin/cache/artifacts/material_fonts/Roboto-Regular.ttf':
        const <String>['Roboto'],
  };
  for (final entry in fontSources.entries) {
    final file = File(entry.key);
    if (!file.existsSync()) {
      continue;
    }
    final bytes = Uint8List.fromList(file.readAsBytesSync());
    for (final family in entry.value) {
      final loader = FontLoader(family)
        ..addFont(
          Future<ByteData>.value(ByteData.view(bytes.buffer)),
        );
      await loader.load();
    }
  }
}

/// 从测试二进制位置推导 flutter SDK 根（bin/cache/artifacts 上两级）。
String _guessFlutterRoot() {
  final executable = Platform.resolvedExecutable;
  var dir = File(executable).parent.path;
  for (var i = 0; i < 6; i++) {
    final candidate = '$dir/bin/cache';
    if (Directory(candidate).existsSync()) {
      return dir;
    }
    dir = File(dir).parent.path;
  }
  return '/opt/homebrew/share/flutter';
}

/// mock flutter_tester 缺平台实现的原生通道（音频/通知/secure_storage/连通性）。
/// 截图（matchesGoldenFile）会等 endOfFrame，把 probe 模式下未决的平台调用
/// 全部冲刷出来，无 mock 即 MissingPluginException 假失败。
void q03MockPlatformChannels() {
  // audioplayers：player 通道带 UUID 后缀，无法逐个 mock——直接替换平台
  // 实现为静音假体（BgmService/SensoryFeedbackService 均经此平台层）。
  AudioplayersPlatformInterface.instance = _Q03SilentAudioplayers();
  GlobalAudioplayersPlatformInterface.instance = _Q03SilentGlobalAudioplayers();

  final messenger =
      TestWidgetsFlutterBinding.instance.defaultBinaryMessenger;
  const channels = <String>[
    'plugins.it_nomads.com/flutter_secure_storage',
    'dexterous.com/flutter/local_notifications',
    'dev.fluttercommunity.plus/connectivity',
    'dev.fluttercommunity.plus/connectivity_status',
    'plugins.flutter.io/path_provider',
  ];
  for (final name in channels) {
    messenger.setMockMethodCallHandler(
      MethodChannel(name),
      (call) async {
        if (call.method == 'readAll') {
          return <String, String>{};
        }
        // path_provider：指向临时目录，避免 BGM 库目录扫描炸 MissingPlugin。
        if (call.method == 'getApplicationDocumentsDirectory' ||
            call.method == 'getApplicationSupportDirectory' ||
            call.method == 'getTemporaryDirectory') {
          return Directory.systemTemp.createTempSync('q03_path_').path;
        }
        // local_notifications.initialize 契约是 Future<bool>，返回 null 会
        // 在真实调用方炸 _TypeError。
        if (call.method == 'initialize') {
          return true;
        }
        return null;
      },
    );
  }
}

/// audioplayers 静音假体：所有播放器操作 no-op，事件流恒空。
class _Q03SilentAudioplayers extends AudioplayersPlatformInterface {
  @override
  Stream<AudioEvent> getEventStream(String playerId) =>
      const Stream<AudioEvent>.empty();

  @override
  Future<void> create(String playerId) async {}

  @override
  Future<void> dispose(String playerId) async {}

  @override
  dynamic noSuchMethod(Invocation invocation) {
    // 两个时长查询的真实契约是 Future<int?>（毫秒）。
    if (invocation.memberName == #getDuration ||
        invocation.memberName == #getCurrentPosition) {
      return Future<int?>.value(0);
    }
    return Future<void>.value();
  }
}

class _Q03SilentGlobalAudioplayers
    extends GlobalAudioplayersPlatformInterface {
  @override
  Stream<GlobalAudioEvent> getGlobalEventStream() =>
      const Stream<GlobalAudioEvent>.empty();

  @override
  dynamic noSuchMethod(Invocation invocation) => Future<void>.value();
}

Future<void> q03EnsureTestStorage() async {
  q03MockPlatformChannels();  final bundledIsarCore = Platform.isMacOS
      ? '${Directory.current.path}/third_party_plugins/isar_flutter_libs'
          '/macos/libisar.dylib'
      : Platform.isLinux
          ? '${Directory.current.path}/third_party_plugins/isar_flutter_libs'
              '/linux/libisar.so'
          : null;
  await Isar.initializeIsarCore(
    libraries: bundledIsarCore == null
        ? const <ffi.Abi, String>{}
        : <ffi.Abi, String>{ffi.Abi.current(): bundledIsarCore},
    download: bundledIsarCore == null,
  );
  final hiveDir = Directory.systemTemp.createTempSync('sparkle_q03_hive_');
  final isarDir = await Directory.systemTemp.createTemp('sparkle_q03_isar_');
  Hive.init(hiveDir.path);
  final isar = await Isar.open(
    [
      LocalKnowledgeNodeSchema,
      PendingUpdateSchema,
      LocalCRDTSnapshotSchema,
      OutboxItemSchema,
      UserAnalyticsEventSchema,
      TranslationRecordSchema,
      TranslationWordLinkSchema,
      VocabWordSchema,
      VocabReviewSchema,
      FocusSessionRecordSchema,
      CachedStatisticsModelSchema,
      OfflineChatMessageSchema,
    ],
    directory: isarDir.path,
  );
  LocalDatabase().isar = isar;
}

UserModel q03BuildUser() => UserModel(
      id: '00000000-0000-0000-0000-000000000001',
      username: 'visual_qa_user',
      email: 'visual-qa@example.com',
      nickname: '视觉审查',
      flameLevel: 3,
      flameBrightness: 0.8,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

class _Q03QuietAuroraStatusNotifier extends AuroraStatusNotifier {
  _Q03QuietAuroraStatusNotifier() : super(_Q03ApiClientStub());

  @override
  Future<void> refresh({String? conversationId}) async {}

  @override
  void startPeriodicRefresh({String? conversationId}) {}

  @override
  void stopPeriodicRefresh() {}
}

class _Q03ApiClientStub implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Q03FakeAuthNotifier extends AuthNotifier {  _Q03FakeAuthNotifier(AuthState authState)
      : super(_Q03UnusedRef(), _Q03UnusedAuthRepository()) {
    state = authState;
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _Q03OnboardingCompletedNotifier extends OnboardingCompletedNotifier {
  _Q03OnboardingCompletedNotifier(this._completed, Ref ref) : super(ref);

  final bool _completed;

  @override
  Future<void> syncForUser(UserModel? user) async {
    state = _completed;
  }

  @override
  Future<void> setCompleted(bool value) async {
    state = value;
  }
}

class _Q03UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Q03UnusedAuthRepository extends AuthRepository {
  _Q03UnusedAuthRepository()
      : super(_Q03UnusedApiClient(), SecureTokenStorage(storage: _Q03MemStore()));

  @override
  Future<bool> isLoggedIn() async => false;

  @override
  Future<UserModel> getCurrentUser() {
    throw UnimplementedError();
  }

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}
}

class _Q03UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Q03GalaxyRepository extends EnhancedGalaxyRepository {
  _Q03GalaxyRepository() : super(_Q03UnusedApiClient());

  @override
  Stream<SSEEvent> getGalaxyEventsStream({String? lastEventId}) =>
      Stream<SSEEvent>.multi((controller) {});
}

class _Q03MemStore implements FlutterSecureStorage {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
