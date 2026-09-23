import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/data/models/user_galaxy_contribution.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy_contribution_banner.dart';
import '../../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  group('GalaxyContributionBanner', () {
    testWidgets('starts animated counts from zero before counting up', (
      tester,
    ) async {
      const stats = UserGalaxyContribution(
        firstActivationCount: 32,
        errorRepairedCount: 8,
        conversationUpdatedCount: 15,
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: GalaxyContributionBanner(
              isDarkMode: true,
              stats: stats,
            ),
          ),),
      );

      expect(find.text('0 个节点'), findsNWidgets(3));

      await tester.pump(const Duration(milliseconds: 700));

      expect(find.text('32 个节点'), findsOneWidget);
      expect(find.text('8 个节点'), findsOneWidget);
      expect(find.text('15 个节点'), findsOneWidget);
    });

    testWidgets('shows onboarding copy instead of zero-node metrics when empty',
        (
      tester,
    ) async {
      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: GalaxyContributionBanner(
              isDarkMode: true,
              stats: UserGalaxyContribution.empty,
            ),
          ),),
      );

      expect(find.text('开始你的第一次学习'), findsOneWidget);
      expect(find.text('0 个节点'), findsNothing);
    });

    testWidgets('error form renders the visible micro copy (EE-G7)', (
      tester,
    ) async {
      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: const GalaxyContributionBanner.error(
              isDarkMode: true,
            ),
          ),),
      );

      // error 态有可见形：单行「贡献数据暂不可见」，不再静默消失。
      expect(find.text('贡献数据暂不可见'), findsOneWidget);
      // 异常对象本身无路可入 UI：横幅不接 error 对象。
      expect(find.textContaining('Exception'), findsNothing);
    });

    testWidgets('error form keeps the loading-form height (no layout jump)',
        (tester) async {
      Future<double> measure(Widget banner) async {
        await tester.pumpWidget(
          testMaterialApp(
            home: Scaffold(
              body: Align(
                alignment: Alignment.topCenter,
                child: banner,
              ),
            ),
          ),
        );
        final box = tester.renderObject<RenderBox>(
          find.byType(GalaxyContributionBanner),
        );
        return box.size.height;
      }

      final loadingHeight = await measure(
        const GalaxyContributionBanner.loading(isDarkMode: true),
      );
      final errorHeight = await measure(
        const GalaxyContributionBanner.error(isDarkMode: true),
      );

      expect(errorHeight, loadingHeight);
      expect(errorHeight, greaterThan(0));
    });

    testWidgets('error form is not tappable and opens no detail sheet', (
      tester,
    ) async {
      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: const GalaxyContributionBanner.error(
              isDarkMode: true,
            ),
          ),),
      );

      final inkWell = tester.widget<InkWell>(find.byType(InkWell));
      expect(inkWell.onTap, isNull);
    });
  });
}
