import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/achievement/data/repositories/achievement_repository.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

void main() {
  late _FakeAchievementRepository achievementRepository;
  late _FakeAuthNotifier authNotifier;
  late ProviderContainer container;

  setUp(() {
    achievementRepository = _FakeAchievementRepository();
    authNotifier = _FakeAuthNotifier();
    container = ProviderContainer(
      overrides: [
        achievementRepositoryProvider.overrideWithValue(achievementRepository),
        authProvider.overrideWith((ref) => authNotifier),
      ],
    );
  });

  tearDown(() {
    container.dispose();
  });

  test('equipSkin refreshes skins and current user state', () async {
    container.read(achievementProvider);
    await Future<void>.delayed(Duration.zero);

    final notifier = container.read(achievementProvider.notifier);
    final result = await notifier.equipSkin('legendary_anniversary');

    expect(result, isTrue);
    expect(
        achievementRepository.equipGalaxySkinCalls, ['legendary_anniversary']);
    expect(achievementRepository.getGalaxySkinsCalls, greaterThanOrEqualTo(2));
    expect(authNotifier.refreshUserCalls, 1);
  });

  test('equipTitle refreshes titles and current user state', () async {
    container.read(achievementProvider);
    await Future<void>.delayed(Duration.zero);

    final notifier = container.read(achievementProvider.notifier);
    final result = await notifier.equipTitle('night_owl');

    expect(result, isTrue);
    expect(achievementRepository.equipTitleCalls, ['night_owl']);
    expect(achievementRepository.getTitlesCalls, greaterThanOrEqualTo(2));
    expect(authNotifier.refreshUserCalls, 1);
  });
}

class _FakeAchievementRepository extends AchievementRepository {
  _FakeAchievementRepository() : super(_UnusedApiClient());

  final List<String> equipGalaxySkinCalls = <String>[];
  final List<String> equipTitleCalls = <String>[];
  int getGalaxySkinsCalls = 0;
  int getTitlesCalls = 0;

  @override
  Future<AchievementListResponse> getAchievements({
    String? category,
    AchievementRarity? rarity,
    bool includeHidden = false,
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
  Future<GalaxySkinListResponse> getGalaxySkins() async {
    getGalaxySkinsCalls += 1;
    return GalaxySkinListResponse(
      equippedSkinId: 'legendary_anniversary',
      skins: <GalaxySkin>[
        GalaxySkin(
          id: 'legendary_anniversary',
          name: '周年传说',
          rarity: AchievementRarity.legendary,
          sortOrder: 1,
          createdAt: DateTime(2026, 3, 10),
          updatedAt: DateTime(2026, 3, 10),
          skinConfig: const <String, dynamic>{
            'colors': <String>['#FFAA00', '#0033FF'],
          },
          isUnlocked: true,
          isEquipped: true,
        ),
      ],
    );
  }

  @override
  Future<List<UserTitle>> getTitles() async {
    getTitlesCalls += 1;
    return <UserTitle>[
      UserTitle(
        userId: 'user-1',
        titleId: 'night_owl',
        titleName: '夜航者',
        titleDisplay: '夜航者',
        unlockedAt: DateTime(2026, 3, 10),
        isEquipped: true,
      ),
    ];
  }

  @override
  Future<SparkContract?> getContractStatus() async => null;

  @override
  Future<bool> equipGalaxySkin(String skinId) async {
    equipGalaxySkinCalls.add(skinId);
    return true;
  }

  @override
  Future<bool> equipTitle(String titleId) async {
    equipTitleCalls.add(titleId);
    return true;
  }

  @override
  Future<AchievementMapData> getAchievementMap() async =>
      AchievementMapData(nodes: const <AchievementMapNode>[]);
}

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier() : super(_UnusedAuthRepository()) {
    state = AuthState(
      isLoading: false,
      isAuthenticated: true,
      user: _buildUser(),
    );
  }

  int refreshUserCalls = 0;

  @override
  Future<void> checkAuthStatus() async {}

  @override
  Future<void> refreshUser() async {
    refreshUserCalls += 1;
  }
}

UserModel _buildUser() => UserModel(
      id: '00000000-0000-0000-0000-000000000001',
      username: 'achievement_user',
      email: 'achievement@example.com',
      flameLevel: 3,
      flameBrightness: 0.8,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026, 1, 1),
      updatedAt: DateTime(2026, 1, 1),
    );

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository()
      : super(_UnusedApiClient(), const FlutterSecureStorage());

  @override
  Future<bool> isLoggedIn() async => true;

  @override
  Future<UserModel> getCurrentUser() async => _buildUser();

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
