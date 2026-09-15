import 'package:shared_preferences/shared_preferences.dart';

/// Maps task IDs to their notification IDs
///
/// This service maintains a persistent mapping between task IDs and the
/// notification IDs that were scheduled for them. This allows us to:
/// 1. Cancel all notifications for a specific task
/// 2. Avoid ID collisions by storing the actual notification IDs
class TaskNotificationIdMapper {
  static const String _keyPrefix = 'task_notification_';
  static SharedPreferences? _prefs;

  /// Initialize the mapper
  static Future<void> init() async {
    _prefs ??= await SharedPreferences.getInstance();
  }

  SharedPreferences get _instance {
    if (_prefs == null) {
      throw Exception(
        'TaskNotificationIdMapper not initialized. Call init() first.',
      );
    }
    return _prefs!;
  }

  /// Save the mapping between a task ID and its notification IDs
  Future<void> saveMapping(String taskId, List<int> notificationIds) async {
    final key = '$_keyPrefix$taskId';
    await _instance.setStringList(
      key,
      notificationIds.map((id) => id.toString()).toList(),
    );
  }

  /// Get all notification IDs for a specific task
  Future<List<int>> getNotificationIds(String taskId) async {
    final key = '$_keyPrefix$taskId';
    final idStrings = _instance.getStringList(key);
    if (idStrings == null) return [];
    return idStrings.map((s) => int.tryParse(s) ?? -1).where((id) => id >= 0).toList();
  }

  /// Remove the mapping for a specific task
  Future<void> removeMapping(String taskId) async {
    final key = '$_keyPrefix$taskId';
    await _instance.remove(key);
  }

  /// Clear all task notification mappings
  Future<void> clearAll() async {
    final keys = _instance.getKeys();
    for (final key in keys) {
      if (key.startsWith(_keyPrefix)) {
        await _instance.remove(key);
      }
    }
  }

  /// Get all task IDs that have notifications
  Future<List<String>> getAllTaskIds() async {
    final keys = _instance.getKeys();
    return keys
        .where((key) => key.startsWith(_keyPrefix))
        .map((key) => key.substring(_keyPrefix.length))
        .toList();
  }
}
