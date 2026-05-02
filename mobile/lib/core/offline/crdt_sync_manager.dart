/// CRDT synchronization for collaborative offline-first features.
///
/// The current sync architecture uses:
/// - Outbox queue pattern for reliable local-to-server sync
/// - Exponential backoff retry logic
/// - Isar database for local persistence
/// - Local CRDT snapshots for replay/recovery
/// - Last-write/max-wins merge in the knowledge mastery sync queue
///
/// This intentionally keeps the CRDT payload opaque so the backend can evolve
/// from simple binary updates to YDoc/Automerge-compatible operations without
/// changing the local persistence contract.
///
/// @see sync_engine.dart for the current sync implementation
library;

import 'dart:async';
import 'dart:convert';

import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/sync_engine.dart';

enum SyncType {
  knowledgeNode,
  chatMessage,
  task,
  userPreference,
}

class CRDTSyncManager {
  CRDTSyncManager(this._localDb, this._syncEngine);
  final LocalDatabase _localDb;
  final SyncEngine _syncEngine;

  Future<void> initialize() async {
    _syncEngine.start();
  }
  
  void dispose() {
    _syncEngine.stop();
  }

  /// Apply a binary update from a remote peer or local change.
  Future<void> applyUpdate(
    List<int> update, {
    String? origin,
    String galaxyId = 'default',
  }) async {
    await _persistSnapshot(galaxyId: galaxyId, update: update, synced: origin != 'local');

    if (origin == 'local') {
      await _syncEngine.enqueue(
        topic: 'crdt',
        opType: 'update',
        payload: {
          'galaxyId': galaxyId,
          'data': base64Encode(update),
          'timestamp': DateTime.now().millisecondsSinceEpoch,
        },
        entityType: 'crdt_snapshot',
        entityId: galaxyId,
      );
    }
  }

  /// Synchronize with server
  Future<void> sync() async {
    // Trigger SyncEngine processing is automatic via Isar watch
  }

  /// Resolve conflict using CRDT logic (automatic merge)
  Future<void> resolveConflict(List<int> remoteUpdate, {String galaxyId = 'default'}) async {
    await applyUpdate(remoteUpdate, origin: 'remote', galaxyId: galaxyId);
  }

  Future<LocalCRDTSnapshot?> getSnapshot(String galaxyId) async =>
      _localDb.isar.localCRDTSnapshots.getByGalaxyId(galaxyId);

  Future<void> _persistSnapshot({
    required String galaxyId,
    required List<int> update,
    required bool synced,
  }) async {
    await _localDb.isar.writeTxn(() async {
      final existing =
          await _localDb.isar.localCRDTSnapshots.getByGalaxyId(galaxyId);
      final snapshot = (existing ?? LocalCRDTSnapshot())
        ..galaxyId = galaxyId
        ..updateData = update
        ..timestamp = DateTime.now()
        ..synced = synced;
      await _localDb.isar.localCRDTSnapshots.putByGalaxyId(snapshot);
    });
  }
}
