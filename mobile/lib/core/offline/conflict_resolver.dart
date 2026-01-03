import 'package:isar/isar.dart';
import 'local_database.dart';

enum ConflictResolutionType {
  useLocal,
  useServer,
  merge,
}

class ConflictResolution {
  final ConflictResolutionType type;
  final dynamic data;

  ConflictResolution._(this.type, this.data);

  factory ConflictResolution.useLocal(LocalKnowledgeNode node) {
    return ConflictResolution._(ConflictResolutionType.useLocal, node);
  }

  factory ConflictResolution.useServer(ServerKnowledgeNode node) {
    return ConflictResolution._(ConflictResolutionType.useServer, node);
  }
}

// Minimal Server Node representation for conflict resolution
class ServerKnowledgeNode {
  final String id;
  final int mastery;
  final DateTime lastUpdated;

  ServerKnowledgeNode({
    required this.id,
    required this.mastery,
    required this.lastUpdated,
  });
}

class ConflictResolver {
  Future<ConflictResolution> resolveConflict(
    LocalKnowledgeNode local,
    ServerKnowledgeNode server
  ) async {
    // Strategy 1: Timestamp Priority (Last Writer Wins)
    if (local.lastUpdated.isAfter(server.lastUpdated)) {
      return ConflictResolution.useLocal(local);
    } else if (server.lastUpdated.isAfter(local.lastUpdated)) {
      return ConflictResolution.useServer(server);
    }

    // Strategy 2: Higher Mastery Wins (Encourage Learning)
    if (local.mastery > server.mastery) {
      return ConflictResolution.useLocal(local);
    } else {
      return ConflictResolution.useServer(server);
    }
  }
}
