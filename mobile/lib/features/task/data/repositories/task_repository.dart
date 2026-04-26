import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/task/data/models/execution_intent_model.dart';
import 'package:sparkle/features/task/data/models/execution_record_model.dart';
import 'package:sparkle/features/task/data/models/execution_template_model.dart';
import 'package:sparkle/features/task/data/models/next_action.dart';
import 'package:sparkle/features/task/data/models/next_action_selection_submission.dart';
import 'package:sparkle/features/task/data/models/task_completion_result.dart';
import 'package:sparkle/features/task/data/models/task_feedback_response.dart';
import 'package:sparkle/features/task/data/models/task_feedback_submission.dart';
import 'package:sparkle/features/task/data/models/task_nudge.dart';
import 'package:sparkle/shared/entities/subtask_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/models/api_response_model.dart';

enum TaskGuidanceAudience { human, ai }

extension TaskGuidanceAudienceX on TaskGuidanceAudience {
  String get wireValue => switch (this) {
        TaskGuidanceAudience.human => 'human',
        TaskGuidanceAudience.ai => 'ai',
      };
}

class TaskGuidanceModel {
  TaskGuidanceModel({
    required this.id,
    required this.taskId,
    required this.userId,
    required this.audience,
    required this.content,
    required this.generatedBy,
    required this.policyVersion,
    required this.contentFormat,
    required this.createdAt,
    required this.updatedAt,
    this.sourceGuidanceId,
    this.sourceTaskUpdatedAt,
  });

  factory TaskGuidanceModel.fromJson(Map<String, dynamic> json) {
    dynamic valueForKeys(List<String> keys) {
      for (final key in keys) {
        if (json.containsKey(key)) {
          return json[key];
        }
      }
      return null;
    }

    String readString(List<String> keys, {String fallback = ''}) {
      final value = valueForKeys(keys);
      return value?.toString() ?? fallback;
    }

    DateTime readDateTime(List<String> keys) {
      final value = valueForKeys(keys);
      if (value is DateTime) {
        return value;
      }
      final parsed = DateTime.tryParse(value?.toString() ?? '');
      if (parsed == null) {
        throw FormatException(
          'Invalid task guidance datetime for ${keys.first}: $value',
        );
      }
      return parsed;
    }

    DateTime? readNullableDateTime(List<String> keys) {
      final value = valueForKeys(keys);
      if (value == null) {
        return null;
      }
      if (value is DateTime) {
        return value;
      }
      return DateTime.tryParse(value.toString());
    }

    final audienceValue =
        readString(['audience'], fallback: 'human').toLowerCase();
    final audience = audienceValue == 'ai'
        ? TaskGuidanceAudience.ai
        : TaskGuidanceAudience.human;
    return TaskGuidanceModel(
      id: readString(['id']),
      taskId: readString(['task_id', 'taskId']),
      userId: readString(['user_id', 'userId']),
      audience: audience,
      content: readString(['content']),
      generatedBy:
          readString(['generated_by', 'generatedBy'], fallback: 'unknown'),
      policyVersion: readString(
        ['policy_version', 'policyVersion'],
        fallback: 'stage4.task_guidance.v1',
      ),
      contentFormat: readString(
        ['content_format', 'contentFormat'],
        fallback: 'markdown',
      ),
      createdAt: readDateTime(['created_at', 'createdAt']),
      updatedAt: readDateTime(['updated_at', 'updatedAt']),
      sourceGuidanceId:
          valueForKeys(['source_guidance_id', 'sourceGuidanceId'])?.toString(),
      sourceTaskUpdatedAt: readNullableDateTime(
        ['source_task_updated_at', 'sourceTaskUpdatedAt'],
      ),
    );
  }

  final String id;
  final String taskId;
  final String userId;
  final TaskGuidanceAudience audience;
  final String content;
  final String generatedBy;
  final String policyVersion;
  final String contentFormat;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? sourceGuidanceId;
  final DateTime? sourceTaskUpdatedAt;
}

class TaskQuickActionResult {
  const TaskQuickActionResult({
    required this.action,
    required this.message,
    required this.task,
    this.subtasks = const [],
  });

  factory TaskQuickActionResult.fromResponse(Map<String, dynamic> response) {
    final payload = ApiResponseParser.unwrapMap(
      response,
      action: 'taskQuickAction',
    );
    final taskPayload = (payload['task'] is Map<String, dynamic>)
        ? payload['task'] as Map<String, dynamic>
        : payload;
    final subtasksPayload = payload['subtasks'] as List<dynamic>? ?? const [];

    return TaskQuickActionResult(
      action:
          response['action']?.toString() ?? payload['action']?.toString() ?? '',
      message: response['message']?.toString() ??
          payload['message']?.toString() ??
          '',
      task: TaskModel.fromJson(taskPayload),
      subtasks: subtasksPayload
          .whereType<Map<String, dynamic>>()
          .map(SubTaskModel.fromJson)
          .toList(),
    );
  }

  final String action;
  final String message;
  final TaskModel task;
  final List<SubTaskModel> subtasks;
}

class TaskStuckResult {
  const TaskStuckResult({
    required this.task,
    required this.diagnosis,
    required this.message,
  });

  factory TaskStuckResult.fromResponse(Map<String, dynamic> response) {
    final payload = ApiResponseParser.unwrapMap(response, action: 'taskStuck');
    final taskPayload = (payload['task'] is Map<String, dynamic>)
        ? payload['task'] as Map<String, dynamic>
        : payload;
    final diagnosisPayload = payload['diagnosis'] is Map<String, dynamic>
        ? payload['diagnosis'] as Map<String, dynamic>
        : const <String, dynamic>{};
    return TaskStuckResult(
      task: TaskModel.fromJson(taskPayload),
      diagnosis: diagnosisPayload,
      message: response['message']?.toString() ??
          payload['message']?.toString() ??
          '',
    );
  }

  final TaskModel task;
  final Map<String, dynamic> diagnosis;
  final String message;
}

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

  Future<String?> _resolveTaskCardId(String taskId) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.cardsSearch,
      queryParameters: {
        'card_type': 'TASK',
        'legacy_task_id': taskId,
        'limit': 1,
      },
    );
    final data = ApiResponseParser.unwrapList(
      response.data,
      action: 'resolveTaskCardId',
    );
    if (data.isEmpty) return null;
    return (data.first as Map<String, dynamic>)['card_id'] as String?;
  }

  Future<String?> _resolvePlanCardId(String planId) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.cardsSearch,
      queryParameters: {
        'card_type': 'PLAN',
        'legacy_plan_id': planId,
        'limit': 1,
      },
    );
    final data = ApiResponseParser.unwrapList(
      response.data,
      action: 'resolvePlanCardId',
    );
    if (data.isEmpty) return null;
    return (data.first as Map<String, dynamic>)['card_id'] as String?;
  }

  String _taskGuidancePath(String taskId) =>
      '${ApiEndpoints.task(taskId)}/guidance';

  TaskQuickActionResult _parseQuickActionResponse(
    Map<String, dynamic>? responseData, {
    required String action,
  }) {
    if (responseData == null) {
      throw Exception('$action response is empty');
    }
    return TaskQuickActionResult.fromResponse(responseData);
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
          filters.map((key, value) => MapEntry(key, value.toString())),
        );
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
      return DemoDataService().demoTasks.firstWhere(
            (t) => t.id == id,
            orElse: () => DemoDataService().demoTasks.first,
          );
    }
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.task(id),
      );
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'getTask');
      return TaskModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'getTask');
    }
  }

  Future<void> moveTaskToPlan(
    String taskId,
    String? targetPlanId,
  ) async {
    if (DemoDataService.isDemoMode) {
      final demoTasks = DemoDataService().demoTasks;
      final taskIndex = demoTasks.indexWhere((task) => task.id == taskId);
      if (taskIndex != -1) {
        demoTasks[taskIndex] =
            demoTasks[taskIndex].copyWith(planId: targetPlanId);
      }
      return;
    }

    try {
      final taskCardId = await _resolveTaskCardId(taskId);
      if (taskCardId == null) {
        throw Exception('Task card not found');
      }
      String? planCardId;
      if (targetPlanId != null && targetPlanId.isNotEmpty) {
        planCardId = await _resolvePlanCardId(targetPlanId);
        if (planCardId == null) {
          throw Exception('Target plan card not found');
        }
      }

      await _apiClient.post<dynamic>(
        ApiEndpoints.moveCard(taskCardId),
        data: {
          'new_parent_card_id': planCardId,
        },
      );
    } on DioException catch (e) {
      return _handleDioError(e, 'moveTaskToPlan');
    }
  }

  Future<ExecutionIntentModel> handoffTask(
    String taskId, {
    String? goal,
    List<String>? instructions,
    String? templateId,
    String? source,
  }) async {
    if (DemoDataService.isDemoMode) {
      return ExecutionIntentModel.fromJson({
        'id': 'demo_exec_${DateTime.now().millisecondsSinceEpoch}',
        'task_id': taskId,
        'execution_mode': 'agent',
        'executor': 'openclaw',
        'status': 'succeeded',
        'trust_level': 'validated',
        'goal': goal ?? 'Demo AI handoff',
        'template_name': templateId,
        'created_at': DateTime.now().toIso8601String(),
        'completed_at': DateTime.now().toIso8601String(),
      });
    }

    try {
      final payload = <String, dynamic>{
        if (goal != null && goal.trim().isNotEmpty) 'goal': goal.trim(),
        if (instructions != null && instructions.isNotEmpty)
          'instructions': instructions,
        if (templateId != null && templateId.trim().isNotEmpty)
          'template_id': templateId.trim(),
        if (source != null && source.trim().isNotEmpty) 'source': source.trim(),
      };
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.handoffTaskExecution(taskId),
        data: payload,
      );
      final data =
          ApiResponseParser.unwrapMap(response.data, action: 'handoffTask');
      return ExecutionIntentModel.fromJson(data);
    } on DioException catch (e) {
      return _handleDioError(e, 'handoffTask');
    }
  }

  Future<List<ExecutionTemplateModel>> listExecutionTemplates(
    String taskId,
  ) async {
    if (DemoDataService.isDemoMode) {
      return [
        const ExecutionTemplateModel(
          templateId: 'web_research_brief',
          name: '网页调研简报',
          description: '适合搜索与总结',
          executionMode: ExecutionMode.agent,
          targetEnv: 'browser',
          matchScore: 0.91,
          matchReasons: ['keyword:搜索'],
        ),
      ];
    }

    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.executionTemplates(taskId),
      );
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'listExecutionTemplates',
      );
      return data
          .map(
            (json) =>
                ExecutionTemplateModel.fromJson(json as Map<String, dynamic>),
          )
          .toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'listExecutionTemplates');
    }
  }

  Future<List<ExecutionIntentModel>> listExecutionIntents(String taskId) async {
    if (DemoDataService.isDemoMode) {
      return const [];
    }

    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.taskExecutionIntents(taskId),
      );
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'listExecutionIntents',
      );
      return data
          .map(
            (json) =>
                ExecutionIntentModel.fromJson(json as Map<String, dynamic>),
          )
          .toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'listExecutionIntents');
    }
  }

  Future<ExecutionRecordModel?> getExecutionRecord(String intentId) async {
    if (DemoDataService.isDemoMode) {
      return null;
    }

    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.executionRecord(intentId),
      );
      final data = response.data;
      if (data == null) return null;
      final payload = ApiResponseParser.unwrapMap(
        data,
        action: 'getExecutionRecord',
      );
      if (payload.isEmpty) return null;
      return ExecutionRecordModel.fromJson(payload);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      return _handleDioError(e, 'getExecutionRecord');
    }
  }

  Future<ExecutionIntentModel> retryExecution(String intentId) async {
    if (DemoDataService.isDemoMode) {
      return ExecutionIntentModel.fromJson({
        'id': 'demo_retry_${DateTime.now().millisecondsSinceEpoch}',
        'task_id': 'demo_task',
        'execution_mode': 'agent',
        'executor': 'openclaw',
        'status': 'running',
        'trust_level': 'raw',
        'goal': 'Demo retry',
        'created_at': DateTime.now().toIso8601String(),
      });
    }

    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.retryExecution(intentId),
      );
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'retryExecution',
      );
      return ExecutionIntentModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'retryExecution');
    }
  }

  Future<ExecutionRecordModel> confirmExecutionResult(String recordId) async {
    if (DemoDataService.isDemoMode) {
      return ExecutionRecordModel.fromJson({
        'id': recordId,
        'execution_intent_id': 'demo_intent',
        'trust_level': 'trusted',
        'artifacts': <Object>[],
      });
    }

    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.confirmExecutionResult(recordId),
      );
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'confirmExecutionResult',
      );
      return ExecutionRecordModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'confirmExecutionResult');
    }
  }

  Future<ExecutionRecordModel> rejectExecutionResult(
    String recordId, {
    String? reason,
  }) async {
    if (DemoDataService.isDemoMode) {
      return ExecutionRecordModel.fromJson({
        'id': recordId,
        'execution_intent_id': 'demo_intent',
        'trust_level': 'raw',
        'artifacts': <Object>[],
        'error_category': 'user_rejected',
        'error_message': reason ?? 'Rejected by user',
      });
    }

    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.rejectExecutionResult(recordId),
        data: {
          if (reason != null && reason.trim().isNotEmpty)
            'reason': reason.trim(),
        },
      );
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'rejectExecutionResult',
      );
      return ExecutionRecordModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'rejectExecutionResult');
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
      final data =
          ApiResponseParser.unwrapList(response.data, action: 'getTodayTasks');
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
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getRecommendedTasks',
      );
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
          .where(
            (t) =>
                t.dueDate != null &&
                t.dueDate!.isAfter(start.subtract(const Duration(days: 1))) &&
                t.dueDate!.isBefore(end.add(const Duration(days: 1))),
          )
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
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getTasksByDateRange',
      );
      return data
          .map((json) => TaskModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getTasksByDateRange');
    }
  }

  Future<TaskModel> createTask(
    TaskCreate task, {
    bool generateGuide = false,
  }) async {
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
        guideContent:
            generateGuide ? '# AI 执行指南\n\n1. 准备阶段\n2. 执行阶段\n3. 复习阶段' : null,
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
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'createTask');
      return TaskModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'createTask');
    }
  }

  /// Create task and return nudges if available
  Future<TaskCreateResult> createTaskWithNudges(
    TaskCreate task, {
    bool generateGuide = false,
  }) async {
    if (DemoDataService.isDemoMode) {
      final newTask = await createTask(task, generateGuide: generateGuide);
      // Mock nudges for demo
      final nudges = task.estimatedMinutes < 30
          ? [
              TaskNudge(
                type: 'time_adjustment',
                title: '检测到规划乐观偏差',
                message:
                    '根据您的历史行为模式，建议将预估时间调整为 ${task.estimatedMinutes * 130 ~/ 100} 分钟',
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
      final taskData =
          ApiResponseParser.unwrapMap(payload, action: 'createTaskWithNudges');
      final nudgesData = _extractNudges(payload, taskData);
      final taskModel = TaskModel.fromJson(taskData);
      final nudges = nudgesData
              ?.map((json) => TaskNudge.fromJson(json as Map<String, dynamic>))
              .toList() ??
          <TaskNudge>[];
      return TaskCreateResult(task: taskModel, nudges: nudges);
    } on DioException catch (e) {
      return _handleDioError(e, 'createTaskWithNudges');
    }
  }

  List<dynamic>? _extractNudges(
    Map<String, dynamic> responsePayload,
    Map<String, dynamic> taskPayload,
  ) {
    final candidates = <dynamic>[
      responsePayload['nudges'],
      responsePayload['nudge'],
      taskPayload['nudges'],
      taskPayload['nudge'],
    ];
    for (final candidate in candidates) {
      if (candidate is List<dynamic>) {
        return candidate;
      }
      if (candidate is Map<String, dynamic>) {
        return <dynamic>[candidate];
      }
    }
    return null;
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
          type: task.type ?? existing.type,
          estimatedMinutes: task.estimatedMinutes ?? existing.estimatedMinutes,
          difficulty: task.difficulty ?? existing.difficulty,
          tags: task.tags ?? existing.tags,
          status: task.status ?? existing.status,
          dueDate: task.dueDate ?? existing.dueDate,
          updatedAt: DateTime.now(),
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
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'updateTask');
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

  Future<List<TaskModel>> reorderTasks(List<String> taskIds) async {
    if (DemoDataService.isDemoMode) {
      final demoTasks = DemoDataService().demoTasks;
      final taskMap = {for (final task in demoTasks) task.id: task};
      final reordered = <TaskModel>[];
      for (var i = 0; i < taskIds.length; i++) {
        final task = taskMap[taskIds[i]];
        if (task != null) {
          reordered.add(task.copyWith(orderIndex: (i + 1) * 1000));
        }
      }
      demoTasks
        ..clear()
        ..addAll(reordered);
      return reordered;
    }
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.tasksReorder,
        data: {'task_ids': taskIds},
      );
      final data =
          ApiResponseParser.unwrapList(response.data, action: 'reorderTasks');
      return data
          .map((json) => TaskModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'reorderTasks');
    }
  }

  /// Generate or regenerate AI guide for an existing task.
  Future<TaskModel> generateGuide(String id) async {
    if (DemoDataService.isDemoMode) {
      final existingIndex =
          DemoDataService().demoTasks.indexWhere((t) => t.id == id);
      if (existingIndex != -1) {
        final existing = DemoDataService().demoTasks[existingIndex];
        final updated = existing.copyWith(
          guideContent: _demoGuide(existing.title),
        );
        DemoDataService().demoTasks[existingIndex] = updated;
        return updated;
      }
      throw Exception('Task not found in demo data');
    }
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.taskGenerateGuide(id),
      );
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'generateGuide');
      return TaskModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'generateGuide');
    }
  }

  Future<TaskGuidanceModel?> getTaskGuidance(
    String taskId, {
    TaskGuidanceAudience audience = TaskGuidanceAudience.human,
  }) async {
    if (DemoDataService.isDemoMode) {
      final existing = DemoDataService().demoTasks.firstWhere(
            (task) => task.id == taskId,
            orElse: () => DemoDataService().demoTasks.first,
          );
      final content = audience == TaskGuidanceAudience.ai
          ? 'TASK_GUIDANCE_SCAFFOLD v1\n'
              'task_id=$taskId\n'
              'task_title=${existing.title}\n'
              'Use this only inside Sparkle task assistant.'
          : (existing.guideContent ?? _demoGuide(existing.title));
      return TaskGuidanceModel(
        id: 'demo_${taskId}_${audience.wireValue}',
        taskId: taskId,
        userId: existing.userId,
        audience: audience,
        content: content,
        generatedBy: audience == TaskGuidanceAudience.ai
            ? 'task_guidance_ai_scaffold'
            : 'demo_task_guidance',
        policyVersion: 'stage4.task_guidance.v1',
        contentFormat:
            audience == TaskGuidanceAudience.ai ? 'plaintext' : 'markdown',
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );
    }

    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        _taskGuidancePath(taskId),
        queryParameters: {'audience': audience.wireValue},
      );
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getTaskGuidance',
      );
      if (payload.isEmpty) return null;
      return TaskGuidanceModel.fromJson(payload);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      return _handleDioError(e, 'getTaskGuidance');
    }
  }

  Future<TaskGuidanceModel> createOrRefreshTaskGuidance(
    String taskId, {
    TaskGuidanceAudience audience = TaskGuidanceAudience.human,
    bool regenerate = false,
  }) async {
    if (DemoDataService.isDemoMode) {
      final guidance = await getTaskGuidance(taskId, audience: audience);
      if (guidance == null) {
        throw Exception('Task guidance not found in demo data');
      }
      return guidance;
    }

    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        _taskGuidancePath(taskId),
        queryParameters: {
          'audience': audience.wireValue,
          if (regenerate) 'regenerate': 'true',
        },
      );
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'createOrRefreshTaskGuidance',
      );
      return TaskGuidanceModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'createOrRefreshTaskGuidance');
    }
  }

  Future<TaskQuickActionResult> snoozeTask(
    String id, {
    int days = 1,
    DateTime? targetDate,
    String? reason,
  }) async {
    if (DemoDataService.isDemoMode) {
      final existingIndex =
          DemoDataService().demoTasks.indexWhere((t) => t.id == id);
      if (existingIndex == -1) {
        throw Exception('Task not found in demo data');
      }
      final existing = DemoDataService().demoTasks[existingIndex];
      final nextDate = targetDate ?? DateTime.now().add(Duration(days: days));
      final updated = existing.copyWith(
        dueDate: DateTime(nextDate.year, nextDate.month, nextDate.day),
        tags: {
          ...existing.tags,
          'snoozed',
        }.toList(),
        updatedAt: DateTime.now(),
      );
      DemoDataService().demoTasks[existingIndex] = updated;
      return TaskQuickActionResult(
        action: 'snooze',
        message: '已推迟到明天，今天先把节奏放轻一点。',
        task: updated,
      );
    }

    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.snoozeTask(id),
        data: {
          'days': days,
          if (reason != null && reason.isNotEmpty) 'reason': reason,
          if (targetDate != null)
            'target_date': DateFormat('yyyy-MM-dd').format(targetDate),
        },
      );
      return _parseQuickActionResponse(response.data, action: 'snoozeTask');
    } on DioException catch (e) {
      return _handleDioError(e, 'snoozeTask');
    }
  }

  Future<TaskQuickActionResult> markTaskTooHard(
    String id, {
    String? reason,
  }) async {
    if (DemoDataService.isDemoMode) {
      final existingIndex =
          DemoDataService().demoTasks.indexWhere((t) => t.id == id);
      if (existingIndex == -1) {
        throw Exception('Task not found in demo data');
      }
      final existing = DemoDataService().demoTasks[existingIndex];
      final now = DateTime.now();
      final subtasks = [
        SubTaskModel(
          id: 'demo_${id}_step_1',
          parentTaskId: id,
          title: '先找出最卡的一点',
          order: 0,
          status: SubTaskStatus.pending,
          createdAt: now,
          updatedAt: now,
          estimatedMinutes: 5,
          guideContent: '只定位卡点，不解决整张任务卡。',
        ),
        SubTaskModel(
          id: 'demo_${id}_step_2',
          parentTaskId: id,
          title: '把这个卡点讲成一句人话',
          order: 1,
          status: SubTaskStatus.pending,
          createdAt: now,
          updatedAt: now,
          estimatedMinutes: 10,
          guideContent: '先讲清楚，再决定下一步。',
        ),
        SubTaskModel(
          id: 'demo_${id}_step_3',
          parentTaskId: id,
          title: '做一个最小验证动作',
          order: 2,
          status: SubTaskStatus.pending,
          createdAt: now,
          updatedAt: now,
          estimatedMinutes: 10,
          guideContent: '只验证刚拆出来的这一步。',
        ),
      ];
      final updated = existing.copyWith(
        difficulty: existing.difficulty > 1 ? existing.difficulty - 1 : 1,
        subtasksTotal: subtasks.length,
        tags: {
          ...existing.tags,
          'too_hard',
          'adaptive_breakdown',
        }.toList(),
        updatedAt: now,
      );
      DemoDataService().demoTasks[existingIndex] = updated;
      return TaskQuickActionResult(
        action: 'too_hard',
        message: '我把它拆成 3 小步了，先做「${subtasks.first.title}」。',
        task: updated,
        subtasks: subtasks,
      );
    }

    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.taskTooHard(id),
        data: {
          if (reason != null && reason.isNotEmpty) 'reason': reason,
        },
      );
      return _parseQuickActionResponse(
        response.data,
        action: 'markTaskTooHard',
      );
    } on DioException catch (e) {
      return _handleDioError(e, 'markTaskTooHard');
    }
  }

  Future<TaskQuickActionResult> skipTask(
    String id, {
    String? reason,
  }) async {
    if (DemoDataService.isDemoMode) {
      final existingIndex =
          DemoDataService().demoTasks.indexWhere((t) => t.id == id);
      if (existingIndex == -1) {
        throw Exception('Task not found in demo data');
      }
      final updated = DemoDataService().demoTasks[existingIndex].copyWith(
            status: TaskStatus.abandoned,
            userNote: 'Skipped from quick action',
            completedAt: DateTime.now(),
            updatedAt: DateTime.now(),
          );
      DemoDataService().demoTasks[existingIndex] = updated;
      return TaskQuickActionResult(
        action: 'skip',
        message: '已跳过，这张卡不会再挤在今天了。',
        task: updated,
      );
    }

    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.skipTask(id),
        data: {
          if (reason != null && reason.isNotEmpty) 'reason': reason,
        },
      );
      return _parseQuickActionResponse(response.data, action: 'skipTask');
    } on DioException catch (e) {
      return _handleDioError(e, 'skipTask');
    }
  }

  String _demoGuide(String title) => '''
# $title

## 🎯 任务目标
明确任务的核心产出和完成标准。

## 📋 准备清单
- [ ] 确认相关资料已就绪
- [ ] 设定专注时间段
- [ ] 排除干扰因素

## 📍 执行步骤

### 步骤 1: 理解与拆解
- 梳理任务要求和关键点
- 将大任务拆分为可执行的小步骤

### 步骤 2: 核心执行
- 按优先级逐步完成各项子任务
- 及时记录关键发现和笔记

### 步骤 3: 检查与总结
- 对照完成标准自查
- 记录经验教训和改进点

## 💡 注意事项
- 保持专注，使用番茄工作法
- 遇到难点先标记，后续集中攻克
- 完成后及时在星火中记录反思

## ✅ 完成标准
- [ ] 核心内容已完成
- [ ] 质量达到预期标准
- [ ] 已记录总结和反思
''';

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
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'startTask');
      return TaskModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'startTask');
    }
  }

  Future<TaskStuckResult> markTaskStuck(
    String id, {
    String? stuckPoint,
    List<String> recentSteps = const [],
    int? currentStepIndex,
    int? elapsedSeconds,
    String? trigger,
  }) async {
    if (DemoDataService.isDemoMode) {
      final existingIndex =
          DemoDataService().demoTasks.indexWhere((t) => t.id == id);
      if (existingIndex == -1) {
        throw Exception('Task not found in demo data');
      }
      final existing = DemoDataService().demoTasks[existingIndex];
      final diagnosis = <String, dynamic>{
        'diagnosis_question': '你现在最像卡在哪一步？',
        'diagnosis_options': ['概念没想清', '步骤顺序乱了', '题目条件不会用'],
        'targeted_fix': '先只做一个 5 分钟内能完成的小动作。',
        'check_question': '下一步你能先写下哪一句？',
        'source': 'demo',
      };
      final updated = existing.copyWith(
        status: TaskStatus.stuck,
        guideJson: {
          ...?existing.guideJson,
          'stuck_help': diagnosis,
        },
        updatedAt: DateTime.now(),
      );
      DemoDataService().demoTasks[existingIndex] = updated;
      return TaskStuckResult(
        task: updated,
        diagnosis: diagnosis,
        message: 'Aurora 已根据当前任务状态给出诊断。',
      );
    }

    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.taskStuck(id),
        data: {
          if (stuckPoint != null && stuckPoint.isNotEmpty)
            'stuck_point': stuckPoint,
          if (recentSteps.isNotEmpty) 'recent_steps': recentSteps,
          if (currentStepIndex != null) 'current_step_index': currentStepIndex,
          if (elapsedSeconds != null) 'elapsed_seconds': elapsedSeconds,
          if (trigger != null && trigger.isNotEmpty) 'trigger': trigger,
        },
      );
      return TaskStuckResult.fromResponse(response.data ?? <String, dynamic>{});
    } on DioException catch (e) {
      return _handleDioError(e, 'markTaskStuck');
    }
  }

  Future<TaskCompletionResult> completeTask(
    String id,
    int actualMinutes,
    String? note,
  ) async {
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
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'completeTask');
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
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'abandonTask');
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
            isNew: false,
          ),
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
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'getSuggestions');
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
    } on DioException catch (e) {
      return _handleDioError(e, 'submitTaskFeedback');
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
        return const TaskFeedbackResponse(success: true);
      }
      return TaskFeedbackResponse.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'submitTaskFeedbackWithResponse');
    }
  }

  Future<void> submitReflectionAnswer(
    String feedbackId, {
    String? selectedOption,
    String? freeText,
    String? stuckPoint,
    String? effectiveMethod,
    String? adjustmentIntention,
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
          if (stuckPoint != null && stuckPoint.isNotEmpty)
            'stuck_point': stuckPoint,
          if (effectiveMethod != null && effectiveMethod.isNotEmpty)
            'effective_method': effectiveMethod,
          if (adjustmentIntention != null && adjustmentIntention.isNotEmpty)
            'adjustment_intention': adjustmentIntention,
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

  Future<Map<String, dynamic>> confirmGeneratedTasks(
    String toolResultId,
  ) async {
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
