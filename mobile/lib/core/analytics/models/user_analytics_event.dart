import 'package:isar/isar.dart';

part 'user_analytics_event.g.dart';

@collection
@Name('uae_815')
class UserAnalyticsEvent {
  Id id = Isar.autoIncrement;

  @Index(name: 'i_uae_et_106')
  late String eventType; // e.g., 'app_open', 'task_completed', 'focus_session_start'

  @Index(name: 'i_uae_ts_1220')
  late DateTime timestamp;

  String? metadataJson; // JSON string for extra details (duration, taskId, etc.)
  
  // Helper to store structured metadata
  // Map<String, dynamic> get metadata => metadataJson != null ? jsonDecode(metadataJson!) : {};
}
