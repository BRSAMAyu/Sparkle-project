import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/features/recovery/data/models/stuck_journey_models.dart';

final stuckJourneyRepositoryProvider = Provider<StuckJourneyRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return StuckJourneyRepository(apiClient);
});

/// J-05 ·「我卡住了」统一恢复旅程仓库：消费 /experience/stuck-journey/*。
/// 诚实抛错，无 mock fallback（错误态由 provider 呈现重试入口）。
class StuckJourneyRepository {
  StuckJourneyRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<StuckJourneyPayload> startJourney({
    required String surface,
    String? goalId,
    String? taskId,
  }) async {
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.stuckJourneyStart,
        data: _contextBody(surface, goalId: goalId, taskId: taskId),
      );
      return StuckJourneyPayload.fromJson(
        ApiResponseParser.unwrapMap(
          response.data,
          action: 'startJourney',
        ),
      );
    } on DioException catch (e) {
      throw Exception(_extractDioMessage(e, 'Failed to start stuck journey'));
    }
  }

  Future<StuckJourneyPayload> answerQuestion({
    required String surface,
    required String questionId,
    required String branchKey,
    String? goalId,
    String? taskId,
  }) async {
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.stuckJourneyAnswer,
        data: {
          ..._contextBody(surface, goalId: goalId, taskId: taskId),
          'question_id': questionId,
          'branch_key': branchKey,
        },
      );
      return StuckJourneyPayload.fromJson(
        ApiResponseParser.unwrapMap(
          response.data,
          action: 'answerQuestion',
        ),
      );
    } on DioException catch (e) {
      throw Exception(_extractDioMessage(e, 'Failed to answer stuck journey'));
    }
  }

  Future<StuckJourneyCorrectionResult> correct({
    required String surface,
    required String frictionType,
    String? interventionKey,
    String? goalId,
    String? taskId,
    String? reasonText,
  }) async {
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.stuckJourneyCorrect,
        data: {
          ..._contextBody(surface, goalId: goalId, taskId: taskId),
          'friction_type': frictionType,
          if (interventionKey != null && interventionKey.isNotEmpty)
            'intervention_key': interventionKey,
          if (reasonText != null && reasonText.isNotEmpty)
            'reason_text': reasonText,
        },
      );
      return StuckJourneyCorrectionResult.fromJson(
        ApiResponseParser.unwrapMap(response.data, action: 'correct'),
      );
    } on DioException catch (e) {
      throw Exception(_extractDioMessage(e, 'Failed to correct stuck journey'));
    }
  }

  Map<String, dynamic> _contextBody(
    String surface, {
    String? goalId,
    String? taskId,
  }) =>
      {
        'surface': surface,
        if (goalId != null && goalId.isNotEmpty) 'goal_id': goalId,
        if (taskId != null && taskId.isNotEmpty) 'task_id': taskId,
      };

  String _extractDioMessage(DioException error, String fallbackMessage) {
    final data = error.response?.data;
    if (data is Map) {
      final detail = data['detail'];
      if (detail is String && detail.isNotEmpty) return detail;
      final message = data['message'];
      if (message is String && message.isNotEmpty) return message;
    }
    return fallbackMessage;
  }
}
