// ignore_for_file: cascade_invocations, unnecessary_lambdas

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/focus/data/models/focus_session_model.dart';
import 'package:sparkle/features/task/utils/task_identity.dart';

class LoggedFocusSession {
  const LoggedFocusSession({
    required this.response,
    this.unlockedAchievements = const <Map<String, dynamic>>[],
    this.masteryUpdates = const <FocusMasteryUpdate>[],
  });

  final FocusSessionResponse response;
  final List<Map<String, dynamic>> unlockedAchievements;
  final List<FocusMasteryUpdate> masteryUpdates;
}

class FocusMasteryUpdate {
  const FocusMasteryUpdate({
    required this.nodeId,
    required this.nodeName,
    required this.oldMastery,
    required this.newMastery,
    required this.delta,
  });

  factory FocusMasteryUpdate.fromJson(Map<String, dynamic> json) {
    int readInt(String key) => ((json[key] as num?) ?? 0).round();

    return FocusMasteryUpdate(
      nodeId: (json['node_id'] ?? '').toString(),
      nodeName: (json['node_name'] ?? '').toString(),
      oldMastery: readInt('old_mastery'),
      newMastery: readInt('new_mastery'),
      delta: readInt('delta'),
    );
  }

  final String nodeId;
  final String nodeName;
  final int oldMastery;
  final int newMastery;
  final int delta;
}

/// Repository for focus session operations (P0.3)
class FocusRepository {
  FocusRepository(this._apiClient);

  final ApiClient _apiClient;

  /// Log a completed focus session and receive flame rewards
  ///
  /// P0.3: Called when user exits focus mode to persist session data
  /// and update user flame level
  Future<LoggedFocusSession> logFocusSession({
    required DateTime startTime,
    required DateTime endTime,
    required int durationMinutes,
    String? taskId,
    String focusType = 'pomodoro',
    String status = 'completed',
    String? whiteNoiseType,
  }) async {
    if (DemoDataService.isDemoMode) {
      final now = DateTime.now();
      final sessions = DemoDataService().demoFocusSessions;
      sessions.add({
        'id': 'mock-session-${now.millisecondsSinceEpoch}',
        'start_time': startTime.toIso8601String(),
        'end_time': endTime.toIso8601String(),
        'duration_minutes': durationMinutes,
        'focus_type': focusType,
        'status': status,
        if (taskId != null) 'task_id': taskId,
        if (whiteNoiseType != null) 'white_noise_type': whiteNoiseType,
      });
      return LoggedFocusSession(
        response: FocusSessionResponse(
          id: 'mock-session-${now.millisecondsSinceEpoch}',
          success: true,
          rewards: const FocusSessionRewards(
            flameEarned: 10,
            leveledUp: false,
            newLevel: 5,
          ),
        ),
      );
    }

    try {
      final validTaskId = (taskId != null && isServerTaskId(taskId)) ? taskId : null;

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
      final unlockedAchievements =
          (payload['unlocked_achievements'] as List<dynamic>?)
                  ?.whereType<Map<Object?, Object?>>()
                  .map((item) => Map<String, dynamic>.from(item))
                  .toList() ??
              const <Map<String, dynamic>>[];
      final masteryUpdates = (payload['mastery_updates'] as List<dynamic>?)
              ?.whereType<Map<Object?, Object?>>()
              .map(
                (item) => FocusMasteryUpdate.fromJson(
                  Map<String, dynamic>.from(item),
                ),
              )
              .where((item) => item.nodeName.isNotEmpty)
              .toList() ??
          const <FocusMasteryUpdate>[];
      return LoggedFocusSession(
        response: FocusSessionResponse.fromJson(payload),
        unlockedAchievements: unlockedAchievements,
        masteryUpdates: masteryUpdates,
      );
    } on DioException catch (e) {
      debugPrint('❌ Failed to log focus session: ${e.message}');
      debugPrint('Response: ${e.response?.data}');
      rethrow;
    }
  }

  /// Get today's focus statistics
  Future<FocusStatsResponse> getFocusStats() async {
    if (DemoDataService.isDemoMode) {
      final sessions = DemoDataService().demoFocusSessions;
      final totalMinutes = sessions.fold<int>(0, (sum, item) => sum + (item['duration_minutes'] as int? ?? 0));
      return FocusStatsResponse(
        totalMinutes: totalMinutes,
        pomodoroCount: sessions.where((item) => item['focus_type'] == 'pomodoro').length,
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
      final sessions = DemoDataService().demoFocusSessions;
      return FocusWeeklyStatsResponse(
        periodStart: now.subtract(const Duration(days: 6)).toIso8601String().split('T')[0],
        periodEnd: now.toIso8601String().split('T')[0],
        totalMinutes: sessions.fold<int>(0, (sum, item) => sum + (item['duration_minutes'] as int? ?? 0)),
        sessionCount: sessions.length,
        avgDuration: sessions.isEmpty ? 0 : sessions.fold<int>(0, (sum, item) => sum + (item['duration_minutes'] as int? ?? 0)) ~/ sessions.length,
        dailyBreakdown: {
          for (int i = 0; i < 7; i++)
            DateTime.now().subtract(Duration(days: 6-i)).toIso8601String().split('T')[0]:
            (50 + (i * 20) % 110),
        },
        focusTypeDistribution: {
          'pomodoro': sessions.where((item) => item['focus_type'] == 'pomodoro').length,
          'deep_work': sessions.where((item) => item['focus_type'] == 'deep_work').length,
        },
        streakDays: 4,
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
      final sessions = DemoDataService().demoFocusSessions;
      final totalMinutes = sessions.fold<int>(0, (sum, item) => sum + (item['duration_minutes'] as int? ?? 0));
      return FocusMonthlyStatsResponse(
        periodStart: DateTime(now.year, now.month).toIso8601String().split('T')[0],
        periodEnd: now.toIso8601String().split('T')[0],
        totalMinutes: totalMinutes,
        sessionCount: sessions.length,
        avgDuration: sessions.isEmpty ? 0 : totalMinutes ~/ sessions.length,
        dailyBreakdown: {},
        weeklyBreakdown: {'week-1': 480, 'week-2': 540, 'week-3': 600, 'week-4': 720},
        focusTypeDistribution: {
          'pomodoro': sessions.where((item) => item['focus_type'] == 'pomodoro').length,
          'deep_work': sessions.where((item) => item['focus_type'] == 'deep_work').length,
        },
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
      final sessions = DemoDataService().demoFocusSessions;
      return FocusSessionHistoryResponse(
        sessions: sessions.skip(offset).take(limit).map((item) => FocusSessionDetail(
          id: item['id'] as String,
          startTime: DateTime.parse(item['start_time'] as String),
          endTime: DateTime.parse(item['end_time'] as String),
          durationMinutes: item['duration_minutes'] as int,
          focusType: item['focus_type'] as String,
          status: item['status'] as String,
          taskId: item['task_id'] as String?,
          taskTitle: item['task_id'] == null
              ? null
              : DemoDataService()
                  .demoTasks
                  .firstWhere(
                    (task) => task.id == item['task_id'],
                    orElse: () => DemoDataService().demoTasks.first,
                  )
                  .title,
        ),).toList(),
        totalCount: sessions.length,
        limit: limit,
        offset: offset,
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
      for (final session in DemoDataService().demoFocusSessions) {
        final start = DateTime.parse(session['start_time'] as String);
        final key = start.toIso8601String().split('T')[0];
        heatmap[key] = (heatmap[key] ?? 0) + (session['duration_minutes'] as num).toDouble();
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
