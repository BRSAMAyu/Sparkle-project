import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';

final dashboardRepositoryProvider = Provider<DashboardRepository>(
    (ref) => DashboardRepository(ref.read(apiClientProvider)),);

class DashboardRepository {
  DashboardRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<Map<String, dynamic>> getDashboardStatus() async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoDashboard;
    }
    final response = await _apiClient.get<dynamic>(ApiEndpoints.dashboardStatus);
    return ApiResponseParser.unwrapMap(response.data, action: 'getDashboardStatus');
  }

  Future<Map<String, dynamic>> getPredictiveDashboard() async {
    if (DemoDataService.isDemoMode) {
      return {
        'engagement_forecast': <String, dynamic>{},
        'dropout_risk': <String, dynamic>{},
        'optimal_time': <String, dynamic>{},
        'next_intent_forecast': {
          'title': '系统预测你接下来会继续推进最关键任务',
          'summary': '根据最近 24 小时的节奏，先推进当前重点任务最合适。',
          'confidence': 0.72,
          'predicted_action_type': 'resume_priority_task',
          'predicted_window': 'next_2h',
          'reasons': ['最近24小时持续活跃', '当前仍有重点待办'],
          'suggested_prompt': '帮我继续推进今天最关键的任务',
          'prediction_source': 'rules',
          'prediction_tier': 'rules',
          'fallback_used': true,
          'generated_at': DateTime.now().toIso8601String(),
        },
      };
    }
    final response =
        await _apiClient.get<dynamic>(ApiEndpoints.predictiveDashboard);
    return ApiResponseParser.unwrapMap(response.data,
        action: 'getPredictiveDashboard',);
  }
}
