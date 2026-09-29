import 'dart:async';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/app/routes.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/session_refresh_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart'
    show sharedPreferencesProvider;
import 'package:sparkle/features/auth/presentation/screens/register_screen.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart'
    show WsConnectionState;
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart'
    show chatRepositoryProvider;
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/presentation/screens/guest_upgrade_screen.dart';
import 'package:sparkle/features/user/presentation/screens/profile_screen.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

import '../../../../shared/i18n_test_helper.dart';

/// V4-U06 · 首程落点（FIX-541 裁决面）——「注册/升级不落意外我的页」的
/// 真路由可失败测试。
///
/// 裁决规则（卡面 objective「携带用户待发请求到目标对话，否则到该目标今天」）：
/// 注册/升级 = 使用途中的身份切换，成功落点 = 「今天」（/home 驾驶舱）；
/// 「我的」（/profile）是设置面，不是首程落点。
///
/// 三条腿（每腿一正一反，全部走真 router redirect 链，非 provider 直捅）：
/// 1. 升级腿（邮箱）：guest → /profile/upgrade-guest 真实填表提交 →
///    落点必须 = /home 且 DashboardScreen 可见（修复前此测试红：
///    guest_upgrade_screen 两腿显式 context.go('/profile')）；
/// 2. 注册腿：未认证 → /register 真实填表提交（真 redirect，注册屏零显式
///    导航）→ 落点必须 = /home，不得落 /profile；
/// 3. redirect 语义一正一反：已认证用户访问 auth 页 → /home（正）；
///    已认证用户深链 /profile → 保持 /profile（反：落点规则是显式成功
///    导航，不是把 /profile 重写掉的粗暴 redirect；return_to 语义不动）。
void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    // 刻意不初始化 Isar/LocalDatabase：本测试的注册/升级链会走 N-4
    // 身份清除链（LocalDatabase().clearUserScopedData）——isar 就位时该
    // 调用在 fake-async 中真异步挂起（FFI 回调不进测试事件环）；isar 缺位
    // 时抛错被 _clearUserScopedLocalData 的 try/catch 诚实跳过（生产语义
    // 不受影响——本卡验证的是落点路由，不是本地库清除）。
    SharedPreferences.setMockInitialValues({});
    Hive.init(Directory.systemTemp.createTempSync('sparkle_u06_hive_').path);
    await ViewStorageService.ensureInitialized();
  });

  tearDown(() {
    DemoDataService.isDemoMode = false;
  });

  /// 记录型假仓库：register/upgradeGuest 返回真实形用户（非 guest），
  /// 调用留痕供「真实 UI 动作驱动」断言（无 API 旁路冒充）。
  _FakeUpgradeRepo makeRepo() => _FakeUpgradeRepo();

  Future<_LandingHarness> pumpRouter(
    WidgetTester tester, {
    required AuthNotifier Function(Ref ref, AuthRepository repo) buildNotifier,
  }) async {
    tester.view.devicePixelRatio = 1.0;
    // N25/验证时序测试同口径的加高视口（800x2400 逻辑）：ListView 惰性
    // 子项全部可构建，提交钮进 finder 视野（默认视口下表单超一屏）。
    tester.view.physicalSize = const Size(800, 2400);
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();

    final repo = makeRepo();
    final container = ProviderContainer(
      overrides: [
        authProvider.overrideWith(
          (ref) => buildNotifier(ref, repo),
        ),
        sharedPreferencesProvider.overrideWithValue(
          await SharedPreferences.getInstance(),
        ),
        onboardingCompletedProvider.overrideWith(
          (Ref ref) => _FakeOnboardingCompletedNotifier(true, ref),
        ),
        enhancedGalaxyRepositoryProvider.overrideWithValue(
          _UnusedGalaxyRepository(),
        ),
        // 身份切换后的 session 绑定刷新在测试里零承载（n4 同口径）；
        // 聊天仓库假件承接 warmUpConnection（真仓库的 WS 重连计时器会在
        // fake-async 里留下 pending timer——O3 同款教训，见其仓库注记）。
        sessionBoundProvidersProvider.overrideWithValue(const []),
        chatRepositoryProvider.overrideWithValue(_FakeChatRepository()),
      ],
    );
    addTearDown(container.dispose);

    final router = container.read(routerProvider);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp.router(
          routerConfig: router,
          theme: AppThemes.lightTheme,
          // i18n helper 同口径：zh locale（finder 文案锚定中文 arb 词条）。
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

    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
    return _LandingHarness(router: router, repo: repo, container: container);
  }

  /// 轮询等待 finder 非空（SparkleStaggerItem 逐项入场有 index 延迟，
  /// 首屏表单底部的提交钮需要更多帧才进树）。
  Future<bool> waitUntilFound(WidgetTester tester, Finder finder) async {
    for (var i = 0; i < 60; i++) {
      if (finder.evaluate().isNotEmpty) {
        return true;
      }
      await tester.pump(const Duration(milliseconds: 100));
    }
    return finder.evaluate().isNotEmpty;
  }

  /// 等待落点稳定：轮询 router location（升 4s 上限），返回最终 path。
  Future<String> settleLanding(WidgetTester tester, _LandingHarness harness) async {
    var path = harness.router.routeInformationProvider.value.uri.path;
    for (var i = 0; i < 40; i++) {
      await tester.pump(const Duration(milliseconds: 100));
      path = harness.router.routeInformationProvider.value.uri.path;
      if (path == '/home' || path == '/profile') {
        // 落点已翻转到候选面，再多泵几帧让目标屏真正挂载。
        for (var j = 0; j < 8; j++) {
          await tester.pump(const Duration(milliseconds: 100));
        }
        return harness.router.routeInformationProvider.value.uri.path;
      }
    }
    return path;
  }

  Future<void> tearDownHarness(WidgetTester tester, _LandingHarness harness) async {
    // 冲过 AppFeedback toast 的 dismiss 计时器（success 2.5s + 退场动画），
    // 否则 teardown 的 pending-timer 不变量会误杀（f539 同口径的泵法；
    // 驾驶舱有周期动画，不能 pumpAndSettle——固定步进泵过 5s 窗口）。
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 250));
    }
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
    harness.container.dispose();
  }

  testWidgets('升级腿（邮箱）：guest 升级成功落 /home，不落「我的」（修复前红）',
      (tester) async {
    final harness = await pumpRouter(
      tester,
      buildNotifier: _GuestStartAuthNotifier.new,
    );

    // guest 会话 → 进入升级屏（真实路由，非 provider 直捅）。
    harness.router.go(UserRoutes.guestUpgrade);
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
    expect(
      harness.router.routeInformationProvider.value.uri.path,
      UserRoutes.guestUpgrade,
      reason: '前置：guest 必须真实站在升级屏上',
    );
    expect(find.byType(GuestUpgradeScreen), findsOneWidget);

    // 真实填表（四字段 + 两块协议 tile）+ 点「使用邮箱升级」。
    final fields = find.byType(TextFormField);
    expect(fields.evaluate().length, 4);
    await tester.enterText(fields.at(0), 'u06upgraded');
    await tester.enterText(fields.at(1), 'u06upgraded@example.com');
    await tester.enterText(fields.at(2), 'U06-Passw0rd!');
    await tester.enterText(fields.at(3), 'U06-Passw0rd!');
    await tester.pump(const Duration(milliseconds: 200));
    final tiles = find.byType(CheckboxListTile);
    expect(tiles.evaluate().length, 2);
    for (var t = 0; t < 2; t++) {
      await tester.tap(tiles.at(t), warnIfMissed: false);
      await tester.pump(const Duration(milliseconds: 150));
    }
    final upgradeBtn = find.text('使用邮箱升级');
    expect(upgradeBtn, findsOneWidget);
    await tester.ensureVisible(upgradeBtn);
    await tester.pump(const Duration(milliseconds: 200));
    await tester.tap(upgradeBtn, warnIfMissed: false);

    final landing = await settleLanding(tester, harness);

    // 升级真实发生（假仓库留痕 = 真实 UI 动作到达 command 层）。
    expect(harness.repo.upgradeCalls, 1, reason: '升级提交必须真实到达仓库层');
    expect(landing, '/home',
        reason: 'FIX-541 裁决：升级成功落「今天」，不落「我的」；'
            '修复前此断言红（两腿显式 context.go(\'/profile\')）',);
    expect(find.byType(DashboardScreen), findsOneWidget,
        reason: '落地面 = 驾驶舱（今天），可交互可见',);
    await tearDownHarness(tester, harness);
  });

  testWidgets('注册腿：注册成功经真 redirect 落 /home，不落「我的」', (tester) async {
    final harness = await pumpRouter(
      tester,
      buildNotifier: AuthNotifier.new,
    );

    // 未认证 → 落 login；切到注册屏（真实 UI 通道）。
    expect(
      harness.router.routeInformationProvider.value.uri.path,
      '/login',
      reason: '前置：未认证用户落 login',
    );
    harness.router.go('/register');
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
    expect(find.byType(RegisterScreen), findsOneWidget);

    final fields = find.byType(TextFormField);
    expect(fields.evaluate().length, 4);
    await tester.enterText(fields.at(0), 'u06registered');
    await tester.enterText(fields.at(1), 'u06registered@example.com');
    await tester.enterText(fields.at(2), 'U06-Passw0rd!');
    await tester.enterText(fields.at(3), 'U06-Passw0rd!');
    await tester.pump(const Duration(milliseconds: 200));
    final tiles = find.byType(CheckboxListTile);
    expect(tiles.evaluate().length, 2);
    for (var t = 0; t < 2; t++) {
      await tester.tap(tiles.at(t), warnIfMissed: false);
      await tester.pump(const Duration(milliseconds: 150));
    }
    // AppBar 标题与提交钮同文案——按按钮类型锚定（f539 同口径）。
    final registerBtn = find.widgetWithText(SparkleButton, '注册');
    expect(await waitUntilFound(tester, registerBtn), isTrue,
        reason: '提交钮（stagger index 7）入场后必须可达',);
    await tester.ensureVisible(registerBtn);
    // stagger 入场完成后（IgnorePointer 解除）再点。
    for (var i = 0; i < 20 && registerBtn.evaluate().isEmpty; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
    await tester.tap(registerBtn);
    await tester.pump(const Duration(milliseconds: 600));
    if (harness.repo.registerCalls == 0) {
      // ignore: avoid_print
      print('U06DBG afterTap texts='
          '${tester.widgetList<Text>(find.byType(Text)).where((t) => (t.data ?? '').contains('至少') || (t.data ?? '').contains('格式') || (t.data ?? '').contains('协议')).map((t) => t.data).toList()}');
      final fieldsNow = find.byType(TextFormField);
      for (var f = 0; f < fieldsNow.evaluate().length; f++) {
        final tf = tester.widget<TextFormField>(fieldsNow.at(f));
        // ignore: avoid_print
        print('U06DBG field$f="${tf.controller?.text}"');
      }
    }

    final landing = await settleLanding(tester, harness);

    expect(harness.repo.registerCalls, 1, reason: '注册提交必须真实到达仓库层');
    expect(landing, '/home',
        reason: '注册屏零显式导航，落点由真 redirect 语义（无 pending → /home）'
            '决定——注册成功落「今天」，不得落「我的」',);
    expect(find.byType(DashboardScreen), findsOneWidget);
    await tearDownHarness(tester, harness);
  });

  testWidgets('redirect 一正一反：auth 页 → /home；/profile 深链不被重写', (tester) async {
    final harness = await pumpRouter(
      tester,
      buildNotifier: _GuestStartAuthNotifier.new,
    );

    // 正：已认证用户访问 auth 页（/login）→ /home（无 pending）。
    harness.router.go('/login');
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
    expect(
      harness.router.routeInformationProvider.value.uri.path,
      '/home',
      reason: '已认证访问 auth 页 → 「今天」（redirect 语义正向锚）',
    );

    // 反：已认证用户深链 /profile → 保持 /profile（落点规则不越权重写）。
    harness.router.go('/profile');
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
    expect(
      harness.router.routeInformationProvider.value.uri.path,
      '/profile',
      reason: '「我的」深链保持原位——landing 裁决不把 /profile 从用户手里夺走，'
          '只在注册/升级「成功时刻」选对落点',
    );
    expect(find.byType(ProfileScreen), findsOneWidget);
    await tearDownHarness(tester, harness);
  });
}

class _LandingHarness {
  _LandingHarness({
    required this.router,
    required this.repo,
    required this.container,
  });

  final GoRouter router;
  final _FakeUpgradeRepo repo;
  final ProviderContainer container;
}

/// 以 guest 身份起跑的真实 AuthNotifier（升级腿用；checkAuthStatus 直接
/// 置 guest 态，register/upgradeGuest 继承真实实现走假仓库）。
class _GuestStartAuthNotifier extends AuthNotifier {
  _GuestStartAuthNotifier(super.ref, super.authRepository) {
    state = AuthState(isAuthenticated: true, user: _guestUser());
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _FakeUpgradeRepo extends AuthRepository {
  _FakeUpgradeRepo() : super(_UnusedApiClient(), SecureTokenStorage(storage: _MemorySecureStorage()));

  int registerCalls = 0;
  int upgradeCalls = 0;

  @override
  Future<bool> isLoggedIn() async => false;

  @override
  Future<UserModel> register(
    String username,
    String email,
    String password, {
    required bool acceptedTos,
    required bool acceptedPrivacy,
    String tosVersion = 'v1',
    String privacyVersion = 'v1',
    String? agreedLocale,
  }) async {
    registerCalls++;
    return _upgradedUser(username);
  }

  @override
  Future<UserModel> upgradeGuest({
    required String username,
    required String email,
    required String password,
    required bool acceptedTos,
    required bool acceptedPrivacy,
    String tosVersion = 'v1',
    String privacyVersion = 'v1',
    String? agreedLocale,
  }) async {
    upgradeCalls++;
    return _upgradedUser(username);
  }

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}
}

UserModel _guestUser() => UserModel(
      id: '00000000-0000-0000-0000-000000000006',
      username: 'u06_guest',
      email: 'u06guest@example.com',
      nickname: 'U06 Guest',
      flameLevel: 1,
      flameBrightness: 0.5,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      registrationSource: 'guest',
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

UserModel _upgradedUser(String username) => UserModel(
      id: '00000000-0000-0000-0000-000000000061',
      username: username,
      email: '$username@example.com',
      nickname: username,
      flameLevel: 1,
      flameBrightness: 0.5,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      registrationSource: 'email',
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

class _FakeOnboardingCompletedNotifier extends OnboardingCompletedNotifier {
  _FakeOnboardingCompletedNotifier(this._completed, Ref ref) : super(ref);

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

/// n4 同口径的假聊天仓库：ensureConnected 即完成，零重连计时器。
class _FakeChatRepository extends ChatRepository {
  _FakeChatRepository() : super(Dio(), container: ProviderContainer());

  final _connectionController =
      StreamController<WsConnectionState>.broadcast();

  @override
  Stream<WsConnectionState> get connectionStateStream =>
      _connectionController.stream;

  @override
  WsConnectionState get connectionState => WsConnectionState.disconnected;

  @override
  Future<void> dispose() async {
    await _connectionController.close();
  }
}


class _UnusedGalaxyRepository extends EnhancedGalaxyRepository {
  _UnusedGalaxyRepository() : super(_UnusedApiClient());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
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
