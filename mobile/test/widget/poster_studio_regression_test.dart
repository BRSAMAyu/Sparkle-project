import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/share_poster_service.dart';
import 'package:sparkle/features/achievement/data/repositories/achievement_repository.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/cognitive/data/models/curiosity_capsule_model.dart';
import 'package:sparkle/features/cognitive/data/repositories/capsule_repository.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/user/presentation/screens/poster_studio_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import 'package:sparkle/shared/entities/user_model.dart';

void main() {
  group('poster studio regression', () {
    testWidgets('poster studio stays stable on compact width', (tester) async {
      await tester.binding.setSurfaceSize(const Size(320, 760));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await _pumpApp(
        tester,
        child: const PosterStudioScreen(),
        overrides: [
          currentUserProvider.overrideWith((ref) => _fakeUser()),
          achievementProvider.overrideWith(
            (ref) => _StaticAchievementNotifier(_fakeAchievementState()),
          ),
          planListProvider.overrideWith(
            (ref) => _StaticPlanNotifier(_fakePlanState()),
          ),
          capsuleProvider.overrideWith(
            (ref) => _StaticCapsuleNotifier(_fakeCapsules()),
          ),
        ],
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1200));

      expect(find.text('海报工坊'), findsOneWidget);
      expect(find.text('海报类型'), findsOneWidget);
      final scrollable = find.byType(Scrollable).first;
      await tester.scrollUntilVisible(
        find.text('重新生成预览'),
        200,
        scrollable: scrollable,
      );
      expect(find.text('重新生成预览'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets(
      'share poster baseline guard disables debug baselines and restores them',
      (tester) async {
        expect(debugPaintBaselinesEnabled, isFalse);

        bool? observedInside;
        final result =
            await SharePosterService.runWithoutDebugPaintGuides(() async {
          observedInside = debugPaintBaselinesEnabled;
          return 42;
        });

        expect(result, 42);
        expect(observedInside, isFalse);
        expect(debugPaintBaselinesEnabled, isFalse);
      },
    );
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

UserModel _fakeUser() => UserModel(
      id: 'user-1',
      username: 'aurora_user',
      email: 'aurora@example.com',
      flameLevel: 8,
      flameBrightness: 0.87,
      depthPreference: 0.6,
      curiosityPreference: 0.7,
      isActive: true,
      createdAt: DateTime(2026, 1, 1),
      updatedAt: DateTime(2026, 3, 29),
      nickname: '极光征服者超长昵称版本',
    );

AchievementState _fakeAchievementState() => AchievementState(
      achievements: [
        AchievementWithProgress(
          achievement: AchievementModel(
            id: 'ach-legend',
            name: '连胜极光征服者',
            type: AchievementType.streak,
            rarity: AchievementRarity.legendary,
            description: '用于海报工坊回归测试的成就描述。',
            createdAt: DateTime(2026, 1, 1),
            updatedAt: DateTime(2026, 3, 29),
          ),
          isUnlocked: true,
          progressPercentage: 100,
          userProgress: UserAchievementProgress(
            achievementId: 'ach-legend',
            progress: 1,
            progressValue: 30,
            progressTarget: 30,
            unlockedAt: DateTime(2026, 3, 28),
          ),
        ),
      ],
      stats: AchievementStats(
        totalAchievements: 12,
        unlockedCount: 8,
        unlockedPercentage: 66.7,
        commonCount: 2,
        rareCount: 3,
        epicCount: 2,
        legendaryCount: 1,
        hiddenFound: 0,
        currentStreak: 7,
        totalPhotons: 1200,
      ),
      streakStats: StreakStats(
        currentStreak: 7,
        maxStreak: 12,
        longestStreak: 12,
        freezeCharges: 1,
        maxFreezeCharges: 3,
        totalCheckinDays: 28,
      ),
      titles: [
        UserTitle(
          titleId: 'title-1',
          titleName: 'aurora-conqueror',
          titleDisplay: '极光征服者',
          unlockedAt: DateTime(2026, 3, 28),
          isEquipped: true,
        ),
      ],
    );

PlanListState _fakePlanState() => PlanListState(
      plans: [
        PlanModel(
          id: 'plan-1',
          userId: 'user-1',
          name: '超长计划标题用于验证海报工坊卡片不会在紧凑宽度下溢出布局',
          description: '把大目标拆成清晰任务并稳定推进。',
          type: PlanType.growth,
          dailyAvailableMinutes: 90,
          masteryLevel: 0.58,
          progress: 0.64,
          isActive: true,
          createdAt: DateTime(2026, 2, 1),
          updatedAt: DateTime(2026, 3, 29),
          subject: '跨学科项目',
        ),
      ],
      activePlans: [
        PlanModel(
          id: 'plan-1',
          userId: 'user-1',
          name: '超长计划标题用于验证海报工坊卡片不会在紧凑宽度下溢出布局',
          description: '把大目标拆成清晰任务并稳定推进。',
          type: PlanType.growth,
          dailyAvailableMinutes: 90,
          masteryLevel: 0.58,
          progress: 0.64,
          isActive: true,
          createdAt: DateTime(2026, 2, 1),
          updatedAt: DateTime(2026, 3, 29),
          subject: '跨学科项目',
        ),
      ],
    );

List<CuriosityCapsuleModel> _fakeCapsules() => [
      CuriosityCapsuleModel(
        id: 'capsule-1',
        title: '超长灵感胶囊标题用于验证海报工坊在小屏上依然稳定',
        content: '如果把复盘和计划写成一张海报，哪些信息最值得保留？',
        isRead: false,
        createdAt: DateTime(2026, 3, 29, 9),
        relatedSubject: '设计系统',
        depthLevel: 'deep',
      ),
    ];

class _StaticAchievementNotifier extends AchievementNotifier {
  _StaticAchievementNotifier(this._value)
      : super(_FakeAchievementRepository(), _FakeRef()) {
    state = _value;
  }

  final AchievementState _value;

  @override
  Future<void> loadInitialData() async {
    state = _value;
  }
}

class _StaticPlanNotifier extends PlanNotifier {
  _StaticPlanNotifier(this._value) : super(_FakePlanRepository(), _FakeRef()) {
    state = _value;
  }

  final PlanListState _value;

  @override
  Future<void> loadPlans({PlanType? type}) async {
    state = _value;
  }

  @override
  Future<void> loadActivePlans() async {
    state = _value;
  }

  @override
  Future<void> refresh() async {
    state = _value;
  }
}

class _StaticCapsuleNotifier extends CapsuleNotifier {
  _StaticCapsuleNotifier(this._value) : super(_FakeCapsuleRepository()) {
    state = AsyncValue.data(_value);
  }

  final List<CuriosityCapsuleModel> _value;

  @override
  Future<void> fetchTodayCapsules() async {
    state = AsyncValue.data(_value);
  }
}

class _FakeAchievementRepository extends AchievementRepository {
  _FakeAchievementRepository() : super(_UnusedApiClient());
}

class _FakePlanRepository extends PlanRepository {
  _FakePlanRepository() : super(_UnusedApiClient());
}

class _FakeCapsuleRepository extends CapsuleRepository {
  _FakeCapsuleRepository() : super(_UnusedApiClient());
}

class _FakeRef implements Ref {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
