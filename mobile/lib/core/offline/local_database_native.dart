import 'package:isar/isar.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';
import 'package:sparkle/core/offline/models/focus_session_record.dart';
import 'package:sparkle/core/offline/models/translation_record.dart';
import 'package:sparkle/core/offline/models/vocab_word.dart';
import 'package:sparkle/core/statistics/data/models/cached_statistics_model.dart';
import 'package:sparkle/core/offline/local_database.dart';

// The schemas are imported from local_database.g.dart via local_database.dart

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
        CachedStatisticsModelSchema, // Added for unified statistics caching
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
  IsarCollection<CachedStatisticsModel> get cachedStatistics => isar.cachedStatisticsModels;
}
