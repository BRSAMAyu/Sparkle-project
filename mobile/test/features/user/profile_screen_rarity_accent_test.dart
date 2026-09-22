import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/features/achievement/data/repositories/achievement_repository.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';
import 'package:sparkle/features/user/presentation/screens/profile_screen.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import 'package:sparkle/shared/providers/visual_element_provider.dart';

import '../../shared/i18n_test_helper.dart';

/// U-01 Step 5：profile 面「最近高光」稀有度 accent 收编验证。
///
/// 比色结论（见 v3-output/U01-STEP5/REPORT.md）：profile 私有稀有度色表
/// 与 DS.rarity* 卡片体系 **逐值不同**（4/4），按 CONVENTION 规则 5 以
/// `DS.profileRarity*` 命名 token 入册（值=profile 既有 UI 值），未硬迁。
/// 本文件固定：1) token 冻结值；2) ProfileScreen 高光行渲染真实取色。
void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  group('DS.profileRarity* frozen values (profile legacy palette)', () {
    test('legendary keeps profile orange (not card red)', () {
      expect(DS.profileRarityLegendary, const Color(0xFFFFA726));
      expect(DS.getProfileRarityAccent('legendary'), DS.profileRarityLegendary);
      // 与卡片体系值不同（比色登记，防未来被"顺手统一"）
      expect(DS.profileRarityLegendary, isNot(DS.rarityLegendary));
    });

    test('epic keeps profile purple (not card deep purple)', () {
      expect(DS.profileRarityEpic, const Color(0xFFAB47BC));
      expect(DS.getProfileRarityAccent('epic'), DS.profileRarityEpic);
      expect(DS.profileRarityEpic, isNot(DS.rarityEpic));
    });

    test('rare keeps profile blue (not card gold)', () {
      expect(DS.profileRarityRare, const Color(0xFF42A5F5));
      expect(DS.getProfileRarityAccent('rare'), DS.profileRarityRare);
      expect(DS.profileRarityRare, isNot(DS.rarityRare));
    });

    test('common keeps profile blue-grey and unknown falls back to common', () {
      expect(DS.profileRarityCommon, const Color(0xFFB0BEC5));
      expect(DS.getProfileRarityAccent('common'), DS.profileRarityCommon);
      expect(DS.getProfileRarityAccent('garbage'), DS.profileRarityCommon);
    });
  });

  group('ProfileScreen rarity accent rendering', () {
    for (final rarity in AchievementRarity.values) {
      testWidgets('highlight row renders $rarity accent from DS token', (
        tester,
      ) async {
        await _pumpProfileScreen(
          tester,
          achievements: [
            _achievement('a-${rarity.name}', rarity),
          ],
        );

        // 高光行图标取稀有度 accent（Row: Icon(auto_awesome) + 名称 + 标签）
        final icon = tester.widget<Icon>(
          find.byWidgetPredicate(
            (w) => w is Icon && w.icon == Icons.auto_awesome,
          ),
        );
        expect(
          icon.color,
          DS.getProfileRarityAccent(rarity.name),
          reason: '$rarity 高光行 accent 必须来自 DS.profileRarity* token',
        );
        expect(find.text('a-${rarity.name}'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}

AchievementWithProgress _achievement(String id, AchievementRarity rarity) =>
    AchievementWithProgress(
      achievement: AchievementModel(
        id: id,
        name: id,
        type: AchievementType.milestone,
        rarity: rarity,
        createdAt: DateTime(2026),
        updatedAt: DateTime(2026),
      ),
      isUnlocked: true,
      progressPercentage: 100,
      userProgress: UserAchievementProgress(
        achievementId: id,
        progress: 1,
        progressValue: 1,
        progressTarget: 1,
        unlockedAt: DateTime(2026),
      ),
    );

Future<void> _pumpProfileScreen(
  WidgetTester tester, {
  required List<AchievementWithProgress> achievements,
}) async {
  SharedPreferences.setMockInitialValues({});
  await ViewStorageService.ensureInitialized();

  final container = ProviderContainer(
    overrides: [
      authProvider.overrideWith((ref) => _FakeAuthNotifier()),
      achievementProvider.overrideWith(
        (ref) => _FakeAchievementNotifier(
          AchievementState.loading().copyWith(
            achievements: achievements,
            isLoading: false,
          ),
        ),
      ),
      visualElementProvider.overrideWith(
        (ref) => VisualElementNotifier(_UnusedApiClient()),
      ),
      profileContextProvider.overrideWith((ref) async => <String, dynamic>{}),
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: testMaterialApp(
        theme: AppThemes.lightTheme,
        home: const ProfileScreen(),
      ),
    ),
  );

  for (var i = 0; i < 8; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

class _FakeAchievementNotifier extends AchievementNotifier {
  _FakeAchievementNotifier(AchievementState initialState)
      : super(_UnusedAchievementRepository(), _UnusedRef()) {
    state = initialState;
  }

  @override
  Future<void> loadInitialData() async {}
}

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier() : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = AuthState(isAuthenticated: true, user: _buildUser());
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _UnusedAchievementRepository extends AchievementRepository {
  _UnusedAchievementRepository() : super(_UnusedApiClient());
}

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository() : super(_UnusedApiClient(), _UnusedTokenStorage());
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedTokenStorage implements TokenStorage {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

UserModel _buildUser() => UserModel(
      id: '00000000-0000-0000-0000-000000000042',
      username: 'rarity_test_user',
      email: 'rarity@example.com',
      nickname: 'Rarity Test',
      flameLevel: 1,
      flameBrightness: 0.5,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );
