import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/shared/entities/subtask_model.dart';

class SubtaskRepository {
  SubtaskRepository(this._apiClient);
  final ApiClient _apiClient;

  T _handleDioError<T>(DioException e, String functionName) {
    final errorMessage =
        e.response?.data?['detail'] ?? 'An unknown error occurred in $functionName';
    throw Exception(errorMessage);
  }

  /// Get all subtasks for a task
  Future<List<SubTaskModel>> getSubtasks(String taskId) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        '${ApiEndpoints.tasks}/$taskId/subtasks',
      );
      final data = _unwrapResponseList(response.data);
      return data
          .map((json) => SubTaskModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      return _handleDioError<List<SubTaskModel>>(e, 'getSubtasks');
    }
  }

  /// Create a new subtask
  Future<SubTaskModel> createSubtask(
    String taskId,
    SubTaskCreate subtask,
  ) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        '${ApiEndpoints.tasks}/$taskId/subtasks',
        data: subtask.toJson(),
      );
      final payload = _unwrapResponseMap(response.data, action: 'createSubtask');
      return SubTaskModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError<SubTaskModel>(e, 'createSubtask');
    }
  }

  /// Update a subtask
  Future<SubTaskModel> updateSubtask(
    String subtaskId,
    SubTaskUpdate subtask,
  ) async {
    try {
      final response = await _apiClient.put<Map<String, dynamic>>(
        '${ApiEndpoints.subtasks}/$subtaskId',
        data: subtask.toJson(),
      );
      final payload = _unwrapResponseMap(response.data, action: 'updateSubtask');
      return SubTaskModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError<SubTaskModel>(e, 'updateSubtask');
    }
  }

  /// Delete a subtask
  Future<void> deleteSubtask(String subtaskId) async {
    try {
      await _apiClient.delete<void>(
        '${ApiEndpoints.subtasks}/$subtaskId',
      );
    } on DioException catch (e) {
      return _handleDioError<void>(e, 'deleteSubtask');
    }
  }

  /// Reorder subtasks in bulk
  Future<void> reorderSubtasks(List<SubTaskReorderItem> items) async {
    try {
      await _apiClient.post<void>(
        '${ApiEndpoints.subtasks}/reorder',
        data: {
          'subtask_orders':
              items.map((item) => item.toJson()).toList(),
        },
      );
    } on DioException catch (e) {
      return _handleDioError<void>(e, 'reorderSubtasks');
    }
  }

  Map<String, dynamic> _unwrapResponseMap(
    Map<String, dynamic>? payload, {
    required String action,
  }) {
    if (payload == null) {
      throw Exception('$action response is empty');
    }
    final rawData = payload['data'];
    if (rawData is Map<String, dynamic>) {
      return rawData;
    }
    return payload;
  }

  List<dynamic> _unwrapResponseList(Map<String, dynamic>? payload) {
    if (payload == null) {
      return [];
    }
    final rawData = payload['data'];
    if (rawData is List<dynamic>) {
      return rawData;
    }
    return [];
  }
}

// Provider for SubtaskRepository
final subtaskRepositoryProvider = Provider<SubtaskRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return SubtaskRepository(apiClient);
});
