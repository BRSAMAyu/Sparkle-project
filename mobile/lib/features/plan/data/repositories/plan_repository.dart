import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/plan/data/models/learning_path_progress_model.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/models/plan_phase_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/core/services/i18n_service.dart';

class PlanRepository {
  PlanRepository(this._apiClient);
  final ApiClient _apiClient;
  static final Map<String, PlanPhaseBundle> _demoPhaseStore = {};

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
        planStage:
            plan.type == PlanType.growth ? PlanStage.daily : PlanStage.sprint,
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
          dayHighlights: existing.dayHighlights,
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
      await _apiClient.post<dynamic>(ApiEndpoints.planArchive(id));
    } on DioException catch (e) {
      return _handleDioError(e, 'deletePlan');
    }
  }

  Future<void> _updateActivation(String id, bool activate) async {
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
          dayHighlights: existing.dayHighlights,
          priority: existing.priority,
          planStage: existing.planStage,
          isPrimary: activate ? existing.isPrimary : false,
        );
        demoPlans[index] = updated;
        return;
      }
      return;
    }
    try {
      await _apiClient.post<dynamic>(
        activate ? ApiEndpoints.planRestore(id) : ApiEndpoints.planArchive(id),
      );
    } on DioException catch (e) {
      return _handleDioError<void>(
        e,
        activate ? 'activatePlan' : 'deactivatePlan',
      );
    }
  }

  Future<void> activatePlan(String id) async => _updateActivation(id, true);

  Future<void> deactivatePlan(String id) async => _updateActivation(id, false);

  Future<void> setPrimaryPlan(String id) async {
    if (DemoDataService.isDemoMode) {
      final demoPlans = DemoDataService().demoPlans;
      for (var i = 0; i < demoPlans.length; i++) {
        final existing = demoPlans[i];
        demoPlans[i] = PlanModel(
          id: existing.id,
          userId: existing.userId,
          name: existing.name,
          type: existing.type,
          dailyAvailableMinutes: existing.dailyAvailableMinutes,
          masteryLevel: existing.masteryLevel,
          progress: existing.progress,
          isActive: existing.isActive,
          createdAt: existing.createdAt,
          updatedAt: DateTime.now(),
          description: existing.description,
          targetDate: existing.targetDate,
          subject: existing.subject,
          totalEstimatedHours: existing.totalEstimatedHours,
          tasks: existing.tasks,
          source: existing.source,
          sourceMetadata: existing.sourceMetadata,
          dayHighlights: existing.dayHighlights,
          priority: existing.priority,
          planStage: existing.planStage,
          isPrimary: existing.id == id,
        );
      }
      return;
    }
    try {
      await _apiClient.post<dynamic>(
        ApiEndpoints.planPrimary,
        data: {'plan_id': id},
      );
    } on DioException catch (e) {
      return _handleDioError(e, 'setPrimaryPlan');
    }
  }

  Future<PlanPhaseBundle> getPlanPhases(String planId) async {
    if (DemoDataService.isDemoMode) {
      return _demoPhaseStore[planId] ??
          PlanPhaseBundle(
            planCardId: null,
            currentPhaseCardId: null,
            progressMode: 'legacy',
            weightedProgress: null,
            phases: const [],
          );
    }
    try {
      final response =
          await _apiClient.get<dynamic>(ApiEndpoints.planPhases(planId));
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'getPlanPhases');
      return PlanPhaseBundle.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'getPlanPhases');
    }
  }

  Future<PlanPhaseModel?> createPhase(
    String planId, {
    required String name,
    required int phaseIndex,
    DateTime? estimatedStart,
    DateTime? estimatedEnd,
    List<String>? entryCriteria,
    List<String>? exitCriteria,
    bool feedbackGateRequired = true,
    double? phaseWeight,
    String? objective,
  }) async {
    if (DemoDataService.isDemoMode) {
      final bundle = _demoPhaseStore[planId] ??
          PlanPhaseBundle(
            planCardId: 'demo_plan_card_$planId',
            currentPhaseCardId: null,
            progressMode: 'weighted_phase',
            weightedProgress: 0,
            phases: const [],
          );
      final phases = [...bundle.phases];
      final phase = PlanPhaseModel(
        cardId: 'demo_phase_${DateTime.now().millisecondsSinceEpoch}',
        title: name,
        phaseIndex: phaseIndex,
        lifecycleStatus: 'DRAFT',
        progress: 0,
        taskCount: 0,
        occurrenceCount: 0,
        completedOccurrenceCount: 0,
        objective: objective,
        estimatedStart: estimatedStart,
        estimatedEnd: estimatedEnd,
        entryCriteria: entryCriteria ?? const [],
        exitCriteria: exitCriteria ?? const [],
        feedbackGateRequired: feedbackGateRequired,
        phaseWeight: phaseWeight,
      );
      phases.add(phase);
      final sortedPhases = [...phases]
        ..sort((a, b) => a.phaseIndex.compareTo(b.phaseIndex));
      _demoPhaseStore[planId] = PlanPhaseBundle(
        planCardId: bundle.planCardId,
        currentPhaseCardId: bundle.currentPhaseCardId ?? phase.cardId,
        progressMode: 'weighted_phase',
        weightedProgress: bundle.weightedProgress,
        phases: sortedPhases,
      );
      return phase;
    }
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.planPhases(planId),
        data: {
          'name': name,
          'phase_index': phaseIndex,
          'estimated_start': estimatedStart?.toIso8601String(),
          'estimated_end': estimatedEnd?.toIso8601String(),
          'entry_criteria': entryCriteria,
          'exit_criteria': exitCriteria,
          'feedback_gate_required': feedbackGateRequired,
          'phase_weight': phaseWeight,
          'objective': objective,
        },
      );
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'createPhase');
      return PlanPhaseModel.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'createPhase');
    }
  }

  Future<void> activatePhase(String phaseCardId) async {
    if (DemoDataService.isDemoMode) return;
    try {
      await _apiClient.post<dynamic>(ApiEndpoints.activatePhase(phaseCardId));
    } on DioException catch (e) {
      return _handleDioError(e, 'activatePhase');
    }
  }

  Future<Map<String, dynamic>> completePhase(String phaseCardId) async {
    if (DemoDataService.isDemoMode) {
      return {'status': 'NEEDS_FEEDBACK'};
    }
    try {
      final response = await _apiClient
          .post<dynamic>(ApiEndpoints.completePhase(phaseCardId));
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'completePhase',
      );
    } on DioException catch (e) {
      return _handleDioError(e, 'completePhase');
    }
  }

  Future<Map<String, dynamic>> submitPhaseFeedback(
    String phaseCardId, {
    required double rating,
    String? reflection,
    bool blocked = false,
    bool lifeChanged = false,
    bool requestCompassReview = false,
  }) async {
    if (DemoDataService.isDemoMode) {
      return {'next_phase_activated': false};
    }
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.submitPhaseFeedback(phaseCardId),
        data: {
          'rating': rating,
          'reflection': reflection,
          'blocked': blocked,
          'life_changed': lifeChanged,
          'request_compass_review': requestCompassReview,
        },
      );
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'submitPhaseFeedback',
      );
    } on DioException catch (e) {
      return _handleDioError(e, 'submitPhaseFeedback');
    }
  }

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
        dayHighlights: plan.dayHighlights,
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
          dayHighlights: existing.dayHighlights,
          priority: existing.priority,
          planStage: existing.planStage,
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
          dayHighlights: existing.dayHighlights,
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
    String planId,
  ) async {
    if (DemoDataService.isDemoMode) {
      return LearningPathProgressModel(
        targetNode: LearningPathNodeProgress(
          id: 'demo_target',
          name: S.planTargetNode,
          status: 'unlocked',
          mastery: 45,
          isTarget: true,
        ),
        nodes: [
          LearningPathNodeProgress(
            id: 'demo_1',
            name: S.planMasteredNode,
            status: 'mastered',
            mastery: 92,
          ),
          LearningPathNodeProgress(
            id: 'demo_2',
            name: S.planLearningNode,
            status: 'unlocked',
            mastery: 45,
          ),
          LearningPathNodeProgress(
            id: 'demo_target',
            name: S.planTargetNode,
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
