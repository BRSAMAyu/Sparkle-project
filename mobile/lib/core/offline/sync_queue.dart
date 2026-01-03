import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:isar/isar.dart';
import 'package:logger/logger.dart';
import 'local_database.dart';
import '../services/websocket_service.dart';
import 'conflict_resolver.dart';
import 'dart:async';

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
  final ConflictResolver _conflictResolver = ConflictResolver();
  
  final Map<int, Completer<bool>> _ackCompleters = {};
  StreamSubscription? _ackSubscription;

  OfflineSyncQueue(this._localDb, this._wsService, this._connectivity) {
    _listenForAcks();
  }

  void _listenForAcks() {
    _ackSubscription = _wsService.stream.listen((message) {
      if (message is Map && message['type'] == 'ack_node_mastery') {
        final payload = message['payload'];
        if (payload != null) {
           final updateId = payload['updateId'] as int?; // Assume server echoes back our local update ID if we sent it, or use request ID
           // In a real scenario, we need a way to correlate request and response.
           // For now, assuming we handle ACKs via a mechanism where we can match them.
           // If the protocol doesn't support request ID, we might need to rely on nodeId + timestamp.
        }
      }
    });
  }
  
  void dispose() {
    _ackSubscription?.cancel();
  }

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
        // Mark as waiting for ACK
        await _localDb.isar.writeTxn(() async {
          update.syncStatus = SyncStatus.waitingAck;
          await _localDb.isar.pendingUpdates.put(update);
        });

        // Send to server with the original timestamp as version
        final message = UpdateNodeMasteryMessage(
          nodeId: update.nodeId,
          mastery: update.newMastery,
          timestamp: update.timestamp,
        );
        
        final ackFuture = _waitForAck(update.nodeId, update.timestamp);
        
        _wsService.send(message.toJson());

        // Wait for ACK with timeout
        await ackFuture.timeout(const Duration(seconds: 5));

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
        if (e is TimeoutException) {
             _logger.w("Sync timed out for update ${update.id}");
             await _localDb.isar.writeTxn(() async {
                update.syncStatus = SyncStatus.pending; // Revert to pending to retry later
                await _localDb.isar.pendingUpdates.put(update);
             });
        } else if (e is BusinessException) {
          // Permanent Error (e.g., stale update)
          _logger.e("Sync failed permanently for update ${update.id}: $e");
          
          await _localDb.isar.writeTxn(() async {
            update.synced = true; // Remove from active queue
            update.error = e.message;
            update.syncStatus = SyncStatus.failed; // Or conflict
            await _localDb.isar.pendingUpdates.put(update);
          });

          // Trigger conflict resolution if it's a stale update
          if (e.message.contains("stale") || e.message.contains("conflict")) {
             // In a real scenario, we would need the server's version of the node here.
             // Since the error message might not contain the full node data, 
             // we might need to fetch the latest state or wait for a push update.
             // For now, we assume the server will push the latest state shortly after rejection,
             // or we can explicitly request it.
             // requestNodeSync(update.nodeId); 
          }
          
          continue; // Continue to next item
        } else {
          // Transient Error
          _logger.i("Transient sync error, pausing queue: $e");
          await _localDb.isar.writeTxn(() async {
            update.syncStatus = SyncStatus.pending;
            await _localDb.isar.pendingUpdates.put(update);
          });
          break; // Stop queue processing
        }
      }
    }
  }
  
  Future<void> _waitForAck(String nodeId, DateTime timestamp) {
      final completer = Completer<void>();
      // Determine a key to identify this request. 
      // In a real app we'd use a unique ID in the message.
      // Here we rely on nodeId and timestamp.
      final key = "${nodeId}_${timestamp.millisecondsSinceEpoch}";
      
      // We need a way to register this completer so the main listener can complete it.
      // Since _listenForAcks is generic, let's make it smarter or add a one-off listener.
      
      // Ideally, we'd add to a map of pending acks.
      // For this implementation, let's use a temporary subscription filter.
      
      final subscription = _wsService.stream.listen((message) {
          if (message is Map && message['type'] == 'ack_update_node_mastery') {
             final payload = message['payload'];
             if (payload['nodeId'] == nodeId && 
                 payload['version'] == timestamp.toIso8601String()) {
                 completer.complete();
             }
          } else if (message is Map && message['type'] == 'error_update_node_mastery') {
              final payload = message['payload'];
               if (payload['nodeId'] == nodeId && 
                 payload['version'] == timestamp.toIso8601String()) {
                 completer.completeError(BusinessException((payload['error'] as String?) ?? 'Unknown error'));
             }
          }
      });
      
      return completer.future.whenComplete(() {
          subscription.cancel();
      });
  }
  
  // Handle server-side updates (conflict resolution)
  Future<void> handleServerUpdate(ServerKnowledgeNode serverNode) async {
    await _localDb.isar.writeTxn(() async {
        final localNode = await _localDb.isar.localKnowledgeNodes
            .filter()
            .serverIdEqualTo(serverNode.id)
            .findFirst();
            
        if (localNode != null) {
            // Check if we have pending updates for this node
            final hasPending = await _localDb.isar.pendingUpdates
                .filter()
                .nodeIdEqualTo(serverNode.id)
                .syncedEqualTo(false)
                .isNotEmpty();
                
            if (hasPending) {
                // Conflict!
                final resolution = await _conflictResolver.resolveConflict(localNode, serverNode);
                
                if (resolution.type == ConflictResolutionType.useServer) {
                   // Server wins, update local and clear pending
                    localNode.mastery = serverNode.mastery;
                    localNode.lastUpdated = serverNode.lastUpdated;
                    localNode.syncStatus = SyncStatus.synced;
                    await _localDb.isar.localKnowledgeNodes.put(localNode);
                    
                    // Clear pending updates as they are now obsolete/overwritten
                    final pendingUpdates = await _localDb.isar.pendingUpdates
                        .filter()
                        .nodeIdEqualTo(serverNode.id)
                        .syncedEqualTo(false)
                        .findAll();
                    
                    for (var p in pendingUpdates) {
                        p.synced = true;
                        p.syncStatus = SyncStatus.conflict; // Mark as resolved via conflict
                        await _localDb.isar.pendingUpdates.put(p);
                    }
                } else {
                   // Local wins, do nothing, let the pending update overwrite server eventually
                   // Or potentially re-queue to ensure it's sent?
                   // The pending update is already in the queue.
                }
            } else {
                // No conflict, just update
                localNode.mastery = serverNode.mastery;
                localNode.lastUpdated = serverNode.lastUpdated;
                localNode.syncStatus = SyncStatus.synced;
                await _localDb.isar.localKnowledgeNodes.put(localNode);
            }
        } else {
            // New node from server
             final newNode = LocalKnowledgeNode()
                ..serverId = serverNode.id
                ..name = "Unknown" // Should be fetched
                ..mastery = serverNode.mastery
                ..lastUpdated = serverNode.lastUpdated
                ..globalSparkCount = 0
                ..syncStatus = SyncStatus.synced;
             await _localDb.isar.localKnowledgeNodes.put(newNode);
        }
    });
  }

  Future<bool> _isOnline() async {
    final connectivityResult = await _connectivity.checkConnectivity();
    return !connectivityResult.contains(ConnectivityResult.none);
  }
}

