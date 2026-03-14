import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/shared/entities/user_model.dart';

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
  AuthNotifier(this._authRepository) : super(AuthState()) {
    unawaited(checkAuthStatus());
  }
  final AuthRepository _authRepository;

  Future<void> checkAuthStatus() async {
    state = state.copyWith(isLoading: true);
    try {
      final isLoggedIn = await _authRepository.isLoggedIn();
      if (isLoggedIn) {
        final user = await _authRepository.getCurrentUser();
        state =
            state.copyWith(isLoading: false, isAuthenticated: true, user: user);
      } else {
        state = state.copyWith(isLoading: false, isAuthenticated: false);
      }
    } catch (e) {
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

  Future<void> register(String username, String email, String password) async {
    state = state.copyWith(isLoading: true);
    try {
      final user = await _authRepository.register(username, email, password);
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
      // 游客登录默认走真实联调链路，避免社区模块混入 mock 数据。
      DemoDataService.isDemoMode = false;
      debugPrint('🔌 Guest login using real backend data');

      final user = await _authRepository.guestLogin('guest_user');
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
      DemoDataService.isDemoMode = false;
      state = state.copyWith(
        isLoading: false,
        isAuthenticated: false,
        error: e.toString(),
      );
    }
  }

  Future<void> loginAsDemoAccount() async {
    state = state.copyWith(isLoading: true);
    try {
      // ✅ 演示账号登录：使用真实账户chat_test + 预设数据库数据
      // 必须关闭DemoMode以确保从后端API读取真实数据
      DemoDataService.isDemoMode = false;
      debugPrint('🎬 Demo account login (real data from backend)');

      final user = await _authRepository.login('chat_test', 'Chat123456');
      state = state.copyWith(
        isLoading: false,
        isAuthenticated: true,
        user: user,
      );
      debugPrint(
        '✅ Demo account login successful, fetching real data from API',
      );
    } catch (e) {
      debugPrint('⚠️ Demo account login failed: $e');
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

  Future<void> logout() async {
    await _authRepository.logout();
    state = AuthState(); // Reset to initial state
  }
}

// 3. Providers
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (ref) => AuthNotifier(ref.watch(authRepositoryProvider)),
);

final currentUserProvider =
    Provider<UserModel?>((ref) => ref.watch(authProvider).user);

final isAuthenticatedProvider =
    Provider<bool>((ref) => ref.watch(authProvider).isAuthenticated);
