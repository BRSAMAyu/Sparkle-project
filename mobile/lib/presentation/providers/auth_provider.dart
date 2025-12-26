import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/user_model.dart';
import 'package:sparkle/data/repositories/auth_repository.dart';
import 'package:sparkle/core/services/demo_data_service.dart';

// 1. AuthState Class
class AuthState {
  final bool isLoading;
  final bool isAuthenticated;
  final UserModel? user;
  final String? error;

  AuthState({
    this.isLoading = false,
    this.isAuthenticated = false,
    this.user,
    this.error,
  });

  AuthState copyWith({
    bool? isLoading,
    bool? isAuthenticated,
    UserModel? user,
    String? error,
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      user: user ?? this.user,
      error: error, // Don't carry over old errors
    );
  }
}

// 2. AuthNotifier Class
class AuthNotifier extends StateNotifier<AuthState> {
  final AuthRepository _authRepository;

  AuthNotifier(this._authRepository) : super(AuthState()) {
    checkAuthStatus();
  }

  Future<void> checkAuthStatus() async {
    state = state.copyWith(isLoading: true);
    try {
      final isLoggedIn = await _authRepository.isLoggedIn();
      if (isLoggedIn) {
        final user = await _authRepository.getCurrentUser();
        state = state.copyWith(isLoading: false, isAuthenticated: true, user: user);
      } else {
        state = state.copyWith(isLoading: false, isAuthenticated: false, user: null);
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, isAuthenticated: false, user: null, error: e.toString());
    }
  }

  Future<void> login(String usernameOrEmail, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await _authRepository.login(usernameOrEmail, password);
      final user = await _authRepository.getCurrentUser();
      state = state.copyWith(isLoading: false, isAuthenticated: true, user: user);
    } catch (e) {
      state = state.copyWith(isLoading: false, isAuthenticated: false, error: e.toString());
    }
  }

  Future<void> socialLogin({
    required String provider,
    required String token,
    String? email,
    String? nickname,
    String? avatarUrl,
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await _authRepository.socialLogin(
        provider: provider,
        token: token,
        email: email,
        nickname: nickname,
        avatarUrl: avatarUrl,
      );
      final user = await _authRepository.getCurrentUser();
      state = state.copyWith(isLoading: false, isAuthenticated: true, user: user);
    } catch (e) {
      state = state.copyWith(isLoading: false, isAuthenticated: false, error: e.toString());
    }
  }

  Future<void> register(String username, String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final user = await _authRepository.register(username, email, password);
      state = state.copyWith(isLoading: false, isAuthenticated: true, user: user);
    } catch (e) {
      state = state.copyWith(isLoading: false, isAuthenticated: false, error: e.toString());
    }
  }

  void loginAsGuest() {
    state = state.copyWith(isLoading: true, error: null);
    DemoDataService.isDemoMode = true;
    
    // Simulate a short delay
    Future.delayed(const Duration(milliseconds: 500), () {
      final guestUser = DemoDataService().demoUser;
      
      state = state.copyWith(
        isLoading: false, 
        isAuthenticated: true, 
        user: guestUser,
      );
    });
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
    state = state.copyWith(isLoading: true, error: null);
    try {
      final user = await _authRepository.updateProfile(data);
      state = state.copyWith(isLoading: false, user: user);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      rethrow;
    }
  }

  Future<void> updateAvatar(String filePath) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final user = await _authRepository.updateAvatar(filePath);
      state = state.copyWith(isLoading: false, user: user);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      rethrow;
    }
  }

  Future<void> changePassword(String oldPassword, String newPassword) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await _authRepository.changePassword(oldPassword, newPassword);
      state = state.copyWith(isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      rethrow;
    }
  }

  Future<void> logout() async {
    await _authRepository.logout();
    state = AuthState(); // Reset to initial state
  }
}

// 3. Providers
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref.watch(authRepositoryProvider));
});

final currentUserProvider = Provider<UserModel?>((ref) {
  return ref.watch(authProvider).user;
});

final isAuthenticatedProvider = Provider<bool>((ref) {
  return ref.watch(authProvider).isAuthenticated;
});