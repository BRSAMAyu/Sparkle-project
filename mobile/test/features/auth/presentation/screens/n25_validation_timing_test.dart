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
import 'package:sparkle/features/auth/presentation/screens/forgot_password_screen.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/features/auth/presentation/screens/register_screen.dart';
import 'package:sparkle/features/auth/presentation/screens/reset_password_screen.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import '../../../../shared/i18n_test_helper.dart';

/// N25（A-SPEC5 v1.5）校验三段制时序断言（auth 四屏）：
/// ① 未提交：输入非法值不报错（autovalidateMode=disabled，不提前打扰）；
/// ② 提交：全量校验兜底，错误一次性行内爆出，同时转 onUserInteraction；
/// ③ 提交后：修正字段即时消错（失焦/输入即校验）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<ProviderContainer> pumpAuthScreen(
    WidgetTester tester,
    Widget screen,
  ) async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final container = ProviderContainer(
      overrides: [
        authRepositoryProvider.overrideWithValue(_NoopAuthRepository()),
        sharedPreferencesProvider.overrideWithValue(prefs),
        sessionBoundProvidersProvider.overrideWithValue(const []),
      ],
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: testMaterialApp(home: screen),
      ),
    );
    await tester.pumpAndSettle();
    return container;
  }

  Future<void> enlargeViewport(WidgetTester tester) async {
    tester.view
      ..physicalSize = const Size(800, 2400)
      ..devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  }

  testWidgets('login：未提交输入非法不报错；提交后报错；改对即时消错', (tester) async {
    await enlargeViewport(tester);
    await pumpAuthScreen(tester, const LoginScreen());

    // ① 未提交：输入非法（空已测，输非法短文本）不出现任何错误行。
    await tester.enterText(find.byType(TextFormField).at(0), 'a');
    await tester.pump();
    expect(find.text('请输入密码'), findsNothing,
        reason: '未提交前不得提前报错（三段制第一段）',);

    // ② 提交：全量兜底——密码为空的错误行内出现。
    await tester.tap(find.widgetWithText(SparkleButton, '登录'));
    await tester.pump();
    expect(find.text('请输入密码'), findsOneWidget,
        reason: '提交时必填错误行内爆出（三段制第二段）',);

    // ③ 提交后：输入合法密码即时消错（onUserInteraction）。
    await tester.enterText(find.byType(TextFormField).at(1), 'password123');
    await tester.pump();
    expect(find.text('请输入密码'), findsNothing,
        reason: '首提交后转即时校验，改对即时消错（三段制第三段）',);
  });

  testWidgets('register：未提交不报错；提交爆出全量错误；逐字段修正即时消错', (tester) async {
    await enlargeViewport(tester);
    await pumpAuthScreen(tester, const RegisterScreen());

    // ① 未提交：输入非法邮箱不报错。
    await tester.enterText(find.byType(TextFormField).at(1), 'bad-email');
    await tester.pump();
    expect(find.textContaining('邮箱格式'), findsNothing,
        reason: '未提交前格式错不报（三段制第一段）',);

    // ② 提交：用户名/邮箱/密码错误一并行内爆出。
    await tester.tap(find.widgetWithText(SparkleButton, '注册'));
    await tester.pump();
    expect(find.text('请输入用户名或邮箱'), findsOneWidget);
    expect(find.textContaining('邮箱格式'), findsOneWidget);
    expect(find.text('密码至少需要6个字符'), findsOneWidget);

    // ③ 修正邮箱 → 该字段错误即时消失，其余保持。
    await tester.enterText(find.byType(TextFormField).at(1), 'a@b.com');
    await tester.pump();
    expect(find.textContaining('邮箱格式'), findsNothing,
        reason: '首提交后改对字段即时消错',);
    expect(find.text('密码至少需要6个字符'), findsOneWidget,
        reason: '未动字段错误保持',);
  });

  testWidgets('forgot：未提交不报错；提交报格式错；填合法即时消错', (tester) async {
    await pumpAuthScreen(tester, const ForgotPasswordScreen());

    // ① 未提交。
    await tester.enterText(find.byType(TextFormField), 'not-an-email');
    await tester.pump();
    expect(find.textContaining('邮箱格式'), findsNothing);

    // ② 提交。
    await tester.tap(find.widgetWithText(SparkleButton, '发送重置邮件'));
    await tester.pump();
    expect(find.textContaining('邮箱格式'), findsOneWidget);

    // ③ 修正。
    await tester.enterText(find.byType(TextFormField), 'a@b.com');
    await tester.pump();
    expect(find.textContaining('邮箱格式'), findsNothing);
  });

  testWidgets('reset：未提交不报错；提交爆出必填与长度错；填重置码即时消错', (tester) async {
    await pumpAuthScreen(tester, const ResetPasswordScreen());

    // ① 未提交。
    await tester.pump();
    expect(find.text('请输入重置码'), findsNothing);

    // ② 提交：重置码必填 + 密码长度错误行内爆出。
    await tester.tap(find.widgetWithText(SparkleButton, '确认重置'));
    await tester.pump();
    expect(find.text('请输入重置码'), findsOneWidget);
    expect(find.text('密码至少需要 6 位'), findsOneWidget);

    // ③ 填重置码 → 该字段错误即时消，长度错误保持。
    await tester.enterText(find.byType(TextFormField).at(0), 'reset-code');
    await tester.pump();
    expect(find.text('请输入重置码'), findsNothing);
    expect(find.text('密码至少需要 6 位'), findsOneWidget);
  });
}

class _NoopAuthRepository extends AuthRepository {
  _NoopAuthRepository() : super(_UnusedApiClient(), _MemoryTokenStorage());

  @override
  Future<bool> isLoggedIn() async => false;

  @override
  Future<UserModel> login(String usernameOrEmail, String password) async {
    throw Exception('not expected in validation timing tests');
  }

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}
}

class _MemoryTokenStorage implements TokenStorage {
  final Map<String, String> _values = <String, String>{};

  @override
  Future<String?> read(String key) async => _values[key];

  @override
  Future<String> write(String key, String value) async {
    _values[key] = value;
    return value;
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
