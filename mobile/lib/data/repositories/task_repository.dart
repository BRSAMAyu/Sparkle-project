import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/data/models/api_response_model.dart';
import 'package:sparkle/data/models/task_model.dart';
import 'package:sparkle/data/models/task_completion_result.dart';

class TaskRepository {
  final ApiClient _apiClient;

  TaskRepository(this._apiClient);

  // A generic error handler for Dio exceptions
  T _handleDioError<T>(DioException e, String functionName) {
    final errorMessage = e.response?.data?['detail'] ?? 'An unknown error occurred in $functionName';
    throw Exception(errorMessage);
  }

  Future<PaginatedResponse<TaskModel>> getTasks({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 10,
  }) async {
    try {
      final Map<String, dynamic> queryParams = {'page': page, 'page_size': pageSize};
      if (filters != null) {
        queryParams.addAll(filters.map((key, value) => MapEntry(key, value.toString())));
      }
      final response = await _apiClient.get(ApiEndpoints.tasks, queryParameters: queryParams);
      // Assuming the paginated response is in the data field
      // Checking for 'data' wrapper if exists, otherwise assume root
      final data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      // Paginated response usually has 'data' (list) and 'meta'.
      // If backend returns {data: [tasks], meta: ...}, then PaginatedResponse.fromJson(response.data) is correct if it handles that structure.
      // But based on previous backend code: return {"data": [...], "meta": ...}
      return PaginatedResponse.fromJson(response.data, (json) => TaskModel.fromJson(json as Map<String, dynamic>));
    } on DioException catch (e) {
      return _handleDioError(e, 'getTasks');
    }
  }

  Future<TaskModel> getTask(String id) async {
    try {
      final response = await _apiClient.get(ApiEndpoints.task(id));
      final data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      return TaskModel.fromJson(data);
    } on DioException catch (e) {
      return _handleDioError(e, 'getTask');
    }
  }

  Future<List<TaskModel>> getTodayTasks() async {
    try {
      final response = await _apiClient.get(ApiEndpoints.todayTasks);
      final List<dynamic> data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      return data.map((json) => TaskModel.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getTodayTasks');
    }
  }

  Future<List<TaskModel>> getRecommendedTasks({int limit = 5}) async {
    try {
      final response = await _apiClient.get(ApiEndpoints.recommendedTasks, queryParameters: {'limit': limit});
      final List<dynamic> data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      return data.map((json) => TaskModel.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getRecommendedTasks');
    }
  }

  Future<TaskModel> createTask(TaskCreate task) async {
    try {
      final response = await _apiClient.post(ApiEndpoints.tasks, data: task.toJson());
      final data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      return TaskModel.fromJson(data);
    } on DioException catch (e) {
      return _handleDioError(e, 'createTask');
    }
  }

  Future<TaskModel> updateTask(String id, TaskUpdate task) async {
    try {
      final response = await _apiClient.put(ApiEndpoints.task(id), data: task.toJson());
      final data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      return TaskModel.fromJson(data);
    } on DioException catch (e) {
      return _handleDioError(e, 'updateTask');
    }
  }

  Future<void> deleteTask(String id) async {
    try {
      await _apiClient.delete(ApiEndpoints.task(id));
    } on DioException catch (e) {
      return _handleDioError(e, 'deleteTask');
    }
  }

  Future<TaskModel> startTask(String id) async {
    try {
      final response = await _apiClient.post(ApiEndpoints.startTask(id));
      final data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      return TaskModel.fromJson(data);
    } on DioException catch (e) {
      return _handleDioError(e, 'startTask');
    }
  }

  Future<TaskCompletionResult> completeTask(String id, int actualMinutes, String? note) async {
    try {
      final taskComplete = TaskComplete(actualMinutes: actualMinutes, userNote: note);
      final response = await _apiClient.post(ApiEndpoints.completeTask(id), data: taskComplete.toJson());
      final data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      return TaskCompletionResult.fromJson(data);
    } on DioException catch (e) {
      return _handleDioError(e, 'completeTask');
    }
  }

  Future<TaskModel> abandonTask(String id) async {
    try {
      // Backend uses a POST for this action
      final response = await _apiClient.post(ApiEndpoints.abandonTask(id));
      final data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      return TaskModel.fromJson(data);
    } on DioException catch (e) {
      return _handleDioError(e, 'abandonTask');
    }
  }
}

// Provider for TaskRepository
final taskRepositoryProvider = Provider<TaskRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return TaskRepository(apiClient);
});
