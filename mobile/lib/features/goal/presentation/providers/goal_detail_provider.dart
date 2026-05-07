import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/cognitive/data/models/strategy_migration_models.dart';
import 'package:sparkle/features/goal/data/repositories/goal_repository.dart';

final goalDetailProvider = StateNotifierProvider.family<GoalDetailNotifier,
    AsyncValue<GoalDetailData>, String>(
  (ref, goalId) {
    final notifier = GoalDetailNotifier(ref, goalId);
    unawaited(notifier.load());
    return notifier;
  },
);

class GoalDetailNotifier extends StateNotifier<AsyncValue<GoalDetailData>> {
  GoalDetailNotifier(this._ref, this._goalId)
      : super(const AsyncValue.loading());

  final Ref _ref;
  final String _goalId;

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final response = await _ref.read(apiClientProvider).get<dynamic>(
            '/experience/goal-detail/$_goalId',
          );
      final payload = _asMap(response.data);
      if (payload == null) {
        throw const FormatException('Goal detail response was not a map');
      }
      state = AsyncValue.data(GoalDetailData.fromJson(payload));
    } on DioException catch (error, stackTrace) {
      debugPrint('GoalDetail: load failed: ${error.message}');
      state = AsyncValue.error(error, stackTrace);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  Future<void> startNextStep() async {
    final taskId = state.valueOrNull?.todaysMinimalNextStep.taskId;
    if (taskId == null || taskId.isEmpty) return;
    try {
      await _ref.read(apiClientProvider).post<dynamic>('/tasks/$taskId/start');
      unawaited(load());
    } catch (e) {
      rethrow;
    }
  }

  Future<void> undoStartNextStep() async {
    final taskId = state.valueOrNull?.todaysMinimalNextStep.taskId;
    if (taskId == null || taskId.isEmpty) return;
    try {
      await _ref.read(apiClientProvider).post<dynamic>('/tasks/$taskId/pause');
      unawaited(load());
    } catch (e) {
      rethrow;
    }
  }

  Future<void> completeNextStep() async {
    final taskId = state.valueOrNull?.todaysMinimalNextStep.taskId;
    if (taskId == null || taskId.isEmpty) return;
    try {
      await _ref.read(apiClientProvider).post<dynamic>('/tasks/$taskId/complete');
      unawaited(load());
    } catch (e) {
      rethrow;
    }
  }

  Future<void> confirmMinimumCriteria() async {
    final value = state.valueOrNull;
    if (value == null) return;
    await _ref.read(apiClientProvider).put<dynamic>(
      '/experience/goal-detail/$_goalId/criteria-status',
      data: {'status': 'confirmed'},
    );
    state = AsyncValue.data(
      value.copyWith(
        minimumAcceptanceCriteria:
            value.minimumAcceptanceCriteria.copyWith(status: 'confirmed'),
      ),
    );
  }

  Future<void> undoConfirmMinimumCriteria() async {
    final value = state.valueOrNull;
    if (value == null) return;
    await _ref.read(apiClientProvider).put<dynamic>(
      '/experience/goal-detail/$_goalId/criteria-status',
      data: {'status': 'pending_confirmation'},
    );
    state = AsyncValue.data(
      value.copyWith(
        minimumAcceptanceCriteria: value.minimumAcceptanceCriteria
            .copyWith(status: 'pending_confirmation'),
      ),
    );
  }

  Future<void> updateGoal({
    String? title,
    String? description,
  }) async {
    await _ref.read(goalRepositoryProvider).updateGoal(
      goalId: _goalId,
      title: title,
      description: description,
    );
    await load();
  }
}

@immutable
class GoalDetailData {
  const GoalDetailData({
    required this.goal,
    required this.minimumAcceptanceCriteria,
    required this.planHealth,
    required this.currentPhase,
    required this.todaysMinimalNextStep,
    required this.knowledgeBottlenecks,
    required this.accountabilityStatus,
    required this.relatedSources,
    this.strategyBelief,
  });

  factory GoalDetailData.fromJson(Map<String, dynamic> json) => GoalDetailData(
        goal: GoalSummary.fromJson(_asMap(json['goal']) ?? const {}),
        minimumAcceptanceCriteria: MinimumAcceptanceCriteria.fromJson(
          _asMap(json['minimum_acceptance_criteria']) ?? const {},
        ),
        planHealth: PlanHealth.fromJson(
          _asMap(json['plan_health']) ?? const {},
        ),
        currentPhase: CurrentPhase.fromJson(
          _asMap(json['current_phase']) ?? const {},
        ),
        todaysMinimalNextStep: TodaysMinimalNextStep.fromJson(
          _asMap(json['todays_minimal_next_step']) ?? const {},
        ),
        knowledgeBottlenecks: _asList(json['knowledge_bottlenecks'])
            .map(_asMap)
            .whereType<Map<String, dynamic>>()
            .map(KnowledgeBottleneck.fromJson)
            .toList(growable: false),
        accountabilityStatus: AccountabilityStatusSummary.fromJson(
          _asMap(json['accountability_status']) ?? const {},
        ),
        relatedSources: _asList(json['related_sources'])
            .map(_asMap)
            .whereType<Map<String, dynamic>>()
            .map(RelatedSource.fromJson)
            .toList(growable: false),
        strategyBelief: _asMap(json['strategy_belief']) == null
            ? null
            : StrategyBeliefView.fromJson(_asMap(json['strategy_belief'])!),
      );

  final GoalSummary goal;
  final MinimumAcceptanceCriteria minimumAcceptanceCriteria;
  final PlanHealth planHealth;
  final CurrentPhase currentPhase;
  final TodaysMinimalNextStep todaysMinimalNextStep;
  final List<KnowledgeBottleneck> knowledgeBottlenecks;
  final AccountabilityStatusSummary accountabilityStatus;
  final List<RelatedSource> relatedSources;
  final StrategyBeliefView? strategyBelief;

  GoalDetailData copyWith({
    MinimumAcceptanceCriteria? minimumAcceptanceCriteria,
  }) =>
      GoalDetailData(
        goal: goal,
        minimumAcceptanceCriteria:
            minimumAcceptanceCriteria ?? this.minimumAcceptanceCriteria,
        planHealth: planHealth,
        currentPhase: currentPhase,
        todaysMinimalNextStep: todaysMinimalNextStep,
        knowledgeBottlenecks: knowledgeBottlenecks,
        accountabilityStatus: accountabilityStatus,
        relatedSources: relatedSources,
        strategyBelief: strategyBelief,
      );
}

@immutable
class GoalSummary {
  const GoalSummary({
    required this.id,
    required this.title,
    required this.goalType,
    required this.status,
    required this.mastery,
    required this.progress,
    required this.priority,
    this.targetDate,
  });

  factory GoalSummary.fromJson(Map<String, dynamic> json) => GoalSummary(
        id: _asString(json['id']),
        title: _asString(json['title']),
        goalType: _asString(json['goal_type']),
        status: _asString(json['status']),
        targetDate: _asNullableString(json['target_date']),
        mastery: _asRatio(json['mastery']),
        progress: _asRatio(json['progress']),
        priority: _asString(json['priority'], fallback: 'normal'),
      );

  final String id;
  final String title;
  final String goalType;
  final String status;
  final String? targetDate;
  final double mastery;
  final double progress;
  final String priority;
}

@immutable
class MinimumAcceptanceCriteria {
  const MinimumAcceptanceCriteria({
    required this.description,
    required this.status,
    required this.thresholds,
  });

  factory MinimumAcceptanceCriteria.fromJson(Map<String, dynamic> json) =>
      MinimumAcceptanceCriteria(
        description: _asString(json['description']),
        status: _asString(
          json['status'],
          fallback: 'pending_confirmation',
        ),
        thresholds: _asList(json['thresholds'])
            .map(_asMap)
            .whereType<Map<String, dynamic>>()
            .map(CriteriaThreshold.fromJson)
            .toList(growable: false),
      );

  final String description;
  final String status;
  final List<CriteriaThreshold> thresholds;

  bool get isConfirmed => status == 'confirmed';

  MinimumAcceptanceCriteria copyWith({String? status}) =>
      MinimumAcceptanceCriteria(
        description: description,
        status: status ?? this.status,
        thresholds: thresholds,
      );
}

@immutable
class CriteriaThreshold {
  const CriteriaThreshold({
    required this.id,
    required this.label,
    required this.met,
    this.metric,
    this.threshold,
    this.unit,
    this.currentValue,
  });

  factory CriteriaThreshold.fromJson(Map<String, dynamic> json) =>
      CriteriaThreshold(
        id: _asString(json['id']),
        label: _asString(json['label']),
        metric: _asNullableString(json['metric']),
        threshold: _asNullableString(json['threshold']),
        unit: _asNullableString(json['unit']),
        currentValue: _asNullableString(json['current_value']),
        met: json['met'] == true,
      );

  final String id;
  final String label;
  final String? metric;
  final String? threshold;
  final String? unit;
  final String? currentValue;
  final bool met;
}

@immutable
class PlanHealth {
  const PlanHealth({
    required this.overall,
    required this.phaseHealth,
    required this.taskCompletionRate,
  });

  factory PlanHealth.fromJson(Map<String, dynamic> json) => PlanHealth(
        overall: _asRatio(json['overall']),
        phaseHealth: _asRatio(json['phase_health']),
        taskCompletionRate: _asRatio(json['task_completion_rate']),
      );

  final double overall;
  final double phaseHealth;
  final double taskCompletionRate;
}

@immutable
class CurrentPhase {
  const CurrentPhase({
    required this.name,
    required this.progress,
  });

  factory CurrentPhase.fromJson(Map<String, dynamic> json) => CurrentPhase(
        name: _asString(json['name']),
        progress: _asRatio(json['progress']),
      );

  final String name;
  final double progress;
}

@immutable
class TodaysMinimalNextStep {
  const TodaysMinimalNextStep({
    this.taskId,
    this.title,
    this.type,
    this.estimatedMinutes,
  });

  factory TodaysMinimalNextStep.fromJson(Map<String, dynamic> json) =>
      TodaysMinimalNextStep(
        taskId: _asNullableString(json['task_id']),
        title: _asNullableString(json['title']),
        type: _asNullableString(json['type']),
        estimatedMinutes: _asInt(json['estimated_minutes']),
      );

  final String? taskId;
  final String? title;
  final String? type;
  final int? estimatedMinutes;

  bool get hasTask => taskId != null && title != null;
}

@immutable
class KnowledgeBottleneck {
  const KnowledgeBottleneck({
    required this.nodeId,
    required this.label,
    required this.mastery,
    required this.goalImpact,
  });

  factory KnowledgeBottleneck.fromJson(Map<String, dynamic> json) =>
      KnowledgeBottleneck(
        nodeId: _asString(json['node_id']),
        label: _asString(json['label']),
        mastery: _asRatio(json['mastery']),
        goalImpact: _asString(json['goal_impact']),
      );

  final String nodeId;
  final String label;
  final double mastery;
  final String goalImpact;
}

@immutable
class AccountabilityStatusSummary {
  const AccountabilityStatusSummary({
    required this.partnerCount,
    required this.activeCommitments,
    this.lastCheckin,
  });

  factory AccountabilityStatusSummary.fromJson(Map<String, dynamic> json) =>
      AccountabilityStatusSummary(
        partnerCount: _asInt(json['partner_count']) ?? 0,
        activeCommitments: _asInt(json['active_commitments']) ?? 0,
        lastCheckin: _asNullableString(json['last_checkin']),
      );

  final int partnerCount;
  final int activeCommitments;
  final String? lastCheckin;
}

@immutable
class RelatedSource {
  const RelatedSource({
    required this.id,
    required this.title,
    required this.type,
    required this.relevance,
  });

  factory RelatedSource.fromJson(Map<String, dynamic> json) => RelatedSource(
        id: _asString(json['id']),
        title: _asString(json['title']),
        type: _asString(json['type']),
        relevance: _asRatio(json['relevance']),
      );

  final String id;
  final String title;
  final String type;
  final double relevance;
}

Map<String, dynamic>? _asMap(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) return Map<String, dynamic>.from(value);
  return null;
}

List<dynamic> _asList(dynamic value) => value is List ? value : const [];

String _asString(dynamic value, {String fallback = ''}) {
  final text = value?.toString().trim();
  return text == null || text.isEmpty ? fallback : text;
}

String? _asNullableString(dynamic value) {
  final text = _asString(value);
  return text.isEmpty ? null : text;
}

int? _asInt(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value);
  return null;
}

double _asRatio(dynamic value) {
  double number;
  if (value is num) {
    number = value.toDouble();
  } else if (value is String) {
    number = double.tryParse(value) ?? 0;
  } else {
    number = 0;
  }
  if (number > 1) number = number / 100;
  return number.clamp(0, 1).toDouble();
}
