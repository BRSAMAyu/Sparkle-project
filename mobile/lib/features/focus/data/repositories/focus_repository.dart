import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/focus/data/models/focus_session_model.dart';

/// Repository for focus session operations (P0.3)
class FocusRepository {
  FocusRepository(this._apiClient);

  final ApiClient _apiClient;

  /// Log a completed focus session and receive flame rewards
  ///
  /// P0.3: Called when user exits focus mode to persist session data
  /// and update user flame level
  Future<FocusSessionResponse> logFocusSession({
    required DateTime startTime,
    required DateTime endTime,
    required int durationMinutes,
    String? taskId,
    String focusType = 'pomodoro',
    String status = 'completed',
    String? whiteNoiseType,
  }) async {
    try {
      final request = FocusSessionRequest(
        taskId: taskId,
        startTime: startTime,
        endTime: endTime,
        durationMinutes: durationMinutes,
        focusType: focusType,
        status: status,
        whiteNoiseType: whiteNoiseType,
      );

      debugPrint('📤 Logging focus session: ${request.toJson()}');

      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.focusSessions,
        data: request.toJson(),
      );

      debugPrint('📥 Focus session logged: ${response.data}');

      return FocusSessionResponse.fromJson(
        response.data as Map<String, dynamic>,
      );
    } on DioException catch (e) {
      debugPrint('❌ Failed to log focus session: ${e.message}');
      debugPrint('Response: ${e.response?.data}');
      rethrow;
    }
  }

  /// Get today's focus statistics
  Future<FocusStatsResponse> getFocusStats() async {
    try {
      final response =
          await _apiClient.get<dynamic>(ApiEndpoints.focusStats);

      return FocusStatsResponse.fromJson(
        response.data as Map<String, dynamic>,
      );
    } on DioException catch (e) {
      debugPrint('❌ Failed to get focus stats: ${e.message}');
      rethrow;
    }
  }

  /// Get LLM methodological guidance during focus
  Future<String> getLLMGuidance({
    required String taskTitle,
    required String context,
  }) async {
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.focusLlmGuide,
        data: {
          'task_title': taskTitle,
          'context': context,
        },
      );

      final data = response.data as Map<String, dynamic>;
      return data['guidance'] as String;
    } on DioException catch (e) {
      debugPrint('❌ Failed to get LLM guidance: ${e.message}');
      rethrow;
    }
  }

  /// Break down a task using LLM
  Future<List<String>> breakdownTask({
    required String taskTitle,
    required String taskType,
  }) async {
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.focusLlmBreakdown,
        data: {
          'task_title': taskTitle,
          'task_type': taskType,
        },
      );

      final data = response.data as Map<String, dynamic>;
      return (data['subtasks'] as List<dynamic>)
          .map((e) => e.toString())
          .toList();
    } on DioException catch (e) {
      debugPrint('❌ Failed to breakdown task: ${e.message}');
      rethrow;
    }
  }

  /// Get weekly focus statistics
  Future<FocusWeeklyStatsResponse> getWeeklyStats() async {
    try {
      final response = await _apiClient.get<dynamic>(
        '/focus/stats/weekly',
      );

      return FocusWeeklyStatsResponse.fromJson(
        response.data as Map<String, dynamic>,
      );
    } on DioException catch (e) {
      debugPrint('❌ Failed to get weekly stats: ${e.message}');
      rethrow;
    }
  }

  /// Get monthly focus statistics
  Future<FocusMonthlyStatsResponse> getMonthlyStats() async {
    try {
      final response = await _apiClient.get<dynamic>(
        '/focus/stats/monthly',
      );

      return FocusMonthlyStatsResponse.fromJson(
        response.data as Map<String, dynamic>,
      );
    } on DioException catch (e) {
      debugPrint('❌ Failed to get monthly stats: ${e.message}');
      rethrow;
    }
  }

  /// Get focus session history
  Future<FocusSessionHistoryResponse> getSessionHistory({
    int limit = 20,
    int offset = 0,
  }) async {
    try {
      final response = await _apiClient.get<dynamic>(
        '/focus/sessions/history',
        queryParameters: {
          'limit': limit,
          'offset': offset,
        },
      );

      return FocusSessionHistoryResponse.fromJson(
        response.data as Map<String, dynamic>,
      );
    } on DioException catch (e) {
      debugPrint('❌ Failed to get session history: ${e.message}');
      rethrow;
    }
  }

  /// Get focus heatmap data
  Future<Map<String, double>> getHeatmapData({int days = 90}) async {
    try {
      final response = await _apiClient.get<dynamic>(
        '/focus/stats/heatmap',
        queryParameters: {'days': days},
      );

      final data = response.data as Map<String, dynamic>;
      return data.map<String, double>(
        (key, value) => MapEntry(key, (value as num).toDouble()),
      );
    } on DioException catch (e) {
      debugPrint('❌ Failed to get heatmap data: ${e.message}');
      rethrow;
    }
  }
}

/// Focus repository provider (P0.3)
final focusRepositoryProvider = Provider<FocusRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return FocusRepository(apiClient);
});
