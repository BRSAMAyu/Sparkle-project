import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/widgets/universal_share_bottom_sheet.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/features/achievement/data/repositories/achievement_repository.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/screens/achievement_list_screen.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/data/repositories/seed_library_repository.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_library_detail_screen.dart';
import 'package:sparkle/features/visual_elements/presentation/widgets/visual_element_preview_dialog.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

void main() {
  group('J4 frontend closure', () {
    testWidgets('achievement list filters switch without blanking or overflow',
        (tester) async {
      final repo = _FakeAchievementRepository();

      await _pumpApp(
        tester,
        child: const AchievementListScreen(),
        overrides: [
          achievementRepositoryProvider.overrideWithValue(repo),
        ],
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1200));

      final scrollable = find.byType(Scrollable).first;
      await tester.scrollUntilVisible(
        find.text('里程碑速通'),
        300,
        scrollable: scrollable,
      );

      expect(find.text('里程碑速通'), findsOneWidget);
      expect(find.text('连胜第 7 天'), findsOneWidget);

      await tester.tap(find.text('已解锁'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.text('里程碑速通'), findsOneWidget);
      expect(find.text('连胜第 7 天'), findsOneWidget);
      expect(find.text('探索新节点'), findsNothing);

      await tester.tap(find.text('进行中'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.text('探索新节点'), findsOneWidget);
      expect(find.text('里程碑速通'), findsNothing);

      await tester.tap(find.text('里程碑'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.text('里程碑速通'), findsOneWidget);
      expect(find.text('连胜第 7 天'), findsNothing);

      await tester.tap(find.text('全部'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.scrollUntilVisible(
        find.text('探索新节点'),
        300,
        scrollable: scrollable,
      );
      expect(find.text('里程碑速通'), findsOneWidget);
      expect(find.text('连胜第 7 天'), findsOneWidget);
      expect(find.text('探索新节点'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('seed library detail renders content and item preview stably',
        (tester) async {
      final repo = _FakeSeedLibraryRepository();

      await _pumpApp(
        tester,
        child: const SeedLibraryDetailScreen(libraryId: 'seed-lib-1'),
        overrides: [
          seedLibraryRepositoryProvider.overrideWithValue(repo),
        ],
      );

      await tester.pumpAndSettle();

      expect(find.text('验收知识库'), findsOneWidget);
      expect(find.text('用于验证种子库详情与正文显示'), findsOneWidget);
      expect(find.text('验收测试原则'), findsOneWidget);
      expect(find.textContaining('先跑主链，再补证据'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('visual element preview handles long content without overflow',
        (tester) async {
      var equipCount = 0;
      final element = VisualElementModel(
        id: 'visual-1',
        name: '超长名称超长名称超长名称超长名称超长名称超长名称',
        description: '这是一个用于验证视觉元素预览弹窗在长标题和长描述下仍然稳定显示的测试描述文本。',
        elementType: VisualElementType.effect,
        rarity: VisualElementRarity.legendary,
        unlockSource: VisualElementUnlockSource.achievement,
        isDefault: false,
        sortOrder: 1,
        isUnlocked: true,
      );

      await _pumpApp(
        tester,
        child: VisualElementPreviewDialog(
          element: element,
          isUnlocked: true,
          onEquip: () => equipCount += 1,
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));

      expect(find.textContaining('超长名称'), findsOneWidget);
      expect(find.text('装备'), findsOneWidget);
      await tester.tap(find.text('装备'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));

      expect(equipCount, 1);
      expect(tester.takeException(), isNull);
    });

    testWidgets('universal share sheet keeps template and action controls available',
        (tester) async {
      final tempFile = File(
        '${Directory.systemTemp.path}/j4_share_preview.png',
      )..writeAsBytesSync(const <int>[137, 80, 78, 71]);

      await _pumpApp(
        tester,
        child: UniversalShareBottomSheet(
          payload: const UniversalSharePayload(
            contentType: ShareableContentType.achievement,
            resourceId: 'ach-1',
            title: '速通大师',
            subtitle: '已完成 7 天连续打卡',
          ),
          onGenerateCard: (_) async => tempFile,
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      expect(find.text('星空'), findsOneWidget);
      expect(find.text('简约'), findsOneWidget);
      final shareSheetScroll = find.descendant(
        of: find.byType(UniversalShareBottomSheet),
        matching: find.byType(Scrollable),
      );
      await tester.scrollUntilVisible(
        find.text('分享文案'),
        240,
        scrollable: shareSheetScroll.first,
      );
      expect(find.text('分享文案'), findsOneWidget);

      await tester.scrollUntilVisible(
        find.text('分享到社群'),
        240,
        scrollable: shareSheetScroll.first,
      );
      expect(find.text('分享到社群'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}

Future<void> _pumpApp(
  WidgetTester tester, {
  required Widget child,
  List<Override> overrides = const [],
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        localizationsDelegates: const [
          ...AppLocalizations.localizationsDelegates,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
        home: Scaffold(body: child),
      ),
    ),
  );
}

class _FakeSeedLibraryRepository extends SeedLibraryRepository {
  _FakeSeedLibraryRepository() : super(_UnusedApiClient());

  final SeedLibrary _library = SeedLibrary(
    id: 'seed-lib-1',
    name: '验收知识库',
    description: '用于验证种子库详情与正文显示',
    category: LibraryCategory.teachingContent,
    visibility: LibraryVisibility.official,
    language: 'zh',
    isOfficial: true,
    isFeatured: true,
    usageCount: 12,
    itemCount: 1,
    subscriberCount: 3,
    createdAt: DateTime(2026, 3),
    updatedAt: DateTime(2026, 3),
    userRatingAvg: 4.8,
    userRatingCount: 5,
  );

  @override
  Future<SeedLibrary> getLibrary(String id) async => _library;

  @override
  Future<PaginatedResponse<UserLibrarySubscription>> getMySubscriptions({
    int page = 1,
    int pageSize = 20,
    bool? isEnabled,
  }) async =>
      PaginatedResponse<UserLibrarySubscription>(
        items: const [],
        total: 0,
        page: 1,
        pageSize: 20,
        totalPages: 1,
      );

  @override
  Future<PaginatedResponse<SeedItem>> listLibraryItems(
    String libraryId, {
    ItemType? itemType,
    String? subject,
    DifficultyLevel? difficultyLevel,
    String? search,
    int page = 1,
    int pageSize = 20,
  }) async =>
      PaginatedResponse<SeedItem>(
        items: [
          SeedItem(
            id: 'item-1',
            libraryId: libraryId,
            itemType: ItemType.knowledge,
            title: '验收测试原则',
            content: '先跑主链，再补证据，最后回写关单结果。',
            subject: '工程管理',
            difficultyLevel: DifficultyLevel.beginner,
            isActive: true,
            createdAt: DateTime(2026, 3),
            updatedAt: DateTime(2026, 3),
          ),
        ],
        total: 1,
        page: 1,
        pageSize: 20,
        totalPages: 1,
      );
}

class _FakeAchievementRepository extends AchievementRepository {
  _FakeAchievementRepository() : super(_UnusedApiClient());

  @override
  Future<AchievementListResponse> getAchievements({
    String? category,
    AchievementRarity? rarity,
    bool includeHidden = false,
    bool includeInactive = false,
  }) async {
    final now = DateTime(2026, 3, 25);
    return AchievementListResponse(
      achievements: [
        AchievementWithProgress(
          achievement: AchievementModel(
            id: 'ach-milestone',
            name: '里程碑速通',
            description: '用于验证里程碑筛选和双列网格的稳定性',
            type: AchievementType.milestone,
            rarity: AchievementRarity.rare,
            category: 'milestone',
            createdAt: now,
            updatedAt: now,
          ),
          isUnlocked: true,
          progressPercentage: 100,
          userProgress: UserAchievementProgress(
            achievementId: 'ach-milestone',
            progress: 1,
            progressValue: 1,
            progressTarget: 1,
            unlockedAt: now,
          ),
        ),
        AchievementWithProgress(
          achievement: AchievementModel(
            id: 'ach-streak',
            name: '连胜第 7 天',
            description: '用于验证已解锁筛选不空白',
            type: AchievementType.streak,
            rarity: AchievementRarity.common,
            category: 'streak',
            createdAt: now,
            updatedAt: now,
          ),
          isUnlocked: true,
          progressPercentage: 100,
          userProgress: UserAchievementProgress(
            achievementId: 'ach-streak',
            progress: 1,
            progressValue: 7,
            progressTarget: 7,
            unlockedAt: now,
          ),
        ),
        AchievementWithProgress(
          achievement: AchievementModel(
            id: 'ach-progress',
            name: '探索新节点',
            description: '用于验证进行中筛选仍能显示数据',
            type: AchievementType.nodeExplore,
            rarity: AchievementRarity.epic,
            category: 'exploration',
            createdAt: now,
            updatedAt: now,
          ),
          isUnlocked: false,
          progressPercentage: 60,
          userProgress: UserAchievementProgress(
            achievementId: 'ach-progress',
            progress: 0.6,
            progressValue: 3,
            progressTarget: 5,
          ),
        ),
      ],
      totalAchievements: 3,
      totalUnlocked: 2,
      categories: const {
        'milestone': 1,
        'streak': 1,
        'exploration': 1,
      },
    );
  }

  @override
  Future<AchievementStats> getAchievementStats() async => AchievementStats(
        totalAchievements: 3,
        unlockedCount: 2,
        unlockedPercentage: 66.7,
        commonCount: 1,
        rareCount: 1,
        epicCount: 1,
        legendaryCount: 0,
        hiddenFound: 0,
        currentStreak: 7,
        totalPhotons: 120,
      );

  @override
  Future<StreakStats> getStreakStats() async => StreakStats(
        currentStreak: 7,
        maxStreak: 14,
        longestStreak: 14,
        freezeCharges: 1,
        maxFreezeCharges: 3,
        totalCheckinDays: 18,
        lastActivityDate: DateTime(2026, 3, 25),
      );

  @override
  Future<GalaxySkinListResponse> getGalaxySkins() async =>
      GalaxySkinListResponse(skins: const []);

  @override
  Future<List<UserTitle>> getTitles() async => const [];

  @override
  Future<SparkContract?> getContractStatus() async => null;
}


class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
