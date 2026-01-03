import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:isar/isar.dart';
import 'package:logger/logger.dart';
import 'local_database.dart';
import '../../services/websocket_service.dart';

class BusinessException implements Exception {
  final String message;
  BusinessException(this.message);
  @override
  String toString() => message;
}

class UpdateNodeMasteryMessage {
  final String nodeId;
  final int mastery;
  final DateTime timestamp;
  
  UpdateNodeMasteryMessage({
    required this.nodeId, 
    required this.mastery,
    required this.timestamp,
  });
  
  Map<String, dynamic> toJson() => {
    'type': 'update_node_mastery',
    'payload': {
      'nodeId': nodeId,
      'mastery': mastery,
      'version': timestamp.toIso8601String(),
    }
  };
}

class OfflineSyncQueue {
  final LocalDatabase _localDb;
  final WebSocketService _wsService;
  final Connectivity _connectivity;
  final Logger _logger = Logger();

  OfflineSyncQueue(this._localDb, this._wsService, this._connectivity);

  Future<void> queueMasteryUpdate(String nodeId, int mastery) async {
    // 1. Immediately store to local DB (Optimistic Update)
    await _localDb.isar.writeTxn(() async {
      final node = await _localDb.isar.localKnowledgeNodes
          .filter()
          .serverIdEqualTo(nodeId)
          .findFirst();

      if (node != null) {
        node.mastery = mastery;
        node.lastUpdated = DateTime.now();
        node.syncStatus = SyncStatus.pending;
        await _localDb.isar.localKnowledgeNodes.put(node);
      }

      // 2. Add to sync queue
      await _localDb.isar.pendingUpdates.put(
        PendingUpdate()
          ..nodeId = nodeId
          ..newMastery = mastery
          ..timestamp = DateTime.now()
          ..synced = false
          ..createdAt = DateTime.now()
          ..syncStatus = SyncStatus.pending
      );
    });

    // 3. Try sync if online
    if (await _isOnline()) {
      await syncPendingUpdates();
    }
  }

  Future<void> syncPendingUpdates() async {
    final pending = await _localDb.isar.pendingUpdates
        .filter()
        .syncedEqualTo(false)
        .sortByCreatedAt()
        .findAll();

    for (final update in pending) {
      try {
        // Send to server with the original timestamp as version
        await _wsService.send(UpdateNodeMasteryMessage(
          nodeId: update.nodeId,
          mastery: update.newMastery,
          timestamp: update.timestamp,
        ).toJson());

        // Mark as synced
        await _localDb.isar.writeTxn(() async {
          update.synced = true;
          update.syncStatus = SyncStatus.synced;
          await _localDb.isar.pendingUpdates.put(update);

          // Update local node status
          final node = await _localDb.isar.localKnowledgeNodes
              .filter()
              .serverIdEqualTo(update.nodeId)
              .findFirst();
              
          if (node != null) {
            node.syncStatus = SyncStatus.synced;
            await _localDb.isar.localKnowledgeNodes.put(node);
          }
        });
        
      } catch (e) {
        if (e is BusinessException) {
          // Permanent Error
          _logger.e("Sync failed permanently for update ${update.id}: $e");
          
          await _localDb.isar.writeTxn(() async {
            update.synced = true; // Remove from active queue
            update.error = e.message;
            update.syncStatus = SyncStatus.failed;
            await _localDb.isar.pendingUpdates.put(update);
          });
          
          continue; // Continue to next item
        } else {
          // Transient Error
          _logger.i("Transient sync error, pausing queue: $e");
          break; // Stop queue processing
        }
      }
    }
  }

  Future<bool> _isOnline() async {
    final connectivityResult = await _connectivity.checkConnectivity();
    return !connectivityResult.contains(ConnectivityResult.none);
  }
}
