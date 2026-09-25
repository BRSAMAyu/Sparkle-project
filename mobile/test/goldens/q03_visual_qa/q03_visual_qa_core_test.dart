/// Q-03 Autonomous Visual QA — 核心 journey 屏逐屏真实渲染截图（wt401）。
///
/// 截图证据：`Q03_VISUAL_CAPTURE=true flutter test --update-goldens test/goldens/q03_visual_qa/`
/// 落 PNG 到 v3-output/WT401-Q03-VISUAL/evidence/；本测试任何模式下都跑
/// 布局探针（RenderFlex 溢出 / 截断候选 / 越界 widget），异常即失败（红测先行）。
library;

import 'package:flutter_riverpod/flutter_riverpod.dart' show Override;
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart'
    show AuthState;
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

import 'q03_harness.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    await q03LoadRealFont();
    await q03EnsureTestStorage();
  });

  tearDownAll(() async {
    await q03FlushProbeReports('core');
  });

  group('Q03 visual QA: core journey screens (standard profile)', () {
    testWidgets('C01 /home dashboard: loading + default + empty + error',
        (tester) async {
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = false);

      // —— loading / default：同一 harness，先短泵捕 loading，再稳定捕 default。
      final harness = await pumpQ03App(tester);
      await harness.go(tester, '/home', settlePumps: 1);
      await harness.capture(tester, 'C01_home', 'loading');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'C01_home', 'default');
      await harness.dispose(tester);

      // —— empty：空 dashboard 状态（新用户首目标空态），provider 真实状态。
      final emptyHarness = await pumpQ03App(
        tester,
        extraOverrides: <Override>[
          dashboardProvider.overrideWith(
            (ref) => _Q03DashboardNotifier(
              DashboardState(
                weather: WeatherData(type: 'sunny', condition: 'clear'),
                flame:
                    FlameData(level: 1, brightness: 0, todayFocusMinutes: 0),
                sprint: null,
                nextActions: const [],
                cognitive: CognitiveData(status: 'empty'),
              ),
            ),
          ),
        ],
      );
      await emptyHarness.go(tester, '/home');
      await emptyHarness.capture(tester, 'C01_home', 'empty');
      await emptyHarness.dispose(tester);

      // —— error：provider 真实 error 态（断网重试文案）。
      final errorHarness = await pumpQ03App(
        tester,
        extraOverrides: [
          dashboardProvider.overrideWith(
            (ref) => _Q03DashboardNotifier(DashboardState.error('网络不可用')),
          ),
        ],
      );
      await errorHarness.go(tester, '/home');
      await errorHarness.capture(tester, 'C01_home', 'error');
      await errorHarness.dispose(tester);
    });

    testWidgets('C02 /galaxy: loading + default', (tester) async {
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = false);

      final harness = await pumpQ03App(tester);
      await harness.go(tester, '/galaxy', settlePumps: 1);
      await harness.capture(tester, 'C02_galaxy', 'loading');
      await harness.pumpFrames(tester, 12);
      await harness.capture(tester, 'C02_galaxy', 'default');
      await harness.dispose(tester);
    });

    testWidgets('C03 /chat: default + fixture conversation', (tester) async {
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = false);

      final harness = await pumpQ03App(tester);
      // V3-FIX-53（wt400 修复中）涉及真后端工具流：本卡 chat 态一律由
      // fixture（initial 消息）驱动，不依赖后端流。
      await harness.go(tester, '/chat');
      await harness.capture(tester, 'C03_chat', 'default');
      await harness.pumpFrames(tester, 30);
      await harness.go(
        tester,
        '/chat',
        extra: <String, dynamic>{
          'initial_ai_message':
              '昨天的错题「二次函数判别式」我已经分析过了。你想先看解题思路，还是先做一道类似的练习？',
          'initial_user_message': '继续复习数学错题',
        },
      );
      await harness.pumpFrames(tester, 6);
      await harness.capture(tester, 'C03_chat', 'fixture_conversation');
      await harness.dispose(tester);
    });

    testWidgets('C04 /community: loading + default', (tester) async {
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = false);

      final harness = await pumpQ03App(tester);
      await harness.go(tester, '/community', settlePumps: 1);
      await harness.capture(tester, 'C04_community', 'loading');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'C04_community', 'default');
      await harness.dispose(tester);
    });

    testWidgets('C05 /profile: default', (tester) async {
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = false);

      final harness = await pumpQ03App(tester);
      await harness.go(tester, '/profile');
      await harness.capture(tester, 'C05_profile', 'default');
      await harness.dispose(tester);
    });

    testWidgets('C06 /login: default (public surface)', (tester) async {
      final harness = await pumpQ03App(
        tester,
        authState: AuthState(),
      );
      await harness.pumpFrames(tester);
      await harness.capture(tester, 'C06_login', 'default');
      await harness.dispose(tester);
    });

    testWidgets('C07 /onboarding/persona: default', (tester) async {
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = false);

      final harness = await pumpQ03App(tester);
      await harness.go(tester, '/onboarding/persona');
      await harness.capture(tester, 'C07_persona_onboarding', 'default');
      await harness.dispose(tester);
    });

    testWidgets('C08 /errors: loading + default', (tester) async {
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = false);

      final harness = await pumpQ03App(tester);
      await harness.go(tester, '/errors', settlePumps: 1);
      await harness.capture(tester, 'C08_errors', 'loading');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'C08_errors', 'default');
      await harness.dispose(tester);
    });

    testWidgets('C09 /errors/new: default', (tester) async {
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = false);

      final harness = await pumpQ03App(tester);
      await harness.go(tester, '/errors/new');
      await harness.capture(tester, 'C09_error_new', 'default');
      await harness.dispose(tester);
    });

    testWidgets('C10 /goals/new: default', (tester) async {
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = false);

      final harness = await pumpQ03App(tester);
      await harness.go(tester, '/goals/new');
      await harness.capture(tester, 'C10_goal_new', 'default');
      await harness.dispose(tester);
    });

    testWidgets('C11 /plans: loading + default', (tester) async {
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = false);

      final harness = await pumpQ03App(tester);
      await harness.go(tester, '/plans', settlePumps: 1);
      await harness.capture(tester, 'C11_plans', 'loading');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'C11_plans', 'default');
      await harness.dispose(tester);
    });

    testWidgets('C12 /review?mode=today: default', (tester) async {
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = false);

      final harness = await pumpQ03App(tester);
      await harness.go(tester, '/review?mode=today', settlePumps: 10);
      await harness.capture(tester, 'C12_review', 'default');
      await harness.dispose(tester);
    });

    testWidgets('C13 /notification-center: loading + default', (tester) async {
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = false);

      final harness = await pumpQ03App(tester);
      await harness.go(tester, '/notification-center', settlePumps: 1);
      await harness.capture(tester, 'C13_notification_center', 'loading');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'C13_notification_center', 'default');
      await harness.dispose(tester);
    });
  });
}

class _Q03DashboardNotifier extends DashboardNotifier {
  _Q03DashboardNotifier(DashboardState initialState)
      : super(_Q03UnusedDashboardRepository()) {
    state = initialState;
  }

  @override
  Future<void> fetchData() async {}
}

class _Q03UnusedDashboardRepository extends DashboardRepository {
  _Q03UnusedDashboardRepository() : super(_Q03NoopApiClient());

  @override
  Future<Map<String, dynamic>> getDashboardStatus() async => <String, dynamic>{};

  @override
  Future<Map<String, dynamic>> getPredictiveDashboard() async =>
      <String, dynamic>{};
}

class _Q03NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
