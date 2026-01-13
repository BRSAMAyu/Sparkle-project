import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import '../../offline/local_database.dart';
import '../models/user_analytics_event.dart';

final localFeatureServiceProvider = Provider<LocalFeatureService>((ref) {
  final db = ref.watch(localDatabaseProvider);
  return LocalFeatureService(db.isar);
});

class LocalFeatureService {
  final Isar _isar;

  LocalFeatureService(this._isar);

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
      }
    };
  }
// ... existing code ...

  /// Helper to record a new event manually (to be used by other features)
  Future<void> logEvent(String type, {Map<String, dynamic>? metadata}) async {
    final event = UserAnalyticsEvent()
      ..eventType = type
      ..timestamp = DateTime.now();
    
    await _isar.writeTxn(() async {
      await _isar.userAnalyticsEvents.put(event);
    });
  }
}
