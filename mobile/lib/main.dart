import 'dart:async';
import 'dart:ui';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/app/app.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart' as custom;
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/errors/user_facing_error.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/services/client_observability_service.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/performance_monitor.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/services/user_preferences_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/tracing/tracing_service.dart';
import 'package:sparkle/core/utils/error_messages.dart';
import 'package:sparkle/core/utils/text_rendering.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/cognitive/data/repositories/local_cognitive_repository.dart';
import 'package:sparkle/l10n/app_localizations.dart';

void main() async {
  final startupStopwatch = Stopwatch()..start();
  try {
    await _bootstrapAndRun(startupStopwatch);
  } catch (e, stack) {
    debugPrint('❌ FATAL ERROR DURING STARTUP: $e');
    debugPrint(stack.toString());

    // Show a minimal error app instead of just crashing
    // （V3-FIX-370：失败屏只出类别人话+重试/复制诊断入口，原始异常与
    // 堆栈仅留在上方 debug 日志，不再直出用户面）。
    _runStartupErrorApp(e, stack, startupStopwatch);
  }
}

/// 启动成功路径（V3-FIX-370 自原 main() try 体逐字抽取）：初始化关键服务
/// 并 runApp 正式根节点。重试入口 [StartupErrorScreen] 复用本函数重走
/// 完整 bootstrap——正常启动路径行为零变化。
Future<void> _bootstrapAndRun(Stopwatch startupStopwatch) async {
  WidgetsFlutterBinding.ensureInitialized();

  // W-5/W-6（round1 web 走查）：Flutter web 的语义树默认懒构建——只在
  // 浏览器侧辅助技术被探测到（点击 flt-semantics-placeholder / Tab 焦点
  // 遍历）后才生成语义 DOM，走查在未激活状态下整页只见「1 个匿名
  // textbox + 隐藏 submit」。web 端常开语义，读屏与自动化拿到的都是
  // 完整语义树；移动端维持按需构建的默认（无障碍激活时才付构建开销）。
  // 这也是 W-6 glass-pane 0×0 的应用层缓解：语义启用驱动引擎重建事件/
  // 语义宿主层（详见 round1-batch4.md W-6 定性）。
  if (kIsWeb) {
    SemanticsBinding.instance.ensureSemantics();
  }

  FlutterError.onError = (details) {
    FlutterError.presentError(details);
    PerformanceMonitor().reportCrash(
      details.exception,
      details.stack ?? StackTrace.current,
      context: 'flutter_error',
    );
  };

  // Override default red error screen with branded recovery UI
  ErrorWidget.builder = (details) => Material(
        color: DS.surfacePrimary,
        child: custom.CustomErrorWidget(
          type: custom.ErrorType.page,
          message: ErrorMessages.getUserFriendlyMessage(
            'UNKNOWN', details.exceptionAsString(),),
        ),
      );
  PlatformDispatcher.instance.onError = (error, stack) {
    PerformanceMonitor().reportCrash(
      error,
      stack,
      context: 'platform_dispatcher',
    );
    return true;
  };

  // Initialize Hive for local storage
  await Hive.initFlutter();

  // Register Chat Adapters
  // V3-FIX-370：adapter 注册不可重复（重复注册抛 HiveError），重试路径
  // 据此跳过；首次启动只注册一次，行为不变。
  if (!_chatAdaptersRegistered) {
    ChatCacheService.registerAdapters();
    _chatAdaptersRegistered = true;
  }

  // Initialize Local Database (Isar)
  await LocalDatabase().init();

  // Migrate legacy Hive cognitive queue into Outbox
  await LocalCognitiveRepository(localDb: LocalDatabase())
      .migrateToOutboxIfNeeded();

  // Initialize SharedPrefs
  final prefs = await SharedPreferences.getInstance();
  const sentryDsn = String.fromEnvironment('SENTRY_DSN');
  const sentryEnvironment = String.fromEnvironment(
    'SENTRY_ENVIRONMENT',
    defaultValue: 'production',
  );
  const sentryRelease = String.fromEnvironment('SENTRY_RELEASE');
  const sentryTracesSampleRateRaw = String.fromEnvironment(
    'SENTRY_TRACES_SAMPLE_RATE',
    defaultValue: '0.1',
  );
  const sentryPerformanceEnabled = bool.fromEnvironment(
    'SENTRY_PERFORMANCE_ENABLED',
    defaultValue: true,
  );
  const sentryCrashReportingEnabled = bool.fromEnvironment(
    'SENTRY_CRASH_REPORTING_ENABLED',
    defaultValue: true,
  );
  await PerformanceMonitor().initialize(
    sentryDsn: sentryDsn,
    environment: sentryEnvironment,
    release: sentryRelease,
    tracesSampleRate: double.tryParse(sentryTracesSampleRateRaw) ?? 0.1,
    enablePerformanceMonitoring: sentryPerformanceEnabled,
    enableCrashReporting: sentryCrashReportingEnabled,
  );
  await PerformanceService.instance.hydratePreferences(prefs);
  PerformanceService.instance.startMonitoring();

  // Initialize critical services required before the first meaningful frame.
  const otelEndpoint = String.fromEnvironment('OTEL_EXPORTER_OTLP_ENDPOINT');
  final collectorUri =
      otelEndpoint.isNotEmpty ? Uri.parse(otelEndpoint) : null;
  await Future.wait(<Future<void>>[
    ViewStorageService.ensureInitialized(),
    ThemeManager().initialize(),
    TracingService.instance.initialize(collectorUri: collectorUri),
  ]);

  // Enable Demo Mode via --dart-define=DEMO_MODE=true
  const isDemoMode = bool.fromEnvironment('DEMO_MODE');
  DemoDataService.isDemoMode =
      isDemoMode || (prefs.getBool('demo_guest_mode_enabled') ?? false);

  // Initialize unified push service (FCM + JPush)
  // This will be called after app starts, as it needs ProviderScope
  // The actual initialization happens in SparkleApp

  runApp(
    ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        userPreferencesServiceProvider.overrideWithValue(
          UserPreferencesService(prefs),
        ),
      ],
      child: const SparkleApp(),
    ),
  );

  WidgetsBinding.instance.addPostFrameCallback((_) {
    final firstFrameMs = startupStopwatch.elapsedMilliseconds;
    unawaited(
      ClientObservabilityService.instance.recordEvent(
        eventType: 'app_first_frame',
        category: 'lifecycle',
        route: 'bootstrap',
        metadata: <String, dynamic>{
          'startup_ms': firstFrameMs,
          'demo_mode': DemoDataService.isDemoMode,
        },
      ),
    );
  });

  unawaited(_runDeferredStartupWarmups());

  unawaited(
    ClientObservabilityService.instance.recordEvent(
      eventType: 'app_launch',
      category: 'lifecycle',
      route: 'bootstrap',
      metadata: <String, dynamic>{
        'demo_mode': DemoDataService.isDemoMode,
      },
    ),
  );
}

/// Hive adapter 是否已注册（V3-FIX-370 重试幂等守卫，见 [_bootstrapAndRun]）。
bool _chatAdaptersRegistered = false;

/// 启动失败兜底根（V3-FIX-370）：挂上与正式根相同的本地化与字体口径，
/// 内容交给 [StartupErrorScreen]。
void _runStartupErrorApp(
  Object error,
  StackTrace stack,
  Stopwatch startupStopwatch,
) {
  runApp(
    MaterialApp(
      theme: _startupErrorTheme(),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      // 与正式根一致的中文优先解析（失败屏不因语言解析缺位变英文哑面）。
      localeResolutionCallback: (locale, supportedLocales) {
        if (locale != null) {
          for (final supported in supportedLocales) {
            if (supported.languageCode == locale.languageCode) {
              return supported;
            }
          }
        }
        return const Locale('zh');
      },
      builder: (context, child) => DefaultTextStyle.merge(
        style: const TextStyle(fontFamilyFallback: sparkleFontFallback),
        child: child ?? const SizedBox.shrink(),
      ),
      home: StartupErrorScreen(
        error: error,
        onRetry: () => _bootstrapAndRun(startupStopwatch),
      ),
    ),
  );
}

/// 失败屏主题：优先与正式根同款光亮主题；主题装配自身失败时兜底最小
/// 主题（仍须注册 [SparkleThemeExtension]——owner 组件 `context.colors`
/// 构建即读，未注册直接断言失败）。
ThemeData _startupErrorTheme() {
  try {
    return AppThemes.lightTheme;
  } catch (e) {
    debugPrint('⚠️ Startup error theme fallback: $e');
    return ThemeData(
      extensions: <ThemeExtension<dynamic>>[SparkleThemeExtension.light()],
    );
  }
}

/// bootstrap 失败屏（V3-FIX-370）：原实现把原始异常+堆栈 `SelectableText`
/// 直出用户面且无下一步。现只呈现三类信息：
///
/// - 人话：标题 `startupFailedTitle` + 类别文案——复用 wt673 单源映射
///   （`categorizeUiError` → `uiErrorMessage`，经 [UserFacingError] 附
///   `[ERR-*]` 诊断码）；原始异常文本不进 UI；
/// - 重试：重新走完整 bootstrap 流（[_bootstrapAndRun]），成功即由
///   `runApp` 换上正式根节点；再失败按新错误重分类、屏内更新；
/// - 复制诊断信息：剪贴板只放类名/时间戳/类别码，不放原始堆栈
///   （堆栈仅 debugPrint 进日志，与首次失败同一口径）。
class StartupErrorScreen extends StatefulWidget {
  const StartupErrorScreen({
    required this.error,
    required this.onRetry,
    super.key,
  });

  /// 触发 bootstrap 失败的原始异常（仅用于类别判定与调试日志）。
  final Object error;

  /// 重试入口：重新执行完整 bootstrap；成功路径由其内部 runApp 换根。
  final Future<void> Function() onRetry;

  @override
  State<StartupErrorScreen> createState() => _StartupErrorScreenState();
}

class _StartupErrorScreenState extends State<StartupErrorScreen> {
  bool _retrying = false;
  bool _diagnosticsCopied = false;
  late Object _error = widget.error;

  Future<void> _handleRetry() async {
    if (_retrying) return;
    setState(() => _retrying = true);
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    try {
      await widget.onRetry();
    } catch (e, stack) {
      // 原始异常与堆栈只进调试日志，不进用户面。
      debugPrint('❌ STARTUP RETRY FAILED: $e');
      debugPrint(stack.toString());
      if (!mounted) return;
      setState(() {
        _retrying = false;
        _diagnosticsCopied = false;
        _error = e;
      });
      return;
    }
    // 成功路径：bootstrap 已 runApp 正式根节点，本树即将被整体替换；
    // 若此刻仍挂载（如宿主未立即换根），仅复位加载态。
    if (!mounted) return;
    setState(() => _retrying = false);
  }

  Future<void> _handleCopyDiagnostics() async {
    final report = <String>[
      'app: Sparkle startup',
      'time: ${DateTime.now().toUtc().toIso8601String()}',
      'errorType: ${_error.runtimeType}',
      'category: ${categorizeUiError(_error).name}',
    ].join('\n');
    await Clipboard.setData(ClipboardData(text: report));
    if (!mounted) return;
    setState(() => _diagnosticsCopied = true);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      body: SafeArea(
        child: custom.CustomErrorWidget.page(
          context: context,
          title: l10n.startupFailedTitle,
          message: UserFacingError.from(_error),
          actions: [
            SparkleButton(
              label: l10n.retry,
              onPressed: _retrying ? null : () => unawaited(_handleRetry()),
              icon: const Icon(Icons.refresh_rounded),
              variant: ButtonVariant.destructive,
              loading: _retrying,
            ),
            const SizedBox(height: DS.spacing12),
            SparkleButton(
              label: l10n.startupCopyDiagnostics,
              onPressed:
                  _retrying ? null : () => unawaited(_handleCopyDiagnostics()),
              icon: Icon(
                _diagnosticsCopied
                    ? Icons.check_rounded
                    : Icons.copy_rounded,
              ),
              variant: ButtonVariant.secondary,
            ),
          ],
        ),
      ),
    );
  }
}

Future<void> _runDeferredStartupWarmups() async {
  try {
    await Future.wait(<Future<void>>[
      Hive.openBox<dynamic>('settings'),
      Hive.openBox<dynamic>('user'),
      _initializeFirebase(),
    ]);
  } catch (e, stack) {
    debugPrint('⚠️ Deferred startup warmup failed: $e');
    PerformanceMonitor().reportCrash(
      e,
      stack,
      context: 'deferred_startup_warmup',
    );
  }
}

/// Initialize Firebase and FCM
///
/// This initializes Firebase Core and Firebase Cloud Messaging.
/// Requires:
/// - Android: google-services.json in android/app/
/// - iOS: GoogleService-Info.plist in ios/Runner/
Future<void> _initializeFirebase() async {
  try {
    // Check if Firebase is already initialized (by native plugins)
    // If using FlutterFire CLI generated options, use:
    // await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

    // For now, let native plugins handle initialization
    // Firebase will be initialized when FirebaseMessagingService.initialize() is called
    debugPrint('🔥 Firebase will be initialized on demand');
  } catch (e) {
    // Firebase initialization failure should not crash the app
    // Push notifications will simply be unavailable
    debugPrint('⚠️ Firebase initialization skipped: $e');
  }
}
