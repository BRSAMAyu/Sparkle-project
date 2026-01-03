import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:isar/isar.dart';
import 'package:logger/logger.dart';
import 'package:uuid/uuid.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/services/websocket_service.dart';
import 'package:sparkle/core/offline/conflict_resolver.dart';
import 'dart:async';

class BusinessException implements Exception {
  BusinessException(this.message);
  final String message;
  @override
  String toString() => message;
}

class UpdateNodeMasteryMessage {
  
  UpdateNodeMasteryMessage({
    required this.nodeId, 
    required this.mastery,
    required this.timestamp,
    required this.requestId,
    required this.revision,
  });
  final String nodeId;
  final int mastery;
  final DateTime timestamp;
  final String requestId;
  final int revision;
  
  Map<String, dynamic> toJson() => {
    'type': 'update_node_mastery',
    'payload': {
      'nodeId': nodeId,
      'mastery': mastery,
      'version': timestamp.toIso8601String(), // Keep for legacy/audit
      'requestId': requestId,
      'revision': revision,
    },
  };
}

class OfflineSyncQueue {

  OfflineSyncQueue(this._localDb, this._wsService, this._connectivity) {
    _listenForAcks();
  }
  final LocalDatabase _localDb;
  final WebSocketService _wsService;
  final Connectivity _connectivity;
  final Logger _logger = Logger();
  final ConflictResolver _conflictResolver = ConflictResolver();
  final Uuid _uuid = const Uuid();
  
  StreamSubscription? _ackSubscription;

  void _listenForAcks() {
    // This global listener is kept for general monitoring or other message types.
    // Specific ACK handling is done via _waitForAck's temporary listeners or a centralized dispatcher.
    // For now, we keep this empty or for logging, as _waitForAck attaches its own listener.
  }
  
  void dispose() {
    _ackSubscription?.cancel();
  }

  Future<void> queueMasteryUpdate(String nodeId, int mastery) async {
    final requestId = _uuid.v4();
    
    // 1. Immediately store to local DB (Optimistic Update)
    await _localDb.isar.writeTxn(() async {
      final node = await _localDb.isar.localKnowledgeNodes
          .filter()
          .serverIdEqualTo(nodeId)
          .findFirst();

      var currentRevision = 0;
      if (node != null) {
        node.mastery = mastery;
        node.lastUpdated = DateTime.now();
        node.revision = node.revision + 1; // Increment revision
        currentRevision = node.revision;
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
          ..requestId = requestId
          ..revision = currentRevision,
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

        // Ensure requestId exists (for migration of old pending updates)
        final reqId = update.requestId ?? _uuid.v4();

        // Send to server
        final message = UpdateNodeMasteryMessage(
          nodeId: update.nodeId,
          mastery: update.newMastery,
          timestamp: update.timestamp,
          requestId: reqId,
          revision: update.revision,
        );
        
        final ackFuture = _waitForAck(reqId);
        
        _wsService.send(message.toJson());

        // Wait for ACK with timeout
        await ackFuture.timeout(const Duration(seconds: 5));

        // Mark as synced
        await _localDb.isar.writeTxn(() async {
          update.synced = true;
          update.syncStatus = SyncStatus.synced;
          update.requestId ??= reqId;
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
             _logger.w('Sync timed out for update ${update.id}');
             await _localDb.isar.writeTxn(() async {
                update.syncStatus = SyncStatus.pending; // Revert to pending to retry later
                await _localDb.isar.pendingUpdates.put(update);
             });
        } else if (e is BusinessException) {
          // Permanent Error (e.g., stale update / conflict)
          _logger.e('Sync failed permanently for update ${update.id}: $e');
          
          await _localDb.isar.writeTxn(() async {
            update.synced = true; // Remove from active queue
            update.error = e.message;
            update.syncStatus = SyncStatus.failed; 
            await _localDb.isar.pendingUpdates.put(update);
          });

          // Trigger conflict resolution if needed
          if (e.message.contains('conflict') || e.message.contains('stale')) {
             // Request latest state from server
             // requestNodeSync(update.nodeId);
          }
          
          continue; 
        } else {
          // Transient Error
          _logger.i('Transient sync error, pausing queue: $e');
          await _localDb.isar.writeTxn(() async {
            update.syncStatus = SyncStatus.pending;
            await _localDb.isar.pendingUpdates.put(update);
          });
          break; // Stop queue processing
        }
      }
    }
  }
  
  Future<void> _waitForAck(String requestId) {
      final completer = Completer<void>();
      
      final subscription = _wsService.stream.listen((message) {
          if (message is Map && message['type'] == 'ack_node_mastery') {
             final payload = message['payload'];
             // Match by request_id
             if (payload['requestId'] == requestId) {
                 completer.complete();
             }
          } else if (message is Map && message['type'] == 'error_node_mastery') {
              final payload = message['payload'];
               if (payload['requestId'] == requestId) {
                 completer.completeError(BusinessException((payload['error'] as String?) ?? 'Unknown error'));
             }
          }
      });
      
      return completer.future.whenComplete(subscription.cancel);
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
                    localNode.revision = serverNode.revision; // Sync revision
                    localNode.syncStatus = SyncStatus.synced;
                    await _localDb.isar.localKnowledgeNodes.put(localNode);
                    
                    // Clear pending updates as they are now obsolete/overwritten
                    final pendingUpdates = await _localDb.isar.pendingUpdates
                        .filter()
                        .nodeIdEqualTo(serverNode.id)
                        .syncedEqualTo(false)
                        .findAll();
                    
                    for (final p in pendingUpdates) {
                        p.synced = true;
                        p.syncStatus = SyncStatus.conflict; // Mark as resolved via conflict
                        await _localDb.isar.pendingUpdates.put(p);
                    }
                } else {
                   // Local wins.
                   // Ideally we should force a push here if our revision is higher,
                   // but syncPendingUpdates loop will handle it eventually.
                }
            } else {
                // No conflict, just update
                // Only update if server revision is newer
                if (serverNode.revision > localNode.revision) {
                    localNode.mastery = serverNode.mastery;
                    localNode.lastUpdated = serverNode.lastUpdated;
                    localNode.revision = serverNode.revision;
                    localNode.syncStatus = SyncStatus.synced;
                    await _localDb.isar.localKnowledgeNodes.put(localNode);
                }
            }
        } else {
            // New node from server
             final newNode = LocalKnowledgeNode()
                ..serverId = serverNode.id
                ..name = 'Unknown' // Should be fetched
                ..mastery = serverNode.mastery
                ..lastUpdated = serverNode.lastUpdated
                ..revision = serverNode.revision
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

