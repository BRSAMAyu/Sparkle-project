import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/providers/persistent_state_notifier.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';

class ActiveGoalNotifier extends PersistentNotifier<String?> {
  ActiveGoalNotifier(this._ref)
      : super(
          namespace: 'active_goal',
          key: 'current_goal_id',
          defaultValue: null,
          serializer: (s) => s,
          deserializer: (s) => (s == null || s.isEmpty) ? null : s,
        );

  final Ref _ref;

  Future<void> selectGoal(String? goalId, {bool syncRemote = true}) async {
    final normalized = _normalizeGoalId(goalId);
    state = normalized;
    await saveImmediate();
    if (!syncRemote) return;

    try {
      await _ref.read(userRepositoryProvider).updateUserSettings({
        'current_goal_id': normalized,
      });
    } catch (e) {
      debugPrint('ActiveGoal: failed to sync current_goal_id: $e');
    }
  }

  Future<void> clearSelection() => selectGoal(null);

  Future<void> hydrateFromRemote(String? goalId) async {
    final normalized = _normalizeGoalId(goalId);
    if (normalized == state) return;
    state = normalized;
    await saveImmediate();
  }
}

final activeGoalProvider = StateNotifierProvider<ActiveGoalNotifier, String?>(
  ActiveGoalNotifier.new,
);

final activeGoalHeaderProvider = Provider<String?>((ref) {
  final goalId = ref.watch(activeGoalProvider);
  return _normalizeGoalId(goalId);
});

@immutable
class ActiveGoalSnapshot {
  const ActiveGoalSnapshot({
    required this.id,
    required this.title,
    required this.goalType,
    required this.healthScore,
    required this.weeklyConflictCount,
    this.deadlineDays,
    this.currentPhase,
    this.timeFraction,
    this.priorityScore,
    this.conflictReasons = const [],
  });

  factory ActiveGoalSnapshot.fromSpine(
    Map<String, dynamic> json, {
    double? timeFraction,
    double? priorityScore,
    List<String> conflictReasons = const [],
  }) {
    final zh = I18nService.instance.isChinese;
    final deadlineDays = _asNullableInt(
      json['deadline_days'] ?? json['deadlineDays'],
    );
    final mastery = _normalizeScore(
      _asDouble(json['mastery'] ?? json['health_score'] ?? json['healthScore']),
    );
    final bottleneck = _normalizeScore(
      _asDouble(json['bottleneck_severity'] ?? json['bottleneckSeverity']),
    );
    final health = mastery > 0 ? mastery : (1 - bottleneck).clamp(0, 1);

    return ActiveGoalSnapshot(
      id: _asString(json['goal_id'] ?? json['id']),
      title: _asString(
        json['title'] ?? json['name'],
        fallback: zh ? '未命名目标' : 'Untitled goal',
      ),
      goalType: _asString(json['goal_type'] ?? json['type'], fallback: 'goal'),
      deadlineDays: deadlineDays,
      currentPhase: _asNullableString(
        json['current_phase'] ?? json['phase'] ?? json['plan_stage'],
      ),
      healthScore: health.toDouble(),
      weeklyConflictCount: conflictReasons.length,
      timeFraction: timeFraction,
      priorityScore: priorityScore,
      conflictReasons: conflictReasons,
    );
  }

  factory ActiveGoalSnapshot.fromPlan(
    PlanModel plan, {
    double? timeFraction,
    double? priorityScore,
    List<String> conflictReasons = const [],
  }) =>
      ActiveGoalSnapshot(
        id: plan.id,
        title: plan.name,
        goalType: plan.type.name,
        deadlineDays: _daysUntil(plan.targetDate),
        currentPhase: _planStageLabel(plan.planStage),
        healthScore: _normalizeScore(plan.healthScore ?? plan.progress),
        weeklyConflictCount: conflictReasons.length,
        timeFraction: timeFraction,
        priorityScore: priorityScore,
        conflictReasons: conflictReasons,
      );

  final String id;
  final String title;
  final String goalType;
  final int? deadlineDays;
  final String? currentPhase;
  final double healthScore;
  final int weeklyConflictCount;
  final double? timeFraction;
  final double? priorityScore;
  final List<String> conflictReasons;
}

@immutable
class GoalArbitrationSuggestion {
  const GoalArbitrationSuggestion({
    required this.primaryGoalId,
    required this.primaryGoalTitle,
    required this.rationale,
    this.conflicts = const [],
  });

  final String primaryGoalId;
  final String primaryGoalTitle;
  final String rationale;
  final List<String> conflicts;

  bool get hasConflict => conflicts.isNotEmpty;
}

@immutable
class MultiGoalOverview {
  const MultiGoalOverview({
    required this.goals,
    required this.selectedGoalId,
    this.suggestion,
    this.usingPlanFallback = false,
  });

  const MultiGoalOverview.empty()
      : goals = const [],
        selectedGoalId = null,
        suggestion = null,
        usingPlanFallback = false;

  final List<ActiveGoalSnapshot> goals;
  final String? selectedGoalId;
  final GoalArbitrationSuggestion? suggestion;
  final bool usingPlanFallback;

  ActiveGoalSnapshot? get selectedGoal =>
      _firstWhereOrNull(goals, (goal) => goal.id == selectedGoalId) ??
      (goals.isEmpty ? null : goals.first);
}

final multiGoalOverviewProvider =
    FutureProvider<MultiGoalOverview>((ref) async {
  final localSelectedGoalId = ref.watch(activeGoalProvider);
  final remoteSelectedGoalId = await _fetchRemoteCurrentGoalId(ref);
  if (remoteSelectedGoalId != null &&
      remoteSelectedGoalId != localSelectedGoalId) {
    await ref
        .read(activeGoalProvider.notifier)
        .hydrateFromRemote(remoteSelectedGoalId);
  }

  final selectedGoalId = remoteSelectedGoalId ?? localSelectedGoalId;
  final spinePayload = await _fetchSpineGoals(ref);
  final planGoals = await _fetchPlanGoals(ref);
  final arbitration = _asStringKeyedMap(spinePayload?['arbitration']);
  final conflicts = _asStringList(arbitration?['conflicts']);
  final primaryGoalId = _asNullableString(
    arbitration?['primary_goal_id'] ?? arbitration?['primaryGoalId'],
  );
  final timeSplit = _asDoubleMap(
    arbitration?['time_split'] ??
        arbitration?['suggested_time_split'] ??
        arbitration?['suggestedTimeSplit'],
  );
  final priorityScores = _asDoubleMap(
    arbitration?['priority_scores'] ?? arbitration?['priorityScores'],
  );

  final byId = <String, ActiveGoalSnapshot>{};
  final spineItems = _extractList(spinePayload?['goals']);
  for (final item in spineItems) {
    final map = _asStringKeyedMap(item);
    if (map == null) continue;
    final id = _asString(map['goal_id'] ?? map['id']);
    if (id.isEmpty) continue;
    byId[id] = ActiveGoalSnapshot.fromSpine(
      map,
      timeFraction: timeSplit[id],
      priorityScore: priorityScores[id],
      conflictReasons: _goalConflicts(id, primaryGoalId, conflicts),
    );
  }

  for (final plan in planGoals) {
    byId.putIfAbsent(
      plan.id,
      () => ActiveGoalSnapshot.fromPlan(
        plan,
        timeFraction: timeSplit[plan.id],
        priorityScore: priorityScores[plan.id],
        conflictReasons: _goalConflicts(plan.id, primaryGoalId, conflicts),
      ),
    );
  }

  final goals = byId.values.toList(growable: false)
    ..sort((a, b) {
      final scoreCompare =
          (b.priorityScore ?? 0).compareTo(a.priorityScore ?? 0);
      if (scoreCompare != 0) return scoreCompare;
      final deadlineA = a.deadlineDays ?? 9999;
      final deadlineB = b.deadlineDays ?? 9999;
      return deadlineA.compareTo(deadlineB);
    });

  final resolvedSelectedGoalId = _normalizeGoalId(selectedGoalId) ??
      primaryGoalId ??
      (goals.isEmpty ? null : goals.first.id);
  if (resolvedSelectedGoalId != null &&
      resolvedSelectedGoalId != localSelectedGoalId) {
    unawaited(
      ref.read(activeGoalProvider.notifier).selectGoal(resolvedSelectedGoalId),
    );
  }

  final primaryGoal = _firstWhereOrNull(
    goals,
    (goal) => goal.id == primaryGoalId,
  );
  final suggestion = primaryGoalId == null
      ? null
      : GoalArbitrationSuggestion(
          primaryGoalId: primaryGoalId,
          primaryGoalTitle: primaryGoal?.title ?? primaryGoalId,
          rationale: _buildRationale(arbitration, primaryGoal?.title),
          conflicts: conflicts,
        );

  return MultiGoalOverview(
    goals: goals,
    selectedGoalId: resolvedSelectedGoalId,
    suggestion: suggestion,
    usingPlanFallback: spineItems.isEmpty && goals.isNotEmpty,
  );
});

Future<String?> _fetchRemoteCurrentGoalId(Ref ref) async {
  try {
    final settings = await ref.read(userRepositoryProvider).fetchUserSettings();
    return _normalizeGoalId(settings['current_goal_id']?.toString());
  } catch (e) {
    debugPrint('ActiveGoal: user settings unavailable: $e');
    return null;
  }
}

Future<Map<String, dynamic>?> _fetchSpineGoals(Ref ref) async {
  try {
    final response = await ref.read(apiClientProvider).get<dynamic>(
          '/aurora/spine/goals',
        );
    return _asStringKeyedMap(response.data);
  } on DioException catch (e) {
    debugPrint('ActiveGoal: spine goals unavailable: ${e.message}');
    return null;
  } catch (e) {
    debugPrint('ActiveGoal: spine goals parse failed: $e');
    return null;
  }
}

Future<List<PlanModel>> _fetchPlanGoals(Ref ref) async {
  try {
    return await ref.read(planRepositoryProvider).getActivePlans();
  } catch (e) {
    debugPrint('ActiveGoal: active plans unavailable: $e');
    return const [];
  }
}

List<String> _goalConflicts(
  String goalId,
  String? primaryGoalId,
  List<String> conflicts,
) {
  if (conflicts.isEmpty) return const [];
  if (primaryGoalId == null || primaryGoalId == goalId) return conflicts;
  return const [];
}

String _buildRationale(Map<String, dynamic>? arbitration, String? title) {
  final zh = I18nService.instance.isChinese;
  final raw = _asNullableString(
    arbitration?['rationale'] ?? arbitration?['reason'],
  );
  if (raw != null && raw != 'single_active_goal') {
    return raw;
  }
  if (title != null && title.trim().isNotEmpty) {
    return zh
        ? '今天我建议先做 $title，因为它的优先级和时间窗口最紧。'
        : 'I suggest starting with $title today because its priority and timing are strongest.';
  }
  return zh
      ? '今天我建议先处理系统排在最前的目标。'
      : 'I suggest starting with the highest ranked goal today.';
}

String? _normalizeGoalId(String? value) {
  final text = value?.trim();
  return text == null || text.isEmpty ? null : text;
}

Map<String, dynamic>? _asStringKeyedMap(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) {
    try {
      return Map<String, dynamic>.from(value);
    } catch (_) {
      return null;
    }
  }
  return null;
}

List<dynamic> _extractList(dynamic value) {
  if (value is List) return value;
  final map = _asStringKeyedMap(value);
  final data = map?['data'];
  if (data is List) return data;
  final goals = map?['goals'];
  if (goals is List) return goals;
  return const [];
}

Map<String, double> _asDoubleMap(dynamic value) {
  final map = _asStringKeyedMap(value);
  if (map == null) return const {};
  return {
    for (final entry in map.entries) entry.key: _asDouble(entry.value),
  };
}

String _asString(dynamic value, {String fallback = ''}) {
  final text = value?.toString().trim();
  return text == null || text.isEmpty ? fallback : text;
}

String? _asNullableString(dynamic value) {
  final text = _asString(value);
  return text.isEmpty ? null : text;
}

List<String> _asStringList(dynamic value) {
  if (value is! List) return const [];
  return value
      .map((item) => item.toString().trim())
      .where((item) => item.isNotEmpty)
      .toList(growable: false);
}

int? _asNullableInt(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value);
  return null;
}

double _asDouble(dynamic value, {double fallback = 0}) {
  if (value is double) return value;
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value) ?? fallback;
  return fallback;
}

double _normalizeScore(double value) {
  if (value <= 0) return 0;
  if (value > 1) return (value / 100).clamp(0, 1).toDouble();
  return value.clamp(0, 1).toDouble();
}

int? _daysUntil(DateTime? value) {
  if (value == null) return null;
  final today = DateTime.now();
  final todayDate = DateTime(today.year, today.month, today.day);
  final targetDate = DateTime(value.year, value.month, value.day);
  return targetDate.difference(todayDate).inDays;
}

String _planStageLabel(PlanStage stage) {
  final zh = I18nService.instance.isChinese;
  return switch (stage) {
    PlanStage.sprint => zh ? '冲刺阶段' : 'Sprint',
    PlanStage.daily => zh ? '日常推进' : 'Daily',
    PlanStage.review => zh ? '复盘阶段' : 'Review',
    PlanStage.paused => zh ? '已暂停' : 'Paused',
  };
}

T? _firstWhereOrNull<T>(Iterable<T> items, bool Function(T) test) {
  for (final item in items) {
    if (test(item)) return item;
  }
  return null;
}
