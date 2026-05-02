// ignore_for_file: cascade_invocations

import 'dart:async';
import 'dart:convert';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/offline/conflict_resolver.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/offline_crdt_document.dart';
import 'package:sparkle/core/offline/outbox_dedupe_key.dart';
import 'package:sparkle/core/offline/sync_engine.dart';
import 'package:sparkle/core/services/performance_monitor.dart';
import 'package:sparkle/core/tracing/tracing_service.dart';
import 'package:uuid/uuid.dart';

class OfflineSyncQueue {
  OfflineSyncQueue(
    this._localDb,
    this._connectivity, {
    required SyncEngine syncEngine,
    PerformanceMonitor? performanceMonitor,
  })  : _syncEngine = syncEngine,
        _performanceMonitor = performanceMonitor ?? PerformanceMonitor();
  final LocalDatabase _localDb;
  final Connectivity _connectivity;
  final SyncEngine _syncEngine;
  final PerformanceMonitor _performanceMonitor;
  final ConflictResolver _conflictResolver = ConflictResolver();
  final Uuid _uuid = const Uuid();
  final String _actorId = const Uuid().v4();

  void dispose() {}

  Future<void> queueMasteryUpdate(String nodeId, int mastery) async {
    final requestId = _uuid.v4();
    final startTime = DateTime.now();

    try {
      // 跟踪同步开始
      _performanceMonitor.trackOfflineSync(
        syncType: 'mastery_update',
        itemCount: 1,
        success: false, // 初始状态
        durationMs: 0,
      );

      final masteryDelta = await _buildMasteryDelta(nodeId, mastery);
      final mergedMastery = masteryDelta.document.knowledgeMastery(nodeId);

      // 1. Immediately store to local DB (Optimistic Update)
      await _localDb.isar.writeTxn(() async {
        final node = await _localDb.isar.localKnowledgeNodes
            .filter()
            .serverIdEqualTo(nodeId)
            .findFirst();

        var currentRevision = 0;
        if (node != null) {
          node.mastery = mergedMastery;
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
            ..newMastery = mergedMastery
            ..timestamp = DateTime.now()
            ..synced = false
            ..createdAt = DateTime.now()
            ..syncStatus = SyncStatus.pending
            ..requestId = requestId
            ..revision = currentRevision,
        );

        await _localDb.isar.localCRDTSnapshots.putByGalaxyId(
          (await _localDb.isar.localCRDTSnapshots
                  .getByGalaxyId(masteryDelta.galaxyId) ??
              LocalCRDTSnapshot())
            ..galaxyId = masteryDelta.galaxyId
            ..updateData = masteryDelta.document.toBytes()
            ..timestamp = DateTime.now()
            ..synced = false,
        );

        if (masteryDelta.operation != null) {
          await _localDb.isar.outboxItems.put(
            OutboxItem()
              ..uuid = _uuid.v4()
              ..type = 'crdt_delta'
              ..topic = 'crdt'
              ..opType = 'delta'
              ..entityType = 'knowledge_mastery'
              ..entityId = nodeId
              ..payloadJson = jsonEncode(
                operationsPayload(
                  galaxyId: masteryDelta.galaxyId,
                  actorId: masteryDelta.operation!.actorId,
                  operations: [masteryDelta.operation!],
                  document: masteryDelta.document,
                ),
              )
              ..dedupeKey = OutboxDedupeKey.knowledgeUpdate(nodeId, requestId)
              ..createdAt = DateTime.now()
              ..priority = 10
              ..requiresAuth = true
              ..traceId = TracingService.instance.createTraceId()
              ..status = SyncStatus.pending,
          );
        }
      });

      // 3. Try sync if online
      if (await _isOnline()) {
        await _syncEngine.processNow();
      }

      // 记录同步成功
      final duration = DateTime.now().difference(startTime);
      _performanceMonitor.trackOfflineSync(
        syncType: 'mastery_update',
        itemCount: 1,
        success: true,
        durationMs: duration.inMilliseconds,
      );
    } catch (e, stackTrace) {
      // 记录同步失败
      final duration = DateTime.now().difference(startTime);
      _performanceMonitor.trackOfflineSync(
        syncType: 'mastery_update',
        itemCount: 1,
        success: false,
        error: e.toString(),
        durationMs: duration.inMilliseconds,
      );

      // 报告崩溃
      _performanceMonitor.reportCrash(
        e,
        stackTrace,
        context: 'queueMasteryUpdate',
      );

      // 重新抛出异常
      rethrow;
    }
  }

  Future<void> syncPendingUpdates() async {
    await _syncEngine.processNow();
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
          final resolution =
              await _conflictResolver.resolveConflict(localNode, serverNode);

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
              p.syncStatus =
                  SyncStatus.conflict; // Mark as resolved via conflict
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

  Future<_MasteryCrdtDelta> _buildMasteryDelta(
    String nodeId,
    int newMastery,
  ) async {
    const galaxyId = 'default';
    final snapshot =
        await _localDb.isar.localCRDTSnapshots.getByGalaxyId(galaxyId);
    final document = snapshot != null
        ? OfflineCrdtDocument.fromBytes(snapshot.updateData)
        : OfflineCrdtDocument.empty();
    final targetMastery = newMastery.clamp(0, 100);
    final delta = targetMastery - document.knowledgeMastery(nodeId);
    if (delta == 0) {
      return _MasteryCrdtDelta(
        galaxyId: galaxyId,
        document: document,
      );
    }

    final operation = makeKnowledgeMasteryDelta(
      opId: _uuid.v4(),
      actorId: _actorId,
      nodeId: nodeId,
      delta: delta,
      lamport: document.nextLamport(_actorId),
      createdAt: DateTime.now().toUtc(),
    );
    document.apply(operation);

    return _MasteryCrdtDelta(
      galaxyId: galaxyId,
      document: document,
      operation: operation,
    );
  }

  Future<bool> _isOnline() async {
    final connectivityResult = await _connectivity.checkConnectivity();
    return !connectivityResult.contains(ConnectivityResult.none);
  }
}

class _MasteryCrdtDelta {
  const _MasteryCrdtDelta({
    required this.galaxyId,
    required this.document,
    this.operation,
  });

  final String galaxyId;
  final OfflineCrdtDocument document;
  final OfflineCrdtOperation? operation;
}
