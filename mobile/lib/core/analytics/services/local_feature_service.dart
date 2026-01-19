import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/services/app_usage_service.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';

final localFeatureServiceProvider = Provider<LocalFeatureService>((ref) {
  final db = ref.watch(localDatabaseProvider);
  final appUsage = ref.watch(appUsageServiceProvider);
  final service = LocalFeatureService(db.isar, appUsage);
  ref.onDispose(service.dispose);
  return service;
});

typedef InterventionTriggerCallback = void Function(
  String trigger,
  Map<String, dynamic> context,
);

class LocalFeatureService {

  LocalFeatureService(this._isar, this._appUsageService);
  final Isar _isar;
  final AppUsageService _appUsageService;

  Timer? _taskStuckTimer;
  StreamSubscription<AppUsageEvent>? _usageSubscription;
  final List<DateTime> _switchEvents = [];

  /// Aggregates local events into a feature vector for Qwen3-0.6B.
  Future<Map<String, dynamic>> buildFeatureVector() async {
    final now = DateTime.now();
    final todayStart = DateTime(now.year, now.month, now.day);
    final lastHour = now.subtract(const Duration(hours: 1));

    // 1. Task Progress (Fast count queries)
    final totalTasks = await _isar.localKnowledgeNodes.count();
    final highMasteryNodes = await _isar.localKnowledgeNodes
        .filter()
        .masteryGreaterThan(80)
        .count();

    // 2. Recent Behavior (Last Hour)
    // OPTIMIZATION: Limit to 500 events to prevent OOM/Jank
    final recentEvents = await _isar.userAnalyticsEvents
        .filter()
        .timestampGreaterThan(lastHour)
        .sortByTimestampDesc()
        .limit(500) 
        .findAll();

    final taskCompletions = recentEvents.where((e) => e.eventType == 'task_completed').length;
    final focusStarts = recentEvents.where((e) => e.eventType == 'focus_start').length;
    final focusAborts = recentEvents.where((e) => e.eventType == 'focus_abort').length;

    // 3. Daily Stats (Simplified count)
    final dailyEventsCount = await _isar.userAnalyticsEvents
        .filter()
        .timestampGreaterThan(todayStart)
        .count();

    // 4. Construct the Vector
    return {
      'time': {
        'hour': now.hour,
        'weekday': now.weekday,
      },
      'stats_24h': {
        'events': dailyEventsCount,
        'knowledge_nodes': totalTasks,
        'mastered_nodes': highMasteryNodes,
      },
      'recent_1h': {
        'tasks_done': taskCompletions,
        'focus_attempts': focusStarts,
        'focus_aborts': focusAborts,
        'interaction_density': recentEvents.length,
      },
      'device': {
        'is_low_power': false, 
      },
    };
  }

  /// Helper to record a new event manually (to be used by other features)
  Future<void> logEvent(String type, {Map<String, dynamic>? metadata}) async {
    final event = UserAnalyticsEvent()
      ..eventType = type
      ..timestamp = DateTime.now();
    
    await _isar.writeTxn(() async {
      await _isar.userAnalyticsEvents.put(event);
    });
  }

  void startInterventionTriggers({
    required InterventionTriggerCallback onTrigger,
    Duration taskStuckInterval = const Duration(minutes: 10),
  }) {
    _appUsageService.startMonitoring();
    _taskStuckTimer?.cancel();
    _taskStuckTimer = Timer.periodic(taskStuckInterval, (_) async {
      final now = DateTime.now();
      final tenMinutesAgo = now.subtract(const Duration(minutes: 10));
      final recentEvents = await _isar.userAnalyticsEvents
          .filter()
          .timestampGreaterThan(tenMinutesAgo)
          .findAll();
      final hasProgress = recentEvents.any(
        (event) => event.eventType == 'task_progress' || event.eventType == 'task_completed',
      );
      if (!hasProgress) {
        onTrigger('task_stuck_no_start', {'duration_minutes': 10});
      }
    });

    _usageSubscription?.cancel();
    _usageSubscription = _appUsageService.usageEvents.listen((event) {
      if (!event.isForeground) return;
      _switchEvents.add(event.timestamp);
      _switchEvents.removeWhere(
        (item) => event.timestamp.difference(item) > const Duration(minutes: 5),
      );
      if (_switchEvents.length >= 3) {
        onTrigger('distraction_pattern', {'switch_count': _switchEvents.length});
        _switchEvents.clear();
      }
    });
  }

  void dispose() {
    _taskStuckTimer?.cancel();
    _usageSubscription?.cancel();
    _appUsageService.stopMonitoring();
  }
}
