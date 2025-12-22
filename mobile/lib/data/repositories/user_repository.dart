import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/data/models/user_model.dart';

class UserRepository {
  final ApiClient _apiClient;

  UserRepository(this._apiClient);

  /// 更新用户学习偏好
  Future<UserModel> updateUserPreferences(UserPreferencesModel preferences) async {
    try {
      final response = await _apiClient.put(
        '/users/me/preferences', 
        data: preferences.toJson(),
      );
      return UserModel.fromJson(response.data);
    } catch (e) {
      rethrow;
    }
  }

  /// 更新推送偏好
  Future<UserModel> updatePushPreferences(PushPreferences prefs) async {
    try {
      // Assuming a dedicated endpoint or patching the user profile
      // For now, let's assume we patch the user profile with a nested 'push_preference' object
      // or a specific endpoint. 
      // If backend logic was "update User model", likely we send data to /users/me
      // But usually updating relations is cleaner via specific endpoint.
      // Let's assume PATCH /api/v1/users/me/push-preference based on common patterns
      // If not, we can adjust.
      
      final response = await _apiClient.put(
        '/users/me/push-preference', 
        data: prefs.toJson(),
      );
      return UserModel.fromJson(response.data);
    } catch (e) {
      rethrow;
    }
  }
}

final userRepositoryProvider = Provider<UserRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return UserRepository(apiClient);
});

