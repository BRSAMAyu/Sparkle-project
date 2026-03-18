import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/task/data/models/next_action.dart';
import 'package:sparkle/features/task/data/models/next_action_selection_submission.dart';
import 'package:sparkle/features/task/data/models/task_completion_result.dart';
import 'package:sparkle/features/task/data/models/task_feedback_response.dart';
import 'package:sparkle/features/task/data/models/task_feedback_submission.dart';
import 'package:sparkle/features/task/data/models/task_nudge.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/models/api_response_model.dart';

class TaskRepository {
  TaskRepository(this._apiClient);
  final ApiClient _apiClient;

  // A generic error handler for Dio exceptions
  T _handleDioError<T>(DioException e, String functionName) {
    String errorMessage;

    if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.sendTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      errorMessage = '网络超时，请检查网络连接';
    } else if (e.type == DioExceptionType.connectionError) {
      errorMessage = '网络连接失败，请检查网络设置';
    } else if (e.response != null) {
      // Try to extract error message from response
      final data = e.response!.data;
      if (data is Map) {
        errorMessage = (data['detail'] as String?) ??
            (data['message'] as String?) ??
            (data['error'] as String?) ??
            '服务器返回错误 (HTTP ${e.response!.statusCode})';
      } else if (data is String) {
        errorMessage = data;
      } else {
        errorMessage = '服务器返回错误 (HTTP ${e.response!.statusCode})';
      }
    } else {
      errorMessage = '未知错误: ${e.message ?? "无法连接到服务器"}';
    }

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
      final queryParams = <String, dynamic>{
        'page': page,
        'page_size': pageSize,
      };
      if (filters != null) {
        queryParams.addAll(
            filters.map((key, value) => MapEntry(key, value.toString())),);
      }
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.tasks,
        queryParameters: queryParams,
      );
      return ApiResponseParser.parsePaginated(
        response.data,
        (json) => TaskModel.fromJson(json as Map<String, dynamic>),
        action: 'getTasks',
      );
    } on DioException catch (e) {
      return _handleDioError(e, 'getTasks');
    }
  }

  Future<TaskModel> getTask(String id) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoTasks.firstWhere((t) => t.id == id,
          orElse: () => DemoDataService().demoTasks.first,);
    }
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.task(id),
      );
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'getTask');
      return TaskModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'getTask');
    }
  }

  Future<List<TaskModel>> getTodayTasks() async {
    if (DemoDataService.isDemoMode) {
      // Return tasks that are pending or in progress, or recently completed
      return DemoDataService()
          .demoTasks
          .where((t) => t.status != TaskStatus.abandoned)
          .toList();
    }
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.todayTasks,
      );
      final data = ApiResponseParser.unwrapList(response.data, action: 'getTodayTasks');
      return data
          .map((json) => TaskModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getTodayTasks');
    }
  }

  Future<List<TaskModel>> getRecommendedTasks({int limit = 5}) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoTasks.take(limit).toList();
    }
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.recommendedTasks,
        queryParameters: {'limit': limit},
      );
      final data = ApiResponseParser.unwrapList(response.data, action: 'getRecommendedTasks');
      return data
          .map((json) => TaskModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getRecommendedTasks');
    }
  }

  /// Get tasks within a date range (for calendar markers)
  Future<List<TaskModel>> getTasksByDateRange(
    DateTime start,
    DateTime end,
  ) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService()
          .demoTasks
          .where((t) =>
              t.dueDate != null &&
              t.dueDate!.isAfter(start.subtract(const Duration(days: 1))) &&
              t.dueDate!.isBefore(end.add(const Duration(days: 1))),)
          .toList();
    }
    try {
      final dateFormat = DateFormat('yyyy-MM-dd');
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.tasks,
        queryParameters: {
          'due_date_start': dateFormat.format(start),
          'due_date_end': dateFormat.format(end),
          'page_size': 100, // Load all tasks for the month
          'page': 1,
        },
      );
      final data = ApiResponseParser.unwrapList(response.data, action: 'getTasksByDateRange');
      return data
          .map((json) => TaskModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getTasksByDateRange');
    }
  }

  Future<TaskModel> createTask(TaskCreate task, {bool generateGuide = false}) async {
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
        guideContent: generateGuide ? '# AI 执行指南\n\n1. 准备阶段\n2. 执行阶段\n3. 复习阶段' : null,
      );
      DemoDataService().demoTasks.add(newTask);
      return newTask;
    }
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.tasks,
        data: task.toJson(),
        queryParameters: generateGuide ? {'generate_guide': 'true'} : null,
      );
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'createTask');
      return TaskModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'createTask');
    }
  }

  /// Create task and return nudges if available
  Future<TaskCreateResult> createTaskWithNudges(TaskCreate task, {bool generateGuide = false}) async {
    if (DemoDataService.isDemoMode) {
      final newTask = await createTask(task, generateGuide: generateGuide);
      // Mock nudges for demo
      final nudges = task.estimatedMinutes < 30
          ? [
              TaskNudge(
                type: 'time_adjustment',
                title: '检测到规划乐观偏差',
                message: '根据您的历史行为模式，建议将预估时间调整为 ${task.estimatedMinutes * 130 ~/ 100} 分钟',
                suggestedValue: task.estimatedMinutes * 130 ~/ 100,
                confidence: 0.8,
              ),
            ]
          : <TaskNudge>[];
      return TaskCreateResult(task: newTask, nudges: nudges);
    }
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.tasks,
        data: task.toJson(),
        queryParameters: generateGuide ? {'generate_guide': 'true'} : null,
      );
      final payload = response.data;
      if (payload == null) {
        throw Exception('createTaskWithNudges response is empty');
      }
      // Handle both wrapped and direct formats
      final taskData = ApiResponseParser.unwrapMap(payload, action: 'createTaskWithNudges');
      final nudgesData = payload['nudges'] as List<dynamic>?;
      final taskModel = TaskModel.fromJson(taskData);
      final nudges = nudgesData
          ?.map((json) => TaskNudge.fromJson(json as Map<String, dynamic>))
          .toList() ?? <TaskNudge>[];
      return TaskCreateResult(task: taskModel, nudges: nudges);
    } on DioException catch (e) {
      return _handleDioError(e, 'createTaskWithNudges');
    }
  }

  Future<TaskModel> updateTask(String id, TaskUpdate task) async {
    if (DemoDataService.isDemoMode) {
      // Find and mock update
      final existingIndex =
          DemoDataService().demoTasks.indexWhere((t) => t.id == id);
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
      final response = await _apiClient.put<Map<String, dynamic>>(
        ApiEndpoints.task(id),
        data: task.toJson(),
      );
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'updateTask');
      return TaskModel.fromJson(payload);
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
      await _apiClient.delete<void>(ApiEndpoints.task(id));
    } on DioException catch (e) {
      return _handleDioError(e, 'deleteTask');
    }
  }

  Future<TaskModel> startTask(String id) async {
    if (DemoDataService.isDemoMode) {
      final existingIndex =
          DemoDataService().demoTasks.indexWhere((t) => t.id == id);
      if (existingIndex != -1) {
        final updated = DemoDataService()
            .demoTasks[existingIndex]
            .copyWith(status: TaskStatus.inProgress, startedAt: DateTime.now());
        DemoDataService().demoTasks[existingIndex] = updated;
        return updated;
      }
    }
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.startTask(id),
      );
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'startTask');
      return TaskModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'startTask');
    }
  }

  Future<TaskCompletionResult> completeTask(
      String id, int actualMinutes, String? note,) async {
    if (DemoDataService.isDemoMode) {
      final existingIndex =
          DemoDataService().demoTasks.indexWhere((t) => t.id == id);
      if (existingIndex != -1) {
        final updated = DemoDataService().demoTasks[existingIndex].copyWith(
              status: TaskStatus.completed,
              completedAt: DateTime.now(),
              actualMinutes: actualMinutes,
              userNote: note,
            );
        DemoDataService().demoTasks[existingIndex] = updated;
        // Demo mode: include mock next actions
        return TaskCompletionResult(
          task: updated.toJson(),
          feedback: 'Mock feedback: Great job!',
          flameUpdate: {'level': 15, 'brightness_change': 10},
          statsUpdate: {'total_minutes': 100, 'streak_days': 7},
          nextActions: const [
            NextAction(
              type: NextActionType.quickReview,
              title: '快速回顾',
              description: '回顾刚才的核心要点',
              estimatedMinutes: 5,
              energyCost: 1,
              difficulty: 1,
              reason: '及时回顾对抗遗忘',
            ),
            NextAction(
              type: NextActionType.lightExpand,
              title: '拓展: 相关概念',
              description: '了解相关知识点',
              estimatedMinutes: 10,
              energyCost: 2,
              difficulty: 2,
              reason: '加深理解',
            ),
          ],
        );
      }
    }
    try {
      final taskComplete =
          TaskComplete(actualMinutes: actualMinutes, userNote: note);
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.completeTask(id),
        data: taskComplete.toJson(),
      );
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'completeTask');
      return TaskCompletionResult.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'completeTask');
    }
  }

  Future<TaskModel> abandonTask(String id) async {
    if (DemoDataService.isDemoMode) {
      final existingIndex =
          DemoDataService().demoTasks.indexWhere((t) => t.id == id);
      if (existingIndex != -1) {
        final updated = DemoDataService()
            .demoTasks[existingIndex]
            .copyWith(status: TaskStatus.abandoned);
        DemoDataService().demoTasks[existingIndex] = updated;
        return updated;
      }
    }
    try {
      // Backend uses a POST for this action
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.abandonTask(id),
      );
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'abandonTask');
      return TaskModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'abandonTask');
    }
  }

  Future<TaskSuggestionResponse> getSuggestions(String inputText) async {
    if (DemoDataService.isDemoMode) {
      return TaskSuggestionResponse(
        intent: 'learning',
        suggestedNodes: [
          SuggestedNode(
              name: 'Data Structures',
              reason: 'Relevant to your text',
              isNew: false,),
        ],
        suggestedTags: ['CS'],
        estimatedMinutes: 60,
        difficulty: 3,
      );
    }
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.taskSuggestions,
        data: {'input_text': inputText},
      );
      final payload = ApiResponseParser.unwrapMap(response.data, action: 'getSuggestions');
      return TaskSuggestionResponse.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'getSuggestions');
    }
  }

  Future<void> submitTaskFeedback(
    String taskId,
    TaskFeedbackSubmission feedback,
  ) async {
    if (DemoDataService.isDemoMode) {
      // Demo mode: no-op - feedback is optional
      return;
    }
    try {
      await _apiClient.post<void>(
        ApiEndpoints.taskFeedback(taskId),
        data: feedback.toJson(),
      );
    } on DioException {
      // Feedback is optional - fail silently
      // Log for debugging but don't throw
      return;
    }
  }

  /// Submit task feedback and return the response with preference updates
  Future<TaskFeedbackResponse?> submitTaskFeedbackWithResponse(
    String taskId,
    TaskFeedbackSubmission feedback,
  ) async {
    if (DemoDataService.isDemoMode) {
      // Demo mode: return mock response
      return const TaskFeedbackResponse(
        success: true,
        message: '偏好已更新（演示模式）',
        preferenceUpdates: PreferenceUpdates(
          depthPreference: 0.02,
          difficultyPreference: -0.01,
        ),
      );
    }
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.taskFeedback(taskId),
        data: feedback.toJson(),
      );
      final payload = response.data;
      if (payload == null) {
        return null;
      }
      return TaskFeedbackResponse.fromJson(payload);
    } on DioException {
      // Feedback is optional - fail silently
      // Log for debugging but don't throw
      return null;
    }
  }

  Future<void> submitReflectionAnswer(
    String feedbackId, {
    String? selectedOption,
    String? freeText,
  }) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    try {
      await _apiClient.post<void>(
        ApiEndpoints.taskFeedbackReflection(feedbackId),
        data: {
          if (selectedOption != null && selectedOption.isNotEmpty)
            'selected_option': selectedOption,
          if (freeText != null && freeText.isNotEmpty) 'free_text': freeText,
        },
      );
    } on DioException catch (e) {
      _handleDioError<void>(e, 'submitReflectionAnswer');
    }
  }

  /// Record user interaction with next action suggestions
  Future<void> recordNextActionSelection(
    String taskId,
    NextActionSelectionSubmission selection,
  ) async {
    if (DemoDataService.isDemoMode) {
      // Demo mode: no-op
      return;
    }
    try {
      await _apiClient.post<void>(
        ApiEndpoints.nextActionSelection(taskId),
        data: selection.toJson(),
      );
    } on DioException {
      // Selection tracking is optional - fail silently
      return;
    }
  }

  /// Record skip (user skipped all next action suggestions)
  Future<void> recordNextActionsSkip(
    String taskId,
    List<NextAction> actions,
  ) async {
    if (DemoDataService.isDemoMode) {
      // Demo mode: no-op
      return;
    }
    try {
      final skipRecords = NextActionSelectionSubmission.createSkipRecords(
        taskId: taskId,
        actions: actions,
      );
      // Send all skip records
      for (final record in skipRecords) {
        await _apiClient.post<void>(
          ApiEndpoints.nextActionSelection(taskId),
          data: record.toJson(),
        );
      }
    } on DioException {
      // Selection tracking is optional - fail silently
      return;
    }
  }

  Future<Map<String, dynamic>> confirmGeneratedTasks(String toolResultId) async {
    final response = await _apiClient.post<dynamic>(
      '/tasks/confirm-batch/$toolResultId',
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to confirm tasks: ${response.data}');
    }
    final data = response.data;
    if (data is Map<String, dynamic>) {
      final wrapped = data['data'];
      if (wrapped is Map<String, dynamic>) {
        return wrapped;
      }
      return data;
    }
    throw Exception('Unexpected response format for confirmGeneratedTasks');
  }
}

// Provider for TaskRepository
final taskRepositoryProvider = Provider<TaskRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return TaskRepository(apiClient);
});
