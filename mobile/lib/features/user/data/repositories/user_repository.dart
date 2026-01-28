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

  Future<Map<String, dynamic>> fetchTransparentProfile() async {
    if (DemoDataService.isDemoMode) {
      return {
        'layer_1': {
          'preferences': <String>[],
          'goals': <String>[],
        },
        'layer_2': {
          'persona': {
            'tags': ['demo'],
            'capabilities': {'mastery_avg': 0.5},
          },
          'editable': false,
        },
        'layer_3': {
          'patterns': <Map<String, dynamic>>[],
          'fragments': <Map<String, dynamic>>[],
        },
      };
    }
    final response =
        await _apiClient.get<Map<String, dynamic>>('/profile/transparent');
    final payload = response.data;
    if (payload == null) {
      throw Exception('Failed to load transparent profile');
    }
    return payload;
  }

  Future<void> submitOnboarding(Map<String, dynamic> payload) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    await _apiClient.post<Map<String, dynamic>>(
      '/profile/onboarding',
      data: payload,
    );
  }

  Future<void> submitProfileCorrection(Map<String, dynamic> payload) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    await _apiClient.post<Map<String, dynamic>>(
      '/profile/corrections',
      data: payload,
    );
  }

  Future<List<Map<String, dynamic>>> fetchSystemUpdates({
    int limit = 50,
    int offset = 0,
  }) async {
    if (DemoDataService.isDemoMode) {
      return [];
    }
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/profile/system-updates',
      queryParameters: {
        'limit': limit,
        'offset': offset,
      },
    );
    final payload = response.data;
    if (payload == null || payload['items'] == null) {
      return [];
    }
    final items = payload['items'] as List<dynamic>;
    return items.cast<Map<String, dynamic>>();
  }

  Future<void> updateTransparentPreference({
    required String prefKey,
    required dynamic value,
  }) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    await _apiClient.put<Map<String, dynamic>>(
      '/profile/preferences',
      data: {
        'pref_key': prefKey,
        'value': value,
      },
    );
  }

  Future<void> rollbackTransparentPreference(String prefKey) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    await _apiClient.post<Map<String, dynamic>>(
      '/profile/preferences/rollback',
      data: {
        'pref_key': prefKey,
      },
    );
  }

  Future<void> updateGoal({
    required String goalId,
    String? title,
    String? status,
  }) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    await _apiClient.put<Map<String, dynamic>>(
      '/profile/goals',
      data: {
        'goal_id': goalId,
        if (title != null) 'title': title,
        if (status != null) 'status': status,
      },
    );
  }

  Future<Map<String, dynamic>> fetchUserSettings() async {
    if (DemoDataService.isDemoMode) {
      return {
        'transparency_level': 0,
        'system_update_level': 1,
        'task_reminders_enabled': true,
        'task_reminder_times': [1440, 60, 15],
      };
    }
    final response = await _apiClient.get<Map<String, dynamic>>('/user/settings');
    final payload = response.data;
    if (payload == null) {
      throw Exception('Failed to load user settings');
    }
    return payload;
  }

  Future<void> updateUserSettings(Map<String, dynamic> payload) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    await _apiClient.post<Map<String, dynamic>>(
      '/user/settings',
      data: payload,
    );
  }
}

final userRepositoryProvider = Provider<UserRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return UserRepository(apiClient);
});
