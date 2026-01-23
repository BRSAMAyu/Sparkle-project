import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';
import 'package:sparkle/core/offline/models/focus_session_record.dart';
import 'package:sparkle/core/offline/models/translation_record.dart';
import 'package:sparkle/core/offline/models/vocab_word.dart';

// Use different implementations for web and other platforms
import 'local_database_web.dart' if (dart.library.io) 'local_database_native.dart';

// Global provider for the database instance
final localDatabaseProvider = Provider<LocalDatabase>((ref) => LocalDatabase());

enum SyncStatus {
// ... existing code ...
  pending,
  synced,
  conflict,
  failed,
  waitingAck,
}

@collection
class LocalKnowledgeNode {
  Id id = Isar.autoIncrement;

  @Index(unique: true)
  late String serverId; // Corresponds to server node ID

  late String name;
  late int mastery;
  late DateTime lastUpdated;

  late int globalSparkCount; // New collaborative field

  int revision = 0; // Logical clock for conflict resolution

  @enumerated
  late SyncStatus syncStatus; // pending, synced, conflict

  String? error; // To store error messages
}

@collection
class PendingUpdate {
  Id id = Isar.autoIncrement;

  late String nodeId;
  late int newMastery;
  late DateTime timestamp;
  late bool synced;

  @Index()
  late DateTime createdAt;

  String? requestId; // UUID for ACK matching
  int revision = 0; // Logical clock at the time of update

  String? error; // To store error messages

  @enumerated
  SyncStatus syncStatus = SyncStatus.pending;
}

@collection
class LocalCRDTSnapshot {
  Id id = Isar.autoIncrement;

  @Index(unique: true)
  late String galaxyId;

  late List<int> updateData;
  late DateTime timestamp;
  late bool synced;
}

@collection
class OutboxItem {
  Id id = Isar.autoIncrement;

  @Index()
  String? type; // Legacy: e.g. 'mastery_update', 'spark_creation'

  @Index()
  String? uuid;

  @Index()
  String? topic; // e.g. 'cognitive', 'knowledge', 'analytics'

  String? opType; // create/update/delete/patch

  String? entityType;
  String? entityId;

  String? payloadJson; // Serialized JSON payload
  List<int>? payloadBytes; // Optional protobuf payload

  @Index()
  String? dedupeKey;

  @Index()
  late DateTime createdAt;

  int attemptCount = 0;
  DateTime? lastSentAt;
  DateTime? nextAttemptAt;
  String? lastErrorCode;
  int priority = 0;
  bool requiresAuth = true;
  String? traceId;

  int retryCount = 0; // Legacy field; keep for compatibility

  @enumerated
  SyncStatus status = SyncStatus.pending;

  String? error;
}

class LocalDatabase {
  factory LocalDatabase() => _instance;

  LocalDatabase._internal();
  static final LocalDatabase _instance = LocalDatabase._internal();
  late Isar isar;

  Future<void> init() async {
    final dir = await getApplicationDocumentsDirectory();
    // In production, you would fetch a secure key from SecureStorage
    // final secureStorage = const FlutterSecureStorage();
    // final encryptionKey = await secureStorage.read(key: 'db_key');

    isar = await Isar.open(
      [
        LocalKnowledgeNodeSchema,
        PendingUpdateSchema,
        LocalCRDTSnapshotSchema,
        OutboxItemSchema,
        UserAnalyticsEventSchema, // Added for Edge AI
        TranslationRecordSchema,
        TranslationWordLinkSchema,
        VocabWordSchema,
        VocabReviewSchema,
        FocusSessionRecordSchema, // Added for focus statistics
      ],
      directory: dir.path,
    );
  }

  // Convenience accessors for collections
  IsarCollection<TranslationRecord> get translationRecords => isar.translationRecords;
  IsarCollection<TranslationWordLink> get translationWordLinks => isar.translationWordLinks;
  IsarCollection<VocabWord> get vocabWords => isar.vocabWords;
  IsarCollection<VocabReview> get vocabReviews => isar.vocabReviews;
  IsarCollection<LocalKnowledgeNode> get knowledgeNodes => isar.localKnowledgeNodes;
  IsarCollection<PendingUpdate> get pendingUpdates => isar.pendingUpdates;
  IsarCollection<LocalCRDTSnapshot> get crdtSnapshots => isar.localCRDTSnapshots;
  IsarCollection<OutboxItem> get outboxItems => isar.outboxItems;
  IsarCollection<UserAnalyticsEvent> get analyticsEvents => isar.userAnalyticsEvents;
  IsarCollection<FocusSessionRecord> get focusSessionRecords => isar.focusSessionRecords;
}
