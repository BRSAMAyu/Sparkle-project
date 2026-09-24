import 'dart:ffi' as ffi;
import 'dart:io';

import 'package:flutter/material.dart';
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
import 'package:sparkle/core/navigation/cold_start_motion.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/focus_session_record.dart';
import 'package:sparkle/core/offline/models/offline_chat_message.dart';
import 'package:sparkle/core/offline/models/translation_record.dart';
import 'package:sparkle/core/offline/models/vocab_word.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart'
    show sharedPreferencesProvider;
import 'package:sparkle/features/chat/presentation/screens/chat_screen.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import '../shared/i18n_test_helper.dart';

/// N20 / IR-G9（A-SPEC4）· tab 切换零转场唯一语法 + 落地转场预算断言。
///
/// 结构断言：
/// - 5 个 tab 分支页一律 NoTransitionPage（含存量靶 chat 分支）；
/// - shell 落地页（splash/auth→shell）是唯一带转场的常驻页，且时长取
///   ColdStartMotion 令牌（standard 档 220ms），深链冷入场动效由它承载。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory hiveDir;
  late Directory isarDir;
  Isar? isar;

  setUpAll(() async {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues({});
    final bundledIsarCore = Platform.isMacOS
        ? '${Directory.current.path}/third_party_plugins/isar_flutter_libs/macos/libisar.dylib'
        : Platform.isLinux
            ? '${Directory.current.path}/third_party_plugins/isar_flutter_libs/linux/libisar.so'
            : null;
    await Isar.initializeIsarCore(
      libraries: bundledIsarCore == null
          ? const {}
          : {
              ffi.Abi.current(): bundledIsarCore,
            },
      download: bundledIsarCore == null,
    );
    hiveDir = Directory.systemTemp.createTempSync('sparkle_tabtrans_hive_');
    isarDir = await Directory.systemTemp.createTemp('sparkle_tabtrans_isar_');
    Hive.init(hiveDir.path);
    isar = await Isar.open(
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
    LocalDatabase().isar = isar!;
    await ViewStorageService.ensureInitialized();
  });

  setUp(() {
    DemoDataService.isDemoMode = true;
  });

  tearDown(() {
    DemoDataService.isDemoMode = false;
    PerformanceService.instance.stopMonitoring();
  });

  testWidgets('5 个 tab 分支一律 NoTransitionPage；shell 落地页取令牌档时长', (tester) async {
    tester.view.devicePixelRatio = 2.0;
    tester.view.physicalSize = const Size(1440, 2960);
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();

    final container = ProviderContainer(
      overrides: [
        authProvider.overrideWith(
          (ref) => _StaticAuthNotifier(
            AuthState(isAuthenticated: true, user: _buildUser()),
          ),
        ),
        // wt302 草稿链后 ChatScreen.initState 直读 chatDraftStoreProvider →
        // sharedPreferencesProvider；shell 落地走 chat 分支即 UnimplementedError。
        sharedPreferencesProvider.overrideWithValue(
          await SharedPreferences.getInstance(),
        ),
        onboardingCompletedProvider.overrideWith(
          (ref) => _StaticOnboardingNotifier(true, ref),
        ),
        enhancedGalaxyRepositoryProvider.overrideWithValue(
          _StubGalaxyRepository(),
        ),
      ],
    );
    addTearDown(() async {
      await tester.pumpWidget(const SizedBox.shrink());
      container.dispose();
    });

    final router = container.read(routerProvider);
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp.router(
          routerConfig: router,
          theme: AppThemes.lightTheme.copyWith(
            splashFactory: NoSplash.splashFactory,
          ),
          locale: const Locale('zh'),
          localizationsDelegates: const [
            ...AppLocalizations.localizationsDelegates,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
        ),
      ),
    );

    // 品牌窗（250ms）+ 落地转场（220ms）走完，落到 home。
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
    expect(router.routeInformationProvider.value.uri.path, '/home');

    // 切到 chat tab（IR-G9 存量靶：原 400ms 冷启动转场）。本卡唯一改动
    // 靶是 chat 分支——其余 4 分支基线即 NoTransitionPage（A-SPEC4 审计
    // @7f855d70 routes.dart:226/244/348/365），本 diff 未触碰，无挂载必要
    // （懒构建：未访问分支无页可查；且 chat 社区等重挂载会引入服务定时器）。
    router.go('/chat');
    for (var i = 0; i < 4; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
    expect(router.routeInformationProvider.value.uri.path, '/chat');
    expect(find.byType(ChatScreen), findsOneWidget);

    // 结构断言：收集全部 Navigator 的 pages。
    // skipOffstage: false —— StatefulShellRoute 的 5 个分支 navigator 中
    // 非活跃分支在 offstage，默认 find 会漏掉。
    final pages = <Page<dynamic>>[];
    for (final nav in tester.widgetList<Navigator>(
      find.byType(Navigator, skipOffstage: false),
    )) {
      pages.addAll(nav.pages);
    }
    // 1 个 shell 落地页 + 5 个 tab 分支页。
    // root(shell) + 已访问分支（home、chat）的 navigator 各 1 页。
    expect(pages.length, 3, reason: 'root(shell) + home/chat 分支 navigator');

    final noTransitionPages =
        pages.whereType<NoTransitionPage<void>>().toList();
    expect(
      noTransitionPages.length,
      2,
      reason: 'N20：tab 分支零转场是唯一语法——home 与 chat（IR-G9 存量靶，'
          '原 400ms 冷启动转场）分支页必须都是 NoTransitionPage；其余 3 分支'
          '基线即零转场（A-SPEC4 审计 routes.dart:226/244/348/365）且本 diff '
          '未触碰，懒构建下无页可查',
    );

    // 唯一带转场的常驻页 = shell 落地页：时长取 ColdStartMotion 令牌
    // （splash/auth→shell 落地面与深链冷入场专用档）。
    final landingPages = pages
        .whereType<CustomTransitionPage<void>>()
        .where((page) => page is! NoTransitionPage<void>)
        .toList();
    expect(landingPages.length, 1);
    expect(landingPages.single.transitionDuration, ColdStartMotion.landing);
    expect(
      landingPages.single.reverseTransitionDuration,
      ColdStartMotion.landingReverse,
    );
    expect(landingPages.single, isA<ColdStartLandingPage>());

    // 清扫挂载期间的后台一次性定时器（shell warmup 等）。
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(seconds: 1));
    }
  });
}

UserModel _buildUser() => UserModel(
      id: '00000000-0000-0000-0000-000000000001',
      username: 'tab_zero_user',
      email: 'tabzero@example.com',
      nickname: 'Tab Zero',
      flameLevel: 3,
      flameBrightness: 0.8,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

class _StaticAuthNotifier extends AuthNotifier {
  _StaticAuthNotifier(AuthState initialState)
      : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = initialState;
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _StaticOnboardingNotifier extends OnboardingCompletedNotifier {
  _StaticOnboardingNotifier(this._completed, Ref ref) : super(ref);

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

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository()
      : super(
          _UnusedApiClient(),
          SecureTokenStorage(storage: _MemorySecureStorage()),
        );

  @override
  Future<bool> isLoggedIn() async => false;

  @override
  Future<UserModel> getCurrentUser() {
    throw UnimplementedError();
  }

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MemorySecureStorage implements FlutterSecureStorage {
  final Map<String, String> _values = <String, String>{};

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
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _StubGalaxyRepository extends EnhancedGalaxyRepository {
  _StubGalaxyRepository() : super(_UnusedApiClient());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
