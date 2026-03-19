import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/plan/data/models/learning_path_progress_model.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class PlanRepository {
  PlanRepository(this._apiClient);
  final ApiClient _apiClient;

  T _handleDioError<T>(DioException e, String functionName) {
    final detail =
        (e.response?.data as Map<String, dynamic>?)?['detail'] as String?;
    final errorMessage = detail ?? 'An unknown error occurred in $functionName';
    throw Exception(errorMessage);
  }

  Future<List<PlanModel>> getPlans({PlanType? type, bool? isActive}) async {
    if (DemoDataService.isDemoMode) {
      var plans = DemoDataService().demoPlans;
      if (type != null) plans = plans.where((p) => p.type == type).toList();
      if (isActive != null) {
        plans = plans.where((p) => p.isActive == isActive).toList();
      }
      return plans;
    }
    try {
      final query = <String, dynamic>{};
      if (type != null) query['type'] = type.name;
      if (isActive != null) query['is_active'] = isActive;

      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.plans,
        queryParameters: query,
      );
      final data =
          ApiResponseParser.unwrapList(response.data, action: 'getPlans');
      return data
          .map((json) => PlanModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getPlans');
    }
  }

  Future<PlanModel> getPlan(String id) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoPlans.firstWhere(
            (p) => p.id == id,
            orElse: () => DemoDataService().demoPlans.first,
          );
    }
    try {
      final response = await _apiClient.get<dynamic>(ApiEndpoints.plan(id));
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'getPlan');
      return PlanModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'getPlan');
    }
  }

  Future<List<PlanModel>> getActivePlans() async => getPlans(isActive: true);

  Future<PlanModel> createPlan(PlanCreate plan) async {
    if (DemoDataService.isDemoMode) {
      final demoService = DemoDataService();
      final newPlan = PlanModel(
        id: 'mock_plan_${DateTime.now().millisecondsSinceEpoch}',
        userId: demoService.demoUser.id,
        name: plan.name,
        type: plan.type,
        dailyAvailableMinutes: plan.dailyAvailableMinutes,
        masteryLevel: 0,
        progress: 0,
        isActive: true,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
        description: plan.description,
        targetDate: plan.targetDate,
        subject: plan.subject,
        priority: plan.priority,
        planStage: plan.type == PlanType.growth ? PlanStage.daily : PlanStage.sprint,
      );
      demoService.demoPlans.add(newPlan);
      return newPlan;
    }
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.plans,
        data: plan.toJson(),
      );
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'createPlan');
      return PlanModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'createPlan');
    }
  }

  Future<PlanModel> updatePlan(String id, PlanUpdate plan) async {
    if (DemoDataService.isDemoMode) {
      final demoPlans = DemoDataService().demoPlans;
      final index = demoPlans.indexWhere((p) => p.id == id);
      if (index != -1) {
        final existing = demoPlans[index];
        final updated = PlanModel(
          id: existing.id,
          userId: existing.userId,
          name: plan.name ?? existing.name,
          type: existing.type,
          dailyAvailableMinutes:
              plan.dailyAvailableMinutes ?? existing.dailyAvailableMinutes,
          masteryLevel: existing.masteryLevel,
          progress: existing.progress,
          isActive: plan.isActive ?? existing.isActive,
          createdAt: existing.createdAt,
          updatedAt: DateTime.now(),
          description: plan.description ?? existing.description,
          targetDate: plan.targetDate ?? existing.targetDate,
          subject: existing.subject,
          totalEstimatedHours: existing.totalEstimatedHours,
          tasks: existing.tasks,
          source: existing.source,
          sourceMetadata: existing.sourceMetadata,
          priority: plan.priority ?? existing.priority,
          planStage: plan.planStage ?? existing.planStage,
          isPrimary: existing.isPrimary,
        );
        demoPlans[index] = updated;
        return updated;
      }
    }
    try {
      final response = await _apiClient.put<dynamic>(
        ApiEndpoints.plan(id),
        data: plan.toJson(),
      );
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'updatePlan');
      return PlanModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'updatePlan');
    }
  }

  Future<void> deletePlan(String id) async {
    if (DemoDataService.isDemoMode) {
      DemoDataService().demoPlans.removeWhere((p) => p.id == id);
      return;
    }
    try {
      await _apiClient.delete<dynamic>(ApiEndpoints.plan(id));
    } on DioException catch (e) {
      return _handleDioError(e, 'deletePlan');
    }
  }

  Future<PlanModel> _updateActivation(String id, bool activate) async {
    if (DemoDataService.isDemoMode) {
      final demoPlans = DemoDataService().demoPlans;
      final index = demoPlans.indexWhere((p) => p.id == id);
      if (index != -1) {
        final existing = demoPlans[index];
        final updated = PlanModel(
          id: existing.id,
          userId: existing.userId,
          name: existing.name,
          type: existing.type,
          dailyAvailableMinutes: existing.dailyAvailableMinutes,
          masteryLevel: existing.masteryLevel,
          progress: existing.progress,
          isActive: activate,
          createdAt: existing.createdAt,
          updatedAt: DateTime.now(),
          description: existing.description,
          targetDate: existing.targetDate,
          subject: existing.subject,
          totalEstimatedHours: existing.totalEstimatedHours,
          tasks: existing.tasks,
          source: existing.source,
          sourceMetadata: existing.sourceMetadata,
          priority: existing.priority,
          planStage: existing.planStage,
          isPrimary: activate ? existing.isPrimary : false,
        );
        demoPlans[index] = updated;
        return updated;
      }
    }
    try {
      final planUpdate = PlanUpdate(isActive: activate);
      final response = await _apiClient.put<dynamic>(
        ApiEndpoints.plan(id),
        data: planUpdate.toJson(),
      );
      final payload = ApiResponseParser.unwrapMap(response.data,
          action: activate ? 'activatePlan' : 'deactivatePlan',);
      return PlanModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, activate ? 'activatePlan' : 'deactivatePlan');
    }
  }

  Future<PlanModel> activatePlan(String id) async =>
      _updateActivation(id, true);

  Future<PlanModel> deactivatePlan(String id) async =>
      _updateActivation(id, false);

  Future<List<TaskModel>> generateTasks(String planId, {int count = 5}) async {
    if (DemoDataService.isDemoMode) {
      final demoService = DemoDataService();
      final demoPlans = demoService.demoPlans;
      final index = demoPlans.indexWhere((p) => p.id == planId);
      if (index == -1) {
        return const [];
      }

      final plan = demoPlans[index];
      final now = DateTime.now();
      final generatedTasks = List.generate(count, (taskIndex) {
        final taskNumber = taskIndex + 1;
        return TaskModel(
                id: 'demo_plan_task_${planId}_${taskNumber}_${now.millisecondsSinceEpoch}',
          userId: demoService.demoUser.id,
          planId: planId,
          title: '${plan.name} - 第$taskNumber阶段任务',
          type: taskIndex.isEven ? TaskType.learning : TaskType.training,
          tags: [plan.subject ?? plan.name, 'Generated'],
          estimatedMinutes: 25 + (taskIndex * 10),
          difficulty: 2 + (taskIndex % 3),
          energyCost: 2 + (taskIndex % 2),
          status: TaskStatus.pending,
          priority: taskIndex == 0 ? 3 : 2,
          createdAt: now,
          updatedAt: now,
          dueDate: now.add(Duration(days: taskNumber * 2)),
        );
      });

      demoPlans[index] = PlanModel(
        id: plan.id,
        userId: plan.userId,
        name: plan.name,
        type: plan.type,
        dailyAvailableMinutes: plan.dailyAvailableMinutes,
        masteryLevel: plan.masteryLevel,
        progress: plan.progress,
        isActive: plan.isActive,
        createdAt: plan.createdAt,
        updatedAt: now,
        description: plan.description,
        targetDate: plan.targetDate,
        subject: plan.subject,
        totalEstimatedHours: plan.totalEstimatedHours,
        tasks: [...?plan.tasks, ...generatedTasks],
        source: plan.source,
        sourceMetadata: plan.sourceMetadata,
        priority: plan.priority,
        planStage: plan.planStage,
        isPrimary: plan.isPrimary,
      );
      return generatedTasks;
    }
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.generateTasks(planId),
        data: {'count': count},
      );
      final data =
          ApiResponseParser.unwrapList(response.data, action: 'generateTasks');
      return data
          .map((json) => TaskModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'generateTasks');
    }
  }

  Future<void> archivePlan(String id) async {
    if (DemoDataService.isDemoMode) {
      final demoPlans = DemoDataService().demoPlans;
      final index = demoPlans.indexWhere((p) => p.id == id);
      if (index != -1) {
        final existing = demoPlans[index];
        demoPlans[index] = PlanModel(
          id: existing.id,
          userId: existing.userId,
          name: existing.name,
          type: existing.type,
          dailyAvailableMinutes: existing.dailyAvailableMinutes,
          masteryLevel: existing.masteryLevel,
          progress: existing.progress,
          isActive: false,
          createdAt: existing.createdAt,
          updatedAt: DateTime.now(),
          description: existing.description,
          targetDate: existing.targetDate,
          subject: existing.subject,
          totalEstimatedHours: existing.totalEstimatedHours,
          tasks: existing.tasks,
          source: existing.source,
          sourceMetadata: existing.sourceMetadata,
          priority: existing.priority,
          planStage: existing.planStage,
          isPrimary: false,
        );
      }
      return;
    }
    try {
      await _apiClient.post<dynamic>(ApiEndpoints.planArchive(id));
    } on DioException catch (e) {
      return _handleDioError(e, 'archivePlan');
    }
  }

  Future<void> restorePlan(String id) async {
    if (DemoDataService.isDemoMode) {
      final demoPlans = DemoDataService().demoPlans;
      final index = demoPlans.indexWhere((p) => p.id == id);
      if (index != -1) {
        final existing = demoPlans[index];
        demoPlans[index] = PlanModel(
          id: existing.id,
          userId: existing.userId,
          name: existing.name,
          type: existing.type,
          dailyAvailableMinutes: existing.dailyAvailableMinutes,
          masteryLevel: existing.masteryLevel,
          progress: existing.progress,
          isActive: true,
          createdAt: existing.createdAt,
          updatedAt: DateTime.now(),
          description: existing.description,
          targetDate: existing.targetDate,
          subject: existing.subject,
          totalEstimatedHours: existing.totalEstimatedHours,
          tasks: existing.tasks,
          source: existing.source,
          sourceMetadata: existing.sourceMetadata,
          priority: existing.priority,
          planStage: existing.planStage,
          isPrimary: existing.isPrimary,
        );
      }
      return;
    }
    try {
      await _apiClient.post<dynamic>(ApiEndpoints.planRestore(id));
    } on DioException catch (e) {
      return _handleDioError(e, 'restorePlan');
    }
  }

  Future<LearningPathProgressModel> getLearningPathProgress(
      String planId,) async {
    if (DemoDataService.isDemoMode) {
      return LearningPathProgressModel(
        targetNode: LearningPathNodeProgress(
          id: 'demo_target',
          name: '目标节点',
          status: 'unlocked',
          mastery: 45,
          isTarget: true,
        ),
        nodes: [
          LearningPathNodeProgress(
            id: 'demo_1',
            name: '已掌握节点',
            status: 'mastered',
            mastery: 92,
          ),
          LearningPathNodeProgress(
            id: 'demo_2',
            name: '学习中节点',
            status: 'unlocked',
            mastery: 45,
          ),
          LearningPathNodeProgress(
            id: 'demo_target',
            name: '目标节点',
            status: 'locked',
            mastery: 0,
            isTarget: true,
          ),
        ],
        overallProgress: 0.33,
      );
    }
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.learningPathProgress(planId),
      );
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getLearningPathProgress',
      );
      return LearningPathProgressModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'getLearningPathProgress');
    }
  }
}

final planRepositoryProvider = Provider<PlanRepository>(
  (ref) => PlanRepository(ref.watch(apiClientProvider)),
);
