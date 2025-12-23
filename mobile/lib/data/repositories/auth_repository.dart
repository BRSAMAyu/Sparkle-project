import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/data/models/api_response_model.dart';
import 'package:sparkle/data/models/user_model.dart';

// Keys for SharedPreferences
const String _accessTokenKey = 'accessToken';
const String _refreshTokenKey = 'refreshToken';

class AuthRepository {
  final ApiClient _apiClient;
  final SharedPreferences _prefs;

  AuthRepository(this._apiClient, this._prefs);

  Future<UserModel> register(String username, String email, String password) async {
    try {
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
      final response = await _apiClient.post(
        '/auth/social-login', // Assuming endpoint is relative to base URL prefix
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
    // In a real app, you might want to call a server endpoint to invalidate the token
    await clearTokens();
  }

  Future<TokenResponse> refreshToken() async {
    final refreshToken = getRefreshToken();
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
      final response = await _apiClient.put(ApiEndpoints.me, data: data);
      return UserModel.fromJson(response.data);
    } on DioException catch (e) {
      throw e.response?.data['detail'] ?? 'Could not update profile.';
    } catch (e) {
      throw 'An unexpected error occurred';
    }
  }

  Future<void> saveTokens(TokenResponse tokenResponse) async {
    await _prefs.setString(_accessTokenKey, tokenResponse.accessToken);
    await _prefs.setString(_refreshTokenKey, tokenResponse.refreshToken);
  }

  Future<void> clearTokens() async {
    await _prefs.remove(_accessTokenKey);
    await _prefs.remove(_refreshTokenKey);
  }

  String? getAccessToken() {
    return _prefs.getString(_accessTokenKey);
  }

  // Alias for getAccessToken to match usage in ApiInterceptor
  String? getToken() => getAccessToken();
  
  String? getRefreshToken() {
    return _prefs.getString(_refreshTokenKey);
  }

  bool isLoggedIn() {
    return getAccessToken() != null;
  }
}

// Provider for SharedPreferences - will be overridden in main.dart with preloaded instance
final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('SharedPreferences must be overridden in main.dart');
});


// Provider for AuthRepository
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final sharedPrefs = ref.watch(sharedPreferencesProvider);

  return AuthRepository(apiClient, sharedPrefs);
});
