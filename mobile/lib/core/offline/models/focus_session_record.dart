import 'package:isar/isar.dart';

part 'focus_session_record.g.dart';

/// Focus session record stored locally in Isar database
/// Enables offline support and automatic sync when online
@collection
class FocusSessionRecord {
  Id id = Isar.autoIncrement;

  /// Server ID for deduplication and sync
  @Index(unique: true)
  String? serverId;

  /// Session start time
  @Index()
  late DateTime startTime;

  /// Session end time
  late DateTime endTime;

  /// Duration in minutes
  late int durationMinutes;

  /// Focus type: 'pomodoro' or 'stopwatch'
  late String focusType;

  /// Session status: 'completed' or 'interrupted'
  late String status;

  /// Associated task ID (optional)
  String? taskId;

  /// Associated task title (denormalized for display)
  String? taskTitle;

  /// White noise type used (optional)
  String? whiteNoiseType;

  /// Number of interruptions during session
  late int interruptionCount;

  /// Quality score (1-5) - self-evaluation after session
  int? qualityScore;

  /// Whether this record has been synced to server
  @Index()
  late bool isSynced;

  /// When this record was created locally
  @Index()
  late DateTime createdAt;

  /// Last sync attempt timestamp
  DateTime? lastSyncAttempt;

  /// Sync error message if sync failed
  String? syncError;
}

extension FocusSessionRecordExtension on FocusSessionRecord {
  /// Create a completed focus session record
  static FocusSessionRecord createCompleted({
    required DateTime startTime,
    required DateTime endTime,
    required int durationMinutes,
    String focusType = 'pomodoro',
    String? taskId,
    String? taskTitle,
    String? whiteNoiseType,
    int interruptionCount = 0,
    int? qualityScore,
  }) {
    final now = DateTime.now();
    return FocusSessionRecord()
      ..startTime = startTime
      ..endTime = endTime
      ..durationMinutes = durationMinutes
      ..focusType = focusType
      ..status = 'completed'
      ..taskId = taskId
      ..taskTitle = taskTitle
      ..whiteNoiseType = whiteNoiseType
      ..interruptionCount = interruptionCount
      ..qualityScore = qualityScore
      ..isSynced = false
      ..createdAt = now;
  }

  /// Create an interrupted focus session record
  static FocusSessionRecord createInterrupted({
    required DateTime startTime,
    required DateTime endTime,
    required int durationMinutes,
    String focusType = 'pomodoro',
    String? taskId,
    String? taskTitle,
    String? whiteNoiseType,
    int interruptionCount = 0,
  }) {
    final now = DateTime.now();
    return FocusSessionRecord()
      ..startTime = startTime
      ..endTime = endTime
      ..durationMinutes = durationMinutes
      ..focusType = focusType
      ..status = 'interrupted'
      ..taskId = taskId
      ..taskTitle = taskTitle
      ..whiteNoiseType = whiteNoiseType
      ..interruptionCount = interruptionCount
      ..isSynced = false
      ..createdAt = now;
  }

  /// Mark as synced with server ID
  void markAsSynced(String serverIdValue) {
    serverId = serverIdValue;
    isSynced = true;
    lastSyncAttempt = DateTime.now();
    syncError = null;
  }

  /// Mark sync as failed
  void markSyncFailed(String error) {
    isSynced = false;
    lastSyncAttempt = DateTime.now();
    syncError = error;
  }

  /// Get date key for grouping/statistics (YYYY-MM-DD format)
  String get dateKey => '${startTime.year}-${startTime.month.toString().padLeft(2, '0')}-${startTime.day.toString().padLeft(2, '0')}';

  /// Check if session was completed
  bool get isCompleted => status == 'completed';

  /// Check if session was interrupted
  bool get isInterrupted => status == 'interrupted';

  /// Get duration formatted as "Xh Ym"
  String get durationFormatted {
    final hours = durationMinutes ~/ 60;
    final minutes = durationMinutes % 60;
    if (hours > 0) {
      return '${hours}h ${minutes}m';
    }
    return '${minutes}m';
  }
}
