/// B-04 · V3 视觉基线截图采集（wt667）——9 canonical states × 3 viewport。
///
/// 采集（写 PNG）：
/// ```
/// B04_VISUAL_CAPTURE=true B04_BUILD_SHA8=$(git rev-parse --short=8 HEAD) \
///   flutter test --update-goldens test/goldens/b04_visual_baseline/
/// ```
/// 复验（比对 PNG 不变）：
/// ```
/// B04_VISUAL_CAPTURE=true B04_BUILD_SHA8=<同上> \
///   flutter test test/goldens/b04_visual_baseline/
/// ```
/// 两模式都跑布局探针（溢出/截断候选）；探针异常即测试失败。
///
/// canonical 状态注册表：scripts/devtools/visual_baseline/states.py；
/// 命名：naming.py GBNF；PNG 落 v3-output/B-04/screenshots/<批次>/。
/// state 与入口的裁决注记（/plans 为真实目标库、chat 引用块为 fixture
/// 注入）见 states.py 同名条目与本目录 REPORT。
library;

import 'package:flutter_test/flutter_test.dart';

import '../../goldens/q03_visual_qa/q03_harness.dart';
import 'b04_harness.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    await q03LoadRealFont();
    await q03EnsureTestStorage();
    b04InstallTolerantComparator();
  });

  tearDownAll(() async {
    await q03FlushProbeReports('b04');
  });

  for (final batch in b04ViewportBatches) {
    group('B-04 visual baseline [${batch.dirName}]', () {
      testWidgets('onboarding/persona_start (new_user)', (tester) async {
        // 新注册账号首登：onboarding 未完成语义。
        final harness = await pumpB04App(
          tester,
          batch,
          onboardingCompleted: false,
        );
        await harness.go(tester, '/onboarding/persona');
        await b04Capture(
          tester,
          harness,
          batch,
          batch.fileName(
            surface: 'onboarding',
            state: 'persona_start',
            persona: 'new_user',
          ),
        );
        await harness.dispose(tester);
      });

      testWidgets('home/main (demo_data)', (tester) async {
        final harness = await pumpB04App(tester, batch);
        await harness.go(tester, '/home');
        await harness.pumpFrames(tester, 10);
        await b04Capture(
          tester,
          harness,
          batch,
          batch.fileName(
            surface: 'home',
            state: 'main',
            persona: 'demo_data',
          ),
        );
        await harness.dispose(tester);
      });

      testWidgets('chat/history_citations (demo_data)', (tester) async {
        final harness = await pumpB04App(tester, batch, chatCitations: true);
        await harness.go(tester, '/chat');
        await harness.pumpFrames(tester, 18);
        // 引用块 fixture 必须真实进树（消息正文 + 引用条标题），否则
        // canonical 状态名不符实——直接红。
        b04SeedCitationMessage(harness);
        await harness.pumpFrames(tester, 6);
        expect(find.textContaining('韦达定理反向构造'), findsWidgets);
        expect(find.textContaining('微分中值定理'), findsWidgets);
        await b04Capture(
          tester,
          harness,
          batch,
          batch.fileName(
            surface: 'chat',
            state: 'history_citations',
            persona: 'demo_data',
          ),
        );
        await harness.dispose(tester);
      });

      testWidgets('goal/library_main (demo_data)', (tester) async {
        // 裁决：真实目标库主视图是 /plans（SprintScreen，demo 数据在库）；
        // /goals 无列表路由，目标详情 /goals/{id} 需真后端（无 demo 分支）。
        final harness = await pumpB04App(tester, batch);
        await harness.go(tester, '/plans');
        await harness.pumpFrames(tester, 10);
        await b04Capture(
          tester,
          harness,
          batch,
          batch.fileName(
            surface: 'goal',
            state: 'library_main',
            persona: 'demo_data',
          ),
        );
        await harness.dispose(tester);
      });

      testWidgets('task/library_main (demo_data)', (tester) async {
        final harness = await pumpB04App(tester, batch);
        await harness.go(tester, '/tasks');
        await harness.pumpFrames(tester, 10);
        await b04Capture(
          tester,
          harness,
          batch,
          batch.fileName(
            surface: 'task',
            state: 'library_main',
            persona: 'demo_data',
          ),
        );
        await harness.dispose(tester);
      });

      testWidgets('memory/panel_main (demo_data)', (tester) async {
        // memory 链路无 demo 分支：canned API（契约形状 JSON）+ 真实
        // fromJson 解析 + 真实渲染管线。
        final harness = await pumpB04App(tester, batch, memoryCannedApi: true);
        await harness.go(tester, '/memory');
        await harness.pumpFrames(tester, 10);
        await b04Capture(
          tester,
          harness,
          batch,
          batch.fileName(
            surface: 'memory',
            state: 'panel_main',
            persona: 'demo_data',
          ),
        );
        await harness.dispose(tester);
      });

      testWidgets('galaxy/tree_expanded (demo_data)', (tester) async {
        final harness = await pumpB04App(tester, batch);
        await harness.go(tester, '/galaxy');
        await harness.pumpFrames(tester, 12);
        // 关掉首引可见的「知识星确认」对话卡，让节点树本体入镜
        // （tree_expanded 语义）；对话框不存在时（状态演进）直接采集。
        final laterFinder = find.text('稍后再看');
        if (laterFinder.evaluate().isNotEmpty) {
          await tester.tap(laterFinder.first, warnIfMissed: false);
          await harness.pumpFrames(tester, 6);
        }
        await b04Capture(
          tester,
          harness,
          batch,
          batch.fileName(
            surface: 'galaxy',
            state: 'tree_expanded',
            persona: 'demo_data',
          ),
        );
        await harness.dispose(tester);
      });

      testWidgets('profile/main (demo_data)', (tester) async {
        final harness = await pumpB04App(tester, batch);
        await harness.go(tester, '/profile');
        await harness.pumpFrames(tester);
        await b04Capture(
          tester,
          harness,
          batch,
          batch.fileName(
            surface: 'profile',
            state: 'main',
            persona: 'demo_data',
          ),
        );
        await harness.dispose(tester);
      });

      testWidgets('settings/main (demo_data)', (tester) async {
        final harness = await pumpB04App(tester, batch);
        await harness.go(tester, '/profile/settings');
        await harness.pumpFrames(tester);
        await b04Capture(
          tester,
          harness,
          batch,
          batch.fileName(
            surface: 'settings',
            state: 'main',
            persona: 'demo_data',
          ),
        );
        await harness.dispose(tester);
      });
    });
  }
}
