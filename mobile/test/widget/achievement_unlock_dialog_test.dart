import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_unlock_dialog.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

AchievementUnlockEvent _buildEvent() => AchievementUnlockEvent(
      achievementId: 'mirofish_first_simulation',
      name: '仿真开场',
      rarity: AchievementRarity.common,
      unlockedAt: DateTime(2026, 3, 28, 12),
      rewardPreview: const <String>['解锁高光样式'],
      gloryLines: const <String>['你第一次把知识点拉进了真实讨论现场。'],
      surfacePreview: const <String>['学习场景模拟'],
    );

void main() {
  testWidgets('achievement unlock dialog closes before share callback',
      (tester) async {
    var shared = 0;

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: FilledButton(
                onPressed: () => showDialog<void>(
                  context: context,
                  builder: (_) => AchievementUnlockDialog(
                    event: _buildEvent(),
                    onShare: () {
                      shared += 1;
                    },
                  ),
                ),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();
    expect(find.text('仿真开场'), findsOneWidget);

    await tester.ensureVisible(find.text('分享'));
    await tester.tap(find.text('分享'));
    await tester.pumpAndSettle();

    expect(shared, 1);
    expect(find.text('仿真开场'), findsNothing);
  });

  testWidgets('achievement unlock dialog closes from close action',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: FilledButton(
                onPressed: () => showDialog<void>(
                  context: context,
                  builder: (_) => AchievementUnlockDialog(
                    event: _buildEvent(),
                  ),
                ),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();
    expect(find.text('仿真开场'), findsOneWidget);

    await tester.ensureVisible(find.text('关闭'));
    await tester.tap(find.text('关闭'));
    await tester.pumpAndSettle();

    expect(find.text('仿真开场'), findsNothing);
  });

  testWidgets('achievement unlock dialog compact view rewards closes once',
      (tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await tester.binding.setSurfaceSize(const Size(280, 640));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    var viewed = 0;

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: FilledButton(
                onPressed: () => showDialog<void>(
                  context: context,
                  builder: (_) => AchievementUnlockDialog(
                    event: _buildEvent(),
                    onViewRewards: () {
                      viewed += 1;
                    },
                  ),
                ),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();

    final rewardsFinder = find.text('查看奖励');
    await tester.ensureVisible(rewardsFinder);
    await tester.tap(rewardsFinder, warnIfMissed: false);
    await tester.pumpAndSettle();

    expect(viewed, 1);
    expect(find.text('仿真开场'), findsNothing);
  });
}
