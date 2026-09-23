import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/app/routes.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/core/services/session_refresh_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';
import 'package:sparkle/features/auth/data/models/token_model.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

import '../shared/i18n_test_helper.dart';

/// N20（A-SPEC4）· splash 去网络门控的放行路径测试。
///
/// 两层证明：
/// ① widget 层（真路由 + 品牌窗）：splash 不是加载闸也不是闪光——
///    认证未决/已决一律由品牌窗（250ms）统一放行；网络错形态的认证态
///    （isAuthenticated=true、user=null、isLoading=false，由 ② 证明其
///    真实产生）落到 home；401 形态（未认证）落 login 且不闪现。
/// ② provider 层（真 AuthNotifier + 场景化假仓）：stale-while-revalidate
///    ——有 token 先放行（isAuthenticated=true、isLoading=false）；网络层
///    失败保留会话与放行态（IR-G12 不回退）；仅 401 走登出分支。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory hiveDir;

  setUpAll(() async {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues({});
    hiveDir = Directory.systemTemp.createTempSync('sparkle_coldstart_hive_');
    Hive.init(hiveDir.path);
    await ViewStorageService.ensureInitialized();
  });

  setUp(() {
    DemoDataService.isDemoMode = true;
  });

  tearDown(() {
    DemoDataService.isDemoMode = false;
    PerformanceService.instance.stopMonitoring();
  });

  group('① 路由放行（widget，真 routerProvider + 品牌窗）', () {
    Future<void> pumpRouterHarness(
      WidgetTester tester,
      ProviderContainer container,
    ) async {
      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp.router(
            routerConfig: container.read(routerProvider),
            theme: AppThemes.lightTheme.copyWith(
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
    }

    ProviderContainer buildContainer(AuthState initialState) {
      final container = ProviderContainer(
        overrides: [
          authProvider.overrideWith(
            (ref) => _StaticAuthNotifier(initialState),
          ),
        ],
      );
      addTearDown(container.dispose);
      return container;
    }

    String locationOf(ProviderContainer container) => container
        .read(routerProvider)
        .routeInformationProvider
        .value
        .uri
        .path;

    testWidgets('网络错形态（已认证·user 未达）→ 品牌窗后落 home，不卡 splash',
        (tester) async {
      final container = buildContainer(
        // 网络层失败后 SWR 的真实落点形态（见 ② 的 provider 层证明）。
        AuthState(isAuthenticated: true),
      );

      await pumpRouterHarness(tester, container);
      await tester.pump(const Duration(milliseconds: 100));

      // 品牌窗（250ms）内不放行——认证已决也不缩成闪光。
      expect(locationOf(container), '/');

      await tester.pump(const Duration(milliseconds: 200));
      for (var i = 0; i < 4; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }

      expect(
        locationOf(container),
        '/home',
        reason: '网络错保留的会话必须进 app（home + 各数据面离线路径），'
            '不得卡 splash 或打回 login（IR-G12 + N20）',
      );
      expect(find.byType(DashboardScreen), findsOneWidget);

      // 清扫 shell 挂载后的延迟 warmup 定时器（visual-element 1200ms）。
      for (var i = 0; i < 6; i++) {
        await tester.pump(const Duration(seconds: 1));
      }
    });

    testWidgets('401 形态（未认证）→ 品牌窗内不闪现 login，窗后落 login',
        (tester) async {
      final container = buildContainer(AuthState());

      await pumpRouterHarness(tester, container);
      await tester.pump(const Duration(milliseconds: 100));

      // 会话终局已定，但品牌窗未走完——splash 不闪现 login。
      expect(locationOf(container), '/');

      await tester.pump(const Duration(milliseconds: 200));
      for (var i = 0; i < 4; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }

      expect(locationOf(container), '/login');
      expect(find.byType(LoginScreen), findsOneWidget);
    });
  });

  group('② 认证放行语义（provider，真 AuthNotifier + 场景假仓）', () {
    Future<SharedPreferences> mockPrefs(Map<String, Object> values) async {
      SharedPreferences.setMockInitialValues(values);
      return SharedPreferences.getInstance();
    }

    Future<void> waitFor(
      bool Function() predicate, {
      Duration timeout = const Duration(seconds: 2),
    }) async {
      final deadline = DateTime.now().add(timeout);
      while (DateTime.now().isBefore(deadline)) {
        if (predicate()) {
          return;
        }
        await Future<void>.delayed(const Duration(milliseconds: 10));
      }
      expect(predicate(), isTrue);
    }

    ProviderContainer buildRepoContainer(
      AuthRepository authRepository,
      SharedPreferences prefs,
    ) {
      final container = ProviderContainer(
        overrides: [
          authRepositoryProvider.overrideWithValue(authRepository),
          sharedPreferencesProvider.overrideWithValue(prefs),
          sessionBoundProvidersProvider.overrideWithValue(const []),
        ],
      );
      addTearDown(container.dispose);
      return container;
    }

    test('stale-while-revalidate：有 token 先放行，网络层失败保留放行态',
        () async {
      final prefs = await mockPrefs({});
      final repo = _OfflineAuthRepository();
      await repo.saveTokens(_tokens());
      final container = buildRepoContainer(repo, prefs);

      await waitFor(() => container.read(authProvider).isLoading == false);

      final authState = container.read(authProvider);
      // N20：先放行后校验——网络错不打回未认证（splash 由品牌窗放行进 app）。
      expect(authState.isAuthenticated, isTrue);
      expect(authState.isLoading, isFalse);
      // IR-G12 会话保护不回退。
      expect(repo.clearTokensCallCount, 0);
      expect(await repo.getAccessToken(), isNotNull);
    });

    test('仅真 401 走登出分支：先放行态被 reset，token 清除', () async {
      final prefs = await mockPrefs({});
      final repo = _ServerRejectingAuthRepository();
      await repo.saveTokens(_tokens());
      final container = buildRepoContainer(repo, prefs);

      await waitFor(() => container.read(authProvider).isLoading == false);

      final authState = container.read(authProvider);
      expect(authState.isAuthenticated, isFalse);
      expect(repo.clearTokensCallCount, greaterThanOrEqualTo(1));
      expect(await repo.getAccessToken(), isNull);
    });

    test('认证成功：先放行后校验，user 补写完成', () async {
      const userId = '11111111-1111-1111-1111-111111111111';
      final prefs = await mockPrefs({
        '${kOnboardingCompletedKey}_$userId': true,
      });
      final repo = _HappyAuthRepository(_user(id: userId));
      await repo.saveTokens(_tokens());
      final container = buildRepoContainer(repo, prefs);

      await waitFor(() => container.read(authProvider).user != null);

      final authState = container.read(authProvider);
      expect(authState.isAuthenticated, isTrue);
      expect(authState.isLoading, isFalse);
      expect(authState.user?.id, userId);
    });
  });
}

UserModel _user({required String id}) => UserModel(
      id: id,
      username: 'coldstart_user',
      email: 'coldstart@example.com',
      nickname: 'Cold Start',
      flameLevel: 1,
      flameBrightness: 0.5,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

TokenResponse _tokens() => TokenResponse(
      accessToken: 'coldstart-access-token',
      refreshToken: 'coldstart-refresh-token',
      expiresIn: 3600,
    );

class _StaticAuthNotifier extends AuthNotifier {
  _StaticAuthNotifier(AuthState initialState)
      : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = initialState;
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// 场景化基座：isLoggedIn 走真实 token 判定，getCurrentUser 由子类定义。
class _ScenarioAuthRepository extends AuthRepository {
  _ScenarioAuthRepository()
      : super(_UnusedApiClient(), SecureTokenStorage(storage: _memoryStorage()));

  int clearTokensCallCount = 0;

  @override
  Future<bool> isLoggedIn() async => await getAccessToken() != null;

  @override
  Future<void> logout({bool keepDemoMode = false}) async {
    await clearTokens();
  }

  @override
  Future<void> clearTokens() async {
    clearTokensCallCount += 1;
    await super.clearTokens();
  }
}

/// N20 主场景：getCurrentUser 连接层失败（离线/超时形态）——retryable。
class _OfflineAuthRepository extends _ScenarioAuthRepository {
  _OfflineAuthRepository();

  @override
  Future<UserModel> getCurrentUser() async {
    throw DioException(
      requestOptions: RequestOptions(path: '/api/v1/users/me'),
      type: DioExceptionType.connectionError,
    );
  }
}

/// 会话终局场景：服务端明确拒绝（401）。
class _ServerRejectingAuthRepository extends _ScenarioAuthRepository {
  _ServerRejectingAuthRepository();

  @override
  Future<UserModel> getCurrentUser() async {
    throw DioException(
      requestOptions: RequestOptions(path: '/api/v1/users/me'),
      response: Response(
        statusCode: 401,
        requestOptions: RequestOptions(path: '/api/v1/users/me'),
      ),
    );
  }
}

/// 常规冷启动：getCurrentUser 成功返回。
class _HappyAuthRepository extends _ScenarioAuthRepository {
  _HappyAuthRepository(this._user);

  final UserModel _user;

  @override
  Future<UserModel> getCurrentUser() async => _user;
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

_MemorySecureStorage _memoryStorage() => _MemorySecureStorage();

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
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
