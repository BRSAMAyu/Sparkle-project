import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/data/models/api_response_model.dart';
import 'package:sparkle/data/models/user_model.dart';
import 'package:sparkle/core/services/demo_data_service.dart';

// Keys for Secure Storage
const String _accessTokenKey = 'accessToken';
const String _refreshTokenKey = 'refreshToken';

class AuthRepository {
  final ApiClient _apiClient;
  final FlutterSecureStorage _storage;

  AuthRepository(this._apiClient, this._storage);

  Future<UserModel> register(String username, String email, String password) async {
    try {
      if (DemoDataService.isDemoMode) {
        return DemoDataService().demoUser;
      }
      final response = await _apiClient.post(
        ApiEndpoints.register,
        data: {
          'username': username,
          'email': email,
          'password': password,
        },
      );
      // Assuming registration returns the user and tokens directly
      final tokenResponse = TokenResponse.fromJson(response.data['token']);
      await saveTokens(tokenResponse);
      return UserModel.fromJson(response.data['user']);
    } on DioException catch (e) {
      // Handle Dio-specific errors
      throw e.response?.data['detail'] ?? 'Registration failed';
    } catch (e) {
      throw 'An unexpected error occurred';
    }
  }

  Future<TokenResponse> login(String usernameOrEmail, String password) async {
    try {
      if (DemoDataService.isDemoMode) {
        // Should not happen via this method usually, but for safety
        return TokenResponse(
          accessToken: 'demo_token', 
          refreshToken: 'demo_refresh_token', 
          tokenType: 'bearer',
          expiresIn: 3600,
        );
      }
      final response = await _apiClient.post(
        ApiEndpoints.login,
        data: {
          'username': usernameOrEmail,
          'password': password,
        },
      );
      final tokenResponse = TokenResponse.fromJson(response.data);
      await saveTokens(tokenResponse);
      return tokenResponse;
    } on DioException catch (e) {
      throw e.response?.data['detail'] ?? 'Login failed';
    } catch (e) {
      throw 'An unexpected error occurred';
    }
  }

  Future<TokenResponse> socialLogin({
    required String provider,
    required String token,
    String? email,
    String? nickname,
    String? avatarUrl,
  }) async {
    try {
      if (DemoDataService.isDemoMode) {
        return TokenResponse(
          accessToken: 'demo', 
          refreshToken: 'demo', 
          tokenType: 'bearer',
          expiresIn: 3600,
        );
      }
      final endpoint = provider == 'apple' ? '/auth/apple' : '/auth/social-login';
      final response = await _apiClient.post(
        endpoint,
        data: {
          'provider': provider,
          'token': token,
          'email': email,
          'nickname': nickname,
          'avatar_url': avatarUrl,
        },
      );

      final tokenResponse = TokenResponse.fromJson(response.data);
      await saveTokens(tokenResponse);
      return tokenResponse;
    } on DioException catch (e) {
      throw e.response?.data['detail'] ?? 'Social login failed';
    } catch (e) {
      throw 'An unexpected error occurred: $e';
    }
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
        tokenType: 'bearer',
        expiresIn: 3600,
      );
    }
    final refreshToken = await getRefreshToken();
    if (refreshToken == null) {
      throw 'No refresh token available.';
    }
    try {
       final response = await _apiClient.post(
        ApiEndpoints.refresh,
        data: {'refresh_token': refreshToken},
      );
      final tokenResponse = TokenResponse.fromJson(response.data);
      await saveTokens(tokenResponse);
      return tokenResponse;
    } on DioException catch (e) {
      await clearTokens(); // Clear tokens if refresh fails
      throw e.response?.data['detail'] ?? 'Session expired. Please log in again.';
    } catch(e) {
      await clearTokens();
      throw 'An unexpected error occurred during token refresh.';
    }
  }

  Future<UserModel> getCurrentUser() async {
    try {
      if (DemoDataService.isDemoMode) {
        return DemoDataService().demoUser;
      }
      final response = await _apiClient.get(ApiEndpoints.me);
      return UserModel.fromJson(response.data);
    } on DioException catch (e) {
      throw e.response?.data['detail'] ?? 'Could not fetch user profile.';
    } catch (e) {
      throw 'An unexpected error occurred';
    }
  }

  Future<UserModel> updateProfile(Map<String, dynamic> data) async {
    try {
      if (DemoDataService.isDemoMode) {
        return DemoDataService().demoUser;
      }
      final response = await _apiClient.put(ApiEndpoints.me, data: data);
      return UserModel.fromJson(response.data);
    } on DioException catch (e) {
      throw e.response?.data['detail'] ?? 'Could not update profile.';
    } catch (e) {
      throw 'An unexpected error occurred';
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

      final response = await _apiClient.post(
        '${ApiEndpoints.me}/avatar',
        data: formData,
      );
      return UserModel.fromJson(response.data);
    } on DioException catch (e) {
      throw e.response?.data['detail'] ?? 'Could not update avatar.';
    } catch (e) {
      throw 'An unexpected error occurred';
    }
  }

  Future<void> changePassword(String oldPassword, String newPassword) async {
    try {
      if (DemoDataService.isDemoMode) {
        return;
      }
      await _apiClient.post(
        '${ApiEndpoints.me}/password',
        data: {
          'old_password': oldPassword,
          'new_password': newPassword,
        },
      );
    } on DioException catch (e) {
      throw e.response?.data['detail'] ?? 'Could not change password.';
    } catch (e) {
      throw 'An unexpected error occurred';
    }
  }

  Future<void> saveTokens(TokenResponse tokenResponse) async {
    await _storage.write(key: _accessTokenKey, value: tokenResponse.accessToken);
    await _storage.write(key: _refreshTokenKey, value: tokenResponse.refreshToken);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
  }

  Future<String?> getAccessToken() async {
    return await _storage.read(key: _accessTokenKey);
  }

  // Alias for getAccessToken to match usage in ApiInterceptor
  Future<String?> getToken() => getAccessToken();
  
  Future<String?> getRefreshToken() async {
    return await _storage.read(key: _refreshTokenKey);
  }

  Future<bool> isLoggedIn() async {
    if (DemoDataService.isDemoMode) return true;
    return await getAccessToken() != null;
  }
}

// Provider for FlutterSecureStorage
final flutterSecureStorageProvider = Provider<FlutterSecureStorage>((ref) {
  return const FlutterSecureStorage();
});


// Provider for AuthRepository
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final storage = ref.watch(flutterSecureStorageProvider);

  return AuthRepository(apiClient, storage);
});