import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/user/data/models/account_security_model.dart';
import 'package:sparkle/shared/entities/user_model.dart';

const _demoGuestModePreferenceKey = 'demo_guest_mode_enabled';

// 1. AuthState Class
class AuthState {
  AuthState({
    this.isLoading = false,
    this.isAuthenticated = false,
    this.user,
    this.error,
  });
  final bool isLoading;
  final bool isAuthenticated;
  final UserModel? user;
  final String? error;

  AuthState copyWith({
    bool? isLoading,
    bool? isAuthenticated,
    UserModel? user,
    String? error,
  }) =>
      AuthState(
        isLoading: isLoading ?? this.isLoading,
        isAuthenticated: isAuthenticated ?? this.isAuthenticated,
        user: user ?? this.user,
        error: error, // Don't carry over old errors
      );
}

// 2. AuthNotifier Class
class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier(this._ref, this._authRepository) : super(AuthState()) {
    unawaited(checkAuthStatus());
  }
  final Ref _ref;
  final AuthRepository _authRepository;

  Future<void> checkAuthStatus() async {
    state = state.copyWith(isLoading: true);
    try {
      final prefs = _ref.read(sharedPreferencesProvider);
      // 只有 loginAsDemoAccount 会存 true；访客模式现在存 false
      final savedDemoMode = prefs.getBool(_demoGuestModePreferenceKey) ?? false;
      DemoDataService.isDemoMode = savedDemoMode;

      final isLoggedIn = await _authRepository.isLoggedIn();
      if (isLoggedIn) {
        try {
          // 有真实 token 时，强制关闭 isDemoMode，确保从后端读取真实数据
          DemoDataService.isDemoMode = false;
          final user = await _authRepository.getCurrentUser();
          state = state.copyWith(
            isLoading: false,
            isAuthenticated: true,
            user: user,
          );
        } catch (e) {
          debugPrint('⚠️ Stored auth state invalid, clearing tokens: $e');
          await _authRepository.logout();
          state = state.copyWith(
            isLoading: false,
            isAuthenticated: false,
            error: e.toString(),
          );
        }
      } else {
        state = state.copyWith(isLoading: false, isAuthenticated: false);
      }
    } catch (e) {
      await _authRepository.logout();
      state = state.copyWith(
        isLoading: false,
        isAuthenticated: false,
        error: e.toString(),
      );
    }
  }

  Future<void> login(String usernameOrEmail, String password) async {
    state = state.copyWith(isLoading: true);
    try {
      DemoDataService.isDemoMode = false;
      await _ref
          .read(sharedPreferencesProvider)
          .setBool(_demoGuestModePreferenceKey, false);
      final user = await _authRepository.login(usernameOrEmail, password);
      state = state.copyWith(isAuthenticated: true, user: user);
    } catch (e) {
      state = state.copyWith(isAuthenticated: false, error: e.toString());
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<void> socialLogin({
    required String provider,
    required String token,
    String? openid,
    String? email,
    String? nickname,
    String? avatarUrl,
  }) async {
    state = state.copyWith(isLoading: true);
    try {
      DemoDataService.isDemoMode = false;
      await _ref
          .read(sharedPreferencesProvider)
          .setBool(_demoGuestModePreferenceKey, false);
      final user = await _authRepository.socialLogin(
        provider: provider,
        token: token,
        openid: openid,
        email: email,
        nickname: nickname,
        avatarUrl: avatarUrl,
      );
      state = state.copyWith(isAuthenticated: true, user: user);
    } catch (e) {
      state = state.copyWith(isAuthenticated: false, error: e.toString());
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<void> register(
    String username,
    String email,
    String password, {
    required bool acceptedTos,
    required bool acceptedPrivacy,
    String tosVersion = 'v1',
    String privacyVersion = 'v1',
    String? agreedLocale,
  }) async {
    state = state.copyWith(isLoading: true);
    try {
      DemoDataService.isDemoMode = false;
      await _ref
          .read(sharedPreferencesProvider)
          .setBool(_demoGuestModePreferenceKey, false);
      final user = await _authRepository.register(
        username,
        email,
        password,
        acceptedTos: acceptedTos,
        acceptedPrivacy: acceptedPrivacy,
        tosVersion: tosVersion,
        privacyVersion: privacyVersion,
        agreedLocale: agreedLocale,
      );
      state = state.copyWith(isAuthenticated: true, user: user);
    } catch (e) {
      state = state.copyWith(isAuthenticated: false, error: e.toString());
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<void> loginAsGuest() async {
    state = state.copyWith(isLoading: true);
    try {
      // 访客模式：使用真实后端 token + 后端预置演示数据，不走本地假数据
      DemoDataService.isDemoMode = false;
      await _ref
          .read(sharedPreferencesProvider)
          .setBool(_demoGuestModePreferenceKey, false);
      debugPrint('🎭 Guest login using real backend token + seeded data');

      final guestService = _ref.read(guestServiceProvider);
      final guestId = await guestService.getGuestId();
      final user = await _authRepository.guestLogin(guestId);
      final accessToken = await _authRepository.getAccessToken();
      if (accessToken == null || accessToken.isEmpty) {
        throw Exception('游客登录未获取到有效登录令牌');
      }
      state = state.copyWith(
        isLoading: false,
        isAuthenticated: true,
        user: user,
      );
    } catch (e) {
      debugPrint('⚠️ Guest login failed: $e');
      state = state.copyWith(
        isLoading: false,
        isAuthenticated: false,
        error: e.toString(),
      );
    }
  }


  Future<void> refreshUser() async {
    if (state.isAuthenticated) {
      try {
        final user = await _authRepository.getCurrentUser();
        state = state.copyWith(user: user);
      } catch (e) {
        // Could fail if token expired and refresh failed, log out user
        await logout();
      }
    }
  }

  Future<void> updateProfile(Map<String, dynamic> data) async {
    state = state.copyWith(isLoading: true);
    try {
      final user = await _authRepository.updateProfile(data);
      state = state.copyWith(user: user);
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<void> updateAvatar(String filePath) async {
    state = state.copyWith(isLoading: true);
    try {
      final user = await _authRepository.updateAvatar(filePath);
      state = state.copyWith(user: user);
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<void> changePassword(String oldPassword, String newPassword) async {
    state = state.copyWith(isLoading: true);
    try {
      await _authRepository.changePassword(oldPassword, newPassword);
      // No state change needed other than loading
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<String> setPassword(String newPassword) async {
    state = state.copyWith(isLoading: true);
    try {
      return await _authRepository.setPassword(newPassword);
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<String> forgotPassword(String email) async {
    state = state.copyWith(isLoading: true);
    try {
      return await _authRepository.forgotPassword(email);
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<String> resetPasswordWithToken(
    String token,
    String newPassword,
  ) async {
    state = state.copyWith(isLoading: true);
    try {
      return await _authRepository.resetPasswordWithToken(token, newPassword);
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<String> sendVerificationEmail() async {
    state = state.copyWith(isLoading: true);
    try {
      return await _authRepository.sendVerificationEmail();
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<String> verifyEmail(String token) async {
    state = state.copyWith(isLoading: true);
    try {
      final message = await _authRepository.verifyEmail(token);
      await refreshUser();
      return message;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<List<SocialAccountStatusModel>> getSocialAccounts() =>
      _authRepository.getSocialAccounts();

  Future<String> linkSocial({
    required String provider,
    required String token,
    String? openid,
  }) async {
    state = state.copyWith(isLoading: true);
    try {
      final message = await _authRepository.linkSocial(
        provider: provider,
        token: token,
        openid: openid,
      );
      await refreshUser();
      return message;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<String> unlinkSocial(String provider) async {
    state = state.copyWith(isLoading: true);
    try {
      final message = await _authRepository.unlinkSocial(provider);
      await refreshUser();
      return message;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<List<UserSessionModel>> getSessions() => _authRepository.getSessions();

  Future<String> revokeSession(String sessionId) async {
    state = state.copyWith(isLoading: true);
    try {
      return await _authRepository.revokeSession(sessionId);
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<String> revokeOtherSessions() async {
    state = state.copyWith(isLoading: true);
    try {
      return await _authRepository.revokeOtherSessions();
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<List<AuthAuditLogModel>> getSecurityLog() =>
      _authRepository.getSecurityLog();

  Future<void> deleteAccount({
    required String confirmation,
    String? password,
    String? provider,
    String? providerToken,
  }) async {
    state = state.copyWith(isLoading: true);
    try {
      await _authRepository.deleteAccount(
        confirmation: confirmation,
        password: password,
        provider: provider,
        providerToken: providerToken,
      );
      await logout();
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<void> upgradeGuest({
    required String username,
    required String email,
    required String password,
    required bool acceptedTos,
    required bool acceptedPrivacy,
    String tosVersion = 'v1',
    String privacyVersion = 'v1',
    String? agreedLocale,
  }) async {
    state = state.copyWith(isLoading: true);
    try {
      final user = await _authRepository.upgradeGuest(
        username: username,
        email: email,
        password: password,
        acceptedTos: acceptedTos,
        acceptedPrivacy: acceptedPrivacy,
        tosVersion: tosVersion,
        privacyVersion: privacyVersion,
        agreedLocale: agreedLocale,
      );
      DemoDataService.isDemoMode = false;
      await _ref
          .read(sharedPreferencesProvider)
          .setBool(_demoGuestModePreferenceKey, false);
      state = state.copyWith(isAuthenticated: true, user: user);
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<void> upgradeGuestWithSocial({
    required String provider,
    required String token,
    required bool acceptedTos,
    required bool acceptedPrivacy,
    String tosVersion = 'v1',
    String privacyVersion = 'v1',
    String? agreedLocale,
    String? openid,
  }) async {
    state = state.copyWith(isLoading: true);
    try {
      final user = await _authRepository.upgradeGuestWithSocial(
        provider: provider,
        token: token,
        openid: openid,
        acceptedTos: acceptedTos,
        acceptedPrivacy: acceptedPrivacy,
        tosVersion: tosVersion,
        privacyVersion: privacyVersion,
        agreedLocale: agreedLocale,
      );
      DemoDataService.isDemoMode = false;
      await _ref
          .read(sharedPreferencesProvider)
          .setBool(_demoGuestModePreferenceKey, false);
      state = state.copyWith(isAuthenticated: true, user: user);
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<void> logout() async {
    await _authRepository.logout();
    await _ref
        .read(sharedPreferencesProvider)
        .setBool(_demoGuestModePreferenceKey, false);
    DemoDataService.isDemoMode = false;
    state = AuthState(); // Reset to initial state
  }
}

// 3. Providers
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (ref) => AuthNotifier(ref, ref.watch(authRepositoryProvider)),
);

final currentUserProvider =
    Provider<UserModel?>((ref) => ref.watch(authProvider).user);

final isAuthenticatedProvider =
    Provider<bool>((ref) => ref.watch(authProvider).isAuthenticated);
