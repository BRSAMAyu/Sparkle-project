import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
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
    if (DemoDataService.isDemoMode) {
      return FocusSessionResponse(
        id: 'mock-session-${DateTime.now().millisecondsSinceEpoch}',
        success: true,
        rewards: FocusSessionRewards(
          flameEarned: 10,
          leveledUp: false,
          newLevel: 5,
        ),
      );
    }

    try {
      // 🔧 Fix: Ensure taskId is a valid UUID or null. 
      // "quick_focus_" IDs are local-only and will cause backend validation errors.
      final validTaskId = (taskId != null && taskId.length == 36 && !taskId.contains('_')) 
          ? taskId 
          : null;

      final request = FocusSessionRequest(
        taskId: validTaskId,
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

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'logFocusSession');
      return FocusSessionResponse.fromJson(payload);
    } on DioException catch (e) {
      debugPrint('❌ Failed to log focus session: ${e.message}');
      debugPrint('Response: ${e.response?.data}');
      rethrow;
    }
  }

  /// Get today's focus statistics
  Future<FocusStatsResponse> getFocusStats() async {
    if (DemoDataService.isDemoMode) {
      return FocusStatsResponse(
        totalMinutes: 120,
        pomodoroCount: 4,
        todayDate: DateTime.now().toIso8601String().split('T')[0],
      );
    }

    try {
      final response =
          await _apiClient.get<dynamic>(ApiEndpoints.focusStats);

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'getFocusStats');
      return FocusStatsResponse.fromJson(payload);
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
    if (DemoDataService.isDemoMode) {
      return 'Mock LLM Guidance: 建议使用番茄工作法，将任务分解为25分钟的专注块，每块之间休息5分钟。保持环境安静，关闭手机通知。';
    }

    try {
      final taskContext = taskTitle.trim().isEmpty ? context : taskTitle;
      final userInput = context.trim().isEmpty ? taskTitle : context;
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.focusLlmGuide,
        data: {
          'task_context': taskContext,
          'user_input': userInput,
        },
      );

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'getLLMGuidance');
      return (payload['content'] ?? payload['guidance']) as String;
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
    if (DemoDataService.isDemoMode) {
      return ['创建项目大纲', '编写核心功能代码', '添加测试用例', '完善文档'];
    }

    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.focusLlmBreakdown,
        data: {
          'task_title': taskTitle,
          'task_description': taskType,
        },
      );

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'breakdownTask');
      return (payload['subtasks'] as List<dynamic>).map((item) {
        if (item is Map<String, dynamic>) {
          return (item['title'] ?? item['name'] ?? item['description'] ?? item.toString()).toString();
        }
        return item.toString();
      }).toList();
    } on DioException catch (e) {
      debugPrint('❌ Failed to breakdown task: ${e.message}');
      rethrow;
    }
  }

  /// Get weekly focus statistics
  Future<FocusWeeklyStatsResponse> getWeeklyStats() async {
    if (DemoDataService.isDemoMode) {
      final now = DateTime.now();
      return FocusWeeklyStatsResponse(
        periodStart: now.subtract(const Duration(days: 6)).toIso8601String().split('T')[0],
        periodEnd: now.toIso8601String().split('T')[0],
        totalMinutes: 840,
        sessionCount: 7,
        avgDuration: 120,
        dailyBreakdown: {
          for (int i = 0; i < 7; i++)
            DateTime.now().subtract(Duration(days: 6-i)).toIso8601String().split('T')[0]:
            (60 + (i * 15) % 120),
        },
        focusTypeDistribution: {'pomodoro': 5, 'deep_work': 2},
        streakDays: 3,
        longestStreak: 7,
      );
    }

    try {
      final response = await _apiClient.get<dynamic>(
        '/focus/stats/weekly',
      );

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'getWeeklyStats');
      return FocusWeeklyStatsResponse.fromJson(payload);
    } on DioException catch (e) {
      debugPrint('❌ Failed to get weekly stats: ${e.message}');
      rethrow;
    }
  }

  /// Get monthly focus statistics
  Future<FocusMonthlyStatsResponse> getMonthlyStats() async {
    if (DemoDataService.isDemoMode) {
      final now = DateTime.now();
      return FocusMonthlyStatsResponse(
        periodStart: DateTime(now.year, now.month, 1).toIso8601String().split('T')[0],
        periodEnd: now.toIso8601String().split('T')[0],
        totalMinutes: 3240,
        sessionCount: 27,
        avgDuration: 120,
        dailyBreakdown: {},
        weeklyBreakdown: {'week-1': 720, 'week-2': 840, 'week-3': 900, 'week-4': 780},
        focusTypeDistribution: {'pomodoro': 20, 'deep_work': 7},
        streakDays: 5,
        longestStreak: 10,
      );
    }

    try {
      final response = await _apiClient.get<dynamic>(
        '/focus/stats/monthly',
      );

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'getMonthlyStats');
      return FocusMonthlyStatsResponse.fromJson(payload);
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
    if (DemoDataService.isDemoMode) {
      return FocusSessionHistoryResponse(
        sessions: List.generate(5, (i) => FocusSessionDetail(
          id: 'mock-session-$i',
          startTime: DateTime.now().subtract(Duration(days: i, hours: 2)),
          endTime: DateTime.now().subtract(Duration(days: i, hours: 1)),
          durationMinutes: 25 + (i * 5),
          focusType: i % 3 == 0 ? 'deep_work' : 'pomodoro',
          status: 'completed',
          taskId: 'mock-task-$i',
          taskTitle: 'Mock Focus Task $i',
        )),
        totalCount: 5,
        limit: 20,
        offset: 0,
      );
    }

    try {
      final response = await _apiClient.get<dynamic>(
        '/focus/sessions/history',
        queryParameters: {
          'limit': limit,
          'offset': offset,
        },
      );

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'getSessionHistory');
      return FocusSessionHistoryResponse.fromJson(payload);
    } on DioException catch (e) {
      debugPrint('❌ Failed to get session history: ${e.message}');
      rethrow;
    }
  }

  /// Get focus heatmap data
  Future<Map<String, double>> getHeatmapData({int days = 90}) async {
    if (DemoDataService.isDemoMode) {
      final heatmap = <String, double>{};
      for (int i = 0; i < 30; i++) {
        final date = DateTime.now().subtract(Duration(days: i));
        final key = date.toIso8601String().split('T')[0];
        heatmap[key] = 30.0 + (i % 10) * 15.0;
      }
      return heatmap;
    }

    try {
      final response = await _apiClient.get<dynamic>(
        '/focus/stats/heatmap',
        queryParameters: {'days': days},
      );

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'getHeatmapData');
      return payload.map<String, double>(
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
