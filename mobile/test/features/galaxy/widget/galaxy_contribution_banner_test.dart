import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/data/models/user_galaxy_contribution.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy_contribution_banner.dart';

void main() {
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
        const MaterialApp(
          home: Scaffold(
            body: GalaxyContributionBanner(
              isDarkMode: true,
              stats: stats,
            ),
          ),
        ),
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
        const MaterialApp(
          home: Scaffold(
            body: GalaxyContributionBanner(
              isDarkMode: true,
              stats: UserGalaxyContribution.empty,
            ),
          ),
        ),
      );

      expect(find.text('开始你的第一次学习'), findsOneWidget);
      expect(find.text('0 个节点'), findsNothing);
    });
  });
}
