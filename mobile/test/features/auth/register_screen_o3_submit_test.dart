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
import 'package:sparkle/features/auth/presentation/screens/register_screen.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import '../../shared/i18n_test_helper.dart';
import '../../shared/no_network_http_overrides.dart';

/// O3（wt436）红绿测试：注册提交必须有真实反馈路径，且桌面主手势
/// （键盘 Enter / IME done）必须能触发提交。
///
/// J-01（wt398）实测 macOS 桌面「注册提交无效且零反馈」（7 runs × 3 点击
/// 策略）。wt436 复盘拆出两层根因：
///
/// 1. 测量驱动假阳性：J01 驱动以 `最后出现的「注册」文本` 定位提交按钮，
///    而注册屏 GraphiteScaffold 的遍历顺序里 AppBar 标题「注册」排在 body
///    之后 —— 驱动点了标题（无手势、无反馈）×21 次，真实提交按钮从未被
///    触达（复现证据：submit_center=(94,28) 且无 SparkleButton 祖先）。
///    产品按钮链路本身完整（失败 snackbar / TOS 提示 / 成功跳转）。
/// 2. 真实产品缺陷：登录屏有 W-4 键盘提交链（done + onFieldSubmitted），
///    注册屏四字段零 textInputAction/onFieldSubmitted —— 桌面用户填完
///    确认密码按 Enter 完全无响应（提交不发生、零反馈），与 J01 观察
///    同 symptom。
///
/// 红（修复前）：合法表单 + 已勾选协议，IME done 提交 → register 0 次调用。
/// 绿（修复后）：键盘 done 触发 _submit → register 恰好 1 次调用。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  // V3-FIX-120：transport 层禁网——屏内未覆盖的 provider（userRepository 等）
  // 不得真发 GET /user/settings 到常驻网关（双测合并跑互扰根因）。
  setUp(installNoNetworkHttpOverrides);
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<ProviderContainer> pumpRegisterScreen(
    WidgetTester tester,
    _CountingAuthRepository repo,
  ) async {
    // J01 实测桌面窗口几何（1600x1200 物理像素 @2x = 逻辑 800x600）。
    tester.view
      ..physicalSize = const Size(1600, 1200)
      ..devicePixelRatio = 2.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

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
        child: testMaterialApp(home: const RegisterScreen()),
      ),
    );
    await tester.pumpAndSettle();
    return container;
  }

  Future<void> fillValidForm(WidgetTester tester) async {
    final fields = find.byType(TextFormField);
    expect(fields.evaluate().length, 4);
    await tester.enterText(fields.at(0), 'j01px1diag');
    await tester.enterText(fields.at(1), 'j01px1diag@example.com');
    await tester.enterText(fields.at(2), 'J01-Passw0rd!');
    await tester.enterText(fields.at(3), 'J01-Passw0rd!');
    await tester.pump(const Duration(milliseconds: 300));
    // 勾选两块协议 tile（滚动到可见再点，真实命中）。
    for (var t = 0; t < 2; t++) {
      await tester.scrollUntilVisible(
        find.byType(CheckboxListTile).at(t),
        120,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pump(const Duration(milliseconds: 250));
      await tester.tap(find.byType(CheckboxListTile).at(t));
      await tester.pump(const Duration(milliseconds: 250));
    }
  }

  testWidgets('O3 核心：键盘 done（桌面 Enter 主手势）必须触发注册提交', (tester) async {
    final repo = _CountingAuthRepository();
    await pumpRegisterScreen(tester, repo);
    await fillValidForm(tester);

    // 焦点在确认密码字段（最后 enterText 的字段），IME done = 桌面 Enter。
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();
    await tester.pumpAndSettle();

    // 红（修复前）：0 —— 提交不发生且零反馈；绿（修复后）：1。
    expect(repo.registerCalls, 1);
  });

  testWidgets('O3 反馈路径：点真实提交按钮，TOS 未勾给出可见提示，勾选后提交失败给出可见错误', (tester) async {
    final repo = _CountingAuthRepository();
    await pumpRegisterScreen(tester, repo);
    await fillValidForm(tester);

    // 真实提交按钮唯一可达：label「注册」的 SparkleButton（AppBar 标题无
    // SparkleButton 祖先，天然排除 —— 这是 J01 误触陷阱的正确绕法）。
    final submitButton = find.widgetWithText(SparkleButton, '注册');
    expect(submitButton, findsOneWidget);

    await tester.ensureVisible(submitButton);
    await tester.pump(const Duration(milliseconds: 300));

    // 撤销协议勾选 → 提交必须有可见提示（零反馈即缺陷）。
    await tester.tap(find.byType(CheckboxListTile).at(0));
    await tester.tap(find.byType(CheckboxListTile).at(1));
    await tester.pump(const Duration(milliseconds: 250));
    await tester.tap(submitButton);
    await tester.pump();
    await tester.pumpAndSettle();
    expect(
      find.text('请先同意用户协议与隐私政策'),
      findsOneWidget,
      reason: 'O3：TOS 未勾的提交必须有可见反馈',
    );

    // 勾回协议 → 提交真正到达 repository（stub 失败）→ 可见错误 snackbar。
    await tester.tap(find.byType(CheckboxListTile).at(0));
    await tester.tap(find.byType(CheckboxListTile).at(1));
    await tester.pump(const Duration(milliseconds: 250));
    await tester.tap(submitButton);
    await tester.pump();
    await tester.pumpAndSettle();
    expect(repo.registerCalls, 1, reason: 'O3：提交链路必须真实触发');
    expect(
      find.byType(SnackBar),
      findsOneWidget,
      reason: 'O3：注册失败必须有可见错误反馈（成功路径为路由跳转，见 J01 provider_login_to_dashboard）',
    );
  });
}

class _CountingAuthRepository extends AuthRepository {
  _CountingAuthRepository() : super(_UnusedApiClient(), _MemoryTokenStorage());

  int registerCalls = 0;

  @override
  Future<bool> isLoggedIn() async => false;

  /// 计数后即抛错：走 notifier 失败路径（不触发 SessionRefreshService →
  /// WebSocket warmUp 连锁，避免 fake-async 挂起 timer）。
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
    registerCalls += 1;
    await Future<void>.delayed(const Duration(milliseconds: 5));
    throw Exception('register counted (test stub)');
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
