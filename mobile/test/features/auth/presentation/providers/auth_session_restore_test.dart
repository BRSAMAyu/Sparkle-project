import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/session_refresh_service.dart';
import 'package:sparkle/features/auth/data/models/token_model.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const userId = '11111111-1111-1111-1111-111111111111';
  final restoredUser = UserModel(
    id: userId,
    username: 'restore_user',
    email: 'restore@example.com',
    nickname: 'Restore User',
    flameLevel: 2,
    flameBrightness: 0.6,
    depthPreference: 0.5,
    curiosityPreference: 0.6,
    isActive: true,
    status: UserStatus.online,
    createdAt: DateTime(2026),
    updatedAt: DateTime(2026),
  );

  Future<SharedPreferences> initPrefs({
    required bool onboardingCompleted,
  }) async {
    SharedPreferences.setMockInitialValues(
      {'${kOnboardingCompletedKey}_$userId': onboardingCompleted},
    );
    return SharedPreferences.getInstance();
  }

  group('Auth session restoration', () {
    test('cold start restores stored auth session and onboarding state',
        () async {
      final prefs = await initPrefs(onboardingCompleted: true);
      final storage = _MemorySecureStorage();
      final authRepo = _FakeAuthRepository(storage, restoredUser);
      final userRepo = _FakeUserRepository();

      await authRepo.saveTokens(
        TokenResponse(
          accessToken: 'stored-access-token',
          refreshToken: 'stored-refresh-token',
          expiresIn: 3600,
        ),
      );

      final container = ProviderContainer(
        overrides: [
          authRepositoryProvider.overrideWithValue(authRepo),
          userRepositoryProvider.overrideWithValue(userRepo),
          sharedPreferencesProvider.overrideWithValue(prefs),
          sessionBoundProvidersProvider.overrideWithValue(const []),
        ],
      );
      addTearDown(container.dispose);

      await _waitFor(
        () => container.read(authProvider).isAuthenticated,
      );
      await _waitFor(
        () => container.read(onboardingCompletedProvider),
      );

      final authState = container.read(authProvider);
      expect(authState.isAuthenticated, isTrue);
      expect(authState.user?.id, userId);
      expect(container.read(onboardingCompletedProvider), isTrue);
    });

    test('provider state survives container rebuild after login', () async {
      final prefs = await initPrefs(onboardingCompleted: false);
      final storage = _MemorySecureStorage();
      final authRepo = _FakeAuthRepository(storage, restoredUser);
      final userRepo = _FakeUserRepository();

      ProviderContainer buildContainer() => ProviderContainer(
            overrides: [
              authRepositoryProvider.overrideWithValue(authRepo),
              userRepositoryProvider.overrideWithValue(userRepo),
              sharedPreferencesProvider.overrideWithValue(prefs),
              sessionBoundProvidersProvider.overrideWithValue(const []),
            ],
          );

      final firstContainer = buildContainer();
      addTearDown(firstContainer.dispose);

      await firstContainer
          .read(authProvider.notifier)
          .login('restore_user', 'password');
      await firstContainer
          .read(onboardingCompletedProvider.notifier)
          .setCompleted(true);
      await _waitFor(
        () => firstContainer.read(authProvider).isAuthenticated,
      );
      expect(firstContainer.read(onboardingCompletedProvider), isTrue);

      firstContainer.dispose();

      final rebuiltContainer = buildContainer();
      addTearDown(rebuiltContainer.dispose);

      await _waitFor(
        () => rebuiltContainer.read(authProvider).isAuthenticated,
      );
      await _waitFor(
        () => rebuiltContainer.read(onboardingCompletedProvider),
      );

      final rebuiltAuthState = rebuiltContainer.read(authProvider);
      expect(rebuiltAuthState.isAuthenticated, isTrue);
      expect(rebuiltAuthState.user?.id, userId);
      expect(rebuiltContainer.read(onboardingCompletedProvider), isTrue);
    });
  });
}

Future<void> _waitFor(bool Function() predicate) async {
  final deadline = DateTime.now().add(const Duration(seconds: 2));
  while (DateTime.now().isBefore(deadline)) {
    if (predicate()) {
      return;
    }
    await Future<void>.delayed(const Duration(milliseconds: 20));
  }
  expect(predicate(), isTrue);
}

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository(FlutterSecureStorage storage, this._user)
      : super(_UnusedApiClient(), storage);

  final UserModel _user;

  @override
  Future<bool> isLoggedIn() async => await getAccessToken() != null;

  @override
  Future<UserModel> getCurrentUser() async => _user;

  @override
  Future<UserModel> login(String usernameOrEmail, String password) async {
    await saveTokens(
      TokenResponse(
        accessToken: 'login-access-token',
        refreshToken: 'login-refresh-token',
        expiresIn: 3600,
      ),
    );
    return _user;
  }

  @override
  Future<void> logout({bool keepDemoMode = false}) async {
    await clearTokens();
  }
}

class _FakeUserRepository extends UserRepository {
  _FakeUserRepository() : super(_UnusedApiClient());

  @override
  Future<Map<String, dynamic>> fetchProfileContext() async => {
      'preference_version': 5,
      'preferences': {
        'study_time_preference': 90,
      },
    };
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MemorySecureStorage implements FlutterSecureStorage {
  final Map<String, String> _values = <String, String>{};

  @override
  Future<void> write({
    required String key,
    String? value,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (value == null) {
      _values.remove(key);
    } else {
      _values[key] = value;
    }
  }

  @override
  Future<String?> read({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async => _values[key];

  @override
  Future<void> delete({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    _values.remove(key);
  }

  @override
  Future<void> deleteAll({
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    _values.clear();
  }

  @override
  Future<bool> containsKey({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      _values.containsKey(key);

  @override
  Future<Map<String, String>> readAll({
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      Map<String, String>.from(_values);

  @override
  Future<bool?> isCupertinoProtectedDataAvailable() async => true;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
