import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
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
        data: <String, dynamic>{
          'learning_depth': preferences.depthPreference,
          'curiosity_level': preferences.curiosityPreference,
        },
      );
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'updateUserPreferences',
      );
      return UserModel.fromJson(payload);
    } catch (e) {
      rethrow;
    }
  }

  /// 更新推送偏好
  Future<void> updatePushPreferences(PushPreferences prefs) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    try {
      await _apiClient.put<Map<String, dynamic>>(
        '/users/me/push-preference',
        data: prefs.toJson(),
      );
    } catch (e) {
      rethrow;
    }
  }

  Future<Map<String, dynamic>> fetchTransparentProfile() async {
    if (DemoDataService.isDemoMode) {
      return {
        'layer_1': {'preferences': <String>[], 'goals': <String>[]},
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
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/profile/transparent',
    );
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchTransparentProfile',
    );
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
        'metacognition_dashboard': {
          'available': true,
          'hidden': false,
          'generated_at': '2026-04-22T10:00:00',
          'cards': [
            {
              'dim': 'time_estimation_bias',
              'title': '时间预估',
              'status': 'ready',
              'body': '你过去 10 次对完成时间估得偏乐观 2.3 小时。',
              'trend_text': '最近几周正在变稳。',
            },
          ],
        },
        'user_state_v1': {
          'schema_version': 'user_state.v1.13',
          'working_memory_snapshot': {
            'value': {
              'active_session_id': 'session-stage35-demo',
              'items': [
                {
                  'summary': '英语长难句拆解还卡在倒装句，下一次练习先回看第 3 题。',
                  'subject_type': 'study_focus',
                  'mention_count': 3,
                  'consolidated': false,
                  'last_seen_at': '2026-04-22T09:40:00',
                },
                {
                  'summary': '这周要把概率论错题本整理成 2 页复盘卡片。',
                  'subject_type': 'task',
                  'mention_count': 2,
                  'consolidated': true,
                  'last_seen_at': '2026-04-22T08:20:00',
                },
              ],
            },
            'computed_at': '2026-04-22T10:00:00',
            'source_snapshot_ids': ['wm-demo-1'],
            'freshness_seconds': 90,
          },
          'achievement_summary': {
            'value': {
              'recent_unlocks': [
                {
                  'achievement_id': 'weekly-streak',
                  'name': '七日连学',
                  'rarity': 'rare',
                  'unlocked_at': '2026-04-21T21:00:00',
                },
              ],
              'in_progress_achievements': [
                {
                  'achievement_id': 'deep-work-10',
                  'name': '深度专注 10 次',
                  'progress': 0.7,
                },
              ],
              'total_achievement_score': 18.5,
            },
            'computed_at': '2026-04-22T10:00:00',
            'source_snapshot_ids': ['achievement-demo-1'],
            'freshness_seconds': 120,
          },
          'active_skills_summary': {
            'value': {
              'items': [
                {
                  'skill_id': 'chunking',
                  'name': '分块推进',
                  'activation_match_score': 0.92,
                },
                {
                  'skill_id': 'replan',
                  'name': '轻量重排',
                  'activation_match_score': 0.78,
                },
              ],
            },
            'computed_at': '2026-04-22T10:00:00',
            'source_snapshot_ids': ['skills-demo-1'],
            'freshness_seconds': 75,
          },
          'engagement_state': {
            'value': {
              'last_active_at': '2026-04-22T09:50:00',
              'session_count_7d': 6,
              'streak': 4,
            },
            'computed_at': '2026-04-22T10:00:00',
            'source_snapshot_ids': ['engagement-demo-1'],
            'freshness_seconds': 60,
          },
          'foresight_hint': {
            'value': {
              'hint_text': '你今天后半段更容易被切碎，先把最难的一题压到午前完成。',
              'generated_at': '2026-04-22T09:55:00',
              'deviation_count': 2,
              'attractor_confidences': [
                {'dim': 'execution_stability', 'confidence': 0.84},
                {'dim': 'overload_risk', 'confidence': 0.66},
              ],
            },
            'computed_at': '2026-04-22T10:00:00',
            'source_snapshot_ids': ['foresight-demo-1'],
            'freshness_seconds': 45,
          },
          'metacognition_profile': {
            'value': {
              'items': [
                {
                  'dim': 'time_estimation_bias',
                  'sample_size': 10,
                  'bias_mean': -2.3,
                  'trend': 'improving',
                },
                {
                  'dim': 'difficulty_calibration',
                  'sample_size': 8,
                  'bias_mean': -0.4,
                  'trend': 'stable',
                },
              ],
            },
            'computed_at': '2026-04-22T10:00:00',
            'source_snapshot_ids': ['metacog-demo-1'],
            'freshness_seconds': 180,
          },
        },
        'metacognition_profile': {
          'items': [
            {
              'dim': 'time_estimation_bias',
              'sample_size': 10,
              'bias_mean': -2.3,
              'trend': 'improving',
            },
            {
              'dim': 'difficulty_calibration',
              'sample_size': 8,
              'bias_mean': -0.4,
              'trend': 'stable',
            },
          ],
        },
        'idiographic_summary': {
          'mode': 'shadow',
          'confidence': 0.42,
          'disclaimer_text': '这只是你数据中的模式，不代表因果关系。',
          'top_associations': <dynamic>[],
        },
      };
    }
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/profile/context',
    );
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchProfileContext',
    );
  }

  Future<Map<String, dynamic>> fetchProfileInsights() async {
    if (DemoDataService.isDemoMode) {
      return {
        'claims': <dynamic>[],
        'predictions': <dynamic>[],
        'recent_changes': <dynamic>[],
        'unknowns': <dynamic>[],
        'calibration': <String, dynamic>{},
        'current_profile': <String, dynamic>{},
      };
    }
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/profile/insights',
    );
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchProfileInsights',
    );
  }

  Future<Map<String, dynamic>> fetchTraitsColdstartQuestions() async {
    if (DemoDataService.isDemoMode) {
      return {'questions': <Map<String, dynamic>>[], 'allow_skip': true};
    }
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/profile/traits/coldstart/questions',
    );
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchTraitsColdstartQuestions',
    );
  }

  Future<Map<String, dynamic>> submitTraitsColdstart({
    Map<String, String> answers = const <String, String>{},
    bool skip = false,
  }) async {
    if (DemoDataService.isDemoMode) {
      return {
        'status': 'ok',
        'skipped': skip,
        'traits_prior': <String, dynamic>{},
      };
    }
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/profile/traits/coldstart',
      data: <String, dynamic>{'answers': answers, 'skip': skip},
    );
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'submitTraitsColdstart',
    );
  }

  Future<List<Map<String, dynamic>>> fetchInferredPreferences() async {
    if (DemoDataService.isDemoMode) {
      return [];
    }
    final response = await _apiClient.get<List<dynamic>>(
      '/profile/inferred-preferences',
    );
    final items = response.data ?? <dynamic>[];
    return items.whereType<Map<String, dynamic>>().toList();
  }

  Future<List<Map<String, dynamic>>> fetchActivePolicies() async {
    if (DemoDataService.isDemoMode) {
      return [];
    }
    final response = await _apiClient.get<List<dynamic>>(
      '/profile/active-policies',
    );
    final items = response.data ?? <dynamic>[];
    return items.whereType<Map<String, dynamic>>().toList();
  }

  Future<String?> submitOnboarding(Map<String, dynamic> payload) async {
    if (DemoDataService.isDemoMode) {
      return null;
    }
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/profile/onboarding',
      data: payload,
    );
    final data = response.data;
    if (data is Map<String, dynamic>) {
      final msg = data['first_message'];
      if (msg is String && msg.trim().isNotEmpty) return msg.trim();
    }
    return null;
  }

  Future<Map<String, dynamic>> fetchOnboardingPreview(
    Map<String, dynamic> payload,
  ) async {
    final goal = payload['learning_goal']?.toString().trim() ?? '';
    if (DemoDataService.isDemoMode) {
      return {
        'message': goal.isEmpty
            ? '先告诉我你现在最想推进的学习目标，我会立刻帮你判断难度并给出第一版起步建议。'
            : '我已经理解你想先推进「$goal」。接下来我会先补齐画像，再给你第一版学习路径和任务建议。',
        'source': 'demo_fallback',
        'fallback_used': true,
      };
    }
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/profile/onboarding/preview',
      data: payload,
    );
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchOnboardingPreview',
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

  Future<void> submitInsightControl(Map<String, dynamic> payload) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    await _apiClient.post<Map<String, dynamic>>(
      '/profile/insights/control',
      data: payload,
    );
  }

  Future<Map<String, dynamic>> updateMetacognitionPanelPreference({
    required bool hidden,
  }) async {
    if (DemoDataService.isDemoMode) {
      return {'hidden': hidden};
    }
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/profile/metacognition/panel',
      data: <String, dynamic>{'hidden': hidden},
    );
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'updateMetacognitionPanelPreference',
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
      queryParameters: {'limit': limit, 'offset': offset},
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
    final data = ApiResponseParser.unwrapList(
      response.data,
      action: 'fetchSystemUpdates',
    );
    return data.cast<Map<String, dynamic>>();
  }

  Future<bool> hydrateChatOpening(String conversationId) async {
    final normalizedConversationId = conversationId.trim();
    if (normalizedConversationId.isEmpty || DemoDataService.isDemoMode) {
      return false;
    }

    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.profileChatOpening,
      data: {'conversation_id': normalizedConversationId},
    );
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'hydrateChatOpening',
    );
    return payload['created'] == true;
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
      data: {'pref_key': prefKey, 'value': value},
    );
  }

  Future<void> rollbackTransparentPreference(String prefKey) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    await _apiClient.post<Map<String, dynamic>>(
      '/profile/preferences/rollback',
      data: {'pref_key': prefKey},
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
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/user/settings',
    );
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchUserSettings',
    );
  }

  Future<void> updateUserSettings(Map<String, dynamic> payload) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    // Use PUT for idempotent update operation
    await _apiClient.put<Map<String, dynamic>>('/user/settings', data: payload);
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
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/user/settings/ai-usage',
    );
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchAiUsageSummary',
    );
  }

  Future<Map<String, dynamic>> fetchAiOpsDashboard({int days = 7}) async {
    if (DemoDataService.isDemoMode) {
      return {
        'window_days': days,
        'items': [
          {
            'chat_mode': 'standard',
            'requests_total': 16,
            'requests_success': 15,
            'requests_failed': 1,
            'success_rate_percent': 93.75,
            'fallback_rate_percent': 12.5,
            'total_tokens': 22840,
            'total_cost_usd': 0.0412,
            'avg_total_duration_ms': 4320.0,
            'avg_first_token_ms': 924.0,
            'avg_stream_duration_ms': 2860.0,
            'positive_feedback_count': 5,
            'negative_feedback_count': 1,
            'positive_feedback_rate_percent': 83.33,
            'feedback_coverage_percent': 37.5,
            'task_count': 4,
            'plan_count': 1,
            'execution_count': 7,
            'task_conversion_rate_percent': 18.75,
            'plan_conversion_rate_percent': 6.25,
            'execution_conversion_rate_percent': 31.25,
            'avg_prompt_utilization_percent': 78.0,
            'avg_inference_utilization_percent': 71.0,
            'prompt_utilization_known_count': 12,
            'prompt_utilization_unknown_count': 3,
            'prompt_utilization_not_applicable_count': 1,
            'inference_utilization_known_count': 11,
            'inference_utilization_unknown_count': 4,
            'inference_utilization_not_applicable_count': 1,
            'reasoning_mode_breakdown': [
              {
                'mode': 'fast',
                'requests_total': 4,
                'requests_success': 4,
                'fallback_count': 1,
                'total_cost_usd': 0.0061,
              },
              {
                'mode': 'balanced',
                'requests_total': 10,
                'requests_success': 9,
                'fallback_count': 1,
                'total_cost_usd': 0.0242,
              },
              {
                'mode': 'deep',
                'requests_total': 2,
                'requests_success': 2,
                'fallback_count': 0,
                'total_cost_usd': 0.0109,
              },
            ],
          },
          {
            'chat_mode': 'study_plan',
            'requests_total': 5,
            'requests_success': 5,
            'requests_failed': 0,
            'success_rate_percent': 100.0,
            'fallback_rate_percent': 20.0,
            'total_tokens': 11930,
            'total_cost_usd': 0.0285,
            'avg_total_duration_ms': 16120.0,
            'avg_first_token_ms': 1188.0,
            'avg_stream_duration_ms': 10220.0,
            'positive_feedback_count': 3,
            'negative_feedback_count': 0,
            'positive_feedback_rate_percent': 100.0,
            'feedback_coverage_percent': 60.0,
            'task_count': 9,
            'plan_count': 4,
            'execution_count': 5,
            'task_conversion_rate_percent': 80.0,
            'plan_conversion_rate_percent': 80.0,
            'execution_conversion_rate_percent': 100.0,
            'avg_prompt_utilization_percent': 84.0,
            'avg_inference_utilization_percent': 76.0,
            'prompt_utilization_known_count': 4,
            'prompt_utilization_unknown_count': 1,
            'prompt_utilization_not_applicable_count': 0,
            'inference_utilization_known_count': 4,
            'inference_utilization_unknown_count': 1,
            'inference_utilization_not_applicable_count': 0,
            'reasoning_mode_breakdown': [
              {
                'mode': 'balanced',
                'requests_total': 4,
                'requests_success': 4,
                'fallback_count': 1,
                'total_cost_usd': 0.0202,
              },
              {
                'mode': 'deep',
                'requests_total': 1,
                'requests_success': 1,
                'fallback_count': 0,
                'total_cost_usd': 0.0083,
              },
            ],
          },
        ],
      };
    }
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/user/settings/ai-ops',
      queryParameters: {'days': days},
    );
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchAiOpsDashboard',
    );
  }

  Future<Map<String, dynamic>> fetchAiOpsExport({int days = 14}) async {
    if (DemoDataService.isDemoMode) {
      return {
        'window_days': days,
        'overview': {
          'requests_total': 21,
          'requests_success': 20,
          'requests_failed': 1,
          'success_rate_percent': 95.24,
          'fallback_rate_percent': 14.29,
          'total_cost_usd': 0.0697,
          'avg_total_duration_ms': 7064.0,
          'avg_first_token_ms': 986.0,
          'avg_stream_duration_ms': 4482.0,
          'task_count': 13,
          'plan_count': 5,
          'execution_count': 12,
          'task_conversion_rate_percent': 61.9,
          'plan_conversion_rate_percent': 23.81,
          'execution_conversion_rate_percent': 57.14,
          'avg_prompt_utilization_percent': 79.5,
          'avg_inference_utilization_percent': 72.5,
          'prompt_utilization_known_count': 16,
          'prompt_utilization_unknown_count': 4,
          'prompt_utilization_not_applicable_count': 1,
          'inference_utilization_known_count': 15,
          'inference_utilization_unknown_count': 5,
          'inference_utilization_not_applicable_count': 1,
        },
        'items': (await fetchAiOpsDashboard(days: days))['items'],
        'trend_series': [
          {
            'chat_mode': 'standard',
            'points': [
              {
                'date': '2026-03-14',
                'requests_total': 2,
                'success_rate_percent': 100.0,
                'fallback_rate_percent': 0.0,
                'total_cost_usd': 0.0038,
                'avg_total_duration_ms': 4210.0,
                'avg_first_token_ms': 780.0,
                'avg_stream_duration_ms': 2610.0,
                'execution_conversion_rate_percent': 50.0,
              },
              {
                'date': '2026-03-15',
                'requests_total': 3,
                'success_rate_percent': 100.0,
                'fallback_rate_percent': 33.3,
                'total_cost_usd': 0.0071,
                'avg_total_duration_ms': 4680.0,
                'avg_first_token_ms': 910.0,
                'avg_stream_duration_ms': 2920.0,
                'execution_conversion_rate_percent': 33.3,
              },
              {
                'date': '2026-03-16',
                'requests_total': 4,
                'success_rate_percent': 75.0,
                'fallback_rate_percent': 25.0,
                'total_cost_usd': 0.0105,
                'avg_total_duration_ms': 5030.0,
                'avg_first_token_ms': 1010.0,
                'avg_stream_duration_ms': 3110.0,
                'execution_conversion_rate_percent': 50.0,
              },
            ],
          },
          {
            'chat_mode': 'study_plan',
            'points': [
              {
                'date': '2026-03-14',
                'requests_total': 1,
                'success_rate_percent': 100.0,
                'fallback_rate_percent': 0.0,
                'total_cost_usd': 0.0042,
                'avg_total_duration_ms': 15220.0,
                'avg_first_token_ms': 1280.0,
                'avg_stream_duration_ms': 9740.0,
                'execution_conversion_rate_percent': 100.0,
              },
              {
                'date': '2026-03-15',
                'requests_total': 2,
                'success_rate_percent': 100.0,
                'fallback_rate_percent': 50.0,
                'total_cost_usd': 0.0111,
                'avg_total_duration_ms': 16840.0,
                'avg_first_token_ms': 1210.0,
                'avg_stream_duration_ms': 10840.0,
                'execution_conversion_rate_percent': 100.0,
              },
              {
                'date': '2026-03-16',
                'requests_total': 2,
                'success_rate_percent': 100.0,
                'fallback_rate_percent': 0.0,
                'total_cost_usd': 0.0132,
                'avg_total_duration_ms': 17420.0,
                'avg_first_token_ms': 1180.0,
                'avg_stream_duration_ms': 11320.0,
                'execution_conversion_rate_percent': 100.0,
              },
            ],
          },
        ],
      };
    }
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/user/settings/ai-ops/export',
      queryParameters: {'days': days},
    );
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchAiOpsExport',
    );
  }

  Future<Map<String, dynamic>> fetchClientTelemetrySummary({
    int days = 7,
  }) async {
    if (DemoDataService.isDemoMode) {
      return {
        'days': days,
        'overall': {
          'count': 428,
          'success_count': 401,
          'error_count': 27,
          'crash_count': 2,
          'avg_duration_ms': 612.4,
        },
        'daily_totals': [
          {
            'date': '2026-03-14',
            'count': 58,
            'error_count': 4,
            'crash_count': 0,
            'avg_duration_ms': 584.0,
          },
          {
            'date': '2026-03-15',
            'count': 67,
            'error_count': 5,
            'crash_count': 0,
            'avg_duration_ms': 601.0,
          },
          {
            'date': '2026-03-16',
            'count': 72,
            'error_count': 6,
            'crash_count': 1,
            'avg_duration_ms': 645.0,
          },
        ],
        'by_event_type': [
          {
            'event_type': 'all',
            'count': 428,
            'success_rate_percent': 93.69,
            'error_count': 27,
            'crash_count': 2,
            'avg_duration_ms': 612.4,
          },
          {
            'event_type': 'api_request',
            'count': 211,
            'success_rate_percent': 92.42,
            'error_count': 16,
            'crash_count': 0,
            'avg_duration_ms': 418.2,
          },
          {
            'event_type': 'screen_view',
            'count': 104,
            'success_rate_percent': 100.0,
            'error_count': 0,
            'crash_count': 0,
            'avg_duration_ms': 0.0,
          },
          {
            'event_type': 'crash',
            'count': 2,
            'success_rate_percent': 0.0,
            'error_count': 2,
            'crash_count': 2,
            'avg_duration_ms': 0.0,
          },
        ],
        'recent_events': [
          {
            'event_type': 'api_request',
            'category': 'network',
            'route': '/chat/stream',
            'status': 'error',
            'severity': 'warning',
            'duration_ms': 1288,
            'platform': 'ios',
            'occurred_at': '2026-03-20T10:08:00Z',
          },
        ],
      };
    }
    final response = await _apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.clientTelemetrySummary,
      queryParameters: {'days': days},
    );
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchClientTelemetrySummary',
    );
  }

  Future<Map<String, dynamic>> fetchHealthCapacity() async {
    if (DemoDataService.isDemoMode) {
      return {
        'generated_at': '2026-03-20T10:10:00Z',
        'database': {
          'probe_latency_ms': 18.5,
          'pool_size': 20,
          'max_overflow': 30,
          'pool_timeout_seconds': 30,
        },
        'redis': {
          'status': 'ok',
          'used_memory_human': '182.1M',
          'used_memory_peak_human': '240.0M',
          'maxmemory_human': '0B',
          'connected_clients': 29,
        },
        'queues': {'summarization': 18, 'billing': 0, 'expansion': 7},
        'disk': {
          'total_gb': 512.0,
          'used_gb': 324.2,
          'free_gb': 187.8,
          'used_ratio_percent': 63.32,
        },
        'thresholds': {
          'disk_warning_percent': 80,
          'queue_warning_total': 300,
          'queue_critical_total': 500,
          'db_probe_warning_ms': 200,
        },
        'recommendations': <String>['当前容量健康，可继续观察 AI 高峰时段的首包时延。'],
      };
    }
    final response = await _apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.healthCapacity,
    );
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchHealthCapacity',
    );
  }

  Future<Map<String, dynamic>> fetchPrometheusAlerts() async {
    if (DemoDataService.isDemoMode) {
      return {
        'alerts': [
          {
            'severity': 'warning',
            'name': 'SparklePredictionRulesFallbackSpike',
            'message': '规则回退正在抬头，请检查 free/free_fast 健康度',
            'value': 14,
          },
        ],
        'firing': true,
        'timestamp': '2026-03-20T10:12:00Z',
      };
    }
    final response = await _apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.healthPrometheusAlerts,
    );
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchPrometheusAlerts',
    );
  }

  /// Update weekly schedule preferences (time slots grid)
  Future<UserModel> updateSchedulePreferences(
    Map<String, dynamic> scheduleData,
  ) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoUser; // Mock update
    }
    try {
      final response = await _apiClient.put<Map<String, dynamic>>(
        '/users/me/schedule-preferences',
        data: scheduleData,
      );
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'updateSchedulePreferences',
      );
      return UserModel.fromJson(payload);
    } catch (e) {
      rethrow;
    }
  }

  /// Download all user data as a ZIP archive.
  Future<List<int>> exportUserData() async {
    try {
      final response = await _apiClient.dio.get<List<int>>(
        ApiEndpoints.meExport,
        options: Options(responseType: ResponseType.bytes),
      );
      return response.data ?? const [];
    } catch (e) {
      rethrow;
    }
  }
}

final userRepositoryProvider = Provider<UserRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return UserRepository(apiClient);
});
