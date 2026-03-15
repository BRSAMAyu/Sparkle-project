import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/achievement/data/repositories/achievement_repository.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository_provider.dart';
import 'package:sparkle/features/shop/presentation/providers/title_provider.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import 'package:sparkle/shared/entities/shop_model.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await ThemeManager().reset();
  });

  tearDown(() async {
    await ThemeManager().reset();
  });

  test(
      'titleProvider resolves achievement title display from achievement source',
      () async {
    final container = ProviderContainer(
      overrides: [
        authProvider.overrideWith((ref) => _SourceAwareAuthNotifier()),
        shopRepositoryProvider.overrideWithValue(_FakeShopRepository()),
        achievementRepositoryProvider
            .overrideWithValue(_FakeAchievementRepository()),
      ],
    );
    addTearDown(container.dispose);

    final subscription =
        container.listen<Map<String, dynamic>?>(titleProvider, (_, __) {});
    addTearDown(subscription.close);

    final authNotifier =
        container.read(authProvider.notifier) as _SourceAwareAuthNotifier;
    authNotifier.setUser(_achievementTitleUser());
    await _settleProviderUpdates();

    expect(container.read(equippedTitleIdProvider), 'night_owl');
    expect(container.read(titleTextProvider), '夜航者');
    expect(container.read(titleDisplayFormatProvider), 'prefix');
  });
}

class _FakeShopRepository extends ShopRepository {
  _FakeShopRepository() : super(_UnusedApiClient());

  @override
  Future<Map<String, List<InventoryItem>>> getInventory() async =>
      <String, List<InventoryItem>>{
        'skins': <InventoryItem>[],
        'titles': <InventoryItem>[],
        'consumables': <InventoryItem>[],
        'boosts': <InventoryItem>[],
      };
}

class _FakeAchievementRepository extends AchievementRepository {
  _FakeAchievementRepository() : super(_UnusedApiClient());

  @override
  Future<GalaxySkinListResponse> getGalaxySkins() async =>
      GalaxySkinListResponse(
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

  @override
  Future<List<UserTitle>> getTitles() async => <UserTitle>[
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

class _SourceAwareAuthNotifier extends AuthNotifier {
  _SourceAwareAuthNotifier() : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = AuthState(
      isAuthenticated: true,
    );
  }

  @override
  Future<void> checkAuthStatus() async {}

  void setUser(UserModel user) {
    state = state.copyWith(user: user);
  }
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

UserModel _achievementTitleUser() => UserModel(
      id: '00000000-0000-0000-0000-000000000002',
      username: 'title_user',
      email: 'title@example.com',
      flameLevel: 3,
      flameBrightness: 0.8,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
      equippedTitle: 'night_owl',
      equippedTitleSource: 'achievement',
    );

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository()
      : super(_UnusedApiClient(), const FlutterSecureStorage());

  @override
  Future<bool> isLoggedIn() async => true;

  @override
  Future<UserModel> getCurrentUser() async => _achievementTitleUser();

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Future<void> _settleProviderUpdates() async {
  await Future<void>.delayed(const Duration(milliseconds: 10));
  await Future<void>.delayed(Duration.zero);
}
