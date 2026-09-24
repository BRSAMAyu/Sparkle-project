import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/session_refresh_service.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import '../../../../shared/i18n_test_helper.dart';

/// W-4 红绿测试：登录页提交防重入。
///
/// round-1 web 走查：一次 Enter 同时产生 login 与 guest 两个 POST
/// （flt-text-editing-host 内原生 form submit 与 Flutter 提交双通道，
/// 间隔远小于一帧）。本测试以「同帧内两次触发」模拟该双通道竞态：
///
/// 红（修复前）：登录按钮同帧双击 → login 被调用两次；login+guest 连击
/// → 两个认证 POST 都发出。
/// 绿（修复后）：800ms 防重入窗口内只放行第一次提交。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  /// 拉高测试视口，登录/访客按钮同屏可见——保证同帧双通道连击都能真实命中。
  void enlargeViewport(WidgetTester tester) {
    tester.view
      ..physicalSize = const Size(800, 2200)
      ..devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  }

  setUp(setUpI18nForTesting);

  tearDown(tearDownI18n);

  Future<ProviderContainer> pumpLoginScreen(WidgetTester tester,
      _CountingAuthRepository repo,) async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final container = ProviderContainer(
      overrides: [
        authRepositoryProvider.overrideWithValue(repo),
        sharedPreferencesProvider.overrideWithValue(prefs),
        sessionBoundProvidersProvider.overrideWithValue(const []),
      ],
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const LoginScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    // 预填合法凭据，保证表单校验放行、提交真正打到 repository。
    await tester.enterText(find.byType(TextFormField).at(0), 'login_user');
    await tester.enterText(find.byType(TextFormField).at(1), 'password123');
    await tester.pump();
    return container;
  }

  testWidgets('同一帧内双击登录按钮只提交一次（双通道防重入）', (tester) async {
    enlargeViewport(tester);
    final repo = _CountingAuthRepository();
    await pumpLoginScreen(tester, repo);

    final loginButton = find.widgetWithText(SparkleButton, '登录');
    expect(loginButton, findsOneWidget);

    // 模拟双通道触发：原生 form submit + Flutter 侧提交落在同一帧内。
    await tester.tap(loginButton, warnIfMissed: false);
    await tester.tap(loginButton, warnIfMissed: false);
    await tester.pump();

    await tester.pumpAndSettle();

    // 红：2（双 POST）；绿：1。
    expect(repo.loginCalls, 1);
  });

  testWidgets('提交后 800ms 内的访客连击被吸收（login+guest 双 POST 复现）',
      (tester) async {
    enlargeViewport(tester);
    final repo = _CountingAuthRepository();
    await pumpLoginScreen(tester, repo);

    final loginButton = find.widgetWithText(SparkleButton, '登录');
    final guestButton = find.widgetWithText(SparkleButton, '以访客身份继续');
    expect(guestButton, findsOneWidget);

    // round-1 实测形态：一次手势序列同时触发 login 与 guest。
    await tester.tap(loginButton, warnIfMissed: false);
    await tester.tap(guestButton, warnIfMissed: false);
    await tester.pump();

    await tester.pumpAndSettle();

    expect(repo.loginCalls, 1);
    // 红：1（guest POST 也发出）；绿：0（防重入窗口内被吸收）。
    expect(repo.guestCalls, 0);
  });
}

class _CountingAuthRepository extends AuthRepository {
  _CountingAuthRepository() : super(_UnusedApiClient(), _MemoryTokenStorage());

  int loginCalls = 0;
  int guestCalls = 0;

  @override
  Future<bool> isLoggedIn() async => false;

  /// 计数后即抛错：走 notifier 的失败路径（不触发 SessionRefreshService →
  /// WebSocket warmUp 连锁，避免 fake-async 挂起 timer），而提交计数发生在
  /// repository 入口，防重入语义不受影响。
  @override
  Future<UserModel> login(String usernameOrEmail, String password) async {
    loginCalls += 1;
    await Future<void>.delayed(const Duration(milliseconds: 5));
    throw Exception('login counted (test stub)');
  }

  @override
  Future<UserModel> guestLogin(String guestId) async {
    guestCalls += 1;
    await Future<void>.delayed(const Duration(milliseconds: 5));
    throw Exception('guest counted (test stub)');
  }

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}
}

class _MemoryTokenStorage implements TokenStorage {
  final Map<String, String> _values = <String, String>{};

  @override
  Future<String?> read(String key) async => _values[key];

  @override
  Future<void> write(String key, String value) async {
    _values[key] = value;
  }

  @override
  Future<void> delete(String key) async {
    _values.remove(key);
  }
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
