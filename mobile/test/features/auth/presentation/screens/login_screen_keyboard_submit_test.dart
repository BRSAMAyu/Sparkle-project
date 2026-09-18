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

/// W-4（web-round2 误伤）红绿测试：键盘 Enter 提交必须发出请求。
///
/// round-2 实测：登录页聚焦输入框后 Enter ×8 零请求。根因是旧的
/// `_consumeSubmitTicket` 把按钮点击与键盘提交放进同一个 800ms 窗口——
/// 按钮通道消费的票据会把紧随其后的键盘提交一并吞掉（且 login/guest
/// 跨动作互吞）。
///
/// 修复：防重入分域 —— 按钮域 800ms（防双击/双 POST，round-1 语义保持），
/// 键盘域 100ms（只吸收 web 原生 form submit + performAction 的同帧双触发）。
///
/// 红（修复前）：「点登录按钮 → 800ms 内 Enter」场景 login 只被调用 1 次
/// （Enter 被按钮票据吞掉）；同帧双 Enter 也会双发。
/// 绿（修复后）：按钮后的 Enter 独立放行（2 次）；同帧双 Enter 只发 1 次。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(setUpI18nForTesting);

  tearDown(tearDownI18n);

  Future<ProviderContainer> pumpLoginScreen(
    WidgetTester tester,
    _CountingAuthRepository repo,
  ) async {
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

  testWidgets('点击登录按钮后紧随的键盘 Enter 提交必须发出请求（分域核心）',
      (tester) async {
    final repo = _CountingAuthRepository();
    await pumpLoginScreen(tester, repo);

    final loginButton = find.widgetWithText(SparkleButton, '登录');
    expect(loginButton, findsOneWidget);

    // 1) 按钮通道提交（消费按钮域票据）。
    await tester.tap(loginButton, warnIfMissed: false);
    await tester.pump();

    // 2) 800ms 内的键盘 Enter（onFieldSubmitted / TextInputAction.done）。
    //    修复前：被按钮域票据吞掉（loginCalls == 1，红）。
    //    修复后：键盘域独立放行（loginCalls == 2，绿）。
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();
    await tester.pumpAndSettle();

    expect(repo.loginCalls, 2);
  });

  testWidgets('键盘通道自身的同帧双触发只提交一次（防原生 form 双通道）',
      (tester) async {
    final repo = _CountingAuthRepository();
    await pumpLoginScreen(tester, repo);

    // 模拟 web 双通道：原生 form submit 与 Flutter performAction 同帧触发。
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();
    await tester.pumpAndSettle();

    // 红（修复前旧窗口也会吸收，但按钮/键盘混域）：本用例锁定键盘域 100ms
    // 独立窗口的语义 —— 双触发只发 1 次。
    expect(repo.loginCalls, 1);
  });
}

class _CountingAuthRepository extends AuthRepository {
  _CountingAuthRepository() : super(_UnusedApiClient(), _MemoryTokenStorage());

  int loginCalls = 0;

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
