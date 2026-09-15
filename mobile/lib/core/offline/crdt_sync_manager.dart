/// CRDT synchronization for collaborative offline-first features.
///
/// The current sync architecture uses:
/// - Outbox queue pattern for reliable local-to-server sync
/// - Exponential backoff retry logic
/// - Isar database for local persistence
/// - Local CRDT snapshots for replay/recovery
/// - Operation-based CRDT merges for mastery, tasks, and chat messages
///
/// The backend can translate the JSON CmRDT deltas into its Yjs document while
/// the mobile client keeps deterministic local merge semantics and ACK-backed
/// replay.
///
/// @see sync_engine.dart for the current sync implementation
library;

import 'dart:async';
import 'dart:convert';

import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/offline_crdt_document.dart';
import 'package:sparkle/core/offline/sync_engine.dart';
import 'package:uuid/uuid.dart';

enum SyncType {
  knowledgeNode,
  chatMessage,
  task,
  userPreference,
}

class CRDTSyncManager {
  CRDTSyncManager(
    this._localDb,
    this._syncEngine, {
    String? actorId,
  }) : _actorId = actorId ?? const Uuid().v4();

  final LocalDatabase _localDb;
  final SyncEngine _syncEngine;
  final String _actorId;
  final Uuid _uuid = const Uuid();

  void initialize() {
    _syncEngine.start();
  }

  void dispose() {
    _syncEngine.stop();
  }

  /// Apply a CRDT update from a remote peer or local change.
  ///
  /// The preferred payload is `sparkle-crdt-v1` JSON bytes containing an
  /// `operations` array. Undecodable binary data is persisted only for backward
  /// compatibility and is not sent as a new mobile delta.
  Future<void> applyUpdate(
    List<int> update, {
    String? origin,
    String galaxyId = 'default',
  }) async {
    final operations = _tryDecodeOperations(update);
    if (operations.isEmpty) {
      await _persistSnapshot(
        galaxyId: galaxyId,
        update: update,
        synced: origin != 'local',
      );
      return;
    }

    final document = await _loadDocument(galaxyId);
    document.applyAll(operations);
    await _persistDocument(
      galaxyId: galaxyId,
      document: document,
      synced: origin != 'local',
    );

    if (origin == 'local' && operations.isNotEmpty) {
      await _enqueueOperations(galaxyId, document, operations);
    }
  }

  Future<void> applyKnowledgeMasteryDelta({
    required String nodeId,
    required int delta,
    String galaxyId = 'default',
  }) async {
    if (delta == 0) return;
    final document = await _loadDocument(galaxyId);
    final operation = makeKnowledgeMasteryDelta(
      opId: _uuid.v4(),
      actorId: _actorId,
      nodeId: nodeId,
      delta: delta,
      lamport: document.nextLamport(_actorId),
      createdAt: DateTime.now().toUtc(),
    );
    await _applyLocalOperations(galaxyId, document, [operation]);
  }

  Future<void> setKnowledgeMastery({
    required String nodeId,
    required int mastery,
    String galaxyId = 'default',
  }) async {
    final document = await _loadDocument(galaxyId);
    final target = mastery.clamp(0, 100);
    final delta = target - document.knowledgeMastery(nodeId);
    if (delta == 0) return;
    final operation = makeKnowledgeMasteryDelta(
      opId: _uuid.v4(),
      actorId: _actorId,
      nodeId: nodeId,
      delta: delta,
      lamport: document.nextLamport(_actorId),
      createdAt: DateTime.now().toUtc(),
    );
    await _applyLocalOperations(galaxyId, document, [operation]);
  }

  Future<void> setTaskState({
    required String taskId,
    required String status,
    String galaxyId = 'default',
    Map<String, dynamic> metadata = const <String, dynamic>{},
  }) async {
    final document = await _loadDocument(galaxyId);
    final operation = makeTaskStatusOperation(
      opId: _uuid.v4(),
      actorId: _actorId,
      taskId: taskId,
      status: status,
      lamport: document.nextLamport(_actorId),
      createdAt: DateTime.now().toUtc(),
      metadata: metadata,
    );
    await _applyLocalOperations(galaxyId, document, [operation]);
  }

  Future<void> appendChatMessage({
    required String sessionId,
    required String messageId,
    required String content,
    required String role,
    String galaxyId = 'default',
    Map<String, dynamic> metadata = const <String, dynamic>{},
  }) async {
    final document = await _loadDocument(galaxyId);
    final operation = makeChatAddOperation(
      opId: _uuid.v4(),
      actorId: _actorId,
      sessionId: sessionId,
      messageId: messageId,
      content: content,
      role: role,
      lamport: document.nextLamport(_actorId),
      createdAt: DateTime.now().toUtc(),
      metadata: metadata,
    );
    await _applyLocalOperations(galaxyId, document, [operation]);
  }

  /// Synchronize with server
  Future<void> sync() async {
    // Trigger SyncEngine processing is automatic via Isar watch
  }

  /// Resolve conflict using CRDT logic (automatic merge)
  Future<void> resolveConflict(
    List<int> remoteUpdate, {
    String galaxyId = 'default',
  }) async {
    await applyUpdate(remoteUpdate, origin: 'remote', galaxyId: galaxyId);
  }

  Future<LocalCRDTSnapshot?> getSnapshot(String galaxyId) async =>
      _localDb.isar.localCRDTSnapshots.getByGalaxyId(galaxyId);

  Future<OfflineCrdtDocument> getDocument(String galaxyId) =>
      _loadDocument(galaxyId);

  Future<void> _applyLocalOperations(
    String galaxyId,
    OfflineCrdtDocument document,
    List<OfflineCrdtOperation> operations,
  ) async {
    document.applyAll(operations);
    await _persistDocument(
      galaxyId: galaxyId,
      document: document,
      synced: false,
    );
    await _enqueueOperations(galaxyId, document, operations);
  }

  Future<OfflineCrdtDocument> _loadDocument(String galaxyId) async {
    final snapshot =
        await _localDb.isar.localCRDTSnapshots.getByGalaxyId(galaxyId);
    if (snapshot == null) return OfflineCrdtDocument.empty();

    try {
      return OfflineCrdtDocument.fromBytes(snapshot.updateData);
    } catch (_) {
      return OfflineCrdtDocument.empty();
    }
  }

  Future<void> _persistDocument({
    required String galaxyId,
    required OfflineCrdtDocument document,
    required bool synced,
  }) =>
      _persistSnapshot(
        galaxyId: galaxyId,
        update: document.toBytes(),
        synced: synced,
      );

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

  Future<void> _enqueueOperations(
    String galaxyId,
    OfflineCrdtDocument document,
    List<OfflineCrdtOperation> operations,
  ) async {
    await _syncEngine.enqueue(
      topic: 'crdt',
      opType: 'delta',
      payload: operationsPayload(
        galaxyId: galaxyId,
        actorId: _actorId,
        operations: operations,
        document: document,
      ),
      entityType: 'crdt_delta',
      entityId: galaxyId,
      dedupeKey: operations.map((operation) => operation.opId).join(','),
    );
  }

  List<OfflineCrdtOperation> _tryDecodeOperations(List<int> update) {
    try {
      final decoded = jsonDecode(utf8.decode(update));
      if (decoded is! Map) return const <OfflineCrdtOperation>[];
      return operationsFromPayload(decoded.cast<String, dynamic>());
    } catch (_) {
      return const <OfflineCrdtOperation>[];
    }
  }
}
