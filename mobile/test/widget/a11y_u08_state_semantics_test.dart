import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
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
/// 全部用例真实泵入渲染树后断言语义节点（返工版）：断言手法按 Flutter
/// 语义装配的真实形态校准——
/// 1. 带 label 节点从「元素→renderObject.debugSemantics」枚举（与
///    bySemanticsLabel 同源），不走 rootPipelineOwner（测试下是空容器）；
/// 2. `Semantics(container:true)` 的子内容装配时**折叠合并**进容器节点
///    （label 以 \n 拼接、flags/actions 归并），故 label 断言用 RegExp
///    子串匹配，live/button 断言取合并节点自身；
/// 3. 语义 tap 用 `renderViews.first.owner.semanticsOwner.performAction`
///    （TalkBack/VoiceOver 激活的框架内等价路径，真 GoRouter 实证跳转）。
///
/// 钉住的不变式（对读屏的可感知性，不钉内部实现）：
/// - 等待族全程可感知：快路径有「加载中」唯一 label、骨架不贡献语义、
///   升格 stage 文案 liveRegion 自动播报并按间隔推进（WCAG 4.1.3）；
/// - 失败族/offline 横幅整块 liveRegion，标题+说明+可操作下一步在同一
///   播报块内（button 语义可达）——「error 可被辅助技术读出」；
/// - GJ03 current run 条：单节点 button（名字=可见文案）+ 语义 tap 可
///   触发 + 48 触控下限。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  final zh = AppLocalizationsZh();

  Widget shell(Widget child, [List<Override> overrides = const []]) =>
      ProviderScope(
        overrides: overrides,
        child: testMaterialApp(home: Scaffold(body: child)),
      );

  /// 当前语义树上「有可读 label」的节点（元素→debugSemantics 枚举，
  /// 与 semantics finder 同源；跨测试重建的 0/1/2 号系统节点无 label）。
  List<SemanticsNode> labeledNodes(WidgetTester tester) {
    final nodes = <SemanticsNode>{};
    for (final el in tester.allElements) {
      if (el is! RenderObjectElement) continue;
      final node = el.renderObject.debugSemantics;
      if (node != null && node.label.trim().isNotEmpty) nodes.add(node);
    }
    return nodes.toList();
  }

  /// 卸载树：取消 StagedSurfaceLoader 的 Timer，避免 pending timer。
  Future<void> unmount(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
  }

  group('U-08 · 等待族语义（StagedSurfaceLoader / U-06 渲染面）', () {
    testWidgets('快路径（<500ms）：骨架零语义贡献，播报「加载中」唯一 label',
        (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(shell(const StagedSurfaceLoader()));
      await tester.pump(const Duration(milliseconds: 100));

      // 骨架真实渲染（视觉不变）……
      expect(find.byType(SparkleSkeleton), findsNWidgets(3));
      // ……语义树上带可读 label 的节点恰 1 个：加载中（骨架不贡献任何
      // 语义节点，读屏用户在等待期拿到可理解播报而非噪音/空树）。
      final labeled = labeledNodes(tester);
      expect(labeled, hasLength(1));
      expect(labeled.single.label, zh.commonLoading);
      final loading = find.bySemanticsLabel(zh.commonLoading);
      // 快路径不抢播报（<500ms 是产品契约的零文案噪音段）。
      expect(
        tester.getSemantics(loading).flagsCollection.isLiveRegion,
        isFalse,
      );
      await unmount(tester);
      semantics.dispose();
    });

    testWidgets('升格（>500ms）：stage 文案进入播报块且 liveRegion，按间隔推进',
        (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(shell(const StagedSurfaceLoader()));
      await tester.pump(const Duration(milliseconds: 700));

      final stage1 = find.bySemanticsLabel(RegExp(zh.stateStagePreparing));
      expect(stage1, findsOneWidget);
      expect(
        tester.getSemantics(stage1).flagsCollection.isLiveRegion,
        isTrue,
        reason: 'stage 升格必须作为 liveRegion 自动播报（WCAG 4.1.3）',
      );

      await tester.pump(const Duration(milliseconds: 2600));
      expect(
        find.bySemanticsLabel(RegExp(zh.stateStageLoading)),
        findsOneWidget,
      );
      await unmount(tester);
      semantics.dispose();
    });

    testWidgets('compact 形态：快路径唯一 label，升格转 liveRegion',
        (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(
        shell(const StagedSurfaceLoader(compact: true, height: 72)),
      );
      await tester.pump(const Duration(milliseconds: 100));

      final labeled = labeledNodes(tester);
      expect(labeled, hasLength(1));
      expect(labeled.single.label, zh.commonLoading);

      await tester.pump(const Duration(milliseconds: 700));
      final stage1 = find.bySemanticsLabel(RegExp(zh.stateStagePreparing));
      expect(stage1, findsOneWidget);
      expect(
        tester.getSemantics(stage1).flagsCollection.isLiveRegion,
        isTrue,
      );
      await unmount(tester);
      semantics.dispose();
    });
  });

  group('U-08 · 失败族/状态横幅语义（SurfaceStateView / U-06 渲染面）', () {
    testWidgets(
        '可恢复错误：整块 liveRegion 播报（标题+说明+下一步同块）；重试可真实触发',
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

      // 失败块是一个 liveRegion 播报节点：success→error 的状态突变自动
      // 播报，标题+说明+动作同块可读（WCAG 4.1.3 / ACCESSIBILITY.md
      // 「error 可被辅助技术读出」）。
      final failure = find.bySemanticsLabel(RegExp('网络开小差了'));
      expect(failure, findsOneWidget);
      final node = tester.getSemantics(failure);
      expect(node.flagsCollection.isLiveRegion, isTrue);
      // 合并播报块携带 button 语义（可操作下一步动作在块内可达）。
      expect(node.flagsCollection.isButton, isTrue);
      expect(find.bySemanticsLabel(RegExp('内容没有丢失')), findsOneWidget);

      // 功能性触发：真实点按「重试」按钮（激活链路与 wt358 同款 finder）。
      final retryButton = find.widgetWithText(SparkleButton, zh.retry);
      expect(retryButton, findsOneWidget);
      await tester.tap(retryButton);
      expect(retried, isTrue);
      await unmount(tester);
      semantics.dispose();
    });

    testWidgets('offline 横幅：liveRegion 可读出且降级动作在块内可达',
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

      final banner = find.bySemanticsLabel(RegExp(zh.statePhaseOffline));
      expect(banner, findsOneWidget);
      expect(
        tester.getSemantics(banner).flagsCollection.isLiveRegion,
        isTrue,
      );
      // 横幅默认下一步（offline→retry「重试」）在播报块内语义可达。
      expect(find.bySemanticsLabel(RegExp(zh.retry)), findsOneWidget);
      await unmount(tester);
      semantics.dispose();
    });
  });

  group('U-08 · GJ03 控件（Today current run 条）', () {
    testWidgets(
        'run 进行中：单节点 button（名字=可见文案），语义 tap 真实触达 /chat，'
        '可点面满足 48 触控下限', (tester) async {
      final semantics = tester.ensureSemantics();
      // GoRouter 承载真实跳转：语义 tap（TalkBack/VoiceOver 激活路径）
      // 触发后断言落在 /chat——「辅助技术可完成」的功能性证据。
      final router = GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(
            // 与真实宿主同构：dashboard 屏在 Scaffold 内承载卡片
            // （InkWell 需 Material 祖先；内容 Column 需有界/可滚高度）。
            path: '/',
            builder: (context, state) => const Scaffold(
              body: SingleChildScrollView(
                child: TodayCockpitCard(),
              ),
            ),
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

      // excludeSemantics 单节点形态：名字=可见文案，恰一个语义节点。
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

      // 辅助技术激活路径：经视图语义 owner 下发 tap（performAction 即
      // 引擎侧 onSemanticsActionEvent 的入口；未接线会抛错/不跳转）。
      tester.binding.renderViews
          .map((rv) => rv.owner?.semanticsOwner)
          .whereType<SemanticsOwner>()
          .first
          .performAction(node.id, SemanticsAction.tap);
      await tester.pump();
      await tester.pump();
      expect(find.text('U08-CHAT-DEST'), findsOneWidget);
      await unmount(tester);
      semantics.dispose();
    });
  });
}
