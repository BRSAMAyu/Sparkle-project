import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/experience/presentation/widgets/goal_detail_snapshot_card.dart';
import 'package:sparkle/features/home/presentation/widgets/multi_goal_dashboard_card.dart';
import 'package:sparkle/features/home/presentation/widgets/today_cockpit_card.dart';
import 'package:sparkle/features/insights/presentation/widgets/return_case_file_card.dart';

import '../../../shared/i18n_test_helper.dart';
import '../dashboard_test_harness.dart';

/// U-05 首页 L2：growthSections 收敛为「仅突出 Primary Action / Why /
/// Stuck / Run」的行动脊柱后，次要卡（returnCaseFile / goalDetailSnapshot /
/// multiGoalDashboard 等）在首页必须只有一个实例——slot 系统的
/// CollapsibleSlot 版本。回归锚点：修复前这些卡在 growthSections 原样渲染
/// 一次、slot 系统又渲染一次（全展开基线下 find 会命中 2 个）。
void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Dashboard growth sections L2 single-instance', () {
    testWidgets(
      'secondary cards render exactly once (slot system), cockpit stays the '
      'single primary card',
      (tester) async {
        await initializeDashboardTestEnvironment();
        await tester.binding.setSurfaceSize(const Size(390, 4200));
        addTearDown(() => tester.binding.setSurfaceSize(null));
        await tester.pumpWidget(
          buildDashboardTestHarness(
            // 全展开基线：修复前该基线下次要卡会出现「原样 + slot」双实例，
            // 本用例钉住单实例契约。
            size: const Size(390, 4200),
            extraOverrides: [dashboardSlotConfigAllExpandedOverride()],
          ),
        );
        for (var i = 0; i < 10; i++) {
          await tester.pump(const Duration(milliseconds: 100));
        }

        // 唯一主行动卡与其唯一 primary CTA。
        expect(find.byType(TodayCockpitCard), findsOneWidget);
        expect(
          find.byKey(const ValueKey('today-cockpit-primary-cta')),
          findsOneWidget,
        );

        // 次要卡单实例（U-05 前为双实例）。
        expect(find.byType(ReturnCaseFileCard), findsOneWidget);
        expect(find.byType(GoalDetailSnapshotCard), findsOneWidget);
        expect(find.byType(MultiGoalDashboardCard), findsOneWidget);
      },
    );
  });
}
