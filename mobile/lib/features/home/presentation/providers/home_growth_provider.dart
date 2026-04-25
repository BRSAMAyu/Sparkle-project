import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/shared/entities/task_model.dart';

@immutable
class HomeActivePlanStatus {
  const HomeActivePlanStatus({
    required this.id,
    required this.name,
    required this.healthScore,
    this.currentPhase,
  });

  factory HomeActivePlanStatus.fromJson(Map<String, dynamic> json) {
    final planMap = _asStringKeyedMap(json['plan']) ??
        _asStringKeyedMap(json['active_plan']) ??
        json;

    return HomeActivePlanStatus(
      id: _asString(planMap['id'] ?? json['id']),
      name: _asString(
        planMap['name'] ?? planMap['title'] ?? json['name'] ?? json['title'],
        fallback: '当前计划',
      ),
      healthScore: _normalizeScore(
        _asDouble(
          json['health_score'] ??
              json['healthScore'] ??
              planMap['health_score'] ??
              planMap['healthScore'] ??
              planMap['mastery_level'] ??
              planMap['progress'],
        ),
      ),
      currentPhase: _asNullableString(
        json['current_phase'] ??
            json['currentPhase'] ??
            json['phase'] ??
            planMap['current_phase'] ??
            planMap['currentPhase'] ??
            planMap['phase'] ??
            planMap['plan_stage'],
      ),
    );
  }

  final String id;
  final String name;
  final double healthScore;
  final String? currentPhase;

  String get phaseLabel {
    final value = currentPhase?.trim();
    if (value == null || value.isEmpty) {
      return '进行中';
    }
    if (value.toLowerCase().startsWith('phase')) {
      return value;
    }
    return 'Phase 1: $value';
  }
}

@immutable
class HomeGrowthTask {
  const HomeGrowthTask({
    required this.id,
    required this.title,
    required this.priority,
    required this.isCompleted,
    this.dueDate,
    this.planId,
    this.knowledgeNodeId,
    this.tags = const [],
    this.taskModel,
  });

  factory HomeGrowthTask.fromJson(Map<String, dynamic> json) {
    TaskModel? taskModel;
    try {
      taskModel = TaskModel.fromJson(json);
    } catch (_) {
      taskModel = null;
    }

    final status = _asString(json['status']).toLowerCase();
    final completed = _asBool(
      json['completed'] ?? json['is_completed'],
      fallback: status == 'completed' ||
          status == 'complete' ||
          status == 'done' ||
          status == 'finished' ||
          status == 'completed_successfully',
    );

    return HomeGrowthTask(
      id: _asString(json['id'] ?? json['task_id']),
      title: _asString(json['title'] ?? json['name'], fallback: '未命名任务'),
      priority: _asInt(json['priority']),
      isCompleted: completed,
      dueDate: _asDateTime(json['due_date'] ?? json['dueDate']),
      planId: _asNullableString(json['plan_id'] ?? json['planId']),
      knowledgeNodeId: _asNullableString(
        json['knowledge_node_id'] ?? json['knowledgeNodeId'],
      ),
      tags: _asStringList(json['tags']),
      taskModel: taskModel,
    );
  }

  final String id;
  final String title;
  final int priority;
  final bool isCompleted;
  final DateTime? dueDate;
  final String? planId;
  final String? knowledgeNodeId;
  final List<String> tags;
  final TaskModel? taskModel;

  bool get isHighPriority => priority >= 4;

  bool relatesTo(HomeBottleneck bottleneck) {
    if (bottleneck.relatedTaskIds.contains(id)) {
      return true;
    }
    if (knowledgeNodeId != null &&
        knowledgeNodeId == bottleneck.knowledgeNodeId) {
      return true;
    }

    final topic = bottleneck.topic.trim().toLowerCase();
    if (topic.isEmpty) {
      return false;
    }
    final searchable = [
      title,
      ...tags,
    ].join(' ').toLowerCase();
    return searchable.contains(topic);
  }
}

@immutable
class HomeBottleneck {
  const HomeBottleneck({
    required this.id,
    required this.topic,
    required this.severity,
    this.knowledgeNodeId,
    this.relatedTaskIds = const [],
  });

  factory HomeBottleneck.fromJson(Map<String, dynamic> json) => HomeBottleneck(
        id: _asString(json['id'] ?? json['bottleneck_id']),
        topic: _asString(
          json['knowledge_point'] ??
              json['topic'] ??
              json['concept'] ??
              json['name'] ??
              json['title'],
          fallback: '这个知识点',
        ),
        severity: _asString(json['severity'], fallback: 'medium')
            .trim()
            .toLowerCase(),
        knowledgeNodeId: _asNullableString(
          json['knowledge_node_id'] ?? json['knowledgeNodeId'],
        ),
        relatedTaskIds: _asStringList(
          json['related_task_ids'] ??
              json['relatedTaskIds'] ??
              json['task_ids'],
        ),
      );

  final String id;
  final String topic;
  final String severity;
  final String? knowledgeNodeId;
  final List<String> relatedTaskIds;

  bool get isHighSeverity => severity == 'high';
}

@immutable
class HomeTodayTasksSnapshot {
  const HomeTodayTasksSnapshot({
    required this.tasks,
    required this.total,
    required this.completed,
  });

  const HomeTodayTasksSnapshot.empty()
      : tasks = const [],
        total = 0,
        completed = 0;

  factory HomeTodayTasksSnapshot.fromResponse(dynamic response) {
    final map = _unwrapOptionalMap(response);
    final items = _extractList(
      response,
      keys: const ['tasks', 'items', 'today_tasks', 'todayTasks'],
    );
    final tasks = items
        .map(_asStringKeyedMap)
        .whereType<Map<String, dynamic>>()
        .map(HomeGrowthTask.fromJson)
        .toList(growable: false);

    final total = _asInt(
      map?['total'] ??
          map?['tasks_total'] ??
          map?['total_tasks'] ??
          map?['tasksTotal'],
      fallback: tasks.length,
    );
    final completed = _asInt(
      map?['completed'] ??
          map?['completed_tasks'] ??
          map?['tasks_completed'] ??
          map?['completedTasks'],
      fallback: tasks.where((task) => task.isCompleted).length,
    );

    return HomeTodayTasksSnapshot(
      tasks: tasks,
      total: total,
      completed: completed,
    );
  }

  final List<HomeGrowthTask> tasks;
  final int total;
  final int completed;
}

@immutable
class HomeDailyContextLine {
  const HomeDailyContextLine({
    required this.text,
    required this.source,
    required this.date,
    this.generatedAt,
  });

  factory HomeDailyContextLine.fallback() {
    final now = DateTime.now();
    return HomeDailyContextLine(
      text: '早上好，今天先从一小步开始，把节奏找回来就很好。',
      source: 'local_rule',
      date: _dateKey(now),
      generatedAt: now,
    );
  }

  factory HomeDailyContextLine.fromJson(Map<String, dynamic> json) {
    final text = _asString(json['text']);
    if (text.isEmpty) {
      return HomeDailyContextLine.fallback();
    }
    final now = DateTime.now();
    return HomeDailyContextLine(
      text: text,
      source: _asString(json['source'], fallback: 'rule'),
      date: _asString(json['date'], fallback: _dateKey(now)),
      generatedAt: _asDateTime(json['generated_at'] ?? json['generatedAt']),
    );
  }

  final String text;
  final String source;
  final String date;
  final DateTime? generatedAt;
}

@immutable
class HomeGrowthState {
  const HomeGrowthState({
    required this.planHealth,
    required this.tasksTotal,
    required this.tasksCompleted,
    required this.streak,
    this.activePlan,
    this.activeBottleneck,
    this.nextAction,
    this.currentPhase,
  });

  const HomeGrowthState.empty()
      : planHealth = 0,
        tasksTotal = 0,
        tasksCompleted = 0,
        streak = 0,
        activePlan = null,
        activeBottleneck = null,
        nextAction = null,
        currentPhase = null;

  final HomeActivePlanStatus? activePlan;
  final double planHealth;
  final int tasksTotal;
  final int tasksCompleted;
  final int streak;
  final HomeBottleneck? activeBottleneck;
  final HomeGrowthTask? nextAction;
  final String? currentPhase;

  bool get hasActivePlan => activePlan != null;
  bool get hasTasks => tasksTotal > 0;
  double get completionRate => tasksTotal <= 0
      ? 0
      : (tasksCompleted / tasksTotal).clamp(0, 1).toDouble();
}

final homeGrowthDashboardSnapshotProvider =
    FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  try {
    final response = await apiClient.get<dynamic>('/growth/dashboard');
    return _unwrapOptionalMap(response.data) ?? <String, dynamic>{};
  } on DioException catch (e) {
    debugPrint('Home growth dashboard unavailable: ${e.message}');
    return <String, dynamic>{};
  }
});

final homeDailyContextLineProvider =
    FutureProvider.autoDispose<HomeDailyContextLine>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  try {
    final response = await apiClient.get<dynamic>('/growth/daily-context-line');
    final payload = _unwrapOptionalMap(response.data);
    if (payload == null || payload.isEmpty) {
      return HomeDailyContextLine.fallback();
    }
    return HomeDailyContextLine.fromJson(payload);
  } on DioException catch (e) {
    debugPrint('Home daily context line unavailable: ${e.message}');
    return HomeDailyContextLine.fallback();
  }
});

final homeActivePlanStatusProvider =
    FutureProvider.autoDispose<HomeActivePlanStatus?>((ref) async {
  final growthDashboard =
      await ref.watch(homeGrowthDashboardSnapshotProvider.future);
  final activePlanMap =
      _asStringKeyedMap(growthDashboard['active_plan_progress']);
  if (activePlanMap != null && activePlanMap.isNotEmpty) {
    return HomeActivePlanStatus.fromJson(activePlanMap);
  }

  final apiClient = ref.watch(apiClientProvider);
  try {
    final response = await apiClient.get<dynamic>('/plans/active');
    if (response.statusCode == 204) {
      return null;
    }
    final payload = _unwrapOptionalMap(response.data);
    if (payload == null || payload.isEmpty) {
      return null;
    }
    return HomeActivePlanStatus.fromJson(payload);
  } on DioException catch (e) {
    debugPrint('Home active plan unavailable: ${e.message}');
    return null;
  }
});

final homeTodayTasksSnapshotProvider =
    FutureProvider.autoDispose<HomeTodayTasksSnapshot>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  try {
    final response = await apiClient.get<dynamic>('/tasks/today');
    return HomeTodayTasksSnapshot.fromResponse(response.data);
  } on DioException catch (e) {
    debugPrint('Home today tasks unavailable: ${e.message}');
    return const HomeTodayTasksSnapshot.empty();
  }
});

final homeStreakProvider = FutureProvider.autoDispose<int>((ref) async {
  final growthDashboard =
      await ref.watch(homeGrowthDashboardSnapshotProvider.future);
  final growthStatusMap = _asStringKeyedMap(growthDashboard['growth_status']);
  final dashboardStreak = _asInt(growthStatusMap?['streak_days']);
  if (dashboardStreak > 0) {
    return dashboardStreak;
  }

  final apiClient = ref.watch(apiClientProvider);
  try {
    final response = await apiClient.get<dynamic>('/achievements/streak');
    final data = response.data;
    if (data is num) {
      return data.toInt();
    }
    final payload = _unwrapOptionalMap(data);
    return _asInt(
      payload?['streak'] ??
          payload?['days'] ??
          payload?['current_streak'] ??
          payload?['streak_days'],
    );
  } on DioException catch (e) {
    debugPrint('Home streak unavailable: ${e.message}');
    return 0;
  }
});

final homePlanBottlenecksProvider =
    FutureProvider.autoDispose<List<HomeBottleneck>>((ref) async {
  final growthDashboard =
      await ref.watch(homeGrowthDashboardSnapshotProvider.future);
  final activeBottleneckMap =
      _asStringKeyedMap(growthDashboard['active_bottleneck']);
  if (activeBottleneckMap != null && activeBottleneckMap.isNotEmpty) {
    return [HomeBottleneck.fromJson(activeBottleneckMap)];
  }

  final plan = await ref.watch(homeActivePlanStatusProvider.future);
  if (plan == null || plan.id.isEmpty) {
    return const [];
  }

  final apiClient = ref.watch(apiClientProvider);
  try {
    final response = await apiClient.get<dynamic>(
      '/plans/${plan.id}/bottlenecks',
    );
    return _extractList(
      response.data,
      keys: const ['bottlenecks', 'items'],
    )
        .map(_asStringKeyedMap)
        .whereType<Map<String, dynamic>>()
        .map(HomeBottleneck.fromJson)
        .toList(growable: false);
  } on DioException catch (e) {
    debugPrint('Home bottlenecks unavailable: ${e.message}');
    return const [];
  }
});

final homeGrowthStateProvider =
    FutureProvider.autoDispose<HomeGrowthState>((ref) async {
  final planStatus = await ref.watch(homeActivePlanStatusProvider.future);
  final todayTasks = await ref.watch(homeTodayTasksSnapshotProvider.future);
  final streak = await ref.watch(homeStreakProvider.future);
  final bottlenecks = await ref.watch(homePlanBottlenecksProvider.future);

  final activeBottleneck = _firstOrNull(
    bottlenecks.where((bottleneck) => bottleneck.isHighSeverity),
  );

  return HomeGrowthState(
    activePlan: planStatus,
    planHealth: planStatus?.healthScore ?? 0,
    tasksTotal: todayTasks.total,
    tasksCompleted: todayTasks.completed,
    streak: streak,
    activeBottleneck: activeBottleneck,
    nextAction: _selectNextAction(todayTasks.tasks, activeBottleneck),
    currentPhase: planStatus?.currentPhase,
  );
});

HomeGrowthTask? _selectNextAction(
  List<HomeGrowthTask> tasks,
  HomeBottleneck? bottleneck,
) {
  final openTasks = tasks.where((task) => !task.isCompleted).toList();
  if (openTasks.isEmpty) {
    return null;
  }

  final highPriorityTasks = openTasks
      .where((task) => task.isHighPriority)
      .toList()
    ..sort(_comparePriorityThenDueDate);
  if (highPriorityTasks.isNotEmpty) {
    return highPriorityTasks.first;
  }

  if (bottleneck != null) {
    final relatedTasks = openTasks
        .where((task) => task.relatesTo(bottleneck))
        .toList()
      ..sort(_comparePriorityThenDueDate);
    if (relatedTasks.isNotEmpty) {
      return relatedTasks.first;
    }
  }

  openTasks.sort(_compareDueDateThenPriority);
  return openTasks.first;
}

int _comparePriorityThenDueDate(HomeGrowthTask a, HomeGrowthTask b) {
  final priorityCompare = b.priority.compareTo(a.priority);
  if (priorityCompare != 0) {
    return priorityCompare;
  }
  return _compareDueDateThenPriority(a, b);
}

int _compareDueDateThenPriority(HomeGrowthTask a, HomeGrowthTask b) {
  final aDue = a.dueDate;
  final bDue = b.dueDate;
  if (aDue == null && bDue == null) {
    return b.priority.compareTo(a.priority);
  }
  if (aDue == null) {
    return 1;
  }
  if (bDue == null) {
    return -1;
  }
  final dueCompare = aDue.compareTo(bDue);
  if (dueCompare != 0) {
    return dueCompare;
  }
  return b.priority.compareTo(a.priority);
}

T? _firstOrNull<T>(Iterable<T> values) {
  final iterator = values.iterator;
  if (!iterator.moveNext()) {
    return null;
  }
  return iterator.current;
}

Map<String, dynamic>? _unwrapOptionalMap(dynamic value) {
  if (value == null) {
    return null;
  }
  final map = _asStringKeyedMap(value);
  if (map == null) {
    return null;
  }
  if (map.containsKey('data')) {
    final data = map['data'];
    if (data == null) {
      return null;
    }
    return _asStringKeyedMap(data) ?? map;
  }
  return map;
}

List<dynamic> _extractList(
  dynamic value, {
  required List<String> keys,
}) {
  if (value is List) {
    return value;
  }

  final directMap = _asStringKeyedMap(value);
  final directData = directMap?['data'];
  if (directData is List) {
    return directData;
  }

  final map = _unwrapOptionalMap(value);
  if (map == null) {
    return const [];
  }

  for (final key in keys) {
    final nested = map[key];
    if (nested is List) {
      return nested;
    }
  }

  return const [];
}

Map<String, dynamic>? _asStringKeyedMap(dynamic value) {
  if (value is Map<String, dynamic>) {
    return value;
  }
  if (value is Map) {
    try {
      return Map<String, dynamic>.from(value);
    } catch (_) {
      return null;
    }
  }
  return null;
}

String _asString(dynamic value, {String fallback = ''}) {
  final text = value?.toString().trim();
  if (text == null || text.isEmpty) {
    return fallback;
  }
  return text;
}

String? _asNullableString(dynamic value) {
  final text = _asString(value);
  return text.isEmpty ? null : text;
}

List<String> _asStringList(dynamic value) {
  if (value is! List) {
    return const [];
  }
  return value
      .map((item) => item.toString().trim())
      .where((item) => item.isNotEmpty)
      .toList(growable: false);
}

int _asInt(dynamic value, {int fallback = 0}) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value) ?? fallback;
  }
  return fallback;
}

double _asDouble(dynamic value, {double fallback = 0}) {
  if (value is double) {
    return value;
  }
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value) ?? fallback;
  }
  return fallback;
}

bool _asBool(dynamic value, {bool fallback = false}) {
  if (value is bool) {
    return value;
  }
  if (value is num) {
    return value != 0;
  }
  if (value is String) {
    switch (value.trim().toLowerCase()) {
      case 'true':
      case '1':
      case 'yes':
      case 'y':
      case 'completed':
      case 'done':
        return true;
      case 'false':
      case '0':
      case 'no':
      case 'n':
      case 'pending':
        return false;
    }
  }
  return fallback;
}

DateTime? _asDateTime(dynamic value) {
  if (value is DateTime) {
    return value;
  }
  if (value is String && value.trim().isNotEmpty) {
    return DateTime.tryParse(value.trim());
  }
  return null;
}

String _dateKey(DateTime value) => '${value.year.toString().padLeft(4, '0')}-'
    '${value.month.toString().padLeft(2, '0')}-'
    '${value.day.toString().padLeft(2, '0')}';

double _normalizeScore(double value) {
  if (value <= 0) {
    return 0;
  }
  if (value > 1) {
    return (value / 100).clamp(0, 1).toDouble();
  }
  return value.clamp(0, 1).toDouble();
}
