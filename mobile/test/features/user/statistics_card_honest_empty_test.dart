import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/presentation/widgets/statistics_card.dart';

import '../../shared/i18n_test_helper.dart';

/// V13-MAJORS M-02（诚实性红线）：驾驶舱/我的页「本周成长趋势」原先渲染一组
/// 硬编码 FlSpot(3,5,2,8,4,7,9)——当天注册、零学习行为的用户也看到完整
/// 7 天假曲线。本卡改为诚实空态（该卡无任何真实数据源），此测试钉住：
/// 1) 空态文案在场；2) 不再渲染任何折线图。
void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  group('StatisticsCard honest empty state', () {
    testWidgets('renders header and honest empty hint, no fabricated curve',
        (tester) async {
      await tester.pumpWidget(
        testMaterialApp(
          home: const Scaffold(body: StatisticsCard()),
        ),
      );
      await tester.pump();

      expect(find.text('本周成长趋势'), findsOneWidget);
      expect(find.textContaining('还没有学习记录'), findsOneWidget);

      // 诚实红线：任何折线图（含伪造数据）都不得出现。
      expect(find.byType(LineChart), findsNothing);
    });

    testWidgets('empty state stays stable across rebuilds', (tester) async {
      await tester.pumpWidget(
        testMaterialApp(
          home: const Scaffold(body: StatisticsCard()),
        ),
      );
      await tester.pump();
      await tester.pump();

      expect(find.textContaining('还没有学习记录'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
