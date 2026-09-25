import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/state/staged_loading.dart';
import 'package:sparkle/core/state/surface_state.dart';
import 'package:sparkle/core/state/surface_state_view.dart';
import 'package:sparkle/features/home/presentation/providers/today_cockpit_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/today_cockpit_card.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

import '../shared/i18n_test_helper.dart';

/// U-08（Accessibility 全链）· 状态链与 GJ03 控件的 Semantics 树结构性断言。
///
/// 钉住的事实（不靠 mock 冒充：全部真实泵入渲染树后断言语义节点）：
/// 1. 等待族（U-06 渲染面）全程可被辅助技术读出——快路径有「加载中」
///    label，升格 stage 文案转 liveRegion 自动播报（WCAG 4.1.3）；
/// 2. 装饰性骨架不进语义树（SparkleSkeleton / 遗留 _SkeletonBox），
///    读屏用户等待期拿到可理解的播报而非空节点噪音；
/// 3. 失败族 / offline-reconnecting-partial 横幅整块 liveRegion，标题与
///    「可操作下一步」按钮（button 角色 + 名字）语义可达——错误可被
///    辅助技术读出（ACCESSIBILITY.md 验收行）；
/// 4. GJ03（Today → action）current run 条：单节点按钮语义（名字=可见
///    文案 + tap 动作）且满足 48 触控下限。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  final zh = AppLocalizationsZh();

  Widget shell(Widget child, [List<Override> overrides = const []]) =>
      ProviderScope(
        overrides: overrides,
        child: testMaterialApp(home: Scaffold(body: child)),
      );

  /// 遍历真实语义树计节点数（rootSemanticsNode 起深搜）。
  int countSemanticsNodes(WidgetTester tester) {
    final owner = tester.binding.rootPipelineOwner.semanticsOwner;
    final root = owner?.rootSemanticsNode;
    if (root == null) return 0;
    var count = 0;
    bool visit(SemanticsNode node) {
      count++;
      node.visitChildren(visit);
      return true;
    }

    visit(root);
    return count;
  }

  /// 卸载树：取消 StagedSurfaceLoader 的 Timer，避免 pending timer。
  Future<void> unmount(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  }

  group('U-08 · 等待族语义（StagedSurfaceLoader / U-06 渲染面）', () {
    testWidgets('快路径（<500ms）：骨架退出语义树，播报「加载中」单节点',
        (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(shell(const StagedSurfaceLoader()));
      await tester.pump(const Duration(milliseconds: 100));

      // 骨架真实渲染（视觉不变）……
      expect(find.byType(SparkleSkeleton), findsNWidgets(3));
      // ……但整棵语义树只有 1 个节点：加载中 label（装饰性骨架整体退出）。
      expect(countSemanticsNodes(tester), 1);
      final loading = find.bySemanticsLabel(zh.commonLoading);
      expect(loading, findsOneWidget);
      // 快路径不抢播报（<500ms 是产品契约的零文案噪音段）。
      expect(
        tester.getSemantics(loading).flagsCollection.isLiveRegion,
        isFalse,
      );
      await unmount(tester);
      semantics.dispose();
    });

    testWidgets('升格（>500ms）：stage 文案 liveRegion 播报并按间隔推进',
        (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(shell(const StagedSurfaceLoader()));
      await tester.pump(const Duration(milliseconds: 700));

      final stage1 = find.bySemanticsLabel(zh.stateStagePreparing);
      expect(stage1, findsOneWidget);
      // liveRegion 挂在 loader 根节点（整块等待面自动播报），不在文案子节点。
      expect(
        tester
            .getSemantics(find.byType(StagedSurfaceLoader))
            .flagsCollection
            .isLiveRegion,
        isTrue,
        reason: 'stage 升格必须作为 liveRegion 自动播报（WCAG 4.1.3）',
      );

      await tester.pump(const Duration(milliseconds: 2600));
      expect(find.bySemanticsLabel(zh.stateStageLoading), findsOneWidget);
      await unmount(tester);
      semantics.dispose();
    });

    testWidgets('compact 形态：同为单节点，升格转 liveRegion', (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(
        shell(
          const StagedSurfaceLoader(compact: true, height: 72),
        ),
      );
      await tester.pump(const Duration(milliseconds: 100));
      expect(find.bySemanticsLabel(zh.commonLoading), findsOneWidget);
      expect(countSemanticsNodes(tester), 1);

      await tester.pump(const Duration(milliseconds: 700));
      expect(find.bySemanticsLabel(zh.stateStagePreparing), findsOneWidget);
      expect(
        tester
            .getSemantics(find.byType(StagedSurfaceLoader))
            .flagsCollection
            .isLiveRegion,
        isTrue,
      );
      await unmount(tester);
      semantics.dispose();
    });
  });

  group('U-08 · 失败族/状态横幅语义（SurfaceStateView / U-06 渲染面）', () {
    testWidgets('可恢复错误：整块 liveRegion；标题可读；「重试」按钮语义可达',
        (tester) async {
      final semantics = tester.ensureSemantics();
      var retried = false;
      await tester.pumpWidget(
        shell(
          SurfaceStateView(
            state: const SurfaceState(
              SurfacePhase.errorRecoverable,
              message: '网络开小差了',
              detail: '内容没有丢失',
            ),
            onRetry: () => retried = true,
          ),
        ),
      );
      await tester.pump();

      // 整块容器 liveRegion：success→error 的状态突变自动播报（WCAG 4.1.3）。
      expect(
        tester
            .getSemantics(find.byType(SurfaceStateView))
            .flagsCollection
            .isLiveRegion,
        isTrue,
      );
      // 标题（自定义 message 优先）真实可读。
      expect(find.bySemanticsLabel('网络开小差了'), findsOneWidget);
      // 可操作下一步：button 角色 + 名字「重试」，辅助技术可触发。
      final retry = find.bySemanticsLabel(zh.retry);
      expect(retry, findsOneWidget);
      expect(tester.getSemantics(retry).flagsCollection.isButton, isTrue);
      await tester.tap(retry);
      expect(retried, isTrue);
      await unmount(tester);
      semantics.dispose();
    });

    testWidgets('offline 横幅：liveRegion + 降级动作语义可达（非阻断但可读出）',
        (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(
        shell(
          SurfaceStateView(
            state: const SurfaceState(SurfacePhase.offline),
            onRetry: () {},
          ),
        ),
      );
      await tester.pump();

      expect(
        tester
            .getSemantics(find.byType(SurfaceStateView))
            .flagsCollection
            .isLiveRegion,
        isTrue,
      );
      expect(find.bySemanticsLabel(zh.statePhaseOffline), findsOneWidget);
      // 横幅自带可解释动作（offline 默认下一步=retry「重试」），button 角色可达。
      final retry = find.bySemanticsLabel(zh.retry);
      expect(retry, findsOneWidget);
      expect(tester.getSemantics(retry).flagsCollection.isButton, isTrue);
      await unmount(tester);
      semantics.dispose();
    });
  });

  group('U-08 · GJ03 控件（Today current run 条）', () {
    testWidgets(
        'run 进行中：单节点按钮语义（名字=可见文案），语义 tap 真实触达 /chat，'
        '可点面满足 48 触控下限', (tester) async {
      final semantics = tester.ensureSemantics();
      // GoRouter 承载真实跳转：语义 tap（TalkBack/VoiceOver 激活路径）
      // 触发后断言落在 /chat——「辅助技术可完成」的功能性证据。
      final router = GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(
            path: '/',
            builder: (context, state) => const TodayCockpitCard(),
          ),
          GoRoute(
            path: '/chat',
            builder: (context, state) =>
                const Scaffold(body: Text('U08-CHAT-DEST')),
          ),
        ],
      );
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayCockpitProvider.overrideWithValue(
              const TodayCockpitVm(
                mode: TodayCockpitMode.active,
                action: TodayCockpitAction.openTasks,
                runIsActive: true,
              ),
            ),
          ],
          child: testMaterialApp(routerConfig: router),
        ),
      );
      await tester.pump();

      final strip = find.bySemanticsLabel(zh.todayCockpitRunOngoing);
      expect(strip, findsOneWidget);
      final node = tester.getSemantics(strip);
      expect(node.flagsCollection.isButton, isTrue);

      // 触控下限：DS.touchTargetMinSize（48）——run 条可点面不小于触控档。
      final stripContainer = find
          .ancestor(
            of: find.text(zh.todayCockpitRunOngoing),
            matching: find.byType(Container),
          )
          .first;
      expect(
        tester.getSize(stripContainer).height,
        greaterThanOrEqualTo(48),
      );

      // 辅助技术激活路径：经 SemanticsOwner 下发 tap（TalkBack/VoiceOver
      // 的激活等价物；未接线会抛错/不跳转）——跳转落在 /chat。
      tester.binding.rootPipelineOwner.semanticsOwner!
          .performAction(node.id, SemanticsAction.tap);
      await tester.pump();
      await tester.pump();
      expect(find.text('U08-CHAT-DEST'), findsOneWidget);
      await unmount(tester);
      semantics.dispose();
    });
  });
}
