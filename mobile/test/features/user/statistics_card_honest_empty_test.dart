import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/presentation/widgets/statistics_card.dart';

import '../../shared/i18n_test_helper.dart';

/// V13-MAJORS M-02（诚实性红线）：驾驶舱/我的页「本周成长趋势」原先渲染一组
/// 硬编码 FlSpot(3,5,2,8,4,7,9)——当天注册、零学习行为的用户也看到完整
/// 7 天假曲线。本卡改为诚实空态（该卡无任何真实数据源），此测试钉住：
/// 不再渲染任何折线图。
///
/// A-SPEC2 top10 #8（选项 A 折叠保位）：假曲线修复后本卡成为首卡位永久空态
/// 死重，默认折叠为单行（标题 + 「接入后可见」次级文案），点击展开才显示
/// 诚实空态说明。本测试同时钉住：
/// 1) 默认折叠（单行高度，空态文案不可见）；2) 展开/收起交互；
/// 3) 展开后仍是诚实空态、无伪造曲线；4) 折叠态相对展开态的高度回收。
void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  group('StatisticsCard honest empty state', () {
    testWidgets('collapsed by default: header row only, empty hint hidden',
        (tester) async {
      await tester.pumpWidget(
        testMaterialApp(
          // Align 松开 Scaffold body 的紧约束，让卡片按内容自适应高度
          // （高度回收断言需要真实内容高度而非满屏）。
          home: const Scaffold(
            body: Align(
              alignment: Alignment.topCenter,
              child: StatisticsCard(),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.text('本周成长趋势'), findsOneWidget);
      expect(find.text('接入后可见'), findsOneWidget);
      expect(find.textContaining('还没有学习记录'), findsNothing);

      // 诚实红线：任何折线图（含伪造数据）都不得出现。
      expect(find.byType(LineChart), findsNothing);
    });

    testWidgets('tap expands to honest empty state, tap again collapses',
        (tester) async {
      await tester.pumpWidget(
        testMaterialApp(
          // Align 松开 Scaffold body 的紧约束，让卡片按内容自适应高度
          // （高度回收断言需要真实内容高度而非满屏）。
          home: const Scaffold(
            body: Align(
              alignment: Alignment.topCenter,
              child: StatisticsCard(),
            ),
          ),
        ),
      );
      await tester.pump();

      final collapsedHeight =
          tester.getSize(find.byType(StatisticsCard)).height;

      // 展开：出现诚实空态说明，仍无任何折线图。
      await tester.tap(find.text('本周成长趋势'));
      await tester.pumpAndSettle();

      expect(find.textContaining('还没有学习记录'), findsOneWidget);
      expect(find.byType(LineChart), findsNothing);

      final expandedHeight = tester.getSize(find.byType(StatisticsCard)).height;
      // 首屏高度回收断言：折叠态比展开态至少省出整个空态区（120px）量级。
      expect(expandedHeight - collapsedHeight, greaterThanOrEqualTo(100));

      // 收起：回到单行折叠态。
      await tester.tap(find.text('本周成长趋势'));
      await tester.pumpAndSettle();

      expect(find.textContaining('还没有学习记录'), findsNothing);
      expect(
        tester.getSize(find.byType(StatisticsCard)).height,
        collapsedHeight,
      );
      expect(tester.takeException(), isNull);
    });

    testWidgets('expanded empty state stays stable across rebuilds',
        (tester) async {
      await tester.pumpWidget(
        testMaterialApp(
          // Align 松开 Scaffold body 的紧约束，让卡片按内容自适应高度
          // （高度回收断言需要真实内容高度而非满屏）。
          home: const Scaffold(
            body: Align(
              alignment: Alignment.topCenter,
              child: StatisticsCard(),
            ),
          ),
        ),
      );
      await tester.pump();
      await tester.tap(find.text('本周成长趋势'));
      await tester.pumpAndSettle();
      await tester.pump();

      expect(find.textContaining('还没有学习记录'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
