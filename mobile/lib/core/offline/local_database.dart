import 'package:isar/isar.dart';
import 'package:path_provider/path_provider.dart';

part 'local_database.g.dart';

enum SyncStatus {
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
  
  String? error; // To store error messages
  
  @enumerated
  SyncStatus syncStatus = SyncStatus.pending;
}

class LocalDatabase {
  static final LocalDatabase _instance = LocalDatabase._internal();
  late Isar isar;

  factory LocalDatabase() {
    return _instance;
  }

  LocalDatabase._internal();

  Future<void> init() async {
    final dir = await getApplicationDocumentsDirectory();
    isar = await Isar.open(
      [LocalKnowledgeNodeSchema, PendingUpdateSchema],
      directory: dir.path,
    );
  }
}
