import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/errors/failures.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/session_refresh_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/data/services/chat_cache_service.dart';
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
    this.failure,
  });
  final bool isLoading;
  final bool isAuthenticated;
  final UserModel? user;

  /// N15（A-SPEC3）：UI 可达错误字段只存类型化类别（渲染侧经
  /// error_lexicon owner 出人话）；原始异常细节只进 debugPrint 日志。
  final UiErrorCategory? error;
  final AppFailure? failure;
  String? get errorCode => failure?.errorCode;

  AuthState copyWith({
    bool? isLoading,
    bool? isAuthenticated,
    UserModel? user,
    bool clearUser = false,
    UiErrorCategory? error,
    AppFailure? failure,
  }) =>
      AuthState(
        isLoading: isLoading ?? this.isLoading,
        isAuthenticated: isAuthenticated ?? this.isAuthenticated,
        user: clearUser ? null : (user ?? this.user),
        error: error, // Don't carry over old errors
        failure: failure,
      );
}

// 2. AuthNotifier Class
class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier(this._ref, this._authRepository) : super(AuthState()) {
    unawaited(checkAuthStatus());
  }
  final Ref _ref;
  final AuthRepository _authRepository;

  /// 会话世代（W-1 竞态收口）。
  ///
  /// 每个认证流程入口（checkAuthStatus/login/register/socialLogin/loginAsGuest/
  /// logout）开启新世代；流程内所有 await 之后的 state 写入前先校验世代，
  /// 过世代（已有更新流程开启）的写入一律丢弃。否则并发时旧流程的
  /// finally/catch/_failedAuthState 会把新流程的成功态覆盖回未认证
  /// （web-round1 实测：登录 200 后 UI 不跳转的疑因 2）。
  int _sessionGeneration = 0;
  int _beginSessionOp() => ++_sessionGeneration;
  bool _isStaleSessionOp(int generation) => generation != _sessionGeneration;

  AuthState _failedAuthState(
    Object error, {
    required bool isAuthenticated,
    bool isLoading = false,
  }) {
    final failure = AppFailureMapper.from(error);
    return state.copyWith(
      isLoading: isLoading,
      isAuthenticated: isAuthenticated,
      // N15：错误字段只存类型化类别（AppFailure 自报，零文本嗅探）；
      // 具体人话仍由 failure.userMessage 承载（登录/注册监听优先读它）。
      error: failure.uiErrorCategory,
      failure: failure,
    );
  }

  Future<void> _clearUserScopedLocalData() async {
    await _ref.read(guestServiceProvider).clearGuestData();
    await ChatCacheService().clearAllCache();
    try {
      await ViewStorageService.instance.clearAllViewState();
    } catch (e) {
      debugPrint('ℹ️ View storage cleanup skipped during auth reset: $e');
    }
    try {
      await LocalDatabase().clearUserScopedData();
    } catch (e) {
      debugPrint('ℹ️ Local database cleanup skipped during auth reset: $e');
    }
  }

  Future<void> _resetInvalidStoredSession(
    Object error, {
    required int generation,
  }) async {
    if (_isStaleSessionOp(generation)) {
      debugPrint(
          'ℹ️ Skipping stale session reset (generation $generation superseded)');
      return;
    }
    debugPrint(
        'ℹ️ Stored auth session expired, clearing local auth state: $error');
    await _authRepository.clearTokens();
    await _clearUserScopedLocalData();
    state = state.copyWith(
      isLoading: false,
      isAuthenticated: false,
      // copyWith 对 user 做空值合并，必须用 clearUser 标志才能真正清掉
      // 被吊销会话残留的过期用户，否则 currentUserProvider 会继续返回
      // 已失效的身份。
      clearUser: true,
    );
  }

  /// IR-G12（A-SPEC4）：基础设施抖动/离线不可清会话——仅服务端明确拒绝
  /// （401/403）才 reset。原实现 catch 不分类型一律
  /// _resetInvalidStoredSession：离线冷启动时 getCurrentUser 的网络错
  /// 也清 token+本地数据 = 强制登出（数据信任灾难）。与
  /// TokenRefreshCoordinator 的 sessionTerminal/retryable 分级咬合。
  bool _isSessionTerminalError(Object error) {
    // AppFailureMapper 已含 Dio 状态码感知分类；无 response 的网络层
    // 异常（连接失败/超时）与 5xx 都是 retryable——保留会话等重试。
    final failure = AppFailureMapper.from(
      error,
      fallbackMessage: 'auth status check failed',
    );
    final code = failure.code;
    // 403 在 AppFailureMapper 的码是 AUTH_REQUIRED（failures.dart:256）。
    return code == 'TOKEN_EXPIRED' ||
        code == 'UNAUTHORIZED' ||
        code == 'AUTH_REQUIRED';
  }

  Future<void> _handleSessionCheckFailure(
    Object error, {
    required int generation,
  }) async {
    if (_isSessionTerminalError(error)) {
      await _resetInvalidStoredSession(error, generation: generation);
      return;
    }
    if (_isStaleSessionOp(generation)) return;
    debugPrint('⚠️ Auth status check failed (retryable, session kept): $error');
    // 会话保留：以已存储身份进入 app，数据面走各自的离线/重试路径。
    state = state.copyWith(
      isLoading: false,
      // isAuthenticated 维持当前值（有 token 场景下为默认 true 假设），
      // 不主动改写；clearUser 绝不触发。
    );
  }

  Future<void> checkAuthStatus() async {
    final generation = _beginSessionOp();
    state = state.copyWith(isLoading: true);
    try {
      final prefs = _ref.read(sharedPreferencesProvider);
      // 只有 loginAsDemoAccount 会存 true；访客模式现在存 false
      final savedDemoMode = prefs.getBool(_demoGuestModePreferenceKey) ?? false;
      DemoDataService.isDemoMode = savedDemoMode;

      final isLoggedIn = await _authRepository.isLoggedIn();
      if (_isStaleSessionOp(generation)) return;
      if (isLoggedIn) {
        try {
          // 有真实 token 时，强制关闭 isDemoMode，确保从后端读取真实数据
          DemoDataService.isDemoMode = false;
          var user = await _authRepository.getCurrentUser();
          if (_isStaleSessionOp(generation)) return;
          if (user.registrationSource == 'guest') {
            try {
              final guestId =
                  await _ref.read(guestServiceProvider).getGuestId();
              if (guestId == user.username) {
                user = await _authRepository.guestLogin(guestId);
              }
            } catch (e) {
              debugPrint('⚠️ Guest reseed refresh skipped: $e');
            }
          } else {
            await _ref.read(guestServiceProvider).clearGuestData();
          }
          if (_isStaleSessionOp(generation)) return;
          state = state.copyWith(
            isLoading: false,
            isAuthenticated: true,
            user: user,
          );
          SessionRefreshService.refreshSessionBoundProviders(_ref);
        } catch (e) {
          await _handleSessionCheckFailure(e, generation: generation);
        }
      } else {
        state = state.copyWith(isLoading: false, isAuthenticated: false);
      }
    } catch (e) {
      await _handleSessionCheckFailure(e, generation: generation);
    }
  }

  Future<void> login(String usernameOrEmail, String password) async {
    final generation = _beginSessionOp();
    state = state.copyWith(isLoading: true);
    try {
      DemoDataService.isDemoMode = false;
      await _ref
          .read(sharedPreferencesProvider)
          .setBool(_demoGuestModePreferenceKey, false);
      // N-4：登录即切换身份 —— 先清上一身份的本地用户态（含上次会话
      // 未走 logout 的崩溃残留），避免新账号读到旧账号数据。
      await _clearUserScopedLocalData();
      await _ref.read(guestServiceProvider).clearGuestData();
      final user = await _authRepository.login(usernameOrEmail, password);
      if (_isStaleSessionOp(generation)) return;
      state = state.copyWith(isAuthenticated: true, user: user);
      SessionRefreshService.refreshSessionBoundProviders(_ref);
    } catch (e) {
      if (_isStaleSessionOp(generation)) return;
      state = _failedAuthState(e, isAuthenticated: false);
    } finally {
      if (!_isStaleSessionOp(generation)) {
        state = state.copyWith(
          isLoading: false,
          error: state.error,
          failure: state.failure,
        );
      }
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
    final generation = _beginSessionOp();
    state = state.copyWith(isLoading: true);
    try {
      DemoDataService.isDemoMode = false;
      await _ref
          .read(sharedPreferencesProvider)
          .setBool(_demoGuestModePreferenceKey, false);
      // N-4：登录即切换身份，见 login() 内注释。
      await _clearUserScopedLocalData();
      await _ref.read(guestServiceProvider).clearGuestData();
      final user = await _authRepository.socialLogin(
        provider: provider,
        token: token,
        openid: openid,
        email: email,
        nickname: nickname,
        avatarUrl: avatarUrl,
      );
      if (_isStaleSessionOp(generation)) return;
      state = state.copyWith(isAuthenticated: true, user: user);
      SessionRefreshService.refreshSessionBoundProviders(_ref);
    } catch (e) {
      if (_isStaleSessionOp(generation)) return;
      state = _failedAuthState(e, isAuthenticated: false);
    } finally {
      if (!_isStaleSessionOp(generation)) {
        state = state.copyWith(
          isLoading: false,
          error: state.error,
          failure: state.failure,
        );
      }
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
    final generation = _beginSessionOp();
    state = state.copyWith(isLoading: true);
    try {
      DemoDataService.isDemoMode = false;
      await _ref
          .read(sharedPreferencesProvider)
          .setBool(_demoGuestModePreferenceKey, false);
      // N-4：登录即切换身份，见 login() 内注释。
      await _clearUserScopedLocalData();
      await _ref.read(guestServiceProvider).clearGuestData();
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
      if (_isStaleSessionOp(generation)) return;
      state = state.copyWith(isAuthenticated: true, user: user);
      SessionRefreshService.refreshSessionBoundProviders(_ref);
    } catch (e) {
      if (_isStaleSessionOp(generation)) return;
      state = _failedAuthState(e, isAuthenticated: false);
    } finally {
      if (!_isStaleSessionOp(generation)) {
        state = state.copyWith(
          isLoading: false,
          error: state.error,
          failure: state.failure,
        );
      }
    }
  }

  Future<void> loginAsGuest() async {
    final generation = _beginSessionOp();
    state = state.copyWith(isLoading: true);
    try {
      // 访客模式：使用真实后端 token + 后端预置演示数据，不走本地假数据
      DemoDataService.isDemoMode = false;
      await _ref
          .read(sharedPreferencesProvider)
          .setBool(_demoGuestModePreferenceKey, false);
      // N-4：登录即切换身份，见 login() 内注释。
      await _clearUserScopedLocalData();
      debugPrint('🎭 Guest login using real backend token + seeded data');

      final guestService = _ref.read(guestServiceProvider);
      final guestId = await guestService.getGuestId();
      final user = await _authRepository.guestLogin(guestId);
      final accessToken = await _authRepository.getAccessToken();
      if (_isStaleSessionOp(generation)) return;
      if (accessToken == null || accessToken.isEmpty) {
        throw Exception(I18nService.instance.l10n.authGuestTokenFailed);
      }
      state = state.copyWith(
        isLoading: false,
        isAuthenticated: true,
        user: user,
      );
      SessionRefreshService.refreshSessionBoundProviders(_ref);
    } catch (e) {
      if (_isStaleSessionOp(generation)) return;
      debugPrint('⚠️ Guest login failed: $e');
      state = _failedAuthState(e, isAuthenticated: false);
    }
  }

  Future<void> refreshUser() async {
    if (state.isAuthenticated) {
      try {
        final user = await _authRepository.getCurrentUser();
        state = state.copyWith(user: user);
      } on AuthFailure {
        // Token expired and refresh failed — log out
        await logout();
      } on SocketException {
        // Network error — keep current state, don't log out
        debugPrint('[Auth] refreshUser: network error, keeping current state');
      } catch (e) {
        // Only logout on auth failures, not transient errors
        if (e.toString().contains('401') || e.toString().contains('unauthorized')) {
          await logout();
        } else {
          debugPrint('[Auth] refreshUser: non-auth error, keeping state: $e');
        }
      }
    }
  }

  Future<void> updateProfile(Map<String, dynamic> data) async {
    state = state.copyWith(isLoading: true);
    try {
      final user = await _authRepository.updateProfile(data);
      state = state.copyWith(user: user);
      SessionRefreshService.refreshSessionBoundProviders(_ref);
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别（经 AppFailure
      // 类型化判定，勿存 e.toString()）。
      debugPrint('[auth] account-security op failed: $e');
      state = state.copyWith(error: AppFailureMapper.from(e).uiErrorCategory);
      rethrow;
    } finally {
      // carry-over 与 login 家族 finally 同型：copyWith 对 error 是直接
      // 赋值语义，不显式带旧值会把刚写入的类别抹回 null。
      state = state.copyWith(
        isLoading: false,
        error: state.error,
        failure: state.failure,
      );
    }
  }

  Future<void> updateAvatar(String filePath) async {
    state = state.copyWith(isLoading: true);
    try {
      final user = await _authRepository.updateAvatar(filePath);
      state = state.copyWith(user: user);
      SessionRefreshService.refreshSessionBoundProviders(_ref);
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别（经 AppFailure
      // 类型化判定，勿存 e.toString()）。
      debugPrint('[auth] account-security op failed: $e');
      state = state.copyWith(error: AppFailureMapper.from(e).uiErrorCategory);
      rethrow;
    } finally {
      // carry-over 与 login 家族 finally 同型：copyWith 对 error 是直接
      // 赋值语义，不显式带旧值会把刚写入的类别抹回 null。
      state = state.copyWith(
        isLoading: false,
        error: state.error,
        failure: state.failure,
      );
    }
  }

  Future<void> changePassword(String oldPassword, String newPassword) async {
    state = state.copyWith(isLoading: true);
    try {
      await _authRepository.changePassword(oldPassword, newPassword);
      // No state change needed other than loading
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别（经 AppFailure
      // 类型化判定，勿存 e.toString()）。
      debugPrint('[auth] account-security op failed: $e');
      state = state.copyWith(error: AppFailureMapper.from(e).uiErrorCategory);
      rethrow;
    } finally {
      // carry-over 与 login 家族 finally 同型：copyWith 对 error 是直接
      // 赋值语义，不显式带旧值会把刚写入的类别抹回 null。
      state = state.copyWith(
        isLoading: false,
        error: state.error,
        failure: state.failure,
      );
    }
  }

  Future<String> setPassword(String newPassword) async {
    state = state.copyWith(isLoading: true);
    try {
      return await _authRepository.setPassword(newPassword);
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别（经 AppFailure
      // 类型化判定，勿存 e.toString()）。
      debugPrint('[auth] account-security op failed: $e');
      state = state.copyWith(error: AppFailureMapper.from(e).uiErrorCategory);
      rethrow;
    } finally {
      // carry-over 与 login 家族 finally 同型：copyWith 对 error 是直接
      // 赋值语义，不显式带旧值会把刚写入的类别抹回 null。
      state = state.copyWith(
        isLoading: false,
        error: state.error,
        failure: state.failure,
      );
    }
  }

  Future<String> forgotPassword(String email) async {
    state = state.copyWith(isLoading: true);
    try {
      return await _authRepository.forgotPassword(email);
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别（经 AppFailure
      // 类型化判定，勿存 e.toString()）。
      debugPrint('[auth] account-security op failed: $e');
      state = state.copyWith(error: AppFailureMapper.from(e).uiErrorCategory);
      rethrow;
    } finally {
      // carry-over 与 login 家族 finally 同型：copyWith 对 error 是直接
      // 赋值语义，不显式带旧值会把刚写入的类别抹回 null。
      state = state.copyWith(
        isLoading: false,
        error: state.error,
        failure: state.failure,
      );
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
      // N15：原始异常只进日志；错误字段存类型化类别（经 AppFailure
      // 类型化判定，勿存 e.toString()）。
      debugPrint('[auth] account-security op failed: $e');
      state = state.copyWith(error: AppFailureMapper.from(e).uiErrorCategory);
      rethrow;
    } finally {
      // carry-over 与 login 家族 finally 同型：copyWith 对 error 是直接
      // 赋值语义，不显式带旧值会把刚写入的类别抹回 null。
      state = state.copyWith(
        isLoading: false,
        error: state.error,
        failure: state.failure,
      );
    }
  }

  Future<String> sendVerificationEmail() async {
    state = state.copyWith(isLoading: true);
    try {
      return await _authRepository.sendVerificationEmail();
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别（经 AppFailure
      // 类型化判定，勿存 e.toString()）。
      debugPrint('[auth] account-security op failed: $e');
      state = state.copyWith(error: AppFailureMapper.from(e).uiErrorCategory);
      rethrow;
    } finally {
      // carry-over 与 login 家族 finally 同型：copyWith 对 error 是直接
      // 赋值语义，不显式带旧值会把刚写入的类别抹回 null。
      state = state.copyWith(
        isLoading: false,
        error: state.error,
        failure: state.failure,
      );
    }
  }

  Future<String> verifyEmail(String token) async {
    state = state.copyWith(isLoading: true);
    try {
      final message = await _authRepository.verifyEmail(token);
      await refreshUser();
      return message;
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别（经 AppFailure
      // 类型化判定，勿存 e.toString()）。
      debugPrint('[auth] account-security op failed: $e');
      state = state.copyWith(error: AppFailureMapper.from(e).uiErrorCategory);
      rethrow;
    } finally {
      // carry-over 与 login 家族 finally 同型：copyWith 对 error 是直接
      // 赋值语义，不显式带旧值会把刚写入的类别抹回 null。
      state = state.copyWith(
        isLoading: false,
        error: state.error,
        failure: state.failure,
      );
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
      // N15：原始异常只进日志；错误字段存类型化类别（经 AppFailure
      // 类型化判定，勿存 e.toString()）。
      debugPrint('[auth] account-security op failed: $e');
      state = state.copyWith(error: AppFailureMapper.from(e).uiErrorCategory);
      rethrow;
    } finally {
      // carry-over 与 login 家族 finally 同型：copyWith 对 error 是直接
      // 赋值语义，不显式带旧值会把刚写入的类别抹回 null。
      state = state.copyWith(
        isLoading: false,
        error: state.error,
        failure: state.failure,
      );
    }
  }

  Future<String> unlinkSocial(String provider) async {
    state = state.copyWith(isLoading: true);
    try {
      final message = await _authRepository.unlinkSocial(provider);
      await refreshUser();
      return message;
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别（经 AppFailure
      // 类型化判定，勿存 e.toString()）。
      debugPrint('[auth] account-security op failed: $e');
      state = state.copyWith(error: AppFailureMapper.from(e).uiErrorCategory);
      rethrow;
    } finally {
      // carry-over 与 login 家族 finally 同型：copyWith 对 error 是直接
      // 赋值语义，不显式带旧值会把刚写入的类别抹回 null。
      state = state.copyWith(
        isLoading: false,
        error: state.error,
        failure: state.failure,
      );
    }
  }

  Future<List<UserSessionModel>> getSessions() => _authRepository.getSessions();

  Future<String> revokeSession(String sessionId) async {
    state = state.copyWith(isLoading: true);
    try {
      return await _authRepository.revokeSession(sessionId);
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别（经 AppFailure
      // 类型化判定，勿存 e.toString()）。
      debugPrint('[auth] account-security op failed: $e');
      state = state.copyWith(error: AppFailureMapper.from(e).uiErrorCategory);
      rethrow;
    } finally {
      // carry-over 与 login 家族 finally 同型：copyWith 对 error 是直接
      // 赋值语义，不显式带旧值会把刚写入的类别抹回 null。
      state = state.copyWith(
        isLoading: false,
        error: state.error,
        failure: state.failure,
      );
    }
  }

  Future<String> revokeOtherSessions() async {
    state = state.copyWith(isLoading: true);
    try {
      return await _authRepository.revokeOtherSessions();
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别（经 AppFailure
      // 类型化判定，勿存 e.toString()）。
      debugPrint('[auth] account-security op failed: $e');
      state = state.copyWith(error: AppFailureMapper.from(e).uiErrorCategory);
      rethrow;
    } finally {
      // carry-over 与 login 家族 finally 同型：copyWith 对 error 是直接
      // 赋值语义，不显式带旧值会把刚写入的类别抹回 null。
      state = state.copyWith(
        isLoading: false,
        error: state.error,
        failure: state.failure,
      );
    }
  }

  Future<List<AuthAuditLogModel>> getSecurityLog({
    int limit = 20,
    int offset = 0,
  }) =>
      _authRepository.getSecurityLog(limit: limit, offset: offset);

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
      // N15：原始异常只进日志；错误字段存类型化类别（经 AppFailure
      // 类型化判定，勿存 e.toString()）。
      debugPrint('[auth] account-security op failed: $e');
      state = state.copyWith(error: AppFailureMapper.from(e).uiErrorCategory);
      rethrow;
    } finally {
      // carry-over 与 login 家族 finally 同型：copyWith 对 error 是直接
      // 赋值语义，不显式带旧值会把刚写入的类别抹回 null。
      state = state.copyWith(
        isLoading: false,
        error: state.error,
        failure: state.failure,
      );
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
      await _ref.read(guestServiceProvider).clearGuestData();
      state = state.copyWith(isAuthenticated: true, user: user);
      SessionRefreshService.refreshSessionBoundProviders(_ref);
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别（经 AppFailure
      // 类型化判定，勿存 e.toString()）。
      debugPrint('[auth] account-security op failed: $e');
      state = state.copyWith(error: AppFailureMapper.from(e).uiErrorCategory);
      rethrow;
    } finally {
      // carry-over 与 login 家族 finally 同型：copyWith 对 error 是直接
      // 赋值语义，不显式带旧值会把刚写入的类别抹回 null。
      state = state.copyWith(
        isLoading: false,
        error: state.error,
        failure: state.failure,
      );
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
      await _ref.read(guestServiceProvider).clearGuestData();
      state = state.copyWith(isAuthenticated: true, user: user);
      SessionRefreshService.refreshSessionBoundProviders(_ref);
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别（经 AppFailure
      // 类型化判定，勿存 e.toString()）。
      debugPrint('[auth] account-security op failed: $e');
      state = state.copyWith(error: AppFailureMapper.from(e).uiErrorCategory);
      rethrow;
    } finally {
      // carry-over 与 login 家族 finally 同型：copyWith 对 error 是直接
      // 赋值语义，不显式带旧值会把刚写入的类别抹回 null。
      state = state.copyWith(
        isLoading: false,
        error: state.error,
        failure: state.failure,
      );
    }
  }

  Future<void> logout() async {
    // 注销开启新世代：作废所有在途登录/会话检查的 state 写入。
    _beginSessionOp();
    await _authRepository.logout();
    await _clearUserScopedLocalData();
    await _ref
        .read(sharedPreferencesProvider)
        .setBool(_demoGuestModePreferenceKey, false);
    DemoDataService.isDemoMode = false;
    state = AuthState(); // Reset to initial state
    SessionRefreshService.refreshSessionBoundProviders(_ref);
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
