/// Q-03 Autonomous Visual QA — 视觉 A/B 缺陷回归守卫（红测先行，wt401）。
///
/// 四个缺陷各一条守卫测试（默认恒跑，无 golden 写入）：
///  G1. 发布动态心情选择条 390w 不溢出（base：RenderFlex overflow 63px）；
///  G2. 连胜日历今日格子不建双 ticker（base：SingleTickerProviderStateMixin
///      断言 → ErrorWidget）；
///  G3. 分享海报覆盖层在源屏销毁后重建不炸（base：deactivated ancestor）；
///  G4. 星图顶部模式面板与统计/贡献横幅互不遮挡（base：sibling Positioned
///      top:48 列 vs top:112 面板重叠）。
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/share_poster_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/features/community/presentation/screens/create_post_screen.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy_contribution_banner.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/goal_world_graph_mini_panel.dart';

import '../../shared/i18n_test_helper.dart';
import 'q03_harness.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(setUpI18nForTesting);

  group('Q03 fix guards (red-first regressions)', () {
    testWidgets('G1 mood selector row has no overflow at 390x844',
        (tester) async {
      tester.view.devicePixelRatio = q03DevicePixelRatio;
      tester.view.physicalSize = q03PhysicalSize;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        ProviderScope(
          child: testMaterialApp(home: const CreatePostScreen()),
        ),
      );
      for (var i = 0; i < 8; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }

      expect(
        tester.takeException(),
        isNull,
        reason: '心情选择条在 390w 标准档溢出（base 记录 RenderFlex +63px）',
      );

      // V3-FIX-65（wt410 审查）：零溢出≠可达——chip 被裁剪/不可滚容器吞掉时
      // takeException 照样为 null。守卫升格为行为可达锁：第 5 chip 必须可滚
      // 入视口、完整落位、且 tap 真实命中（选中态生效）。
      const fifthMoodLabel = '📚';
      final fifthChip = find.text(fifthMoodLabel);
      expect(fifthChip, findsOneWidget, reason: '第 5 心情 chip 必须在树内');

      final horizontalScrollable = find
          .byWidgetPredicate(
            (widget) =>
                widget is Scrollable &&
                (widget.axisDirection == AxisDirection.left ||
                    widget.axisDirection == AxisDirection.right),
          )
          .first;
      await tester.scrollUntilVisible(
        fifthChip,
        50,
        scrollable: horizontalScrollable,
      );
      await tester.pump(const Duration(milliseconds: 100));

      final chipRect = tester.getRect(fifthChip);
      final screenSize = tester.getSize(find.byType(CreatePostScreen));
      expect(
        chipRect.left >= 0 &&
            chipRect.right <= screenSize.width &&
            chipRect.top >= 0 &&
            chipRect.bottom <= screenSize.height,
        isTrue,
        reason: '滚动后第 5 心情 chip($chipRect) 必须完整落在视口'
            '(${screenSize.width}x${screenSize.height})内——被裁剪容器吞掉即红',
      );

      await tester.tap(fifthChip);
      await tester.pump(const Duration(milliseconds: 300));
      final chipContainer = tester.widget<AnimatedContainer>(
        find
            .ancestor(of: fifthChip, matching: find.byType(AnimatedContainer))
            .first,
      );
      expect(
        (chipContainer.decoration as BoxDecoration?)?.color,
        DS.brandPrimary.withValues(alpha: 0.12),
        reason: '第 5 心情 chip 点选后必须呈现选中态——tap 被 rail/裁剪面截获即红',
      );
    });

    testWidgets('G2 streak calendar today cell uses no second ticker',
        (tester) async {
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = false);

      final harness = await pumpQ03App(tester);
      await harness.go(tester, '/achievements/streak');
      // 日历格入场动画 Future.delayed 至 1500ms 封顶，泵过它。
      await harness.pumpFrames(tester, 20);
      expect(
        tester.takeException(),
        isNull,
        reason: '今日格子用 SingleTickerProviderStateMixin 建了两个 ticker',
      );
      await harness.dispose(tester);
    });

    testWidgets('G3 poster overlay build survives source screen disposal',
        (tester) async {
      q03MockPlatformChannels();

      // 产品路径是用户动作触发（非 build 相位）：用按钮发起生成。
      await tester.pumpWidget(
        testMaterialApp(
          home: Builder(
            builder: (context) => TextButton(
              key: const ValueKey('q03-trigger'),
              onPressed: () {
                unawaited(
                  SharePosterService().generatePoster(
                    context,
                    const UniversalSharePayload(
                      contentType: ShareableContentType.achievement,
                      resourceId: 'q03-guard',
                      title: '视觉守卫',
                    ),
                  ),
                );
              },
              child: const Text('生成'),
            ),
          ),
        ),
      );
      await tester.pump();
      await tester.tap(find.byKey(const ValueKey('q03-trigger')));
      await tester.pump(); // 覆盖层插入并首次构建（此刻 context 仍存活）。

      // 生成窗口期内离开源页（根 Navigator/Overlay 存活，仅 home 子树
      // 替换 → 源 context 失活，覆盖层条目仍挂着并被重入）。
      await tester.pumpWidget(
        testMaterialApp(home: const Scaffold(body: SizedBox.shrink())),
      );
      // pump 60ms 冲 40ms 延迟 timer，再补一帧给第二个 endOfFrame。
      await tester.pump(const Duration(milliseconds: 60));
      await tester.pump(const Duration(milliseconds: 16));

      final exception = tester.takeException();
      // 兜底冲刷：让 in-flight 服务链自然走到边界回收。
      await tester.runAsync(() async {
        await Future<void>.delayed(const Duration(milliseconds: 120));
      });

      expect(
        exception,
        isNull,
        reason: '海报覆盖层 builder 在源 context 失活后重入 '
            '（Theme.of(deactivated)），根覆盖层整屏红',
      );
    });

    testWidgets('G4 galaxy mode panel does not overlap stats column',
        (tester) async {
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = false);

      final harness = await pumpQ03App(tester);
      await harness.go(tester, '/galaxy');
      await harness.pumpFrames(tester, 12);

      final panelFinder = find.byType(GoalWorldGraphMiniPanel);
      final bannerFinder = find.byType(GalaxyContributionBanner);
      expect(panelFinder, findsOneWidget);
      expect(bannerFinder, findsOneWidget);

      final panelRect = tester.getRect(panelFinder);
      final bannerRect = tester.getRect(bannerFinder);
      final overlap = panelRect.intersect(bannerRect);
      expect(
        overlap.width <= 0 || overlap.height <= 0,
        isTrue,
        reason: '星图模式面板($panelRect)与贡献横幅($bannerRect)重叠 '
            '(${overlap.width}x${overlap.height})，顶部控件互相遮挡',
      );

      // V3-FIX-65（wt410 审查）：wt401 修后面板/横幅已同为 Column 兄弟——
      // flow 布局下「不相交」构造性恒真，仅对改回兄弟 Positioned 的回归有效。
      // 把修复设计本身锁进守卫：两者必须共享同一个 Column 祖先（同一条纵向
      // 流），有人拆出兄弟 Positioned 即红。
      final panelColumns = find
          .ancestor(of: panelFinder, matching: find.byType(Column))
          .evaluate()
          .toSet();
      final bannerColumns = find
          .ancestor(of: bannerFinder, matching: find.byType(Column))
          .evaluate()
          .toSet();
      expect(
        panelColumns.intersection(bannerColumns).isNotEmpty,
        isTrue,
        reason: '模式面板与统计/横幅必须同挂一条纵向流（wt401 修复设计）——'
            '拆回兄弟 Positioned 即回归',
      );
      await harness.dispose(tester);
    });
  });
}
