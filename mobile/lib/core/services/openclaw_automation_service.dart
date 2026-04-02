import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';

class OpenClawExecutionBatchItem {
  const OpenClawExecutionBatchItem({
    required this.intentId,
    required this.taskId,
    this.status,
    this.targetEnv,
    this.errorMessage,
  });

  factory OpenClawExecutionBatchItem.fromJson(Map<String, dynamic> json) =>
      OpenClawExecutionBatchItem(
        intentId: json['intent_id']?.toString() ?? '',
        taskId: json['task_id']?.toString() ?? '',
        status: json['status']?.toString(),
        targetEnv: json['target_env']?.toString(),
        errorMessage: json['error_message']?.toString(),
      );

  final String intentId;
  final String taskId;
  final String? status;
  final String? targetEnv;
  final String? errorMessage;
}

class OpenClawExecutionBatchSummary {
  const OpenClawExecutionBatchSummary({
    required this.batchId,
    required this.status,
    required this.requestedStrategy,
    required this.resolvedStrategy,
    this.taskIds = const <String>[],
    this.intentIds = const <String>[],
    this.completedCount = 0,
    this.failedCount = 0,
    this.queuedCount = 0,
    this.items = const <OpenClawExecutionBatchItem>[],
  });

  factory OpenClawExecutionBatchSummary.fromJson(Map<String, dynamic> json) =>
      OpenClawExecutionBatchSummary(
        batchId: json['batch_id']?.toString() ?? '',
        status: json['status']?.toString() ?? 'unknown',
        requestedStrategy: json['requested_strategy']?.toString() ?? 'auto',
        resolvedStrategy: json['resolved_strategy']?.toString() ?? 'auto',
        taskIds: (json['task_ids'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(growable: false),
        intentIds: (json['intent_ids'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(growable: false),
        completedCount: (json['completed_count'] as num?)?.toInt() ?? 0,
        failedCount: (json['failed_count'] as num?)?.toInt() ?? 0,
        queuedCount: (json['queued_count'] as num?)?.toInt() ?? 0,
        items: (json['items'] as List<dynamic>? ?? const [])
            .whereType<Map<dynamic, dynamic>>()
            .map(
              (item) => OpenClawExecutionBatchItem.fromJson(
                Map<String, dynamic>.from(item),
              ),
            )
            .toList(growable: false),
      );

  final String batchId;
  final String status;
  final String requestedStrategy;
  final String resolvedStrategy;
  final List<String> taskIds;
  final List<String> intentIds;
  final int completedCount;
  final int failedCount;
  final int queuedCount;
  final List<OpenClawExecutionBatchItem> items;
}

class OpenClawExecutionSchedule {
  const OpenClawExecutionSchedule({
    required this.id,
    required this.userId,
    required this.taskId,
    required this.intentTemplate,
    required this.triggerType,
    required this.triggerConfig,
    required this.isActive,
    this.lastRunAt,
    this.nextRunAt,
    this.createdAt,
    this.updatedAt,
  });

  factory OpenClawExecutionSchedule.fromJson(Map<String, dynamic> json) =>
      OpenClawExecutionSchedule(
        id: json['id']?.toString() ?? '',
        userId: json['user_id']?.toString() ?? '',
        taskId: json['task_id']?.toString() ?? '',
        intentTemplate: json['intent_template'] is Map
            ? Map<String, dynamic>.from(json['intent_template'] as Map)
            : const <String, dynamic>{},
        triggerType: json['trigger_type']?.toString() ?? 'cron',
        triggerConfig: json['trigger_config'] is Map
            ? Map<String, dynamic>.from(json['trigger_config'] as Map)
            : const <String, dynamic>{},
        isActive: json['is_active'] as bool? ?? true,
        lastRunAt: _tryParse(json['last_run_at']?.toString()),
        nextRunAt: _tryParse(json['next_run_at']?.toString()),
        createdAt: _tryParse(json['created_at']?.toString()),
        updatedAt: _tryParse(json['updated_at']?.toString()),
      );

  final String id;
  final String userId;
  final String taskId;
  final Map<String, dynamic> intentTemplate;
  final String triggerType;
  final Map<String, dynamic> triggerConfig;
  final bool isActive;
  final DateTime? lastRunAt;
  final DateTime? nextRunAt;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  static DateTime? _tryParse(String? value) =>
      value == null ? null : DateTime.tryParse(value);
}

class OpenClawAutomationService extends ChangeNotifier {
  OpenClawAutomationService({
    required Future<List<Map<String, dynamic>>> Function() schedulesLoader,
    required Future<Map<String, dynamic>> Function(Map<String, dynamic> payload)
        scheduleCreator,
    required Future<Map<String, dynamic>> Function(String scheduleId)
        schedulePauser,
    required Future<Map<String, dynamic>> Function(String scheduleId)
        scheduleResumer,
    required Future<void> Function(String scheduleId) scheduleDeleter,
    required Future<Map<String, dynamic>> Function(
      List<String> taskIds,
      String executionStrategy,
    )
        taskBatchHandoff,
  })  : _schedulesLoader = schedulesLoader,
        _scheduleCreator = scheduleCreator,
        _schedulePauser = schedulePauser,
        _scheduleResumer = scheduleResumer,
        _scheduleDeleter = scheduleDeleter,
        _taskBatchHandoff = taskBatchHandoff;

  final Future<List<Map<String, dynamic>>> Function() _schedulesLoader;
  final Future<Map<String, dynamic>> Function(Map<String, dynamic> payload)
      _scheduleCreator;
  final Future<Map<String, dynamic>> Function(String scheduleId)
      _schedulePauser;
  final Future<Map<String, dynamic>> Function(String scheduleId)
      _scheduleResumer;
  final Future<void> Function(String scheduleId) _scheduleDeleter;
  final Future<Map<String, dynamic>> Function(
    List<String> taskIds,
    String executionStrategy,
  ) _taskBatchHandoff;

  List<OpenClawExecutionSchedule> _schedules =
      const <OpenClawExecutionSchedule>[];
  OpenClawExecutionBatchSummary? _latestBatch;
  bool _isLoading = false;
  bool _isSubmittingBatch = false;
  bool _isSavingSchedule = false;
  String? _error;

  List<OpenClawExecutionSchedule> get schedules => List.unmodifiable(_schedules);
  OpenClawExecutionBatchSummary? get latestBatch => _latestBatch;
  bool get isLoading => _isLoading;
  bool get isSubmittingBatch => _isSubmittingBatch;
  bool get isSavingSchedule => _isSavingSchedule;
  String? get error => _error;

  Future<void> initialize() => refreshSchedules();

  Future<void> refreshSchedules() async {
    if (_isLoading) return;
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      final payload = await _schedulesLoader();
      _schedules = payload
          .map(OpenClawExecutionSchedule.fromJson)
          .where((item) => item.id.isNotEmpty)
          .toList(growable: false);
    } catch (error) {
      _error = error.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> createSchedule(Map<String, dynamic> payload) async {
    if (_isSavingSchedule) return false;
    _isSavingSchedule = true;
    _error = null;
    notifyListeners();
    try {
      final created = OpenClawExecutionSchedule.fromJson(
        await _scheduleCreator(payload),
      );
      _schedules = [created, ..._schedules];
      return true;
    } catch (error) {
      _error = error.toString();
      return false;
    } finally {
      _isSavingSchedule = false;
      notifyListeners();
    }
  }

  Future<bool> pauseSchedule(String scheduleId) async =>
      _mutateSchedule(scheduleId, _schedulePauser);

  Future<bool> resumeSchedule(String scheduleId) async =>
      _mutateSchedule(scheduleId, _scheduleResumer);

  Future<bool> deleteSchedule(String scheduleId) async {
    _error = null;
    notifyListeners();
    try {
      await _scheduleDeleter(scheduleId);
      _schedules = _schedules
          .where((schedule) => schedule.id != scheduleId)
          .toList(growable: false);
      notifyListeners();
      return true;
    } catch (error) {
      _error = error.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> handoffTaskBatch(
    List<String> taskIds, {
    String executionStrategy = 'auto',
  }) async {
    if (_isSubmittingBatch) return false;
    _isSubmittingBatch = true;
    _error = null;
    notifyListeners();
    try {
      final payload = await _taskBatchHandoff(taskIds, executionStrategy);
      _latestBatch = OpenClawExecutionBatchSummary.fromJson(payload);
      return true;
    } catch (error) {
      _error = error.toString();
      return false;
    } finally {
      _isSubmittingBatch = false;
      notifyListeners();
    }
  }

  Future<bool> _mutateSchedule(
    String scheduleId,
    Future<Map<String, dynamic>> Function(String scheduleId) action,
  ) async {
    _error = null;
    notifyListeners();
    try {
      final updated = OpenClawExecutionSchedule.fromJson(await action(scheduleId));
      _schedules = _schedules
          .map((schedule) => schedule.id == scheduleId ? updated : schedule)
          .toList(growable: false);
      notifyListeners();
      return true;
    } catch (error) {
      _error = error.toString();
      notifyListeners();
      return false;
    }
  }
}

final openClawAutomationProvider =
    ChangeNotifierProvider<OpenClawAutomationService>((ref) {
  final apiClient = ref.read(apiClientProvider);
  final service = OpenClawAutomationService(
    schedulesLoader: () async {
      final response = await apiClient.get<List<dynamic>>(
        ApiEndpoints.executionSchedules,
      );
      return ApiResponseParser.unwrapList(
        response.data,
        action: 'executionSchedules',
      )
          .whereType<Map<dynamic, dynamic>>()
          .map(Map<String, dynamic>.from)
          .toList(growable: false);
    },
    scheduleCreator: (payload) async {
      final response = await apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.executionSchedules,
        data: payload,
      );
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'createExecutionSchedule',
      );
    },
    schedulePauser: (scheduleId) async {
      final response = await apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.executionSchedulePause(scheduleId),
      );
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'pauseExecutionSchedule',
      );
    },
    scheduleResumer: (scheduleId) async {
      final response = await apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.executionScheduleResume(scheduleId),
      );
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'resumeExecutionSchedule',
      );
    },
    scheduleDeleter: (scheduleId) async {
      await apiClient.delete<dynamic>(
        ApiEndpoints.executionScheduleDelete(scheduleId),
      );
    },
    taskBatchHandoff: (taskIds, executionStrategy) async {
      final response = await apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.executionTaskBatchHandoff,
        data: <String, dynamic>{
          'task_ids': taskIds,
          'execution_strategy': executionStrategy,
        },
      );
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'executionTaskBatchHandoff',
      );
    },
  );
  unawaited(service.initialize());
  return service;
});
