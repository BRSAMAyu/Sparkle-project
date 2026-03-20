import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/response_parser.dart';
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
      final payload = ApiResponseParser.unwrapMap(response.data,
          action: 'updateUserPreferences');
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
      final payload = ApiResponseParser.unwrapMap(response.data,
          action: 'updatePushPreferences');
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
    return ApiResponseParser.unwrapMap(response.data,
        action: 'fetchTransparentProfile');
  }

  Future<Map<String, dynamic>> fetchProfileContext() async {
    if (DemoDataService.isDemoMode) {
      return {
        'preferences': <String, dynamic>{},
        'preference_version': 0,
        'knowledge_summary': {
          'overall_mastery': 0.0,
          'weak_spots': <dynamic>[],
          'recent_mastery_changes': <dynamic>[],
          'active_learning_subjects': <dynamic>[],
        },
        'cognitive_summary': {
          'active_patterns': <dynamic>[],
          'dominant_pattern_type': null,
          'risk_signals': <dynamic>[],
        },
      };
    }
    final response =
        await _apiClient.get<Map<String, dynamic>>('/profile/context');
    return ApiResponseParser.unwrapMap(response.data,
        action: 'fetchProfileContext');
  }

  Future<List<Map<String, dynamic>>> fetchInferredPreferences() async {
    if (DemoDataService.isDemoMode) {
      return [];
    }
    final response =
        await _apiClient.get<List<dynamic>>('/profile/inferred-preferences');
    final items = response.data ?? <dynamic>[];
    return items.whereType<Map<String, dynamic>>().toList();
  }

  Future<List<Map<String, dynamic>>> fetchActivePolicies() async {
    if (DemoDataService.isDemoMode) {
      return [];
    }
    final response =
        await _apiClient.get<List<dynamic>>('/profile/active-policies');
    final items = response.data ?? <dynamic>[];
    return items.whereType<Map<String, dynamic>>().toList();
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
    if (payload == null) {
      return [];
    }
    // Handle both {items: [...]} and direct [...] formats
    if (payload.containsKey('items')) {
      final items = payload['items'] as List<dynamic>;
      return items.cast<Map<String, dynamic>>();
    }
    // Direct list format
    final data = ApiResponseParser.unwrapList(response.data,
        action: 'fetchSystemUpdates');
    return data.cast<Map<String, dynamic>>();
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

  Future<void> overrideInferredPreference({
    required String key,
    required dynamic value,
    String? reason,
  }) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    await _apiClient.post<Map<String, dynamic>>(
      '/profile/override-inferred',
      data: {
        'key': key,
        'value': value,
        if (reason != null && reason.isNotEmpty) 'reason': reason,
      },
    );
  }

  Future<void> resetInferredOverride(String key) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    await _apiClient.post<Map<String, dynamic>>(
      '/profile/reset-override',
      data: {'key': key},
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
        'ai_reasoning_mode': 'balanced',
        'task_reminders_enabled': true,
        'task_reminder_times': [1440, 60, 15],
      };
    }
    final response =
        await _apiClient.get<Map<String, dynamic>>('/user/settings');
    return ApiResponseParser.unwrapMap(response.data,
        action: 'fetchUserSettings');
  }

  Future<void> updateUserSettings(Map<String, dynamic> payload) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    // Use PUT for idempotent update operation
    await _apiClient.put<Map<String, dynamic>>(
      '/user/settings',
      data: payload,
    );
  }

  Future<Map<String, dynamic>> fetchAiUsageSummary() async {
    if (DemoDataService.isDemoMode) {
      return {
        'current_mode': 'balanced',
        'items': [
          {
            'mode': 'fast',
            'label': '敏捷',
            'requests_used': 12,
            'requests_limit': 120,
            'requests_remaining': 108,
            'total_tokens': 18420,
            'total_cost_usd': 0.0184,
            'total_duration_ms': 32540,
            'avg_total_duration_ms': 2711.67,
            'avg_first_token_ms': 652.0,
            'avg_stream_duration_ms': 2059.67,
          },
          {
            'mode': 'balanced',
            'label': '均衡',
            'requests_used': 6,
            'requests_limit': 60,
            'requests_remaining': 54,
            'total_tokens': 14310,
            'total_cost_usd': 0.0267,
            'total_duration_ms': 28460,
            'avg_total_duration_ms': 4743.33,
            'avg_first_token_ms': 1124.0,
            'avg_stream_duration_ms': 3387.67,
          },
          {
            'mode': 'deep',
            'label': '深思',
            'requests_used': 1,
            'requests_limit': 24,
            'requests_remaining': 23,
            'total_tokens': 6120,
            'total_cost_usd': 0.0153,
            'total_duration_ms': 9430,
            'avg_total_duration_ms': 9430.0,
            'avg_first_token_ms': 1820.0,
            'avg_stream_duration_ms': 7110.0,
          },
        ],
      };
    }
    final response =
        await _apiClient.get<Map<String, dynamic>>('/user/settings/ai-usage');
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchAiUsageSummary',
    );
  }

  /// Update weekly schedule preferences (time slots grid)
  Future<UserModel> updateSchedulePreferences(
      Map<String, dynamic> scheduleData) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoUser; // Mock update
    }
    try {
      final response = await _apiClient.put<Map<String, dynamic>>(
        '/users/me/schedule-preferences',
        data: scheduleData,
      );
      final payload = ApiResponseParser.unwrapMap(response.data,
          action: 'updateSchedulePreferences');
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
