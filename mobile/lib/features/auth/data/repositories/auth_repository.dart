import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/auth/data/models/token_model.dart';
import 'package:sparkle/features/user/data/models/account_security_model.dart';
import 'package:sparkle/shared/entities/user_model.dart';

const String _legacyAccessTokenKey = 'accessToken';
const String _legacyRefreshTokenKey = 'refreshToken';

class AuthRepository {
  AuthRepository(this._apiClient, this._storage);
  final ApiClient _apiClient;
  final FlutterSecureStorage _storage;

  Future<UserModel> register(
    String username,
    String email,
    String password, {
    required bool acceptedTos,
    required bool acceptedPrivacy,
    String tosVersion = 'v1',
    String privacyVersion = 'v1',
    String? agreedLocale,
  }) async {
    try {
      if (DemoDataService.isDemoMode) {
        return DemoDataService().demoUser;
      }
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.register,
        data: {
          'username': username,
          'email': email,
          'password': password,
          'accepted_tos': acceptedTos,
          'accepted_privacy': acceptedPrivacy,
          'tos_version': tosVersion,
          'privacy_version': privacyVersion,
          'agreed_locale': agreedLocale,
        },
      );
      // Assuming registration returns the user and tokens directly
      final data = response.data;
      final tokenData = data!['token'] as Map<String, dynamic>? ?? data;
      final tokenResponse = TokenResponse.fromJson(tokenData);
      await saveTokens(tokenResponse);
      return UserModel.fromJson(data['user'] as Map<String, dynamic>);
    } on DioException catch (e) {
      final message = _extractErrorMessage(e.response?.data);
      throw Exception(message ?? 'Registration failed');
    } catch (e) {
      throw Exception('An unexpected error occurred: $e');
    }
  }

  Future<UserModel> login(String usernameOrEmail, String password) async {
    try {
      if (DemoDataService.isDemoMode) {
        // Should not happen via this method usually, but for safety
        await saveTokens(
          TokenResponse(
            accessToken: 'demo_token',
            refreshToken: 'demo_refresh_token',
            expiresIn: 3600,
          ),
        );
        return DemoDataService().demoUser;
      }
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.login,
        data: {
          'username': usernameOrEmail,
          'password': password,
        },
      );
      final data = response.data!;
      // Use the nested token object if available (new structure), otherwise fallback to root (old structure)
      final tokenData = data['token'] is Map<String, dynamic>
          ? data['token'] as Map<String, dynamic>
          : data;

      final tokenResponse = TokenResponse.fromJson(tokenData);
      await saveTokens(tokenResponse);

      return UserModel.fromJson(data['user'] as Map<String, dynamic>);
    } on DioException catch (e) {
      final message = _extractErrorMessage(e.response?.data);
      throw Exception(message ?? 'Login failed');
    } catch (e) {
      throw Exception('An unexpected error occurred: $e');
    }
  }

  Future<UserModel> socialLogin({
    required String provider,
    required String token,
    String? openid,
    String? email,
    String? nickname,
    String? avatarUrl,
  }) async {
    try {
      if (DemoDataService.isDemoMode) {
        await saveTokens(
          TokenResponse(
            accessToken: 'demo',
            refreshToken: 'demo',
            expiresIn: 3600,
          ),
        );
        return DemoDataService().demoUser;
      }
      final endpoint =
          provider == 'apple' ? '/auth/apple' : '/auth/social-login';
      final response = await _apiClient.post<Map<String, dynamic>>(
        endpoint,
        data: {
          'provider': provider,
          'token': token,
          if (openid != null) 'openid': openid,
          'email': email,
          'nickname': nickname,
          'avatar_url': avatarUrl,
        },
      );

      final data = response.data!;
      // Use the nested token object if available (new structure), otherwise fallback to root (old structure)
      final tokenData = data['token'] is Map<String, dynamic>
          ? data['token'] as Map<String, dynamic>
          : data;

      final tokenResponse = TokenResponse.fromJson(tokenData);
      await saveTokens(tokenResponse);
      final userData = data['user'] as Map<String, dynamic>?;
      final hasFullProfile = userData != null &&
          userData.containsKey('flame_level') &&
          userData.containsKey('created_at') &&
          userData.containsKey('updated_at');
      if (!hasFullProfile) {
        return await getCurrentUser();
      }
      return UserModel.fromJson(userData);
    } on DioException catch (e) {
      final message = _extractErrorMessage(e.response?.data);
      throw Exception(message ?? 'Social login failed');
    } catch (e) {
      throw Exception('An unexpected error occurred: $e');
    }
  }

  String? _extractErrorMessage(dynamic data) {
    if (data == null) return null;
    if (data is String) return data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'] ?? data['message'] ?? data['error'];
      if (detail is String) return detail;
      if (detail != null) return detail.toString();
    }
    return data.toString();
  }

  Future<void> logout({bool keepDemoMode = false}) async {
    if (DemoDataService.isDemoMode) {
      if (!keepDemoMode) {
        DemoDataService.isDemoMode = false;
      }
      await clearTokens();
      return;
    }
    // Attempt server-side logout (token revocation), but always clear local tokens.
    try {
      final refreshToken = await getRefreshToken();
      await _apiClient.post<dynamic>(
        ApiEndpoints.logout,
        data: {
          if (refreshToken != null && refreshToken.isNotEmpty)
            'refresh_token': refreshToken,
        },
      );
    } catch (_) {
      // Ignore network errors; client-side logout should still proceed.
    } finally {
      await clearTokens();
    }
  }

  Future<TokenResponse> refreshToken() async {
    final currentRefreshToken = await getRefreshToken();
    if (currentRefreshToken == null || currentRefreshToken.isEmpty) {
      await clearTokens();
      throw Exception('Session expired. Please log in again.');
    }
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.refresh,
        data: {'refresh_token': currentRefreshToken},
      );
      final data = response.data ?? const <String, dynamic>{};
      final refreshedAccessToken = data['access_token'] as String?;
      if (refreshedAccessToken == null || refreshedAccessToken.isEmpty) {
        throw Exception('Refresh response missing access token.');
      }
      final tokenResponse = TokenResponse(
        accessToken: refreshedAccessToken,
        refreshToken: (data['refresh_token'] as String?) ?? currentRefreshToken,
        tokenType: (data['token_type'] as String?) ?? 'bearer',
        expiresIn: data['expires_in'] as int?,
      );
      await saveTokens(tokenResponse);
      return tokenResponse;
    } on DioException catch (e) {
      await clearTokens(); // Clear tokens if refresh fails
      final detail =
          (e.response?.data as Map<String, dynamic>?)?['detail'] as String?;
      throw Exception(
        detail ?? 'Session expired. Please log in again.',
      );
    } catch (e) {
      await clearTokens();
      throw Exception('An unexpected error occurred during token refresh.');
    }
  }

  Future<UserModel> getCurrentUser() async {
    try {
      if (DemoDataService.isDemoMode) {
        return DemoDataService().demoUser;
      }
      final response =
          await _apiClient.get<Map<String, dynamic>>(ApiEndpoints.me);
      return UserModel.fromJson(response.data!);
    } on DioException catch (e) {
      final detail =
          (e.response?.data as Map<String, dynamic>?)?['detail'] as String?;
      throw Exception(detail ?? 'Could not fetch user profile.');
    } catch (e) {
      throw Exception('An unexpected error occurred');
    }
  }

  Future<UserModel> updateProfile(Map<String, dynamic> data) async {
    try {
      if (DemoDataService.isDemoMode) {
        return DemoDataService().demoUser;
      }
      final response = await _apiClient
          .put<Map<String, dynamic>>(ApiEndpoints.me, data: data);
      return UserModel.fromJson(response.data!);
    } on DioException catch (e) {
      final detail =
          (e.response?.data as Map<String, dynamic>?)?['detail'] as String?;
      throw Exception(detail ?? 'Could not update profile.');
    } catch (e) {
      throw Exception('An unexpected error occurred');
    }
  }

  Future<UserModel> updateAvatar(String filePath) async {
    try {
      if (DemoDataService.isDemoMode) {
        DemoDataService().updateDemoAvatar(filePath);
        return DemoDataService().demoUser;
      }

      // If it's a network URL (from system presets), use updateProfile instead of upload
      if (filePath.startsWith('http')) {
        return await updateProfile({'avatar_url': filePath});
      }

      final formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(filePath),
      });

      final response = await _apiClient.post<Map<String, dynamic>>(
        '${ApiEndpoints.me}/avatar',
        data: formData,
      );
      return UserModel.fromJson(response.data!);
    } on DioException catch (e) {
      final detail =
          (e.response?.data as Map<String, dynamic>?)?['detail'] as String?;
      throw Exception(detail ?? 'Could not update avatar.');
    } catch (e) {
      throw Exception('An unexpected error occurred');
    }
  }

  Future<void> changePassword(String oldPassword, String newPassword) async {
    try {
      if (DemoDataService.isDemoMode) {
        return;
      }
      await _apiClient.post<dynamic>(
        '${ApiEndpoints.me}/password',
        data: {
          'old_password': oldPassword,
          'new_password': newPassword,
        },
      );
    } on DioException catch (e) {
      final detail =
          (e.response?.data as Map<String, dynamic>?)?['detail'] as String?;
      throw Exception(detail ?? 'Could not change password.');
    } catch (e) {
      throw Exception('An unexpected error occurred');
    }
  }

  Future<String> setPassword(String newPassword) async {
    try {
      if (DemoDataService.isDemoMode) {
        return '密码设置成功';
      }
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.setPassword,
        data: {'new_password': newPassword},
      );
      return _extractErrorMessage(response.data) ?? '密码设置成功';
    } on DioException catch (e) {
      final detail =
          (e.response?.data as Map<String, dynamic>?)?['detail'] as String?;
      throw Exception(detail ?? 'Could not set password.');
    } catch (e) {
      throw Exception('An unexpected error occurred');
    }
  }

  Future<String> forgotPassword(String email) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.forgotPassword,
        data: {'email': email},
      );
      return _extractErrorMessage(response.data) ?? '如果该邮箱已注册，重置邮件已发送';
    } on DioException catch (e) {
      final message = _extractErrorMessage(e.response?.data);
      throw Exception(message ?? 'Could not request password reset.');
    } catch (e) {
      throw Exception('An unexpected error occurred');
    }
  }

  Future<String> resetPasswordWithToken(
    String token,
    String newPassword,
  ) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.resetPassword,
        data: {
          'token': token,
          'new_password': newPassword,
        },
      );
      return _extractErrorMessage(response.data) ?? '密码已重置，请重新登录';
    } on DioException catch (e) {
      final message = _extractErrorMessage(e.response?.data);
      throw Exception(message ?? 'Could not reset password.');
    } catch (e) {
      throw Exception('An unexpected error occurred');
    }
  }

  Future<String> sendVerificationEmail() async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.sendVerification,
      );
      return _extractErrorMessage(response.data) ?? '验证邮件已发送';
    } on DioException catch (e) {
      final message = _extractErrorMessage(e.response?.data);
      throw Exception(message ?? 'Could not send verification email.');
    } catch (e) {
      throw Exception('An unexpected error occurred');
    }
  }

  Future<String> verifyEmail(String token) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.verifyEmail,
        data: {'token': token},
      );
      return _extractErrorMessage(response.data) ?? '邮箱验证成功';
    } on DioException catch (e) {
      final message = _extractErrorMessage(e.response?.data);
      throw Exception(message ?? 'Could not verify email.');
    } catch (e) {
      throw Exception('An unexpected error occurred');
    }
  }

  Future<List<SocialAccountStatusModel>> getSocialAccounts() async {
    final response =
        await _apiClient.get<List<dynamic>>(ApiEndpoints.socialAccounts);
    final data = response.data ?? const <dynamic>[];
    return data
        .whereType<Map<String, dynamic>>()
        .map(SocialAccountStatusModel.fromJson)
        .toList();
  }

  Future<String> linkSocial({
    required String provider,
    required String token,
    String? openid,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.linkSocial,
        data: {
          'provider': provider,
          'token': token,
          if (openid != null) 'openid': openid,
        },
      );
      return _extractErrorMessage(response.data) ?? '绑定成功';
    } on DioException catch (e) {
      throw Exception(_extractErrorMessage(e.response?.data) ??
          'Could not link social account.',);
    }
  }

  Future<String> unlinkSocial(String provider) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.unlinkSocial,
        data: {'provider': provider},
      );
      return _extractErrorMessage(response.data) ?? '解绑成功';
    } on DioException catch (e) {
      throw Exception(_extractErrorMessage(e.response?.data) ??
          'Could not unlink social account.',);
    }
  }

  Future<List<UserSessionModel>> getSessions() async {
    final response =
        await _apiClient.get<List<dynamic>>(ApiEndpoints.userSessions);
    final data = response.data ?? const <dynamic>[];
    return data
        .whereType<Map<String, dynamic>>()
        .map(UserSessionModel.fromJson)
        .toList();
  }

  Future<String> revokeSession(String sessionId) async {
    try {
      final response = await _apiClient.delete<Map<String, dynamic>>(
        '${ApiEndpoints.userSessions}/$sessionId',
      );
      return _extractErrorMessage(response.data) ?? '设备已下线';
    } on DioException catch (e) {
      throw Exception(_extractErrorMessage(e.response?.data) ??
          'Could not revoke session.',);
    }
  }

  Future<String> revokeOtherSessions() async {
    try {
      final response = await _apiClient.delete<Map<String, dynamic>>(
        ApiEndpoints.userSessions,
      );
      return _extractErrorMessage(response.data) ?? '其他设备已下线';
    } on DioException catch (e) {
      throw Exception(_extractErrorMessage(e.response?.data) ??
          'Could not revoke other sessions.',);
    }
  }

  Future<List<AuthAuditLogModel>> getSecurityLog() async {
    final response =
        await _apiClient.get<List<dynamic>>(ApiEndpoints.securityLog);
    final data = response.data ?? const <dynamic>[];
    return data
        .whereType<Map<String, dynamic>>()
        .map(AuthAuditLogModel.fromJson)
        .toList();
  }

  Future<String> deleteAccount({
    required String confirmation,
    String? password,
    String? provider,
    String? providerToken,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.deleteAccount,
        data: {
          'confirmation': confirmation,
          if (password != null && password.isNotEmpty) 'password': password,
          if (provider != null) 'provider': provider,
          if (providerToken != null && providerToken.isNotEmpty)
            'provider_token': providerToken,
        },
      );
      return _extractErrorMessage(response.data) ?? '账号已注销';
    } on DioException catch (e) {
      throw Exception(_extractErrorMessage(e.response?.data) ??
          'Could not delete account.',);
    }
  }

  Future<UserModel> upgradeGuest({
    required String username,
    required String email,
    required String password,
    required bool acceptedTos,
    required bool acceptedPrivacy,
    String tosVersion = 'v1',
    String privacyVersion = 'v1',
    String? agreedLocale,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.upgradeGuest,
        data: {
          'username': username,
          'email': email,
          'password': password,
          'accepted_tos': acceptedTos,
          'accepted_privacy': acceptedPrivacy,
          'tos_version': tosVersion,
          'privacy_version': privacyVersion,
          'agreed_locale': agreedLocale,
        },
      );
      final data = response.data!;
      final tokenData = data['token'] as Map<String, dynamic>? ?? data;
      await saveTokens(TokenResponse.fromJson(tokenData));
      return UserModel.fromJson(data['user'] as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_extractErrorMessage(e.response?.data) ??
          'Could not upgrade guest account.',);
    }
  }

  Future<UserModel> upgradeGuestWithSocial({
    required String provider,
    required String token,
    required bool acceptedTos,
    required bool acceptedPrivacy,
    String tosVersion = 'v1',
    String privacyVersion = 'v1',
    String? agreedLocale,
    String? openid,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.upgradeGuestSocial,
        data: {
          'provider': provider,
          'token': token,
          if (openid != null) 'openid': openid,
          'accepted_tos': acceptedTos,
          'accepted_privacy': acceptedPrivacy,
          'tos_version': tosVersion,
          'privacy_version': privacyVersion,
          'agreed_locale': agreedLocale,
        },
      );
      final data = response.data!;
      final tokenData = data['token'] as Map<String, dynamic>? ?? data;
      await saveTokens(TokenResponse.fromJson(tokenData));
      return UserModel.fromJson(data['user'] as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_extractErrorMessage(e.response?.data) ??
          'Could not upgrade guest account.',);
    }
  }

  Future<void> saveTokens(TokenResponse tokenResponse) async {
    await _storage.write(
      key: AppConstants.keyAccessToken,
      value: tokenResponse.accessToken,
    );
    if (tokenResponse.refreshToken != null &&
        tokenResponse.refreshToken!.isNotEmpty) {
      await _storage.write(
        key: AppConstants.keyRefreshToken,
        value: tokenResponse.refreshToken,
      );
    } else {
      await _storage.delete(key: AppConstants.keyRefreshToken);
      await _storage.delete(key: _legacyRefreshTokenKey);
    }

    // Keep legacy keys during migration so older code paths do not lose session.
    await _storage.write(
      key: _legacyAccessTokenKey,
      value: tokenResponse.accessToken,
    );
    if (tokenResponse.refreshToken != null &&
        tokenResponse.refreshToken!.isNotEmpty) {
      await _storage.write(
        key: _legacyRefreshTokenKey,
        value: tokenResponse.refreshToken,
      );
    }
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: AppConstants.keyAccessToken);
    await _storage.delete(key: AppConstants.keyRefreshToken);
    await _storage.delete(key: _legacyAccessTokenKey);
    await _storage.delete(key: _legacyRefreshTokenKey);
  }

  Future<String?> getAccessToken() async => _readToken(
        primaryKey: AppConstants.keyAccessToken,
        legacyKey: _legacyAccessTokenKey,
      );

  // Alias for getAccessToken to match usage in ApiInterceptor
  Future<String?> getToken() => getAccessToken();

  Future<String?> getRefreshToken() async => _readToken(
        primaryKey: AppConstants.keyRefreshToken,
        legacyKey: _legacyRefreshTokenKey,
      );

  Future<bool> isLoggedIn() async {
    if (DemoDataService.isDemoMode) return true;
    return await getAccessToken() != null;
  }

  /// Guest login - 优先使用后端真实数据，失败时回退到本地演示数据
  Future<UserModel> guestLogin(String guestId) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        '/auth/guest',
        queryParameters: {'guest_id': guestId},
      );

      final data = response.data!;
      final tokenData = data['token'] is Map<String, dynamic>
          ? data['token'] as Map<String, dynamic>
          : data;

      final tokenResponse = TokenResponse.fromJson(tokenData);
      await saveTokens(tokenResponse);

      return UserModel.fromJson(data['user'] as Map<String, dynamic>);
    } on DioException catch (e) {
      // 后端不可用时回退到本地演示数据，保证离线/开发时可用
      if (DemoDataService.isDemoMode) {
        debugPrint('⚠️ Guest API failed, using demo user as fallback: $e');
        return DemoDataService().demoUser;
      }
      final message = _extractErrorMessage(e.response?.data);
      throw Exception(message ?? '访客登录失败');
    } catch (e) {
      if (DemoDataService.isDemoMode) {
        debugPrint('⚠️ Guest API failed, using demo user as fallback: $e');
        return DemoDataService().demoUser;
      }
      throw Exception('An unexpected error occurred: $e');
    }
  }

  Future<String?> _readToken({
    required String primaryKey,
    required String legacyKey,
  }) async {
    final primaryValue = await _storage.read(key: primaryKey);
    if (primaryValue != null && primaryValue.isNotEmpty) {
      return primaryValue;
    }

    final legacyValue = await _storage.read(key: legacyKey);
    if (legacyValue != null && legacyValue.isNotEmpty) {
      await _storage.write(key: primaryKey, value: legacyValue);
      return legacyValue;
    }

    return null;
  }
}

// Provider for FlutterSecureStorage
final flutterSecureStorageProvider = Provider<FlutterSecureStorage>(
  (ref) => const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock,
    ),
  ),
);

// Provider for AuthRepository
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final storage = ref.watch(flutterSecureStorageProvider);

  return AuthRepository(apiClient, storage);
});
