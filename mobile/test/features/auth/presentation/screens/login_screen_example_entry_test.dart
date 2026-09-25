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

/// O5（wt436）红绿测试：登录屏必须有「体验一个示例」用户入口，且点击走
/// 既有 guest/example 链路（GJ02 已验证的 upgrade-guest 同源路径）。
///
/// J-01（wt398）实测：`体验示例/示例体验/tryExample` 全库 0 命中；产品内
/// 无任何示例体验声明入口，唯一 demo 体验需编译期 `--dart-define=DEMO_MODE=true`
/// （开发者知识依赖）。FIRST_3_MINUTES Screen 1 目标设计为
/// 「开始我的目标（Primary）/ 体验一个示例（Secondary）」双入口分叉。
///
/// 红（修复前）：登录屏无「体验一个示例」入口；点击无从谈起（guest 0 次调用）。
/// 绿（修复后）：次级入口可见（不喧宾夺主），点击触发既有 loginAsGuest 链路。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<_CountingAuthRepository> pumpLoginScreen(WidgetTester tester) async {
    // 拉高视口保证全部入口同屏可达（登录/访客/示例）。
    tester.view
      ..physicalSize = const Size(800, 2400)
      ..devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final repo = _CountingAuthRepository();
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
    return repo;
  }

  testWidgets('O5：登录屏存在「体验一个示例」入口且点击走既有 guest/example 链路', (tester) async {
    final repo = await pumpLoginScreen(tester);

    final entry = find.text('体验一个示例');
    expect(
      entry,
      findsOneWidget,
      reason: 'O5：FIRST_3_MINUTES Screen 1 分叉点缺失——登录屏必须有'
          '「体验一个示例」次级入口（可见但不喧宾夺主）',
    );

    await tester.ensureVisible(entry);
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(entry, warnIfMissed: false);
    await tester.pump();
    await tester.pumpAndSettle();

    // 红（修复前）：0 —— 入口缺失，示例链路不可达；绿（修复后）：1。
    expect(
      repo.guestCalls,
      1,
      reason: 'O5：示例入口必须走既有 guest/example 链路（不造新链路）',
    );
  });

  testWidgets('O5：示例入口不抢占主 CTA——登录与访客按钮仍各自独立存在', (tester) async {
    await pumpLoginScreen(tester);

    expect(find.widgetWithText(SparkleButton, '登录'), findsOneWidget);
    expect(find.widgetWithText(SparkleButton, '以访客身份继续'), findsOneWidget);
    // 示例入口存在但为次级形态（TextButton，非主/次 SparkleButton 变体），
    // 不与既有主 CTA 争位。
    expect(find.widgetWithText(SparkleButton, '体验一个示例'), findsNothing);
  });
}

class _CountingAuthRepository extends AuthRepository {
  _CountingAuthRepository() : super(_UnusedApiClient(), _MemoryTokenStorage());

  int guestCalls = 0;

  @override
  Future<bool> isLoggedIn() async => false;

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
