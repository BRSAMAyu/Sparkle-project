import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';
import 'package:sparkle/core/offline/local_database_store.dart';
import 'package:sparkle/core/offline/models/cached_list_snapshot.dart';
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
@Name('kn_950')
class LocalKnowledgeNode {
  Id id = Isar.autoIncrement;

  @Index(name: 'i_kn_si_3333', unique: true)
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
@Name('pu_2239')
class PendingUpdate {
  Id id = Isar.autoIncrement;

  late String nodeId;
  late int newMastery;
  late DateTime timestamp;
  late bool synced;

  @Index(name: 'i_pu_ca_1082')
  late DateTime createdAt;

  String? requestId; // UUID for ACK matching
  int revision = 0; // Logical clock at the time of update

  String? error; // To store error messages

  @enumerated
  SyncStatus syncStatus = SyncStatus.pending;
}

@collection
@Name('crdt_2016')
class LocalCRDTSnapshot {
  Id id = Isar.autoIncrement;

  @Index(name: 'i_crdt_gi_222', unique: true)
  late String galaxyId;

  late List<int> updateData;
  late DateTime timestamp;
  late bool synced;
}

@collection
@Name('obx_669')
class OutboxItem {
  Id id = Isar.autoIncrement;

  @Index(name: 'i_obx_ty_2494')
  String? type; // Legacy: e.g. 'mastery_update', 'spark_creation'

  @Index(name: 'i_obx_uu_2715')
  String? uuid;

  @Index(name: 'i_obx_tp_285')
  String? topic; // e.g. 'cognitive', 'knowledge', 'analytics'

  String? opType; // create/update/delete/patch

  String? entityType;
  String? entityId;

  String? payloadJson; // Serialized JSON payload
  List<int>? payloadBytes; // Optional protobuf payload

  @Index(name: 'i_obx_dk_92')
  String? dedupeKey;

  @Index(name: 'i_obx_ca_974')
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

  /// 平台存储后端（条件导入闸）：io 上为真实 Isar，web 上为 no-op 桩。
  /// 见 local_database_store.dart 与 local_database_store_web.dart 的 TODO。
  final LocalDatabaseStore _store = createLocalDatabaseStore();

  /// Test-only injection; takes precedence over [_store] when set.
  Isar? _isarOverride;

  /// Returns the Isar instance, or null if not initialized (test mode / web stub).
  Isar? get isarOrNull => _isarOverride ?? _store.isarOrNull;

  Isar get isar {
    final isar = isarOrNull;
    if (isar != null) {
      return isar;
    }
    if (localDatabaseTestMode) {
      throw StateError('LocalDatabase.testMode: isar not available');
    }
    if (_store.kind == 'web-stub') {
      // TODO(multi-platform): Web 端离线存储（IndexedDB）接入前，依赖 Isar
      // 的离线队列 / 翻译历史 / 统计缓存 / CRDT 快照在 Web 上降级不可用。
      throw UnsupportedError(
        'LocalDatabase: Isar is unavailable on Web (web-stub backend, '
        'see local_database_store_web.dart).',
      );
    }
    throw StateError('LocalDatabase not initialized. Call init() first.');
  }

  bool get isInitialized => _isarOverride != null || _store.isReady;

  /// Test-only setter to inject a real Isar instance without calling init().
  set isar(Isar value) {
    _isarOverride = value;
  }

  Future<void> init() async {
    if (_isarOverride != null) return; // 测试注入的实例优先，避免被真实打开覆盖
    await _store.init(<CollectionSchema<dynamic>>[
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
      CachedListSnapshotSchema, // N34: warm read snapshots for task/error_book/community
      OfflineChatMessageSchema, // Added for offline message queue
    ]);
  }

  Future<void> clearUserScopedData() async {
    final isar = isarOrNull;
    if (isar == null || !isar.isOpen) {
      return;
    }
    await isar.writeTxn(() async {
      await isar.localKnowledgeNodes.clear();
      await isar.pendingUpdates.clear();
      await isar.localCRDTSnapshots.clear();
      await isar.outboxItems.clear();
      await isar.userAnalyticsEvents.clear();
      await isar.focusSessionRecords.clear();
      await isar.cachedStatisticsModels.clear();
      await isar.cachedListSnapshots.clear();
      await isar.offlineChatMessages.clear();
      await isar.translationWordLinks.clear();
      await isar.translationRecords.clear();
      await isar.vocabReviews.clear();
      await isar.vocabWords.clear();
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
  IsarCollection<CachedListSnapshot> get cachedListSnapshots => isar.cachedListSnapshots;
  IsarCollection<OfflineChatMessage> get offlineChatMessages => isar.offlineChatMessages;
}
