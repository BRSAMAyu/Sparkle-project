import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/data/models/api_response_model.dart';
import 'package:sparkle/data/models/task_completion_result.dart';
import 'package:sparkle/data/models/task_model.dart';

class TaskRepository {

  TaskRepository(this._apiClient);
  final ApiClient _apiClient;

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
    if (DemoDataService.isDemoMode) {
      final tasks = DemoDataService().demoTasks;
      // Simple mock pagination
      return PaginatedResponse(
        items: tasks,
        total: tasks.length,
        page: 1,
        pageSize: pageSize,
      );
    }
    try {
      final queryParams = <String, dynamic>{'page': page, 'page_size': pageSize};
      if (filters != null) {
        queryParams.addAll(filters.map((key, value) => MapEntry(key, value.toString())));
      }
      final response = await _apiClient.get(ApiEndpoints.tasks, queryParameters: queryParams);
      return PaginatedResponse.fromJson(response.data, (json) => TaskModel.fromJson(json as Map<String, dynamic>));
    } on DioException catch (e) {
      return _handleDioError(e, 'getTasks');
    }
  }

  Future<TaskModel> getTask(String id) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoTasks.firstWhere((t) => t.id == id, orElse: () => DemoDataService().demoTasks.first);
    }
    try {
      final response = await _apiClient.get(ApiEndpoints.task(id));
      final data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      return TaskModel.fromJson(data);
    } on DioException catch (e) {
      return _handleDioError(e, 'getTask');
    }
  }

  Future<List<TaskModel>> getTodayTasks() async {
    if (DemoDataService.isDemoMode) {
      // Return tasks that are pending or in progress, or recently completed
      return DemoDataService().demoTasks.where((t) => t.status != TaskStatus.abandoned).toList();
    }
    try {
      final response = await _apiClient.get(ApiEndpoints.todayTasks);
      final List<dynamic> data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      return data.map((json) => TaskModel.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getTodayTasks');
    }
  }

  Future<List<TaskModel>> getRecommendedTasks({int limit = 5}) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoTasks.take(limit).toList();
    }
    try {
      final response = await _apiClient.get(ApiEndpoints.recommendedTasks, queryParameters: {'limit': limit});
      final List<dynamic> data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      return data.map((json) => TaskModel.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getRecommendedTasks');
    }
  }

  Future<TaskModel> createTask(TaskCreate task) async {
    if (DemoDataService.isDemoMode) {
      // Mock creation
      final newTask = TaskModel(
        id: 'mock_task_${DateTime.now().millisecondsSinceEpoch}',
        userId: DemoDataService().demoUser.id,
        title: task.title,
        type: task.type,
        tags: task.tags ?? [],
        estimatedMinutes: task.estimatedMinutes,
        difficulty: task.difficulty,
        energyCost: task.energyCost,
        status: TaskStatus.pending,
        priority: 2,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
        dueDate: task.dueDate,
      );
      DemoDataService().demoTasks.add(newTask);
      return newTask;
    }
    try {
      final response = await _apiClient.post(ApiEndpoints.tasks, data: task.toJson());
      final data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      return TaskModel.fromJson(data);
    } on DioException catch (e) {
      return _handleDioError(e, 'createTask');
    }
  }

  Future<TaskModel> updateTask(String id, TaskUpdate task) async {
     if (DemoDataService.isDemoMode) {
       // Find and mock update
       final existingIndex = DemoDataService().demoTasks.indexWhere((t) => t.id == id);
       if (existingIndex != -1) {
         // This is a shallow copy update simulation
         final existing = DemoDataService().demoTasks[existingIndex];
         final updated = existing.copyWith(
           title: task.title ?? existing.title,
           status: task.status ?? existing.status,
           // ... other fields
         );
         DemoDataService().demoTasks[existingIndex] = updated;
         return updated;
       }
       throw Exception('Task not found in demo data');
     }
    try {
      final response = await _apiClient.put(ApiEndpoints.task(id), data: task.toJson());
      final data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      return TaskModel.fromJson(data);
    } on DioException catch (e) {
      return _handleDioError(e, 'updateTask');
    }
  }

  Future<void> deleteTask(String id) async {
    if (DemoDataService.isDemoMode) {
      DemoDataService().demoTasks.removeWhere((t) => t.id == id);
      return;
    }
    try {
      await _apiClient.delete(ApiEndpoints.task(id));
    } on DioException catch (e) {
      return _handleDioError(e, 'deleteTask');
    }
  }

  Future<TaskModel> startTask(String id) async {
    if (DemoDataService.isDemoMode) {
       final existingIndex = DemoDataService().demoTasks.indexWhere((t) => t.id == id);
       if (existingIndex != -1) {
         final updated = DemoDataService().demoTasks[existingIndex].copyWith(status: TaskStatus.inProgress, startedAt: DateTime.now());
         DemoDataService().demoTasks[existingIndex] = updated;
         return updated;
       }
    }
    try {
      final response = await _apiClient.post(ApiEndpoints.startTask(id));
      final data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      return TaskModel.fromJson(data);
    } on DioException catch (e) {
      return _handleDioError(e, 'startTask');
    }
  }

  Future<TaskCompletionResult> completeTask(String id, int actualMinutes, String? note) async {
     if (DemoDataService.isDemoMode) {
       final existingIndex = DemoDataService().demoTasks.indexWhere((t) => t.id == id);
       if (existingIndex != -1) {
         final updated = DemoDataService().demoTasks[existingIndex].copyWith(
           status: TaskStatus.completed, 
           completedAt: DateTime.now(),
           actualMinutes: actualMinutes,
           userNote: note,
          );
         DemoDataService().demoTasks[existingIndex] = updated;
         return TaskCompletionResult(
           task: updated.toJson(),
           feedback: 'Mock feedback: Great job!',
           flameUpdate: {'level': 15, 'brightness': 85},
           statsUpdate: {'total_minutes': 100}, 
          );
       }
    }
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
    if (DemoDataService.isDemoMode) {
       final existingIndex = DemoDataService().demoTasks.indexWhere((t) => t.id == id);
       if (existingIndex != -1) {
         final updated = DemoDataService().demoTasks[existingIndex].copyWith(status: TaskStatus.abandoned);
         DemoDataService().demoTasks[existingIndex] = updated;
         return updated;
       }
    }
    try {
      // Backend uses a POST for this action
      final response = await _apiClient.post(ApiEndpoints.abandonTask(id));
      final data = response.data is Map && response.data.containsKey('data') ? response.data['data'] : response.data;
      return TaskModel.fromJson(data);
    } on DioException catch (e) {
      return _handleDioError(e, 'abandonTask');
    }
  }

  Future<TaskSuggestionResponse> getSuggestions(String inputText) async {
    if (DemoDataService.isDemoMode) {
      return TaskSuggestionResponse(
        intent: 'learning',
        suggestedNodes: [SuggestedNode(name: 'Data Structures', reason: 'Relevant to your text', isNew: false)],
        suggestedTags: ['CS'],
        estimatedMinutes: 60,
        difficulty: 3,
      );
    }
    try {
      final response = await _apiClient.post(
        ApiEndpoints.taskSuggestions,
        data: {'input_text': inputText},
      );
      return TaskSuggestionResponse.fromJson(response.data);
    } on DioException catch (e) {
      return _handleDioError(e, 'getSuggestions');
    }
  }
}

// Provider for TaskRepository
final taskRepositoryProvider = Provider<TaskRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return TaskRepository(apiClient);
});
