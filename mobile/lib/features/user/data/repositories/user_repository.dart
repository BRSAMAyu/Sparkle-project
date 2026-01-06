import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/shared/entities/user_model.dart';

class UserRepository {
  UserRepository(this._apiClient);
  final ApiClient _apiClient;

  /// 更新用户学习偏好
  Future<UserModel> updateUserPreferences(UserPreferences preferences) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoUser; // Mock update
    }
    try {
      final response = await _apiClient.put<Map<String, dynamic>>(
        '/users/me/preferences',
        data: preferences.toJson(),
      );
      final payload = response.data;
      if (payload == null) {
        throw Exception('Failed to update preferences');
      }
      return UserModel.fromJson(payload);
    } catch (e) {
      rethrow;
    }
  }

  /// 更新推送偏好
  Future<UserModel> updatePushPreferences(PushPreferences prefs) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoUser; // Mock update
    }
    try {
      // Assuming a dedicated endpoint or patching the user profile
      final response = await _apiClient.put<Map<String, dynamic>>(
        '/users/me/push-preference',
        data: prefs.toJson(),
      );
      final payload = response.data;
      if (payload == null) {
        throw Exception('Failed to update push preferences');
      }
      return UserModel.fromJson(payload);
    } catch (e) {
      rethrow;
    }
  }
}

final userRepositoryProvider = Provider<UserRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return UserRepository(apiClient);
});
