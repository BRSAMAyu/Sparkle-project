import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';

class ExecutionCopilotRepository {
  ExecutionCopilotRepository(this._apiClient);

  final ApiClient _apiClient;

  Exception _mapError(DioException e, String action) {
    final detail =
        (e.response?.data as Map<String, dynamic>?)?['detail'] as String?;
    return Exception(detail ?? '$action failed');
  }

  Future<Map<String, dynamic>> getCopilot(String planId) async {
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.executionCopilot(planId),
      );
      return ApiResponseParser.unwrapMap(response.data, action: 'getCopilot');
    } on DioException catch (e) {
      throw _mapError(e, 'getCopilot');
    }
  }

  Future<Map<String, dynamic>> getTimeline(
    String planId, {
    int days = 7,
  }) async {
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.executionCopilotTimeline(planId),
        queryParameters: {'days': days},
      );
      return ApiResponseParser.unwrapMap(response.data, action: 'getTimeline');
    } on DioException catch (e) {
      throw _mapError(e, 'getTimeline');
    }
  }

  Future<Map<String, dynamic>> checkpoint({
    required String planId,
    required String status,
    String? taskId,
    String? note,
  }) async {
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.executionCopilotCheckpoint(planId),
        data: {
          'status': status,
          if (taskId != null && taskId.isNotEmpty) 'task_id': taskId,
          if (note != null && note.isNotEmpty) 'note': note,
        },
      );
      return ApiResponseParser.unwrapMap(response.data, action: 'checkpoint');
    } on DioException catch (e) {
      throw _mapError(e, 'checkpoint');
    }
  }
}

final executionCopilotRepositoryProvider = Provider<ExecutionCopilotRepository>(
  (ref) => ExecutionCopilotRepository(ref.watch(apiClientProvider)),
);
