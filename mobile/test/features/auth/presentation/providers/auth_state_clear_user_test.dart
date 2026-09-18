// M6-06 regression: revoked stored sessions must be able to clear the
// stale user from AuthState. copyWith uses null-merge semantics for `user`,
// so it needs an explicit `clearUser` flag (mirrors the `clearError` pattern)
// — otherwise `isAuthenticated: false` is set while `user` still holds the
// revoked identity and consumers keep reading the stale profile.
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

UserModel _buildUser() => UserModel(
      id: 'user-1',
      username: 'stale_user',
      email: 'stale@example.com',
      nickname: 'Stale',
      flameLevel: 1,
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

  group('M6-06 AuthState.clearUser', () {
    test('clearUser flag drops the stale user on revoked sessions', () {
      final state = AuthState(isAuthenticated: true, user: _buildUser());

      final next = state.copyWith(
        isLoading: false,
        isAuthenticated: false,
        clearUser: true,
      );

      expect(next.isAuthenticated, isFalse);
      expect(
        next.user,
        isNull,
        reason: 'A revoked session must not leave the stale user in state',
      );
    });

    test('copyWith without clearUser keeps null-merge semantics', () {
      final state = AuthState(isAuthenticated: true, user: _buildUser());

      // Existing callers pass a nullable user and expect keep-if-null.
      final kept = state.copyWith(isLoading: false);
      expect(kept.user, same(state.user));
    });
  });
}
