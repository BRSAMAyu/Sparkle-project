import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';
import 'package:sparkle/core/offline/models/focus_session_record.dart';
import 'package:sparkle/core/offline/models/offline_chat_message.dart';
import 'package:sparkle/core/offline/models/translation_record.dart';
import 'package:sparkle/core/offline/models/vocab_word.dart';
import 'package:sparkle/core/statistics/data/models/cached_statistics_model.dart';

part 'local_database.g.dart';

// Global provider for the database instance
final localDatabaseProvider = Provider<LocalDatabase>((ref) => LocalDatabase());

/// Set to true in test setUp to suppress Isar-related crashes.
/// When true, collection accessors return empty results instead of throwing.
bool localDatabaseTestMode = false;

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

  Isar? _isar;
  bool _initialized = false;

  /// Returns the Isar instance, or null if not initialized (test mode).
  Isar? get isarOrNull {
    if (!_initialized || _isar == null) return null;
    return _isar!;
  }

  Isar get isar {
    if (!_initialized || _isar == null) {
      if (localDatabaseTestMode) {
        throw StateError('LocalDatabase.testMode: isar not available');
      }
      throw StateError('LocalDatabase not initialized. Call init() first.');
    }
    return _isar!;
  }

  bool get isInitialized => _initialized;

  Future<void> init() async {
    final dir = await getApplicationDocumentsDirectory();
    // In production, you would fetch a secure key from SecureStorage
    // final secureStorage = const FlutterSecureStorage();
    // final encryptionKey = await secureStorage.read(key: 'db_key');

    _isar = await Isar.open(
      [
        LocalKnowledgeNodeSchema,
        PendingUpdateSchema,
        LocalCRDTSnapshotSchema,
        OutboxItemSchema,
        UserAnalyticsEventSchema,
        TranslationRecordSchema,
        TranslationWordLinkSchema,
        VocabWordSchema,
        VocabReviewSchema,
        FocusSessionRecordSchema, // Added for focus statistics
        CachedStatisticsModelSchema, // Added for unified statistics caching
        OfflineChatMessageSchema, // Added for offline message queue
      ],
      directory: dir.path,
    );
    _initialized = true;
  }

  Future<void> clearUserScopedData() async {
    if (!_initialized || _isar == null || !_isar!.isOpen) {
      return;
    }
    await _isar!.writeTxn(() async {
      await _isar!.localKnowledgeNodes.clear();
      await _isar!.pendingUpdates.clear();
      await _isar!.localCRDTSnapshots.clear();
      await _isar!.outboxItems.clear();
      await _isar!.userAnalyticsEvents.clear();
      await _isar!.focusSessionRecords.clear();
      await _isar!.cachedStatisticsModels.clear();
      await _isar!.offlineChatMessages.clear();
      await _isar!.translationWordLinks.clear();
      await _isar!.translationRecords.clear();
      await _isar!.vocabReviews.clear();
      await _isar!.vocabWords.clear();
    });
  }

  // Convenience accessors
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
  IsarCollection<CachedStatisticsModel> get cachedStatistics => isar.cachedStatisticsModels;
  IsarCollection<OfflineChatMessage> get offlineChatMessages => isar.offlineChatMessages;
}
