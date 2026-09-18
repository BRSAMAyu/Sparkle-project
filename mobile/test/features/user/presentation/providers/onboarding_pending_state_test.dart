// M6-07 regression tests: onboarding state must be tri-state.
//
// `onboardingCompletedProvider` starts at a hard `false` today, so during
// the async sync window the router redirect treats every authenticated
// user as "hasn't completed onboarding" and flashes them into the persona
// onboarding flow, bouncing back when the sync resolves. The fix makes
// the state `bool?` where `null` = pending (no onboarding rewrite).
//
// Locks:
//   1. While sync is still pending (no stored value, profile context not
//      resolved yet) the state must be `null`, not `false`.
//   2. When sync resolves, the state becomes a definitive bool.
import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/core/services/session_refresh_service.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';

class _StaticAuthNotifier extends AuthNotifier {
  _StaticAuthNotifier(AuthState authState)
      : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = authState;
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _DelayedProfileUserRepository extends UserRepository {
  _DelayedProfileUserRepository(this.completer) : super(_UnusedApiClient());

  final Completer<Map<String, dynamic>> completer;

  @override
  Future<Map<String, dynamic>> fetchProfileContext() => completer.future;
}

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository() : super(_UnusedApiClient(), SecureTokenStorage(storage: _MemorySecureStorage()));

  @override
  Future<bool> isLoggedIn() async => false;

  @override
  Future<UserModel> getCurrentUser() {
    throw UnimplementedError();
  }

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MemorySecureStorage implements FlutterSecureStorage {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

UserModel _buildUser() => UserModel(
      id: '20000000-0000-0000-0000-000000000002',
      username: 'onboarding_user',
      email: 'onboarding@example.com',
      nickname: 'Onboarding User',
      flameLevel: 2,
      flameBrightness: 0.5,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('onboarding state is pending (null) until sync resolves, not false',
      () async {
    SharedPreferences.setMockInitialValues({});
    final profileCompleter = Completer<Map<String, dynamic>>();

    final container = ProviderContainer(
      overrides: [
        authProvider.overrideWith(
          (ref) => _StaticAuthNotifier(
            AuthState(isAuthenticated: true, user: _buildUser()),
          ),
        ),
        userRepositoryProvider.overrideWithValue(
          _DelayedProfileUserRepository(profileCompleter),
        ),
        sessionBoundProvidersProvider.overrideWithValue(const []),
      ],
    );
    addTearDown(container.dispose);

    // Constructing the notifier triggers syncForUser: no stored value →
    // profile context fetch is pending.
    final initial = container.read(onboardingCompletedProvider);

    expect(
      initial,
      isNull,
      reason:
          'While the onboarding sync is pending the state must be `null` '
          '(pending), not `false`. A hard `false` makes the router redirect '
          'send already-onboarded users into the persona onboarding flash '
          '(M6-07). Observed: $initial',
    );

    profileCompleter.complete({
      'preference_version': 5,
      'preferences': {'study_time_preference': 90},
    });

    final deadline = DateTime.now().add(const Duration(seconds: 3));
    var resolved = container.read(onboardingCompletedProvider);
    while (resolved == null && DateTime.now().isBefore(deadline)) {
      await Future<void>.delayed(const Duration(milliseconds: 20));
      resolved = container.read(onboardingCompletedProvider);
    }
    expect(resolved, isTrue);
  });

  test('explicit stored value resolves synchronously to that value',
      () async {
    SharedPreferences.setMockInitialValues({
      'settings_onboarding_completed_20000000-0000-0000-0000-000000000002':
          true,
    });

    final container = ProviderContainer(
      overrides: [
        authProvider.overrideWith(
          (ref) => _StaticAuthNotifier(
            AuthState(isAuthenticated: true, user: _buildUser()),
          ),
        ),
        sessionBoundProvidersProvider.overrideWithValue(const []),
      ],
    );
    addTearDown(container.dispose);

    final deadline = DateTime.now().add(const Duration(seconds: 3));
    var resolved = container.read(onboardingCompletedProvider);
    while (resolved != true && DateTime.now().isBefore(deadline)) {
      await Future<void>.delayed(const Duration(milliseconds: 20));
      resolved = container.read(onboardingCompletedProvider);
    }
    expect(
      resolved,
      isTrue,
      reason: 'A stored true must surface as true once sync completes',
    );
  });
}
