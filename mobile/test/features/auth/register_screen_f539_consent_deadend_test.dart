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

/// V3-FIX-539（wt800）：macOS 桌面（800x600 逻辑窗）注册提交 tap
/// 「系统性无效零反馈」的根因复现与修复锚定。
///
/// J-02（wt792）实测脉络（integration_test 实机驱动，6/6 复现）：驱动
/// ① 不滚动直接 tap 两块 CheckboxListTile（warnIfMissed:false —— miss
/// 静默）；② ensureVisible 后 tap 真实提交钮（SparkleButton 作用域
/// finder，已规避 J-01 AppBar 标题陷阱）；③ 等 12s 后才 dumpTexts +
/// 错误词扫描；全程无日志（consent 守卫路径本来就不打日志）。
///
/// 本测试复现同一脉络，实证三层事实（hit-test/手势链本身完好 ——
/// register_screen_o3_submit_test 已绿）：
///
/// 1. 几何事实（探针，恒绿）：800x600 下表单填完后，ToS tile 恰在视口
///    内缘（bottom≈589<600）而 Privacy tile 中心落在折叠线下 —— 驱动式
///    定点 tap 一中一失：ToS 勾上、Privacy 静默保持未勾（miss 无任何
///    告警/状态变化）。
/// 2. 反馈缺陷（红）：此时提交被 consent 守卫拦截，唯一反馈是 2.5s 瞬态
///    snackbar（视口底部）；toast 消失后屏面与 tap 前完全一致 —— 无持久
///    指示、不滚动到因 —— 字面意义「零反馈」，与 J-02 观测同型。
/// 3. 恢复缺陷（红→绿）：被拦截后用户没有任何指向性路径回到可提交态。
///
/// 红（修复前）：提交 tap → register 0 次调用；toast 消失后零残留、
/// 协议区未滚入视口。
/// 绿（修复后）：提交 tap → 协议区滚动入视口 + 持久内联错误 + 未勾 tile
/// 高亮（toast 保留）；补勾后内联错误清除，提交真实到达 repository。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(installNoNetworkHttpOverrides);
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<ProviderContainer> pumpRegisterScreen(
    WidgetTester tester,
    _CountingAuthRepository repo,
  ) async {
    // J-02 实测 macOS 桌面窗口几何（1600x1200 物理 @2x = 逻辑 800x600）。
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

  /// J-02 驱动脉络的填表段：enterText 四字段（无滚动），然后**不滚动**
  /// 定点 tap 两块协议 tile（warnIfMissed:false —— 与驱动逐参数一致）。
  Future<void> fillFormDriverStyle(WidgetTester tester) async {
    final fields = find.byType(TextFormField);
    expect(fields.evaluate().length, 4);
    await tester.enterText(fields.at(0), 'j02px9f539');
    await tester.enterText(fields.at(1), 'j02px9f539@example.com');
    await tester.enterText(fields.at(2), 'J02-Passw0rd!');
    await tester.enterText(fields.at(3), 'J02-Passw0rd!');
    await tester.pump(const Duration(milliseconds: 300));
    final tiles = find.byType(CheckboxListTile);
    expect(tiles.evaluate().length, 2);
    for (var t = 0; t < 2; t++) {
      await tester.tap(tiles.at(t), warnIfMissed: false);
      await tester.pump(const Duration(milliseconds: 250));
    }
  }

  /// 驱动的提交段：ensureVisible + tap（warnIfMissed:false），与驱动一致。
  Future<void> submitDriverStyle(WidgetTester tester) async {
    final regBtn = find.widgetWithText(SparkleButton, '注册');
    expect(regBtn, findsOneWidget);
    await tester.ensureVisible(regBtn);
    await tester.pump(const Duration(milliseconds: 400));
    await tester.tap(regBtn, warnIfMissed: false);
    await tester.pump();
  }

  /// 驱动在提交后等 12s 才 dumpTexts/扫描错误词。瞬态 toast 的 dismiss
  /// 计时器在入场动画完成后才起（+2.5s）——先 settle 入场，再推过
  /// dismiss 窗口与退场动画，等价于驱动的 12s 后观感。
  Future<void> elapseDriverScanWindow(WidgetTester tester) async {
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 3));
    await tester.pumpAndSettle();
  }

  /// 内联持久错误（key 寻址 —— 与同文案的瞬态 toast 消歧）。
  Finder consentInlineError() =>
      find.byKey(const ValueKey('consentInlineError'));

  /// 同文案反馈通道总数（toast + 内联）：拦截发生即 ≥1。
  Finder consentFeedbackText() => find.text('请先同意用户协议与隐私政策');

  Finder consentCheckboxes() => find.descendant(
        of: find.byType(CheckboxListTile),
        matching: find.byType(Checkbox),
      );

  bool tileFullyInViewport(WidgetTester tester, int index) {
    final rect = tester.getRect(find.byType(CheckboxListTile).at(index));
    return rect.top >= 0 && rect.bottom <= 600;
  }

  testWidgets(
      'F539 探针（机理钉死）：驱动式盲 tap 协议区 → ToS 勾上、Privacy 静默漏勾',
      (tester) async {
    final repo = _CountingAuthRepository();
    await pumpRegisterScreen(tester, repo);
    await fillFormDriverStyle(tester);

    // 几何事实：tile0 完整在视口内（命中→勾选），tile1 不完整在视口内
    // （中心点在折叠线下→定点 tap miss→状态不变、零告警）。
    expect(tileFullyInViewport(tester, 0), isTrue,
        reason: '前提：ToS tile 完整可见，驱动 tap 应命中',);
    expect(tileFullyInViewport(tester, 1), isFalse,
        reason: '前提：Privacy tile 中心在折叠线下，驱动 tap 静默 miss',);

    expect(tester.widget<Checkbox>(consentCheckboxes().at(0)).value ?? false,
        isTrue, reason: 'ToS 被盲 tap 勾上',);
    expect(tester.widget<Checkbox>(consentCheckboxes().at(1)).value ?? false,
        isFalse, reason: 'Privacy 因视口外静默保持未勾 —— 提交必被守卫拦截',);
    expect(repo.registerCalls, 0);
  });

  testWidgets(
      'F539 红→绿：consent 拦截后必须有滚动到因 + toast 消失后仍有持久内联错误',
      (tester) async {
    final repo = _CountingAuthRepository();
    await pumpRegisterScreen(tester, repo);
    await fillFormDriverStyle(tester); // Privacy 漏勾（见探针）

    await submitDriverStyle(tester);

    // 拦截生效：0 次网络调用。
    expect(repo.registerCalls, 0, reason: '协议未勾提交必须被拦截');

    // 即时反馈保留：瞬态 toast + 新增内联错误（同文案双通道）。
    expect(consentFeedbackText(), findsNWidgets(2),
        reason: '拦截瞬间应有 toast（既有）+ 内联错误（FIX-539 新增）',);

    // 修复面 1：协议区滚动入视口（红：不滚动；绿：两块 tile 均完整可见）。
    await tester.pumpAndSettle();
    expect(tileFullyInViewport(tester, 0), isTrue,
        reason: 'consent 拦截后 ToS tile 必须滚动入视口',);
    expect(tileFullyInViewport(tester, 1), isTrue,
        reason: 'consent 拦截后 Privacy tile 必须滚动入视口（正是它漏勾）',);

    // 修复面 2：toast 消失后仍有持久内联错误（红：零残留＝J-02 零反馈同型）。
    await elapseDriverScanWindow(tester);
    expect(consentInlineError(), findsOneWidget,
        reason: '瞬态 toast 消失后必须有持久内联错误指示，否则屏面零反馈',);
    expect(consentFeedbackText(), findsOneWidget,
        reason: '此窗口内同文案只剩内联一处 —— toast 已消失（瞬态通道时限的实证）',);
  });

  testWidgets('F539 红→绿：内联错误随补勾清除，补勾后提交真实到达 repository',
      (tester) async {
    final repo = _CountingAuthRepository();
    await pumpRegisterScreen(tester, repo);
    await fillFormDriverStyle(tester); // Privacy 漏勾

    await submitDriverStyle(tester); // 被拦截 → 滚动到因 + 内联错误
    await tester.pumpAndSettle();
    expect(repo.registerCalls, 0);

    // 恢复路径：两块 tile 现已滚入视口，补勾 Privacy（用户可循指示恢复）。
    await tester.tap(find.byType(CheckboxListTile).at(1));
    await tester.pump(const Duration(milliseconds: 250));
    expect(tester.widget<Checkbox>(consentCheckboxes().at(1)).value ?? false,
        isTrue,);

    // 内联错误随双勾清除（不残留旧错误吓用户）。
    expect(consentInlineError(), findsNothing,
        reason: '协议勾齐后内联错误必须清除',);

    // 再次提交 → 真实到达 repository（stub 失败路径出可见 snackbar）。
    await tester.tap(find.widgetWithText(SparkleButton, '注册'));
    await tester.pump();
    await tester.pumpAndSettle();
    expect(repo.registerCalls, 1, reason: '补勾后提交必须真实触发注册');
    expect(find.byType(SnackBar), findsOneWidget,
        reason: 'stub 失败路径必须有可见错误反馈',);
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
