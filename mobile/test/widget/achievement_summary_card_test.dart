import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/user_state_models.dart';
import 'package:sparkle/features/user/presentation/widgets/achievement_summary_card.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('AchievementSummaryCard renders unlock and progress summary', (
    tester,
  ) async {
    await tester.pumpWidget(
      testMaterialApp(home: Scaffold(
          body: AchievementSummaryCard(
            summary: UserStateFieldEnvelope(
              value: Stage35AchievementSummary(
                recentUnlocks: [
                  Stage35AchievementUnlock(
                    achievementId: 'streak-7',
                    name: '七日连学',
                    rarity: 'rare',
                    unlockedAt: DateTime(2026, 4, 21, 21, 0),
                  ),
                ],
                inProgressAchievements: [
                  Stage35AchievementProgress(
                    achievementId: 'deep-work-10',
                    name: '深度专注 10 次',
                    progress: 0.7,
                  ),
                ],
                totalAchievementScore: 18.5,
              ),
            ),
          ),
        ),),
    );

    expect(find.text('成就摘要'), findsOneWidget);
    expect(find.text('总成就分 18.5'), findsOneWidget);
    expect(find.text('七日连学'), findsOneWidget);
    expect(find.text('深度专注 10 次 70%'), findsOneWidget);
  });
}
