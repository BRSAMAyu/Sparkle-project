import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/data/models/user_model.dart';
import 'package:sparkle/core/services/demo_data_service.dart';

class UserRepository {
  final ApiClient _apiClient;

  UserRepository(this._apiClient);

  /// 更新用户学习偏好
  Future<UserModel> updateUserPreferences(UserPreferences preferences) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoUser; // Mock update
    }
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
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoUser; // Mock update
    }
    try {
      // Assuming a dedicated endpoint or patching the user profile
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