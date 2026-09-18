import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
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

/// W-5 红绿测试（round1 web 走查）：登录页语义树完整性。
///
/// 走查实测：Flutter web 未激活语义时整页只暴露「1 个匿名 textbox + 隐藏
/// submit」，读屏与语义自动化不可用。本测试在语义开启（tester.ensureSemantics，
/// 对应 main.dart web 端 ensureSemantics 缓解）的前提下，断言登录页暴露
/// 完整、可辨识、可操作的语义节点：
///
/// - 两个输入框携带 accessible name（用户名/密码）；
/// - 主按钮（登录/继续以访客身份）为命名 button；
/// - 三个社交登录按钮（此前是纯图标无名节点）有名称、button 标志与 tap 动作；
/// - 密码可见性切换按钮有可访问名称（tooltip）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  /// 语义必须在测试验证结束前 dispose（addTearDown 晚于终检），故用
  /// try/finally 包裹测试体（同 c18_accessibility_semantics_test 先例）。
  Future<void> withSemantics(
    WidgetTester tester,
    Future<void> Function() body,
  ) async {
    final semantics = tester.ensureSemantics();
    try {
      await body();
    } finally {
      semantics.dispose();
    }
  }

  Future<void> pumpLoginScreen(WidgetTester tester) async {
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
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const LoginScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('输入框暴露 accessible name（用户名/密码）', (tester) async {
    await withSemantics(tester, () => pumpLoginScreen(tester));

    // 用户名输入框：语义树中存在带「用户名」名称的 text field 节点。
    // 注：本 SDK 测试绑定下 SemanticsFinder（find.semantics.byLabel）依赖的
    // rootSemanticsNode 不落地，语义断言统一走 bySemanticsLabel + getSemantics。
    final usernameField = find.bySemanticsLabel('用户名');
    expect(usernameField, findsOneWidget, reason: '用户名输入框必须有语义名称');
    expect(
      tester
          .getSemantics(usernameField)
          .getSemanticsData()
          .flagsCollection.isTextField,
      isTrue,
      reason: '「用户名」语义节点应被标记为输入框',
    );

    final passwordField = find.bySemanticsLabel('密码');
    expect(passwordField, findsOneWidget, reason: '密码输入框必须有语义名称');
    expect(
      tester
          .getSemantics(passwordField)
          .getSemanticsData()
          .flagsCollection.isTextField,
      isTrue,
    );
  });

  testWidgets('登录与访客按钮是可辨识的命名 button', (tester) async {
    await withSemantics(tester, () => pumpLoginScreen(tester));

    final loginNode =
        tester.getSemantics(find.widgetWithText(SparkleButton, '登录'));
    // Semantics label 与子 Text 合并后形如「登录\n登录」，断言包含即可。
    expect(loginNode.label, contains('登录'));
    expect(loginNode.getSemanticsData().flagsCollection.isButton, isTrue);

    final guestNode = tester.getSemantics(
      find.widgetWithText(SparkleButton, '以访客身份继续'),
    );
    expect(guestNode.label, contains('以访客身份继续'));
    expect(guestNode.getSemanticsData().flagsCollection.isButton, isTrue);
  });

  testWidgets('社交登录按钮有名称、button 标志与 tap 动作（W-5 无名图标修复）', (
    tester,
  ) async {
    await withSemantics(tester, () => pumpLoginScreen(tester));

    final iconByLabel = {
      'Google': find.byIcon(Icons.g_mobiledata_rounded),
      'Apple': find.byIcon(Icons.apple_rounded),
      '微信': find.byIcon(Icons.wechat_rounded),
    };
    for (final entry in iconByLabel.entries) {
      final node = tester.getSemantics(entry.value);
      expect(
        node.label,
        entry.key,
        reason: '${entry.key} 按钮必须暴露语义名称',
      );
      expect(
        node.getSemanticsData().flagsCollection.isButton,
        isTrue,
        reason: '${entry.key} 语义节点应为 button',
      );
      expect(
        node.getSemanticsData().hasAction(SemanticsAction.tap),
        isTrue,
        reason: '${entry.key} 语义节点必须带 tap 动作（读屏可激活）',
      );
    }
  });

  testWidgets('密码可见性切换有可访问名称（tooltip）', (tester) async {
    await withSemantics(tester, () => pumpLoginScreen(tester));

    // Tooltip 语义进的是节点 tooltip 属性而非 label。
    expect(find.byTooltip('显示密码'), findsOneWidget);
    final hiddenNode = tester.getSemantics(find.byIcon(Icons.visibility_off));
    expect(hiddenNode.getSemanticsData().tooltip, '显示密码');

    await tester.tap(find.byIcon(Icons.visibility_off));
    await tester.pump();

    // 切换后语义名称随状态翻转（隐藏密码）。
    expect(find.byTooltip('隐藏密码'), findsOneWidget);
    final shownNode = tester.getSemantics(find.byIcon(Icons.visibility));
    expect(shownNode.getSemanticsData().tooltip, '隐藏密码');
  });
}

class _NoopAuthRepository extends AuthRepository {
  _NoopAuthRepository() : super(_UnusedApiClient(), _MemoryTokenStorage());

  @override
  Future<bool> isLoggedIn() async => false;

  @override
  Future<UserModel> login(String usernameOrEmail, String password) async {
    throw UnimplementedError('semantics test should not call login');
  }

  @override
  Future<UserModel> guestLogin(String guestId) async {
    throw UnimplementedError('semantics test should not call guestLogin');
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
