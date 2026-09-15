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
      throw Exception(e.message ?? 'Submit failed');
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
      throw Exception(e.message ?? 'Submit failed');
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
      throw Exception(e.message ?? 'Submit failed');
    }
  }

  Future<LearningPortfolioResult> fetchLearningPortfolio({
    String? userId,
    int page = 1,
    int pageSize = 20,
  }) async {
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.examSprintPortfolio,
        queryParameters: {
          if (userId != null && userId.trim().isNotEmpty) 'user_id': userId,
          'page': page,
          'page_size': pageSize,
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
      throw Exception(e.message ?? 'Failed to load learning portfolio');
    }
  }
}
