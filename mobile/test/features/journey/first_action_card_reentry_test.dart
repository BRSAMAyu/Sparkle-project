import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/session_refresh_service.dart';
import 'package:sparkle/features/journey/data/repositories/first_action_repository.dart';
import 'package:sparkle/features/journey/presentation/widgets/first_action_card.dart';
import 'package:sparkle/features/task/data/repositories/action_proposal_repository.dart';

import '../../shared/i18n_test_helper.dart';

/// V3-FIX-540 · 快车道 skip 后 FirstActionCard 间歇缺失（J-02 残留）红绿测试.
///
/// 实测背景（WT792-J02-SIM，R 腿 6 跑 4 miss）：goal 每次都已落库
/// （memory_goals=1 实锤），但 skip 落 /chat 或 /home 后首页卡片不浮现，
/// 直接卡 J-02 A1a ≤3min 全量达成。
///
/// 根因（代码亲证，5 个失效面叠加）：
/// 1. `firstActionStateProvider` 是非 autoDispose 的 FutureProvider ——
///    首次 fetch 后整个进程生命周期缓存；soft-wall dashboard（注册落地）
///    在 goal 落库**前**挂载卡片并 fetch（goal=null 被缓存），此后任何
///    重挂载都读旧缓存 → 卡片永不浮现；
/// 2. goal 写链（快车道 `_handleFastPathSubmit` / modeling `_finish`）
///    的 invalidate 级联均不含该 provider；
/// 3. N-4 session 失效清单 `sessionBoundProvidersProvider` 不含该
///    provider —— 用户态 goal 缓存跨登出/换号存活（违反其完整性约束）；
/// 4. dashboard 下拉刷新集 `_refreshHomeGrowthState` 不含该 provider；
/// 5. 卡内守门 `state?.goal == null → SizedBox.shrink` 把以上所有 stale
///    态静默渲染为「卡片不存在」（零布局影响语义吞噬了 staleness）。
///
/// 间歇性（4/6 miss 而非 6/6）与落点方差耦合：register 直落 soft-wall
/// dashboard（A2a 5/5）→ pre-goal fetch 被缓存 → 必 miss；auto-login 复活
/// 流程落「我的」tab（V3-FIX-540 落点分歧）→ dashboard 未 pre-goal 挂载 →
/// 首次 fetch 发生在落库后 → hit。
///
/// 红（修复前）：T1/T2 同一 ProviderContainer（= 同一进程）先以无 goal 态
/// 挂载卡片、卸载、再以「已落库」态重挂 —— 缓存不失效，卡片不浮现。
/// 绿（修复后）：provider autoDispose，重挂载重查服务端，goal 上卡。
void main() {
  setUp(() {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });
  tearDown(tearDownI18n);

  const userAGoalless = FirstActionState(); // 落库前：无 goal（soft-wall 态）
  const userGoalAfterFastPath = FirstActionState(
    goal: FirstActionGoal(
      goalId: 'g-540',
      title: '两周内做出可展示的比赛 demo',
      goalType: 'project',
    ),
  );

  // 生产同构拓扑：根 ProviderScope 常驻整个进程（app.dart 只有一个根
  // scope），快车道只换掉 dashboard 子树（persona/modeling 是 shell 外
  // 顶层路由）。测试复刻这一点——scope 跨挂载/卸载保持挂载，仅替换内容
  // 子树；riverpod 的 autoDispose 卸载经 vsync（下一帧 scope.build）执行，
  // 所以离开 dashboard 后要多 pump 数帧让容器真正释放缓存。
  Widget scopeOf(ProviderContainer container, Widget child) =>
      UncontrolledProviderScope(
        container: container,
        child: testMaterialApp(
          theme: ThemeData.light()
              .copyWith(extensions: [SparkleThemeExtension.light()]),
          home: Scaffold(
            body: SingleChildScrollView(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: child,
              ),
            ),
          ),
        ),
      );

  testWidgets('T1 快车道竞态：goal 落库前缓存了空态，落库后同进程重回 dashboard 卡片必须浮现',
      (tester) async {
    // 脚本化服务端时间线（fake 时序，不依赖真机）：
    // T0 soft-wall 挂载 → fetch 返回无 goal；T1 快车道提交（服务端落库）；
    // T2 skip 重回 dashboard → 重挂载必须重查。
    final scripted = _ScriptedRepository(currentState: userAGoalless);
    final container = ProviderContainer(
      overrides: [firstActionRepositoryProvider.overrideWithValue(scripted)],
    );
    addTearDown(container.dispose);
    Future<void> pumpDashboard() async {
      await tester.pumpWidget(
        scopeOf(container, const FirstActionCard()),
      );
    }

    // ── T0：注册后 soft-wall dashboard 挂载（pre-goal）──
    await pumpDashboard();
    await tester.pump();
    await tester.pump();
    // 无 goal：卡内守门 shrink（soft-wall 面正常表现）
    expect(find.text('生成我的第一步'), findsNothing);
    expect(find.text(userGoalAfterFastPath.goal!.title), findsNothing);

    // ── 离开 dashboard（go 顶层 onboarding 路由 → dashboard 子树卸载，
    //    根 scope 常驻）──
    await tester.pumpWidget(
      scopeOf(container, const SizedBox.shrink()),
    );
    await tester.pump();
    await tester.pump();

    // ── T1：goal 已落库（服务端真源翻转；memory_goals=1 的测试等价面）──
    scripted.currentState = userGoalAfterFastPath;

    // ── T2：skip 落 /home（或 /chat→home tab）→ dashboard 重挂载 ──
    // 修复前：provider 进程级缓存命中空态 → 卡片不浮现（实测 4/6 miss）。
    await pumpDashboard();
    await tester.pump();
    await tester.pump();

    expect(
      find.text(userGoalAfterFastPath.goal!.title),
      findsOneWidget,
      reason: 'goal 已落库后同进程重回 dashboard，FirstActionCard 必须重查'
          '服务端并浮现（V3-FIX-540 实测 6 跑 4 miss 的回归面）',
    );
    expect(find.text('生成我的第一步'), findsOneWidget);
    // 重查痕迹：fetchState 恰好两次（soft-wall 一次 + 重回一次）
    expect(scripted.fetchCount, 2);
  });

  testWidgets('T2 引擎节流毒化：pre-goal fetch 失败（503 打盹）不得把错误缓存成永久缺席',
      (tester) async {
    // PX2 log 实测「服务器正在打盹」节流窗口：soft-wall 首查失败 → 修复前
    // AsyncError 同样进程级缓存 → 重回后卡片缺席（miss 的第二形态）。
    final scripted = _ScriptedRepository(
      currentState: userAGoalless,
      error: Exception('503 服务器正在打盹'),
    );
    final container = ProviderContainer(
      overrides: [firstActionRepositoryProvider.overrideWithValue(scripted)],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(
      scopeOf(container, const FirstActionCard()),
    );
    await tester.pump();
    await tester.pump();
    expect(scripted.fetchCount, 1);

    await tester.pumpWidget(
      scopeOf(container, const SizedBox.shrink()),
    );
    await tester.pump();
    await tester.pump();

    // 节流窗口过去 + goal 已落库
    scripted
      ..error = null
      ..currentState = userGoalAfterFastPath;

    await tester.pumpWidget(
      scopeOf(container, const FirstActionCard()),
    );
    await tester.pump();
    await tester.pump();

    expect(
      find.text(userGoalAfterFastPath.goal!.title),
      findsOneWidget,
      reason: '首查失败不能把卡片永久渲染成缺席——重挂载必须重查',
    );
    expect(scripted.fetchCount, 2);
  });

  test('T3 N-4 完整性约束：firstActionStateProvider 必须登记进 session 失效清单', () {
    // sessionBoundProvidersProvider 的完整性约束（见其注释 ⚠️ N-4）：持有
    // 用户态数据的长生命周期 provider 都必须登记——first-action 投影持有
    // 用户 goal，缺席即跨账号泄漏面（auto-login→登出→注册流程实测存在）。
    final container = ProviderContainer();
    addTearDown(container.dispose);

    expect(
      container.read(sessionBoundProvidersProvider),
      contains(firstActionStateProvider),
      reason: 'first-action 状态是用户态数据：登出/换号必须失效，'
          '否则上一账号 goal 面跨会话存活（N-4 家族）',
    );
  });
}

/// 脚本化假仓库（测试夹具，非生产行为）：fetchState 返回可翻转的服务端
/// 时间线状态，并可注入节流失败；只覆盖 provider 缓存语义，不碰网络面。
class _ScriptedRepository extends FirstActionRepository {
  _ScriptedRepository({
    required FirstActionState currentState,
    Exception? error,
  })  : _currentState = currentState,
        _error = error,
        super(_FakeApiClient(), _FakeProposalRepository());

  FirstActionState _currentState;
  Exception? _error;
  int fetchCount = 0;

  set currentState(FirstActionState value) => _currentState = value;

  set error(Exception? value) => _error = value;

  @override
  Future<FirstActionState?> fetchState() async {
    fetchCount++;
    final error = _error;
    if (error != null) {
      throw error;
    }
    return _currentState;
  }
}

class _FakeApiClient extends Fake implements ApiClient {}

class _FakeProposalRepository extends Fake implements ActionProposalRepository {}
