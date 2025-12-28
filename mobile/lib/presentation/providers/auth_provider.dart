import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/data/models/user_model.dart';
import 'package:sparkle/data/repositories/auth_repository.dart';

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
  }) => AuthState(
      isLoading: isLoading ?? this.isLoading,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      user: user ?? this.user,
      error: error, // Don't carry over old errors
    );
}

// 2. AuthNotifier Class
class AuthNotifier extends StateNotifier<AuthState> {

  AuthNotifier(this._authRepository) : super(AuthState()) {
    checkAuthStatus();
  }
  final AuthRepository _authRepository;

  Future<void> checkAuthStatus() async {
    state = state.copyWith(isLoading: true);
    try {
      final isLoggedIn = await _authRepository.isLoggedIn();
      if (isLoggedIn) {
        final user = await _authRepository.getCurrentUser();
        state = state.copyWith(isLoading: false, isAuthenticated: true, user: user);
      } else {
        state = state.copyWith(isLoading: false, isAuthenticated: false);
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, isAuthenticated: false, error: e.toString());
    }
  }

  Future<void> login(String usernameOrEmail, String password) async {
    state = state.copyWith(isLoading: true);
    try {
      await _authRepository.login(usernameOrEmail, password);
      final user = await _authRepository.getCurrentUser();
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
    String? email,
    String? nickname,
    String? avatarUrl,
  }) async {
    state = state.copyWith(isLoading: true);
    try {
      await _authRepository.socialLogin(
        provider: provider,
        token: token,
        email: email,
        nickname: nickname,
        avatarUrl: avatarUrl,
      );
      final user = await _authRepository.getCurrentUser();
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

  void loginAsGuest() {
    state = state.copyWith(isLoading: true);
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
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) => AuthNotifier(ref.watch(authRepositoryProvider)));

final currentUserProvider = Provider<UserModel?>((ref) => ref.watch(authProvider).user);

final isAuthenticatedProvider = Provider<bool>((ref) => ref.watch(authProvider).isAuthenticated);