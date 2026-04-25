import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';

final examSprintRepositoryProvider = Provider<ExamSprintRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ExamSprintRepository(apiClient);
});

class ExamSprintRepository {
  ExamSprintRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<ExamSprintIntakeResult> submitIntake(
    ExamSprintIntakeRequest request,
  ) async {
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.examSprintIntake,
        data: request.toJson(),
      );
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'examSprintIntake',
      );
      return ExamSprintIntakeResult.fromJson(payload);
    } on DioException catch (e) {
      final data = e.response?.data;
      if (data is Map<String, dynamic>) {
        final detail = data['detail']?.toString();
        if (detail != null && detail.isNotEmpty) {
          throw Exception(detail);
        }
      }
      throw Exception(e.message ?? '考试冲刺设置提交失败');
    }
  }

  Future<void> submitPostExamReview(PostExamReviewRequest request) async {
    try {
      await _apiClient.post<dynamic>(
        ApiEndpoints.examSprintPostExamReview,
        data: request.toJson(),
      );
    } on DioException catch (e) {
      final data = e.response?.data;
      if (data is Map<String, dynamic>) {
        final detail = data['detail']?.toString();
        if (detail != null && detail.isNotEmpty) {
          throw Exception(detail);
        }
      }
      throw Exception(e.message ?? '考试复盘提交失败');
    }
  }

  Future<SprintCompletionCheckResult> checkSprintCompletion(
    String planId,
  ) async {
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.examSprintCompletion,
        queryParameters: {'plan_id': planId},
      );
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'examSprintCompletion',
      );
      return SprintCompletionCheckResult.fromJson(payload);
    } on DioException catch (e) {
      final data = e.response?.data;
      if (data is Map<String, dynamic>) {
        final detail = data['detail']?.toString();
        if (detail != null && detail.isNotEmpty) {
          throw Exception(detail);
        }
      }
      throw Exception(e.message ?? '冲刺完成检测失败');
    }
  }

  Future<LearningPortfolioResult> fetchLearningPortfolio({
    String? userId,
  }) async {
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.examSprintPortfolio,
        queryParameters: {
          if (userId != null && userId.trim().isNotEmpty) 'user_id': userId,
        },
      );
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'examSprintPortfolio',
      );
      return LearningPortfolioResult.fromJson(payload);
    } on DioException catch (e) {
      final data = e.response?.data;
      if (data is Map<String, dynamic>) {
        final detail = data['detail']?.toString();
        if (detail != null && detail.isNotEmpty) {
          throw Exception(detail);
        }
      }
      throw Exception(e.message ?? '学习档案加载失败');
    }
  }
}
