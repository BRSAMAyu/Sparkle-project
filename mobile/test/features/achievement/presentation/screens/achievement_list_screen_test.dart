import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/achievement/data/repositories/achievement_repository.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/screens/achievement_list_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import '../../../../shared/i18n_test_helper.dart';

GoRouter _buildRouter() {
  final router = GoRouter(
    initialLocation: '/achievements',
    routes: [
      GoRoute(
        path: '/achievements',
        builder: (context, state) => const AchievementListScreen(),
      ),
    ],
  );
  addTearDown(router.dispose);
  return router;
}

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('achievement list shows onboarding empty state', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          achievementRepositoryProvider.overrideWithValue(
            _FakeAchievementRepository(),
          ),
        ],
        child: MaterialApp.router(
          theme: AppThemes.lightTheme,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: const Locale('zh'),
          routerConfig: _buildRouter(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 700));

    await tester.scrollUntilVisible(
      find.text('去创建今日任务'),
      300,
      scrollable: find.byType(Scrollable).first,
    );

    expect(find.text('还没有解锁任何成就'), findsOneWidget);
    expect(find.text('去创建今日任务'), findsOneWidget);
    expect(find.text('尚未开始'), findsWidgets);
  });

  testWidgets('achievement list has RefreshIndicator', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          achievementRepositoryProvider.overrideWithValue(
            _FakeAchievementRepository(),
          ),
        ],
        child: MaterialApp.router(
          theme: AppThemes.lightTheme,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: const Locale('zh'),
          routerConfig: _buildRouter(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 700));

    expect(find.byType(RefreshIndicator), findsOneWidget);
  });
}

class _FakeAchievementRepository extends AchievementRepository {
  _FakeAchievementRepository() : super(_NoopApiClient());

  @override
  Future<AchievementListResponse> getAchievements({
    String? category,
    AchievementRarity? rarity,
    bool includeHidden = false,
    bool includeInactive = false,
  }) async =>
      AchievementListResponse(
        achievements: const <AchievementWithProgress>[],
        totalAchievements: 0,
        totalUnlocked: 0,
        categories: const <String, dynamic>{},
      );

  @override
  Future<AchievementStats> getAchievementStats() async => AchievementStats(
        totalAchievements: 0,
        unlockedCount: 0,
        unlockedPercentage: 0,
        commonCount: 0,
        rareCount: 0,
        epicCount: 0,
        legendaryCount: 0,
        hiddenFound: 0,
        currentStreak: 0,
        totalPhotons: 0,
      );

  @override
  Future<StreakStats> getStreakStats() async => StreakStats(
        currentStreak: 0,
        maxStreak: 0,
        longestStreak: 0,
        freezeCharges: 0,
        maxFreezeCharges: 3,
        totalCheckinDays: 0,
      );

  @override
  Future<GalaxySkinListResponse> getGalaxySkins() async =>
      GalaxySkinListResponse(
        skins: const <GalaxySkin>[],
        equippedSkinId: null,
      );

  @override
  Future<List<UserTitle>> getTitles() async => const <UserTitle>[];

  @override
  Future<SparkContract?> getContractStatus() async => null;
}

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}
