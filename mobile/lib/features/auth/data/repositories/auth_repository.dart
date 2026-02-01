import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/auth/data/models/token_model.dart';
import 'package:sparkle/shared/entities/user_model.dart';

// Keys for Secure Storage
const String _accessTokenKey = 'accessToken';
const String _refreshTokenKey = 'refreshToken';

class AuthRepository {
  AuthRepository(this._apiClient, this._storage);
  final ApiClient _apiClient;
  final FlutterSecureStorage _storage;

  Future<UserModel> register(
      String username, String email, String password,) async {
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
        },
      );
      // Assuming registration returns the user and tokens directly
      final data = response.data;
      final tokenResponse = TokenResponse.fromJson(data!['token'] as Map<String, dynamic>);
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
        await saveTokens(TokenResponse(
          accessToken: 'demo_token',
          refreshToken: 'demo_refresh_token',
          expiresIn: 3600,
        ),);
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
        await saveTokens(TokenResponse(
          accessToken: 'demo',
          refreshToken: 'demo',
          expiresIn: 3600,
        ),);
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
      return UserModel.fromJson(data['user'] as Map<String, dynamic>);
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

  Future<void> logout() async {
    if (DemoDataService.isDemoMode) {
      DemoDataService.isDemoMode = false;
      return;
    }
    // In a real app, you might want to call a server endpoint to invalidate the token
    await clearTokens();
  }

  Future<TokenResponse> refreshToken() async {
    if (DemoDataService.isDemoMode) {
      return TokenResponse(
        accessToken: 'demo',
        refreshToken: 'demo',
        expiresIn: 3600,
      );
    }
    final refreshToken = await getRefreshToken();
    if (refreshToken == null) {
      throw Exception('No refresh token available.');
    }
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.refresh,
        data: {'refresh_token': refreshToken},
      );
      final tokenResponse = TokenResponse.fromJson(response.data!);
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
      final response = await _apiClient.get<Map<String, dynamic>>(ApiEndpoints.me);
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
      final response = await _apiClient.put<Map<String, dynamic>>(ApiEndpoints.me, data: data);
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

  Future<void> saveTokens(TokenResponse tokenResponse) async {
    await _storage.write(
        key: _accessTokenKey, value: tokenResponse.accessToken,);
    await _storage.write(
        key: _refreshTokenKey, value: tokenResponse.refreshToken,);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
  }

  Future<String?> getAccessToken() async => _storage.read(key: _accessTokenKey);

  // Alias for getAccessToken to match usage in ApiInterceptor
  Future<String?> getToken() => getAccessToken();

  Future<String?> getRefreshToken() async =>
      _storage.read(key: _refreshTokenKey);

  Future<bool> isLoggedIn() async {
    if (DemoDataService.isDemoMode) return true;
    return await getAccessToken() != null;
  }

  /// Guest login - 获取访客模式的JWT token
  /// 🎭 演示模式：仍然尝试获取真实token以保证LLM功能可用
  /// 只有历史数据使用预设内容
  Future<UserModel> guestLogin(String guestId) async {
    try {
      // 🎭 始终尝试获取真实token，保证LLM对话功能可用
      final response = await _apiClient.post<Map<String, dynamic>>(
        '/auth/guest',
        data: {'guest_id': guestId},
      );

      final data = response.data!;
      final tokenData = data['token'] is Map<String, dynamic>
          ? data['token'] as Map<String, dynamic>
          : data;

      final tokenResponse = TokenResponse.fromJson(tokenData);
      await saveTokens(tokenResponse);

      // 如果是演示模式，返回演示用户，但使用真实token
      if (DemoDataService.isDemoMode) {
        return DemoDataService().demoUser;
      }

      return UserModel.fromJson(data['user'] as Map<String, dynamic>);
    } on DioException catch (e) {
      // 🎭 如果API失败但处于演示模式，返回演示用户（没有有效token）
      if (DemoDataService.isDemoMode) {
        debugPrint('⚠️ Guest API failed, using demo user without token: $e');
        return DemoDataService().demoUser;
      }
      final message = _extractErrorMessage(e.response?.data);
      throw Exception(message ?? '访客登录失败');
    } catch (e) {
      // 🎭 如果API失败但处于演示模式，返回演示用户（没有有效token）
      if (DemoDataService.isDemoMode) {
        debugPrint('⚠️ Guest API failed, using demo user without token: $e');
        return DemoDataService().demoUser;
      }
      throw Exception('An unexpected error occurred: $e');
    }
  }
}

// Provider for FlutterSecureStorage
final flutterSecureStorageProvider =
    Provider<FlutterSecureStorage>((ref) => const FlutterSecureStorage(
          aOptions: AndroidOptions(encryptedSharedPreferences: true),
          iOptions: IOSOptions(
            accessibility: KeychainAccessibility.first_unlock,
          ),
        ),);

// Provider for AuthRepository
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final storage = ref.watch(flutterSecureStorageProvider);

  return AuthRepository(apiClient, storage);
});
